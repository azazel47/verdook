import io
import re
from typing import Dict, List
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
    "Informasi Pemohon": [
        r"informasi\s+kegiatan", r"informasi\s+pemohon", r"rencana\s+kegiatan",
        r"uraian\s+kegiatan", r"profil", r"nama", r"alamat"
    ],
    "Tujuan": [
        r"tujuan", r"maksud", r"sasaran", r"target", r"orientasi",
        r"objective", r"goal", r"visi", r"misi"
    ],
    "Manfaat": [
        r"manfaat", r"kegunaan", r"dampak\s+positif", r"hasil\s+yang\s+diharapkan",
        r"outcome", r"nilai\s+Tambah", r"keuntungan", r"faedah", r"benefit"
    ],
    "Kegiatan Eksisting Yang Dimohonkan": [
        r"kegiatan\s+eksisting", r"kegiatan\s+eksisting\s+yang\s+dimohonkan",
        r"aktivitas\s+yang\s+sedang\s+berjalan", r"kondisi\s+eksisting",
        r"usulan\s+kegiatan", r"proposal\s+kegiatan", r"permohonan\s+kegiatan",
        r"pembangunan", r"fasilitas"
    ],
    "Jadwal Pelaksanaan Kegiatan": [
        r"jadwal", r"timeline", r"rencana\s+waktu", r"schedule",
        r"tahapan\s+pelaksanaan", r"roadmap", r"matriks\s+waktu"
    ],
    "Rencana Tapak/Siteplan": [
        r"site\s*plan|siteplan", r"rencana\s+tapak", r"denah",
        r"gambar\s+tapak", r"layout", r"masterplan",
        r"peta\s+tapak", r"diagram\s+site"
    ],
    "Deskriptif Luasan yang Dibutuhkan": [
        r"luas(?:an)?", r"meter\s*persegi|m2|m\^2|m²|ha|hektar|hektare",
        r"dimensi", r"ukuran", r"kebutuhan\s+luas", r"estimasi\s+luas",
        r"spesifikasi\s+luasan", r"luas\s+lahan", r"kapasitas\s+ruang"
    ],
    "Peta Lokasi": [
        r"peta\s+lokasi", r"denah\s+lokasi", r"gambar\s+lokasi",
        r"lokasi\s+proyek", r"map", r"posisi\s+geografis",
        r"koordinat\s+lokasi", r"lokasi\s+tapak", r"sketsa\s+lokasi"
    ],
}

SECTION_ALIASES = {
    "Informasi Pemohon": ["informasi kegiatan", "rencana kegiatan", "informasi pemohon"],
    "Tujuan": ["tujuan", "maksud"],
    "Manfaat": ["manfaat"],
    "Kegiatan Eksisting Yang Dimohonkan": ["kegiatan eksisting", "usulan kegiatan"],
    "Jadwal Pelaksanaan Kegiatan": ["jadwal", "timeline"],
    "Rencana Tapak/Siteplan": ["siteplan", "rencana tapak", "denah"],
    "Deskriptif Luasan yang Dibutuhkan": ["luasan", "luas", "kebutuhan lahan"],
    "Peta Lokasi": ["peta lokasi", "denah lokasi", "lokasi kegiatan"]
}

REQUIREMENTS = [
    {"name": "Informasi Pemohon", "requires_visual": False, "requires_table": False},
    {"name": "Tujuan", "requires_visual": False, "requires_table": False},
    {"name": "Manfaat", "requires_visual": False, "requires_table": False},
    {"name": "Kegiatan Eksisting Yang Dimohonkan", "requires_visual": False, "requires_table": False},
    {"name": "Jadwal Pelaksanaan Kegiatan", "requires_visual": True, "requires_table": True},
    {"name": "Rencana Tapak/Siteplan", "requires_visual": True, "requires_table": False},
    {"name": "Deskriptif Luasan yang Dibutuhkan", "requires_visual": False, "requires_table": False},
    {"name": "Peta Lokasi", "requires_visual": True, "requires_table": False}
]


# --------------------------- Segmentasi Dokumen ---------------------------
def segment_document(doc) -> Dict[str, str]:
    sections = {r["name"]: "" for r in REQUIREMENTS}
    headings_found = []
    headings = {}

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" not in b:
                continue
            for l in b["lines"]:
                line_text = " ".join([s["text"] for s in l["spans"]]).strip()
                if not line_text:
                    continue

                clean_text = line_text.lower()

                for req, aliases in SECTION_ALIASES.items():
                    for alias in aliases:
                        alias_lower = alias.lower()

                        # cek apakah alias ada dalam teks
                        if alias_lower in clean_text:
                            # cek apakah ada span bold
                            is_bold = any(
                                (s.get("flags", 0) & 2) or ("bold" in s.get("font", "").lower())
                                for s in l["spans"]
                            )
                            if is_bold:
                                headings_found.append((req, page_num, l["bbox"], line_text))
                                headings[req] = line_text
                                break

    # Segmentasi antar heading
    for i, (req, page_num, bbox, heading_text) in enumerate(headings_found):
        end_page, _ = (
            (headings_found[i+1][1], headings_found[i+1][2])
            if i+1 < len(headings_found) else (len(doc)-1, None)
        )
        content_parts = []
        for p in range(page_num, end_page+1):
            page = doc[p]
            content_parts.append(page.get_text("text"))
        sections[req] = "\n".join(content_parts)

    return sections, headings

# --------------------------- Ekstraksi PDF ---------------------------
def extract_with_pymupdf(file_bytes: bytes):
    if fitz is None:
        return None, [], {}
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_pages = [p.get_text("text") or "" for p in doc]
    images_per_page = {i: len(p.get_images(full=True)) for i, p in enumerate(doc)}
    return doc, text_pages, images_per_page


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
    doc, text_pages, images_per_page = extract_with_pymupdf(file_bytes)
    if doc is None:
        text_pages = extract_with_pypdf2(file_bytes)
        images_per_page = {}
        return {"results": [], "stats": {}}

    table_counts = detect_tables_with_pdfplumber(file_bytes)
    segmented, headings = segment_document(doc)

    results = []
    for req in REQUIREMENTS:
        name = req["name"]
        segment_text = segmented.get(name, "").lower()
        found_text = any(re.search(p, segment_text) for p in KEYWORDS.get(name, []))

        visual_ok, table_ok = True, True
        if name in ["Jadwal Pelaksanaan Kegiatan", "Rencana Tapak/Siteplan", "Peta Lokasi"]:
            if req["requires_visual"] and sum(images_per_page.values()) == 0:
                visual_ok = False
            if req["requires_table"] and sum(table_counts.values()) == 0:
                table_ok = False
            status = found_text and visual_ok and table_ok
        else:
            status = found_text
            visual_ok = sum(images_per_page.values()) > 0
            table_ok = sum(table_counts.values()) > 0

        results.append({
            "Persyaratan": name,
            "Judul SubBab": headings.get(name, "-"),
            "Ditemukan Teks": "✅" if found_text else "❌",
            "Ada Gambar/Tabel (Jika Wajib)": "✅" if (visual_ok or table_ok) else "❌",
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
        st.info("Unggah dokumen PDF, sistem akan memeriksa kelengkapan bab/subbab sesuai aturan.")

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
    st.dataframe(results, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
