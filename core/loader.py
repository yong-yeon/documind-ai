import os       # 파일 경로 처리
import sys      # 모듈 경로 추가용
import tempfile # 임시 파일 생성
import fitz     # PDF 텍스트/이미지 렌더링 (PyMuPDF)
import pytesseract          # OCR 엔진 래퍼
from PIL import Image       # fitz 픽셀맵을 pytesseract에 전달하기 위한 이미지 변환

from langchain_core.documents import Document                    # LangChain 문서 객체
from langchain_text_splitters import RecursiveCharacterTextSplitter  # 텍스트 분할기

# Tesseract 절대 경로 고정 (시스템 PATH에 등록되지 않은 경우를 대비)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
OCR_THRESHOLD = 20   # fitz 추출 텍스트가 이 글자 수 미만이면 스캔 페이지로 판단
OCR_DPI       = 300  # 한국어 인식률 확보를 위한 최소 해상도
# --psm 6: 균일한 텍스트 블록으로 처리 / --oem 3: LSTM 엔진 사용 (인식률 최고)
TESS_CONFIG   = "--psm 6 --oem 3"

try:
    from config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP          # 일반 실행 시 import
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 루트 경로 추가
    from config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP          # 직접 실행 시 import


def save_uploaded_file(uploaded_file) -> tuple:
    # Streamlit 업로드 객체는 파일 경로가 없으므로 임시 파일로 저장 후 경로를 반환
    suffix = os.path.splitext(uploaded_file.name)[1]           # 원본 확장자 추출 (.pdf, .docx 등)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())                     # 업로드된 바이트를 임시 파일에 저장
        temp_path = tmp.name                                    # 임시 파일 경로 저장
    return temp_path, uploaded_file.name                        # (임시 경로, 원본 파일명) 반환


def _extract_text_from_blocks(page, filter_margins: bool = False) -> str:
    # blocks 모드로 텍스트 블록을 y→x 순으로 정렬해 읽기 순서 보정
    # filter_margins=True: 상하 8% 영역(헤더/푸터)을 제외한 본문만 추출
    page_height  = page.rect.height
    header_limit = page_height * 0.08  # 상단 8% = 헤더 영역
    footer_limit = page_height * 0.92  # 하단 8% = 푸터 영역

    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
    text_blocks = []
    for b in sorted(blocks, key=lambda b: (round(b[1] / 10), b[0])):
        if b[6] != 0 or not b[4].strip():       # 텍스트 블록(type=0)이 아니거나 빈 블록 제외
            continue
        if filter_margins and (b[1] < header_limit or b[3] > footer_limit):
            continue                             # 헤더/푸터 영역 블록 제외
        text_blocks.append(b[4])
    return "\n".join(text_blocks)


def _get_page_label(page, page_num: int) -> str:
    # PDF에 인쇄된 실제 페이지 번호 레이블을 가져옴 (예: "i", "1", "A-1")
    # 레이블이 없거나 빈 경우 물리적 순서 기반 번호(1-index)로 대체
    try:
        label = page.get_label()
        return label.strip() if label.strip() else str(page_num + 1)
    except Exception:
        return str(page_num + 1)


def load_pdf(file_path: str, original_name: str) -> list:
    doc  = fitz.open(file_path)
    docs = []
    for page_num, page in enumerate(doc):
        # OCR 판단: 헤더/푸터 포함 전체 텍스트로 체크
        raw_text = _extract_text_from_blocks(page, filter_margins=False)

        if len(raw_text.strip()) >= OCR_THRESHOLD:
            # 텍스트 레이어 충분 → 일반 PDF: 헤더/푸터 제거한 본문만 저장
            clean_text = _extract_text_from_blocks(page, filter_margins=True)
            page_label = _get_page_label(page, page_num)
            docs.append(Document(
                page_content=clean_text,
                metadata={"source": original_name, "page": page_num, "page_label": page_label}
            ))
        else:
            # 20자 미만 → 스캔 페이지: fitz로 직접 렌더링 후 OCR
            try:
                pix      = page.get_pixmap(dpi=OCR_DPI)  # 300 DPI로 페이지 렌더링
                img      = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_text = pytesseract.image_to_string(img, lang="kor+eng", config=TESS_CONFIG)
            except Exception:
                ocr_text = ""  # OCR 실패 시 조용히 건너뜀
            if ocr_text.strip():
                page_label = _get_page_label(page, page_num)
                docs.append(Document(
                    page_content=ocr_text,
                    metadata={"source": original_name, "page": page_num, "page_label": page_label}
                ))
    doc.close()
    return docs


def load_docx(file_path: str, original_name: str) -> list:
    from docx import Document as DocxDocument  # 함수 내 import로 의존성 최소화
    docx      = DocxDocument(file_path)
    full_text = []

    for para in docx.paragraphs:          # 단락(paragraph) 순회
        if para.text.strip():             # 빈 단락 제외
            full_text.append(para.text)

    for table in docx.tables:            # 표(table) 순회
        for row in table.rows:
            row_text = " | ".join(       # 셀 내용을 " | " 구분자로 이어 붙임
                cell.text.strip() for cell in row.cells if cell.text.strip()
            )
            if row_text:
                full_text.append(row_text)

    docs = []
    if full_text:
        docs.append(Document(
            page_content="\n".join(full_text),              # 전체 내용을 하나의 Document로 합침
            metadata={"source": original_name, "page": 0}  # DOCX는 페이지 구분이 없어 0으로 고정
        ))
    return docs


def load_xlsx(file_path: str, original_name: str) -> list:
    import openpyxl  # 함수 내 import로 의존성 최소화
    wb   = openpyxl.load_workbook(file_path, data_only=True)  # 수식 대신 계산된 값으로 읽기
    docs = []

    for sheet_num, sheet_name in enumerate(wb.sheetnames):  # 시트별 순회
        ws        = wb[sheet_name]
        rows_text = []
        for row in ws.iter_rows(values_only=True):          # 행별 순회
            row_data = [str(cell) for cell in row if cell is not None]  # None 셀 제외 후 문자열 변환
            if row_data:
                rows_text.append(" | ".join(row_data))      # 셀을 " | " 구분자로 연결

        if rows_text:
            docs.append(Document(
                page_content=f"[시트: {sheet_name}]\n" + "\n".join(rows_text),  # 시트명 헤더 포함
                metadata={"source": original_name, "page": sheet_num}           # 시트 번호를 페이지로 사용
            ))
    return docs


def load_pptx(file_path: str, original_name: str) -> list:
    from pptx import Presentation  # 함수 내 import로 의존성 최소화
    prs  = Presentation(file_path)
    docs = []

    for slide_num, slide in enumerate(prs.slides):  # 슬라이드별 순회
        slide_text = []
        for shape in slide.shapes:                  # 슬라이드 내 도형별 순회
            if shape.has_text_frame:                # 텍스트 박스인 경우
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if text:
                        slide_text.append(text)
            if shape.has_table:                     # 표인 경우
                for row in shape.table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        slide_text.append(row_text)

        if slide_text:
            docs.append(Document(
                page_content=f"[슬라이드 {slide_num + 1}]\n" + "\n".join(slide_text),  # 슬라이드 번호 헤더 포함
                metadata={"source": original_name, "page": slide_num}
            ))
    return docs


def load_file(file_input, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
    # 로컬 경로(str) 또는 Streamlit 업로드 객체 모두 처리
    temp_path = None
    if isinstance(file_input, str):                    # 로컬 파일 경로인 경우
        if not os.path.exists(file_input):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_input}")
        file_path     = file_input
        original_name = os.path.basename(file_input)  # 경로에서 파일명만 추출
    else:                                              # Streamlit 업로드 객체인 경우
        temp_path, original_name = save_uploaded_file(file_input)  # 임시 파일로 저장
        file_path = temp_path

    try:
        ext = os.path.splitext(file_path)[1].lower()  # 확장자 추출 후 소문자로 통일
        if ext == ".pdf":
            docs = load_pdf(file_path, original_name)
        elif ext == ".docx":
            docs = load_docx(file_path, original_name)
        elif ext == ".xlsx":
            docs = load_xlsx(file_path, original_name)
        elif ext in [".pptx", ".ppt"]:
            docs = load_pptx(file_path, original_name)
        else:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")

        if not docs:
            raise ValueError("문서에서 텍스트를 추출할 수 없습니다.")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # 단락 → 줄바꿈 → 문장 마침 순으로 자연스러운 경계에서 분할
            separators=["\n\n", "\n", ". ", "다. ", "요. ", "! ", "? ", " ", ""]
        )
        split_docs = splitter.split_documents(docs)   # 분할 실행

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)                  # 임시 파일 삭제
            except (PermissionError, OSError):
                pass                                  # Windows에서 pymupdf4llm이 파일을 열어둔 경우 조용히 무시

    return split_docs


def get_doc_info(split_docs) -> dict:
    if not split_docs:
        return {"총 조각 수": 0, "총 페이지 수": 0, "출처 파일": "없음", "첫 번째 조각": ""}

    pages = [doc.metadata.get("page", 0) for doc in split_docs]  # 모든 청크의 페이지 번호 수집
    return {
        "총 조각 수":   len(split_docs),
        "총 페이지 수": max(pages) + 1,                           # 0-index이므로 +1
        "출처 파일":    split_docs[0].metadata.get("source", "알 수 없음"),
        "첫 번째 조각": split_docs[0].page_content[:100],         # 미리보기용 100자
    }
