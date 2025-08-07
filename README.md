# AI Metadata Generator for Stock Photo Platforms

A Python GUI application to **generate metadata (title, description, keywords)** for stock photo platforms such as Adobe Stock using **Gemini (Google)** and **OpenAI (ChatGPT Vision)**.

## 🔥 Features
- Gemini & OpenAI model selection (GPT-4o, Gemini 1.5-2.5)
- Image-based metadata generation
- Add metadata directly into images using ExifTool via WSL
- Batch processing for folders
- Downloadable logs
- Error handling and rate-limit rotation for multiple API keys

## 🖥️ Requirements

- Python 3.9+
- WSL + ExifTool installed in Ubuntu WSL
- Gemini API Key or OpenAI API Key

# Make sure ExifTool is available via WSL:
- wsl
- sudo apt update
- sudo apt install libimage-exiftool-perl

## 📦 Installation

```bash
pip install -r requirements.txt



