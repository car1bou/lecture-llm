# whisper_cpp.py
#
# - whisper.cpp의 whisper-cli 바이너리를 호출해서 SRT 생성
# - 모델은 ggml-large-v3.bin 으로 고정
# - run_whisper_cpp_to_srt: audio.wav -> lecture.srt
# - srt_to_text: SRT 파일 -> 순수 텍스트

import os
import subprocess

# whisper.cpp 실행 파일과 모델 경로 (환경에 맞게 고정)
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

    # output_prefix는 .srt 확장자를 제거한 부분
    output_prefix, _ = os.path.splitext(srt_path)

    # 실행 파일/모델/오디오 존재 여부 체크
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

    # whisper-cli 실행 명령
    cmd = [
        WHISPER_BIN,
        "-m",
        WHISPER_MODEL_PATH,
        "-f",
        audio_path,
        "-l",
        "ko",          # 한국어 고정
        "-t",
        "4",           # 스레드 4개 (N150 4코어 기준)
        "-osrt",       # SRT 포맷 출력
        "-of",
        output_prefix,
    ]

    # stdout/stderr를 캡처하지 않고 바로 터미널로 보내서 진행 상황이 보이게 함
    proc = subprocess.Popen(cmd)
    ret = proc.wait()

    if ret != 0:
        raise RuntimeError(
            f"whisper.cpp 실행 실패 (exit={ret})\n"
            f"CMD: {' '.join(cmd)}\n"
        )

    # whisper-cli는 prefix + ".srt" 로 저장하므로 그 경로를 확인
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
            # 숫자 인덱스 줄 (1, 2, 3, ...)
            if stripped.isdigit():
                continue
            # 타임스탬프 줄 (00:00:00,000 --> 00:00:02,000)
            if "-->" in stripped:
                continue
            lines.append(stripped)

    return "\n".join(lines)
