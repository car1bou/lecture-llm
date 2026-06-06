import os
import subprocess

WHISPER_BIN = "/home/srooll/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL_PATH = "/home/srooll/whisper.cpp/models/ggml-large-v3.bin"


def run_whisper_cpp_to_srt(audio_path: str, srt_path: str) -> str:
    """
    whisper-cli를 호출해서 오디오 파일(audio_path)을 SRT 파일(srt_path)로 변환한다.

    - audio_path: 입력 wav 경로 (예: /tmp/.../audio.wav)
    - srt_path:   출력 srt 경로 (예: /tmp/.../lecture.srt)

    반환값: 실제 생성된 srt 경로
    """
    audio_path = os.path.abspath(audio_path)
    srt_path = os.path.abspath(srt_path)

    output_prefix, _ = os.path.splitext(srt_path)

    if not os.path.exists(WHISPER_BIN):
        raise FileNotFoundError(
            f"whisper.cpp 실행 파일을 찾을 수 없습니다: {WHISPER_BIN}"
        )
    if not os.path.exists(WHISPER_MODEL_PATH):
        raise FileNotFoundError(
            f"whisper.cpp 모델 파일을 찾을 수 없습니다: {WHISPER_MODEL_PATH}"
        )
    if not os.path.exists(audio_path):
        raise FileNotFoundError(
            f"오디오 파일을 찾을 수 없습니다: {audio_path}"
        )

    cmd = [
        WHISPER_BIN,
        "-m",
        WHISPER_MODEL_PATH,
        "-f",
        audio_path,
        "-l",
        "ko",       
        "-t",
        "4",          
        "-osrt",     
        "-of",
        output_prefix,
    ]

    proc = subprocess.Popen(cmd)
    ret = proc.wait()

    if ret != 0:
        raise RuntimeError(
            f"whisper.cpp 실행 실패 (exit={ret})\n"
            f"CMD: {' '.join(cmd)}\n"
        )

    generated_srt = output_prefix + ".srt"
    if not os.path.exists(generated_srt):
        raise FileNotFoundError(
            f"SRT 파일이 생성되지 않았습니다: {generated_srt}"
        )

    return generated_srt


def srt_to_text(srt_path: str) -> str:
    """
    SRT 자막 파일에서 순수 대사 텍스트만 뽑아서 한 문자열로 반환한다.
    - 인덱스 번호, 타임스탬프 줄은 제거.
    """
    srt_path = os.path.abspath(srt_path)
    if not os.path.exists(srt_path):
        raise FileNotFoundError(
            f"SRT 파일을 찾을 수 없습니다: {srt_path}"
        )

    lines = []
    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.isdigit():
                continue
            if "-->" in stripped:
                continue
            lines.append(stripped)

    return "\n".join(lines)
