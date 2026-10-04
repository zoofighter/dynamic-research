import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    # 16:9 와이드스크린 설정 (13.333 x 7.5 inches)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6] # 완전히 빈 슬라이드

    # 색상 팔레트
    C_BG_DARK = RGBColor(15, 23, 42)       # #0F172A Slate 900
    C_BG_LIGHT = RGBColor(248, 250, 252)   # #F8FAFC Slate 50
    C_CARD_BG = RGBColor(255, 255, 255)    # White
    C_CARD_BORDER = RGBColor(226, 232, 240)# #E2E8F0 Slate 200
    C_PRIMARY = RGBColor(37, 99, 235)      # #2563EB Blue 600
    C_SECONDARY = RGBColor(14, 165, 233)   # #0EA5E9 Sky 500
    C_ACCENT = RGBColor(16, 185, 129)      # #10B981 Emerald 500
    C_TEXT_DARK = RGBColor(30, 41, 59)     # #1E293B Slate 800
    C_TEXT_MUTED = RGBColor(100, 116, 139) # #64748B Slate 500
    C_TEXT_LIGHT = RGBColor(241, 245, 249) # #F1F5F9 Slate 100

    def add_header(slide, title_text, category_text="자율 리서치 AGENT (DYNAMIC RESEARCH)"):
        # 상단 배경 바 또는 태그
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(11.7), Inches(0.4))
        tf = tag_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = category_text.upper()
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_PRIMARY

        # 타이틀
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.7), Inches(0.8))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_t = tf_title.paragraphs[0]
        p_t.text = title_text
        p_t.font.size = Pt(24)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_DARK

    def set_slide_background(slide, color):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    # ==========================================
    # SLIDE 1: 표지 (Cover)
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, C_BG_DARK)

    # 표지 장식용 카드/라인
    accent_bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(1.8), Inches(1.5), Inches(0.08))
    accent_bar.fill.solid()
    accent_bar.fill.fore_color.rgb = C_SECONDARY
    accent_bar.line.fill.background()

    # 태그
    tag_box = s1.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(10), Inches(0.5))
    tf = tag_box.text_frame
    p = tf.paragraphs[0]
    p.text = "NEXT-GEN AI RESEARCH ARCHITECTURE"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_SECONDARY

    # 메인 타이틀
    title_box = s1.shapes.add_textbox(Inches(1.2), Inches(2.6), Inches(11), Inches(1.8))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "자율 리서치 Agent 시스템"
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)

    p2 = tf.add_paragraph()
    p2.text = "Dynamic Live Search & Human-in-the-Loop 아키텍처"
    p2.font.size = Pt(24)
    p2.font.color.rgb = RGBColor(203, 213, 225)
    p2.space_before = Pt(12)

    # 설명 카드
    desc_box = s1.shapes.add_textbox(Inches(1.2), Inches(4.8), Inches(10.8), Inches(1.5))
    tf_desc = desc_box.text_frame
    tf_desc.word_wrap = True
    p_desc = tf_desc.paragraphs[0]
    p_desc.text = "사전 벡터 DB(RAG)의 시점 한계를 극복하는 100% 실시간 웹 심층 탐색과\n인간-AI 협업(HITL) 기반의 고신뢰성 심층 보고서 자율 생성 플랫폼"
    p_desc.font.size = Pt(16)
    p_desc.font.color.rgb = RGBColor(148, 163, 184)
    p_desc.line_spacing = 1.3

    # 메타 정보 (작성일 / 프로젝트)
    meta_box = s1.shapes.add_textbox(Inches(1.2), Inches(6.4), Inches(8), Inches(0.5))
    tf_meta = meta_box.text_frame
    p_meta = tf_meta.paragraphs[0]
    p_meta.text = "프로젝트: c_1003_dyanmic_research   |   일자: 2026. 10. 04   |   버전: v1.0"
    p_meta.font.size = Pt(12)
    p_meta.font.color.rgb = RGBColor(100, 116, 139)

    # ==========================================
    # SLIDE 2: 문제 정의 및 추진 배경 (Why)
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2, C_BG_LIGHT)
    add_header(s2, "왜 기존 RAG가 아닌 'Dynamic Live Search'인가?")

    # 3개 카드 레이아웃
    card_w = Inches(3.64)
    card_h = Inches(5.0)
    card_y = Inches(1.8)

    cards_data_s2 = [
        {
            "num": "01",
            "title": "사전 임베딩(RAG)의 한계",
            "subtitle": "어제의 데이터로는 오늘을 분석 불가",
            "desc": "• 벡터 DB 구축 및 청킹·임베딩 파이프라인의 높은 비용과 지연\n• 매일 급변하는 최신 시사/경제/기술 이슈에 대응 불가\n• '고정된 지식 창고'에 갇혀 실시간 웹의 최신 정보를 반영하지 못함",
            "color": RGBColor(239, 68, 68)
        },
        {
            "num": "02",
            "title": "맹목적 전면 자동화의 함정",
            "subtitle": "원하지 않는 방향으로 산으로 가는 리포트",
            "desc": "• 사용자 의도와 관점(Angle)이 배제된 일방적 보고서 출력\n• 목차(Outline)가 엉뚱하면 수백 번의 검색도 무용지물\n• 인간이 핵심 방향타를 쥐는 'Human-in-the-Loop' 개입이 필수적",
            "color": RGBColor(245, 158, 11)
        },
        {
            "num": "03",
            "title": "출처 불투명 & 환각(Hallucination)",
            "subtitle": "근거 없는 AI 주장은 신뢰할 수 없음",
            "desc": "• 출처 URL과 기사 본문 매핑 없는 요약문은 검증 불가능\n• 팩트(Fact)와 AI 해석(Analysis)이 뒤섞여 비즈니스 의사결정 위험\n• 엄격한 인라인 각주와 원문 마크다운 대조 체계 필요",
            "color": C_PRIMARY
        }
    ]

    for i, c in enumerate(cards_data_s2):
        card_x = Inches(0.8 + i * 4.0)
        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, card_x, card_y, card_w, card_h)
        card.fill.solid()
        card.fill.fore_color.rgb = C_CARD_BG
        card.line.color.rgb = C_CARD_BORDER
        card.line.width = Pt(1)

        # 번호 태그
        num_box = s2.shapes.add_textbox(card_x + Inches(0.3), card_y + Inches(0.3), Inches(3.0), Inches(0.5))
        tf = num_box.text_frame
        p = tf.paragraphs[0]
        p.text = c["num"]
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = c["color"]

        # 카드 제목
        t_box = s2.shapes.add_textbox(card_x + Inches(0.3), card_y + Inches(0.85), Inches(3.0), Inches(0.9))
        tf = t_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = c["title"]
        p.font.size = Pt(17)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_DARK

        p_sub = tf.add_paragraph()
        p_sub.text = c["subtitle"]
        p_sub.font.size = Pt(11)
        p_sub.font.color.rgb = C_TEXT_MUTED
        p_sub.space_before = Pt(4)

        # 내용
        d_box = s2.shapes.add_textbox(card_x + Inches(0.3), card_y + Inches(2.0), Inches(3.0), Inches(2.7))
        tf = d_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = c["desc"]
        p.font.size = Pt(12)
        p.font.color.rgb = C_TEXT_DARK
        p.line_spacing = 1.35

    # ==========================================
    # SLIDE 3: 핵심 아키텍처 - 2-Agent / 2-Graph 구조
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3, C_BG_LIGHT)
    add_header(s3, "2-Agent 분리 파이프라인: 인간 승인 기반의 느슨한 결합")

    # 상단 안내 바
    info_box = s3.shapes.add_textbox(Inches(0.8), Inches(1.7), Inches(11.733), Inches(0.6))
    tf = info_box.text_frame
    p = tf.paragraphs[0]
    p.text = "※ 사람의 검토가 필수적인 '기획 영역'과 완전 자율 실행되는 '심층 조사 영역'을 독립 LangGraph로 분리"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    # Graph 1 카드
    g1_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.4), Inches(5.3), Inches(4.5))
    g1_card.fill.solid()
    g1_card.fill.fore_color.rgb = C_CARD_BG
    g1_card.line.color.rgb = C_SECONDARY
    g1_card.line.width = Pt(2)

    tb = s3.shapes.add_textbox(Inches(1.1), Inches(2.6), Inches(4.7), Inches(4.0))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Graph 1: TopicOutlineGraph"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    p_sub = tf.add_paragraph()
    p_sub.text = "주제 발굴 & 복수 아웃라인 제안 (HITL 인터랙션)"
    p_sub.font.size = Pt(12)
    p_sub.font.color.rgb = C_TEXT_MUTED
    p_sub.space_before = Pt(4)

    steps_g1 = [
        "1. 뉴스/과거글 스캔: 한경 최신 기사 100건 + 과거 리포트",
        "2. LLM 클러스터링: 핫 트렌드 분석 및 쓸 만한 주제 5개 도출",
        "3. 아웃라인 생성: 독자 수준별 A/B/C 복수 목차 기획",
        "4. Human Review (Interrupt): 터미널에서 선택·수정·승인",
        "▶ 산출물: approved_outline.json (표준 규격 목차)"
    ]
    for s in steps_g1:
        p_item = tf.add_paragraph()
        p_item.text = s
        p_item.font.size = Pt(12)
        p_item.font.color.rgb = C_TEXT_DARK
        p_item.space_before = Pt(8)

    # 연결 화살표 영역
    bridge_box = s3.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(6.25), Inches(4.3), Inches(0.8), Inches(0.6))
    bridge_box.fill.solid()
    bridge_box.fill.fore_color.rgb = C_ACCENT
    bridge_box.line.fill.background()

    # Graph 2 카드
    g2_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.2), Inches(2.4), Inches(5.3), Inches(4.5))
    g2_card.fill.solid()
    g2_card.fill.fore_color.rgb = C_CARD_BG
    g2_card.line.color.rgb = C_PRIMARY
    g2_card.line.width = Pt(2)

    tb2 = s3.shapes.add_textbox(Inches(7.5), Inches(2.6), Inches(4.7), Inches(4.0))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.text = "Graph 2: DLSResearchGraph"
    p2.font.size = Pt(18)
    p2.font.bold = True
    p2.font.color.rgb = C_PRIMARY

    p2_sub = tf2.add_paragraph()
    p2_sub.text = "동적 라이브 검색 & 자율 심층 리서치 엔진"
    p2_sub.font.size = Pt(12)
    p2_sub.font.color.rgb = C_TEXT_MUTED
    p2_sub.space_before = Pt(4)

    steps_g2 = [
        "1. 질문 분해 & 균형 쿼리: 찬반/리스크 포함 다각도 질의 생성",
        "2. 실시간 웹 검색: Google Serper + DuckDuckGo 하이브리드",
        "3. 원문 크롤링: Jina Reader 3단계 Fallback (마크다운 변환)",
        "4. Self-Reflection: 정보 충분성 자율 검증 및 재검색 루프",
        "5. 섹션별 집필 & 조립: 인라인 각주 및 참고문헌 표 1:1 매핑",
        "▶ 산출물: output/{run_id}.md (최종 심층 분석 보고서)"
    ]
    for s in steps_g2:
        p_item = tf2.add_paragraph()
        p_item.text = s
        p_item.font.size = Pt(12)
        p_item.font.color.rgb = C_TEXT_DARK
        p_item.space_before = Pt(8)

    # ==========================================
    # SLIDE 4: Graph 1 상세 - 주제 발굴 및 아웃라인 기획
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4, C_BG_LIGHT)
    add_header(s4, "Graph 1: AI 트렌드 발굴과 Human-in-the-Loop 승인")

    col_w = Inches(5.6)
    col_h = Inches(4.9)
    col_y = Inches(1.8)

    # 좌측 컬럼: 한경 뉴스 연동 및 주제 발굴
    card_l = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    card_l.fill.solid()
    card_l.fill.fore_color.rgb = C_CARD_BG
    card_l.line.color.rgb = C_CARD_BORDER

    tb_l = s4.shapes.add_textbox(Inches(1.1), col_y + Inches(0.3), col_w - Inches(0.6), col_h - Inches(0.6))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True
    p = tf_l.paragraphs[0]
    p.text = "실시간 뉴스 스캔 및 주제 발굴"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_DARK

    items_l = [
        "• 한국경제 오늘의 기사 수집 실측 검증 완료:",
        "  - Google News RSS (site:hankyung.com) 타겟팅",
        "  - 1초 만에 최신 기사 100건 무료·무차단 수집 성공",
        "  - 한경 직접 웹 호출 시 403 봇 차단 문제를 완벽 우회",
        "",
        "• 3대 소스 융합 클러스터링:",
        "  1) 최신 24~72시간 실시간 뉴스 헤드라인",
        "  2) output/ 폴더의 기존 작성 리포트 (중복 방지 & 후속 분석)",
        "  3) 사용자 관심 키워드 및 도메인",
        "",
        "• LLM 추천 결과: 지금 당장 작성할 가치가 있는 '핵심 주제 5개' 도출"
    ]
    for it in items_l:
        p_i = tf_l.add_paragraph()
        p_i.text = it
        p_i.font.size = Pt(12)
        p_i.font.color.rgb = C_TEXT_DARK

    # 우측 컬럼: 아웃라인 제안 및 HITL
    card_r = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    card_r.fill.solid()
    card_r.fill.fore_color.rgb = C_CARD_BG
    card_r.line.color.rgb = C_CARD_BORDER

    tb_r = s4.shapes.add_textbox(Inches(7.1), col_y + Inches(0.3), col_w - Inches(0.6), col_h - Inches(0.6))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "A/B/C 복수 목차 제안 & CLI 승인 인터랙터"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_DARK

    items_r = [
        "• 3가지 관점의 복수 아웃라인(Multi-Proposals):",
        "  - [A안: 산업/투자자 관점] 시장 규모, 밸류체인 수혜 기업, 리스크",
        "  - [B안: 기술/엔지니어링 관점] 기술적 한계, 대안 기술, 아키텍처 비교",
        "  - [C안: 정책/글로벌 관점] 각국 규제 동향, 표준화 경쟁, 거시 전망",
        "",
        "• 대화형 CLI 인터랙터 (Human-in-the-Loop):",
        "  - LangGraph의 interrupt() 기반 안전한 실행 일시정지",
        "  - 터미널 메뉴: [1] A안 승인  [2] B안 승인  [e] 직접 수정  [r] 재생성",
        "  - 사람이 방향을 확정한 직후 Graph 2 자율 리서치로 핸드오프"
    ]
    for it in items_r:
        p_i = tf_r.add_paragraph()
        p_i.text = it
        p_i.font.size = Pt(12)
        p_i.font.color.rgb = C_TEXT_DARK

    # ==========================================
    # SLIDE 5: Graph 2 상세 - DLS 심층 리서치 엔진
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5, C_BG_LIGHT)
    add_header(s5, "Graph 2: 동적 검색·크롤링·반성(Self-Reflection) 루프")

    # 4단계 가로 프로세스 카드
    p_w = Inches(2.7)
    p_h = Inches(5.0)
    p_y = Inches(1.8)

    process_data = [
        {
            "step": "STEP 1",
            "title": "질문 분해 & 균형 쿼리",
            "points": [
                "• 목차 소주제별로 검색 질문 분해",
                "• [편향 방지 쿼리]: 찬양 일색 방지를 위해 비판/리스크 쿼리 1개 이상 강제 생성",
                "• 한국어/영어 최적 키워드 확장"
            ]
        },
        {
            "step": "STEP 2",
            "title": "실시간 검색 & 크롤링",
            "points": [
                "• [검색 하이브리드]: Google Serper 최우선 + DDG 자동 Fallback",
                "• [3단계 크롤링 Fallback]: Jina Reader → Trafilatura → 검색 스니펫",
                "• 봇 차단/Paywall 대응 보장"
            ]
        },
        {
            "step": "STEP 3",
            "title": "자율 반성 (Self-Reflection)",
            "points": [
                "• 수집된 데이터의 충분성 자체 평가",
                "• 팩트 모호/데이터 부족 판정 시 보완 쿼리 자동 생성 후 재검색",
                "• 최대 3회 루프로 무한 루프 방지"
            ]
        },
        {
            "step": "STEP 4",
            "title": "섹션 합성 & 보고서 조립",
            "points": [
                "• 경제/산업 핵심 수치 표(Table) 추출",
                "• 팩트와 해석의 명확한 분리 서술",
                "• 인라인 각주([^1]) 및 하단 출처 표 자동 생성 완료"
            ]
        }
    ]

    for i, p_info in enumerate(process_data):
        px = Inches(0.8 + i * 3.0)
        card = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px, p_y, p_w, p_h)
        card.fill.solid()
        card.fill.fore_color.rgb = C_CARD_BG
        card.line.color.rgb = C_PRIMARY if i == 2 else C_CARD_BORDER
        card.line.width = Pt(2) if i == 2 else Pt(1)

        tb = s5.shapes.add_textbox(px + Inches(0.2), p_y + Inches(0.25), p_w - Inches(0.4), p_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True

        p_s = tf.paragraphs[0]
        p_s.text = p_info["step"]
        p_s.font.size = Pt(12)
        p_s.font.bold = True
        p_s.font.color.rgb = C_PRIMARY

        p_t = tf.add_paragraph()
        p_t.text = p_info["title"]
        p_t.font.size = Pt(16)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_DARK
        p_t.space_before = Pt(4)

        for pt in p_info["points"]:
            p_p = tf.add_paragraph()
            p_p.text = pt
            p_p.font.size = Pt(11.5)
            p_p.font.color.rgb = C_TEXT_DARK
            p_p.space_before = Pt(8)
            p_p.line_spacing = 1.3

    # ==========================================
    # SLIDE 6: 구현 전 11대 엔지니어링 보완 전략 (Pre-Review)
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6, C_BG_LIGHT)
    add_header(s6, "사전 점검을 통해 도출한 11대 핵심 엔지니어링 전략")

    # 4대 카테고리 카드 2x2 배치
    grid_w = Inches(5.6)
    grid_h = Inches(2.35)

    grids = [
        {
            "cat": "1. 실시간 데이터 수집 최적화",
            "items": [
                "• [한경 오늘의 기사]: Google News RSS 연동으로 1초 100건 무료·무차단 수집",
                "• [하이브리드 검색]: Google Serper (정밀) + DuckDuckGo (무료 Fallback)",
                "• [3단계 크롤링]: Jina Reader → Trafilatura (로컬) → 검색 스니펫"
            ],
            "x": Inches(0.8), "y": Inches(1.8)
        },
        {
            "cat": "2. 토큰 비용 & 지연시간 80% 절감",
            "items": [
                "• [State 메모리 압축]: 원문(1만 자) 대신 Key Evidence(500자)만 State 보관",
                "• [디스크 로컬 캐싱]: 검색 쿼리(24h), URL 크롤링(7일) 캐시로 즉각 응답",
                "• [섹션 에러 격리]: 특정 섹션 수집 오류 시에도 전체 파이프라인 무중단 진행"
            ],
            "x": Inches(6.8), "y": Inches(1.8)
        },
        {
            "cat": "3. LLM 3단 계층화 (Tiering)",
            "items": [
                "• [Fast Tier (Flash / Ollama 8B)]: 쿼리 생성, Self-Reflection 등 경량 반복 작업",
                "• [Standard Tier (Gemini Flash)]: 주제 발굴 및 다각도 목차 기획",
                "• [Deep Tier (Gemini Pro / Sonnet)]: 깊이 있는 분석, 섹션 집필 및 최종 조립"
            ],
            "x": Inches(0.8), "y": Inches(4.4)
        },
        {
            "cat": "4. 리포트 품질 및 사용성 혁신",
            "items": [
                "• [균형 쿼리 강제]: 찬반/리스크 쿼리를 생성하여 편향된 보고서 방지",
                "• [경제 정량 수치 표]: 기사 속 매출/점유율 등 핵심 통계를 마크다운 표로 추출",
                "• [대화형 CLI & Notion 연동]: 터미널 실시간 승인 및 Notion 원클릭 발행 지원"
            ],
            "x": Inches(6.8), "y": Inches(4.4)
        }
    ]

    for g in grids:
        card = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, g["x"], g["y"], grid_w, grid_h)
        card.fill.solid()
        card.fill.fore_color.rgb = C_CARD_BG
        card.line.color.rgb = C_CARD_BORDER

        tb = s6.shapes.add_textbox(g["x"] + Inches(0.2), g["y"] + Inches(0.15), grid_w - Inches(0.4), grid_h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p_c = tf.paragraphs[0]
        p_c.text = g["cat"]
        p_c.font.size = Pt(14)
        p_c.font.bold = True
        p_c.font.color.rgb = C_PRIMARY

        for it in g["items"]:
            p_i = tf.add_paragraph()
            p_i.text = it
            p_i.font.size = Pt(11)
            p_i.font.color.rgb = C_TEXT_DARK
            p_i.space_before = Pt(4)

    # ==========================================
    # SLIDE 7: 기술 스택 및 인프라 요약
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7, C_BG_LIGHT)
    add_header(s7, "시스템 기술 스택 및 개발 인프라 구성")

    # 테이블 형태 배치
    table_shape = s7.shapes.add_table(6, 4, Inches(0.8), Inches(1.8), Inches(11.733), Inches(4.8))
    table = table_shape.table

    table.columns[0].width = Inches(2.2)
    table.columns[1].width = Inches(3.2)
    table.columns[2].width = Inches(3.5)
    table.columns[3].width = Inches(2.833)

    headers = ["구분", "채택 기술 / 도구", "역할 및 선정 사유", "비용 / 라이선스"]
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_BG_DARK
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER

    rows_data = [
        ("오케스트레이션", "LangGraph v1.2+", "2-Graph 분리 상태 머신 및 interrupt() 기반 HITL 제어", "오픈소스 (무료)"),
        ("데이터 수집 (News)", "Google News RSS + feedparser", "한경(site:hankyung.com) 최신 기사 1초 100건 수집", "완전 무료 / API키 불필요"),
        ("실시간 웹 검색", "Google Serper + DuckDuckGo", "정밀 Google 검색 엔진 + DDG 무제한 무료 Fallback", "무료 티어 + 무료 오픈소스"),
        ("웹 본문 추출기", "Jina Reader (r.jina.ai)", "광고·CSS 제거 후 순수 마크다운 변환 (Trafilatura 백업)", "완전 무료"),
        ("LLM (하이브리드)", "Gemini 2.5 + 로컬 Ollama", "Fast(Flash/로컬 8B) + Deep(Gemini Pro) 가성비 극대화", "API 프리티어 + 로컬 무료")
    ]

    for i, row in enumerate(rows_data):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_CARD_BG if i % 2 == 0 else RGBColor(241, 245, 249)
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(11.5)
            p.font.color.rgb = C_TEXT_DARK
            if j == 0:
                p.font.bold = True
                p.alignment = PP_ALIGN.CENTER

    # ==========================================
    # SLIDE 8: 실행 로드맵 및 향후 일정 (Next Action)
    # ==========================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8, C_BG_DARK)

    # 헤더
    tag_box = s8.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(11.7), Inches(0.4))
    tf = tag_box.text_frame
    p = tf.paragraphs[0]
    p.text = "PROJECT ROADMAP & NEXT ACTIONS"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_SECONDARY

    title_box = s8.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.7), Inches(0.8))
    tf_title = title_box.text_frame
    p_t = tf_title.paragraphs[0]
    p_t.text = "구현 4단계 로드맵 및 즉시 착수 계획"
    p_t.font.size = Pt(24)
    p_t.font.bold = True
    p_t.font.color.rgb = RGBColor(255, 255, 255)

    # 4단계 카드
    phase_w = Inches(2.7)
    phase_h = Inches(4.8)
    phase_y = Inches(1.9)

    phases = [
        {
            "tag": "PHASE 1",
            "title": "코어 Provider 구축",
            "status": "▶ 즉시 착수 (Next)",
            "status_color": C_ACCENT,
            "tasks": [
                "• RSS 수집 모듈 (한경 타겟)",
                "• 하이브리드 검색 모듈 (Serper+DDG)",
                "• 3단계 스크래퍼 (Jina+로컬)",
                "• LLM 팩토리 & 디스크 캐시",
                "• 단위 테스트 검증"
            ]
        },
        {
            "tag": "PHASE 2",
            "title": "Graph 1 구현",
            "status": "대기",
            "status_color": C_TEXT_MUTED,
            "tasks": [
                "• TopicOutlineGraph 노드 작성",
                "• 한경 뉴스 클러스터링 프롬프트",
                "• A/B/C 복수 아웃라인 생성기",
                "• 대화형 CLI interrupt() UI",
                "• approved_outline.json 검증"
            ]
        },
        {
            "tag": "PHASE 3",
            "title": "Graph 2 구현",
            "status": "대기",
            "status_color": C_TEXT_MUTED,
            "tasks": [
                "• DLSResearchGraph 상태 머신",
                "• 질문 분해 & 균형 쿼리 노드",
                "• Self-Reflection 검증 루프",
                "• 경제 정량 통계 표 추출",
                "• 인라인 각주 & 조립 노드"
            ]
        },
        {
            "tag": "PHASE 4",
            "title": "E2E 검증 & 발행",
            "status": "대기",
            "status_color": C_TEXT_MUTED,
            "tasks": [
                "• 최신 경제 이슈 실제 리서치",
                "• 최종 output/{run_id}.md 검증",
                "• 팩트 정확도 및 각주 매핑 확인",
                "• Notion 원클릭 발행 연동",
                "• 프로젝트 완료 보고"
            ]
        }
    ]

    for i, ph in enumerate(phases):
        px = Inches(0.8 + i * 3.0)
        card = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px, phase_y, phase_w, phase_h)
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(30, 41, 59)
        card.line.color.rgb = C_PRIMARY if i == 0 else RGBColor(51, 65, 85)
        card.line.width = Pt(2) if i == 0 else Pt(1)

        tb = s8.shapes.add_textbox(px + Inches(0.2), phase_y + Inches(0.2), phase_w - Inches(0.4), phase_h - Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p_tag = tf.paragraphs[0]
        p_tag.text = ph["tag"]
        p_tag.font.size = Pt(12)
        p_tag.font.bold = True
        p_tag.font.color.rgb = C_SECONDARY

        p_t = tf.add_paragraph()
        p_t.text = ph["title"]
        p_t.font.size = Pt(16)
        p_t.font.bold = True
        p_t.font.color.rgb = RGBColor(255, 255, 255)
        p_t.space_before = Pt(4)

        p_st = tf.add_paragraph()
        p_st.text = ph["status"]
        p_st.font.size = Pt(11)
        p_st.font.bold = True
        p_st.font.color.rgb = ph["status_color"]
        p_st.space_before = Pt(6)

        for tk in ph["tasks"]:
            p_k = tf.add_paragraph()
            p_k.text = tk
            p_k.font.size = Pt(11.5)
            p_k.font.color.rgb = RGBColor(203, 213, 225)
            p_k.space_before = Pt(8)
            p_k.line_spacing = 1.3

    # 저장 경로
    output_path = "/Users/boon/Dropbox/03_code/c_1003_dyanmic_research/docs/dynamic_research_presentation_20261004.pptx"
    prs.save(output_path)
    print(f"Presentation saved to {output_path}")

if __name__ == "__main__":
    create_deck()
