# streamlit_dashboard_kelengkapan_perizinan.py
# --------------------------------------------------------------
# Jalankan dengan:
#    streamlit run streamlit_dashboard_kelengkapan_perizinan.py
# --------------------------------------------------------------

import io
import re
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import streamlit as st

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

# --------------------------- Keyword Persyaratan ---------------------------
KEYWORDS = {
    "Informasi Kegiatan": [
        r"informasi\s+kegiatan", r"rencana\s+kegiatan", r"uraian\s+kegiatan",
        r"rincian\s+kegiatan", r"gambaran\s+kegiatan", r"profil\s+kegiatan",
        r"deskripsi\s+kegiatan", r"latar\s+belakang\s+kegiatan", r"ringkasan\s+kegiatan",
        r"ruang\s+laut", r"kegiatan\s+utama"
    ],
    "Tujuan": [
        r"tujuan", r"maksud", r"sasaran", r"target", r"orientasi",
        r"objective", r"goal", r"visi", r"misi", r"diharapkan", r"untuk"
    ],
    "Manfaat": [
        r"manfaat", r"kegunaan", r"dampak\s+positif", r"hasil\s+yang\s+diharapkan",
        r"outcome", r"nilai\s+Tambah", r"keuntungan", r"faedah", r"benefit",
        r"meningkatkan", r"menambah", r"mendorong"
    ],
    "Kegiatan Eksisting Yang Dimohonkan": [
        r"kegiatan\s+eksisting", r"kegiatan\s+eksisting\s+yang\s+dimohonkan",
        r"aktivitas\s+yang\s+sedang\s+berjalan",
        r"program\s+berjalan", r"kondisi\s+eksisting", r"usulan\s+kegiatan",
        r"proposal\s+kegiatan", r"permohonan\s+kegiatan",
        r"aktivitas\s+yang\s+diusulkan", r"pembangunan", r"fasilitas"
    ],
    "Jadwal Pelaksanaan Kegiatan": [
        r"jadwal", r"timeline", r"rencana\s+waktu", r"schedule", r"perencanaan\s+waktu",
        r"timeframe", r"tahapan\s+pelaksanaan", r"roadmap", r"matriks\s+waktu"
    ],
    "Rencana Tapak/Siteplan": [
        r"site\s*plan|siteplan", r"rencana\s+tapak", r"denah", r"denah\s+tapak",
        r"gambar\s+tapak", r"layout", r"tata\s+letak", r"masterplan",
        r"sketsa\s+lokasi", r"peta\s+tapak", r"diagram\s+site"
    ],
    "Deskriptif Luasan yang Dibutuhkan": [
        r"luas(?:an)?", r"meter\s*persegi|m2|m\^2|m²|ha|hektar|hektare",
        r"dimensi", r"ukuran", r"kebutuhan\s+luas", r"estimasi\s+luas",
        r"spesifikasi\s+luasan", r"ukuran\s+area", r"kebutuhan\s+lahan",
        r"luas\s+lahan", r"rincian\s+area", r"kapasitas\s+ruang"
    ],
    "Peta Lokasi": [
        r"peta\s+lokasi", r"denah\s+lokasi", r"gambar\s+lokasi",
        r"lokasi\s+proyek", r"map", r"posisi\s+geografis",
        r"koordinat\s+lokasi", r"lokasi\s+tapak", r"sketsa\s+lokasi"
    ],
}

# Alias untuk heading bab → requirement
SECTION_ALIASES = {
    "Informasi Kegiatan": ["informasi kegiatan", "rencana kegiatan"],
    "Tujuan": ["tujuan", "maksud"],
    "Manfaat": ["manfaat"],
    "Kegiatan Eksisting Yang Dimohonkan": ["kegiatan eksisting", "kegiatan eksisting yang dimohonkan", "usulan kegiatan"],
    "Jadwal Pelaksanaan Kegiatan": ["jadwal", "timeline", "rencana jadwal"],
    "Rencana Tapak/Siteplan": ["siteplan", "rencana tapak", "denah"],
    "Deskriptif Luasan yang Dibutuhkan": ["deskriptif luasan", "deskripsi luasan", "luasan", "luas yang dibutuhkan"],
    "Peta Lokasi": ["peta lokasi", "denah lokasi", "lokasi kegiatan"],
}

REQUIREMENTS = [
    {"name": "Informasi Kegiatan", "requires_visual": False, "requires_table": False},
    {"name": "Tujuan", "requires_visual": False, "requires_table": False},
    {"name": "Manfaat", "requires_visual": False, "requires_table": False},
    {"name": "Kegiatan Eksisting Yang Dimohonkan", "requires_visual": False, "requires_table": False},
    {"name": "Jadwal Pelaksanaan Kegiatan", "requires_visual": True, "requires_table": True},
    {"name": "Rencana Tapak/Siteplan", "requires_visual": True, "requires_table": False},
    {"name": "Deskriptif Luasan yang Dibutuhkan", "requires_visual": False, "requires_table": False},
    {"name": "Peta Lokasi", "requires_visual": True, "requires_table": False},
]

NUMBER_PATTERN = re.compile(r"(?<!\d)(?:[1-9]\d{0,2}(?:\.\d{3})*|0)?(?:[\.,]\d+)?\s*(?:m2|m\^2|m²|ha|hektar|hektare|meter\s*persegi)\b")
DATE_PATTERN = re.compile(r"\b(\d{1,2}[\-/]?\d{1,2}[\-/]?\d{2,4}|\bQ[1-4]\b|minggu|bulan|tahun)\b", re.IGNORECASE)

# --------------------------- Segmentasi Dokumen ---------------------------
def segment_document(text: str) -> Dict[str, str]:
    sections = {r["name"]: "" for r in REQUIREMENTS}
    heading_pattern = re.compile(
        r"^(?:\d+(?:\.\d+)*|[A-Z]\.|[A-Z][A-Z\s]{2,})\s+(.+)$",
        re.MULTILINE,
    )

    matches = list(heading_pattern.finditer(text))
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()

        heading = match.group(1).strip().lower()

        # hanya mapping jika heading cocok dengan alias salah satu requirement
        for req, aliases in SECTION_ALIASES.items():
            if any(alias in heading for alias in aliases):
                sections[req] = section_text
                break
        # kalau heading tidak dikenali aliasnya → abaikan saja (tidak isi requirement)

    return sections

# --------------------------- Ekstraksi PDF ---------------------------
def extract_with_pymupdf(file_bytes: bytes) -> Tuple[List[str], Dict[int, int]]:
    text_pages = []
    images_per_page = {}
    if fitz is None:
        return text_pages, images_per_page
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    for i, page in enumerate(doc):
        text_pages.append(page.get_text("text") or "")
        images_per_page[i] = len(page.get_images(full=True))
    return text_pages, images_per_page

def extract_with_pypdf2(file_bytes: bytes) -> List[str]:
    text_pages = []
    if PdfReader is None:
        return text_pages
    reader = PdfReader(io.BytesIO(file_bytes))
    for page in reader.pages:
        try:
            text_pages.append(page.extract_text() or "")
        except Exception:
            text_pages.append("")
    return text_pages

def detect_tables_with_pdfplumber(file_bytes: bytes) -> Dict[int, int]:
    table_counts = {}
    if pdfplumber is None:
        return table_counts
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                tables = page.find_tables() or []
                table_counts[i] = len(tables)
            except Exception:
                table_counts[i] = 0
    return table_counts

# --------------------------- Analisis ---------------------------
def analyze_pdf(file_bytes: bytes) -> Dict:
    text_pages, images_per_page = extract_with_pymupdf(file_bytes)
    if not text_pages:
        text_pages = extract_with_pypdf2(file_bytes)
    table_counts = detect_tables_with_pdfplumber(file_bytes)

    full_text = "\n".join(text_pages).lower()
    segmented = segment_document(full_text)

    results = []
    for req in REQUIREMENTS:
        name = req["name"]
        segment_text = segmented.get(name, "")
        found_text = any(re.search(p, segment_text) for p in KEYWORDS.get(name, []))

        # fallback: deteksi gambar/tabel dari teks (jika extractor gagal)
        visual_ok, table_ok, notes = True, True, []
        if req["requires_visual"]:
            if sum(images_per_page.values()) == 0 and "gambar" not in segment_text:
                visual_ok = False
                notes.append("Wajib menyertakan gambar pada bab ini.")
        if req["requires_table"]:
            if sum(table_counts.values()) == 0 and "tabel" not in segment_text:
                table_ok = False
                notes.append("Wajib menyertakan tabel pada bab ini.")
        if not found_text:
            notes.append("Kata kunci terkait belum ditemukan.")

        status = found_text and visual_ok and table_ok
        results.append({
            "Persyaratan": name,
            "Ditemukan Teks": "✅" if found_text else "❌",
            "Ada Gambar/Tabel (Jika Wajib)": "✅" if (visual_ok and table_ok) else "❌" if (req["requires_visual"] or req["requires_table"]) else "N/A",
            "Status": "✅ LENGKAP" if status else "❌ BELUM LENGKAP",
        })

    total_req = len(results)
    total_ok = sum(1 for r in results if r["Status"].startswith("✅"))
    completeness = round((total_ok / total_req) * 100, 1) if total_req else 0.0

    stats = {
        "Jumlah Halaman": len(text_pages),
        "Jumlah Kata (perkiraan)": sum(len(p.split()) for p in text_pages),
        "Jumlah Gambar (terdeteksi)": sum(images_per_page.values()),
        "Jumlah Tabel (terdeteksi)": sum(table_counts.values()),
        "Kompleteness %": completeness,
    }
    return {"results": results, "stats": stats}

# --------------------------- UI ---------------------------
def main():
    st.set_page_config(page_title="Analisis Kelengkapan Perizinan", page_icon="📄", layout="wide")
    st.title("📄 Dashboard Analisis Kelengkapan & Kesesuaian Dokumen Perizinan")

    with st.sidebar:
        st.header("⚙️ Pengaturan")
        st.info("Unggah dokumen PDF, sistem akan memeriksa kelengkapan bab.")

    uploaded_file = st.file_uploader("Unggah PDF", type=["pdf"])
    if uploaded_file is None:
        st.stop()

    with st.spinner("Menganalisis dokumen..."):
        analysis = analyze_pdf(uploaded_file.read())

    stats = analysis["stats"]
    results = pd.DataFrame(analysis["results"])

    st.subheader("Ringkasan Dokumen")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Halaman", stats["Jumlah Halaman"])
    col2.metric("Kata (≈)", stats["Jumlah Kata (perkiraan)"])
    col3.metric("Gambar", stats["Jumlah Gambar (terdeteksi)"])
    col4.metric("Tabel", stats["Jumlah Tabel (terdeteksi)"])
    col5.metric("Kelengkapan", f"{stats['Kompleteness %']}%")

    st.subheader("Checklist Kelengkapan & Kesesuaian")
    st.dataframe(results, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
