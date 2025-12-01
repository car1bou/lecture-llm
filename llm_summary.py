# llm_summary.py
#
# - exaone3.5:7.8b로 "내용 요약만" 수행
# - 키워드는 LLM에 요청하지 않음
# - 반환값은 (summary_list, []) 형태로 유지해서 기존 호출부와 호환

import json
import requests

# ---------------------------
# Ollama 설정
# ---------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "exaone3.5:7.8b"   # 선택한 한국어 요약용 모델 이름


# ---------------------------
# 프롬프트 (요약 전용)
# ---------------------------

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


# ---------------------------
# summarize_with_ollama
# ---------------------------

def summarize_with_ollama(transcript: str):
    """
    전체 자막 -> (summary_list, keywords_list)

    - 키워드는 요청하지 않으므로 항상 빈 리스트 []를 반환
    - LLM 결과가 잘못되면 예외를 발생시켜 FastAPI로 전달
    """

    # 너무 길면 잘라서 보냄 (CPU/모델 부담 줄이기)
    clipped = transcript[:8000]

    # 중괄호 이스케이프 문제를 피하기 위해 format()을 쓰지 않고 문자열 결합
    prompt = (
        PROMPT_HEADER
        + "\n\n===== 강의 자막 시작 =====\n"
        + clipped
        + "\n===== 강의 자막 끝 =====\n"
    )

    # Ollama /api/chat 호출
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

    # HTTP 오류 검사
    resp.raise_for_status()
    data = resp.json()

    # Ollama 응답 구조: {"message": {"content": "..."}}
    raw = data["message"]["content"]

    # format="json" 옵션 때문에 raw 자체가 JSON 문자열이어야 함
    obj = json.loads(raw)

    summary = obj.get("summary")

    if summary is None:
        raise ValueError("LLM JSON에 'summary'가 없습니다.")

    # summary가 문자열일 수도 있으니 리스트로 정규화
    if isinstance(summary, str):
        summary = [summary]

    # 공백 제거 및 빈 항목 제거
    summary = [s.strip() for s in summary if str(s).strip()]

    if not summary:
        raise ValueError("LLM이 summary를 비워서 반환했습니다.")

    # 두 번째 반환값은 호출부 호환용으로 빈 리스트
    keywords: list[str] = []

    return summary, keywords
