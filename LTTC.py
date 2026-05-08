"""
Copyright (c) 2026 Bishnu Mahali
Licensed under the MIT License. See LICENSE for details.

LTTC (Local Transcription & Timed Captions) Toolkit

Transcribe video/audio in under-supported languages into timed captions using OpenAI Whisper.

Requirements:
1. Python 3.x
2. ffmpeg installed on system (https://ffmpeg.org/)
3. pip install openai-whisper pysrt

Usage (after installation as CLI/module):

    lttc --lang bn --tc video.mp4

Options:
    --lang/-l <code> : language code (e.g., bn for Bengali, asr for Ashuri, etc)
    --tc             : create timed captions (SRT); default is on if not specified
    --model/-m <sz>  : Whisper model size (tiny, base, small, medium, large)
    --output/-o <f>  : output SRT filename
    -i/--interactive : interactive mode (as before)
    -h/--help        : print help

To install globally and use from anywhere, from this directory run:
    pip install .

This will let you invoke 'lttc' from any directory.
"""

import os
import sys
import argparse
import importlib
import shutil
import subprocess

PYTHON_DEPENDENCIES = {
    "whisper": "openai-whisper",
    "pysrt": "pysrt",
}

MODEL_SIZES = {"tiny", "base", "small", "medium", "large"}


def missing_python_dependencies():
    missing = []
    for module_name, package_name in PYTHON_DEPENDENCIES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_name)
    return missing


def install_python_dependencies(packages):
    command = [sys.executable, "-m", "pip", "install", *packages]
    print(f"[LTTC] Installing: {' '.join(packages)}")
    return subprocess.run(command).returncode == 0


def ensure_python_dependencies(auto_install=False):
    missing = missing_python_dependencies()
    if not missing:
        return True

    install_command = f"{sys.executable} -m pip install {' '.join(missing)}"
    print("[LTTC] Missing required Python package(s):")
    for package_name in missing:
        print(f"  - {package_name}")
    print(f"\n[LTTC] Install command:\n  {install_command}\n")

    should_install = auto_install
    if not should_install and sys.stdin.isatty():
        answer = input("Install missing Python package(s) now? [y/N]: ").strip().lower()
        should_install = answer in {"y", "yes"}

    if not should_install:
        print("[LTTC] Dependency installation skipped. Install the package(s), then run LTTC again.")
        return False

    if not install_python_dependencies(missing):
        print("[LTTC] Installation failed. Try running the install command above manually.")
        return False

    still_missing = missing_python_dependencies()
    if still_missing:
        print(f"[LTTC] Still missing after install: {', '.join(still_missing)}")
        return False

    print("[LTTC] Python dependencies are ready.")
    return True


def ensure_ffmpeg_available():
    if shutil.which("ffmpeg"):
        return True

    print("[LTTC] FFmpeg was not found on your system PATH.")
    print("[LTTC] Install FFmpeg, then make sure this command works:")
    print("  ffmpeg -version")
    print("\n[LTTC] Download: https://ffmpeg.org/download.html")
    return False

def extract_audio(video_path, audio_path):
    if not ensure_ffmpeg_available():
        return False

    print(f"[LTTC] Extracting audio from: {video_path}")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        audio_path,
    ]
    result = subprocess.run(command)
    if result.returncode != 0:
        print("[LTTC] Error extracting audio. Ensure the file is accessible and FFmpeg can read it.")
        return False
    return True

def transcribe_to_srt(audio_path, srt_path, model_size="base", lang="bn"):
    import whisper
    import pysrt

    print(f"[LTTC] Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)
    print(f"[LTTC] Transcribing audio (language: {lang})... (this may take a while)")
    result = model.transcribe(audio_path, language=lang)
    subs = pysrt.SubRipFile()
    for i, seg in enumerate(result['segments']):
        start = seg["start"]
        end = seg["end"]
        text = seg["text"].strip()
        sub = pysrt.SubRipItem(
            index=i+1,
            start=pysrt.SubRipTime(seconds=start),
            end=pysrt.SubRipTime(seconds=end),
            text=text
        )
        subs.append(sub)
    subs.save(srt_path, encoding="utf-8")
    print(f"[LTTC] SRT file saved as: {srt_path}")

def interactive_main():
    print("==== LTTC: Local Transcription & Timed Captions Toolkit ====")
    print("Transcribe audio or video to timed captions for under-supported languages.\n")
    if not ensure_python_dependencies():
        return
    if not ensure_ffmpeg_available():
        return

    while True:
        video_file = input("Enter the path to your video/audio file (or 'q' to quit): ").strip()
        if video_file.lower() == 'q':
            print("Exiting.")
            return
        if not os.path.isfile(video_file):
            print(f"File not found: {video_file}\n")
            continue

        lang = input("Enter language code (e.g. bn): ").strip() or "bn"
        default_srt = os.path.splitext(video_file)[0] + f".{lang}.srt"
        srt_file = input(f"Enter output SRT filename [{default_srt}]: ").strip() or default_srt

        default_model = "base"
        model_size = input(f"Choose Whisper model size ('tiny', 'base', 'small', 'medium', 'large') [{default_model}]: ").strip().lower() or default_model
        if model_size not in MODEL_SIZES:
            model_size = default_model

        temp_audio_file = "temp_audio.wav"
        if not extract_audio(video_file, temp_audio_file):
            print("Audio extraction failed. Please try again.\n")
            continue

        try:
            transcribe_to_srt(temp_audio_file, srt_file, model_size, lang)
        except Exception as e:
            print(f"An error occurred during transcription: {e}")
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            continue

        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)
        print(f"SRT file created: {srt_file}\n")

        repeat = input("Transcribe another file? (y/n): ").strip().lower()
        if repeat != 'y':
            print("Thank you for using LTTC.")
            break

def cli_main(argv=None):
    parser = argparse.ArgumentParser(
        prog="lttc",
        description="LTTC: Local Transcription & Timed Captions Toolkit"
    )
    parser.add_argument("input_file", nargs="?", help="Input audio/video file")
    parser.add_argument("--lang", "-l", default="bn", help="Language code for transcription (e.g. bn, asr)")
    parser.add_argument("--tc", action="store_true", help="Output timed captions (SRT). Default if not set.")
    parser.add_argument("--model", "-m", default="base", help="Whisper model (tiny, base, small, medium, large)")
    parser.add_argument("--output", "-o", help="Output SRT filename")
    parser.add_argument("--install-deps", action="store_true", help="Install missing Python dependencies without prompting")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args(argv)

    if not ensure_python_dependencies(auto_install=args.install_deps):
        sys.exit(1)
    if not ensure_ffmpeg_available():
        sys.exit(1)

    if args.interactive or not args.input_file:
        interactive_main()
        return

    input_file = args.input_file
    if not os.path.isfile(input_file):
        print(f"[LTTC] File not found: {input_file}")
        sys.exit(1)

    lang = args.lang
    model_size = args.model
    if model_size not in MODEL_SIZES:
        print(f"[LTTC] Invalid model size '{model_size}', falling back to 'base'.")
        model_size = "base"
    base, ext = os.path.splitext(input_file)
    out_srt = args.output or f"{base}.{lang}.srt"

    temp_audio_file = f"{base}.lttc_temp.wav"
    try:
        if not extract_audio(input_file, temp_audio_file):
            sys.exit(1)
        transcribe_to_srt(temp_audio_file, out_srt, model_size, lang)
    except Exception as e:
        print(f"[LTTC] Error during processing: {e}")
        sys.exit(2)
    finally:
        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)

def main():
    cli_main()

if __name__ == "__main__":
    main()
