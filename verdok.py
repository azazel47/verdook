import streamlit as st
from openai import OpenAI
import fitz  # PyMuPDF
import re

# --- Konfigurasi API ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Persyaratan ---
persyaratan = {
    "dok1": """
    1) Rencana kegiatan:
    I. Dokumen dasar berupa kegiatan, tujuan, manfaat usaha (jelas & lengkap).
    II. Kegiatan eksisting yang dimohonkan (jelas jenisnya).
    III. Rencana jadwal pelaksanaan utama & pendukung (jelas, tabel jika perlu).
    IV. Rencana tapak/site plan + instalasi laut + fasilitas penunjang.
    V. Deskriptif luasan (Ha) per kegiatan utama & penunjang.
    2) Peta lokasi + koordinat lintang/bujur.
    """,
    "dok2": """
    Informasi Pemanfaatan Ruang Laut di sekitar lokasi
    (contoh: penggunaan ruang sekitar oleh masyarakat + jarak dari lokasi pemohon).
    """,
    "dok3": """
    1) Ekosistem sekitar:
       - Mangrove (jenis, persentase tutupan, luas, peta, sumber data)
       - Lamun (jenis, persentase padang lamun sehat, luas, peta, sumber data)
       - Terumbu Karang (jenis, persentase karang hidup, luas, peta, sumber data)
    2) Hidro-oseanografi:
       - Arus (tipe pasang surut, peta, sumber data)
       - Gelombang (peta, sumber data)
       - Pasang surut (peta, sumber data)
       - Batimetri (peta, sumber data)
    3) Profil dasar laut + foto
    4) Sosial ekonomi masyarakat
    5) Aksesibilitas lokasi
    """,
    "dok4": """
    1) Rencana pengambilan material reklamasi (lokasi, jarak, jumlah, metode, gambar)
    2) Rencana pemanfaatan lahan reklamasi + peta + luas
    3) Metode pelaksanaan reklamasi (teknis, material, penimbunan)
    4) Jadwal pelaksanaan reklamasi (tabel)
    """
}

# --- Fungsi Baca PDF ---
def baca_pdf(uploaded_file):
    teks = ""
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in doc:
        teks += page.get_text()
    return teks

# --- Fungsi Analisis ---
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
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content

# --- UI ---
st.title("📄 Verifikasi Kelengkapan Dokumen")

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

    dokumen_input = [
        (dok1, "dok1"),
        (dok2, "dok2"),
        (dok3, "dok3")
    ]
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

    # Hitung skor
    total_skor = sum(skor_list) if skor_list else 0
    rata_skor = (total_skor / len(skor_list)) if skor_list else 0

    # Tampilkan hasil
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
