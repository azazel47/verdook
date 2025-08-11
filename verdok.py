import streamlit as st
import openai
import os
import pandas as pd

# Ambil API key dari secret
openai.api_key = os.getenv("OPENAI_API_KEY")

# Judul Aplikasi
st.title("📄 Verifikasi Dokumen Lingkungan & Hidro-oseanografi")

st.markdown("""
Aplikasi ini memeriksa dokumen dan memberikan skor kelengkapan berdasarkan poin-poin ketentuan.
""")

# Upload Dokumen
uploaded_file = st.file_uploader("Unggah dokumen (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])

# Fungsi analisis AI
def analisis_dokumen(teks):
    prompt = f"""
    Anda adalah asisten verifikasi dokumen lingkungan.
    Periksa dokumen berikut dan:
    1. Pastikan semua poin ketentuan berikut ada:
       **1) Ekosistem sekitar**
       i. Mangrove - jenis, persentase penutupan, luasan.
       ii. Lamun - jenis, persentase penutupan, luasan.
       iii. Terumbu Karang - jenis, persentase tutupan karang hidup, luasan.
       **2) Permodelan hidro-oseanografi**
       i. Arus - sertakan nilai (m/s) dan jenis arus.
       ii. Gelombang - sertakan nilai tinggi gelombang (m).
       iii. Pasang surut - sertakan nilai rentang pasang surut (m).
       iv. Batimetri - sertakan nilai kedalaman (m).
       **3) Profil dasar laut**
       **4) Sosial-ekonomi masyarakat**
       **5) Aksesibilitas lokasi**
    2. Berikan skor kelengkapan 0-100 untuk setiap poin.
    3. Tampilkan tabel checklist berwarna (Hijau = Lengkap, Kuning = Kurang Lengkap, Merah = Tidak Ada).

    Dokumen:
    {teks}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message["content"]

# Jika file diupload
if uploaded_file:
    import docx2txt
    import fitz  # PyMuPDF untuk PDF

    if uploaded_file.type == "application/pdf":
        pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        teks = "\n".join([page.get_text() for page in pdf])
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        teks = docx2txt.process(uploaded_file)
    else:
        teks = uploaded_file.read().decode("utf-8")

    st.success("✅ Dokumen berhasil dibaca, mulai analisis...")

    hasil = analisis_dokumen(teks)

    st.markdown("### 📊 Hasil Analisis")
    st.markdown(hasil)
