import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import os
import json
import google.generativeai as genai
import base64
import io
import subprocess
import threading
import time
from datetime import datetime

# Impor library OpenAI jika terinstal
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI library not found. Install it with 'pip install openai' to enable OpenAI features.")

class AdobeStockMetadataApp:
    def __init__(self, master):
        self.master = master
        master.title("Adobe Stock AI Metadata Generator")
        master.geometry("750x780") # Tinggi sedikit ditambah untuk tombol download log
        master.resizable(False, False)

        self.gemini_api_keys = []
        self.openai_api_keys = []
        self.current_gemini_api_key_index = 0
        self.current_openai_api_key_index = 0

        self.selected_folder = tk.StringVar()
        self.selected_file = tk.StringVar()
        self.total_processed_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.is_processing = False
        self.process_thread = None
        self.stop_event = threading.Event()

        self.ai_provider = tk.StringVar(value="Gemini") # Default provider
        self.gemini_model = tk.StringVar()
        self.openai_model = tk.StringVar()

        # Menambahkan semua versi Gemini Flash dari 1.5 sampai 2.5
        # Catatan: Perhatikan ketersediaan model ini di API Gemini yang sebenarnya.
        # Saat ini, 'gemini-1.5-flash' adalah yang paling umum dan tersedia secara luas.
        # Model 'gemini-2.0-flash' dan 'gemini-2.5-flash' adalah contoh berdasarkan permintaan user,
        # mungkin belum tersedia secara publik atau memiliki nama yang berbeda di masa mendatang.
        self.available_gemini_models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"]
        self.gemini_model.set(self.available_gemini_models[0]) # Set default model

        self.available_openai_models = [] # Akan diisi dinamis

        self.create_widgets()
        self.update_model_dropdown() # Panggil untuk mengatur model default saat startup

        self.check_exiftool_on_start()

    def create_widgets(self):
        api_frame = tk.LabelFrame(self.master, text="AI API Keys (Satu per baris)", padx=10, pady=10)
        api_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(api_frame, text="Enter API Keys (Gemini atau OpenAI):").pack(anchor="w", padx=5)
        self.api_key_text = tk.Text(api_frame, height=4, width=40)
        self.api_key_text.pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(api_frame, text="Set Keys", command=self.set_api_keys).pack(side="left", padx=5, anchor="n")
        
        self.api_key_count_label = tk.Label(api_frame, text="Jumlah Gemini Keys: 0 | Jumlah OpenAI Keys: 0", fg="blue")
        self.api_key_count_label.pack(side="bottom", anchor="w", padx=5, pady=5)

        provider_frame = tk.LabelFrame(self.master, text="AI Provider & Model Selection", padx=10, pady=10)
        provider_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(provider_frame, text="Select AI Provider:").pack(side="left", padx=5)
        self.provider_combobox = ttk.Combobox(provider_frame, textvariable=self.ai_provider, 
                                            values=["Gemini", "OpenAI"] if OPENAI_AVAILABLE else ["Gemini"], 
                                            state="readonly", width=15)
        self.provider_combobox.pack(side="left", padx=5)
        self.provider_combobox.bind("<<ComboboxSelected>>", self.on_provider_selected)

        tk.Label(provider_frame, text="Select Model:").pack(side="left", padx=5)
        self.model_combobox = ttk.Combobox(provider_frame, textvariable=self.gemini_model, 
                                           values=self.available_gemini_models, state="readonly", width=30)
        self.model_combobox.pack(side="left", expand=True, fill="x", padx=5)
        self.model_combobox.bind("<<ComboboxSelected>>", self.on_model_selected)

        input_frame = tk.LabelFrame(self.master, text="Image Selection", padx=10, pady=10)
        input_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(input_frame, text="Selected File/Folder:").pack(side="left", padx=5)
        self.file_label = tk.Label(input_frame, textvariable=self.selected_file, bg="white", relief="sunken", width=40)
        self.file_label.pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(input_frame, text="Browse File", command=self.browse_file).pack(side="left", padx=5)
        tk.Button(input_frame, text="Browse Folder", command=self.browse_folder).pack(side="left", padx="5")

        control_frame = tk.Frame(self.master)
        control_frame.pack(pady=10)

        self.start_button = tk.Button(control_frame, text="Start Processing", command=self.start_processing)
        self.start_button.pack(side="left", padx=5)
        self.stop_button = tk.Button(control_frame, text="Stop Processing", command=self.stop_processing, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        self.exit_button = tk.Button(control_frame, text="Exit", command=self.on_closing)
        self.exit_button.pack(side="left", padx=5)
        
        # --- Tambah tombol Download Log ---
        self.download_log_button = tk.Button(control_frame, text="Download Log", command=self.download_log)
        self.download_log_button.pack(side="left", padx=5)
        # --- Akhir penambahan ---

        self.progress_label = tk.Label(self.master, text="Processed: 0, Success: 0, Failed: 0")
        self.progress_label.pack(pady=5)

        self.log_text = tk.Text(self.master, height=15, width=80, state="disabled")
        self.log_text.pack(pady=10, padx=10, fill="both", expand=True)

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log_message(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    # --- Fungsi untuk download log ---
    def download_log(self):
        log_content = self.log_text.get("1.0", tk.END)
        if not log_content.strip():
            messagebox.showinfo("Informasi", "Log kosong, tidak ada yang bisa didownload.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="application_log.txt"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(log_content)
                messagebox.showinfo("Sukses", f"Log berhasil disimpan ke:\n{file_path}")
                self.log_message(f"Log berhasil didownload ke: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan log:\n{e}")
                self.log_message(f"Error saat mendownload log: {e}")
    # --- Akhir fungsi download log ---

    def update_progress(self, current_file_name=None):
        status_text = f"Processed: {self.total_processed_files}, Success: {self.successful_files}, Failed: {self.failed_files}"
        if current_file_name:
            status_text += f" (Processing: {current_file_name})"
        self.progress_label.config(text=status_text)

    def set_api_keys(self):
        raw_keys = self.api_key_text.get("1.0", tk.END).strip()
        
        self.gemini_api_keys = []
        self.openai_api_keys = []

        if not raw_keys:
            messagebox.showerror("Error", "API Keys tidak boleh kosong. Harap masukkan setidaknya satu kunci.")
            self.api_key_count_label.config(text="Jumlah Gemini Keys: 0 | Jumlah OpenAI Keys: 0", fg="red")
            return

        keys = [key.strip() for key in raw_keys.split('\n') if key.strip()]
        if not keys:
            messagebox.showerror("Error", "Tidak ada API Key valid yang ditemukan dalam input.")
            self.api_key_count_label.config(text="Jumlah Gemini Keys: 0 | Jumlah OpenAI Keys: 0", fg="red")
            return
        
        for key in keys:
            if key.startswith("sk-") and OPENAI_AVAILABLE:
                self.openai_api_keys.append(key)
            elif key.startswith("AIza"):
                self.gemini_api_keys.append(key)
            else:
                self.log_message(f"Peringatan: Kunci '{key[:10]}...' tidak dikenali sebagai Gemini atau OpenAI, atau OpenAI tidak diinstal.")
        
        self.current_gemini_api_key_index = 0
        self.current_openai_api_key_index = 0

        total_keys_msg = f"Gemini: {len(self.gemini_api_keys)} | OpenAI: {len(self.openai_api_keys)}"
        messagebox.showinfo("Sukses", f"API Keys berhasil diatur. {total_keys_msg}")
        self.log_message(f"API Keys berhasil dikonfigurasi. {total_keys_msg}")
        self.api_key_count_label.config(text=f"Jumlah Gemini Keys: {len(self.gemini_api_keys)} | Jumlah OpenAI Keys: {len(self.openai_api_keys)}", fg="blue")

        self.update_model_dropdown() # Perbarui dropdown model setelah API Key diatur

    def on_provider_selected(self, event=None):
        self.log_message(f"AI Provider dipilih: {self.ai_provider.get()}")
        self.update_model_dropdown()

    def update_model_dropdown(self):
        selected_provider = self.ai_provider.get()
        if selected_provider == "Gemini":
            self.model_combobox.config(values=self.available_gemini_models)
            if self.available_gemini_models:
                # Prefer gemini-1.5-flash karena efisien dan terbaru dari 1.5
                if "gemini-1.5-flash" in self.available_gemini_models:
                    self.gemini_model.set("gemini-1.5-flash")
                elif self.available_gemini_models: # Fallback if 1.5-flash not explicitly listed or available
                    self.gemini_model.set(self.available_gemini_models[0])
                else:
                    self.gemini_model.set("")
            else:
                self.gemini_model.set("")
            self.model_combobox.config(textvariable=self.gemini_model)
        elif selected_provider == "OpenAI":
            if OPENAI_AVAILABLE:
                # List model vision yang paling relevan dan efisien dari OpenAI
                self.available_openai_models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4-vision-preview"]
                self.model_combobox.config(values=self.available_openai_models)
                if self.available_openai_models:
                    # Prefer gpt-4o-mini untuk biaya dan performa, lalu gpt-4o
                    if "gpt-4o-mini" in self.available_openai_models:
                        self.openai_model.set("gpt-4o-mini")
                    elif "gpt-4o" in self.available_openai_models:
                        self.openai_model.set("gpt-4o")
                    else:
                        self.openai_model.set(self.available_openai_models[0])
                else:
                    self.openai_model.set("")
                self.model_combobox.config(textvariable=self.openai_model)
            else:
                self.log_message("OpenAI library tidak terinstal. Tidak bisa memilih model OpenAI.")
                self.model_combobox.config(values=[])
                self.openai_model.set("")
                messagebox.showwarning("Peringatan", "OpenAI library tidak terinstal. Fitur OpenAI dinonaktifkan.")

    def on_model_selected(self, event=None):
        if self.ai_provider.get() == "Gemini":
            selected_model = self.gemini_model.get()
        else:
            selected_model = self.openai_model.get()
        self.log_message(f"Model {self.ai_provider.get()} dipilih: {selected_model}")

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.tif *.tiff *.psd")]
        )
        if file_path:
            self.selected_file.set(file_path)
            self.selected_folder.set("")
            self.log_message(f"File dipilih: {file_path}")
            self.start_button.config(state="normal")

    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.selected_folder.set(folder_path)
            self.selected_file.set("")
            self.log_message(f"Folder dipilih: {folder_path}")
            self.start_button.config(state="normal")

    def check_exiftool_on_start(self):
        try:
            result = subprocess.run(["wsl", "exiftool", "-ver"], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.log_message(f"ExifTool {result.stdout.strip()} ditemukan dan berfungsi di WSL.")
            self.start_button.config(state="normal")
            return True
        except FileNotFoundError:
            self.log_message(f"Error: Perintah 'wsl' tidak ditemukan.")
            self.log_message("Harap pastikan WSL terinstal dan fitur 'Windows Subsystem for Linux' sudah diaktifkan.")
            self.start_button.config(state="disabled")
            return False
        except subprocess.CalledProcessError as e:
            self.log_message(f"Error saat menjalankan ExifTool di WSL: {e.stderr.strip()}")
            self.log_message("Harap pastikan 'libimage-exiftool-perl' sudah terinstal di lingkungan WSL Anda (mis. Ubuntu).")
            self.start_button.config(state="disabled")
            return False
        except Exception as e:
            self.log_message(f"Terjadi kesalahan tak terduga saat memeriksa ExifTool di WSL: {e}")
            self.start_button.config(state="disabled")
            return False

    def start_processing(self):
        if self.is_processing:
            return

        if not self.check_exiftool_on_start():
            messagebox.showerror("Error", "WSL atau ExifTool tidak siap. Harap periksa log dan ikuti instruksi instalasi WSL/ExifTool.")
            return

        selected_file = self.selected_file.get()
        selected_folder = self.selected_folder.get()

        if not selected_file and not selected_folder:
            messagebox.showerror("Error", "Pilih file atau folder terlebih dahulu.")
            return

        current_provider = self.ai_provider.get()
        if current_provider == "Gemini" and not self.gemini_api_keys:
            messagebox.showerror("Error", "Harap masukkan setidaknya satu Gemini API Key untuk provider Gemini.")
            return
        elif current_provider == "OpenAI" and not self.openai_api_keys:
            messagebox.showerror("Error", "Harap masukkan setidaknya satu OpenAI API Key untuk provider OpenAI.")
            return
        elif current_provider == "OpenAI" and not OPENAI_AVAILABLE:
            messagebox.showerror("Error", "OpenAI library tidak terinstal. Silakan instal dengan 'pip install openai' atau pilih provider Gemini.")
            return

        self.total_processed_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.update_progress()
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
        self.log_message("Memulai proses...")
        self.log_message("Peringatan: File asli akan ditimpa dengan metadata. Pastikan Anda memiliki cadangan jika diperlukan.")
        
        self.is_processing = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.exit_button.config(state="disabled")
        self.download_log_button.config(state="disabled") # Nonaktifkan saat proses
        self.stop_event.clear()

        self.process_thread = threading.Thread(target=self._process_images_in_background)
        self.process_thread.start()

    def stop_processing(self):
        if not self.is_processing:
            return
        self.log_message("Mengirim sinyal stop ke proses...")
        self.stop_event.set()
        self.stop_button.config(state="disabled")
        self.log_message("Menunggu proses berhenti (mungkin butuh waktu untuk gambar yang sedang diproses)...")

    def _get_configured_ai_client_and_model(self):
        """Mencoba menginisialisasi klien AI (Gemini/OpenAI) dengan API Key yang tersedia."""
        provider = self.ai_provider.get()
        
        if provider == "Gemini":
            if not self.gemini_api_keys: return None, None
            for i in range(len(self.gemini_api_keys)):
                key_to_try = self.gemini_api_keys[self.current_gemini_api_key_index]
                try:
                    genai.configure(api_key=key_to_try)
                    model_name = self.gemini_model.get()
                    model = genai.GenerativeModel(model_name)
                    self.log_message(f"Berhasil menginisialisasi Gemini model '{model_name}' dengan kunci index {self.current_gemini_api_key_index}: {key_to_try[:5]}...")
                    return "Gemini", model
                except Exception as e:
                    self.log_message(f"Gagal inisialisasi Gemini dengan kunci index {self.current_gemini_api_key_index}: {key_to_try[:5]}... Error: {e}")
                    self.current_gemini_api_key_index = (self.current_gemini_api_key_index + 1) % len(self.gemini_api_keys)
                    self.log_message(f"Mencoba kunci Gemini berikutnya (index {self.current_gemini_api_key_index})...")
            return None, None # Semua kunci Gemini gagal

        elif provider == "OpenAI":
            if not OPENAI_AVAILABLE or not self.openai_api_keys: return None, None
            for i in range(len(self.openai_api_keys)):
                key_to_try = self.openai_api_keys[self.current_openai_api_key_index]
                try:
                    client = OpenAI(api_key=key_to_try)
                    self.log_message(f"Berhasil menginisialisasi OpenAI client dengan kunci index {self.current_openai_api_key_index}: {key_to_try[:5]}...")
                    return "OpenAI", client
                except Exception as e:
                    self.log_message(f"Gagal inisialisasi OpenAI dengan kunci index {self.current_openai_api_key_index}: {key_to_try[:5]}... Error: {e}")
                    self.current_openai_api_key_index = (self.current_openai_api_key_index + 1) % len(self.openai_api_keys)
                    self.log_message(f"Mencoba kunci OpenAI berikutnya (index {self.current_openai_api_key_index})...")
            return None, None # Semua kunci OpenAI gagal
        
        return None, None # Provider tidak dikenal

    def _process_images_in_background(self):
        image_paths = []
        selected_file = self.selected_file.get()
        selected_folder = self.selected_folder.get()
        
        if selected_file:
            image_paths.append(selected_file)
        elif selected_folder:
            for root, _, files in os.walk(selected_folder):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.psd')):
                        image_paths.append(os.path.join(root, file))

        if not image_paths:
            self.log_message("Tidak ada file gambar yang ditemukan di lokasi yang dipilih.")
            self._reset_ui_after_processing()
            return

        selected_provider = self.ai_provider.get()
        selected_model_name = self.gemini_model.get() if selected_provider == "Gemini" else self.openai_model.get()

        for image_path in image_paths:
            if self.stop_event.is_set():
                self.log_message("Proses dihentikan oleh pengguna.")
                break

            self.total_processed_files += 1
            file_name_only = os.path.basename(image_path)
            self.log_message(f"\nMemproses gambar: {file_name_only}")
            self.update_progress(current_file_name=file_name_only)
            
            MAX_RETRIES = 5
            INITIAL_DELAY = 2 # Lebih besar untuk rate limit gratisan

            for attempt in range(MAX_RETRIES):
                try:
                    provider_type, ai_client = self._get_configured_ai_client_and_model()
                    if not ai_client:
                        raise Exception(f"Tidak ada API Key valid untuk provider {selected_provider} yang dapat digunakan.")

                    with open(image_path, "rb") as img_file:
                        img_data = img_file.read()
                        
                    encoded_image = base64.b64encode(img_data).decode('utf-8')
                    
                    metadata = {}
                    response_text = ""
                    prompt_tokens = 0
                    completion_tokens = 0
                    total_tokens = 0

                    if provider_type == "Gemini":
                        mime_type = self._get_mime_type(image_path)
                        image_parts = [{"mime_type": mime_type, "data": encoded_image}]
                        prompt_parts = [
                            image_parts[0],
                            "Analyze this image for stock photography metadata. Provide a highly descriptive title (max 200 characters), a comprehensive description (max 200 characters), and exactly 49 relevant, comma-separated keywords (focus on specific nouns, action verbs, vivid adjectives, and relevant concepts). Format the output as a JSON object with keys: 'title', 'description', 'keywords'."
                        ]
                        self.log_message(f"Mengirim gambar ke Gemini AI '{selected_model_name}' (Percobaan {attempt + 1}/{MAX_RETRIES})...")
                        response = ai_client.generate_content(prompt_parts)
                        response_text = response.text.strip()
                        
                        # Ambil penggunaan token dari respons Gemini
                        if response.usage_metadata:
                            prompt_tokens = response.usage_metadata.prompt_token_count
                            completion_tokens = response.usage_metadata.candidates_token_count
                            total_tokens = response.usage_metadata.total_token_count
                    
                    elif provider_type == "OpenAI":
                        if not OPENAI_AVAILABLE:
                            raise Exception("OpenAI library tidak terinstal.")
                        
                        # OpenAI Vision API requires data URL format
                        mime_type = self._get_mime_type(image_path)
                        data_url = f"data:{mime_type};base64,{encoded_image}"

                        self.log_message(f"Mengirim gambar ke OpenAI AI '{selected_model_name}' (Percobaan {attempt + 1}/{MAX_RETRIES})...")
                        chat_completion = ai_client.chat.completions.create(
                            model=selected_model_name,
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": "Analyze this image for stock photography metadata. Provide a highly descriptive title (max 200 characters), a comprehensive description (max 200 characters), and exactly 49 relevant, comma-separated keywords (focus on specific nouns, action verbs, vivid adjectives, and relevant concepts). Format the output as a JSON object with keys: 'title', 'description', 'keywords'."},
                                        {"type": "image_url", "image_url": {"url": data_url}},
                                    ],
                                }
                            ],
                            response_format={"type": "json_object"} # Meminta JSON object langsung
                        )
                        response_text = chat_completion.choices[0].message.content.strip()
                        
                        # Ambil penggunaan token dari respons OpenAI
                        if chat_completion.usage:
                            prompt_tokens = chat_completion.usage.prompt_tokens
                            completion_tokens = chat_completion.usage.completion_tokens
                            total_tokens = chat_completion.usage.total_tokens

                    self.log_message(f"Respon {provider_type}: {response_text}")
                    self.log_message(f"Penggunaan Token: Prompt={prompt_tokens}, Completion={completion_tokens}, Total={total_tokens}")

                    try:
                        # Membersihkan markdown JSON jika ada
                        if response_text.startswith("```json"):
                            response_text = response_text[len("```json"):].strip()
                        if response_text.endswith("```"):
                            response_text = response_text[:-len("```")].strip()
                        metadata = json.loads(response_text)
                    except json.JSONDecodeError as jde:
                        self.log_message(f"Error parsing JSON dari {provider_type}: {jde}. Respon mentah: {response_text}")
                        raise Exception(f"Gagal parsing JSON dari {provider_type}.")

                    title = metadata.get('title', 'Untitled')
                    description = metadata.get('description', 'No description available.')
                    keywords = metadata.get('keywords', '')

                    self.log_message(f"AI Metadata - Title: {title}")
                    self.log_message(f"AI Metadata - Description: {description}")
                    self.log_message(f"AI Metadata - Keywords: {keywords}")

                    self.add_metadata_with_exiftool_wsl(image_path, title, description, keywords)
                    self.successful_files += 1
                    self.update_progress()
                    break # Berhasil, keluar dari loop percobaan
                
                except Exception as e:
                    error_message = str(e).lower()
                    self.log_message(f"Gagal memproses {file_name_only} (Percobaan {attempt + 1}/{MAX_RETRIES}): {e}")

                    if "rate limit" in error_message or "quota" in error_message or "resource exhausted" in error_message or "too many requests" in error_message:
                        delay = INITIAL_DELAY * (2 ** attempt)
                        self.log_message(f"Terdeteksi rate limit/kuota. Menunggu {delay:.1f} detik sebelum mencoba lagi atau beralih API Key.")
                        time.sleep(delay)
                        # _get_configured_ai_client_and_model() akan menangani perpindahan kunci jika perlu
                    elif "invalid api key" in error_message or "authentication" in error_message or "bad api key" in error_message:
                        self.log_message(f"API Key sepertinya tidak valid. Akan mencoba kunci berikutnya jika tersedia.")
                        # _get_configured_ai_client_and_model() sudah akan beralih kunci
                        time.sleep(INITIAL_DELAY)
                    elif "deprecated" in error_message or "model_not_found" in error_message or "invalid model" in error_message:
                        self.log_message(f"Model AI yang dipilih mungkin tidak valid atau sudah deprecated: {selected_model_name}. Harap pilih model lain.")
                        self.failed_files += 1
                        self.update_progress()
                        break # Gagal permanen untuk gambar ini karena masalah model
                    else:
                        self.log_message(f"Terjadi kesalahan tidak terduga: {e}. Menganggap gagal untuk gambar ini.")
                        self.failed_files += 1
                        self.update_progress()
                        break # Keluar dari loop percobaan
            else: # Jika semua percobaan gagal
                self.log_message(f"Gagal memproses {file_name_only} setelah {MAX_RETRIES} percobaan.")
                self.failed_files += 1
                self.update_progress()
            
            time.sleep(1) # Jeda minimal antar gambar

        self._reset_ui_after_processing()
        messagebox.showinfo("Proses Selesai", f"Proses selesai. Berhasil: {self.successful_files}, Gagal: {self.failed_files}, Total: {self.total_processed_files}.")
        self.log_message("\n--- Semua gambar telah diproses. ---")

    def _get_mime_type(self, image_path):
        file_extension = os.path.splitext(image_path)[1].lower()
        if file_extension in (".jpg", ".jpeg"):
            return "image/jpeg"
        elif file_extension == ".png":
            return "image/png"
        elif file_extension in (".tif", ".tiff"):
            return "image/tiff"
        elif file_extension == ".psd":
            return "image/vnd.adobe.photoshop"
        return "application/octet-stream" # Default fallback

    def add_metadata_with_exiftool_wsl(self, image_path, title, description, keywords):
        try:
            wsl_path = image_path.replace("C:", "/mnt/c").replace("\\", "/")

            command = [
                "wsl",
                "exiftool",
                f"-XMP-dc:Title={title}",
                f"-XMP-dc:Description={description}",
                f"-XMP-dc:Subject={keywords}",
                "-overwrite_original",
                "-charset", "UTF8",
                "-m",
                wsl_path
            ]
            
            self.log_message(f"Menjalankan exiftool via WSL untuk penulisan XMP: {' '.join(command)}")
            
            result = subprocess.run(command, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            self.log_message(f"ExifTool Stdout (WSL): {result.stdout.strip()}")
            if result.stderr:
                self.log_message(f"ExifTool Stderr (WSL): {result.stderr.strip()}")
            
            self.log_message(f"Metadata (XMP) berhasil ditambahkan ke {os.path.basename(image_path)} (via ExifTool di WSL).")

        except FileNotFoundError:
            raise Exception(f"Error: Perintah 'wsl' atau 'exiftool' tidak ditemukan. Pastikan WSL terinstal dan ExifTool terinstal di Ubuntu Anda.")
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip() if e.stderr else e.stdout.strip()
            raise Exception(f"Gagal memanggil ExifTool di WSL: {error_output} [Return Code {e.returncode}]")
        except Exception as e:
            raise Exception(f"Terjadi kesalahan tidak terduga saat menambahkan metadata via ExifTool di WSL: {e}")

    def _reset_ui_after_processing(self):
        self.is_processing = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.exit_button.config(state="normal")
        self.download_log_button.config(state="normal") # Aktifkan lagi tombol download

    def on_closing(self):
        if self.is_processing:
            if messagebox.askyesno("Keluar Aplikasi", "Proses sedang berjalan. Apakah Anda yakin ingin menghentikannya dan keluar?"):
                self.stop_event.set()
                self.log_message("Aplikasi ditutup. Menunggu proses berhenti...")
                if self.process_thread and self.process_thread.is_alive():
                    self.process_thread.join(timeout=10) # Beri waktu thread untuk berhenti
                self.master.destroy()
            else:
                pass
        else:
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AdobeStockMetadataApp(root)
    root.mainloop()