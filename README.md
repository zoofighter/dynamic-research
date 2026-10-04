# Dynamic Research (자율 리서치 AI 에이전트)

> **Dynamic Live Search (DLS)** 기반 실시간 웹 심층 리서치 및 리포트 자율 생성 플랫폼

---

## 📌 프로젝트 소개

본 프로젝트는 사전 구축된 벡터 데이터베이스(Vector DB) 없이, **실시간 개방형 웹(Open Web)과 최신 뉴스/공시 데이터를 에이전트가 자율적으로 탐색·파싱·합성**하여 고품질 심층 리포트를 생성하는 자율 리서치 시스템입니다.

### 핵심 특징
- **Zero Pre-indexing**: 복잡한 벡터 DB 구축 없이 초 단위 최신 웹 데이터 반영
- **Outline-First HITL**: AI가 주제와 아웃라인을 제안하고, 사람이 승인·수정한 뒤 리서치 수행
- **5-Step Loop**: 쿼리 분해 → 실시간 검색 → 원문 전체 마크다운 파싱 → 자기반성(Self-Reflection) → 인라인 각주 매핑 합성
- **LangGraph 기반 오케스트레이션**: 상태 머신 및 휴먼 인터럽트(Interrupt) 제어

---

## 📂 프로젝트 구조

```
dynamic-research/
├── docs/                 # 아키텍처, 요건정의서, DLS vs RAG, 벤치마킹 설계서
├── src/                  # 에이전트 그래프, 노드, 검색/파서 프로바이더
├── scripts/              # 발표자료 생성 및 벤치마크 러너 스크립트
├── config/               # 시스템 설정 파일
├── temp/                 # 중간 스크래핑/검색 산출물
└── output/               # 최종 마크다운 리포트
```

---

## 📖 주요 문서

- [Dynamic Live Search 설계서](docs/dls_design_20261003.md)
- [LangGraph 에이전트 통합 설계서](docs/langgraph_design_20261004.md)
- [Dynamic Live Search vs Agentic RAG 비교](docs/dls_vs_agentic_rag_20261004.md)
- [LlamaIndex 도입 검토 및 A/B 성능 벤치마킹 설계서](docs/llamaindex_integration_and_benchmarking_20261004.md)
