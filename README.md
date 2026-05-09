# Sarvam Timed Captions (STC)

A professional desktop application to generate highly accurate timed captions (.srt) from video and audio files. Primarily powered by the **Sarvam AI Cloud API** for superior Bengali accuracy, with **OpenAI Whisper** as a free local fallback.

## 🌟 Key Features

- **Professional Accuracy**: Uses Sarvam AI's specialized models for high-quality Indic language transcription.
- **Smart Slicing**: Automatically handles audio chunking (5-second intervals) to provide granular, well-timed captions.
- **Dual-Engine Strategy**: 
    - **Sarvam AI (Cloud)**: Recommended for maximum accuracy and speed.
    - **Whisper (Local)**: A free, privacy-focused fallback that runs on your machine.
- **Persistent Settings**: Remembers your preferred language, engine, and API key securely between sessions.
- **Modern Dashboard**: A clean, single-screen GUI built for non-technical users.

---

## 🚀 Getting Started

### 1. Prerequisite: API Key
To use the high-accuracy cloud engine, you need an API key:
- Sign up at the [Sarvam AI Dashboard](https://dashboard.sarvam.ai/).
- Copy your **API Subscription Key**.

### 2. Installation (Windows)
1. **Install Python**: [Download here](https://www.python.org/) (Ensure you check **"Add Python to PATH"**).
2. **Install FFmpeg**: [Download here](https://ffmpeg.org/download.html) and add it to your PATH.
3. **Download this repo**: Clone or download the ZIP to your computer.

### 3. Launch
Double-click **`Start STC.bat`**.
- The first run will automatically set up your environment.
- If you plan to use **Whisper (Local)** mode, say `y` when asked about an **NVIDIA GPU**.

---

## 🔒 Security & Privacy

**IMPORTANT: Make your repository PRIVATE.**
STC saves your API key locally in an encoded format (`.stc_config.json`) for convenience. To prevent your key from being exposed:

1. Go to your repository settings on GitHub/GitLab.
2. Under "Danger Zone", click **Change visibility**.
3. Select **Make private**.

---

## 📺 How to Use

1. **Select Engine**: Choose **Sarvam AI** (Default) or **Whisper**.
2. **Browse**: Pick your video or audio file.
3. **Settings**: Enter your **API Key** (for Sarvam) and select **Bengali**.
4. **Start**: Click **START TASK**.
5. Your `.srt` file will be generated in the same folder as your video.

---

## License
MIT License - Copyright (c) 2026 Bishnu Mahali
