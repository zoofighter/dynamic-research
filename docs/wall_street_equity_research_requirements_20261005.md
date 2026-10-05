# 요건정의서 — 월스트리트 투자은행(IB) 스타일 에쿼티 리서치 보고서 (Wall Street Equity Research Note)

> **문서 버전**: v1.0  
> **작성일자**: 2026-10-05  
> **상태**: 승인 대기 (Approved for Implementation)  
> **관련 프로젝트**: `c_1003_dynamic_research`  
> **관련 문서**:  
> - [docs/multi_report_generation_requirements_20261005.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/multi_report_generation_requirements_20261005.md) (4대 핵심 보고서 패키지 요건정의서)  
> - [docs/report_taxonomies_and_expansion_20261005.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/report_taxonomies_and_expansion_20261005.md) (보고서 다각화 분류 체계)  

---

## 1. 배경 및 도입 목적

### 1.1 배경
현재 DLS 시스템은 산업·기술적 관점의 사실 검증과 경영진 전략 분석에 특화되어 있으나, **금융 시장 투자자, 펀드매니저, PE/IB 실무진**이 실제로 매일 소비하는 **월스트리트(Goldman Sachs, Morgan Stanley, J.P. Morgan, Bernstein) 스타일의 주식 분석 보고서(Equity Research Note)** 포맷은 부재한 상태입니다.

월스트리트 보고서는 일반 기술 리포트와 달리 다음의 독보적인 정보 소비 패턴을 가집니다:
1. **투자의견(Rating)과 목표주가(Target Price), 주가 상승여력(Upside)**이 첫 페이지 최상단에 즉시 박혀 있어야 함.
2. 시장 컨센서스(Street Consensus)와 분석가 전망치 간의 **괴리(Variance & Gap)**를 명확히 짚어 주가가 왜 오를/내릴 것인지(Catalyst)를 설득해야 함.
3. 과거 실적과 미래 3개년 **재무 추정치(Financial Summary: 매출, 영업이익률, EPS, P/E 배수)** 요약표가 필수적임.
4. **Bull / Base / Bear 3단계 시나리오별 목표 밸류에이션**을 제공하여 하방 위험과 상방 잠재력을 동시 제시해야 함.

### 1.2 도입 목적
* DLS가 실시간 검색·검증한 산업 팩트 데이터를 바탕으로, 글로벌 투자은행(IB) 수준의 **"Wall Street Equity Research Note"**를 5번째 전문 보고서 유형으로 표준화하여 자동 생성·패키징한다.

---

## 2. 월스트리트 리서치 리포트 표준 구조 및 레이아웃

```text
========================================================================================
[INVESTMENT BANK LOGO / HEADER]
TICKER: 005930.KS (Samsung Electronics) | SECTOR: Global Semiconductors & Hardware
RATING: OVERWEIGHT (BUY) | TARGET PRICE: KRW 115,000 | UPSIDE: +38.5%
CURRENT PRICE: KRW 83,000 | MARKET CAP: $420B | 52-WK RANGE: KRW 65,000 - 88,000
========================================================================================

# 🏛️ [Wall Street Equity Research] {Company / Topic}
## "The Inflection Point: HBM4 Margin Premium Driving Multiple Expansion"

1. 🎯 Executive Investment Thesis (핵심 투자 논거 3대 축)
2. 🥊 What's Priced In vs. Our Variant Perception (시장 컨센서스 vs 우리의 차별화 뷰)
3. 📊 Financial Estimates & Key Metric Highlights (향후 3개년 실적 추정치 요약표)
4. 🗓️ Catalysts & Milestone Calendar (향후 6~12개월 주가 촉매제 일정표)
5. ⚖️ Scenario Valuation Matrix (Bull / Base / Bear 목표주가 및 멀티플)
6. ⚠️ Key Downside Risks to Price Target (주가 하방 리스크 요인)
7. 📜 Analyst Certification & Disclaimer (컴플라이언스 면책 공시)
```

---

## 3. 세부 기능 요건 (Functional Requirements)

### FR-WS-01. 월가 헤더 및 투자 지표 자동 추출 (Header & Rating Block)
* **설명**: 수집된 뉴스/보고서 데이터에서 대상 기업의 티커, 업종, 현재 이슈를 식별하고 표준화된 헤더 블록을 구성한다.
* **구성 필드**:
  * `Rating`: `BUY / OVERWEIGHT` (비중확대), `HOLD / NEUTRAL` (중립), `SELL / UNDERWEIGHT` (비중축소) 중 데이터 분위기(수율, 점유율, 퀄 통과 등)에 기반하여 논리적 판정.
  * `Target Valuation Bias`: 밸류에이션 목표 멀티플(예: Target P/E 15.0x, EV/EBITDA 8.5x).
  * `Upside / Downside Band`: 기본 케이스 기준 주가 변동 기대치(+20~40%).
  * `Analyst Takeaway Subtitle`: "한 줄 투자 헤드라인" (예: *HBM4 턴키 내재화로 밸류에이션 리레이팅 진입*).

### FR-WS-02. 시장 컨센서스 대비 차별화 뷰 분석 (Variant Perception)
* **설명**: 시장의 일반적인 시각(The Street Consensus)과 본 리포트의 팩트 분석이 갖는 차별점(Why We Differ)을 대조 서술.
* **필수 포함 항목**:
  * **Consensus View (시장 우려/기대)**: 예) "HBM 퀄 지연 및 파운드리 적자로 상단 제한."
  * **Our Differentiated View (우리의 시각)**: 예) "엔비디아 SiP 테스트 1위 및 고마진 NVL72 단독 공급으로 ASP +121% 사이클에서 마진 폭증 간과."
  * **Surprise Factor (실적 어닝 서프라이즈 요인)**: 예상보다 빠른 수율 80% 달성 및 턴키 믹스 개선.

### FR-WS-03. 재무 추정 요약표 생성 (Financial Estimates Summary Matrix)
* **설명**: 본문에 등장한 정량 수치(매출, 영업이익, 생산 Capa, ASP 등)를 바탕으로 4개년(FY-1, FY, FY+1, FY+2) 표준 재무 지표 테이블을 조립.
* **표준 지표 양식**:
  | Financial Metric | FY24A (전년) | FY25E (금년 추정) | FY26E (차기년 추정) | FY27E (로드맵) |
  |---|---|---|---|---|
  | **Total Revenue (매출액)** | 실적치 | 추정치 | 추정치 | 슈퍼사이클 반영치 |
  | **Operating Profit (영업이익)** | 실적치 | 추정치 | 추정치 | 추정치 |
  | **OPM (%) (영업이익률)** | % | % | % (프리미엄 반영) | % |
  | **HBM Blended ASP ($/GB)** | 기준가 | +20% | +50% | +121% (TrendForce) |
  | **Implied P/E Multiple** | 12.0x | 10.5x | 8.2x | 6.5x (리레이팅 이전) |

### FR-WS-04. Bull / Base / Bear 3단계 시나리오 밸류에이션
* **설명**: 투자자가 리스크-리워드(Risk/Reward Profile)를 정량적으로 계산할 수 있도록 3단계 시나리오 테이블 제시.
* **구성 내용**:
  * **Bull Case (상방 / 20~25% 확률)**:
    * 가정: 퀄 단독 승인, HBM4E 16단 선점, Capa 풀가동
    * 목표 배수 및 주가 상방 (+50% 이상)
  * **Base Case (기준 / 55~65% 확률)**:
    * 가정: 3사 분할 공급 속 상위 모델 점유, 점유율 35~40% 안착
    * 합리적 목표 배수 및 적정 주가 (+25~35%)
  * **Bear Case (하방 / 15~20% 확률)**:
    * 가정: 수율 불안정, 고객사 물량 삭감, 경쟁사 Capa 추격
    * 하방 지지선 및 주가 할인율 (-10~20%)

### FR-WS-05. 주가 촉매제 캘린더 (Catalyst Calendar)
* **설명**: 향후 주가의 단기/중기 변곡점을 촉발할 이벤트와 시점을 타임라인 형식으로 정리.
  * 예: `2026 Q3`: 엔비디아 Vera Rubin SiP 최종 퀄 통과 공시 여부
  * 예: `2026 Q4`: HBM4 12단 초도 양산 출하 및 분기 실적 믹스 반영
  * 예: `2027 H1`: 청주 M15X 팹 장비 반입 및 Capa 확장 가시화

---

## 4. 파일 저장 및 패키징 연동 요건

### 4.1 저장 파일 규격
* 번들 디렉토리 내 5번째 파일로 생성:
  * 경로: `output/bundles/bundle_{topic}_{timestamp}/05_wall_street_equity_note.md`
  * 아이콘: `🏛️` (Wall Street / Investment Banking)
  * 명칭: `월스트리트 에쿼티 리서치 노트 (Wall Street Equity Note)`

### 4.2 매니페스트 및 ZIP 연동
* `00_bundle_manifest.json`에 `05_wall_street_equity_note.md` 항목 추가
* `full_bundle.zip` 압축 대상에 자동 포함

### 4.3 Web UI (Streamlit) 연동
* `📑 완성된 리포트 열람실`의 번들 서브탭을 기존 4개에서 5개로 확장:
  * `[👔 1. 전략 브리프]`
  * `[🔬 2. 심층 기술보고서]`
  * `[📊 3. 경쟁사 벤치마크]`
  * `[⚠️ 4. 리스크 & DD]`
  * `[🏛️ 5. 월스트리트 IB 노트]` *(신규)*

---

## 5. 비기능 요건 (Non-Functional Requirements)

1. **투자 자문 면책 가드레일 (Regulatory Disclaimer)**:
   * 문서 최하단에 공인된 금융 면책 조항(Disclaimers: "본 문서는 AI 자율 리서치 시스템에 의해 공공 정보만을 바탕으로 시뮬레이션된 연구 목적의 자료이며, 실제 투자 권유나 금융 자문에 해당하지 않습니다")을 필수 강제 출력.
2. **정량 수치 왜곡 방지 (Data Integrity)**:
   * 주가 추정치 및 재무 수치는 허위 조작이 아닌, 원문 텍스트에서 언급된 시장조사기관(트렌드포스, 카운터포인트, 모건스탠리 등)의 수치를 최우선 인용.
3. **톤앤매너 (Wall Street Tone)**:
   * 전문적이고 격조 있는 영문/국문 혼용 금융 용어(Multiple Expansion, Inflection Point, Margin Dilution, Consensus Gap, Street View 등)를 자연스럽게 활용.

---

## 6. 기대 효과

1. **금융·투자 분석 실무 완벽 대응**: 기술 분석 중심의 AI 리포트를 금융 시장에서 실제 거래와 투자 판단에 즉시 활용 가능한 에쿼티 리서치 보고서로 승격.
2. **다차원 인텔리전스 패키지의 완성**:
   * 경영진 전략(1-Pager) ➔ 엔지니어링 기술(Deep-Dive) ➔ 사업개발 비교(Benchmark) ➔ 감사/리스크(Due-Diligence) ➔ **기관 투자/밸류에이션(Wall Street IB)**까지 5각 편대 완성.
