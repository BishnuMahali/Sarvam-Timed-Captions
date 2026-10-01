from setuptools import setup

setup(
    name="sarvam-timed-captions",
    version="1.1.0",
    package_dir={"": "SRC"},
    py_modules=["STC"],
    install_requires=[
        "openai-whisper",
        "pydub",
        "pysrt",
        "requests",
        "customtkinter>=5.2.2",
        "tkinterdnd2",
    ],
    entry_points={
        "console_scripts": [
            "stc=STC:main",
        ],
    },
    author="Bishnu Mahali",
    description="Professional Transcription Toolkit (Powered by Sarvam AI)",
    license="MIT",
    url="https://github.com/bishnumahali/Sarvam-Timed-Captions",
)
