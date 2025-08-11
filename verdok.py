import streamlit as st
import fitz  # PyMuPDF
import re
import google.generativeai as genai

# --- Konfigurasi API Gemini ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- Persyaratan (sama seperti sebelumnya) ---
persyaratan = {
    "dok1": """...""",
    "dok2": """...""",
    "dok3": """...""",
    "dok4": """..."""
}

# --- Fungsi Baca PDF ---
def baca_pdf(uploaded_file):
    teks = ""
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in doc:
        teks += page.get_text()
    return teks

# --- Fungsi Analisis pakai Gemini ---
def analisis_dokumen(teks, syarat):
    prompt = f"""
    Periksa dokumen berikut terhadap persyaratan ini:
    {syarat}

    Keluaran:
    - Skor kelengkapan (0-100)
    - Daftar poin yang tidak lengkap
    - Tabel checklist (Lengkap/Kurang/Tidak Ada)
    - Ringkasan hasil
    Dokumen:
    {teks}
    """
    model = genai.GenerativeModel("gemini-1.5-pro")  # bisa ganti model lain
    response = model.generate_content(prompt)
    return response.text

# --- UI ---
st.title("📄 Verifikasi Kelengkapan Dokumen (Gemini)")

is_reklamasi = st.checkbox("Reklamasi (Dokumen 4 jika ada)")

dok1 = st.file_uploader("📄 Upload Dokumen 1", type=["pdf"])
dok2 = st.file_uploader("📄 Upload Dokumen 2", type=["pdf"])
dok3 = st.file_uploader("📄 Upload Dokumen 3", type=["pdf"])
dok4 = None
if is_reklamasi:
    dok4 = st.file_uploader("📄 Upload Dokumen 4", type=["pdf"])

if st.button("🔍 Proses Analisis"):
    hasil_semua = {}
    skor_list = []

    dokumen_input = [(dok1, "dok1"), (dok2, "dok2"), (dok3, "dok3")]
    if is_reklamasi:
        dokumen_input.append((dok4, "dok4"))

    for dok, nama in dokumen_input:
        if dok:
            teks = baca_pdf(dok)
            hasil = analisis_dokumen(teks, persyaratan[nama])
            hasil_semua[nama] = hasil

            match = re.search(r"Skor\s*[:\-]?\s*(\d+)", hasil)
            if match:
                skor_list.append(int(match.group(1)))
        else:
            hasil_semua[nama] = "⚠️ Dokumen tidak diunggah, analisis dilewati."

    total_skor = sum(skor_list) if skor_list else 0
    rata_skor = (total_skor / len(skor_list)) if skor_list else 0

    st.subheader("📊 Hasil Analisis Per Dokumen")
    for nama, konten in hasil_semua.items():
        st.markdown(f"**{nama.upper()}**")
        st.markdown(konten)

    st.subheader("📈 Rekapitulasi Skor")
    st.write(f"Total Skor: {total_skor}")
    st.write(f"Rata-rata Skor: {rata_skor:.2f}")

    if skor_list:
        if rata_skor >= 70:
            st.success("✅ Lolos Verifikasi")
        else:
            st.error("❌ Tidak Lolos Verifikasi")
    else:
        st.warning("⚠️ Tidak ada dokumen yang bisa dianalisis.")
