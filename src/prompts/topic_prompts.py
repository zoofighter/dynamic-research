TOPIC_DISCOVERY_PROMPT = """당신은 시장 트렌드와 기술 혁신을 포착하는 리서치 디렉터입니다.
아래 수집된 최신 뉴스 헤드라인들을 분석하여, 투자자 및 엔지니어가 깊이 있게 파고들 가치가 있는 심층 리서치 주제 5개를 제안하세요.

[사용자 관심 힌트/키워드]: {user_hint}

[최신 뉴스 헤드라인 목록]:
{news_headlines}

[기존 리포트 목록 (중복 방지용)]:
{past_reports}

[출력 형식]
반드시 유효한 JSON 배열 형태로만 출력하세요 (코드블록 없이):
[
  {{
    "topic_id": "T1",
    "title": "주제 명칭",
    "rationale": "선정 이유 및 시장의 긴급성",
    "related_sources_count": 3
  }},
  ...
]
"""

TOPIC_EXPANSION_PROMPT = """당신은 리서치 기획 전문가입니다.
선택된 주제에 대해 심층 리서치를 진행하기 위한 프레임워크와 의도를 분석하세요.

[선택된 주제]: {topic}
[사용자 원문 요청]: {user_input}

[출력 형식]
반드시 유효한 JSON 형식으로만 출력하세요 (코드블록 없이):
{{
  "topic": "{topic}",
  "target_audience": "주 독자층 (예: 반도체 펀드매니저, 전략기획팀 등)",
  "research_depth": "deep / overview",
  "key_controversies": ["핵심 논쟁점 1", "핵심 논쟁점 2"],
  "core_hypothesis": "리서치를 통해 확인하고자 하는 핵심 가설"
}}
"""
