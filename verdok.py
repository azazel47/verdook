import streamlit as st
import pandas as pd
import pydeck as pdk
from datetime import date
import json
from io import StringIO

st.set_page_config(page_title="Verifikasi Dokumen Rencana Bangunan & Instalasi Laut", layout="wide")

# ------------------------------
# Helpers & State
# ------------------------------
SECTIONS = [
    "1. Informasi Kegiatan",
    "2. Tujuan",
    "3. Manfaat",
    "4. Kegiatan Eksisting Yang Dimohonkan",
    "5. Jadwal Pelaksanaan Kegiatan",
    "6. Rencana Tapak/Siteplan",
    "7. Deskriptif Luasan Yang Dibutuhkan",
    "8. Peta Lokasi",
    "Ringkasan & Ekspor",
]

def init_state():
    defaults = {
        "page": 0,
        "informasi": {
            "Nama Kegiatan": "",
            "Lokasi": "",
            "Pemrakarsa": "",
            "Instansi Pembina": "",
            "Nomor/Rujukan Dokumen": "",
            "Tanggal Dokumen": str(date.today()),
        },
        "tujuan": "",
        "manfaat": "",
        "eksisting": "",
        "jadwal": pd.DataFrame([
            {"Kegiatan": "Perencanaan", "Mulai": date.today(), "Selesai": date.today()},
            {"Kegiatan": "Pelaksanaan", "Mulai": date.today(), "Selesai": date.today()},
            {"Kegiatan": "Monitoring", "Mulai": date.today(), "Selesai": date.today()},
        ]),
        "siteplan_caption": "",
        "siteplan_image": None,
        "luasan": {
            "Luas Tapak (m²)": 0.0,
            "Luas Bangunan (m²)": 0.0,
            "Kedalaman/ Elevasi (m)": 0.0,
            "Catatan Perhitungan": "",
        },
        "map": {
            "latitude": -6.175392,
            "longitude": 106.827153,
            "zoom": 12,
            "geojson_text": "",
        },
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Sidebar Navigation
st.sidebar.title("Navigasi")
selected = st.sidebar.radio("Pilih Bagian", options=SECTIONS, index=st.session_state.page)
st.session_state.page = SECTIONS.index(selected)

# Import/Export controls in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Impor/Ekspor")
export_data = {
    "informasi": st.session_state["informasi"],
    "tujuan": st.session_state["tujuan"],
    "manfaat": st.session_state["manfaat"],
    "eksisting": st.session_state["eksisting"],
    "jadwal": st.session_state["jadwal"].to_dict(orient="records"),
    "siteplan_caption": st.session_state["siteplan_caption"],
    "luasan": st.session_state["luasan"],
    "map": st.session_state["map"],
}
json_str = json.dumps(export_data, default=str, ensure_ascii=False, indent=2)
st.sidebar.download_button("Unduh Data (JSON)", data=json_str, file_name="verifikasi_rencana_bangunan.json", mime="application/json")

uploaded = st.sidebar.file_uploader("Muat Data (JSON)", type=["json"], help="Impor data yang sebelumnya diekspor")
if uploaded is not None:
    try:
        loaded = json.load(uploaded)
        st.session_state["informasi"] = loaded.get("informasi", st.session_state["informasi"]) 
        st.session_state["tujuan"] = loaded.get("tujuan", st.session_state["tujuan"]) 
        st.session_state["manfaat"] = loaded.get("manfaat", st.session_state["manfaat"]) 
        st.session_state["eksisting"] = loaded.get("eksisting", st.session_state["eksisting"]) 
        st.session_state["jadwal"] = pd.DataFrame(loaded.get("jadwal", st.session_state["jadwal"]))
        st.session_state["siteplan_caption"] = loaded.get("siteplan_caption", st.session_state["siteplan_caption"]) 
        st.session_state["luasan"] = loaded.get("luasan", st.session_state["luasan"]) 
        st.session_state["map"] = loaded.get("map", st.session_state["map"]) 
        st.sidebar.success("Berhasil memuat data.")
    except Exception as e:
        st.sidebar.error(f"Gagal memuat data: {e}")

# ------------------------------
# UI Components per Section
# ------------------------------

def section_1():
    st.header("1. Informasi Kegiatan")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state["informasi"]["Nama Kegiatan"] = st.text_input("Nama Kegiatan", st.session_state["informasi"]["Nama Kegiatan"])    
        st.session_state["informasi"]["Pemrakarsa"] = st.text_input("Pemrakarsa", st.session_state["informasi"]["Pemrakarsa"])    
        st.session_state["informasi"]["Nomor/Rujukan Dokumen"] = st.text_input("Nomor/Rujukan Dokumen", st.session_state["informasi"]["Nomor/Rujukan Dokumen"])    
    with col2:
        st.session_state["informasi"]["Lokasi"] = st.text_input("Lokasi (desa/kecamatan/kab/kota)", st.session_state["informasi"]["Lokasi"])    
        st.session_state["informasi"]["Instansi Pembina"] = st.text_input("Instansi Pembina", st.session_state["informasi"]["Instansi Pembina"])    
        st.session_state["informasi"]["Tanggal Dokumen"] = st.date_input("Tanggal Dokumen", value=pd.to_datetime(st.session_state["informasi"]["Tanggal Dokumen"]).date())


def section_2():
    st.header("2. Tujuan")
    st.session_state["tujuan"] = st.text_area("Uraikan tujuan kegiatan", st.session_state["tujuan"], height=150)


def section_3():
    st.header("3. Manfaat")
    st.session_state["manfaat"] = st.text_area("Uraikan manfaat kegiatan", st.session_state["manfaat"], height=150)


def section_4():
    st.header("4. Kegiatan Eksisting Yang Dimohonkan")
    st.session_state["eksisting"] = st.text_area("Uraikan kegiatan eksisting yang dimohonkan", st.session_state["eksisting"], height=200, help="Cantumkan komponen eksisting di darat/laut, perizinan sebelumnya, dan kondisi saat ini.")


def section_5():
    st.header("5. Jadwal Pelaksanaan Kegiatan")
    st.caption("Silakan lengkapi tabel jadwal. Kolom tanggal dapat diedit.")
    jadwal_df = st.data_editor(
        st.session_state["jadwal"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Kegiatan": st.column_config.TextColumn("Kegiatan", help="Nama aktivitas"),
            "Mulai": st.column_config.DateColumn("Mulai"),
            "Selesai": st.column_config.DateColumn("Selesai"),
        },
    )
    st.session_state["jadwal"] = jadwal_df

    # Simple validation feedback
    if not jadwal_df.empty:
        invalid_rows = []
        for idx, row in jadwal_df.iterrows():
            try:
                if pd.to_datetime(row["Selesai"]) < pd.to_datetime(row["Mulai"]):
                    invalid_rows.append(idx)
            except Exception:
                pass
        if invalid_rows:
            st.error(f"Terdapat baris dengan 'Selesai' lebih awal dari 'Mulai': {invalid_rows}")


def section_6():
    st.header("6. Rencana Tapak/Siteplan")
    st.session_state["siteplan_caption"] = st.text_input("Keterangan/Legenda Siteplan", st.session_state["siteplan_caption"])    
    img_file = st.file_uploader("Unggah gambar siteplan (PNG/JPG)", type=["png", "jpg", "jpeg"])
    if img_file is not None:
        st.session_state["siteplan_image"] = img_file.getvalue()
    if st.session_state["siteplan_image"]:
        st.image(st.session_state["siteplan_image"], caption=st.session_state["siteplan_caption"], use_container_width=True)


def section_7():
    st.header("7. Deskriptif Luasan yang Dibutuhkan")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.session_state["luasan"]["Luas Tapak (m²)"] = st.number_input("Luas Tapak (m²)", min_value=0.0, value=float(st.session_state["luasan"].get("Luas Tapak (m²)", 0.0)))
    with col2:
        st.session_state["luasan"]["Luas Bangunan (m²)"] = st.number_input("Luas Bangunan (m²)", min_value=0.0, value=float(st.session_state["luasan"].get("Luas Bangunan (m²)", 0.0)))
    with col3:
        st.session_state["luasan"]["Kedalaman/ Elevasi (m)"] = st.number_input("Kedalaman/ Elevasi (m)", value=float(st.session_state["luasan"].get("Kedalaman/ Elevasi (m)", 0.0)))
    st.session_state["luasan"]["Catatan Perhitungan"] = st.text_area("Catatan Perhitungan/Asumsi", st.session_state["luasan"].get("Catatan Perhitungan", ""), height=150)


def section_8():
    st.header("8. Peta Lokasi")
    st.caption("Masukkan koordinat lokasi dan/atau GeoJSON untuk menampilkan area rencana.")
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        st.session_state["map"]["latitude"] = st.number_input("Latitude", value=float(st.session_state["map"]["latitude"]))
    with col2:
        st.session_state["map"]["longitude"] = st.number_input("Longitude", value=float(st.session_state["map"]["longitude"]))
    with col3:
        st.session_state["map"]["zoom"] = st.slider("Zoom", 1, 20, int(st.session_state["map"]["zoom"]))

    st.session_state["map"]["geojson_text"] = st.text_area(
        "Tempelkan GeoJSON (opsional)",
        st.session_state["map"].get("geojson_text", ""),
        height=150,
        help="Dukungan layer area/garis menggunakan GeoJSON. Biarkan kosong jika tidak ada."
    )

    # Build pydeck layers
    layers = []
    # Point marker
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame({
            "lat": [st.session_state["map"]["latitude"]],
            "lon": [st.session_state["map"]["longitude"]],
        }),
        get_position='[lon, lat]',
        get_radius=20,
        pickable=True,
    ))

    # Optional GeoJSON
    geojson_raw = st.session_state["map"].get("geojson_text", "").strip()
    if geojson_raw:
        try:
            gj = json.loads(geojson_raw)
            layers.append(pdk.Layer(
                "GeoJsonLayer",
                data=gj,
                pickable=True,
                stroked=True,
                filled=True,
                extruded=False,
                lineWidthScale=2,
                lineWidthMinPixels=1,
            ))
        except Exception as e:
            st.warning(f"GeoJSON tidak valid: {e}")

    view_state = pdk.ViewState(
        latitude=st.session_state["map"]["latitude"],
        longitude=st.session_state["map"]["longitude"],
        zoom=st.session_state["map"]["zoom"],
        bearing=0,
        pitch=0,
    )

    r = pdk.Deck(layers=layers, initial_view_state=view_state, map_style=None, tooltip={"text": "Lokasi Utama"})
    st.pydeck_chart(r, use_container_width=True)


def section_summary():
    st.header("Ringkasan & Ekspor")

    # Completeness checklist
    st.subheader("Cek Kelengkapan")
    checks = {
        "Nama Kegiatan": bool(st.session_state["informasi"]["Nama Kegiatan"].strip()),
        "Lokasi": bool(st.session_state["informasi"]["Lokasi"].strip()),
        "Pemrakarsa": bool(st.session_state["informasi"]["Pemrakarsa"].strip()),
        "Tujuan": bool(st.session_state["tujuan"].strip()),
        "Manfaat": bool(st.session_state["manfaat"].strip()),
        "Eksisting": bool(st.session_state["eksisting"].strip()),
        "Jadwal": not st.session_state["jadwal"].empty,
        "Siteplan (opsional)": st.session_state["siteplan_image"] is not None,
        "Koordinat Peta": st.session_state["map"]["latitude"] is not None and st.session_state["map"]["longitude"] is not None,
    }

    cols = st.columns(3)
    items = list(checks.items())
    for i, (label, ok) in enumerate(items):
        with cols[i % 3]:
            st.checkbox(label, value=ok, disabled=True)

    st.markdown("---")
    st.subheader("Pratinjau Cepat")
    colA, colB = st.columns([1,1])
    with colA:
        st.markdown("**Informasi Kegiatan**")
        st.json(st.session_state["informasi"])    
        st.markdown("**Tujuan**")
        st.write(st.session_state["tujuan"])    
        st.markdown("**Manfaat**")
        st.write(st.session_state["manfaat"])    
        st.markdown("**Eksisting**")
        st.write(st.session_state["eksisting"])    
    with colB:
        st.markdown("**Jadwal Pelaksanaan**")
        st.dataframe(st.session_state["jadwal"], use_container_width=True)
        st.markdown("**Deskriptif Luasan**")
        st.json(st.session_state["luasan"])    

    st.markdown("---")
    st.info("Gunakan tombol \"Unduh Data (JSON)\" di sidebar untuk menyimpan data.")

# ------------------------------
# Render selected section
# ------------------------------
page_idx = st.session_state.page
if page_idx == 0:
    section_1()
elif page_idx == 1:
    section_2()
elif page_idx == 2:
    section_3()
elif page_idx == 3:
    section_4()
elif page_idx == 4:
    section_5()
elif page_idx == 5:
    section_6()
elif page_idx == 6:
    section_7()
elif page_idx == 7:
    section_8()
else:
    section_summary()

# Footer navigation buttons
st.markdown("---")
col_prev, col_next = st.columns([1,1])
with col_prev:
    if st.session_state.page > 0:
        if st.button("← Sebelumnya"):
            st.session_state.page -= 1
            st.rerun()
with col_next:
    if st.session_state.page < len(SECTIONS)-1:
        if st.button("Berikutnya →"):
            st.session_state.page += 1
            st.rerun()

# Footer note
st.caption("© Aplikasi verifikasi dokumen (Streamlit) — susun data Anda berurutan dari 1 hingga 8. Jadwal menggunakan tabel, peta lokasi menggunakan peta interaktif.")
