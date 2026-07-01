import os             # 파일 경로 처리
import sys            # 모듈 경로 추가용
import streamlit as st  # LLM 캐싱용

try:
    from config import get_groq_api_key, LLM_MODEL          # 일반 실행 시 import
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 루트 경로 추가
    from config import get_groq_api_key, LLM_MODEL          # 직접 실행 시 import

from langchain_groq import ChatGroq                         # Groq LLM 래퍼
from langchain_core.prompts import PromptTemplate           # 프롬프트 템플릿
from langchain_core.output_parsers import StrOutputParser   # LLM 출력을 문자열로 변환
from langchain_core.runnables import RunnablePassthrough    # 입력값을 그대로 다음 단계로 전달


@st.cache_resource(show_spinner=False)  # 앱 실행 중 한 번만 생성, 이후 재사용
def create_llm():
    api_key = get_groq_api_key()                            # 환경 변수에서 API 키 가져옴
    if not api_key:
        raise ValueError("API 키를 찾을 수 없습니다. .env 파일을 확인해주세요.")
    return ChatGroq(api_key=api_key, model_name=LLM_MODEL, temperature=0.1)  # temperature 낮게 설정해 일관된 답변 생성


def create_prompt(mode: str = "hybrid"):
    # hybrid: 문서 우선, 관련 내용 없으면 AI 자체 지식으로 보완
    # document: 문서 내용만 사용, 외부 지식 완전 차단
    if mode == "document":
        template = """
당신은 문서 분석 전문가 AI입니다.

[역할]
사용자가 제공한 문서(Context)만을 기반으로 질문에 정확하게 답변합니다.

[규칙]
1. 문서의 언어와 상관없이 사용자 질문의 언어로 답변하세요.
2. 반드시 제공된 문서(Context) 내용만 사용하세요.
3. 외부 지식이나 추측은 절대 사용하지 마세요.
4. 문서에서 근거를 찾을 수 없으면 "문서에서 찾을 수 없습니다." 라고만 하세요.
5. 답변은 간결하고 명확하게 작성하세요.
6. 동일한 내용을 반복하지 마세요.
7. 답변은 Markdown 형식으로 작성하세요.
8. 문서에 표가 포함되어 있으면 가능한 한 표 형태를 유지하세요.
9. 여러 페이지의 내용을 참고했다면 모든 페이지를 표시하세요.
10. 페이지 번호는 추측하지 말고 Context에 포함된 정보만 사용하세요.
11. 페이지 번호는 숫자 + "페이지" 형식으로 표시하세요. (예: 13페이지)
12. 답변은 문단 단위로 줄바꿈해서 가독성 있게 작성하세요.
13. 목록은 반드시 줄바꿈해서 한 줄에 하나씩 표시하세요.
14. 숫자 데이터는 항목별로 줄바꿈해서 표시하세요.

[이전 대화]
{chat_history}

[문서 내용]
{context}

[사용자 질문]
{question}

[답변 형식]
답변
(질문에 대한 답변)

참고 페이지 (문서 참고 시에만 표시)
3페이지 또는 3페이지, 5페이지
"""
    else:
        template = """
당신은 문서 분석 전문가 AI입니다.

[역할]
사용자가 제공한 문서(Context)를 기반으로 질문에 정확하게 답변합니다.
문서와 관련 없는 일반 질문은 AI 자체 지식으로 답변합니다.

[규칙]
1. 문서의 언어와 상관없이 사용자 질문의 언어로 답변하세요.
2. 문서(Context)에 관련 내용이 있으면 문서를 우선 참고하세요.
3. 문서에 관련 내용이 없으면 AI 자체 지식으로 자유롭게 답변하세요.
4. 외부 지식 사용 시 "문서에는 없지만," 이라고 먼저 밝히세요.
5. 답변은 간결하고 명확하게 작성하세요.
6. 동일한 내용을 반복하지 마세요.
7. 답변은 Markdown 형식으로 작성하세요.
8. 문서에 표가 포함되어 있으면 가능한 한 표 형태를 유지하세요.
9. 여러 페이지의 내용을 참고했다면 모든 페이지를 표시하세요.
10. 페이지 번호는 추측하지 말고 Context에 포함된 정보만 사용하세요.
11. 페이지 번호는 숫자 + "페이지" 형식으로 표시하세요. (예: 13페이지)
12. 답변은 문단 단위로 줄바꿈해서 가독성 있게 작성하세요.
13. 목록은 반드시 줄바꿈해서 한 줄에 하나씩 표시하세요.
14. 숫자 데이터는 항목별로 줄바꿈해서 표시하세요.

[이전 대화]
{chat_history}

[문서 내용]
{context}

[사용자 질문]
{question}

[답변 형식]
답변
(질문에 대한 답변)

참고 페이지 (문서 참고 시에만 표시)
3페이지 또는 3페이지, 5페이지
"""
    return PromptTemplate.from_template(template)  # 문자열 템플릿을 LangChain 프롬프트 객체로 변환


def format_docs(docs) -> str:
    result = []
    for doc in docs:
        source     = os.path.basename(doc.metadata.get("source", "알 수 없음"))  # 파일명만 추출
        page_label = doc.metadata.get("page_label", "?")               # 실제 인쇄 페이지 번호 레이블
        result.append(f"[출처 : {source} / {page_label}페이지]\n{doc.page_content}")  # 출처 헤더 + 본문
    return "\n\n".join(result)  # 청크 간 빈 줄로 구분해 하나의 문자열로 합침


def create_chain(retriever, chat_history: str = "", mode: str = "hybrid"):
    prompt = create_prompt(mode)  # 모드에 맞는 프롬프트 템플릿 생성
    llm    = create_llm()         # Groq LLM 인스턴스 생성

    chain = (
        {
            "context":      retriever | format_docs,    # 질문으로 검색 후 문자열로 포맷
            "question":     RunnablePassthrough(),       # 질문 그대로 전달
            "chat_history": lambda _: chat_history,     # 이전 대화 기록 고정 주입
        }
        | prompt           # 딕셔너리를 프롬프트 템플릿에 채움
        | llm              # 완성된 프롬프트를 LLM에 전달
        | StrOutputParser()  # LLM 응답 객체를 순수 문자열로 변환
    )
    return chain


def get_sources(retriever, query: str) -> list:
    docs = retriever.invoke(query)  # 질문과 유사한 청크 검색
    sources = []
    seen = set()  # 동일 페이지 중복 출처 카드 방지
    for doc in docs:
        source     = os.path.basename(doc.metadata.get("source", "알 수 없음"))
        page_label = doc.metadata.get("page_label", "?")  # 실제 인쇄 페이지 번호 레이블
        key = (source, page_label)
        if key in seen:
            continue  # 같은 파일·같은 페이지 중복 제거
        seen.add(key)
        sources.append({
            "파일명":        source,
            "페이지":        page_label,
            "내용 미리보기": doc.page_content[:100],  # 출처 카드에 표시할 미리보기 (100자)
        })
    return sources
