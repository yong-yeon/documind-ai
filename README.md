# DocuMind AI

여러 형식의 문서를 업로드하고 자연어로 질문하면, **답변의 근거가 된 출처 페이지를 함께 제공**하는 RAG 기반 문서 질의응답 서비스입니다.

**Live Demo** → https://yy-docuai.streamlit.app
**발표 자료** → [DocuMindAI_Portfolio.pdf](docs/DocuMindAI_Portfolio.pdf)

---

## 해결하려는 문제

대용량 문서에서 원하는 정보를 찾으려면 `Ctrl+F` 키워드 검색에 의존해야 하는데, 이 방식은 문맥을 이해하지 못합니다. 그렇다고 일반 LLM에 문서를 붙여넣어 물으면 답은 나오지만, 그 답이 문서의 어디서 나왔는지 확인할 수 없어 신뢰하기 어렵고 할루시네이션(사실과 다른 내용을 지어내는 현상) 위험도 있습니다.

DocuMind AI는 질문과 관련된 문서 조각을 먼저 검색한 뒤 그 근거만으로 답변을 생성하고, **답변과 함께 출처 페이지 번호를 자동으로 표시**합니다.

---

## 주요 기능

| 기능 | 설명 |
|---|---|
| 다중 형식 문서 지원 | PDF, DOCX, XLSX, PPTX 업로드 |
| 출처 페이지 제공 | 답변 근거가 된 원문 조각과 실제 인쇄 페이지 번호 표시 |
| 하이브리드 검색 | 의미 기반(FAISS) + 키워드 기반(BM25) 결합 |
| 스캔 PDF OCR | 이미지로만 된 PDF도 텍스트 자동 인식 |
| 반복 블록 제거 | 머리말·꼬리말을 패턴으로 감지해 검색 노이즈 제거 |
| 답변 모드 선택 | 문서 전용 / 혼합(문서 우선 + AI 지식 보완) |

---

## 시스템 구조

문서 업로드 시 한 번 수행하는 인덱싱 과정과, 질문마다 수행하는 검색·답변 과정으로 나뉩니다.

**인덱싱 (업로드 시 1회)**
```
문서 업로드 (PDF/DOCX/XLSX/PPTX)
   → PyMuPDF 파싱 (스캔 PDF는 Tesseract OCR 자동 전환)
   → 반복 머리말·꼬리말 제거
   → 청킹 (size=700, overlap=150)
   → 임베딩 → FAISS 인덱스 + BM25 인덱스 구축
```

**질의 (질문마다)**
```
질문 → 임베딩
   → 하이브리드 검색 (FAISS MMR + BM25, 가중치 6:4)
   → 상위 5개 청크 선별 (fetch_k=30, k=5)
   → LLM 답변 생성 + 동일 청크에서 출처 추출
```

서비스 구성: LLM `llama-3.3-70b-versatile` (Groq) · 임베딩 `paraphrase-multilingual-MiniLM-L12-v2` (HuggingFace)

전체 아키텍처 다이어그램은 [발표 자료](docs/DocuMindAI_Portfolio.pdf) 3페이지를 참고하세요.

---

## 기술 스택

| 구분 | 기술 | 선택 이유 |
|---|---|---|
| Language | Python 3.11 | AI/ML 생태계 표준 |
| Framework | Streamlit | 빠른 웹 UI 구현과 캐싱 지원 |
| LLM | Groq (llama-3.3-70b-versatile) | 고속 추론 API, 오픈소스 모델을 낮은 지연으로 활용 |
| Orchestration | LangChain | 로딩·청킹·검색·프롬프트 체인 통합 관리 |
| Embedding | HuggingFace MiniLM-L12-v2 | 다국어(한국어) 지원 경량 모델, 로컬 실행 무료 |
| Retriever | FAISS + BM25 | 의미 검색과 키워드 검색 결합으로 정확도 향상 |
| Parsing | PyMuPDF | 블록 좌표 기반 읽기 순서 복원, 스캔 PDF 연계 |
| OCR | Tesseract | 스캔 PDF 텍스트 추출 (오픈소스) |
| Evaluation | RAGAS | RAG 전용 정량 평가 프레임워크 |

---

## 성능 최적화 실험

한국가스공사 지진감지시스템 표준 문서로 **20문항 QA 데이터셋을 직접 구축**하고, 한 번에 하나의 변수만 바꾸며 RAGAS로 정량 평가했습니다. 심판 모델은 `gpt-4o-mini`로 고정하고, 모든 실험을 `k=5`, `fetch_k=30` 조건으로 통일했습니다.

평가 지표: faithfulness(환각 여부), answer_relevancy(질문 적합성), context_precision·context_recall(검색 품질), factual_correctness(사실 정확도)

### LLM 비교

| 모델 | 평균 |
|---|---|
| **Gemini 3.1 Flash Lite** | **0.6937** |
| gpt-4o | 0.6751 |
| llama-3.1-8b (베이스라인) | 0.6462 |

무료 모델인 Gemini Flash Lite가 유료 gpt-4o보다 높은 평균을 기록했습니다. gpt-4o는 factual_correctness 0.787로 사실 정확도가 가장 높았지만, answer_relevancy에서 뒤처졌습니다.

### 임베딩 비교 (LLM llama-3.1-8b 고정)

| 임베딩 | 평균 |
|---|---|
| text-embedding-3-small | 0.6600 |
| Ko-SBERT | 0.6567 |
| MiniLM-L12-v2 (베이스라인) | 0.6462 |
| all-MiniLM-L6-v2 | 0.6206 |

all-MiniLM-L6-v2는 context_precision이 0.277로 특히 낮았습니다.

### 검색 파라미터 비교

| 설정 | 평균 |
|---|---|
| 가중치 60:40 · 청크 700 (베이스라인) | 0.6462 |
| 가중치 50:50 | 0.6442 |
| 청크 500 | 0.6110 |

FAISS 비중이 높은 60:40이 더 유리했고, 청크를 500으로 줄이면 문맥이 끊겨 성능이 떨어졌습니다.

### 최종 조합에서 얻은 교훈

각 실험에서 1위였던 컴포넌트(Gemini + text-embedding-3-small + 60:40)를 조합했더니 평균 0.6406으로, 오히려 베이스라인(0.6462)보다 낮았습니다. **개별 최고 성능의 조합이 전체 최고 성능을 보장하지 않는다**는 것을 실험으로 확인했습니다. LLM과 임베딩의 벡터 공간 표현 방식이 서로 맞물리지 않으면 상호작용이 달라지기 때문으로 보입니다.

> 성격이 다른 5개 지표를 단순 산술평균으로 합산했으므로, 평균값은 대략적인 경향으로만 해석해야 합니다. 지표별 상세 수치는 [발표 자료](docs/DocuMindAI_Portfolio.pdf)에 있습니다.

---

## 트러블슈팅

### 1. 헤더·푸터가 검색 결과를 오염시킴
- **문제**: 모든 페이지에 반복되는 문서 제목과 페이지 번호가 검색 상위에 잡혔습니다.
- **1차 시도**: 페이지 상하 8% 영역 일괄 제거 → 레이아웃이 다른 문서에서 본문까지 잘렸습니다.
- **해결**: 위치가 아닌 **반복 패턴**으로 판단하도록 변경. 텍스트의 숫자를 `#`로 정규화해 "3 / 20"과 "17 / 20"을 같은 패턴으로 묶고, 전체 페이지의 30% 이상에서 반복되는 짧은 블록만 제거합니다.

### 2. 스캔 PDF에서 텍스트가 추출되지 않음
- **문제**: 이미지로만 된 PDF는 검색 결과가 비었습니다.
- **해결**: 페이지 텍스트가 20자 미만이면 스캔본으로 판단해 OCR로 자동 전환. 300 DPI 렌더링과 `--psm 6 --oem 3` 옵션으로 한국어 인식률을 확보했습니다.

### 3. 같은 검색을 두 번 수행하던 구조
- **문제**: 답변 생성과 출처 표시가 각각 검색을 실행해, 동일 질문으로 검색이 두 번 돌았습니다.
- **해결**: `RunnableParallel`로 검색 결과를 유지하면서 답변만 덧붙이는 구조로 변경. 하나의 검색 결과로 답변과 출처를 모두 처리해 검색 횟수를 절반으로 줄였습니다.

### 4. 로컬은 정상인데 배포 환경에서만 앱이 다운
- **문제**: 로컬에서 잘 돌던 코드가 Streamlit Cloud에서 `ModuleNotFoundError`로 즉시 종료됐습니다.
- **원인**: (1) 로컬에만 설치한 `pytesseract`·`pillow`를 requirements에 누락 (2) Tesseract는 pip로 설치되지 않는 독립 프로그램 (3) 실행 경로를 Windows 절대 경로로 하드코딩.
- **해결**: 누락 패키지를 추가하고, 시스템 패키지용 `packages.txt`로 `tesseract-ocr`을 명시. 실행 경로는 `platform.system()`과 `os.path.exists()`로 OS를 판별해 존재할 때만 지정하도록 수정했습니다.

### 5. RAGAS 설치 시 패키지 충돌
- **문제**: 평가용 패키지 설치 후 앱이 실행되지 않았습니다.
- **원인**: `langchain-core` 요구 버전이 0.3.63과 1.4.x로 충돌.
- **해결**: 앱 실행용과 평가용 conda 환경을 분리했습니다.

더 많은 문제 해결 사례(API 토큰 한도, 심판 모델 비용 등)는 [발표 자료](docs/DocuMindAI_Portfolio.pdf) 7페이지에 정리되어 있습니다.

---

## 실행 방법

```bash
git clone https://github.com/yong-yeon/documind-ai.git
cd documind-ai

conda create -n documind python=3.11
conda activate documind
pip install -r requirements.txt
```

`.env.example`을 복사해 `.env`를 만들고 키를 입력합니다.

```
GROQ_API_KEY=your_groq_api_key_here
```

스캔 PDF의 OCR을 쓰려면 [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) 설치가 필요합니다. Windows 기본 경로에 설치하면 자동 인식하고, 다른 경로라면 시스템 PATH에 등록하면 됩니다.

```bash
streamlit run app.py
```

---

## 한계 및 개선 방향

| 한계 | 개선 방향 |
|---|---|
| 응답 시간을 단계별로 측정하지 못함 | 검색·생성 단계별 시간 측정 및 최적화 |
| 특정 문서 중심 평가로 일반화 검증 부족 | 법률·금융·기술 등 다양한 도메인으로 추가 평가 |
| 검색 결과 재순위화(Re-ranking) 미적용 | Cross-Encoder 기반 Re-ranking 도입 |
| 로컬 FAISS 구조의 확장성 한계 | Qdrant 등 영속형 Vector DB 검토 |

---

## 개발 정보

- **기간**: 2026.05 ~ 2026.07
- **인원**: 1인 (개인 프로젝트)
- **평가 문서**: 테스트에 쓴 원본 PDF는 저작권상 저장소에 포함하지 않았습니다.
