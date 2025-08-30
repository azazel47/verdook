# streamlit_verification_app.py
# Aplikasi verifikasi dokumen rencana bangunan & instalasi laut (versi pintar)
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

# NLP untuk ekstraksi yang lebih pintar
try:
    import spacy
    nlp = spacy.load("id_core_news_sm")  # model bahasa Indonesia (butuh diinstall)
except Exception:
    nlp = None

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

# Definisi bagian yang diverifikasi
SECTIONS = [
    'Informasi Kegiatan',
    'Tujuan',
    'Manfaat',
    'Kegiatan Eksisting Yang Dimohonkan',
    'Jadwal Pelaksanaan Kegiatan',
    'Rencana Tapak/Siteplan',
    'Deskriptif luasan yang dibutuhkan',
    'Peta Lokasi'
]

KEYWORDS = {
    'Informasi Kegiatan': ['kegiatan', 'jenis kegiatan', 'informasi kegiatan', 'uraian kegiatan'],
    'Tujuan': ['tujuan', 'maksud', 'objective', 'objectives'],
    'Manfaat': ['manfaat', 'manfaat kegiatan', 'benefit'],
    'Kegiatan Eksisting Yang Dimohonkan': ['eksisting', 'eksisting yang dimohonkan', 'existing', 'permohonan eksisting'],
    'Jadwal Pelaksanaan Kegiatan': ['jadwal', 'pelaksanaan', 'jadwal pelaksanaan', 'bulan', 'tahun', 'mulai', 'selesai'],
    'Rencana Tapak/Siteplan': ['siteplan', 'tapak', 'site plan', 'rencana tapak'],
    'Deskriptif luasan yang dibutuhkan': ['luasan', 'luas', 'm2', 'meter persegi', 'luasan yang dibutuhkan'],
    'Peta Lokasi': ['peta lokasi', 'lokasi', 'map', 'koordinat', 'latitude', 'longitude']
}

st.set_page_config(page_title='Verifikasi Dokumen Rencana Bangunan & Instalasi Laut', layout='wide')

st.title('Verifikasi Dokumen — Rencana Bangunan & Instalasi Laut (Versi Pintar)')
st.write('Upload dokumen (PDF, DOCX, gambar). Aplikasi akan mengekstrak teks, menggunakan NLP untuk mencari informasi, menampilkan tabel jadwal, serta peta lokasi.')

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
                text = pytesseract.image_to_string(im_rgb, lang='ind')
        except Exception:
            pass
    return text


def extract_dates(text):
    dates = DATE_REGEX.findall(text)
    parsed = []
    for d in dates:
        try:
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

# NLP-based extraction
def extract_with_nlp(text, section):
    if not nlp:
        return None
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    # cari kalimat yang mengandung keyword
    found = []
    for s in sentences:
        for kw in KEYWORDS[section]:
            if kw.lower() in s.lower():
                found.append(s.strip())
                if len(found) > 3:
                    break
        if len(found) > 3:
            break
    return "\n".join(found) if found else None

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
        st.warning('Tidak ada teks berhasil diekstrak. Pastikan OCR (tesseract) tersedia untuk dokumen gambar/scan.')

    st.header('Hasil Verifikasi (urut)')
    results = []
    for idx, section in enumerate(SECTIONS):
        st.subheader(f'{idx+1}. {section}')
        # NLP extraction
        snippet = extract_with_nlp(combined_text, section)
        if not snippet:
            snippet = 'Tidak ada hasil NLP. Coba periksa secara manual.'
        st.markdown('**Hasil Ekstraksi:**')
        st.code(snippet[:2000])

        # special: Jadwal Pelaksanaan
        if section == 'Jadwal Pelaksanaan Kegiatan':
            dates = extract_dates(combined_text)
            if dates:
                df = pd.DataFrame({'Tanggal': dates})
                st.write('Tanggal terdeteksi:')
                st.dataframe(df)
            else:
                st.info('Tidak ada tanggal terdeteksi. Masukkan manual di bawah:')
                with st.form('manual_schedule'):
                    kegiatan = st.text_input('Nama Kegiatan')
                    tanggal = st.text_input('Tanggal (yyyy-mm-dd)')
                    submit = st.form_submit_button('Tambahkan')
                    if submit and kegiatan and tanggal:
                        st.session_state.setdefault('manual_jadwal', []).append({'Kegiatan': kegiatan, 'Tanggal': tanggal})
                if st.session_state.get('manual_jadwal'):
                    st.dataframe(pd.DataFrame(st.session_state['manual_jadwal']))

        # special: Peta Lokasi
        if section == 'Peta Lokasi':
            st.markdown('**Peta / Lokasi**')
            if latlon_found:
                lat, lon = latlon_found
                st.success(f'Koordinat terdeteksi: {lat}, {lon}')
                if folium and st_folium:
                    m = folium.Map(location=[lat, lon], zoom_start=12)
                    folium.Marker([lat, lon], popup='Lokasi').add_to(m)
                    st_folium(m, width=700, height=450)
                else:
                    st.map(pd.DataFrame({'lat':[lat], 'lon':[lon]}))
            else:
                st.info('Koordinat tidak ditemukan.')
                for n,b in images:
                    if Image:
                        img = Image.open(io.BytesIO(b))
                        st.image(img, caption=n)

        results.append({'section': section, 'snippet': snippet})

    st.header('Ringkasan Verifikasi')
    summary = pd.DataFrame([{'No': i+1, 'Bagian': r['section'], 'Ekstrak': (r['snippet'][:50]+'...') if r['snippet'] else '-'} for i,r in enumerate(results)])
    st.table(summary)
    csv = summary.to_csv(index=False).encode('utf-8')
    st.download_button('Download Ringkasan CSV', data=csv, file_name='ringkasan_verifikasi.csv', mime='text/csv')

else:
    st.info('Belum ada file diupload.')

