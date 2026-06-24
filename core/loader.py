import os
import sys
import tempfile
import fitz
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP


def save_uploaded_file(uploaded_file) -> tuple:
    """
    웹 업로드 파일 → 임시 파일로 저장
    원본 파일명도 함께 반환
    """
    suffix = os.path.splitext(uploaded_file.name)[1]
    original_name = uploaded_file.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        temp_path = tmp.name

    return temp_path, original_name


def load_pdf(file_path: str, original_name: str) -> list:
    """
    PDF 파일 읽기
    fitz 로 텍스트 추출
    """
    doc = fitz.open(file_path)
    docs = []

    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            docs.append(Document(
                page_content=text,
                metadata={"source": original_name, "page": page_num}
            ))

    doc.close()
    return docs


def load_docx(file_path: str, original_name: str) -> list:
    """
    DOCX (워드) 파일 읽기
    python-docx 로 텍스트 추출
    """
    from docx import Document as DocxDocument

    docx = DocxDocument(file_path)
    docs = []

    # 단락 추출
    full_text = []
    for para in docx.paragraphs:
        if para.text.strip():
            full_text.append(para.text)

    # 표 추출
    for table in docx.tables:
        for row in table.rows:
            row_text = " | ".join(
                cell.text.strip() for cell in row.cells if cell.text.strip()
            )
            if row_text:
                full_text.append(row_text)

    if full_text:
        docs.append(Document(
            page_content="\n".join(full_text),
            metadata={"source": original_name, "page": 0}
        ))

    return docs


def load_xlsx(file_path: str, original_name: str) -> list:
    """
    XLSX (엑셀) 파일 읽기
    openpyxl 로 시트별 텍스트 추출
    """
    import openpyxl

    wb = openpyxl.load_workbook(file_path, data_only=True)
    docs = []

    for sheet_num, sheet_name in enumerate(wb.sheetnames):
        ws = wb[sheet_name]
        rows_text = []

        for row in ws.iter_rows(values_only=True):
            # None 제거 + 문자열 변환
            row_data = [str(cell) for cell in row if cell is not None]
            if row_data:
                rows_text.append(" | ".join(row_data))

        if rows_text:
            docs.append(Document(
                page_content=f"[시트: {sheet_name}]\n" + "\n".join(rows_text),
                metadata={"source": original_name, "page": sheet_num}
            ))

    return docs


def load_pptx(file_path: str, original_name: str) -> list:
    """
    PPTX (파워포인트) 파일 읽기
    python-pptx 로 슬라이드별 텍스트 추출
    """
    from pptx import Presentation

    prs = Presentation(file_path)
    docs = []

    for slide_num, slide in enumerate(prs.slides):
        slide_text = []

        for shape in slide.shapes:
            # 텍스트 박스
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if text:
                        slide_text.append(text)

            # 표
            if shape.has_table:
                for row in shape.table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        slide_text.append(row_text)

        if slide_text:
            docs.append(Document(
                page_content=f"[슬라이드 {slide_num + 1}]\n" + "\n".join(slide_text),
                metadata={"source": original_name, "page": slide_num}
            ))

    return docs


def load_file(file_input, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
    """
    파일 읽기 + 텍스트 분할 메인 함수
    파일 확장자에 따라 자동으로 로더 선택

    Args:
        file_input   : 파일 경로(str) 또는 웹 업로드 파일 객체
        chunk_size   : 조각 크기
        chunk_overlap: 조각 겹침

    Returns:
        split_docs : 분할된 텍스트 조각 리스트
    """
    temp_path = None
    original_name = None

    # 1. 로컬 경로 vs 웹 업로드 판별
    if isinstance(file_input, str):
        if not os.path.exists(file_input):
            raise FileNotFoundError(f"파일을 찾을 수 없어요 : {file_input}")
        file_path = file_input
        original_name = os.path.basename(file_input)
    else:
        temp_path, original_name = save_uploaded_file(file_input)
        file_path = temp_path

    try:
        # 2. 확장자별 로더 선택
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            docs = load_pdf(file_path, original_name)
        elif ext == ".docx":
            docs = load_docx(file_path, original_name)
        elif ext == ".xlsx":
            docs = load_xlsx(file_path, original_name)
        elif ext in [".pptx", ".ppt"]:
            docs = load_pptx(file_path, original_name)
        else:
            raise ValueError(f"지원하지 않는 파일 형식이에요 : {ext}")

        if not docs:
            raise ValueError("문서에서 텍스트를 추출할 수 없어요!")

        # 3. 텍스트 분할
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        split_docs = splitter.split_documents(docs)

    finally:
        # 4. 임시 파일 삭제
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    return split_docs


def get_doc_info(split_docs) -> dict:
    """
    문서 정보 반환 함수
    """
    if not split_docs:
        return {
            "총 조각 수": 0,
            "총 페이지 수": 0,
            "출처 파일": "없음",
            "첫 번째 조각": ""
        }

    pages = [doc.metadata.get("page", 0) for doc in split_docs]
    total_pages = max(pages) + 1

    return {
        "총 조각 수": len(split_docs),
        "총 페이지 수": total_pages,
        "출처 파일": split_docs[0].metadata.get("source", "알 수 없음"),
        "첫 번째 조각": split_docs[0].page_content[:100]
    }


# ─────────────────────────────────────────
# 테스트 코드
# ─────────────────────────────────────────
def print_loader_test(file_path: str):
    """loader.py 테스트 함수"""
    print("=" * 40)
    print("  loader.py 테스트 (다중 파일 지원)")
    print("=" * 40)

    split_docs = load_file(file_path)
    info = get_doc_info(split_docs)

    print(f"✅ 총 조각 수   : {info['총 조각 수']}")
    print(f"✅ 총 페이지 수 : {info['총 페이지 수']}")
    print(f"✅ 출처 파일    : {info['출처 파일']}")
    print(f"✅ 첫 번째 조각 미리보기 :")
    print(f"   {info['첫 번째 조각']}...")
    print("=" * 40)
    print("✅ loader.py 테스트 완료!")
    print("=" * 40)


if __name__ == "__main__":
    test_file = r"D:\LLMchatbot\workspace\data\2025년서울교통이용통계보고서.pdf"
    print_loader_test(test_file)