# web_app.py
#
# - /        : 업로드 폼 HTML
# - /upload : mp3/mp4 업로드 → ffmpeg로 wav 추출 → whisper.cpp로 SRT 생성
#             → SRT를 텍스트로 변환 → Ollama로 요약 (실패 시 전체 스크립트만)
#             → PDF 생성 후 바로 다운로드 응답

import io
import os
import shutil
import tempfile
import subprocess
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse

from whisper_cpp import run_whisper_cpp_to_srt, srt_to_text
from pdf_generator import generate_pdf_bytes
from llm_summary import summarize_with_ollama

app = FastAPI()


# 간단한 업로드 페이지 (기존에 따로 프론트가 있으면 이 부분은 무시해도 됨)
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return """
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Lecture Assistant</title>
      </head>
      <body>
        <h1>강의 요약 PDF 생성기</h1>
        <form action="/upload" method="post" enctype="multipart/form-data">
          <input type="file" name="file" accept=".mp3,.mp4,.m4a,.wav" />
          <button type="submit">업로드</button>
        </form>
      </body>
    </html>
    """


def _extract_audio_to_wav(src_path: str, dst_path: str) -> None:
    """
    ffmpeg로 mp3/mp4 등을 16kHz mono PCM wav로 변환한다.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        src_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        dst_path,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        stdout = proc.stdout.decode("utf-8", errors="ignore")
        stderr = proc.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"오디오 추출(ffmpeg) 중 오류가 발생했습니다.\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{stdout}\n"
            f"STDERR:\n{stderr}\n"
        )


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # 허용 확장자 체크 (필요하면 더 추가 가능)
    filename = file.filename or ""
    lower_name = filename.lower()
    if not any(lower_name.endswith(ext) for ext in [".mp3", ".mp4", ".m4a", ".wav"]):
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 파일 형식입니다. mp3/mp4/m4a/wav 만 업로드하세요.",
        )

    # 작업용 임시 디렉터리
    tmp_dir = tempfile.mkdtemp(prefix="lecture_")
    try:
        # 1) 업로드 파일 저장
        src_path = os.path.join(tmp_dir, "input" + os.path.splitext(lower_name)[1])
        with open(src_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 2) 오디오 wav 추출
        audio_path = os.path.join(tmp_dir, "audio.wav")
        try:
            _extract_audio_to_wav(src_path, audio_path)
        except Exception as e:
            # ffmpeg 실패 시 바로 에러 반환
            return JSONResponse(
                status_code=500,
                content={"detail": f"오디오 추출 중 오류가 발생했습니다: {e}"},
            )

        # 3) whisper.cpp로 SRT 생성
        srt_path = os.path.join(tmp_dir, "lecture.srt")
        try:
            generated_srt = run_whisper_cpp_to_srt(audio_path, srt_path)
        except Exception as e:
            # whisper 실패 시 에러 반환
            return JSONResponse(
                status_code=500,
                content={"detail": f"자막(SRT) 생성 중 오류가 발생했습니다: {e}"},
            )

        # 4) SRT → 순수 텍스트 (전체 스크립트)
        try:
            transcript = srt_to_text(generated_srt)
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": f"SRT 파싱 중 오류가 발생했습니다: {e}"},
            )

        # 5) Ollama로 요약 생성 (요약 실패해도 PDF는 반드시 생성)
        summary_sentences: List[str]
        try:
            summary_sentences = summarize_with_ollama(transcript)
            # 혹시 빈 결과가 올 경우 대비
            if not summary_sentences:
                summary_sentences = ["요약을 생성할 수 없습니다."]
        except Exception as e:
            # 요약 실패 시 전체 스크립트만 넣고 안내 문구
            summary_sentences = [
                "요약을 생성하는 중 오류가 발생하여 전체 스크립트만 포함합니다.",
                f"(내부 오류: {e})",
            ]

        # 6) PDF 생성
        try:
            pdf_bytes = generate_pdf_bytes(
                summary_sentences=summary_sentences,
                full_text=transcript,
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": f"PDF 생성 중 오류가 발생했습니다: {e}"},
            )

        # 7) PDF 다운로드 응답
        pdf_io = io.BytesIO(pdf_bytes)
        pdf_io.seek(0)

        headers = {
            "Content-Disposition": 'attachment; filename="lecture_summary.pdf"'
        }

        return StreamingResponse(
            pdf_io,
            media_type="application/pdf",
            headers=headers,
        )

    finally:
        # 임시 디렉터리 정리
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            # 실패해도 무시
            pass
