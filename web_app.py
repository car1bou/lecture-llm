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
    filename = file.filename or ""
    lower_name = filename.lower()
    if not any(lower_name.endswith(ext) for ext in [".mp3", ".mp4", ".m4a", ".wav"]):
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 파일 형식입니다. mp3/mp4/m4a/wav 만 업로드하세요.",
        )

    tmp_dir = tempfile.mkdtemp(prefix="lecture_")
    try:
        src_path = os.path.join(tmp_dir, "input" + os.path.splitext(lower_name)[1])
        with open(src_path, "wb") as f:
            content = await file.read()
            f.write(content)

        audio_path = os.path.join(tmp_dir, "audio.wav")
        try:
            _extract_audio_to_wav(src_path, audio_path)
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": f"오디오 추출 중 오류가 발생했습니다: {e}"},
            )

        srt_path = os.path.join(tmp_dir, "lecture.srt")
        try:
            generated_srt = run_whisper_cpp_to_srt(audio_path, srt_path)
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": f"자막(SRT) 생성 중 오류가 발생했습니다: {e}"},
            )

        try:
            transcript = srt_to_text(generated_srt)
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": f"SRT 파싱 중 오류가 발생했습니다: {e}"},
            )

        summary_sentences: List[str]
        try:
            summary_sentences = summarize_with_ollama(transcript)
            if not summary_sentences:
                summary_sentences = ["요약을 생성할 수 없습니다."]
        except Exception as e:
            summary_sentences = [
                "요약을 생성하는 중 오류가 발생하여 전체 스크립트만 포함합니다.",
                f"(내부 오류: {e})",
            ]

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
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass
