# LTTC

**Local Transcription & Timed Captions**

LTTC is a local-first transcription and captioning tool for video/audio files in languages that are poorly supported by mainstream editing software. The project starts with Bengali (`bn`) and is intended to grow into a practical workflow for creators who need timed transcripts and caption files without depending on an editor's built-in language support.

## Why LTTC Exists

Many video editors can generate usable transcripts for English, but support becomes unreliable or unavailable for languages such as Bengali. That slows down editing, captioning, searching, and reviewing spoken content.

LTTC aims to solve that by generating local timed captions, such as `.srt` files, from video or audio files. The first target language is Bengali, but the tool is designed around language codes so more languages can be added and tested over time.

## Name

The best expansion for **LTTC** is:

**Local Transcription & Timed Captions**

It is short, direct, and easy to understand. It says what the tool does without sounding too abstract. “Local Timed Transcriptions & Captions” also works, but it is a little harder to say and less natural as a project name.

## Current Features

- Transcribes video/audio locally using OpenAI Whisper
- Optionally transcribes using Sarvam AI Saaras v3 for Indian-language ASR
- Generates timed captions as `.srt` files
- Defaults to Bengali (`bn`)
- Supports Whisper model sizes: `tiny`, `base`, `small`, `medium`, and `large`
- Includes command-line, classic interactive, and Textual terminal UI modes

## Requirements

- Python 3.x
- FFmpeg installed and available from the terminal
- Python packages:
  - `openai-whisper`
  - `pysrt`
  - `rich`
  - `sarvam-ai`
  - `textual`

## Setup

Clone the repository, then create an isolated virtual environment. This is strongly recommended because Whisper depends on PyTorch, and PyTorch can conflict with other ML packages installed in global Python.

```bash
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install the CPU build of PyTorch first:

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Then install LTTC's Python dependencies:

```bash
python -m pip install -r requirements.txt
```

LTTC can also help install missing Python packages when it starts. If a required package is missing, interactive runs inside a virtual environment will ask whether to install it.

To install missing Python dependencies automatically inside a virtual environment:

```bash
python LTTC.py --install-deps
```

If a package is installed but broken, such as an incomplete PyTorch install on Windows, LTTC will show a repair command. You can run the repair automatically inside a virtual environment:

```bash
python LTTC.py --repair-deps
```

LTTC avoids automatic dependency changes in global Python by default. If you intentionally want to modify global Python, use:

```bash
python LTTC.py --repair-deps --allow-global-install
```

Make sure FFmpeg is installed:

```bash
ffmpeg -version
```

If that command does not work, install FFmpeg first and add it to your system `PATH`.

## Usage

Open the terminal UI:

```bash
python LTTC.py --tui
```

You can also run `python LTTC.py` from an interactive terminal to open the UI by default.

Run LTTC on a video or audio file:

```bash
python LTTC.py "path/to/video.mp4" --lang bn --model base
```

Use Sarvam AI instead of local Whisper:

```bash
$env:SARVAM_API_KEY = "your_api_key_here"
python LTTC.py "path/to/video.mp4" --backend sarvam --lang bn --sarvam-mode transcribe
```

You can also pass the key directly:

```bash
python LTTC.py "path/to/video.mp4" --backend sarvam --lang bn --sarvam-api-key "your_api_key_here"
```

Sarvam uses BCP-47 language codes such as `bn-IN`; LTTC maps `bn` to `bn-IN` automatically. Sarvam's REST API is best for short audio clips; long-video support should later use their batch API.

If Python dependencies are missing, install them automatically while running:

```bash
python LTTC.py "path/to/video.mp4" --lang bn --install-deps
```

If Whisper or PyTorch is installed but fails to load, repair dependencies while running:

```bash
python LTTC.py "path/to/video.mp4" --lang bn --repair-deps
```

Choose an output file:

```bash
python LTTC.py "path/to/video.mp4" --lang bn --model base --output captions.bn.srt
```

Use interactive mode:

```bash
python LTTC.py --interactive
```

In interactive mode, press Enter at the file path prompt to open a browse window and select a video or audio file.

## Examples

Generate Bengali captions from a video:

```bash
python LTTC.py "my-video.mp4" --lang bn
```

Use a larger Whisper model for better quality:

```bash
python LTTC.py "my-video.mp4" --lang bn --model medium
```

## Roadmap

- Improve Bengali transcription and caption timing workflow
- Add cleaner packaging so `lttc` can be installed as a command
- Add more output formats, such as `.vtt` and plain timed transcript text
- Add batch processing for multiple files
- Add simple quality review tools for fixing captions faster
- Test more under-supported languages

## Project Status

LTTC is early and experimental. The first goal is to make a reliable local workflow for Bengali video transcription and timed captions.

## License

MIT License

Copyright (c) 2026 Bishnu Mahali

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
