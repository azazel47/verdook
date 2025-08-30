# Streamlit prototype: Document Verification for Licensing Documents with AI
# Updated: Removed python-docx dependency for easier deployment on Streamlit Cloud.

import streamlit as st
from io import BytesIO
import tempfile
import os
import re
from PIL import Image
import pytesseract
from PyPDF2 import PdfReader

st.set_page_config(page_title="Verifikasi Dokumen Perizinan", layout="wide")

# --- Required sections for licensing documents ---
REQUIRED_SECTIONS = [
    "Rencana kegiatan",
    "dokumen dasar berupa kegiatan, tujuan dan manfaat kegiatan usaha",
    "kegiatan eksisting yang dimohonkan",
    "rencana jadwal pelaksanaan kegiatan utama dan pendukungnya",
    "Rencana tapak/site plan kegiatan",
    "deskriptif luasan",
    "Peta lokasi/plotting batas-batas area"
]

def extract_text(file_bytes: bytes, filename: str) -> str:
    lower = filename.lower()
    text = ""
    if lower.endswith('.pdf'):
        try:
            reader = PdfReader(BytesIO(file_bytes))
            for page in reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            st.error(f"Gagal mengekstrak teks PDF: {e}")
    elif lower.endswith('.txt'):
        text = file_bytes.decode('utf-8', errors='ignore')
    elif lower.endswith(('.png', '.jpg', '.jpeg')):
        img = Image.open(BytesIO(file_bytes))
        text = pytesseract.image_to_string(img)
    else:
        st.warning("Format file tidak didukung untuk ekstraksi teks selain PDF, TXT, atau gambar.")
    return text

def verify_document(text: str) -> dict:
    results = {}
    for section in REQUIRED_SECTIONS:
        results[section] = bool(re.search(re.escape(section), text, re.IGNORECASE))
    # Check for coordinates format (latitude, longitude)
    coord_pattern = r"-?\d{1,3}\.\d+\s*,\s*-?\d{1,3}\.\d+"
    results['koordinat_ditemukan'] = bool(re.search(coord_pattern, text))
    return results

st.title("Verifikasi Dokumen Perizinan")
st.write("Upload dokumen perizinan (PDF, TXT, PNG, JPG) untuk memeriksa kelengkapan persyaratan.")

uploaded = st.file_uploader("Pilih file dokumen", type=['pdf', 'txt', 'png', 'jpg', 'jpeg'])
if uploaded:
    file_bytes = uploaded.read()
    with st.spinner('Ekstraksi teks dari dokumen...'):
        extracted = extract_text(file_bytes, uploaded.name)

    st.subheader("Teks yang diekstrak (preview)")
    st.text_area("Extracted text", value=extracted[:5000], height=300)

    st.subheader("Hasil Verifikasi")
    checks = verify_document(extracted)
    st.json(checks)

    completeness = sum(1 for v in checks.values() if v) / len(checks) * 100
    st.write(f"**Persentase kelengkapan dokumen:** {completeness:.2f}%")
else:
    st.info("Unggah dokumen untuk memulai verifikasi.")
