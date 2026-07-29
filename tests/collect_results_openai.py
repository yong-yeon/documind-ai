import os    # 파일 경로 처리
import sys   # 프로젝트 루트를 sys.path에 추가하기 위해 사용
import json  # 결과를 JSON 파일로 저장
import time  # 질문별 응답 시간 측정

from dotenv import load_dotenv  # .env 파일에서 OPENAI_API_KEY 로드
from openai import OpenAI       # OpenAI LLM 클라이언트

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tests/ 에서 core 패키지를 임포트할 수 있도록 프로젝트 루트 추가

from core.loader import load_file                               # PDF 로드 + 청크 분할 (DocuMind 것 그대로 사용)
from core.vectorstore import create_vectorstore, get_retriever  # 벡터스토어 + 앙상블 리트리버 (DocuMind 것 그대로 사용)
from tests.qa_dataset import QA_DATASET                         # 평가용 질문-정답 20개

# ─────────────────────────────────────────────
# 설정값 (여기만 바꾸면 다른 모델로도 실행 가능)
# ─────────────────────────────────────────────
LLM_MODEL   = "gpt-4o"   # 답변 생성에 사용할 OpenAI 모델
pdf_path    = "tests/한국가스공사_지진감지시스템 규격표준_20260506.pdf"
safe_model  = LLM_MODEL.replace("/", "_")        # 파일명에 못 쓰는 문자(/) 치환
output_path = f"tests/results_{safe_model}.json" # 결과 저장 경로


# ─────────────────────────────────────────────
# 프롬프트: DocuMind rag.py의 document 모드와 완전히 동일
# (모델만 다르고 나머지 조건은 동일해야 공정한 비교가 됨)
# ─────────────────────────────────────────────
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


def format_docs(docs) -> str:
    # 검색된 청크들을 하나의 문자열로 합침 (DocuMind rag.py의 format_docs와 완전히 동일)
    result = []
    for doc in docs:
        source     = os.path.basename(doc.metadata.get("source", "알 수 없음"))
        page_label = doc.metadata.get("page_label", "?")
        result.append(f"[출처 : {source} / {page_label}페이지]\n{doc.page_content}")  # rag.py와 동일한 포맷
    return "\n\n".join(result)


def get_answer(client: OpenAI, context: str, question: str) -> str:
    # OpenAI API 호출해서 답변 생성
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},   # rag.py document 모드 프롬프트와 동일
            {"role": "user",   "content": f"[문서 내용]\n{context}\n\n[사용자 질문]\n{question}"},
        ],
        temperature=0.1,  # DocuMind와 동일하게 낮은 temperature → 일관된 답변
    )
    return response.choices[0].message.content  # 답변 텍스트만 추출


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY를 찾을 수 없습니다. .env 파일을 확인해주세요.")

    client = OpenAI(api_key=api_key)  # OpenAI 클라이언트 생성

    print("PDF 로딩 중...")
    split_docs  = load_file(pdf_path)                    # PDF 로드 + 청크 분할
    vectorstore = create_vectorstore(split_docs)          # 청크 임베딩 후 FAISS 인덱스 생성
    retriever   = get_retriever(vectorstore, split_docs)  # FAISS 60% + BM25 40% 앙상블 리트리버
    print(f"PDF 로딩 완료 → {len(split_docs)}개 청크")

    # 이전 실행 결과 이어받기 (중간에 끊겨도 처음부터 다시 안 해도 됨)
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

            if question in done_questions:  # 이미 완료된 질문은 건너뜀
                print(f"Q{i}/{total} 이미 완료됨 → 건너뜀")
                continue

            docs    = retriever.invoke(question)  # 리트리버로 관련 청크 검색
            context = format_docs(docs)           # 청크들을 하나의 문자열로 합침

            start   = time.perf_counter()
            answer  = get_answer(client, context, question)  # OpenAI로 답변 생성
            elapsed = time.perf_counter() - start

            results.append({
                "question":      question,
                "answer":        answer,
                "contexts":      [doc.page_content for doc in docs],  # RAGAS 채점용 청크 원문
                "ground_truth":  qa["ground_truth"],
                "response_time": round(elapsed, 2),
            })

            print(f"Q{i}/{total} 완료 ({elapsed:.2f}초)")

    finally:
        # 중간에 오류가 나도 그때까지 모은 결과는 항상 저장
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    if len(results) == total:
        print(f"\n전체 완료 → {output_path} 저장됨")
    else:
        print(f"\n{len(results)}/{total}개 저장됨 (중단됨) → {output_path}")


if __name__ == "__main__":
    main()