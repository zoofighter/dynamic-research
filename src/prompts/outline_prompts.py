OUTLINE_GENERATION_PROMPT = """당신은 리서치 보고서 목차 및 질문 설계 전문가입니다.
주어진 주제와 분석 결과를 바탕으로, 주제의 도메인(반도체 하드웨어, AI 소프트웨어/서비스, 플랫폼, 규제 등)에 맞춰 서로 다른 4가지 다각도 관점의 아웃라인 제안(Proposal A, B, C, D)을 작성하세요:
- A: 산업 및 비즈니스 전략 관점 (시장 규모, 고객사, 수익/과금 모델, GTM)
- B: 기술 아키텍처 및 공정/엔지니어링 관점 (하드웨어 공정/수율 또는 소프트웨어 모델 구조/성능 벤치마크)
- C: 경쟁 구도 및 생태계/파트너십 관점 (경쟁사 비교, 플랫폼/SaaS 대체 파급력, 밸류체인 재편)
- D: 규제·정책·투자 리스크 및 미래 전망 관점 (규제/법적 이슈, 안전성/저작권, 투자 판단 요인 및 1~3년 전망)

각 아웃라인은 3~4개의 섹션으로 구성되며, 각 섹션마다 반드시 구체적인 검증 질문(target_questions)과 기대 결론(expected_takeaway)을 포함해야 합니다.

[주제]: {topic}
[의도 분석]:
{analysis}

[출력 형식]
반드시 유효한 JSON 배열 형태로만 출력하세요 (코드블록 없이):
[
  {{
    "proposal_id": "A",
    "theme": "산업 및 비즈니스 전략 관점",
    "sections": [
      {{
        "section_id": "sec_1",
        "title": "섹션 제목",
        "target_questions": ["질문 1", "질문 2"],
        "expected_takeaway": "섹션에서 얻고자 하는 핵심 결론"
      }}
    ]
  }},
  {{
    "proposal_id": "B",
    "theme": "기술 아키텍처 및 공정/엔지니어링 관점",
    "sections": [
      {{
        "section_id": "sec_1",
        "title": "섹션 제목",
        "target_questions": ["질문 1", "질문 2"],
        "expected_takeaway": "섹션에서 얻고자 하는 핵심 결론"
      }}
    ]
  }},
  {{
    "proposal_id": "C",
    "theme": "경쟁 구도 및 생태계/파트너십 관점",
    "sections": [
      {{
        "section_id": "sec_1",
        "title": "섹션 제목",
        "target_questions": ["질문 1", "질문 2"],
        "expected_takeaway": "섹션에서 얻고자 하는 핵심 결론"
      }}
    ]
  }},
  {{
    "proposal_id": "D",
    "theme": "규제·정책·투자 리스크 및 미래 전망 관점",
    "sections": [
      {{
        "section_id": "sec_1",
        "title": "섹션 제목",
        "target_questions": ["질문 1", "질문 2"],
        "expected_takeaway": "섹션에서 얻고자 하는 핵심 결론"
      }}
    ]
  }}
]
"""

OUTLINE_REVISION_PROMPT = """당신은 아웃라인 기획자입니다.
사용자의 피드백을 반영하여 기존 아웃라인을 수정하세요.

[기존 아웃라인]:
{original_outline}

[사용자 피드백]:
{human_feedback}

[출력 형식]
반드시 수정된 sections 리스트가 포함된 유효한 JSON 형식으로만 출력하세요 (코드블록 없이):
{{
  "sections": [
    {{
      "section_id": "sec_1",
      "title": "수정된 섹션 제목",
      "target_questions": ["질문 1", "질문 2"],
      "expected_takeaway": "수정된 기대 결론"
    }}
  ]
}}
"""
