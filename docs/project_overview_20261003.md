# 프로젝트 개요 — 자율 리서치 Agent (Dynamic Research)

> **작성일**: 2026-10-03  
> **프로젝트 경로**: `c_1003_dynamic_research`

---

## 1. 프로젝트 목적

**AI 에이전트가 주제와 아웃라인(질문 + 결론)을 제안하면 사람이 선택·수정하고, 승인된 아웃라인을 기반으로 Dynamic Live Search를 통해 실시간 웹 검색·크롤링·합성을 수행하여 각 슬롯을 채우고 최종 마크다운 리포트를 생성하는 자율 리서치 시스템**을 구축한다.

- **Outline Proposer Agent**: 주제·아웃라인 제안을 전담하는 별도 에이전트로 설계
- 사람은 제안된 아웃라인을 선택·수정·승인하는 **디렉터 역할**

---

## 2. 핵심 워크플로우

```
주제 입력 (Human)
    ↓
아웃라인 제안 (Outline Proposer Agent) — 질문들 + 결론 초안 복수 제시
    ↓
아웃라인 선택·수정·승인 (Human)
    ↓
Dynamic Live Search — 검색 + 아웃라인 채우기 (Search/Scraper Agent)
    ↓  중간 결과물은 temp/ 에 저장
최종 마크다운 리포트 출력 (Synthesizer Agent)
```
### 세부 프로세스 (5-Step Loop)

| 단계 | 설명 |
|:---:|:---|
| 1 | **의도 분석 & 쿼리 분해** — 복합 질문을 3~4개의 전문 검색어로 분해 |
| 2 | **실시간 검색** — Tavily / Google / Serper API 호출 → 상위 결과 랭킹 |
| 3 | **원문 직접 방문 & 파싱** — Jina Reader / Crawl4AI로 웹페이지 전문을 마크다운 추출 |
| 4 | **자기반성 (Self-Reflection)** — 정보 충분성 자율 평가 → 부족 시 Sub-Query 재검색 (2~3회 루프) |
| 5 | **출처 각주 매핑 & 리포트 합성** — 모든 수치에 URL 인라인 각주 매핑, 최종 보고서 작성 |

---

## 3. 미결정 설계 이슈

| 이슈 | 설명 |
|:---:|:---|
| **검색 에이전트 구현 방식** | Dynamic Live Search를 **로컬(Python 자체 구현)** vs **Gemini(Search Grounding)** 중 어디서 수행할지 | 선택할 수 있게 구현 
| **멀티에이전트 구조** | 에이전트를 몇 개로 분리할지, 역할 분담 방식 (예: Query Agent, Scraper Agent, Synthesizer Agent 등) |  선택할 수 있게 구현 

---

## 4. 마크다운 저장 규격 (5대 핵심 요소)

리포트 `.md` 파일 저장 시 반드시 포함해야 할 품질 기준:

1. **원본 출처 투명성** — 검색 쿼리 목록 + 인라인 각주(`[^1]`) + 1차/2차 출처 구분
2. **사실 vs 해석 분리** — `확인된 사실(Facts)` / `에이전트 해석(Analysis)` / `미확인 주장(Unverified)` 3분할
3. **반대 근거 & 반증 조건** — 확증 편향 방지, 결론 철회 기준 사전 정의
4. **휴먼 검토 슬롯 (HITL)** — 사람이 피드백·직접 집필할 Callout 영역 배치
5. **옵시디언 위키링크** — `[[기존_문서]]` 양방향 연결 + MOC + 태그 체계  - 옵시디언 링크는 

---

## 5. 기술 스택 (후보)

| 구분 | 후보 도구 |
|:---|:---|
| **LLM 전용 검색 API** | Tavily Search API, Exa.ai, Google/Serper API |  무료를 사용하거나  직접 구현하는 것을 선택할 수 있게 구현 
| **웹-투-마크다운 파서** | Jina Reader (`r.jina.ai`), Crawl4AI | 선택할 수 있게 구현 
| **LLM** | Gemini (미정) |  선택할 수 있게 구현 
| **오케스트레이션** | 미정 (LangGraph, CrewAI 등 검토 필요) |LangGraph 로 구현 

---

## 6. 참조 프로젝트

기존 유사 작업물을 참고하되, 정확한 참조 범위를 명시할 것:

| 프로젝트 | 참조 목적 (명시 필요) |
|:---|:---|
| `a_0412_content_report` | — |
| `a_0408_report` | — |
| `a_0310_research` | — |

---

## 7. 프로젝트 폴더 구조

```
c_1003_dynamic_research/
├── docs/
│   ├── human.md                          ← 사람이 작성한 기획 메모
│   ├── project_overview_20261003.md      ← 본 문서
│   └── 참조/
│       ├── dynamic_live_search_guide.md  ← Dynamic Live Search 아키텍처 가이드
│       └── markdown_storage_guide.md    ← 마크다운 저장 규격 가이드
```

---

> **다음 단계**: 미결정 설계 이슈(검색 구현 방식, 멀티에이전트 구조)를 확정하고, 참조 프로젝트별 정확한 참조 범위를 정의한 뒤 구현에 착수.
