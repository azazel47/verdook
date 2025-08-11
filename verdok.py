import streamlit as st
from openai import OpenAI
import fitz  # PyMuPDF
import pandas as pd
import time
import random
import re
from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError, ServiceUnavailableError

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
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page in doc:
            teks += page.get_text()
    except Exception as e:
        st.error(f"[Gagal Membaca PDF] {e}")
    return teks

# --- Fungsi Panggil API dengan Retry (Exponential Backoff + Jitter) ---
def analisis_dokumen(teks, syarat, max_retries=6):
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
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return response.choices[0].message.content

        except (RateLimitError, ServiceUnavailableError):
            wait_time = min(60, (2 ** attempt) + random.uniform(0, 2))
            st.warning(f"[RateLimit] Menunggu {wait_time:.1f} detik sebelum retry ({attempt+1}/{max_retries})...")
            time.sleep(wait_time)

        except (APIError, APIConnectionError) as e:
            wait_time = (2 ** attempt) + 1
            st.warning(f"[API Error] {e}. Retry dalam {wait_time:.1f} detik...")
            time.sleep(wait_time)

        except Exception as e:
            st.error(f"[Error Tidak Terduga] {e}")
            break

    return "[Gagal menganalisis dokumen]"

# --- UI ---
st.title("📄 Verifikasi Kelengkapan Dokumen")

is_reklamasi = st.checkbox("Reklamasi (Dokumen 4 wajib diunggah)")

dok1 = st.file_uploader("📄 Upload Dokumen 1", type=["pdf"])
dok2 = st.file_uploader("📄 Upload Dokumen 2", type=["pdf"])
dok3 = st.file_uploader("📄 Upload Dokumen 3", type=["pdf"])
dok4 = None
if is_reklamasi:
    dok4 = st.file_uploader("📄 Upload Dokumen 4", type=["pdf"])

if st.button("🔍 Proses Analisis"):
    if not dok1 or not dok2 or not dok3 or (is_reklamasi and not dok4):
        st.error("⚠️ Semua dokumen wajib diunggah sesuai ketentuan!")
    else:
        hasil_semua = {}
        skor_list = []
        df_hasil = []

        dok_list = [dok1, dok2, dok3, dok4] if is_reklamasi else [dok1, dok2, dok3]
        nama_list = ["dok1", "dok2", "dok3", "dok4"] if is_reklamasi else ["dok1", "dok2", "dok3"]

        for dok, nama in zip(dok_list, nama_list):
            if dok:
                st.info(f"📄 Memproses {nama.upper()} ...")
                teks = baca_pdf(dok)
                hasil = analisis_dokumen(teks, persyaratan[nama])
                hasil_semua[nama] = hasil

                # Ekstraksi skor
                match = re.search(r"Skor\s*[:\-]?\s*(\d+)", hasil)
                skor = int(match.group(1)) if match else 0
                skor_list.append(skor)

                df_hasil.append({
                    "Dokumen": nama.upper(),
                    "Skor": skor,
                    "Hasil Analisis": hasil
                })

                time.sleep(1.5)  # jeda kecil antar dokumen

        # Rekap skor
        total_skor = sum(skor_list)
        rata_skor = total_skor / len(skor_list) if skor_list else 0

        st.subheader("📊 Hasil Analisis Per Dokumen")
        for nama, konten in hasil_semua.items():
            st.markdown(f"**{nama.upper()}**")
            st.markdown(konten)

        st.subheader("📈 Rekapitulasi Skor")
        st.write(f"Total Skor: {total_skor}")
        st.write(f"Rata-rata Skor: {rata_skor:.2f}")
        if rata_skor >= 70:
            st.success("✅ Lolos Verifikasi")
        else:
            st.error("❌ Tidak Lolos Verifikasi")

        # Tampilkan tabel
        st.subheader("📄 Tabel Rekap")
        st.dataframe(pd.DataFrame(df_hasil))
