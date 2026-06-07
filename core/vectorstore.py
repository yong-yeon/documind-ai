import os

try:
    from config import EMBEDDING_MODEL, DEFAULT_SEARCH_TYPE, DEFAULT_K, DEFAULT_FETCH_K
except ModuleNotFoundError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import EMBEDDING_MODEL, DEFAULT_SEARCH_TYPE, DEFAULT_K, DEFAULT_FETCH_K

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


def create_embeddings():
    """
    임베딩 모델 생성 함수
    텍스트를 숫자 벡터로 변환하는 도구

    Returns:
        embeddings : HuggingFace 임베딩 모델 객체
    """
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )
    return embeddings


def create_vectorstore(split_docs, embeddings=None):
    """
    벡터 저장소를 생성하는 함수

    Args:
        split_docs : loader.py에서 받은 텍스트 조각 리스트
        embeddings : 임베딩 모델 (없으면 자동 생성)

    Returns:
        vectorstore : FAISS 벡터 저장소 객체
    """
    # 임베딩 모델이 없으면 새로 생성
    if embeddings is None:
        embeddings = create_embeddings()

    # 조각이 비어있으면 에러
    if not split_docs:
        raise ValueError("문서 조각이 비어있어요! loader.py 결과를 확인해주세요.")

    # FAISS 벡터 저장소 생성
    vectorstore = FAISS.from_documents(split_docs, embeddings)

    return vectorstore


def get_retriever(vectorstore, search_type: str = DEFAULT_SEARCH_TYPE, k: int = DEFAULT_K, fetch_k: int = DEFAULT_FETCH_K):
    """
    벡터 저장소에서 검색기(retriever)를 만드는 함수

    Args:
        vectorstore : FAISS 벡터 저장소
        search_type : 검색 방식 ("similarity" 또는 "mmr")
        k           : 반환할 조각 수 (기본값 5)
        fetch_k     : MMR 후보 조각 수 (기본값 20)

    Returns:
        retriever : 검색기 객체
    """
    if search_type == "mmr":
        retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": fetch_k}
        )
    else:
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )

    return retriever


def search_similar(vectorstore, query: str, search_type: str = DEFAULT_SEARCH_TYPE, k: int = DEFAULT_K):
    """
    질문과 유사한 조각을 직접 검색하는 함수 (테스트용)

    Args:
        vectorstore : FAISS 벡터 저장소
        query       : 검색할 질문
        search_type : 검색 방식 ("similarity" 또는 "mmr")
        k           : 반환할 조각 수

    Returns:
        results : 유사한 조각 리스트
    """
    if search_type == "mmr":
        results = vectorstore.max_marginal_relevance_search(query, k=k)
    else:
        results = vectorstore.similarity_search(query, k=k)

    return results


# ─────────────────────────────────────────
# 테스트 코드
# ─────────────────────────────────────────
def print_vectorstore_test(split_docs):
    """vectorstore.py 테스트 함수"""
    print("=" * 40)
    print("  vectorstore.py 테스트")
    print("=" * 40)

    # 1. 임베딩 모델 생성
    print("임베딩 모델 로딩 중...")
    embeddings = create_embeddings()
    print("임베딩 모델 로딩 완료")

    # 2. 벡터 저장소 생성
    print("벡터 저장소 생성 중...")
    vectorstore = create_vectorstore(split_docs, embeddings)
    print("벡터 저장소 생성 완료")

    # 3. 검색 테스트 (similarity)
    query = "서울 지하철 이용객 수"
    print(f"\n--- Similarity 검색 : '{query}' ---")
    results = search_similar(vectorstore, query, search_type="similarity", k=3)
    for i, doc in enumerate(results):
        page = doc.metadata.get("page", "?")
        print(f"  [{i+1}] 페이지 {page} : {doc.page_content[:80]}...")

    # 4. 검색 테스트 (mmr)
    print(f"\n--- MMR 검색 : '{query}' ---")
    results = search_similar(vectorstore, query, search_type="mmr", k=3)
    for i, doc in enumerate(results):
        page = doc.metadata.get("page", "?")
        print(f"  [{i+1}] 페이지 {page} : {doc.page_content[:80]}...")

    print("=" * 40)
    print("vectorstore.py 테스트 완료!")
    print("=" * 40)


if __name__ == "__main__":
    from core.loader import load_pdf

    test_file = r"D:\LLMchatbot\workspace\data\2025년서울교통이용통계보고서.pdf"

    print("PDF 로딩 중...")
    split_docs = load_pdf(test_file)
    print(f"PDF 로딩 완료 (조각 수 : {len(split_docs)})")

    print_vectorstore_test(split_docs)