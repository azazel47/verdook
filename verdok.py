import streamlit as st
from openai import OpenAI
import os

# --- Konfigurasi API ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Fungsi Analisis ---
def analisis_dokumen(teks):
    prompt = f"""
    Periksa dokumen berikut untuk memastikan kelengkapan dan kesesuaian poin:

    1) Rencana kegiatan:
        i. Dokumen dasar: kegiatan, tujuan, manfaat (lengkap bentuk kegiatan).
        ii. Kegiatan eksisting (lengkap jenisnya).
        iii. Rencana jadwal pelaksanaan utama & pendukung (boleh tabel).
        iv. Rencana tapak/site plan (dilengkapi bangunan, instalasi laut, fasilitas penunjang).
        v. Deskripsi luasan (Ha) per kegiatan utama & penunjang.
    2) Peta lokasi: batas area/jalur dengan titik koordinat lintang & bujur.

    Aturan tambahan:
    - Setiap narasi hidrooseanografi HARUS menyebutkan nilai numerik (contoh kedalaman, kecepatan arus, tinggi gelombang, dsb.).
    - Berikan skor 0-100 untuk setiap poin.
    - Buat tabel checklist berwarna: hijau (lengkap), kuning (kurang lengkap), merah (tidak ada).
    - Berikan ringkasan hasil analisis di akhir.

    Dokumen:
    {teks}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content

# --- UI Streamlit ---
st.title("📄 Analisis Kelengkapan Dokumen")

uploaded_file = st.file_uploader("Upload file teks / PDF", type=["txt", "pdf"])

if uploaded_file:
    # Baca teks dari file
    if uploaded_file.type == "application/pdf":
        import fitz  # PyMuPDF
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        teks = ""
        for page in doc:
            teks += page.get_text()
    else:
        teks = uploaded_file.read().decode("utf-8")

    with st.spinner("🔍 Menganalisis dokumen..."):
        hasil = analisis_dokumen(teks)

    st.subheader("Hasil Analisis")
    st.markdown(hasil)
