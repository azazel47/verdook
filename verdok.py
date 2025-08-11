import streamlit as st
import openai

# =========================
# KONFIGURASI API KEY
# =========================
# Ambil API key dari Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# =========================
# FUNGSI ANALISIS DOKUMEN
# =========================
def analisis_ai(teks_dokumen):
    prompt = f"""
    Anda adalah asisten AI yang bertugas memverifikasi isi dokumen.
    Baca teks dokumen berikut dan berikan analisis yang jelas:
    - Apakah dokumen lengkap?
    - Apakah ada data yang tidak konsisten?
    - Ringkas isi dokumen.

    Teks Dokumen:
    {teks_dokumen}
    """

    client = openai.OpenAI(api_key=openai.api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Anda adalah analis dokumen yang teliti."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content

# =========================
# APLIKASI STREAMLIT
# =========================
st.set_page_config(page_title="Verifikasi Dokumen AI", page_icon="📄", layout="wide")
st.title("📄 Verifikasi Dokumen dengan AI")

uploaded_file = st.file_uploader("Unggah dokumen (TXT atau PDF)", type=["txt", "pdf"])

if uploaded_file is not None:
    # Baca isi file
    if uploaded_file.type == "application/pdf":
        import fitz  # PyMuPDF
        pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        teks = ""
        for halaman in pdf:
            teks += halaman.get_text()
    else:
        teks = uploaded_file.read().decode("utf-8", errors="ignore")

    st.subheader("📜 Isi Dokumen")
    st.text_area("Teks dokumen:", teks, height=300)

    if st.button("🔍 Analisis Dokumen"):
        with st.spinner("Sedang menganalisis dokumen..."):
            hasil = analisis_ai(teks)
        st.subheader("📊 Hasil Analisis AI")
        st.write(hasil)
