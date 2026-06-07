import os

try:
    from config import get_groq_api_key, LLM_MODEL
except ModuleNotFoundError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import get_groq_api_key, LLM_MODEL

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough


def create_llm():
    """
    LLM 모델 생성 함수

    Returns:
        llm : ChatGroq 객체
    """
    api_key = get_groq_api_key()

    if not api_key:
        raise ValueError("API 키를 찾을 수 없어요! .env 파일을 확인해주세요.")

    llm = ChatGroq(
        api_key=api_key,
        model_name=LLM_MODEL
    )
    return llm


def create_prompt():
    """
    프롬프트 템플릿 생성 함수

    Returns:
        prompt : PromptTemplate 객체
    """
    prompt = PromptTemplate.from_template("""
당신은 문서 분석 전문가입니다.
아래 문서 내용과 이전 대화 기록을 바탕으로 질문에 한국어로 상세하게 답변해주세요.
문서에 없는 내용은 "문서에서 찾을 수 없습니다" 라고 답변해주세요.
답변 마지막에 반드시 참고한 내용의 페이지 번호를 표시해주세요.

이전 대화 기록 :
{chat_history}

문서 내용 :
{context}

질문 : {question}

답변 :
""")
    return prompt


def format_docs(docs) -> str:
    """
    검색된 문서 조각들을 하나의 문자열로 합치는 함수

    Args:
        docs : 검색된 문서 조각 리스트

    Returns:
        formatted : 페이지 정보 포함한 문자열
    """
    result = []
    for doc in docs:
        page = doc.metadata.get("page", "?")
        source = os.path.basename(doc.metadata.get("source", "알 수 없음"))
        # page 가 "?" 일 때 int 변환 오류 방지
        page_num = int(page) + 1 if page != "?" else "?"
        result.append(f"[출처 : {source} / {page_num}페이지]\n{doc.page_content}")
    return "\n\n".join(result)


def create_chain(retriever, chat_history: str = ""):
    """
    RAG 체인 생성 함수

    Args:
        retriever    : vectorstore.py 에서 만든 검색기
        chat_history : 이전 대화 기록 문자열 (기본값 빈 문자열)

    Returns:
        chain : 실행 가능한 RAG 체인
    """
    prompt = create_prompt()
    llm = create_llm()

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
            "chat_history": lambda x: chat_history
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def get_sources(retriever, query: str) -> list:
    """
    질문과 관련된 출처 정보를 반환하는 함수

    Args:
        retriever : 검색기
        query     : 질문

    Returns:
        sources : 출처 정보 리스트
    """
    docs = retriever.invoke(query)
    sources = []
    for doc in docs:
        page = doc.metadata.get("page", "?")
        source = os.path.basename(doc.metadata.get("source", "알 수 없음"))
        # page 가 "?" 일 때 int 변환 오류 방지
        page_num = int(page) + 1 if page != "?" else "?"
        sources.append({
            "파일명": source,
            "페이지": page_num,
            "내용 미리보기": doc.page_content[:100]
        })
    return sources


# ─────────────────────────────────────────
# 테스트 코드
# ─────────────────────────────────────────
def print_rag_test(split_docs):
    """rag.py 테스트 함수"""
    from core.vectorstore import create_vectorstore, get_retriever

    print("=" * 40)
    print("  rag.py 테스트")
    print("=" * 40)

    # 1. 벡터 저장소 + 검색기 생성
    print("✅ 벡터 저장소 생성 중...")
    vectorstore = create_vectorstore(split_docs)
    retriever = get_retriever(vectorstore)
    print("✅ 벡터 저장소 생성 완료")

    # 2. 체인 생성
    print("✅ RAG 체인 생성 중...")
    chain = create_chain(retriever)
    print("✅ RAG 체인 생성 완료")

    # 3. 질문 테스트
    question = "서울 지하철 하루 평균 이용객 수는 얼마야?"
    print(f"\n질문 : {question}")
    print("\n답변 생성 중...")
    answer = chain.invoke(question)
    print(f"\n답변 :\n{answer}")

    # 4. 출처 확인
    print("\n--- 참고 출처 ---")
    sources = get_sources(retriever, question)
    for s in sources:
        print(f"  📄 {s['파일명']} / {s['페이지']}페이지")
        print(f"     {s['내용 미리보기']}...")

    print("=" * 40)
    print("✅ rag.py 테스트 완료!")
    print("=" * 40)


if __name__ == "__main__":
    from core.loader import load_pdf

    test_file = r"D:\LLMchatbot\workspace\data\2025년서울교통이용통계보고서.pdf"

    print("✅ PDF 로딩 중...")
    split_docs = load_pdf(test_file)
    print(f"✅ PDF 로딩 완료 (조각 수 : {len(split_docs)})")

    print_rag_test(split_docs)