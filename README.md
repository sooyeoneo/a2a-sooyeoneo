# A2A — Auto to Analysis 
## (기업 정보 수집 → 정제 → 분석 보고서)

<p align="center">
  FastAPI · LangChain · RAG · Tavily(Web) · Alembic · (옵션) LangSmith
</p>

<p align="center">
  <a href="#"><img alt="python" src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white"></a>
  <a href="#"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.11x-009688?logo=fastapi&logoColor=white"></a>
  <a href="#"><img alt="LangChain" src="https://img.shields.io/badge/LangChain-✓-000000"></a>
  <a href="#"><img alt="RAG" src="https://img.shields.io/badge/RAG-Enabled-4B8BBE"></a>
  <a href="#"><img alt="license" src="https://img.shields.io/badge/License-MIT-555555"></a>
</p>

---

## ✨ a2a-sooyeoneo 요약 

**a2a-sooyeoneo**는 기업 공개정보/웹 데이터를 **자동 수집 → 구조화(JSON) → 검증 → 보고서(HTML/JSON) 생성**까지 처리하는 백엔드 파이프라인입니다.

* 목표: 손이 많이 가는 리서치/요약을 **안정적·반복 가능**하게 만들기
* 지향: p95 지연·필드 정합률·재시도율 등 **숫자로 개선 효과 증명**

---

## 🧱 데이터 흐름(Architecture)

1. **웹검색/크롤링**(Tavily 등) → 2) **로딩**(HTML/PDF 텍스트화)
   → 3) **청크**(256\~512 토큰) → 4) **임베딩 저장**(Vector Store)
   → 5) **질의**(섹션별 요청) → 6) **검색(RAG)**(근거 청크 조회)
   → 7) **생성**(LLM **JSON 스키마**에 맞춰 채우기)
   → 8) **검증/부분 재시도**(필드 단위 재생성)
   → 9) **출력**(JSON + HTML 보고서) / (선택) **트레이싱**(LangSmith)

**주요 구성**

* **API**: FastAPI
* **에이전트**: `IngestAgent`(수집/정제/임베딩), `ReportAgent`(RAG+구조화+검증/재시도)
* **RAG**: 청크 → 임베딩 → 유사도 검색 → 근거 기반 생성
* **신뢰성**: 재시도/Fallback(웹서치), 필드 검증, 트레이싱

---

## 🗂️ 폴더 구조(제안)

```
a2a/
├─ app/
│  ├─ api/
│  │  ├─ v1/
│  │  │  ├─ ingest_routes.py
│  │  │  └─ report_routes.py
│  ├─ agents/
│  │  ├─ ingest_agent.py        # 크롤/로딩/청크/임베딩
│  │  └─ report_agent.py        # RAG + 구조화 출력 + 검증/재시도
│  ├─ rag/
│  │  ├─ retriever.py
│  │  └─ vectorstore.py
│  ├─ schemas/
│  │  └─ company_report.py      # Pydantic 모델(구조화 출력 스키마)
│  ├─ services/
│  │  ├─ websearch.py           # Tavily 등
│  │  └─ report_exporter.py     # HTML/JSON 출력
│  ├─ db/
│  │  ├─ models.py
│  │  ├─ session.py
│  │  └─ migrations/            # Alembic
│  ├─ core/
│  │  ├─ config.py
│  │  └─ logging.py
│  └─ main.py
├─ scripts/
│  ├─ run_dev.sh
│  └─ seed_example.sh
├─ tests/
│  ├─ test_schema_validation.py
│  ├─ test_retriever.py
│  └─ test_api.py
├─ alembic.ini
├─ pyproject.toml (또는 requirements.txt)
├─ .env.example
└─ README.md
```

---

## 🧪 핵심 엔드포인트

**자료 수집/임베딩**

```http
POST /api/v1/ingest
Content-Type: application/json
{
  "company": "Acme",
  "sources": ["web", "pdf"],
  "refresh": false
}
```

**보고서 생성**

```http
POST /api/v1/report
Content-Type: application/json
{
  "company": "Acme",
  "sections": ["overview", "financial", "risk"],
  "format": "html"
}
```

**보고서 조회**

```http
GET /api/v1/report/{report_id}
```

---

## 🧩 출력 스키마(예시)

```python
from pydantic import BaseModel
from typing import List

class CompanyReport(BaseModel):
    name: str
    overview: str
    products: List[str]
    markets: List[str]
    risks: List[str]
    citations: List[str]   # 근거 URL 또는 문서 ID
```

* LLM에 **JSON Schema**를 전달해 **구조화 출력**을 강제합니다.
* 필드 검증 실패 시 **그 필드만 부분 재생성(Selective Retry)** 합니다.

---

## ⚙️ 설치 & 실행(로컬)

```bash
# 1) 가상환경
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) 환경변수(.env)
# OPENAI_API_KEY=...
# TAVILY_API_KEY=...
# DB_URL=postgresql+psycopg2://user:pass@localhost:5432/a2a
# LANGSMITH_TRACING=true   # (옵션)

# 3) DB 마이그레이션
alembic upgrade head

# 4) 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📏 지표(숫자/기간/샘플 수 추가 예정)

* **필드 정합률**: `__% → __%` (샘플 N, YYYY.MM)
* **생성 p95 지연**: `__분 → __분`
* **재시도 성공률**: `__%`
* **근거 포함률**: `__%` (각 섹션 1개 이상 citation)

---

## 🧭 로드맵

* [x] Vector Store 교체/검증(FAISS → Qdrant/PGVector)
* [x] **LangGraph** 전환(조건부 흐름/분기 명시)
* [ ] 품질평가 자동화(고정 샘플셋 + 스코어)
* [ ] CI: pytest · ruff · mypy · 슬림 도커
* [ ] 배포: Fly.io/Render/EC2 중 택1 (헬스체크 + 롤백)

---

## 🤖 에이전트 구조 간단 예시

```python
# app/agents/ingest_agent.py
class IngestAgent:
    def run(self, company: str, sources: list[str], refresh: bool=False) -> dict:
        # 1) websearch/crawl -> 2) load -> 3) chunk -> 4) embed/store
        return {"ok": True, "company": company}

# app/agents/report_agent.py
class ReportAgent:
    def run(self, company: str, sections: list[str], fmt: str="html") -> dict:
        # 1) retrieve -> 2) LLM structured output -> 3) field validate
        # 4) selective retry -> 5) export
        return {"report_id": "abc123", "format": fmt}
```


