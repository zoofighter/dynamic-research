# 요건정의서 — 심층 리서치 기반 다각화 보고서 패키지 (Multi-Tier Report Bundle) 자동 생성

> **문서 버전**: v1.0  
> **작성일자**: 2026-10-05  
> **상태**: 승인 대기 (Approved for Implementation)  
> **관련 프로젝트**: `c_1003_dynamic_research`  
> **관련 문서**: 
> - [docs/requirements_20261003.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/requirements_20261003.md) (기본 자율 리서치 요건정의서)
> - [docs/outline_perspectives_design_20261005.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/outline_perspectives_design_20261005.md) (4대 관점 목차 설계서)
> - [docs/dls_design_20261003.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/dls_design_20261003.md) (DLS 엔진 아키텍처)

---

## 1. 배경 및 추진 목적

### 1.1 배경 및 문제 정의
1. **단일 장문 리포트의 독자 피로도**: 현재 시스템은 수집된 모든 정보(팩트, 분석, 리스크, 출처)를 하나의 거대한 마크다운 보고서로 일괄 출력함.
2. **독자별 정보 소비 목적의 상이성**:
   * **경영진(C-Level)**: 1~2페이지 내외의 빠른 결론, 핵심 KPI, 전략적 액션 아이템만 필요.
   * **실무 엔지니어/분석가**: 각주 출처, 상세 기술 아키텍처, 전수 팩트 데이터가 필수.
   * **사업개발/기획팀**: 경쟁사별 스펙·Capa·일정 비교 매트릭스가 핵심.
   * **리스크 관리/투자 심사역**: 미확인 루머, 상충 사실, 퀄테스트 검증 과제 체크리스트가 최우선.
3. **1회 리서치(DLS) 자원의 재활용 극대화**: 웹 검색·스크래핑·정보 평가(Reflection) 과정을 거친 고품질의 팩트 뱅크(Fact Bank)를 1회성 단일 문서로만 소비하는 것은 연산 및 정보 자원의 낭비임.

### 1.2 추진 목적
* 단 1회의 DLS(Dynamic Live Search) 리서치 수행 결과로부터, **독자의 직무 및 의사결정 목적에 맞춘 4종의 차별화된 전문 보고서 패키지(Multi-Tier Report Bundle)**를 원클릭으로 자동 파생·저장하는 시스템을 구축한다.

---

## 2. 다각화 보고서 패키지 구성 (4대 보고서 체계)

```
[DLS 리서치 엔진 (검색 + 크롤링 + 검증)]
                 │
                 ▼ [구조화된 Fact Bank & 출처 메타데이터]
                 │
    ┌────────────┼────────────┬────────────┐
    ▼            ▼            ▼            ▼
[보고서 1]   [보고서 2]   [보고서 3]   [보고서 4]
경영진 전략   심층 기술·산업  경쟁사 비교   리스크 진단 &
1-Pager 브리프  상세 보고서    매트릭스      Due-Diligence
(Executive)   (Technical)   (Benchmark)   (Risk/DD)
```

### 2.1 보고서별 상세 사양

| 구분 | 보고서 1: 경영진 전략 브리프 | 보고서 2: 심층 기술·산업 보고서 | 보고서 3: 벤치마크 비교 매트릭스 | 보고서 4: 리스크 진단 과제서 |
|:---|:---|:---|:---|:---|
| **영문 명칭** | **Executive Strategy 1-Pager** | **Technical Deep-Dive Report** | **Competitive Benchmark Matrix** | **Risk & Due-Diligence Checklist** |
| **주요 독자** | C-Level, 임원진, 최고 의사결정자 | R&D 엔지니어, 수석 애널리스트 | 사업기획, 전략, 마케팅, 구매팀 | 리스크 관리, 감사, 투자 심사역 |
| **권장 분량** | A4 1~2페이지 (1,000자 내외) | 10~20페이지 (풀 버전) | 3~5페이지 (표 및 매트릭스 중심) | 2~4페이지 (체크리스트 중심) |
| **완독 시간** | 3분 내외 (속독/결정용) | 20~30분 (정독/분석용) | 5~10분 (비교/전략 수립용) | 7~10분 (리스크 헤징/점검용) |
| **핵심 구성** | • 3줄 결론 (TL;DR)<br>• 핵심 정량 KPI 카드 (3~4개)<br>• 전략적 시사점<br>• 즉시 실행 과제 (Action Items) | • 연구 배경 및 질문 정의<br>• 문장별 출처 각주 매핑 팩트 전수<br>• 심층 에이전트 해석<br>• 아카이브 출처 링크 | • 플레이어별 4대 축 비교표<br>  (스펙, 생산능력, 수율, 가격)<br>• 경쟁 우위/열위 분석<br>• 시장 점유율 재편 시나리오 | • 상충 보도/정보 신뢰도 평가<br>• 미확인 루머 vs 확인 팩트 분리<br>• 퀄테스트/양산 병목 마일스톤<br>• 향후 모니터링 질문 리스트 |
| **출력 파일명** | `01_executive_brief.md` | `02_technical_deepdive.md` | `03_competitive_matrix.md` | `04_risk_checklist.md` |

---

## 3. 기능 요건 (Functional Requirements)

### FR-MR-01. 리포트 생성 모드 선택 (Generation Mode Selection)
* **설명**: 사용자는 리서치 시작 전 또는 완료 후 원하는 생성 모드를 선택할 수 있어야 한다.
  * `모드 A (Single)`: 기존 단일 상세 리포트만 생성 (빠른 확인용)
  * `모드 B (Full Bundle - 기본값)`: 4종 보고서 전체 패키지 일괄 생성
  * `모드 C (Custom Select)`: 4가지 보고서 중 원하는 보고서만 체크박스로 다중 선택 생성

### FR-MR-02. 다각화 합성 엔진 (Tiered Synthesis Synthesizer)
* **설명**: 수집된 동일한 검증 팩트 뱅크(Fact Bank)와 출처 리스트를 바탕으로 각 보고서 목적에 특화된 프롬프트를 통해 독립적인 보고서 생성.
* **요구사항**:
  * **일관성 보장 (Data Consistency)**: 1-Pager에 인용된 수치(예: 점유율 33%)와 기술 보고서, 벤치마크 표의 수치가 100% 동일해야 함.
  * **프롬프트 템플릿 분리**:
    * `src/prompts/synthesis_executive.py`: 간결성, 수치 중심, 액션 아이템 도출 프롬프트
    * `src/prompts/synthesis_technical.py`: 엄격한 팩트-해석 분리, 문장별 각주 매핑 프롬프트
    * `src/prompts/synthesis_benchmark.py`: 마크다운 표(Table) 및 다자간 비교 전용 프롬프트
    * `src/prompts/synthesis_risk.py`: 상충점 발굴, 신뢰도 평가, 체크리스트 포맷 프롬프트
  * **병렬 생성 지원**: 4종 보고서 생성을 비동기 병렬(`asyncio.gather`) 처리하여 대기 시간 최소화.

### FR-MR-03. 번들 패키징 및 파일 저장 구조 (Bundle Packaging & Storage)
* **설명**: 4종 보고서가 생성되면 개별 파일로 흩어지지 않고 단일 리서치 세션 폴더에 번들 형태로 자동 패키징되어 저장된다.
* **디렉토리 구조**:
  ```text
  output/bundles/
  └── bundle_{topic}_{timestamp}/
      ├── 00_bundle_manifest.json          # 번들 메타데이터 및 각 보고서 요약
      ├── 01_executive_brief.md            # 경영진용 전략 브리프
      ├── 02_technical_deepdive.md         # 심층 기술·산업 상세 보고서
      ├── 03_competitive_benchmark.md      # 경쟁사 비교 매트릭스
      ├── 04_risk_due_diligence.md         # 리스크 진단 및 검증 체크리스트
      └── full_bundle.zip                  # 4종 보고서 통합 압축 파일
  ```
* **매니페스트(`00_bundle_manifest.json`) 필드 규격**:
  * `bundle_id`: 고유 식별자
  * `topic`: 리서치 주제
  * `created_at`: 생성 시각 (ISO8601)
  * `model_used`: 적용 LLM 모델
  * `reports`: 각 보고서별 파일명, 제목, 주요 KPI 목록, 단어 수

### FR-MR-04. 웹 UI 인터랙션 (Streamlit Studio UI)
* **설명**: Streamlit 웹 애플리케이션의 `📑 완성된 리포트 열람실` 및 `💎 스마트 리포트 분석실`에서 번들 보고서를 직관적으로 탐색·활용할 수 있어야 한다.
* **세부 UI 컴포넌트**:
  1. **번들 셀렉터**: 리서치 이력 중 번들 단위로 선택
  2. **서브 탭 네비게이션**:
     * `[👔 전략 브리프]` | `[🔬 심층 분석]` | `[📊 벤치마크 표]` | `[⚠️ 리스크/DD]`
  3. **통합 다운로드 바**:
     * 개별 보고서 다운로드 (`.md`)
     * 번들 전체 원클릭 다운로드 (`.zip`)
  4. **Chat with Bundle (통합 챗봇)**:
     * 특정 단일 문서뿐만 아니라 4종 보고서 전체 컨텍스트를 조망하며 질문할 수 있는 AI Q&A 지원

---

## 4. 비기능 요건 (Non-Functional Requirements)

1. **연산 및 토큰 경제성 (Token Efficiency)**:
   * 검색(Search) 및 크롤링(Scraping)은 반드시 최초 1회만 실행하고 재사용한다.
   * 각 보고서 생성 시 필요한 부분만 컨텍스트로 전달하여 불필요한 토큰 소비를 방지한다.
2. **응답 속도 (Latency)**:
   * 4종 보고서를 순차 생성하지 않고 비동기 병렬 호출(`asyncio.gather`)을 적용하여, 단일 보고서 생성 시간 대비 전체 소요 시간 증가율을 40% 이내로 제어한다.
3. **확장성 (Extensibility)**:
   * 추후 새로운 보고서 유형(예: `05_ir_presentation_deck.md`, `06_patent_analysis.md`)이 필요할 경우, YAML 설정 및 프롬프트 추가만으로 확장 가능한 플러그인 구조를 유지한다.
4. **환각 억제 (Anti-Hallucination)**:
   * 모든 정량 수치와 기업명은 원천 수집 마크다운(`temp/*.md`)에 등장한 근거에 한해서만 생성되도록 시스템 가드레일을 적용한다.

---

## 5. 단계별 구현 일정 (Implementation Roadmap)

| 단계 | 마일스톤 | 산출물 | 완료 기준 |
|:---:|:---|:---|:---|
| **Phase 1** | 보고서별 프롬프트 템플릿 설계 | `src/prompts/bundle_prompts.py` | 4종 보고서 규격 프롬프트 및 테스트 케이스 작성 |
| **Phase 2** | 다각화 합성 노드 및 패키징 모듈 개발 | `src/nodes/bundle_synthesis_nodes.py`<br>`src/utils/bundle_packager.py` | 번들 디렉토리 자동 생성 및 JSON 매니페스트 저장 |
| **Phase 3** | LangGraph 파이프라인 분기 통합 | `src/graphs/dls_research_graph.py` | 모드 선택(Single vs Bundle) 분기 로직 탑재 |
| **Phase 4** | Web UI (Streamlit) 번들 열람실 고도화 | `web/app.py` (Tab 3 & Tab 5) | 서브 탭 뷰, 번들 ZIP 원클릭 다운로드 UI 적용 |
| **Phase 5** | 단위/통합 테스트 및 문서화 | `tests/unit/test_bundle_synthesis.py` | pytest 전원 통과 및 검증 완료 |

---

## 6. 기대 효과

1. **보고서 활용성 극대화**: 동일한 리서치 주제에 대해 임원 보고용 요약본부터 실무진용 데이터 매트릭스까지 한 번에 확보하여 사내 보고 업무 시간 80% 단축.
2. **리서치 신뢰도 향상**: 심층 기술 보고서의 각주와 리스크 진단서의 상충 사실 점검을 분리 제공함으로써 AI 환각 및 일방적 편향 리포팅 원천 차단.
3. **상용 솔루션 수준의 제품 경쟁력 확보**: 단순 챗봇 답변 수준을 넘어 엔터프라이즈 리서치 펌(Gartner, McKinsey 스타일)의 번들형 딜리버리 체계 완성.
