import json
import requests
OLLAMA_URL = ""
MODEL_NAME = "exaone3.5:7.8b"
PROMPT_HEADER = """
당신은 한국어 강의 내용을 요약하는 전문 도우미입니다.

아래 강의 자막을 읽고 다음 JSON 형식만 출력하십시오.

{
  "summary": [
    "핵심 요약 문장 1",
    "핵심 요약 문장 2",
    "핵심 요약 문장 3"
  ]
}

규칙:
- JSON 바깥의 텍스트, 코드블록, 설명은 절대 출력하지 마십시오.
- summary는 3~10문장 사이로, 강의 전체 흐름과 핵심 개념을 정확하게 요약합니다.
- 반드시 한국어로 작성합니다.
""".strip()

def summarize_with_ollama(transcript: str):
    """
    전체 자막 -> (summary_list, keywords_list)

    - 키워드는 요청하지 않으므로 항상 빈 리스트 []를 반환
    - LLM 결과가 잘못되면 예외를 발생시켜 FastAPI로 전달
    """
    clipped = transcript[:8000]
    prompt = (
        PROMPT_HEADER
        + "\n\n===== 강의 자막 시작 =====\n"
        + clipped
        + "\n===== 강의 자막 끝 =====\n"
    )

    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "format": "json",  # JSON-only 강제
        },
        timeout=(10, None),
    )

    resp.raise_for_status()
    data = resp.json()

    raw = data["message"]["content"]

    obj = json.loads(raw)

    summary = obj.get("summary")

    if summary is None:
        raise ValueError("LLM JSON에 'summary'가 없습니다.")

    if isinstance(summary, str):
        summary = [summary]

    summary = [s.strip() for s in summary if str(s).strip()]

    if not summary:
        raise ValueError("LLM이 summary를 비워서 반환했습니다.")

    keywords: list[str] = []

    return summary, keywords
