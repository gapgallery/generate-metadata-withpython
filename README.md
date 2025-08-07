## AI Metadata Generator for Stock Photo Platforms

A Python GUI application to **generate metadata (title, description, keywords)** for stock photo platforms such as Adobe Stock using **Gemini (Google)** and **OpenAI (ChatGPT Vision)**.

---

## 📊 Status

![GitHub last commit](https://img.shields.io/github/last-commit/gapgallery/generate-metadata-withpython)
![GitHub repo size](https://img.shields.io/github/repo-size/gapgallery/generate-metadata-withpython)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![GitHub license](https://img.shields.io/github/license/gapgallery/generate-metadata-withpython)
![GitHub issues](https://img.shields.io/github/issues/gapgallery/generate-metadata-withpython)
![GitHub stars](https://img.shields.io/github/stars/gapgallery/generate-metadata-withpython?style=social)

---

## 🔥 Features

- Gemini & OpenAI model selection (GPT-4o, Gemini 1.5–2.5)
- Image-based metadata generation
- Add metadata directly into images using ExifTool via WSL
- Batch processing for folders
- Downloadable logs
- Error handling and rate-limit rotation for multiple API keys

---

## 🖥️ Requirements

- Python 3.9+
- WSL + ExifTool installed in Ubuntu WSL
- Gemini API Key or OpenAI API Key

## 📦 Installation

```bash
pip install -r requirements.txt
```

Make sure ExifTool is available via WSL:
```bash
wsl
sudo apt update
sudo apt install libimage-exiftool-perl
```

## 🚀 Usage

```bash
python metanew.py
```

1. Masukkan API Key
2. Pilih provider: Gemini atau OpenAI
3. Pilih model
4. Browse gambar atau folder
5. Start proses dan download log hasilnya

## 🧪 Example
![screenshot](pict%20metadata.png)

## 🛠 Dependencies

- `tkinter`
- `Pillow`
- `google-generativeai`
- `openai` (optional, jika pakai OpenAI)
- `subprocess`, `threading`, `base64`, dll (bawaan Python)

## 📝 License

No license — feel free to fork and customize!
