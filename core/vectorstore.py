import os

try:
    from config import EMBEDDING_MODEL, DEFAULT_SEARCH_TYPE, DEFAULT_K, DEFAULT_FETCH_K
except ModuleNotFoundError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import EMBEDDING_MODEL, DEFAULT_SEARCH_TYPE, DEFAULT_K, DEFAULT_FETCH_K

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever


def create_embeddings():
    """
    임베딩 모델 생성 함수

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
    if embeddings is None:
        embeddings = create_embeddings()

    if not split_docs:
        raise ValueError("문서 조각이 비어있어요! loader.py 결과를 확인해주세요.")

    vectorstore = FAISS.from_documents(split_docs, embeddings)
    return vectorstore


def get_retriever(vectorstore, split_docs, search_type: str = DEFAULT_SEARCH_TYPE, k: int = DEFAULT_K, fetch_k: int = DEFAULT_FETCH_K):
    """
    FAISS + BM25 Ensemble 검색기 생성 함수

    Args:
        vectorstore : FAISS 벡터 저장소
        split_docs  : BM25 검색기 생성에 필요한 문서 조각 리스트
        search_type : 검색 방식 ("similarity" 또는 "mmr")
        k           : 반환할 조각 수
        fetch_k     : MMR 후보 조각 수

    Returns:
        ensemble_retriever : FAISS + BM25 Ensemble 검색기
    """
    # 1. FAISS 검색기 (의미 기반)
    if search_type == "mmr":
        faiss_retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": fetch_k}
        )
    else:
        faiss_retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )

    # 2. BM25 검색기 (키워드 기반)
    bm25_retriever = BM25Retriever.from_documents(split_docs)
    bm25_retriever.k = k

    # 3. Ensemble (FAISS 60% + BM25 40%)
    ensemble_retriever = EnsembleRetriever(
        retrievers=[faiss_retriever, bm25_retriever],
        weights=[0.6, 0.4]
    )

    return ensemble_retriever


def search_similar(vectorstore, query: str, search_type: str = DEFAULT_SEARCH_TYPE, k: int = DEFAULT_K):
    """
    질문과 유사한 조각을 직접 검색하는 함수 (테스트용)
    """
    if search_type == "mmr":
        results = vectorstore.max_marginal_relevance_search(query, k=k)
    else:
        results = vectorstore.similarity_search(query, k=k)
    return results