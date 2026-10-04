OUTLINE_GENERATION_PROMPT = """당신은 리서치 보고서 목차 및 질문 설계 전문가입니다.
주어진 주제와 분석 결과를 바탕으로, 서로 다른 관점의 아웃라인 제안(Proposal A, B) 2개를 작성하세요.
각 아웃라인은 3~4개의 섹션으로 구성되며, 각 섹션마다 반드시 구체적인 검증 질문(target_questions)과 기대 결론(expected_takeaway)을 포함해야 합니다.

[주제]: {topic}
[의도 분석]:
{analysis}

[출력 형식]
반드시 유효한 JSON 배열 형태로만 출력하세요 (코드블록 없이):
[
  {{
    "proposal_id": "A",
    "theme": "시장 및 경쟁 구도 중심",
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
    "theme": "기술 혁신 및 수율/양산 검증 중심",
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
