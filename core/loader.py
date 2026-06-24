import os
import sys
import tempfile
import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# config.py import (루트에서 실행 or core 폴더에서 직접 실행 둘 다 대응)
try:
    from config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP


def save_uploaded_file(uploaded_file) -> tuple:
    """
    웹 업로드 파일 → 임시 파일로 저장
    원본 파일명도 함께 반환 (출처 표시용)
    """
    suffix = os.path.splitext(uploaded_file.name)[1]  # 확장자 추출 (.pdf 등)
    original_name = uploaded_file.name  # 원본 파일명 저장

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        temp_path = tmp.name  # 임시 파일 경로

    return temp_path, original_name


def load_pdf(file_input, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
    """
    PDF 읽기 + 텍스트 분할 함수
    fitz(PyMuPDF) 로 마크다운 형식 추출
    → 표/제목/본문 구조 유지

    Args:
        file_input   : 파일 경로(str) 또는 웹 업로드 파일 객체
        chunk_size   : 조각 크기 (기본 800)
        chunk_overlap: 조각 겹침 (기본 150)

    Returns:
        split_docs : 분할된 텍스트 조각 리스트
    """
    temp_path = None
    original_name = None

    # 1. 로컬 경로 vs 웹 업로드 판별
    if isinstance(file_input, str):
        # 로컬 파일 경로로 들어온 경우
        if not os.path.exists(file_input):
            raise FileNotFoundError(f"파일을 찾을 수 없어요 : {file_input}")
        file_path = file_input
        original_name = os.path.basename(file_input)
    else:
        # 웹 업로드 파일 객체로 들어온 경우
        temp_path, original_name = save_uploaded_file(file_input)
        file_path = temp_path

    try:
        # 2. fitz 로 마크다운 추출 (표/제목 구조 유지)
        doc = fitz.open(file_path)
        docs = []

        for page_num, page in enumerate(doc):
            # "markdown" 모드 : 표/제목/본문 마크다운 형식으로 추출
            text = page.get_text("text")

            if text.strip():  # 빈 페이지 제외
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": original_name,  # 원본 파일명 (출처 표시용)
                        "page": page_num           # 페이지 번호
                    }
                ))

        doc.close()

        # 3. 텍스트 분할
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        split_docs = splitter.split_documents(docs)

    finally:
        # 4. 임시 파일 삭제 (웹 업로드 경우만)
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    return split_docs


def get_doc_info(split_docs) -> dict:
    """
    문서 정보 반환 함수
    테스트 및 화면 표시용
    """
    if not split_docs:
        return {
            "총 조각 수": 0,
            "총 페이지 수": 0,
            "출처 파일": "없음",
            "첫 번째 조각": ""
        }

    # 페이지 번호 중 최댓값 + 1 = 총 페이지 수
    pages = [doc.metadata.get("page", 0) for doc in split_docs]
    total_pages = max(pages) + 1

    return {
        "총 조각 수": len(split_docs),
        "총 페이지 수": total_pages,
        "출처 파일": split_docs[0].metadata.get("source", "알 수 없음"),
        "첫 번째 조각": split_docs[0].page_content[:100]
    }


# ─────────────────────────────────────────
# 테스트 코드 (직접 실행할 때만 동작)
# ─────────────────────────────────────────
def print_loader_test(file_path: str):
    """loader.py 테스트 함수"""
    print("=" * 40)
    print("  loader.py 테스트 (fitz 마크다운 모드)")
    print("=" * 40)

    split_docs = load_pdf(file_path)
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