import os      # 파일 경로 처리
import glob    # results_*.json 파일 자동 감지
import json    # 결과 JSON 로드
import csv     # 점수 CSV 저장
import math    # NaN 판별 (일부 샘플에서 채점 불가 시 NaN 반환됨)
import asyncio # ascore()가 비동기 메서드라 asyncio로 실행

from dotenv import load_dotenv       # .env 파일에서 OPENAI_API_KEY 로드
from openai import AsyncOpenAI       # ragas 판정 LLM/임베딩이 사용할 OpenAI 비동기 클라이언트
from ragas.llms.base import llm_factory              # 판정 LLM 래퍼 생성
from ragas.embeddings.base import embedding_factory  # answer_relevancy 채점용 임베딩 모델 래퍼 생성
from ragas.metrics.collections import (              # 최신(0.4.x) 방식 지표 클래스
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    FactualCorrectness,
)

load_dotenv()

JUDGE_MODEL = "gpt-4o-mini"                  # 판정 LLM (OpenAI, 벤치마크 계획에서 고정한 모델)
EMBEDDING_MODEL = "text-embedding-3-small"  # answer_relevancy 계산용 임베딩 모델
DELAY_SECONDS   = 3                         # 샘플 간 딜레이 (TPM 한도 초과 방지)


def find_result_files() -> list:
    # tests/ 폴더에서 results_*.json 파일 자동 감지
    return sorted(glob.glob("tests/results_*.json"))


def extract_model_name(path: str) -> str:
    # "tests/results_gpt-4o-mini.json" → "gpt-4o-mini"
    filename = os.path.basename(path)
    return filename[len("results_"):-len(".json")]


def average(values: list) -> float:
    # NaN(채점 불가 샘플)은 제외하고 평균 계산
    clean = [v for v in values if v is not None and not math.isnan(v)]
    return sum(clean) / len(clean) if clean else float("nan")


async def score_file(path: str, metrics: dict) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    scores = {name: [] for name in metrics}
    total  = len(samples)

    for i, sample in enumerate(samples, start=1):
        user_input         = sample["question"]
        response           = sample["answer"]
        retrieved_contexts = sample["contexts"]
        reference          = sample["ground_truth"]

        scores["faithfulness"].append(
            (await metrics["faithfulness"].ascore(
                user_input=user_input, response=response, retrieved_contexts=retrieved_contexts
            )).value
        )
        scores["answer_relevancy"].append(
            (await metrics["answer_relevancy"].ascore(
                user_input=user_input, response=response
            )).value
        )
        scores["context_precision"].append(
            (await metrics["context_precision"].ascore(
                user_input=user_input, reference=reference, retrieved_contexts=retrieved_contexts
            )).value
        )
        scores["context_recall"].append(
            (await metrics["context_recall"].ascore(
                user_input=user_input, retrieved_contexts=retrieved_contexts, reference=reference
            )).value
        )
        scores["factual_correctness"].append(
            (await metrics["factual_correctness"].ascore(
                response=response, reference=reference
            )).value
        )

        print(f"  샘플 {i}/{total} 채점 완료")

        # TPM 한도 초과 방지: 샘플마다 딜레이 (마지막 샘플은 생략)
        if i < total:
            await asyncio.sleep(DELAY_SECONDS)

    return scores


async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY를 찾을 수 없습니다. .env 파일을 확인해주세요.")

    client     = AsyncOpenAI(api_key=api_key)
    llm        = llm_factory(JUDGE_MODEL, client=client)
    embeddings = embedding_factory("openai", EMBEDDING_MODEL, client=client)

    metrics = {
        "faithfulness":        Faithfulness(llm=llm),
        "answer_relevancy":    AnswerRelevancy(llm=llm, embeddings=embeddings),
        "context_precision":   ContextPrecision(llm=llm),
        "context_recall":      ContextRecall(llm=llm),
        "factual_correctness": FactualCorrectness(llm=llm),
    }

    result_files = find_result_files()
    if not result_files:
        print("tests/ 폴더에서 results_*.json 파일을 찾지 못했습니다.")
        return

    for path in result_files:
        model_name = extract_model_name(path)
        print(f"\n{model_name} 채점 시작 ({path})")

        scores   = await score_file(path, metrics)
        averages = {name: average(values) for name, values in scores.items()}
        overall  = average(list(averages.values()))

        print(f"\n{model_name} 채점 완료")
        print(f"faithfulness        : {averages['faithfulness']:.4f}")
        print(f"answer_relevancy    : {averages['answer_relevancy']:.4f}")
        print(f"context_precision   : {averages['context_precision']:.4f}")
        print(f"context_recall      : {averages['context_recall']:.4f}")
        print(f"factual_correctness : {averages['factual_correctness']:.4f}")
        print(f"평균                : {overall:.4f}")

        csv_path = f"tests/scores_{model_name}.csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "score"])
            for name, value in averages.items():
                writer.writerow([name, value])
            writer.writerow(["average", overall])

        print(f"→ {csv_path} 저장됨")


if __name__ == "__main__":
    asyncio.run(main())