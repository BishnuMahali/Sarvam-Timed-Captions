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
- Generates timed captions as `.srt` files
- Defaults to Bengali (`bn`)
- Supports Whisper model sizes: `tiny`, `base`, `small`, `medium`, and `large`
- Includes both command-line and interactive modes

## Requirements

- Python 3.x
- FFmpeg installed and available from the terminal
- Python packages:
  - `openai-whisper`
  - `pysrt`

## Setup

Clone the repository, then install the Python dependencies:

```bash
pip install openai-whisper pysrt
```

Make sure FFmpeg is installed:

```bash
ffmpeg -version
```

If that command does not work, install FFmpeg first and add it to your system `PATH`.

## Usage

Run LTTC on a video or audio file:

```bash
python LTTC.py "path/to/video.mp4" --lang bn --model base
```

Choose an output file:

```bash
python LTTC.py "path/to/video.mp4" --lang bn --model base --output captions.bn.srt
```

Use interactive mode:

```bash
python LTTC.py --interactive
```

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

No license has been chosen yet.
