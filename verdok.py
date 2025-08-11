import streamlit as st
import PyPDF2
from docx import Document
import openai
import io
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
st.write("OPENAI_API_KEY" in st.secrets)  # Harus True

# ===== KONFIGURASI OPENAI API =====
# Pastikan tambahkan OPENAI_API_KEY di Secrets Streamlit
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ====== FUNGSI EKSTRAK TEKS ======
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

# ====== ANALISIS AI ======
def analisis_ai(teks_dokumen):
    prompt = f"""
    Anda adalah sistem verifikasi dokumen perizinan.
    Periksa apakah dokumen berikut memuat informasi sesuai kriteria:

    1) Rencana kegiatan:
        - Kegiatan, tujuan, manfaat
        - Kegiatan eksisting
        - Jadwal pelaksanaan
        - Site plan
        - Luasan lokasi
    2) Peta lokasi beserta koordinat

    Dokumen:
    {teks_dokumen}

    Buatkan:
    - Ringkasan
    - Checklist kelengkapan poin di atas (lengkap/tidak)
    - Saran perbaikan
    """
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message["content"]

# ====== STREAMLIT APP ======
st.title("📄 AI Verifikasi Dokumen Perizinan")

uploaded_file = st.file_uploader("Unggah dokumen (PDF atau DOCX)", type=["pdf", "docx"])

if uploaded_file is not None:
    if uploaded_file.type == "application/pdf":
        text = extract_text_from_pdf(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = extract_text_from_docx(uploaded_file)
    else:
        st.error("Format file tidak didukung.")
        st.stop()

    st.subheader("📜 Teks Dokumen")
    st.text_area("Isi dokumen:", text, height=200)

    if st.button("🔍 Analisis Dokumen dengan AI"):
        with st.spinner("Menganalisis dokumen..."):
            hasil = analisis_ai(text)
        st.subheader("📊 Hasil Analisis AI")
        st.write(hasil)
