import os
import streamlit as st
import tempfile
from openai import OpenAI
from PyPDF2 import PdfReader
import docx

# Ambil API key dari Streamlit secrets atau environment variable
api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not api_key:
    st.error("API Key OpenAI belum diatur. Tambahkan di Secrets atau Environment.")
    st.stop()

client = OpenAI(api_key=api_key)

# Daftar ketentuan pemeriksaan
KETENTUAN = """
Periksa dokumen ini apakah memuat informasi berikut secara lengkap:

1) Ekosistem sekitar:
   i. Mangrove (narasi, peta/gambar, sumber data):
      - Jenis
      - Persentase penutupan
      - Luasan
   ii. Lamun (narasi, peta/gambar, sumber data):
      - Jenis
      - Persentase penutupan padang lamun kaya/sehat
      - Luasan
   iii. Terumbu Karang (narasi, peta/gambar, sumber data):
      - Jenis terumbu karang
      - Persentase tutupan karang hidup
      - Luasan

2) Permodelan data hidro-oseanografi:
   i. Arus (narasi, peta/gambar, sumber data, tipe arus: pasang surut campuran harian ganda atau lainnya)
   ii. Gelombang (narasi, peta/gambar, sumber data)
   iii. Pasang surut (narasi, peta/gambar, sumber data)
   iv. Batimetri (narasi, peta/gambar, sumber data)

3) Profil dasar laut (narasi: berlumpur/berbatu/dll, gambar dokumentasi dasar laut atau penampang melintang)
4) Kondisi/karakteristik sosial ekonomi masyarakat (mata pencaharian masyarakat sekitar)
5) Aksesibilitas lokasi dan sekitar

Berikan hasil dalam format checklist lengkap dan catatan kekurangan jika ada.
"""

# Fungsi membaca file
def baca_file(uploaded_file):
    ext = uploaded_file.name.split(".")[-1].lower()
    text = ""
    if ext == "pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif ext in ["docx", "doc"]:
        doc = docx.Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif ext in ["txt", "md"]:
        text = uploaded_file.read().decode("utf-8")
    else:
        st.error("Format file tidak didukung. Gunakan PDF, DOCX, atau TXT.")
    return text.strip()

# UI
st.title("📄 Verifikasi Kelengkapan Dokumen - Ekosistem & Hidro-Oseanografi")

uploaded_file = st.file_uploader("Unggah dokumen (PDF/DOCX/TXT)", type=["pdf", "docx", "doc", "txt"])

if uploaded_file:
    st.info("📥 Membaca dokumen...")
    dokumen_text = baca_file(uploaded_file)

    if dokumen_text:
        with st.spinner("🔍 Memeriksa kelengkapan dokumen..."):
            prompt = f"Dokumen:\n{dokumen_text}\n\n{KETENTUAN}"
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Anda adalah asisten yang memeriksa kelengkapan dokumen teknis secara detail."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )

            hasil = response.choices[0].message.content
            st.success("✅ Pemeriksaan selesai")
            st.markdown("### Hasil Pemeriksaan:")
            st.markdown(hasil)

    else:
        st.error("Gagal membaca isi dokumen.")
