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
    --device <name>  : Whisper device (auto, cuda, cpu)
    --output/-o <f>  : output SRT filename
    --tui            : open the Textual terminal UI
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
import threading

PYTHON_DEPENDENCIES = {
    "whisper": "openai-whisper",
    "pysrt": "pysrt",
}

SARVAM_DEPENDENCIES = {
    "sarvamai": "sarvam-ai",
    "pysrt": "pysrt",
}

UI_DEPENDENCIES = {
    "rich": "rich",
    "textual": "textual",
}

REPAIR_DEPENDENCIES = {
    "whisper": ["torch", "openai-whisper"],
    "pysrt": ["pysrt"],
}

MODEL_SIZES = {"tiny", "base", "small", "medium", "large"}
BACKENDS = {"whisper", "sarvam"}
SARVAM_MODES = {"transcribe", "translate", "verbatim", "translit", "codemix"}
DEVICE_CHOICES = {"auto", "cpu", "cuda", "cuda:0"}
SARVAM_LANGUAGE_MAP = {
    "as": "as-IN",
    "bn": "bn-IN",
    "brx": "brx-IN",
    "doi": "doi-IN",
    "en": "en-IN",
    "gu": "gu-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
    "kok": "kok-IN",
    "ks": "ks-IN",
    "mai": "mai-IN",
    "ml": "ml-IN",
    "mni": "mni-IN",
    "mr": "mr-IN",
    "ne": "ne-IN",
    "od": "od-IN",
    "or": "od-IN",
    "pa": "pa-IN",
    "sa": "sa-IN",
    "sat": "sat-IN",
    "sd": "sd-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "ur": "ur-IN",
}


def in_virtual_environment():
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def print_venv_setup_help():
    print("[LTTC] Recommended isolated setup on Windows:")
    print('  py -3.10 -m venv .venv')
    print(r"  .\.venv\Scripts\Activate.ps1")
    print("  python -m pip install --upgrade pip")
    print("  python -m pip install torch --index-url https://download.pytorch.org/whl/cpu")
    print("  python -m pip install -r requirements.txt")
    print("\n[LTTC] Then run LTTC from the activated environment:")
    print('  python LTTC.py "path/to/video.mp4" --lang bn')


def dependency_status(dependencies=None):
    dependencies = dependencies or PYTHON_DEPENDENCIES
    missing = []
    broken = []
    for module_name, package_name in dependencies.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_name)
        except Exception as error:
            broken.append((module_name, package_name, error))
    return missing, broken


def missing_ui_dependencies():
    missing = []
    for module_name, package_name in UI_DEPENDENCIES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_name)
    return missing


def dependencies_for_backend(backend):
    if backend == "sarvam":
        return SARVAM_DEPENDENCIES
    return PYTHON_DEPENDENCIES


def missing_python_dependencies(dependencies=None):
    missing, broken = dependency_status(dependencies)
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


def ensure_python_dependencies(
    auto_install=False,
    auto_repair=False,
    allow_global_install=False,
    prompt=True,
    dependencies=None,
):
    missing, broken = dependency_status(dependencies)
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
        if not should_install and prompt:
            should_install = prompt_yes_no("\nInstall missing Python package(s) now? [y/N]: ")
        if not should_install:
            print("[LTTC] Dependency installation skipped. Install the package(s), then run LTTC again.")
            return False
        if not install_python_dependencies(missing):
            print("[LTTC] Installation failed. Try running the install command above manually.")
            return False

    if repair_packages:
        should_repair = auto_install or auto_repair
        if not should_repair and prompt:
            should_repair = prompt_yes_no("\nRepair broken Python package(s) now? [y/N]: ")
        if not should_repair:
            print("[LTTC] Dependency repair skipped. Run the repair command above, then try LTTC again.")
            return False
        if not install_python_dependencies(repair_packages, repair=True):
            print("[LTTC] Repair failed. Try running the repair command above manually.")
            return False

    still_missing, still_broken = dependency_status(dependencies)
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


def detect_hardware_acceleration():
    info = {
        "recommended": "cpu",
        "cuda_available": False,
        "cuda_device_count": 0,
        "cuda_devices": [],
        "error": None,
    }
    try:
        import torch
    except Exception as error:
        info["error"] = str(error)
        return info

    try:
        info["cuda_available"] = bool(torch.cuda.is_available())
        info["cuda_device_count"] = int(torch.cuda.device_count()) if info["cuda_available"] else 0
        for index in range(info["cuda_device_count"]):
            info["cuda_devices"].append(torch.cuda.get_device_name(index))
        if info["cuda_available"]:
            info["recommended"] = "cuda"
    except Exception as error:
        info["error"] = str(error)
    return info


def print_hardware_report():
    info = detect_hardware_acceleration()
    print("[LTTC] Hardware acceleration check:")
    if info["cuda_available"]:
        print(f"  CUDA: available ({info['cuda_device_count']} device(s))")
        for index, name in enumerate(info["cuda_devices"]):
            print(f"  - cuda:{index}: {name}")
        print("  Recommended device: cuda")
    else:
        print("  CUDA: not available to PyTorch")
        print("  Recommended device: cpu")
    if info["error"]:
        print(f"  Detection note: {info['error']}")
    return info


def resolve_whisper_device(device="auto"):
    requested = (device or "auto").lower()
    if requested == "auto":
        info = detect_hardware_acceleration()
        selected = info["recommended"]
        if selected == "cuda":
            devices = ", ".join(info["cuda_devices"]) or "CUDA device"
            print(f"[LTTC] Hardware acceleration available: {devices}. Using CUDA.")
        else:
            print("[LTTC] CUDA is not available to PyTorch. Using CPU.")
        return selected

    if requested.startswith("cuda"):
        info = detect_hardware_acceleration()
        if info["cuda_available"]:
            print(f"[LTTC] Using requested device: {requested}")
            return requested
        print(f"[LTTC] Requested {requested}, but CUDA is not available to PyTorch. Falling back to CPU.")
        return "cpu"

    print("[LTTC] Using CPU.")
    return "cpu"


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


def read_value(item, key, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def normalize_sarvam_language(lang):
    if not lang:
        return "bn-IN"
    if lang.lower() == "unknown":
        return "unknown"
    if "-" in lang:
        return lang
    return SARVAM_LANGUAGE_MAP.get(lang.lower(), lang)


def words_from_sarvam_timestamps(timestamps):
    if not timestamps:
        return []
    words = read_value(timestamps, "words", [])
    normalized = []
    for word in words or []:
        text = read_value(word, "word") or read_value(word, "text") or read_value(word, "value")
        start = read_value(word, "start_time_seconds", read_value(word, "start", None))
        end = read_value(word, "end_time_seconds", read_value(word, "end", None))
        if text is None or start is None or end is None:
            continue
        normalized.append({"text": str(text), "start": float(start), "end": float(end)})
    return normalized


def save_words_as_srt(words, transcript, srt_path, max_words=12, max_duration=5.0):
    import pysrt

    subs = pysrt.SubRipFile()
    if not words:
        text = (transcript or "").strip()
        if text:
            subs.append(
                pysrt.SubRipItem(
                    index=1,
                    start=pysrt.SubRipTime(seconds=0),
                    end=pysrt.SubRipTime(seconds=5),
                    text=text,
                )
            )
        subs.save(srt_path, encoding="utf-8")
        return

    chunk = []
    chunk_start = words[0]["start"]
    chunk_end = words[0]["end"]
    for word in words:
        would_be_long = word["end"] - chunk_start > max_duration
        would_be_many = len(chunk) >= max_words
        if chunk and (would_be_long or would_be_many):
            subs.append(
                pysrt.SubRipItem(
                    index=len(subs) + 1,
                    start=pysrt.SubRipTime(seconds=chunk_start),
                    end=pysrt.SubRipTime(seconds=chunk_end),
                    text=" ".join(chunk).strip(),
                )
            )
            chunk = []
            chunk_start = word["start"]
        chunk.append(word["text"])
        chunk_end = word["end"]

    if chunk:
        subs.append(
            pysrt.SubRipItem(
                index=len(subs) + 1,
                start=pysrt.SubRipTime(seconds=chunk_start),
                end=pysrt.SubRipTime(seconds=chunk_end),
                text=" ".join(chunk).strip(),
            )
        )

    subs.save(srt_path, encoding="utf-8")


def transcribe_to_srt(audio_path, srt_path, model_size="base", lang="bn", device="auto"):
    import whisper
    import pysrt

    resolved_device = resolve_whisper_device(device)
    print(f"[LTTC] Loading Whisper model: {model_size} on {resolved_device}")
    model = whisper.load_model(model_size, device=resolved_device)
    print(f"[LTTC] Transcribing audio (language: {lang}, device: {resolved_device})... (this may take a while)")
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


def transcribe_with_sarvam_to_srt(audio_path, srt_path, lang="bn", api_key=None, mode="transcribe"):
    from sarvamai import SarvamAI

    api_key = api_key or os.environ.get("SARVAM_API_KEY") or os.environ.get("SARVAM_API_SUBSCRIPTION_KEY")
    if not api_key:
        raise ValueError("Sarvam API key missing. Set SARVAM_API_KEY or pass --sarvam-api-key.")

    language_code = normalize_sarvam_language(lang)
    if mode not in SARVAM_MODES:
        mode = "transcribe"

    print(f"[LTTC] Transcribing with Sarvam Saaras v3 (language: {language_code}, mode: {mode})...")
    client = SarvamAI(api_subscription_key=api_key)
    with open(audio_path, "rb") as audio_file:
        response = client.speech_to_text.transcribe(
            file=audio_file,
            model="saaras:v3",
            mode=mode,
            language_code=language_code,
            with_timestamps=True,
        )

    transcript = read_value(response, "transcript", "")
    timestamps = read_value(response, "timestamps", None)
    words = words_from_sarvam_timestamps(timestamps)
    save_words_as_srt(words, transcript, srt_path)
    print(f"[LTTC] SRT file saved as: {srt_path}")


def transcribe_file_to_srt(
    input_file,
    out_srt,
    backend="whisper",
    model_size="base",
    lang="bn",
    sarvam_api_key=None,
    sarvam_mode="transcribe",
    device="auto",
):
    base, _ = os.path.splitext(input_file)
    temp_audio_file = f"{base}.lttc_temp.wav"
    try:
        if not extract_audio(input_file, temp_audio_file):
            return False
        if backend == "sarvam":
            transcribe_with_sarvam_to_srt(temp_audio_file, out_srt, lang, sarvam_api_key, sarvam_mode)
        else:
            transcribe_to_srt(temp_audio_file, out_srt, model_size, lang, device)
    finally:
        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)
    return True

def interactive_main():
    print("==== LTTC: Local Transcription & Timed Captions Toolkit ====")
    print("Transcribe audio or video to timed captions for under-supported languages.\n")
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
        backend = prompt_text("Choose backend ('whisper' or 'sarvam') [whisper]: ", default="whisper")
        if backend is None:
            return
        backend = backend.lower()
        if backend not in BACKENDS:
            backend = "whisper"
        default_srt = os.path.splitext(video_file)[0] + f".{lang}.srt"
        srt_file = prompt_text(f"Enter output SRT filename [{default_srt}]: ", default=default_srt)
        if srt_file is None:
            return

        default_model = "base"
        model_size = default_model
        device = "auto"
        sarvam_mode = "transcribe"
        sarvam_api_key = None
        if backend == "sarvam":
            sarvam_mode = prompt_text("Choose Sarvam mode ('transcribe', 'translate', 'verbatim', 'translit', 'codemix') [transcribe]: ", default="transcribe")
            if sarvam_mode is None:
                return
            sarvam_mode = sarvam_mode.lower()
            if sarvam_mode not in SARVAM_MODES:
                sarvam_mode = "transcribe"
            if not os.environ.get("SARVAM_API_KEY") and not os.environ.get("SARVAM_API_SUBSCRIPTION_KEY"):
                sarvam_api_key = prompt_text("Enter Sarvam API key (or set SARVAM_API_KEY): ")
                if sarvam_api_key is None:
                    return
        else:
            model_size = prompt_text(
                f"Choose Whisper model size ('tiny', 'base', 'small', 'medium', 'large') [{default_model}]: ",
                default=default_model,
            )
            if model_size is None:
                return
            model_size = model_size.lower()
            if model_size not in MODEL_SIZES:
                model_size = default_model
            device = prompt_text("Choose device ('auto', 'cuda', or 'cpu') [auto]: ", default="auto")
            if device is None:
                return
            device = device.lower()

        if not ensure_python_dependencies(dependencies=dependencies_for_backend(backend)):
            return
        if backend == "whisper":
            print_hardware_report()
        if not ensure_ffmpeg_available():
            return

        try:
            if not transcribe_file_to_srt(video_file, srt_file, backend, model_size, lang, sarvam_api_key, sarvam_mode, device):
                print("Audio extraction failed. Please try again.\n")
                continue
        except Exception as e:
            print(f"An error occurred during transcription: {e}")
            continue
        print(f"SRT file created: {srt_file}\n")

        repeat = prompt_text("Transcribe another file? (y/n): ", default="n")
        if repeat is None:
            return
        repeat = repeat.lower()
        if repeat != 'y':
            print("Thank you for using LTTC.")
            break


def run_tui():
    missing = missing_ui_dependencies()
    if missing:
        install_command = pip_install_command(missing)
        print("[LTTC] Missing terminal UI package(s):")
        for package_name in missing:
            print(f"  - {package_name}")
        print(f"\n[LTTC] Install command:\n  {format_command(install_command)}")
        print("\n[LTTC] Or install all project dependencies:")
        print("  python -m pip install -r requirements.txt")
        return 1

    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Button, Footer, Header, Input, Label, Log, Select, Static
    from rich.text import Text

    class LTTCApp(App):
        TITLE = "LTTC"
        SUB_TITLE = "Local Transcription & Timed Captions"
        CSS = """
        Screen {
            background: #071014;
            color: #f8fafc;
        }

        Header {
            background: #0f766e;
            color: #ecfeff;
            text-style: bold;
        }

        Footer {
            background: #111827;
            color: #93c5fd;
        }

        #shell {
            width: 94%;
            max-width: 110;
            height: auto;
            margin: 1 2;
        }

        #hero {
            height: 7;
            padding: 1 2;
            background: #102027;
            border: double #f59e0b;
        }

        #title {
            text-style: bold;
            color: #fef3c7;
        }

        #tagline {
            color: #67e8f9;
        }

        #hint {
            color: #fda4af;
        }

        #form {
            margin-top: 1;
            padding: 1 2;
            border: round #22c55e;
            background: #0f172a;
        }

        #log_panel {
            margin-top: 1;
            height: 14;
            color: #d1fae5;
            border: round #fb7185;
            background: #0b1120;
        }

        .field_label {
            margin-top: 1;
            color: #fcd34d;
            text-style: bold;
        }

        Input, Select {
            margin-top: 1;
            color: #e0f2fe;
            background: #111827;
            border: tall #2563eb;
        }

        Input:focus, Select:focus {
            border: tall #f97316;
            background: #172554;
        }

        Button {
            margin-top: 1;
            margin-right: 1;
            text-style: bold;
        }

        Button:hover {
            text-style: bold reverse;
        }

        #status {
            margin-top: 1;
            color: #86efac;
            text-style: bold;
            background: #052e16;
            border-left: thick #22c55e;
            padding: 0 1;
        }
        """

        def compose(self) -> ComposeResult:
            yield Header()
            with Container(id="shell"):
                with Vertical(id="hero"):
                    title = Text()
                    title.append("LTTC", style="bold #fef3c7")
                    title.append("  Local Transcription & Timed Captions", style="bold #5eead4")
                    yield Static(title, id="title")
                    tagline = Text()
                    tagline.append("Bengali-first", style="bold #f472b6")
                    tagline.append(" captioning with ", style="#cbd5e1")
                    tagline.append("Whisper", style="bold #93c5fd")
                    tagline.append(" or ", style="#cbd5e1")
                    tagline.append("Sarvam", style="bold #f472b6")
                    tagline.append(", local files, and SRT output.", style="#cbd5e1")
                    yield Static(tagline, id="tagline")
                    yield Static(
                        Text(
                            "Pick media, choose a model, generate timed captions.",
                            style="italic #fbbf24",
                        ),
                        id="hint",
                    )
                with Vertical(id="form"):
                    yield Label(Text("Input media", style="bold #fcd34d"), classes="field_label")
                    with Horizontal():
                        yield Input(placeholder="Choose a video/audio file or paste a path", id="input_file")
                        yield Button("Browse", id="browse", variant="primary")
                    yield Label(Text("Language code", style="bold #f472b6"), classes="field_label")
                    yield Input(value="bn", placeholder="bn", id="language")
                    yield Label(Text("Backend", style="bold #f97316"), classes="field_label")
                    yield Select(
                        [("Whisper local", "whisper"), ("Sarvam API", "sarvam")],
                        value="whisper",
                        id="backend",
                    )
                    yield Label(Text("Whisper model", style="bold #93c5fd"), classes="field_label")
                    yield Select(
                        [(model, model) for model in ["tiny", "base", "small", "medium", "large"]],
                        value="base",
                        id="model",
                    )
                    yield Label(Text("Whisper device", style="bold #67e8f9"), classes="field_label")
                    with Horizontal():
                        yield Select(
                            [("Auto", "auto"), ("CUDA", "cuda"), ("CPU", "cpu")],
                            value="auto",
                            id="device",
                        )
                        yield Button("Check Hardware", id="hardware", variant="warning")
                    yield Label(Text("Sarvam mode", style="bold #f472b6"), classes="field_label")
                    yield Select(
                        [(mode, mode) for mode in ["transcribe", "translate", "verbatim", "translit", "codemix"]],
                        value="transcribe",
                        id="sarvam_mode",
                    )
                    yield Label(Text("Sarvam API key", style="bold #fb7185"), classes="field_label")
                    yield Input(placeholder="Optional if SARVAM_API_KEY is set", password=True, id="sarvam_api_key")
                    yield Label(Text("Output SRT", style="bold #86efac"), classes="field_label")
                    yield Input(placeholder="Leave empty for input-file.bn.srt", id="output_file")
                    with Horizontal():
                        yield Button("Transcribe", id="transcribe", variant="success")
                        yield Button("Quit", id="quit", variant="error")
                    yield Static(Text("Ready", style="bold #86efac"), id="status")
                yield Log(id="log_panel", highlight=True)
            yield Footer()

        def on_mount(self) -> None:
            self.query_one("#input_file", Input).focus()
            self.write_log("Ready. Select a media file, choose a model, then transcribe.")

        def write_log(self, message):
            self.query_one("#log_panel", Log).write_line(str(message))

        def set_status(self, message, style="bold #86efac"):
            self.query_one("#status", Static).update(Text(message, style=style))

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "quit":
                self.exit()
                return
            if event.button.id == "browse":
                file_path = browse_for_media_file()
                if file_path:
                    self.query_one("#input_file", Input).value = file_path
                    output = self.query_one("#output_file", Input)
                    language = self.query_one("#language", Input).value.strip() or "bn"
                    output.value = os.path.splitext(file_path)[0] + f".{language}.srt"
                return
            if event.button.id == "hardware":
                info = detect_hardware_acceleration()
                if info["cuda_available"]:
                    devices = ", ".join(info["cuda_devices"]) or "CUDA device"
                    self.set_status(f"CUDA available: {devices}", "bold #86efac")
                    self.write_log(f"CUDA available: {devices}")
                else:
                    self.set_status("CUDA is not available to PyTorch.", "bold #fbbf24")
                    self.write_log("CUDA is not available to PyTorch. Whisper will use CPU.")
                    if info["error"]:
                        self.write_log(f"Hardware check note: {info['error']}")
                return
            if event.button.id == "transcribe":
                self.start_transcription()

        def start_transcription(self):
            input_file = self.query_one("#input_file", Input).value.strip()
            language = self.query_one("#language", Input).value.strip() or "bn"
            backend = self.query_one("#backend", Select).value or "whisper"
            model = self.query_one("#model", Select).value or "base"
            device = self.query_one("#device", Select).value or "auto"
            sarvam_mode = self.query_one("#sarvam_mode", Select).value or "transcribe"
            sarvam_api_key = self.query_one("#sarvam_api_key", Input).value.strip()
            output_file = self.query_one("#output_file", Input).value.strip()

            if not input_file:
                self.set_status("Choose an input file first.", "bold #fbbf24")
                self.write_log("Input file is required.")
                return
            if not os.path.isfile(input_file):
                self.set_status("Input file was not found.", "bold #fb7185")
                self.write_log(f"File not found: {input_file}")
                return
            if backend not in BACKENDS:
                backend = "whisper"
            if model not in MODEL_SIZES:
                model = "base"
            if sarvam_mode not in SARVAM_MODES:
                sarvam_mode = "transcribe"

            if not output_file:
                output_file = os.path.splitext(input_file)[0] + f".{language}.srt"
                self.query_one("#output_file", Input).value = output_file

            transcribe_button = self.query_one("#transcribe", Button)
            transcribe_button.disabled = True
            self.set_status("Working...", "bold #67e8f9")
            self.write_log(f"Input: {input_file}")
            self.write_log(f"Language: {language}")
            self.write_log(f"Backend: {backend}")
            if backend == "sarvam":
                self.write_log(f"Sarvam mode: {sarvam_mode}")
            else:
                self.write_log(f"Model: {model}")
                self.write_log(f"Device: {device}")
            self.write_log(f"Output: {output_file}")

            worker = threading.Thread(
                target=self.transcribe_worker,
                args=(input_file, output_file, backend, model, language, sarvam_api_key, sarvam_mode, device),
                daemon=True,
            )
            worker.start()

        def transcribe_worker(self, input_file, output_file, backend, model, language, sarvam_api_key, sarvam_mode, device):
            try:
                self.call_from_thread(self.write_log, "Checking dependencies...")
                if not ensure_python_dependencies(prompt=False, dependencies=dependencies_for_backend(backend)):
                    self.call_from_thread(self.set_status, "Dependencies are not ready.", "bold #fb7185")
                    return
                if not ensure_ffmpeg_available():
                    self.call_from_thread(self.set_status, "FFmpeg is not available.", "bold #fb7185")
                    return
                self.call_from_thread(self.write_log, "Extracting audio and transcribing...")
                if not transcribe_file_to_srt(
                    input_file,
                    output_file,
                    backend=backend,
                    model_size=model,
                    lang=language,
                    sarvam_api_key=sarvam_api_key or None,
                    sarvam_mode=sarvam_mode,
                    device=device,
                ):
                    self.call_from_thread(self.set_status, "Audio extraction failed.", "bold #fb7185")
                    return
            except Exception as error:
                self.call_from_thread(self.write_log, f"Error: {error}")
                self.call_from_thread(self.set_status, "Failed.", "bold #fb7185")
                return
            finally:
                self.call_from_thread(lambda: setattr(self.query_one("#transcribe", Button), "disabled", False))

            self.call_from_thread(self.write_log, "Done.")
            self.call_from_thread(self.set_status, f"Saved: {output_file}", "bold #86efac")

    LTTCApp().run()
    return 0


def cli_main(argv=None):
    parser = argparse.ArgumentParser(
        prog="lttc",
        description="LTTC: Local Transcription & Timed Captions Toolkit"
    )
    parser.add_argument("input_file", nargs="?", help="Input audio/video file")
    parser.add_argument("--lang", "-l", default="bn", help="Language code for transcription (e.g. bn, asr)")
    parser.add_argument("--tc", action="store_true", help="Output timed captions (SRT). Default if not set.")
    parser.add_argument("--backend", choices=sorted(BACKENDS), default="whisper", help="Transcription backend")
    parser.add_argument("--model", "-m", default="base", help="Whisper model (tiny, base, small, medium, large)")
    parser.add_argument("--device", default="auto", help="Whisper device: auto, cuda, cuda:0, or cpu")
    parser.add_argument("--output", "-o", help="Output SRT filename")
    parser.add_argument("--sarvam-api-key", help="Sarvam API key. Defaults to SARVAM_API_KEY.")
    parser.add_argument("--sarvam-mode", default="transcribe", choices=sorted(SARVAM_MODES), help="Sarvam Saaras v3 output mode")
    parser.add_argument("--install-deps", action="store_true", help="Install missing Python dependencies without prompting")
    parser.add_argument("--repair-deps", action="store_true", help="Repair broken Python dependencies without prompting")
    parser.add_argument("--allow-global-install", action="store_true", help="Allow dependency installs/repairs outside a virtual environment")
    parser.add_argument("--check-hardware", action="store_true", help="Show available Whisper hardware acceleration and exit")
    parser.add_argument("--tui", action="store_true", help="Open the Textual terminal UI")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args(argv)

    if args.check_hardware:
        print_hardware_report()
        return

    if args.tui:
        sys.exit(run_tui())

    if args.interactive or not args.input_file:
        if not sys.stdin.isatty() and not args.interactive:
            parser.print_help()
            return
        if not args.interactive:
            sys.exit(run_tui())
        interactive_main()
        return

    if not ensure_python_dependencies(
        auto_install=args.install_deps,
        auto_repair=args.repair_deps,
        allow_global_install=args.allow_global_install,
        dependencies=dependencies_for_backend(args.backend),
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
    base, _ = os.path.splitext(input_file)
    out_srt = args.output or f"{base}.{lang}.srt"

    try:
        if not transcribe_file_to_srt(
            input_file,
            out_srt,
            backend=args.backend,
            model_size=model_size,
            lang=lang,
            sarvam_api_key=args.sarvam_api_key,
            sarvam_mode=args.sarvam_mode,
            device=args.device,
        ):
            sys.exit(1)
    except Exception as e:
        print(f"[LTTC] Error during processing: {e}")
        sys.exit(2)

def main():
    cli_main()

if __name__ == "__main__":
    main()
