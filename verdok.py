import openai

def analisis_ai(teks_dokumen):
    prompt = f"""
    Anda adalah sistem verifikasi dokumen perizinan.
    Periksa apakah dokumen berikut memuat informasi sesuai kriteria:

    1) Rencana kegiatan:
        - Kegiatan, tujuan, manfaat
        - Kegiatan eksisting
        - Jadwal pelaksanaan
        - Site plan
        - Luasan lokasi
    2) Peta lokasi beserta koordinat

    Dokumen:
    {teks_dokumen}

    Buatkan:
    - Ringkasan
    - Checklist kelengkapan poin di atas (lengkap/tidak)
    - Saran perbaikan
    """
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"]
