# [프레젠테이션 기획안 및 슬라이드 상세 구성]
## 자율 리서치 Agent (Dynamic Research) 아키텍처

> **문서 버전**: v1.0  
> **생성 일시**: 2026-10-04  
> **파워포인트 파일**: [dynamic_research_presentation_20261004.pptx](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/dynamic_research_presentation_20261004.pptx) (16:9 와이드스크린, 8개 슬라이드)

---

### [Slide 1] 표지 (Title Slide)
- **배경 톤**: Deep Dark Navy (`#0F172A`)
- **Category Tag**: `NEXT-GEN AI RESEARCH ARCHITECTURE`
- **Main Title**: **자율 리서치 Agent 시스템**
- **Sub Title**: Dynamic Live Search & Human-in-the-Loop 아키텍처
- **Description**: 사전 벡터 DB(RAG)의 시점 한계를 극복하는 100% 실시간 웹 심층 탐색과 인간-AI 협업(HITL) 기반의 고신뢰성 심층 보고서 자율 생성 플랫폼
- **Metadata**: 프로젝트: `c_1003_dynamic_research` | 기준일: 2026. 10. 04 | 버전: v1.0

---

### [Slide 2] 문제 정의 및 추진 배경 (Why Dynamic Live Search?)
- **헤더**: 왜 기존 RAG가 아닌 'Dynamic Live Search'인가?
- **3대 핵심 문제 및 요구사항 (카드형 레이아웃)**:
  1. **01. 사전 임베딩(RAG)의 한계 (어제의 데이터로는 오늘을 분석 불가)**
     - 벡터 DB 구축 및 청킹·임베딩 파이프라인의 높은 비용과 지연
     - 매일 급변하는 최신 시사/경제/기술 이슈에 대응 불가
     - '고정된 지식 창고'에 갇혀 실시간 웹의 최신 정보를 반영하지 못함
  2. **02. 맹목적 전면 자동화의 함정 (원하지 않는 방향으로 산으로 가는 리포트)**
     - 사용자 의도와 관점(Angle)이 배제된 일방적 보고서 출력
     - 목차(Outline)가 엉뚱하면 수백 번의 검색도 무용지물
     - 인간이 핵심 방향타를 쥐는 'Human-in-the-Loop' 개입이 필수적
  3. **03. 출처 불투명 & 환각 (근거 없는 AI 주장은 신뢰할 수 없음)**
     - 출처 URL과 기사 본문 매핑 없는 요약문은 검증 불가능
     - 팩트(Fact)와 AI 해석(Analysis)이 뒤섞여 비즈니스 의사결정 위험
     - 엄격한 인라인 각주와 원문 마크다운 대조 체계 필요

---

### [Slide 3] 전체 시스템 구조 — 2-Agent / 2-Graph 분리 아키텍처
- **헤더**: 2-Agent 분리 파이프라인: 인간 승인 기반의 느슨한 결합
- **구조 특징**: 기획 영역(HITL)과 자율 리서치 영역의 명확한 역할 분리 및 `approved_outline.json`을 통한 독립 결합
- **Graph 1: TopicOutlineGraph (주제 발굴 & 아웃라인 제안)**
  1. 뉴스/과거글 스캔: 한경 최신 기사 100건 + 과거 리포트
  2. LLM 클러스터링: 핫 트렌드 분석 및 쓸 만한 주제 5개 도출
  3. 아웃라인 생성: 독자 수준별 A/B/C 복수 목차 기획
  4. Human Review (Interrupt): 터미널에서 선택·수정·승인
  - ▶ *산출물: `approved_outline.json` (표준 규격 목차)*
- **Bridge**: `approved_outline.json` 전달 (독립 실행 및 재사용 가능)
- **Graph 2: DLSResearchGraph (동적 라이브 검색 & 자율 심층 리서치)**
  1. 질문 분해 & 균형 쿼리: 찬반/리스크 포함 다각도 질의 생성
  2. 실시간 웹 검색: Google Serper + DuckDuckGo 하이브리드
  3. 원문 크롤링: Jina Reader 3단계 Fallback (마크다운 변환)
  4. Self-Reflection: 정보 충분성 자율 검증 및 재검색 루프
  5. 섹션별 집필 & 조립: 인라인 각주 및 참고문헌 표 1:1 매핑
  - ▶ *산출물: `output/{run_id}.md` (최종 심층 분석 보고서)*

---

### [Slide 4] Graph 1 상세 — AI 트렌드 발굴과 Human-in-the-Loop 승인
- **헤더**: Graph 1: AI 트렌드 발굴과 Human-in-the-Loop 승인
- **좌측: 실시간 뉴스 스캔 및 주제 발굴**
  - **한국경제 오늘의 기사 수집 실측 검증 완료**:
    - Google News RSS (`site:hankyung.com`) 타겟팅
    - 1초 만에 최신 기사 100건 무료·무차단 수집 성공
    - 한경 직접 웹 호출 시 403 봇 차단 문제를 완벽 우회
  - **3대 소스 융합 클러스터링**:
    1. 최신 24~72시간 실시간 뉴스 헤드라인
    2. `output/` 폴더의 기존 작성 리포트 (중복 방지 & 후속 분석)
    3. 사용자 관심 키워드 및 도메인
  - **LLM 추천 결과**: 지금 당장 작성할 가치가 있는 '핵심 주제 5개' 도출
- **우측: A/B/C 복수 목차 제안 & CLI 승인 인터랙터**
  - **3가지 관점의 복수 아웃라인(Multi-Proposals)**:
    - [A안: 산업/투자자 관점] 시장 규모, 밸류체인 수혜 기업, 리스크
    - [B안: 기술/엔지니어링 관점] 기술적 한계, 대안 기술, 아키텍처 비교
    - [C안: 정책/글로벌 관점] 각국 규제 동향, 표준화 경쟁, 거시 전망
  - **대화형 CLI 인터랙터 (Human-in-the-Loop)**:
    - LangGraph의 `interrupt()` 기반 안전한 실행 일시정지
    - 터미널 메뉴: `[1] A안 승인` `[2] B안 승인` `[e] 직접 수정` `[r] 재생성`
    - 사람이 방향을 확정한 직후 Graph 2 자율 리서치로 핸드오프

---

### [Slide 5] Graph 2 상세 — 동적 검색·크롤링·반성(Self-Reflection) 루프
- **헤더**: Graph 2: 동적 검색·크롤링·반성(Self-Reflection) 루프
- **4단계 프로세스 파이프라인**:
  - **STEP 1. 질문 분해 & 균형 쿼리**
    - 목차 소주제별로 검색 질문 분해
    - [편향 방지 쿼리]: 찬양 일색 방지를 위해 비판/리스크 쿼리 1개 이상 강제 생성
    - 한국어/영어 최적 키워드 확장
  - **STEP 2. 실시간 검색 & 크롤링**
    - [검색 하이브리드]: Google Serper 최우선 + DDG 자동 Fallback
    - [3단계 크롤링 Fallback]: Jina Reader → Trafilatura → 검색 스니펫
    - 봇 차단/Paywall 대응 보장
  - **STEP 3. 자율 반성 (Self-Reflection)**
    - 수집된 데이터의 충분성 자체 평가
    - 팩트 모호/데이터 부족 판정 시 보완 쿼리 자동 생성 후 재검색
    - 최대 3회 루프로 무한 루프 방지
  - **STEP 4. 섹션 합성 & 보고서 조립**
    - 경제/산업 핵심 수치 표(Table) 추출
    - 팩트와 해석의 명확한 분리 서술
    - 인라인 각주(`[^1]`) 및 하단 출처 표 자동 생성 완료

---

### [Slide 6] 구현 전 11대 엔지니어링 보완 전략 (Pre-Review)
- **헤더**: 사전 점검을 통해 도출한 11대 핵심 엔지니어링 전략
- **2x2 매트릭스 구성**:
  1. **실시간 데이터 수집 최적화**
     - [한경 오늘의 기사]: Google News RSS 연동으로 1초 100건 무료·무차단 수집
     - [하이브리드 검색]: Google Serper (정밀) + DuckDuckGo (무료 Fallback)
     - [3단계 크롤링]: Jina Reader → Trafilatura (로컬) → 검색 스니펫
  2. **토큰 비용 & 지연시간 80% 절감**
     - [State 메모리 압축]: 원문(1만 자) 대신 Key Evidence(500자)만 State 보관
     - [디스크 로컬 캐싱]: 검색 쿼리(24h), URL 크롤링(7일) 캐시로 즉각 응답
     - [섹션 에러 격리]: 특정 섹션 수집 오류 시에도 전체 파이프라인 무중단 진행
  3. **LLM 3단 계층화 (Tiering)**
     - [Fast Tier (Flash / Ollama 8B)]: 쿼리 생성, Self-Reflection 등 경량 반복 작업
     - [Standard Tier (Gemini Flash)]: 주제 발굴 및 다각도 목차 기획
     - [Deep Tier (Gemini Pro / Sonnet)]: 깊이 있는 분석, 섹션 집필 및 최종 조립
  4. **리포트 품질 및 사용성 혁신**
     - [균형 쿼리 강제]: 찬반/리스크 쿼리를 생성하여 편향된 보고서 방지
     - [경제 정량 수치 표]: 기사 속 매출/점유율 등 핵심 통계를 마크다운 표로 추출
     - [대화형 CLI & Notion 연동]: 터미널 실시간 승인 및 Notion 원클릭 발행 지원

---

### [Slide 7] 시스템 기술 스택 및 개발 인프라 구성
- **헤더**: 시스템 기술 스택 및 개발 인프라 구성
- **구성표 요약**:
  - **오케스트레이션**: LangGraph v1.2+ (2-Graph 분리 상태 머신 및 interrupt() 기반 HITL 제어, 오픈소스 무료)
  - **데이터 수집 (News)**: Google News RSS + feedparser (한경 최신 기사 1초 100건 수집, 완전 무료 / API키 불필요)
  - **실시간 웹 검색**: Google Serper + DuckDuckGo (정밀 Google 검색 엔진 + DDG 무제한 무료 Fallback, 무료 티어 + 오픈소스)
  - **웹 본문 추출기**: Jina Reader (`r.jina.ai`) (광고·CSS 제거 후 순수 마크다운 변환, Trafilatura 백업, 완전 무료)
  - **LLM (하이브리드)**: Gemini 2.5 + 로컬 Ollama (Fast Tier + Deep Tier 가성비 극대화, API 프리티어 + 로컬 무료)

---

### [Slide 8] 구현 4단계 로드맵 및 향후 추진 계획
- **배경 톤**: Deep Dark Navy (`#0F172A`)
- **Category Tag**: `PROJECT ROADMAP & NEXT ACTIONS`
- **Main Title**: 구현 4단계 로드맵 및 즉시 착수 계획
- **단계별 상세**:
  - **PHASE 1. 코어 Provider 구축 (▶ 즉시 착수)**
    - RSS 수집 모듈 (한경 타겟)
    - 하이브리드 검색 모듈 (Serper + DDG)
    - 3단계 스크래퍼 (Jina + 로컬)
    - LLM 팩토리 & 디스크 캐시 및 단위 테스트 검증
  - **PHASE 2. Graph 1 구현 (대기)**
    - TopicOutlineGraph 노드 작성
    - 한경 뉴스 클러스터링 프롬프트
    - A/B/C 복수 아웃라인 생성기 및 대화형 CLI UI
  - **PHASE 3. Graph 2 구현 (대기)**
    - DLSResearchGraph 상태 머신
    - 질문 분해 & 균형 쿼리 노드
    - Self-Reflection 검증 루프 & 경제 정량 통계 표 추출
  - **PHASE 4. E2E 검증 & 발행 (대기)**
    - 최신 경제 이슈 실제 리서치 수행
    - 최종 `output/{run_id}.md` 팩트 정확도 및 각주 매핑 확인
    - Notion 원클릭 발행 연동 및 완료 보고
