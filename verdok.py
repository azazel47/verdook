# streamlit_verification_app.py
# Aplikasi verifikasi dokumen rencana bangunan & instalasi laut
# Cara pakai: streamlit run streamlit_verification_app.py

import streamlit as st
import io
import re
from datetime import datetime
import pandas as pd

# Optional libs that improve extraction
try:
    import pdfplumber
except Exception:
    pdfplumber = None
try:
    from PIL import Image
except Exception:
    Image = None
try:
    import pytesseract
except Exception:
    pytesseract = None
try:
    import docx
except Exception:
    docx = None
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

# Mapping
try:
    import folium
    from streamlit_folium import st_folium
except Exception:
    folium = None
    st_folium = None

# Utilities
LATLON_REGEX = re.compile(r"([-+]?\d{1,2}\.\d+)[,;\s]+([-+]?\d{1,3}\.\d+)")
DATE_REGEX = re.compile(r"(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}|\d{4}[\-/]\d{1,2}[\-/]\d{1,2})")

KEYWORDS = {
    'Informasi Kegiatan': ['kegiatan', 'jenis kegiatan', 'informasi kegiatan', 'uraian kegiatan'],
    'Tujuan': ['tujuan', 'maksud', 'objective', 'objectives'],
    'Manfaat': ['manfaat', 'manfaat kegiatan', 'benefit'],
    'Kegiatan Eksisting Yang Dimohonkan': ['eksisting', 'eksisting yang dimohonkan', 'existing', 'permohonan eksisting'],
    'Jadwal Pelaksanaan Kegiatan': ['jadwal', 'pelaksanaan', 'jadwal pelaksanaan', 'bulan', 'tahun', 'mulai', 'selesai'],
    'Rencana Tapak/Siteplan': ['siteplan', 'tapak', 'site plan', 'rencana tapak', 'site plan'],
    'Deskriptif luasan yang dibutuhkan': ['luasan', 'luas', 'm2', 'meter persegi', 'luasan yang dibutuhkan'],
    'Peta Lokasi': ['peta lokasi', 'lokasi', 'map', 'koordinat', 'latitude', 'longitude']
}

st.set_page_config(page_title='Verifikasi Dokumen Rencana Bangunan & Instalasi Laut', layout='wide')

st.title('Verifikasi Dokumen — Rencana Bangunan & Instalasi Laut')
st.write('Upload dokumen (PDF, DOCX, gambar). Aplikasi akan mengekstrak teks, mencari informasi sesuai urutan, menampilkan tabel jadwal, dan memetakan lokasi jika ditemukan koordinat.')

uploaded_files = st.file_uploader('Upload 1 atau lebih dokumen', accept_multiple_files=True, type=['pdf','docx','doc','png','jpg','jpeg','tiff'])

# Functions to extract text

def extract_text_from_pdf(file_bytes):
    text = ''
    if pdfplumber:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += '\n' + t
        except Exception:
            pass
    # fallback to PyMuPDF
    if not text and fitz:
        try:
            doc = fitz.open(stream=file_bytes, filetype='pdf')
            for page in doc:
                text += '\n' + page.get_text()
        except Exception:
            pass
    return text


def extract_text_from_docx(file_bytes):
    text = ''
    if docx:
        try:
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            for p in doc.paragraphs:
                text += '\n' + p.text
        except Exception:
            pass
    return text


def extract_text_from_image(file_bytes):
    text = ''
    if Image:
        try:
            im = Image.open(io.BytesIO(file_bytes))
            im_rgb = im.convert('RGB')
            if pytesseract:
                text = pytesseract.image_to_string(im_rgb)
            else:
                # If no OCR available, return empty; UI will still show image
                text = ''
        except Exception:
            pass
    return text


def find_keywords(text, keywords_list):
    found = []
    for kw in keywords_list:
        if re.search(r"\\b" + re.escape(kw) + r"\\b", text, flags=re.IGNORECASE):
            found.append(kw)
    return found


def extract_dates(text):
    dates = DATE_REGEX.findall(text)
    parsed = []
    for d in dates:
        try:
            # normalize separators
            d2 = d.replace('-', '/').replace('.', '/')
            dt = pd.to_datetime(d2, dayfirst=True, errors='coerce')
            if not pd.isna(dt):
                parsed.append(str(dt.date()))
        except Exception:
            pass
    return parsed


def extract_latlon(text):
    m = LATLON_REGEX.search(text)
    if m:
        try:
            lat = float(m.group(1))
            lon = float(m.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except Exception:
            pass
    return None

# Process uploaded files
if uploaded_files:
    combined_text = ''
    images = []
    latlon_found = None

    for uploaded in uploaded_files:
        bytes_data = uploaded.read()
        name = uploaded.name.lower()
        st.write(f'**File:** {uploaded.name}')
        if name.endswith('.pdf'):
            text = extract_text_from_pdf(bytes_data)
            if not text and Image:
                try:
                    # try to render pages as images for OCR if OCR available
                    from pdf2image import convert_from_bytes
                    pages = convert_from_bytes(bytes_data)
                    for p in pages:
                        buf = io.BytesIO()
                        p.save(buf, format='PNG')
                        images.append((uploaded.name, buf.getvalue()))
                except Exception:
                    pass
        elif name.endswith('.docx') or name.endswith('.doc'):
            text = extract_text_from_docx(bytes_data)
        elif name.endswith(('.png','.jpg','.jpeg','.tiff')):
            text = extract_text_from_image(bytes_data)
            images.append((uploaded.name, bytes_data))
        else:
            text = ''
        combined_text += '\n\n----\n\n' + (text or '')

        if not latlon_found:
            latlon_found = extract_latlon(text)

    if not combined_text.strip():
        st.warning('Tidak ada teks yang berhasil diekstrak. Jika dokumen berupa gambar/scan, pasang pytesseract dan pdf2image pada environment agar OCR berjalan.')

    # Run verifikasi berurutan
    st.header('Hasil Verifikasi (urut)')
    results = []
    for idx, key in enumerate(['Informasi Kegiatan','Tujuan','Manfaat','Kegiatan Eksisting Yang Dimohonkan','Jadwal Pelaksanaan Kegiatan','Rencana Tapak/Siteplan','Deskriptif luasan yang dibutuhkan','Peta Lokasi']):
        st.subheader(f'{idx+1}. {key}')
        kws = KEYWORDS.get(key, [])
        found = find_keywords(combined_text, kws)
        snippet = ''
        # extract a snippet near first keyword match
        if found:
            pattern = re.compile(r"(.{0,200}\\b(?:" + "|".join([re.escape(w) for w in found]) + r")\\b.{0,200})", flags=re.IGNORECASE|re.DOTALL)
            m = pattern.search(combined_text)
            if m:
                snippet = m.group(1)
        else:
            # fallback: try to find heading by common heading patterns
            h = re.search(r"(^[A-Z ].{0,200}\n)|(^.{0,200}\n[A-Z].{0,200}\n)", combined_text, flags=re.MULTILINE)
            if h:
                snippet = h.group(0)

        if snippet:
            st.markdown('**Cuplikan yang ditemukan:**')
            st.code(snippet[:2000])
        else:
            st.info('Belum ditemukan teks relevan untuk bagian ini.')

        # special handling for Jadwal Pelaksanaan Kegiatan: build table
        if key == 'Jadwal Pelaksanaan Kegiatan':
            dates = extract_dates(combined_text)
            # heuristik: cari blok teks 'Jadwal' dan ambil baris berformat tabel
            schedule_table = None
            # try to find lines containing months, dates or kata 'Jadwal'
            block_match = re.search(r"jadwal[\s\S]{0,500}", combined_text, flags=re.IGNORECASE)
            lines = []
            if block_match:
                block = block_match.group(0)
                lines = [l.strip() for l in block.splitlines() if l.strip()]
            # try to parse lines into columns using common separators
            rows = []
            for l in lines:
                parts = re.split(r"\s{2,}|\t|,|;| - | -| – |: ", l)
                if len(parts) >= 2:
                    rows.append(parts)
            if rows:
                # normalize to dataframe
                maxcols = max(len(r) for r in rows)
                rows_norm = [r + ['']*(maxcols-len(r)) for r in rows]
                df = pd.DataFrame(rows_norm)
                st.write('Tabel jadwal (heuristik ekstraksi):')
                st.dataframe(df)
            elif dates:
                st.write('Tanggal yang terdeteksi di dokumen:')
                df = pd.DataFrame({'detected_dates': dates})
                st.dataframe(df)
            else:
                st.info('Tidak menemukan tabel atau tanggal jadwal secara otomatis. Anda dapat memasukkan jadwal secara manual di bawah:')
                # manual entry
                with st.form('manual_schedule'):
                    col1, col2 = st.columns(2)
                    with col1:
                        nama = st.text_input('Nama Kegiatan contoh: Pemasangan tiang')
                    with col2:
                        tanggal = st.text_input('Tanggal (contoh: 2025-09-01 sampai 2025-09-10)')
                    submit = st.form_submit_button('Tambahkan ke tabel')
                    if submit and nama and tanggal:
                        st.session_state.setdefault('schedule_rows', []).append({'kegiatan':nama,'tanggal':tanggal})
                        st.success('Ditambahkan')
                if st.session_state.get('schedule_rows'):
                    st.write(pd.DataFrame(st.session_state['schedule_rows']))

        # special handling for Peta Lokasi
        if key == 'Peta Lokasi':
            st.markdown('**Peta / Lokasi**')
            # show images that may be maps
            map_images = [im for im in images if 'map' in im[0].lower() or 'peta' in im[0].lower() or 'lokasi' in im[0].lower() or 'site' in im[0].lower() or 'tapak' in im[0].lower()]
            if map_images:
                st.write('Menemukan gambar yang kemungkinan peta/siteplan:')
                for n, b in map_images:
                    if Image:
                        img = Image.open(io.BytesIO(b))
                        st.image(img, caption=n, use_column_width=True)
            else:
                st.info('Tidak ada gambar yang jelas teridentifikasi sebagai peta/siteplan berdasarkan nama file. Semua gambar yang diupload ditampilkan di bawah.')
                for n,b in images:
                    if Image:
                        img = Image.open(io.BytesIO(b))
                        st.image(img, caption=n, use_column_width=True)

            # if coordinates found, show folium map or st.map
            if latlon_found:
                lat, lon = latlon_found
                st.success(f'Koordinat terdeteksi: {lat}, {lon}')
                if folium and st_folium:
                    m = folium.Map(location=[lat, lon], zoom_start=12)
                    folium.Marker([lat, lon], popup='Lokasi terdeteksi').add_to(m)
                    st_folium(m, width=700, height=450)
                else:
                    # fallback to st.map
                    try:
                        dfm = pd.DataFrame({'lat':[lat],'lon':[lon]})
                        st.map(dfm)
                    except Exception:
                        st.write('Instal paket folium & streamlit_folium untuk pratinjau peta yang lebih baik.')
            else:
                st.info('Koordinat tidak terdeteksi otomatis. Coba cari kata "koordinat" atau upload peta dengan koordinat tertulis.')

        results.append({'section': key, 'found_keywords': found, 'snippet': snippet})

    st.header('Ringkasan Verifikasi')
    summary = pd.DataFrame([{'No': i+1, 'Bagian': r['section'], 'Ditemukan kata kunci (contoh)': ', '.join(r['found_keywords']) or '-'} for i,r in enumerate(results)])
    st.table(summary)

    # export hasil sebagai laporan sederhana
    st.markdown('**Unduh laporan (CSV)**')
    csv = summary.to_csv(index=False).encode('utf-8')
    st.download_button('Download CSV ringkasan', data=csv, file_name='ringkasan_verifikasi.csv', mime='text/csv')

    st.markdown('---')
    st.write('Jika Anda butuh pemeriksaan lebih mendalam (mis. pengecekan gambar siteplan/peta secara manual, validasi koordinat terhadap batas wilayah, atau pemrosesan OCR tingkat lanjut), beri tahu saya dan saya dapat menambahkan fitur tersebut.')

else:
    st.info('Belum ada file diupload. Silakan upload dokumen proyek Anda.')


# Footer: dependencies
st.sidebar.header('Petunjuk & Dependensi')
st.sidebar.markdown('''
Dependencies (disarankan untuk hasil terbaik):

- streamlit
- pdfplumber (untuk ekstraksi teks PDF)
- PyMuPDF (fitz) alternatif untuk PDF
- python-docx (ekstraksi DOCX)
- pillow (PIL) untuk gambar
- pytesseract + tesseract-ocr (untuk OCR gambar/scan)
- pdf2image (untuk convert PDF halaman ke gambar jika perlu) + poppler
- pandas
- folium dan streamlit_folium (untuk pratinjau peta)

Instal contoh: `pip install streamlit pdfplumber pymupdf python-docx pillow pytesseract pdf2image pandas folium streamlit-folium`

Jika Anda menggunakan Windows/Linux, pastikan juga menginstal tesseract-ocr dan poppler untuk OCR/pdf2image.
''')

st.sidebar.markdown('Versi sederhana ini menggunakan heuristik teks untuk mendeteksi bagian. Anda dapat menyesuaikan KEYWORDS atau menambah model NLP (mis. spaCy, transformers) untuk verifikasi yang lebih akurat.')
