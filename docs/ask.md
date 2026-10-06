폴더 읽고 프로젝트 개요를 오늘 날짜로 저장

- Dynamic Live Search 성능 테스트를 할 수 있는 방법 -> [llamaindex_integration_and_benchmarking_20261004.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/llamaindex_integration_and_benchmarking_20261004.md) 에 5대 정량/정성 평가 메트릭 및 A/B 테스트 프레임워크 정리 완료
주제 & 아웃라인 제안 에이전트 (Topic & Outline Proposer Agent) 개요

주제를 찾는 과정에서 ai 가 개입할 수 있는 부분 뉴스 검색 및 지난 글 검색 또는 블로그나 트위터 검색에서 주제를 제안하는 방식
AI 개입 방식: 최근 24~72시간 뉴스 헤드라인 50개를 수집 → LLM이 클러스터링 + 트렌드 요약 → "지금 쓸 만한 주제 5개" 제안

에이전트는 랭그래프로 구현하면 자세한 설계도 생성 저장

구현하기전에 추가적인 제안이나 보완해야 할 부분은 없는가 있으면 문서로 정리 -> [pre_implementation_review_20261004.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/pre_implementation_review_20261004.md) 에 7대 보완 제안 정리 완료

한경 같은 기사도 가능한가 -- 오늘의 기사 -> 우선 차단 리스크가 없고 안정적인 **Google News RSS만 단독 사용**하기로 결정 (한경 공식 RSS 직접 연동은 추후 TODO로 보류)

- Dynamic Live Search 와 agentic rag의 차이점 -> [dls_vs_agentic_rag_20261004.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/dls_vs_agentic_rag_20261004.md) 에 비교 분석 문서 저장 완료

- LlamaIndex 도입 효과 및 비도입 시와의 성능 측정 비교 방안 -> [llamaindex_integration_and_benchmarking_20261004.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/llamaindex_integration_and_benchmarking_20261004.md) 에 A/B 테스트 지표 및 프레임워크 설계 완료

- GitHub 저장소 생성 및 연동 완료 -> [zoofighter/dynamic-research](https://github.com/zoofighter/dynamic-research) (Public 리포지토리 생성, 원격 origin 연결 및 최초 커밋 푸시 완료)

- 구현계획서 및 테스트계획서 작성 -> [implementation_plan_20261004.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/implementation_plan_20261004.md) 및 [test_plan_20261004.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/test_plan_20261004.md) 에 상세 계획 수립 완료

- 심층리서치를 몇가지 보고서로 만드는 요건정의 -> [multi_report_generation_requirements_20261005.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/multi_report_generation_requirements_20261005.md) 에 4대 전문 보고서 패키지(경영진 1-Pager, 심층 기술보고서, 벤치마크 매트릭스, 리스크 진단서) 자동 생성 요건정의서 작성 완료

- 보고서 유형 다각화 분류 체계 및 확장 프레임워크 -> [report_taxonomies_and_expansion_20261005.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/report_taxonomies_and_expansion_20261005.md) 에 4차원 분류 체계(의사결정 목적별, 시간지평별, 전달매체별, 전문관점별) 및 확장 로드맵 문서화 완료

- 월스트리트 투자은행(IB) 스타일 에쿼티 리서치 보고서 요건정의 -> [wall_street_equity_research_requirements_20261005.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/wall_street_equity_research_requirements_20261005.md) 에 골드만삭스/모건스탠리 스타일 투자의견(Rating), 목표주가, 컨센서스 괴리(Variant Perception), 3개년 재무추정치, Bull/Base/Bear 밸류에이션 매트릭스 요건정의서 작성 완료

- 한국경제(Hankyung) 글로벌마켓 심층 기획 기사 자동 생성 요건정의 및 구현 -> [hankyung_article_generation_requirements_20261006.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/hankyung_article_generation_requirements_20261006.md) 에 `/Users/boon/a_0504_hanky/articles` 스타일의 헤드라인·부제, 현장감 리드문, 넘버링 서사(1. -> ①, ②), 전문가 코멘트 인용 및 저널리즘 기사 작성 요건정의 완료

- last30days-skill 기반 소셜 및 예측시장 인텔리전스 통합 요건정의 -> [last30days_integration_requirements_20261006.md](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/docs/last30days_integration_requirements_20261006.md) 에 Reddit/HN/Polymarket/GitHub/arXiv 30일 엄격 시계열 수집, 군중 참여도(Upvote/$ Volume) 가중 랭킹, 미디어 보도 전 폭발 직전 주제 감지(Pre-Media Breakout Discovery), 6호 신규 보고서(`06_last30days_social_brief.md`) 요건정의 완료