import os
import sys
import json
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.loader import load_file
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_openai import OpenAIEmbeddings
from tests.qa_dataset import QA_DATASET

# ─────────────────────────────────────────────
# 최종 조합 설정
# LLM: Gemini 3.1 Flash Lite (1위)
# 임베딩: text-embedding-3-small (1위)
# 가중치: 60/40 (베이스라인)
# 청크: 700 (베이스라인)
# k: 5
# ─────────────────────────────────────────────
LLM_MODEL       = "gemini-3.1-flash-lite"
EMBEDDING_MODEL = "text-embedding-3-small"
FAISS_WEIGHT    = 0.6
BM25_WEIGHT     = 0.4
K_VALUE         = 5
DELAY_SEC       = 5   # Gemini 무료 한도 방지

pdf_path    = "tests/한국가스공사_지진감지시스템 규격표준_20260506.pdf"
output_path = "tests/results_final.json"

SYSTEM_PROMPT = """당신은 문서 분석 전문가 AI입니다.

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
14. 숫자 데이터는 항목별로 줄바꿈해서 표시하세요."""


def get_retriever(vectorstore, split_docs):
    faiss_retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": K_VALUE, "fetch_k": 30}
    )
    bm25_retriever   = BM25Retriever.from_documents(split_docs)
    bm25_retriever.k = K_VALUE
    return EnsembleRetriever(
        retrievers=[faiss_retriever, bm25_retriever],
        weights=[FAISS_WEIGHT, BM25_WEIGHT]
    )


def format_docs(docs) -> str:
    result = []
    for doc in docs:
        source     = os.path.basename(doc.metadata.get("source", "알 수 없음"))
        page_label = doc.metadata.get("page_label", "?")
        result.append(f"[출처 : {source} / {page_label}페이지]\n{doc.page_content}")
    return "\n\n".join(result)


def get_answer(gemini_client, context: str, question: str) -> str:
    prompt   = f"{SYSTEM_PROMPT}\n\n[문서 내용]\n{context}\n\n[사용자 질문]\n{question}"
    response = gemini_client.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    return response.text


def main():
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY를 찾을 수 없습니다.")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY를 찾을 수 없습니다.")

    gemini_client = genai.Client(api_key=gemini_api_key)
    embeddings    = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=openai_api_key)

    print(f"LLM: {LLM_MODEL} | 임베딩: {EMBEDDING_MODEL} | k={K_VALUE} | 가중치={FAISS_WEIGHT}/{BM25_WEIGHT}")
    print("PDF 로딩 중...")
    split_docs  = load_file(pdf_path)
    vectorstore = FAISS.from_documents(split_docs, embeddings)
    retriever   = get_retriever(vectorstore, split_docs)
    print(f"PDF 로딩 완료 → {len(split_docs)}개 청크")

    results        = []
    done_questions = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        done_questions = {r["question"] for r in results}
        print(f"기존 결과 {len(done_questions)}개 발견 → 이어서 진행합니다")

    total = len(QA_DATASET)

    try:
        for i, qa in enumerate(QA_DATASET, start=1):
            question = qa["question"]

            if question in done_questions:
                print(f"Q{i}/{total} 이미 완료됨 → 건너뜀")
                continue

            docs    = retriever.invoke(question)
            context = format_docs(docs)

            start   = time.perf_counter()
            answer  = get_answer(gemini_client, context, question)
            elapsed = time.perf_counter() - start

            results.append({
                "question":      question,
                "answer":        answer,
                "contexts":      [doc.page_content for doc in docs],
                "ground_truth":  qa["ground_truth"],
                "response_time": round(elapsed, 2),
            })

            print(f"Q{i}/{total} 완료 ({elapsed:.2f}초)")
            if i < total:
                time.sleep(DELAY_SEC)

    finally:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    if len(results) == total:
        print(f"\n전체 완료 → {output_path} 저장됨")
    else:
        print(f"\n{len(results)}/{total}개 저장됨 (중단됨) → {output_path}")


if __name__ == "__main__":
    main()
