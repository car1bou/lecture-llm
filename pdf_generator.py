# pdf_generator.py
#
# - summary_sentences: 요약 문장 리스트(List[str]) 또는 str
# - full_text: Whisper로 얻은 전체 스크립트 문자열(str)
# 를 받아 A4 PDF를 생성하여 bytes로 반환한다.

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 나눔고딕 TTF를 프로젝트 내 fonts 디렉터리에서 사용
# 경로: /home/srooll/lecture-llm/fonts/NanumGothic.ttf  (네가 직접 넣어둔 폰트)
pdfmetrics.registerFont(
    TTFont("NanumGothic", "/home/srooll/lecture-llm/fonts/NanumGothic.ttf")
)
BASE_FONT_NAME = "NanumGothic"


def _escape(text: str) -> str:
    """reportlab Paragraph에서 사용할 간단한 HTML escape."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def generate_pdf_bytes(summary_sentences, full_text: str) -> bytes:
    """
    summary_sentences: List[str] 또는 str
    full_text: 전체 스크립트 문자열

    반환값: PDF 파일의 바이너리(bytes)
    """

    # --- 타입 정리 (여기 때문에 'list has no attribute split' 에러가 났었음) ---
    # 요약: 항상 리스트로 만들어서 처리
    if isinstance(summary_sentences, str):
        summary_list = [summary_sentences]
    else:
        # 리스트라고 가정하고, 요소들을 전부 문자열로 변환
        summary_list = [str(s) for s in summary_sentences]

    # 전체 스크립트: 반드시 문자열
    if not isinstance(full_text, str):
        full_text = str(full_text)
    # ---------------------------------------------------------------------------

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName=BASE_FONT_NAME,
        fontSize=18,
        leading=22,
        alignment=1,  # 가운데 정렬
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName=BASE_FONT_NAME,
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName=BASE_FONT_NAME,
        fontSize=11,
        leading=14,
    )

    story = []

    # 1. 제목
    story.append(Paragraph(_escape("강의 요약"), title_style))
    story.append(Spacer(1, 10 * mm))

    # 2. 요약 섹션
    story.append(Paragraph(_escape("1. 요약"), heading_style))
    story.append(Spacer(1, 4 * mm))

    if summary_list:
        for s in summary_list:
            p = Paragraph(_escape("• " + s), body_style)
            story.append(p)
            story.append(Spacer(1, 2 * mm))
    else:
        story.append(Paragraph(_escape("요약 내용이 없습니다."), body_style))

    # 3. 페이지 나누기
    story.append(PageBreak())

    # 4. 전체 스크립트 섹션
    story.append(Paragraph(_escape("2. 전체 스크립트"), heading_style))
    story.append(Spacer(1, 4 * mm))

    # 전체 스크립트 full_text 를 줄 단위로 전부 넣기
    for line in full_text.splitlines():
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2 * mm))
            continue
        story.append(Paragraph(_escape(line), body_style))
        story.append(Spacer(1, 1 * mm))

    # PDF 빌드
    doc.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
