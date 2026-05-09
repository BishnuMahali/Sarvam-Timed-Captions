from setuptools import setup

setup(
    name="sarvam-timed-captions",
    version="0.6.0",
    py_modules=["STC"],
    install_requires=[
        "numpy<2.0",
        "openai-whisper",
        "pydub",
        "pysrt",
        "requests",
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
