import streamlit as st
import os
from openai import OpenAI
import docx
import fitz  # PyMuPDF untuk PDF

# Inisialisasi client OpenAI dengan API Key dari Secret Streamlit
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Fungsi ekstrak teks dari file
def extract_text(file):
    text = ""
    if file.name.endswith(".txt"):
        text = file.read().decode("utf-8")
    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        text = "\n".join([para.text for para in doc.paragraphs])
    elif file.name.endswith(".pdf"):
        pdf = fitz.open(stream=file.read(), filetype="pdf")
        for page in pdf:
            text += page.get_text()
    return text.strip()

# Fungsi analisis AI
def analisis_dokumen(text):
    kriteria = """
Periksa apakah dokumen ini memenuhi semua poin berikut:

1) Rencana kegiatan:
   i. Dokumen dasar: kegiatan, tujuan, dan manfaat usaha.
   ii. Kegiatan eksisting yang dimohonkan.
   iii. Rencana jadwal pelaksanaan kegiatan utama & pendukung.
   iv. Rencana tapak/site plan dengan bangunan, instalasi di laut, & fasilitas penunjang.
   v. Luasan (Ha) per kegiatan utama & penunjang.

2) Peta lokasi / plotting batas area dengan koordinat lintang & bujur.

Buat ringkasan apakah tiap poin tersebut ADA atau TIDAK ADA, dan berikan saran jika kurang.
"""
    prompt = f"Teks dokumen:\n{text}\n\n{kriteria}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Anda adalah asisten yang memeriksa kelengkapan dokumen teknis."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content

# UI Streamlit
st.title("📄 Verifikasi Kelengkapan Dokumen")

uploaded_file = st.file_uploader("Unggah dokumen (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    with st.spinner("📄 Membaca dokumen..."):
        teks_dokumen = extract_text(uploaded_file)

    if teks_dokumen:
        st.subheader("📑 Hasil Analisis AI")
        hasil = analisis_dokumen(teks_dokumen)
        st.write(hasil)
    else:
        st.error("Tidak ada teks yang bisa diekstrak dari dokumen.")
