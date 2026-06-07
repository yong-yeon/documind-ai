import os
import streamlit as st
from dotenv import load_dotenv

# .env 파일 읽기
load_dotenv()


def get_groq_api_key():
    """
    API 키를 가져오는 함수
    - 배포 환경 (Streamlit Cloud) : st.secrets 에서 가져옴
    - 로컬 환경                   : .env 파일에서 가져옴
    """
    # 로컬 환경 먼저 확인 (.env 파일)
    api_key = os.getenv("GROQ_API_KEY")

    # 로컬에 없으면 Streamlit Cloud secrets 확인
    if api_key is None:
        try:
            api_key = st.secrets.get("GROQ_API_KEY", None)
        except Exception:
            pass

    return api_key


# 모델 설정
# ─────────────────────────────────────────
LLM_MODEL = "llama-3.3-70b-versatile"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# 텍스트 분할 기본값
# ─────────────────────────────────────────
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50


# 검색 기본값
# ─────────────────────────────────────────
DEFAULT_SEARCH_TYPE = "mmr"
DEFAULT_K = 5
DEFAULT_FETCH_K = 20


# 지원 파일 형식
# ─────────────────────────────────────────
SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".pptx"]



# 설정 확인 함수 (테스트용)
# ─────────────────────────────────────────
def print_config():
    """현재 설정값 출력 함수"""
    print("  DocuMind AI - 설정 확인")
    print("=" * 40)

    # get_groq_api_key() 로 통일
    api_key = get_groq_api_key()
    if api_key:
        print("GROQ API 키 로드 성공")
    else:
        print("GROQ API 키를 찾을 수 없습니다.")

    print(f"LLM 모델        : {LLM_MODEL}")
    print(f"임베딩 모델     : {EMBEDDING_MODEL}")
    print(f"기본 청크 크기  : {DEFAULT_CHUNK_SIZE}")
    print(f"기본 청크 겹침  : {DEFAULT_CHUNK_OVERLAP}")
    print(f"기본 검색 방식  : {DEFAULT_SEARCH_TYPE}")
    print(f"지원 파일 형식  : {SUPPORTED_EXTENSIONS}")
    print("=" * 40)
    print("config.py 설정 완료")



if __name__ == "__main__":
    print_config()