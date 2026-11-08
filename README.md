# Manga Translator ID — Streamlit

Aplikasi Python satu-paket untuk menerjemahkan manga ke Bahasa Indonesia.

## Fitur
- Upload satu/banyak PNG, JPG, JPEG, WEBP.
- OCR EasyOCR: English, Japanese, Korean, Simplified/Traditional Chinese.
- Terjemahan melalui OpenAI API.
- OpenCV inpainting untuk menghapus area teks, lalu typesetting sederhana.
- Preview, download gambar satuan, dan ZIP.

## Jalankan lokal
Gunakan Python 3.11. EasyOCR/PyTorch cukup besar dan mengunduh model saat pertama kali dijalankan.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Masukkan API key di aplikasi, atau buat `.streamlit/secrets.toml` (jangan commit):
```toml
OPENAI_API_KEY = "sk-..."
```

## Deploy ke Streamlit Community Cloud
1. Buat repository GitHub dan upload isi folder ini ke root repository.
2. Masuk ke https://share.streamlit.io/ dengan akun GitHub.
3. Pilih Create app, repository, branch `main`, file `app.py`.
4. Deploy. Streamlit membaca `requirements.txt` dan `packages.txt`.
5. Buka Settings → Secrets dan tambahkan:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
6. Restart aplikasi.

## Catatan hosting
EasyOCR dan PyTorch membutuhkan resource besar. Community Cloud memiliki batas RAM/resource, jadi model OCR bisa lambat atau gagal dimuat pada paket gratis. Uji satu gambar terlebih dahulu. Jika resource tidak cukup, gunakan hosting dengan RAM lebih besar atau pindahkan OCR ke API.

## Batasan kualitas
Inpainting tidak dapat memulihkan detail asli yang tertutup teks secara persis. OCR dapat keliru membaca teks vertikal, efek suara, font dekoratif, dan tulisan kecil. Versi ini menempatkan terjemahan pada kotak OCR, belum memahami bentuk balon percakapan. Periksa hasil dan lakukan koreksi manual sebelum publikasi.

Gunakan hanya gambar yang Anda punya hak atau izin untuk proses. Jangan pernah mengunggah API key ke GitHub.
