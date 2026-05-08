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

UI_DEPENDENCIES = {
    "rich": "rich",
    "textual": "textual",
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


def missing_ui_dependencies():
    missing = []
    for module_name, package_name in UI_DEPENDENCIES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_name)
    return missing


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


def ensure_python_dependencies(auto_install=False, auto_repair=False, allow_global_install=False, prompt=True):
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
            background: #101418;
            color: #edf2f7;
        }

        #shell {
            width: 92%;
            max-width: 110;
            height: auto;
            margin: 1 2;
        }

        #hero {
            height: 6;
            padding: 1 2;
            background: #17202a;
            border: round #5cc8ff;
        }

        #title {
            text-style: bold;
            color: #f7fbff;
        }

        #tagline {
            color: #a9b7c6;
        }

        #form {
            margin-top: 1;
            padding: 1 2;
            border: round #3a4654;
            background: #121820;
        }

        #log_panel {
            margin-top: 1;
            height: 14;
            border: round #3a4654;
            background: #0d1117;
        }

        .field_label {
            margin-top: 1;
            color: #cbd5e1;
        }

        Input, Select {
            margin-top: 1;
        }

        Button {
            margin-top: 1;
            margin-right: 1;
        }

        #status {
            margin-top: 1;
            color: #8bd5a5;
        }
        """

        def compose(self) -> ComposeResult:
            yield Header()
            with Container(id="shell"):
                with Vertical(id="hero"):
                    yield Static(Text("LTTC", style="bold #f7fbff"), id="title")
                    yield Static(
                        Text(
                            "Local Transcription & Timed Captions for Bengali and under-supported languages",
                            style="#a9b7c6",
                        ),
                        id="tagline",
                    )
                with Vertical(id="form"):
                    yield Label("Input media", classes="field_label")
                    with Horizontal():
                        yield Input(placeholder="Choose a video/audio file or paste a path", id="input_file")
                        yield Button("Browse", id="browse", variant="primary")
                    yield Label("Language code", classes="field_label")
                    yield Input(value="bn", placeholder="bn", id="language")
                    yield Label("Whisper model", classes="field_label")
                    yield Select(
                        [(model, model) for model in ["tiny", "base", "small", "medium", "large"]],
                        value="base",
                        id="model",
                    )
                    yield Label("Output SRT", classes="field_label")
                    yield Input(placeholder="Leave empty for input-file.bn.srt", id="output_file")
                    with Horizontal():
                        yield Button("Transcribe", id="transcribe", variant="success")
                        yield Button("Quit", id="quit", variant="error")
                    yield Static("Ready", id="status")
                yield Log(id="log_panel", highlight=True)
            yield Footer()

        def on_mount(self) -> None:
            self.query_one("#input_file", Input).focus()
            self.write_log("Ready. Select a media file, choose a model, then transcribe.")

        def write_log(self, message):
            self.query_one("#log_panel", Log).write_line(str(message))

        def set_status(self, message):
            self.query_one("#status", Static).update(message)

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
            if event.button.id == "transcribe":
                self.start_transcription()

        def start_transcription(self):
            input_file = self.query_one("#input_file", Input).value.strip()
            language = self.query_one("#language", Input).value.strip() or "bn"
            model = self.query_one("#model", Select).value or "base"
            output_file = self.query_one("#output_file", Input).value.strip()

            if not input_file:
                self.set_status("Choose an input file first.")
                self.write_log("Input file is required.")
                return
            if not os.path.isfile(input_file):
                self.set_status("Input file was not found.")
                self.write_log(f"File not found: {input_file}")
                return
            if model not in MODEL_SIZES:
                model = "base"

            if not output_file:
                output_file = os.path.splitext(input_file)[0] + f".{language}.srt"
                self.query_one("#output_file", Input).value = output_file

            transcribe_button = self.query_one("#transcribe", Button)
            transcribe_button.disabled = True
            self.set_status("Working...")
            self.write_log(f"Input: {input_file}")
            self.write_log(f"Language: {language}")
            self.write_log(f"Model: {model}")
            self.write_log(f"Output: {output_file}")

            worker = threading.Thread(
                target=self.transcribe_worker,
                args=(input_file, output_file, model, language),
                daemon=True,
            )
            worker.start()

        def transcribe_worker(self, input_file, output_file, model, language):
            base, _ = os.path.splitext(input_file)
            temp_audio_file = f"{base}.lttc_temp.wav"
            try:
                self.call_from_thread(self.write_log, "Checking dependencies...")
                if not ensure_python_dependencies(prompt=False):
                    self.call_from_thread(self.set_status, "Dependencies are not ready.")
                    return
                if not ensure_ffmpeg_available():
                    self.call_from_thread(self.set_status, "FFmpeg is not available.")
                    return
                self.call_from_thread(self.write_log, "Extracting audio...")
                if not extract_audio(input_file, temp_audio_file):
                    self.call_from_thread(self.set_status, "Audio extraction failed.")
                    return
                self.call_from_thread(self.write_log, "Transcribing. This can take a while...")
                transcribe_to_srt(temp_audio_file, output_file, model, language)
            except Exception as error:
                self.call_from_thread(self.write_log, f"Error: {error}")
                self.call_from_thread(self.set_status, "Failed.")
                return
            finally:
                if os.path.exists(temp_audio_file):
                    os.remove(temp_audio_file)
                self.call_from_thread(lambda: setattr(self.query_one("#transcribe", Button), "disabled", False))

            self.call_from_thread(self.write_log, "Done.")
            self.call_from_thread(self.set_status, f"Saved: {output_file}")

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
    parser.add_argument("--model", "-m", default="base", help="Whisper model (tiny, base, small, medium, large)")
    parser.add_argument("--output", "-o", help="Output SRT filename")
    parser.add_argument("--install-deps", action="store_true", help="Install missing Python dependencies without prompting")
    parser.add_argument("--repair-deps", action="store_true", help="Repair broken Python dependencies without prompting")
    parser.add_argument("--allow-global-install", action="store_true", help="Allow dependency installs/repairs outside a virtual environment")
    parser.add_argument("--tui", action="store_true", help="Open the Textual terminal UI")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args(argv)

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
