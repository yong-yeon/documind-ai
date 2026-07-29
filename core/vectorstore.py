import os   # 파일 경로 처리 및 모듈 경로 확인용
import sys  # 다른 폴더의 모듈을 import 할 때 경로 추가용

try:
    from config import EMBEDDING_MODEL, DEFAULT_SEARCH_TYPE, DEFAULT_K, DEFAULT_FETCH_K  # 앱 정상 실행 시 루트에서 import
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))          # 직접 실행 시 루트 경로 추가
    from config import EMBEDDING_MODEL, DEFAULT_SEARCH_TYPE, DEFAULT_K, DEFAULT_FETCH_K  # 경로 추가 후 재시도

import streamlit as st                                                                    # 캐싱 데코레이터 사용용
from langchain_community.embeddings import HuggingFaceEmbeddings  # HuggingFace 의 텍스트 → 벡터 변환 모델 래퍼
from langchain_community.vectorstores import FAISS                 # 벡터를 저장하고 유사도로 검색하는 저장소
from langchain_community.retrievers import BM25Retriever           # 키워드 빈도 기반 BM25 검색기
from langchain.retrievers import EnsembleRetriever                 # 여러 검색기를 가중치로 합치는 앙상블 검색기


@st.cache_resource(show_spinner=False)  # 첫 실행 시 모델 로드 후 캐싱 → 이후 재사용 (매번 로드 방지)
def create_embeddings():
    # HuggingFace 임베딩 모델 생성
    # paraphrase-multilingual-MiniLM-L12-v2 = 다국어(한국어 포함) 지원 경량 모델
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,                                        # config.py 에서 지정한 모델명
        encode_kwargs={
            "batch_size": 64,              # 청크를 64개씩 묶어서 한 번에 처리 → 기본값(32) 대비 속도 향상
            "normalize_embeddings": True,  # 벡터 크기를 1로 정규화 → 유사도 계산 정확도 향상
        },
    )


def create_vectorstore(split_docs, embeddings=None):
    # 청크 리스트를 받아서 벡터로 변환하고 FAISS 저장소에 저장
    if embeddings is None:                                # 임베딩 객체가 전달되지 않으면 기본 모델로 생성
        embeddings = create_embeddings()
    if not split_docs:
        raise ValueError("문서 조각이 비어있습니다.")      # 빈 리스트면 오류 발생 (업스트림에서 처리 실패)
    return FAISS.from_documents(split_docs, embeddings)   # 청크 임베딩 후 FAISS 인덱스 생성 및 반환


def get_retriever(
    vectorstore,
    split_docs,
    search_type: str = DEFAULT_SEARCH_TYPE,  # 검색 방식: "mmr" 또는 "similarity"
    k: int = DEFAULT_K,                      # 최종 반환할 청크 개수 (기본 5)
    fetch_k: int = DEFAULT_FETCH_K           # MMR 후보군 크기 (기본 30, 이 중 k개 선별)
):
    # FAISS 검색기 생성 (벡터 유사도 기반 의미 검색)
    if search_type == "mmr":
        faiss_retriever = vectorstore.as_retriever(
            search_type="mmr",                              # MMR: fetch_k 개 후보 중 다양성 고려해 k개 선별
            search_kwargs={"k": k, "fetch_k": fetch_k}     # k=5, fetch_k=30 → 30개 후보에서 다양한 5개 선택
        )
    else:
        faiss_retriever = vectorstore.as_retriever(
            search_type="similarity",                       # Similarity: 유사도 높은 순으로 k개 반환 (단순)
            search_kwargs={"k": k}
        )

    # BM25 검색기 생성 (키워드 빈도 기반 검색)
    # FAISS 와 달리 원본 텍스트 직접 참조 → split_docs 필요
    bm25_retriever   = BM25Retriever.from_documents(split_docs)  # 원본 청크로 BM25 인덱스 생성
    bm25_retriever.k = k                                          # BM25 도 k개 반환하도록 설정

    # FAISS 60% + BM25 40% 앙상블 검색기 반환
    # FAISS: 의미 유사도 검색 (유사 표현도 찾음)
    # BM25: 정확한 키워드 매칭 (숫자, 고유명사에 강함)
    return EnsembleRetriever(
        retrievers=[faiss_retriever, bm25_retriever],
        weights=[0.6, 0.4]                                        # FAISS 60% + BM25 40% 가중치 결합
    )