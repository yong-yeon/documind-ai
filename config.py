import os                      # 환경 변수 접근
import streamlit as st         # Streamlit Cloud secrets 접근
from dotenv import load_dotenv # .env 파일 로드

load_dotenv()  # 프로젝트 루트의 .env 파일을 환경 변수로 불러옴


def get_groq_api_key():
    # 로컬(.env) 우선, 없으면 Streamlit Cloud secrets에서 가져옴
    api_key = os.getenv("GROQ_API_KEY")  # .env 파일에서 API 키 읽기
    if api_key is None:                  # 로컬에 없으면 Streamlit Cloud secrets 확인
        try:
            api_key = st.secrets.get("GROQ_API_KEY", None)  # 배포 환경에서 secrets 접근
        except Exception:
            pass  # secrets 접근 실패 시 None 반환
    return api_key


LLM_MODEL       = "llama-3.3-70b-versatile"                              # 답변 생성에 사용할 Groq LLM 모델
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # 텍스트 임베딩 모델 (한국어 지원)

DEFAULT_CHUNK_SIZE    = 700  # 청크 크기를 줄여 청크당 내용을 세분화, 검색 정확도 향상 (청크 수는 증가, 1000→700)
DEFAULT_CHUNK_OVERLAP = 150   # 청크 간 겹치는 글자 수 (문맥 연결용)

DEFAULT_SEARCH_TYPE = "mmr"   # 기본 검색 방식: MMR (중복 줄이고 다양한 결과 반환)
DEFAULT_K           = 5       # 답변 생성 시 참고할 청크 개수 (7→5)
DEFAULT_FETCH_K     = 30      # MMR 후보군 크기 (이 중에서 k개를 선별, 20→30)

SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".pptx"]  # 업로드 허용 파일 형식


if __name__ == "__main__":
    key = get_groq_api_key()
    print("API 키 로드 성공" if key else "API 키 없음")
    print(f"LLM: {LLM_MODEL} / 임베딩: {EMBEDDING_MODEL}")
