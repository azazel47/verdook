import streamlit as st
from openai import OpenAI
import os

# --- Konfigurasi API ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Fungsi Analisis ---
def analisis_dokumen(teks):
    prompt = f"""
    Periksa dokumen berikut untuk memastikan kelengkapan dan kesesuaian poin:
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
