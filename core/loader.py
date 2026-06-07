import os
import tempfile
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# config import (streamlit run app.py 로 실행하면 정상 동작)
try:
    from config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
except ModuleNotFoundError:
    # core 폴더에서 직접 테스트 실행할 때를 위한 처리
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP


def save_uploaded_file(uploaded_file) -> str:
    """
    웹에서 업로드된 파일을 임시 파일로 저장하고 경로를 반환

    Args:
        uploaded_file : Streamlit st.file_uploader 로 받은 파일 객체

    Returns:
        temp_path : 임시 저장된 파일 경로
    """
    # 원본 파일 확장자 유지
    suffix = os.path.splitext(uploaded_file.name)[1]

    # 임시 파일 생성 (delete=False : 닫아도 파일 유지)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        temp_path = tmp.name

    return temp_path


def load_pdf(file_input, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
    """
    PDF 파일을 읽어서 텍스트 조각으로 분할하는 함수

    Args:
        file_input   : 파일 경로(str) 또는 업로드 파일 객체 둘 다 가능
        chunk_size   : 조각 크기 (기본값 500)
        chunk_overlap: 조각 겹침 (기본값 50)

    Returns:
        split_docs : 분할된 텍스트 조각 리스트
    """
    temp_path = None

    # 1. 입력 타입 판별
    if isinstance(file_input, str):
        # 문자열 경로로 들어온 경우 (로컬 테스트)
        if not os.path.exists(file_input):
            raise FileNotFoundError(f"파일을 찾을 수 없어요 : {file_input}")
        file_path = file_input
    else:
        # 웹 업로드 파일 객체로 들어온 경우
        temp_path = save_uploaded_file(file_input)
        file_path = temp_path

    try:
        # 2. PDF 읽기
        loader = PyMuPDFLoader(file_path)
        docs = loader.load()

        # 3. 텍스트 분할
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        split_docs = splitter.split_documents(docs)

    finally:
        # 4. 임시 파일 사용했으면 삭제
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    return split_docs


def get_doc_info(split_docs) -> dict:
    """
    문서 정보를 반환하는 함수

    Args:
        split_docs : 분할된 텍스트 조각 리스트

    Returns:
        info : 문서 정보 딕셔너리
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
        "출처 파일": os.path.basename(split_docs[0].metadata.get("source", "알 수 없음")),
        "첫 번째 조각": split_docs[0].page_content[:100]
    }


# ─────────────────────────────────────────
# 테스트 코드
# ─────────────────────────────────────────
def print_loader_test(file_path: str):
    """loader.py 테스트 함수"""
    print("=" * 40)
    print("  loader.py 테스트")
    print("=" * 40)

    split_docs = load_pdf(file_path)
    info = get_doc_info(split_docs)

    print(f"총 조각 수   : {info['총 조각 수']}")
    print(f"총 페이지 수 : {info['총 페이지 수']}")
    print(f"출처 파일    : {info['출처 파일']}")
    print(f"첫 번째 조각 미리보기 :")
    print(f"   {info['첫 번째 조각']}...")
    print("=" * 40)
    print("loader.py 테스트 완료!")
    print("=" * 40)


if __name__ == "__main__":
    test_file = r"D:\LLMchatbot\workspace\data\2025년서울교통이용통계보고서.pdf"
    print_loader_test(test_file)