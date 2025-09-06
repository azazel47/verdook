import re
import fitz  # PyMuPDF
import pdfplumber
import PyPDF2
import streamlit as st
from typing import List, Dict

# --------------------------- Persyaratan ---------------------------
REQUIREMENTS = [
    {"name": "Informasi Kegiatan"},
    {"name": "Tujuan"},
    {"name": "Manfaat"},
    {"name": "Kegiatan Eksisting Yang Dimohonkan"},
    {"name": "Jadwal Pelaksanaan Kegiatan"},
    {"name": "Rencana Tapak/Siteplan"},
    {"name": "Deskriptif Luasan yang Dibutuhkan"},
    {"name": "Peta Lokasi"},
]

# --------------------------- Keyword Dictionary ---------------------------
KEYWORDS = {
    "Informasi Kegiatan": [
        r"\bkegiatan\b", r"uraian kegiatan", r"rincian kegiatan", r"gambaran kegiatan",
        r"profil kegiatan", r"deskripsi kegiatan", r"latar belakang kegiatan", r"ringkasan kegiatan"
    ],
    "Tujuan": [
        r"\btujuan\b", r"\bmaksud\b", r"\bsasaran\b", r"\btarget\b",
        r"orientasi", r"objective", r"goal", r"visi.?misi"
    ],
    "Manfaat": [
        r"\bmanfaat\b", r"kegunaan", r"dampak positif", r"hasil.*diharapkan",
        r"outcome", r"nilai tambah", r"keuntungan", r"faedah", r"benefit"
    ],
    "Kegiatan Eksisting Yang Dimohonkan": [
        r"kegiatan eksisting", r"aktivitas.*berjalan", r"program berjalan", r"kondisi eksisting",
        r"rencana kegiatan", r"usulan kegiatan", r"proposal kegiatan", r"permohonan kegiatan", r"aktivitas.*usulkan"
    ],
    "Jadwal Pelaksanaan Kegiatan": [
        r"jadwal.*pelaksanaan", r"timeline", r"rencana waktu", r"schedule",
        r"perencanaan waktu", r"timeframe", r"tahapan pelaksanaan", r"roadmap", r"matriks waktu"
    ],
    "Rencana Tapak/Siteplan": [
        r"rencana tapak", r"siteplan", r"denah tapak", r"gambar tapak", r"layout",
        r"tata letak", r"masterplan", r"sketsa lokasi", r"peta tapak", r"diagram site"
    ],
    "Deskriptif Luasan yang Dibutuhkan": [
        r"deskriptif luasan", r"kebutuhan luas", r"estimasi luas", r"spesifikasi luasan",
        r"ukuran area", r"kebutuhan lahan", r"luas lahan", r"rincian area", r"kapasitas ruang",
        r"\b\d+(\.\d+)?\s*(m2|meter persegi|ha|hektar|hektare)\b"
    ],
    "Peta Lokasi": [
        r"peta lokasi", r"denah lokasi", r"gambar lokasi", r"lokasi proyek",
        r"\bmap\b", r"posisi geografis", r"koordinat lokasi", r"lokasi tapak", r"sketsa lokasi"
    ],
}

# --------------------------- Ekstraksi ---------------------------
def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()

def extract_with_pymupdf(file_bytes: bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_pages, images_per_page = [], {}
    for i, page in enumerate(doc):
        text_pages.append(page.get_text("text"))
        images_per_page[i] = len(page.get_images())
    return text_pages, images_per_page

def extract_with_pypdf2(file_bytes: bytes):
    reader = PyPDF2.PdfReader(file_bytes)
    return [page.extract_text() or "" for page in reader.pages]

def detect_tables_with_pdfplumber(file_bytes: bytes):
    table_counts = {}
    with pdfplumber.open(file_bytes) as pdf:
        for i, page in enumerate(pdf.pages):
            table_counts[i] = len(page.find_tables())
    return table_counts

# --------------------------- Segmentasi Bab ---------------------------
def segment_document(text_pages: List[str],
                     requirement_names: List[str]) -> Dict[str, Dict]:
    """
    Membagi dokumen ke dalam segmen berdasarkan heading bab.
    Heading dicocokkan dengan daftar keyword di KEYWORDS (lebih fleksibel).
    """
    sections = {name: {"text": "", "pages": []} for name in requirement_names}
    full_text = "\n".join(text_pages)

    heading_pattern = re.compile(r"^(\d+)\.\s*(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(full_text))

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        section_text = full_text[start:end].strip()
        heading_text = match.group(2).strip().lower()

        matched_req = None
        for req in requirement_names:
            for pat in KEYWORDS.get(req, []):
                if re.search(pat, heading_text):
                    matched_req = req
                    break
            if matched_req:
                break

        if matched_req:
            start_page = full_text[:start].count("\f")
            end_page = full_text[:end].count("\f")
            page_range = list(range(start_page, max(start_page+1, end_page+1)))

            sections[matched_req]["text"] = section_text
            sections[matched_req]["pages"] = page_range

    return sections

# --------------------------- Analisis ---------------------------
def find_keyword_hits(texts: List[str], patterns: List[str]) -> Dict[int, List[str]]:
    hits = {}
    for i, text in enumerate(texts):
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                hits.setdefault(i, []).append(pat)
    return hits

def score_requirement(name: str, keyword_hits: Dict[int, List[str]],
                      images_per_page: Dict[int, int],
                      tables_per_page: Dict[int, int],
                      segment_texts: List[str]) -> Dict:
    has_keyword = bool(keyword_hits)
    has_image, has_table = any(v > 0 for v in images_per_page.values()), any(v > 0 for v in tables_per_page.values())

    status = "❌ Tidak Ada"
    if name == "Jadwal Pelaksanaan Kegiatan":
        if has_keyword and (has_image or has_table):
            status = "✅ Lengkap"
        elif has_keyword:
            status = "⚠️ Ada teks, tidak ada gambar/tabel"
    elif name in ["Rencana Tapak/Siteplan", "Peta Lokasi"]:
        if has_keyword and has_image:
            status = "✅ Lengkap"
        elif has_keyword:
            status = "⚠️ Ada teks, tidak ada gambar"
    else:
        if has_keyword:
            status = "✅ Lengkap"

    return {
        "Persyaratan": name,
        "Status": status,
        "Keyword ditemukan": ", ".join(set(k for v in keyword_hits.values() for k in v)) or "-",
    }

def analyze_pdf(file_bytes: bytes) -> Dict:
    text_pages, images_per_page = extract_with_pymupdf(file_bytes)
    if not text_pages:
        text_pages = extract_with_pypdf2(file_bytes)
    table_counts = detect_tables_with_pdfplumber(file_bytes)
    text_pages = [clean_text(t) for t in text_pages]

    sections = segment_document(text_pages, [r["name"] for r in REQUIREMENTS])

    results = []
    for req in REQUIREMENTS:
        name = req["name"]
        seg = sections.get(name, {"text": "", "pages": []})

        hits = find_keyword_hits([seg["text"]], KEYWORDS.get(name, [])) if seg["text"] else {}

        row = score_requirement(
            name,
            hits,
            {p: images_per_page.get(p, 0) for p in seg["pages"]},
            {p: table_counts.get(p, 0) for p in seg["pages"]},
            [text_pages[p] for p in seg["pages"]] if seg["pages"] else []
        )

        row["Halaman Bukti (perkiraan, 1-based)"] = (
            ", ".join(str(p+1) for p in seg["pages"]) if seg["pages"] else "-"
        )
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

# --------------------------- Streamlit UI ---------------------------
def main():
    st.title("📑 Dashboard Analisis Kesesuaian & Kelengkapan Dokumen Perizinan")
    uploaded_file = st.file_uploader("Upload dokumen PDF", type=["pdf"])

    if uploaded_file:
        with st.spinner("Menganalisis dokumen..."):
            analysis = analyze_pdf(uploaded_file.read())

        st.subheader("📊 Hasil Analisis")
        st.table(analysis["results"])

        st.subheader("📈 Statistik Dokumen")
        st.json(analysis["stats"])

if __name__ == "__main__":
    main()
