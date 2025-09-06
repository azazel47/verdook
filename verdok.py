# Streamlit Dashboard Analisis Kesesuaian & Kelengkapan Dokumen Perizinan
# --------------------------------------------------------------
# Cara pakai:
# 1) Pastikan Python 3.9+ terpasang.
# 2) (Opsional) Buat virtualenv, lalu install dependensi:
#    pip install streamlit pymupdf pdfplumber PyPDF2 pandas numpy
# 3) Jalankan aplikasi:
#    streamlit run streamlit_dashboard_kelengkapan_perizinan.py
# --------------------------------------------------------------

import io
import re
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# Library PDF
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

# --------------------------- Keywords ---------------------------
KEYWORDS = {
    "Informasi Kegiatan": [
        r"informasi\s+kegiatan", r"deskripsi\s+kegiatan", r"gambaran\s+umum",
        r"kegiatan", r"uraian\s+kegiatan", r"rincian\s+kegiatan", r"gambaran\s+kegiatan",
        r"profil\s+kegiatan", r"latar\s+belakang\s+kegiatan", r"ringkasan\s+kegiatan", r"rencana\s+kegiatan"
    ],
    "Tujuan": [
        r"tujuan", r"maksud", r"sasaran", r"target", r"orientasi", r"objective",
        r"goal", r"visi", r"misi"
    ],
    "Manfaat": [
        r"manfaat", r"kegunaan", r"dampak\s+positif", r"hasil\s+yang\s+diharapkan",
        r"outcome", r"nilai\s+Tambah", r"keuntungan", r"faedah", r"benefit"
    ],
    "Kegiatan Eksisting Yang Dimohonkan": [
        r"kegiatan\s+eksisting", r"yang\s+dimohonkan", r"existing\s+activity",
        r"aktivitas\s+yang\s+sedang\s+berjalan", r"program\s+berjalan", r"kondisi\s+eksisting",
        r"rencana\s+kegiatan", r"usulan\s+kegiatan", r"proposal\s+kegiatan",
        r"permohonan\s+kegiatan", r"aktivitas\s+yang\s+diusulkan"
    ],
    "Jadwal Pelaksanaan Kegiatan": [
        r"jadwal", r"timeline", r"rencana\s+pelaksanaan", r"tahapan",
        r"rencana\s+waktu", r"schedule", r"perencanaan\s+waktu", r"timeframe",
        r"tahapan\s+pelaksanaan", r"roadmap", r"matriks\s+waktu"
    ],
    "Rencana Tapak/Siteplan": [
        r"site\s*plan|siteplan", r"rencana\s+tapak", r"denah", r"denah\s+tapak",
        r"gambar\s+tapak", r"layout", r"tata\s+letak", r"masterplan",
        r"sketsa\s+lokasi", r"peta\s+tapak", r"diagram\s+site"
    ],
    "Deskriptif luasan yang dibutuhkan": [
        r"luas(?:an)?", r"meter\s*persegi|m2|m\^2|m²|ha|hektar|hektare",
        r"dimensi", r"ukuran", r"kebutuhan\s+luas", r"estimasi\s+luas",
        r"spesifikasi\s+luasan", r"ukuran\s+area", r"kebutuhan\s+lahan",
        r"luas\s+lahan", r"rincian\s+area", r"kapasitas\s+ruang"
    ],
    "Peta Lokasi": [
        r"peta\s+lokasi", r"lokasi", r"map", r"koordinat",
        r"denah\s+lokasi", r"gambar\s+lokasi", r"lokasi\s+proyek",
        r"posisi\s+geografis", r"koordinat\s+lokasi", r"lokasi\s+tapak",
        r"sketsa\s+lokasi"
    ],
}

REQUIREMENTS = [
    {"name": "Informasi Kegiatan", "requires_visual": False, "requires_table": False},
    {"name": "Tujuan", "requires_visual": False, "requires_table": False},
    {"name": "Manfaat", "requires_visual": False, "requires_table": False},
    {"name": "Kegiatan Eksisting Yang Dimohonkan", "requires_visual": False, "requires_table": False},
    {"name": "Jadwal Pelaksanaan Kegiatan", "requires_visual": True, "requires_table": True},
    {"name": "Rencana Tapak/Siteplan", "requires_visual": True, "requires_table": False},
    {"name": "Deskriptif luasan yang dibutuhkan", "requires_visual": False, "requires_table": False},
    {"name": "Peta Lokasi", "requires_visual": True, "requires_table": False},
]

NUMBER_PATTERN = re.compile(r"(?<!\d)(?:[1-9]\d{0,2}(?:\.\d{3})*|0)?(?:[\.,]\d+)?\s*(?:m2|m\^2|m²|ha|hektar|hektare|meter\s*persegi|m|meter)\b")
DATE_PATTERN = re.compile(r"\b(\d{1,2}[\-/]?(\d{1,2}|jan|feb|mar|apr|mei|jun|jul|agu|sep|okt|nov|des)[\-/]?\d{2,4}|\bQ[1-4]\b|minggu|bulan|tahun)\b", re.IGNORECASE)

# --------------------------- Segmentasi Dokumen ---------------------------
def segment_document(text: str, requirement_names: List[str]) -> Dict[str, Dict]:
    """
    Membagi dokumen ke dalam segmen berdasarkan heading bab.
    Heading dicocokkan dengan KEYWORDS agar fleksibel.
    """
    sections = {name: {"text": "", "pages": []} for name in requirement_names}
    heading_pattern = re.compile(r"^(\d+)\.\s*(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(text))

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        heading_text = match.group(2).strip().lower()

        matched_req = None
        for req in requirement_names:
            patterns = KEYWORDS.get(req, [])
            if any(re.search(pat, heading_text) for pat in patterns):
                matched_req = req
                break

        if matched_req:
            sections[matched_req]["text"] = section_text
            # hitung halaman perkiraan
            start_page = text[:start].count("\f")
            end_page = text[:end].count("\f")
            page_range = list(range(start_page, max(start_page+1, end_page+1)))
            sections[matched_req]["pages"] = page_range

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
    reader = PdfReader(io.BytesIO(file_bytes))  # FIX pakai BytesIO
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
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:  # FIX pakai BytesIO
        for i, page in enumerate(pdf.pages):
            try:
                tables = page.find_tables() or []
                table_counts[i] = len(tables)
            except Exception:
                table_counts[i] = 0
    return table_counts

# --------------------------- Analisis ---------------------------
def clean_text(t: str) -> str:
    t = t or ""
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()

def analyze_pdf(file_bytes: bytes) -> Dict:
    text_pages, images_per_page = extract_with_pymupdf(file_bytes)
    if not text_pages:
        text_pages = extract_with_pypdf2(file_bytes)
    table_counts = detect_tables_with_pdfplumber(file_bytes)

    text_pages = [clean_text(t) for t in text_pages]
    full_text = "\f".join(text_pages)
    sections = segment_document(full_text, [r["name"] for r in REQUIREMENTS])

    results = []
    for req in REQUIREMENTS:
        name = req["name"]
        section = sections.get(name, {"text": "", "pages": []})
        section_text = section["text"]
        section_pages = section["pages"]

        found_text = any(re.search(pat, section_text) for pat in KEYWORDS.get(name, []))
        visual_ok = not req["requires_visual"] or any(images_per_page.get(p, 0) > 0 for p in section_pages)
        table_ok = not req["requires_table"] or any(table_counts.get(p, 0) > 0 for p in section_pages)

        notes = []
        if not found_text:
            notes.append("Kata kunci terkait belum ditemukan.")
        if req["requires_visual"] and not visual_ok:
            notes.append("Wajib ada gambar pada bab ini.")
        if req["requires_table"] and not table_ok:
            notes.append("Wajib ada tabel pada bab ini.")

        if name == "Deskriptif luasan yang dibutuhkan":
            if not re.search(NUMBER_PATTERN, section_text):
                notes.append("Tidak ditemukan angka + satuan (m²/m2/ha).")

        if name == "Jadwal Pelaksanaan Kegiatan":
            if not re.search(DATE_PATTERN, section_text):
                notes.append("Pertimbangkan menambahkan tanggal/periode/quarter pada jadwal.")

        status = found_text and visual_ok and table_ok
        results.append({
            "Persyaratan": name,
            "Ditemukan Teks": "✅" if found_text else "❌",
            "Ada Gambar/Tabel (Jika Wajib)": "✅" if (visual_ok and table_ok) else "❌" if (req["requires_visual"] or req["requires_table"]) else "N/A",
            "Status": "✅ LENGKAP" if status else "❌ BELUM LENGKAP",
            "Catatan": "; ".join(notes) if notes else "",
            "Halaman Bukti (perkiraan, 1-based)": ", ".join(str(i+1) for i in section_pages) if section_pages else "-",
        })

    total_req = len(results)
    total_ok = sum(1 for r in results if r["Status"].startswith("✅"))
    completeness = round((total_ok / total_req) * 100, 1) if total_req else 0.0

    n_pages = max(len(text_pages), max(images_per_page.keys(), default=-1) + 1, max(table_counts.keys(), default=-1) + 1)
    n_images = sum(images_per_page.values())
    n_tables = sum(table_counts.values())
    n_words = sum(len(p.split()) for p in text_pages)

    return {
        "results": results,
        "stats": {
            "Jumlah Halaman": n_pages,
            "Jumlah Kata (perkiraan)": n_words,
            "Jumlah Gambar (terdeteksi)": n_images,
            "Jumlah Tabel (terdeteksi)": n_tables,
            "Kompleteness %": completeness,
        },
    }

# --------------------------- UI ---------------------------
def main():
    st.set_page_config(page_title="Analisis Kelengkapan Perizinan", page_icon="📄", layout="wide")
    st.title("📄 Dashboard Analisis Kelengkapan & Kesesuaian Dokumen Perizinan")

    with st.sidebar:
        st.header("⚙️ Pengaturan")
        st.markdown(
            """
            Unggah dokumen permohonan izin (PDF), lalu aplikasi akan:
            1) Mengekstrak teks, gambar, dan tabel.
            2) Memeriksa kelengkapan berdasarkan daftar persyaratan.
            3) Menyajikan checklist hasil analisis dan ringkasan.
            """
        )

    uploaded_file = st.file_uploader("Unggah PDF dokumen permohonan izin", type=["pdf"])
    if not uploaded_file:
        st.info("Silakan unggah file PDF untuk mulai analisis.")
        st.stop()

    with st.spinner("Menganalisis dokumen..."):
        analysis = analyze_pdf(uploaded_file.read())

    st.subheader("Ringkasan Dokumen")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Halaman", analysis["stats"]["Jumlah Halaman"])
    col2.metric("Kata (≈)", analysis["stats"]["Jumlah Kata (perkiraan)"])
    col3.metric("Gambar", analysis["stats"]["Jumlah Gambar (terdeteksi)"])
    col4.metric("Tabel", analysis["stats"]["Jumlah Tabel (terdeteksi)"])
    col5.metric("Kelengkapan", f"{analysis['stats']['Kompleteness %']}%")

    st.subheader("Checklist Kelengkapan & Kesesuaian")
    df = pd.DataFrame(analysis["results"])
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("Ekspor Hasil")
    st.download_button(
        label="⬇️ Unduh Laporan (JSON)",
        data=pd.Series(analysis).to_json(force_ascii=False, indent=2),
        file_name=f"laporan_kelengkapan.json",
        mime="application/json",
    )

if __name__ == "__main__":
    main()
