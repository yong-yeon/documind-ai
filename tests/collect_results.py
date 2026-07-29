import os    # 파일 경로 처리
import sys   # 프로젝트 루트를 sys.path 에 추가하기 위해 사용
import json  # 결과를 JSON 파일로 저장
import time  # 질문별 응답 시간 측정

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tests/ 에서 core, tests 패키지를 임포트할 수 있도록 프로젝트 루트 추가

from core.loader import load_file                             # PDF 로드 + 청크 분할
from core.vectorstore import create_vectorstore, get_retriever  # 벡터스토어 생성 + 앙상블 리트리버
from core.rag import create_chain_with_sources                # 답변 + 검색된 docs를 함께 반환하는 RAG 체인
from tests.qa_dataset import QA_DATASET                       # 평가용 질문-정답 20개
from config import LLM_MODEL                                  # 결과 파일명에 모델명을 포함시켜 모델별로 결과 분리

pdf_path    = "tests/한국가스공사_지진감지시스템 규격표준_20260506.pdf"
safe_model  = LLM_MODEL.replace("/", "_")                     # 파일명에 못 쓰는 문자(/) 치환
output_path = f"tests/results_{safe_model}.json"


def main():
    split_docs  = load_file(pdf_path)                          # PDF 로드 + 청크 분할
    vectorstore = create_vectorstore(split_docs)                # 청크 임베딩 후 FAISS 인덱스 생성
    retriever   = get_retriever(vectorstore, split_docs)        # FAISS 60% + BM25 40% 앙상블 리트리버

    # mode="document": 평가셋의 범위 밖 질문 정답이 "문서에서 찾을 수 없습니다." 로 고정되어 있어
    # 외부 지식을 섞는 hybrid 모드가 아닌 문서 전용 모드로 채점 기준과 맞춤
    chain = create_chain_with_sources(retriever, mode="document")

    results = []
    done_questions = set()
    if os.path.exists(output_path):                            # 이전 실행 결과가 있으면 이어서 진행 (API 호출 재낭비 방지)
        with open(output_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        done_questions = {r["question"] for r in results}
        print(f"기존 결과 {len(done_questions)}개 발견 → 이어서 진행합니다")

    total = len(QA_DATASET)

    try:
        for i, qa in enumerate(QA_DATASET, start=1):
            question = qa["question"]
            if question in done_questions:                     # 이미 완료된 질문은 재호출하지 않고 건너뜀
                print(f"Q{i}/{total} 이미 완료됨 → 건너뜀")
                continue

            start   = time.perf_counter()                      # 시작 시간 기록
            output  = chain.invoke(question)                   # 답변과 검색된 docs를 한 번에 생성
            elapsed = time.perf_counter() - start               # 종료 시간 기록 → 응답 시간 계산

            contexts = [doc.page_content for doc in output["docs"]]  # 검색된 청크 본문만 추출

            results.append({
                "question":      question,
                "answer":        output["answer"],
                "contexts":      contexts,
                "ground_truth":  qa["ground_truth"],
                "response_time": round(elapsed, 2),
            })

            print(f"Q{i}/{total} 완료 ({elapsed:.2f}초)")
    finally:
        # 중간에 예외(레이트리밋 등)가 나도 그때까지 모은 결과는 항상 저장
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)   # 한글 원문 유지 + 보기 좋게 들여쓰기

    if len(results) == total:
        print(f"전체 완료 → {output_path} 저장됨")
    else:
        print(f"{len(results)}/{total} 개 저장됨 (중단됨) → {output_path}")


if __name__ == "__main__":
    main()
