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

# Library PDF opsional: PyMuPDF (fitz) untuk gambar, pdfplumber untuk tabel
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

# --------------------------- Util Helpers ---------------------------
KEYWORDS = {
    "Informasi Kegiatan": [
        r"informasi\s+kegiatan", r"deskripsi\s+kegiatan", r"gambaran\s+umum",
        r"kegiatan", r"uraian\s+kegiatan", r"rincian\s+kegiatan", r"gambaran\s+kegiatan",
        r"profil\s+kegiatan", r"deskripsi\s+kegiatan", r"latar\s+belakang\s+kegiatan",
        r"ringkasan\s+kegiatan"
    ],
    "Tujuan": [
        r"tujuan", r"maksud", r"sasaran", r"target", r"orientasi", r"objective", r"goal",
        r"visi", r"misi"
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

# Aturan:
# - Rencana Tapak/Siteplan → wajib ada gambar
# - Peta Lokasi → wajib ada gambar
# - Jadwal Pelaksanaan Kegiatan → wajib ada gambar ATAU tabel
REQUIREMENTS = [
    {"name": "Informasi Kegiatan", "requires_visual": False, "requires_table": False},
    {"name": "Tujuan", "requires_visual": False, "requires_table": False},
    {"name": "Manfaat", "requires_visual": False, "requires_table": False},
    {"name": "Kegiatan Eksisting Yang Dimohonkan", "requires_visual": False, "requires_table": False},
    {"name": "Jadwal Pelaksanaan Kegiatan", "requires_visual": True, "requires_table": True},  # salah satu wajib
    {"name": "Rencana Tapak/Siteplan", "requires_visual": True, "requires_table": False},
    {"name": "Deskriptif luasan yang dibutuhkan", "requires_visual": False, "requires_table": False},
    {"name": "Peta Lokasi", "requires_visual": True, "requires_table": False},
]

NUMBER_PATTERN = re.compile(r"(?<!\d)(?:[1-9]\d{0,2}(?:\.\d{3})*|0)?(?:[\.,]\d+)?\s*(?:m2|m\^2|m²|ha|hektar|hektare|meter\s*persegi|m|meter)\b")
DATE_PATTERN = re.compile(r"\b(\d{1,2}[\-/]?(\d{1,2}|jan|feb|mar|apr|mei|jun|jul|agu|sep|okt|nov|des)[\-/]?\d{2,4}|\bQ[1-4]\b|minggu|bulan|tahun)\b", re.IGNORECASE)

# (sisanya tetap sama seperti versi sebelumnya: fungsi ekstraksi, analisis, UI)

def clean_text(t: str) -> str:
    t = t or ""
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def find_keyword_hits(text_pages: List[str], patterns: List[str]) -> Dict[int, List[str]]:
    hits = {}
    for i, page_text in enumerate(text_pages):
        low = page_text.lower()
        matched = []
        for p in patterns:
            if re.search(p, low):
                matched.append(p)
        if matched:
            hits[i] = matched
    return hits


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


def score_requirement(name: str,
                      keyword_hits: Dict[int, List[str]],
                      images_per_page: Dict[int, int],
                      table_counts: Dict[int, int],
                      text_pages: List[str]) -> Dict:
    requires_visual = next(r for r in REQUIREMENTS if r["name"] == name)["requires_visual"]
    requires_table = next(r for r in REQUIREMENTS if r["name"] == name)["requires_table"]

    found_text = len(keyword_hits) > 0
    pages_with_text = sorted(keyword_hits.keys())

    def _sum_counts(indices: List[int], mapping: Dict[int, int]):
        return sum(mapping.get(i, 0) for i in indices)

    visual_on_same = _sum_counts(pages_with_text, images_per_page)
    tables_on_same = _sum_counts(pages_with_text, table_counts)

    any_visual = sum(images_per_page.values()) if images_per_page else 0
    any_table = sum(table_counts.values()) if table_counts else 0

    visual_ok = (visual_on_same > 0) or (not pages_with_text and any_visual > 0) if requires_visual else True
    table_ok = (tables_on_same > 0) or (not pages_with_text and any_table > 0) if requires_table else True

    notes = []
    evidence_pages = pages_with_text[:3]

    if name == "Deskriptif luasan yang dibutuhkan":
        area_hits = {}
        for i, t in enumerate(text_pages):
            if re.search(NUMBER_PATTERN, t.lower()):
                area_hits[i] = True
        if area_hits:
            evidence_pages = sorted(set(evidence_pages + list(area_hits.keys())[:2]))
        else:
            notes.append("Tidak ditemukan angka + satuan (m²/m2/meter persegi).")

    if name == "Jadwal Pelaksanaan Kegiatan":
        got_dateword = False
        for i in pages_with_text:
            if re.search(DATE_PATTERN, text_pages[i].lower()):
                got_dateword = True
                break
        if not got_dateword:
            notes.append("Pertimbangkan menambahkan tanggal/periode/quarter pada jadwal.")

    status = found_text and visual_ok and table_ok

    if requires_visual and not visual_ok:
        notes.append("Wajib menyertakan gambar pada bagian ini (idealnya pada halaman yang sama).")
    if requires_table and not table_ok:
        notes.append("Wajib menyertakan tabel pada bagian ini (idealnya pada halaman yang sama).")
    if not found_text:
        notes.append("Kata kunci terkait belum ditemukan.")

    return {
        "Persyaratan": name,
        "Ditemukan Teks": "✅" if found_text else "❌",
        "Ada Gambar/Tabel (Jika Wajib)": "✅" if (visual_ok and table_ok) else "❌" if (requires_visual or requires_table) else "N/A",
        "Status": "✅ LENGKAP" if status else "❌ BELUM LENGKAP",
        "Catatan": "; ".join(notes) if notes else "",
        "Halaman Bukti (perkiraan, 1-based)": ", ".join(str(i+1) for i in evidence_pages) if evidence_pages else "-",
    }


def analyze_pdf(file_bytes: bytes) -> Dict:
    text_pages, images_per_page = extract_with_pymupdf(file_bytes)
    if not text_pages:
        text_pages = extract_with_pypdf2(file_bytes)
    table_counts = detect_tables_with_pdfplumber(file_bytes)
    text_pages = [clean_text(t) for t in text_pages]

    results = []
    for req in REQUIREMENTS:
        name = req["name"]
        patterns = KEYWORDS.get(name, [])
        hits = find_keyword_hits(text_pages, patterns)
        row = score_requirement(name, hits, images_per_page, table_counts, text_pages)
        results.append(row)

    total_req = len(results)
    total_ok = sum(1 for r in results if r["Status"].startswith("✅"))
    completeness = round((total_ok / total_req) * 100, 1) if total_req else 0.0

    n_pages = max(len(text_pages), max(images_per_page.keys(), default=-1) + 1, max(table_counts.keys(), default=-1) + 1)
    n_images = sum(images_per_page.values()) if images_per_page else 0
    n_tables = sum(table_counts.values()) if table_counts else 0
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

        **Catatan:** Deteksi bersifat *heuristic*. Silakan tinjau catatan pada tiap persyaratan.
        """
    )

uploaded = st.file_uploader("Unggah PDF dokumen permohonan izin", type=["pdf"]) 

if uploaded is None:
    st.info("Silakan unggah file PDF untuk mulai analisis.")
    st.stop()

file_bytes = uploaded.read()

with st.spinner("Menganalisis dokumen..."):
    try:
        output = analyze_pdf(file_bytes)
    except Exception as e:
        st.error(f"Gagal menganalisis PDF: {e}")
        st.stop()

st.subheader("Ringkasan Dokumen")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Halaman", output["stats"].get("Jumlah Halaman", 0))
col2.metric("Kata (≈)", output["stats"].get("Jumlah Kata (perkiraan)", 0))
col3.metric("Gambar", output["stats"].get("Jumlah Gambar (terdeteksi)", 0))
col4.metric("Tabel", output["stats"].get("Jumlah Tabel (terdeteksi)", 0))
col5.metric("Kelengkapan", f"{output['stats'].get('Kompleteness %', 0.0)}%")

st.subheader("Checklist Kelengkapan & Kesesuaian")
df = pd.DataFrame(output["results"]) 

status_colors = {"✅ LENGKAP": "#22c55e", "❌ BELUM LENGKAP": "#ef4444"}

def style_df(d: pd.DataFrame):
    styler = d.style.format(na_rep="-")
    styler = styler.apply(lambda s: [
        "background-color: %s; color: white; font-weight: 700" % status_colors.get(v, "") if s.name == "Status" else ""
        for v in s
    ])
    return styler

st.dataframe(style_df(df), use_container_width=True, hide_index=True)

st.subheader("Tinjauan Per Persyaratan")
for idx, row in df.iterrows():
    ok = row["Status"].startswith("✅")
    with st.expander(f"{row['Persyaratan']} — {'✅' if ok else '❌'}"):
        c1, c2, c3 = st.columns([2, 2, 3])
        c1.checkbox(
            "Teks terkait ditemukan",
            value=(row["Ditemukan Teks"] == "✅"),
            disabled=True,
            key=f"text_{idx}_{row['Persyaratan']}"
        )
        req_visual_table = row["Ada Gambar/Tabel (Jika Wajib)"]
        c2.checkbox(
            "Gambar/Tabel sesuai (jika wajib)",
            value=(req_visual_table == "✅"),
            disabled=True,
            key=f"visual_{idx}_{row['Persyaratan']}"
        )
        c3.markdown(f"**Status:** {row['Status']}  ")
        if row["Catatan"]:
            st.warning(row["Catatan"])
        st.caption(f"Halaman bukti (perkiraan): {row['Halaman Bukti (perkiraan, 1-based)']}")

st.subheader("Ekspor Hasil")
report = {
    "metadata": {
        "filename": uploaded.name,
    },
    "stats": output["stats"],
    "results": output["results"],
}

st.download_button(
    label="⬇️ Unduh Laporan (JSON)",
    data=pd.Series(report).to_json(force_ascii=False, indent=2),
    file_name=f"laporan_kelengkapan_{uploaded.name.replace('.pdf','')}.json",
    mime="application/json",
)

st.success("Analisis selesai. Silakan tinjau hasil dan catatan untuk perbaikan dokumen.")
