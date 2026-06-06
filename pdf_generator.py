import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(
    TTFont("NanumGothic", "")
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

    if isinstance(summary_sentences, str):
        summary_list = [summary_sentences]
    else:
        summary_list = [str(s) for s in summary_sentences]
    if not isinstance(full_text, str):
        full_text = str(full_text)
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
        alignment=1,  
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
    story.append(Paragraph(_escape("강의 요약"), title_style))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(_escape("1. 요약"), heading_style))
    story.append(Spacer(1, 4 * mm))

    if summary_list:
        for s in summary_list:
            p = Paragraph(_escape("• " + s), body_style)
            story.append(p)
            story.append(Spacer(1, 2 * mm))
    else:
        story.append(Paragraph(_escape("요약 내용이 없습니다."), body_style))
    story.append(PageBreak())
    story.append(Paragraph(_escape("2. 전체 스크립트"), heading_style))
    story.append(Spacer(1, 4 * mm))
    for line in full_text.splitlines():
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2 * mm))
            continue
        story.append(Paragraph(_escape(line), body_style))
        story.append(Spacer(1, 1 * mm))
    doc.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
