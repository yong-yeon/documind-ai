import os   # 모듈 경로 처리용
import sys  # 모듈 경로 추가용

try:
    from config import EMBEDDING_MODEL, DEFAULT_SEARCH_TYPE, DEFAULT_K, DEFAULT_FETCH_K  # 일반 실행 시 import
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))          # 루트 경로 추가
    from config import EMBEDDING_MODEL, DEFAULT_SEARCH_TYPE, DEFAULT_K, DEFAULT_FETCH_K  # 직접 실행 시 import

import streamlit as st
from langchain_community.embeddings import HuggingFaceEmbeddings  # HuggingFace 임베딩 모델 래퍼
from langchain_community.vectorstores import FAISS                 # 벡터 유사도 검색 저장소
from langchain_community.retrievers import BM25Retriever           # 키워드 기반 BM25 검색기
from langchain.retrievers import EnsembleRetriever                 # 여러 검색기를 가중치로 결합


@st.cache_resource(show_spinner=False)  # 앱 전체에서 한 번만 로드, 이후 재사용 (파일 업로드마다 재로드 방지)
def create_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"batch_size": 64, "normalize_embeddings": True},  # 배치 크기 64: CPU 처리량 극대화
    )


def create_vectorstore(split_docs, embeddings=None):
    if embeddings is None:                           # 임베딩 객체가 없으면 기본 모델로 생성
        embeddings = create_embeddings()
    if not split_docs:
        raise ValueError("문서 조각이 비어있습니다.")
    return FAISS.from_documents(split_docs, embeddings)  # 청크를 임베딩해 FAISS 인덱스 생성


def get_retriever(
    vectorstore,
    split_docs,
    search_type: str = DEFAULT_SEARCH_TYPE,
    k: int = DEFAULT_K,
    fetch_k: int = DEFAULT_FETCH_K
):
    # FAISS: 벡터 유사도 기반 의미 검색
    if search_type == "mmr":
        faiss_retriever = vectorstore.as_retriever(
            search_type="mmr",                                  # MMR: 유사하면서도 다양한 결과 선별
            search_kwargs={"k": k, "fetch_k": fetch_k}         # fetch_k개 후보 중 k개 최종 선택
        )
    else:
        faiss_retriever = vectorstore.as_retriever(
            search_type="similarity",                           # 유사도 높은 순으로 k개 반환
            search_kwargs={"k": k}
        )

    # BM25: TF-IDF 계열 키워드 기반 검색 (정확한 단어 매칭에 강함)
    bm25_retriever   = BM25Retriever.from_documents(split_docs)
    bm25_retriever.k = k  # 반환할 결과 수 설정

    # FAISS 60% + BM25 40% 가중치로 결합 (의미 검색 + 키워드 검색 동시 활용)
    return EnsembleRetriever(
        retrievers=[faiss_retriever, bm25_retriever],
        weights=[0.6, 0.4]
    )
