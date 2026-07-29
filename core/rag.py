import os
import sys
import re
import streamlit as st

try:
    from config import get_groq_api_key, LLM_MODEL
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import get_groq_api_key, LLM_MODEL

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda


@st.cache_resource(show_spinner=False)
def create_llm():
    api_key = get_groq_api_key()
    if not api_key:
        raise ValueError("API 키를 찾을 수 없습니다. .env 파일을 확인해주세요.")
    return ChatGroq(api_key=api_key, model_name=LLM_MODEL, temperature=0.1)


def create_prompt(mode: str = "hybrid"):
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
**답변:** (질문에 대한 답변)

(문서를 참고한 경우에만 아래 줄 추가, 참고하지 않은 경우 생략)
**참고 페이지:** 3페이지 또는 3페이지, 5페이지
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
**답변:** (질문에 대한 답변)

(문서를 참고한 경우에만 아래 줄 추가, 참고하지 않은 경우 생략)
**참고 페이지:** 3페이지 또는 3페이지, 5페이지
"""
    return PromptTemplate.from_template(template)


def clean_answer(answer: str) -> str:
    # "참고 페이지: 없음" 패턴 제거 (실제 페이지 번호 있는 경우는 유지)
    answer = re.sub(r'\*{0,2}참고 페이지\*{0,2}:\s*(없음|None|없습니다\.?)\s*\n?', '', answer)
    return answer.strip()


def format_docs(docs) -> str:
    result = []
    for doc in docs:
        source     = os.path.basename(doc.metadata.get("source", "알 수 없음"))
        page_label = doc.metadata.get("page_label", "?")
        result.append(f"[출처 : {source} / {page_label}페이지]\n{doc.page_content}")
    return "\n\n".join(result)


def create_chain_with_sources(retriever, chat_history: str = "", mode: str = "hybrid"):
    prompt = create_prompt(mode)
    llm    = create_llm()

    chain = (
        RunnableParallel({
            "docs":     retriever,
            "question": RunnablePassthrough(),
        })
        | RunnablePassthrough.assign(
            answer=(
                {
                    "context":      lambda x: format_docs(x["docs"]),
                    "question":     lambda x: x["question"],
                    "chat_history": lambda _: chat_history,
                }
                | prompt
                | llm
                | StrOutputParser()
                | RunnableLambda(clean_answer)
            )
        )
    )
    return chain


def extract_sources(docs: list) -> list:
    sources = []
    seen = set()
    for doc in docs:
        source     = os.path.basename(doc.metadata.get("source", "알 수 없음"))
        page_label = doc.metadata.get("page_label", "?")
        key = (source, page_label)
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "파일명":        source,
            "페이지":        page_label,
            "내용 미리보기": doc.page_content[:100],
        })
    return sources