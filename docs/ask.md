폴더 읽고 프로젝트 개요를 오늘 날짜로 저장

- Dynamic Live Search 성능 테스트를 할 수 있는 방법 -> [llamaindex_integration_and_benchmarking_20261004.md](file:///Users/boon/Dropbox/03_code/c_1003_dyanmic_research/docs/llamaindex_integration_and_benchmarking_20261004.md) 에 5대 정량/정성 평가 메트릭 및 A/B 테스트 프레임워크 정리 완료
주제 & 아웃라인 제안 에이전트 (Topic & Outline Proposer Agent) 개요

주제를 찾는 과정에서 ai 가 개입할 수 있는 부분 뉴스 검색 및 지난 글 검색 또는 블로그나 트위터 검색에서 주제를 제안하는 방식
AI 개입 방식: 최근 24~72시간 뉴스 헤드라인 50개를 수집 → LLM이 클러스터링 + 트렌드 요약 → "지금 쓸 만한 주제 5개" 제안

에이전트는 랭그래프로 구현하면 자세한 설계도 생성 저장

구현하기전에 추가적인 제안이나 보완해야 할 부분은 없는가 있으면 문서로 정리 -> [pre_implementation_review_20261004.md](file:///Users/boon/Dropbox/03_code/c_1003_dyanmic_research/docs/pre_implementation_review_20261004.md) 에 7대 보완 제안 정리 완료

한경 같은 기사도 가능한가 -- 오늘의 기사 -> 가능 (한국경제 공식 RSS `feedparser` 연동을 통한 무료·초고속 실시간 수집 아키텍처 확정)

- Dynamic Live Search 와 agentic rag의 차이점 -> [dls_vs_agentic_rag_20261004.md](file:///Users/boon/Dropbox/03_code/c_1003_dyanmic_research/docs/dls_vs_agentic_rag_20261004.md) 에 비교 분석 문서 저장 완료

- LlamaIndex 도입 효과 및 비도입 시와의 성능 측정 비교 방안 -> [llamaindex_integration_and_benchmarking_20261004.md](file:///Users/boon/Dropbox/03_code/c_1003_dyanmic_research/docs/llamaindex_integration_and_benchmarking_20261004.md) 에 A/B 테스트 지표 및 프레임워크 설계 완료