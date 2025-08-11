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
    Periksa dokumen berikut:
1) Ekosistem sekitar:
i. Mangrove ( disampaikan secara detail disertai narasi,peta/gambar,
sumber data) yang mencakup:
•	Penjelasan terkait informasi jenis;
•	Penjelasan terkait informasi persentase penutupan mangrove;
•	Penjelasan terkait informasi luasan.
ii. Lamun ( disampaikan secara detail disertai narasi,peta/gambar, sumber
data) yang mencakup);
•	Penjelasan terkait informasi jenis;
•	Penjelasan terkait informasi persentase penutupan padang lamun kaya/sehat;
•	Penjelasan terkait informasi luasan.
iii. Terumbu Karang ( disampaikan secara detail disertai narasi,
peta/gambar, sumber data) yang mencakup:
•	Penjelasan terkait informasi jenis terumbu karang
•	penjelasan terkait informasi persentase tutupan karang hidup;
•	Penjelasan terkait informasi luasan.
2) Permodelan data hidro-oseanografi:
i. arus ( disertai narasi (pasang surut campuran harian gand atau yg lainnya),peta/gambar, sumber data)
ii. gelombang ( disertai narasi,peta/gambar, sumber data)
iii. pasang surut ( disertai narasi,peta/gambar, sumber data)
iv. batimetri ( disertai narasi,peta/gambar, sumber data)

3) Profil dasar laut disertai narasi (berlumpur/berbatu/dll) dan gambar dokumentasi dasar laut atau profil penampang melintang;
4) kondisi/karakteristik sosial ekonomi masyarakat (mata pencaharian
masyarakat sekitar); dan
5) Aksesibilitas lokasi dan sekitar


    Aturan tambahan:
    - Setiap narasi hidrooseanografi HARUS menyebutkan nilai numerik (contoh kedalaman, kecepatan arus, tinggi gelombang, dsb.).
    - Berikan skor 0-100 untuk setiap poin.
    - Buat tabel checklist berwarna: hijau (lengkap), kuning (kurang lengkap), merah (tidak ada).
    - Berikan ringkasan hasil analisis di akhir.
    - Pada data ekosistem, jika dilokasi tidak terdapat magnrove/lamun/terumbu karang skors tetap hijau jika dijelaskan dalam narasi tidak ada. Namun jika tidak ada keterangan apapun maka merah

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
