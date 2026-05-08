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

REPAIR_DEPENDENCIES = {
    "whisper": ["torch", "openai-whisper"],
    "pysrt": ["pysrt"],
}

MODEL_SIZES = {"tiny", "base", "small", "medium", "large"}


def in_virtual_environment():
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def print_venv_setup_help():
    print("[LTTC] Recommended isolated setup on Windows:")
    print('  py -3.10 -m venv .venv')
    print(r"  .\.venv\Scripts\Activate.ps1")
    print("  python -m pip install --upgrade pip")
    print("  python -m pip install torch --index-url https://download.pytorch.org/whl/cpu")
    print("  python -m pip install openai-whisper pysrt")
    print("\n[LTTC] Then run LTTC from the activated environment:")
    print('  python LTTC.py "path/to/video.mp4" --lang bn')


def dependency_status():
    missing = []
    broken = []
    for module_name, package_name in PYTHON_DEPENDENCIES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_name)
        except Exception as error:
            broken.append((module_name, package_name, error))
    return missing, broken


def missing_python_dependencies():
    missing, broken = dependency_status()
    for module_name, package_name, _ in broken:
        repair_packages = REPAIR_DEPENDENCIES.get(module_name, [package_name])
        missing.extend(repair_packages)
    return list(dict.fromkeys(missing))


def repair_python_dependencies(broken):
    packages = []
    for module_name, package_name, _ in broken:
        packages.extend(REPAIR_DEPENDENCIES.get(module_name, [package_name]))
    return list(dict.fromkeys(packages))


def pip_install_command(packages, repair=False):
    command = [sys.executable, "-m", "pip", "install"]
    if repair:
        command.extend(["--upgrade", "--force-reinstall"])
    command.extend(packages)
    return command


def format_command(command):
    return " ".join(f'"{part}"' if " " in part else part for part in command)


def install_python_dependencies(packages, repair=False):
    command = pip_install_command(packages, repair=repair)
    print(f"[LTTC] Installing: {' '.join(packages)}")
    return subprocess.run(command).returncode == 0


def print_dependency_report(missing, broken):
    if missing:
        print("[LTTC] Missing required Python package(s):")
        for package_name in missing:
            print(f"  - {package_name}")

    if broken:
        print("[LTTC] Installed package(s) found, but they failed to load:")
        for module_name, package_name, error in broken:
            print(f"  - {package_name} ({module_name}): {error}")
        print("\n[LTTC] On Windows, this often means PyTorch installed incompletely or from the wrong wheel.")
        print("[LTTC] Repairing Whisper will also reinstall torch.")
        if not in_virtual_environment():
            print("[LTTC] You are not inside a virtual environment, so global repair may conflict with other ML packages.")


def print_install_commands(missing, repair_packages):
    if missing:
        install_command = pip_install_command(missing)
        print(f"\n[LTTC] Install command:\n  {format_command(install_command)}")
    if repair_packages:
        repair_command = pip_install_command(repair_packages, repair=True)
        print(f"\n[LTTC] Repair command:\n  {format_command(repair_command)}")


def prompt_yes_no(message):
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(message).strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def prompt_text(message, default=None):
    try:
        value = input(message).strip()
    except EOFError:
        print("\n[LTTC] No interactive input available.")
        return None
    return value or default


def browse_for_media_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as error:
        print(f"[LTTC] File browser is not available: {error}")
        return None

    root = tk.Tk()
    root.withdraw()
    root.update()
    try:
        file_path = filedialog.askopenfilename(
            title="Select video or audio file",
            filetypes=[
                ("Media files", "*.mp4 *.mkv *.mov *.avi *.webm *.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
                ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm"),
                ("Audio files", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
                ("All files", "*.*"),
            ],
        )
    finally:
        root.destroy()

    return file_path or None


def prompt_input_file():
    try:
        value = input("Enter the path to your video/audio file, press Enter to browse, or type 'q' to quit: ").strip()
    except EOFError:
        print("\n[LTTC] No interactive input available.")
        return None

    if value:
        return value

    print("[LTTC] Opening file browser...")
    file_path = browse_for_media_file()
    if not file_path:
        print("[LTTC] No file selected.\n")
    return file_path


def ensure_python_dependencies(auto_install=False, auto_repair=False, allow_global_install=False):
    missing, broken = dependency_status()
    if not missing and not broken:
        return True

    repair_packages = repair_python_dependencies(broken)
    print_dependency_report(missing, broken)
    print_install_commands(missing, repair_packages)

    can_modify_environment = in_virtual_environment() or allow_global_install
    if (missing or repair_packages) and not can_modify_environment:
        print("\n[LTTC] Automatic dependency changes are disabled outside a virtual environment.")
        print("[LTTC] This protects other Python/ML projects from package conflicts.")
        print_venv_setup_help()
        print("\n[LTTC] Advanced override: add --allow-global-install if you intentionally want LTTC to modify global Python.")
        return False

    if missing:
        should_install = auto_install
        if not should_install:
            should_install = prompt_yes_no("\nInstall missing Python package(s) now? [y/N]: ")
        if not should_install:
            print("[LTTC] Dependency installation skipped. Install the package(s), then run LTTC again.")
            return False
        if not install_python_dependencies(missing):
            print("[LTTC] Installation failed. Try running the install command above manually.")
            return False

    if repair_packages:
        should_repair = auto_install or auto_repair
        if not should_repair:
            should_repair = prompt_yes_no("\nRepair broken Python package(s) now? [y/N]: ")
        if not should_repair:
            print("[LTTC] Dependency repair skipped. Run the repair command above, then try LTTC again.")
            return False
        if not install_python_dependencies(repair_packages, repair=True):
            print("[LTTC] Repair failed. Try running the repair command above manually.")
            return False

    still_missing, still_broken = dependency_status()
    if still_missing or still_broken:
        print("[LTTC] Some dependencies are still not ready.")
        print_dependency_report(still_missing, still_broken)
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
        video_file = prompt_input_file()
        if video_file is None:
            continue
        if video_file.lower() == 'q':
            print("Exiting.")
            return
        if not os.path.isfile(video_file):
            print(f"File not found: {video_file}\n")
            continue

        lang = prompt_text("Enter language code (e.g. bn): ", default="bn")
        if lang is None:
            return
        default_srt = os.path.splitext(video_file)[0] + f".{lang}.srt"
        srt_file = prompt_text(f"Enter output SRT filename [{default_srt}]: ", default=default_srt)
        if srt_file is None:
            return

        default_model = "base"
        model_size = prompt_text(
            f"Choose Whisper model size ('tiny', 'base', 'small', 'medium', 'large') [{default_model}]: ",
            default=default_model,
        )
        if model_size is None:
            return
        model_size = model_size.lower()
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

        repeat = prompt_text("Transcribe another file? (y/n): ", default="n")
        if repeat is None:
            return
        repeat = repeat.lower()
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
    parser.add_argument("--repair-deps", action="store_true", help="Repair broken Python dependencies without prompting")
    parser.add_argument("--allow-global-install", action="store_true", help="Allow dependency installs/repairs outside a virtual environment")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args(argv)

    if args.interactive or not args.input_file:
        if not sys.stdin.isatty() and not args.interactive:
            parser.print_help()
            return
        interactive_main()
        return

    if not ensure_python_dependencies(
        auto_install=args.install_deps,
        auto_repair=args.repair_deps,
        allow_global_install=args.allow_global_install,
    ):
        sys.exit(1)
    if not ensure_ffmpeg_available():
        sys.exit(1)

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
