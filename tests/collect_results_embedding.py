import os    # 파일 경로 처리
import sys   # 프로젝트 루트를 sys.path에 추가하기 위해 사용
import json  # 결과를 JSON 파일로 저장
import time  # 질문별 응답 시간 측정

from dotenv import load_dotenv  # .env 파일에서 GROQ_API_KEY 로드
from groq import Groq            # Groq LLM 클라이언트 (LLM은 llama-3.1-8b 고정)

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.loader import load_file          # PDF 로드 + 청크 분할
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_community.embeddings import HuggingFaceEmbeddings
from tests.qa_dataset import QA_DATASET    # 평가용 질문-정답 20개

# ─────────────────────────────────────────────
# 설정값 (여기만 바꾸면 다른 임베딩 모델로 실험 가능)
# ─────────────────────────────────────────────
LLM_MODEL       = "llama-3.1-8b-instant"                      # LLM 고정
EMBEDDING_MODEL = "all-MiniLM-L6-v2"      # 바꿀 임베딩 모델
# EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # all-MiniLM-L6-v2 쓸 때

pdf_path    = "tests/한국가스공사_지진감지시스템 규격표준_20260506.pdf"
safe_name   = EMBEDDING_MODEL.split("/")[-1].replace(".", "-") # 모델명에서 파일명용 이름 추출
output_path = f"tests/results_emb_{safe_name}.json"

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


def create_embeddings():
    # HuggingFace 임베딩 모델 생성 (로컬에서 실행, 무료)
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={
            "batch_size": 64,
            "normalize_embeddings": True,
        },
    )


def get_retriever(vectorstore, split_docs, k=5):
    # FAISS 60% + BM25 40% 앙상블 리트리버 (k=3, Groq 토큰 한도 방지)
    faiss_retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": 30}
    )
    bm25_retriever   = BM25Retriever.from_documents(split_docs)
    bm25_retriever.k = k
    return EnsembleRetriever(
        retrievers=[faiss_retriever, bm25_retriever],
        weights=[0.6, 0.4]
    )


def format_docs(docs) -> str:
    result = []
    for doc in docs:
        source     = os.path.basename(doc.metadata.get("source", "알 수 없음"))
        page_label = doc.metadata.get("page_label", "?")
        result.append(f"[출처 : {source} / {page_label}페이지]\n{doc.page_content}")
    return "\n\n".join(result)


def get_answer(client, context: str, question: str) -> str:
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"[문서 내용]\n{context}\n\n[사용자 질문]\n{question}"},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content


def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY를 찾을 수 없습니다.")

    client = Groq(api_key=api_key)

    print(f"임베딩 모델: {EMBEDDING_MODEL}")
    print("PDF 로딩 중...")
    split_docs  = load_file(pdf_path)
    embeddings  = create_embeddings()                          # 지정한 임베딩 모델로 생성
    vectorstore = FAISS.from_documents(split_docs, embeddings) # 임베딩으로 FAISS 인덱스 생성
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
            answer  = get_answer(client, context, question)
            elapsed = time.perf_counter() - start

            results.append({
                "question":      question,
                "answer":        answer,
                "contexts":      [doc.page_content for doc in docs],
                "ground_truth":  qa["ground_truth"],
                "response_time": round(elapsed, 2),
            })

            print(f"Q{i}/{total} 완료 ({elapsed:.2f}초)")
            print(f"Q{i}/{total} 완료 ({elapsed:.2f}초)")
            time.sleep(10)  # Groq 토큰 한도 방지

    finally:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    if len(results) == total:
        print(f"\n전체 완료 → {output_path} 저장됨")
    else:
        print(f"\n{len(results)}/{total}개 저장됨 (중단됨) → {output_path}")


if __name__ == "__main__":
    main()
