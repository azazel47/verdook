import streamlit as st
from io import BytesIO
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
    "rencana jadwal pelaksanaan kegiatan", 
    "Rencana tapak/site plan kegiatan",
    "deskriptif luasan",
    "Peta lokasi/plotting batas-batas area"
]

def extract_text_and_images(file_bytes: bytes, filename: str):
    lower = filename.lower()
    text = ""
    has_image = False

    if lower.endswith('.pdf'):
        try:
            reader = PdfReader(BytesIO(file_bytes))
            for page in reader.pages:
                text += page.extract_text() or ""
                # cek apakah ada objek gambar di halaman PDF
                if "/XObject" in page.get("/Resources", {}):
                    xobj = page["/Resources"]["/XObject"].get_object()
                    for obj in xobj:
                        if xobj[obj]["/Subtype"] == "/Image":
                            has_image = True
        except Exception as e:
            st.error(f"Gagal mengekstrak teks PDF: {e}")

    elif lower.endswith('.txt'):
        text = file_bytes.decode('utf-8', errors='ignore')
        has_image = False

    elif lower.endswith(('.png', '.jpg', '.jpeg')):
        img = Image.open(BytesIO(file_bytes))
        text = pytesseract.image_to_string(img)
        has_image = True  # karena berupa gambar

    else:
        st.warning("Format file tidak didukung untuk ekstraksi teks selain PDF, TXT, atau gambar.")
    return text, has_image

def verify_document(text: str, has_image: bool) -> dict:
    results = {}
    for section in REQUIRED_SECTIONS:
        results[section] = bool(re.search(re.escape(section), text, re.IGNORECASE))

    # Check for coordinates format (latitude, longitude)
    coord_pattern = r"-?\d{1,3}\.\d+\s*,\s*-?\d{1,3}\.\d+"
    results['koordinat_ditemukan'] = bool(re.search(coord_pattern, text))

    # --- Additional requirements ---
    if results["rencana jadwal pelaksanaan kegiatan"]:
        results["jadwal_memiliki_tabel_gambar"] = has_image  # asumsi ada gambar/tabel jika ada image di dokumen
    else:
        results["jadwal_memiliki_tabel_gambar"] = False

    if results["Peta lokasi/plotting batas-batas area"]:
        results["peta_memiliki_gambar"] = has_image
    else:
        results["peta_memiliki_gambar"] = False

    return results

st.title("Verifikasi Dokumen Perizinan")
st.write("Upload dokumen perizinan (PDF, TXT, PNG, JPG) untuk memeriksa kelengkapan persyaratan.")

uploaded = st.file_uploader("Pilih file dokumen", type=['pdf', 'txt', 'png', 'jpg', 'jpeg'])
if uploaded:
    file_bytes = uploaded.read()
    with st.spinner('Ekstraksi teks dari dokumen...'):
        extracted, has_image = extract_text_and_images(file_bytes, uploaded.name)

    st.subheader("Teks yang diekstrak (preview)")
    st.text_area("Extracted text", value=extracted[:5000], height=300)

    st.subheader("Hasil Verifikasi")
    checks = verify_document(extracted, has_image)
    st.json(checks)

    completeness = sum(1 for v in checks.values() if v) / len(checks) * 100
    st.write(f"**Persentase kelengkapan dokumen:** {completeness:.2f}%")
else:
    st.info("Unggah dokumen untuk memulai verifikasi.")
