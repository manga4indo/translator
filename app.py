
import io
import zipfile
from pathlib import Path

import streamlit as st
from modules.pipeline import translate_image

st.set_page_config(
    page_title="Manga Translator ID",
    page_icon="📚",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #0d1117;
}
.main .block-container {
    max-width: 1100px;
    padding-top: 2rem;
}
.hero h1 {
    font-size: 3.4rem;
    letter-spacing: -2px;
}
.hero span {
    color: #b8f36b;
}
.muted {
    color: #9aa4b2;
}
.stButton>button[kind="primary"] {
    background: #b8f36b;
    color: #10150c;
    border: 0;
    font-weight: 700;
}
div[data-testid="stFileUploader"] {
    border: 1px dashed #64748b;
    border-radius: 14px;
    padding: 12px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="hero">'
    '<p class="muted">✦ AI MANGA TRANSLATION WORKSPACE</p>'
    '<h1>Manga Translator <span>ID</span></h1>'
    '<p class="muted">Terjemahkan manga, manhwa, dan manhua ke Bahasa Indonesia.</p>'
    '</div>',
    unsafe_allow_html=True
)

# Pengaturan sidebar
with st.sidebar:
    st.header("⚙️ Pengaturan")

    st.markdown("**Bahasa sumber**")

    source_language = st.selectbox(
        "Pilih bahasa sumber",
        [
            "English",
            "Jepang",
            "Korea",
            "Mandarin Sederhana",
            "Mandarin Tradisional",
        ],
    )

    st.markdown("**Bahasa tujuan**")
    st.info("🇮🇩 Bahasa Indonesia")

    st.caption("OCR: EasyOCR")
    st.caption("Terjemahan: MyMemory")

    st.divider()

    st.caption(
        "Tidak memerlukan OpenAI API Key."
    )

# Upload gambar
st.subheader("01 · Upload gambar manga")

uploads = st.file_uploader(
    "Pilih satu atau beberapa gambar",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True
)

if uploads:
    st.caption(
        f"{len(uploads)} gambar dipilih · "
        f"{sum(f.size for f in uploads) / 1048576:.1f} MB"
    )

    cols = st.columns(min(3, len(uploads)))

    for i, f in enumerate(uploads[:3]):
        with cols[i]:
            st.image(
                f,
                caption=f.name,
                use_container_width=True
            )

    if len(uploads) > 3:
        st.caption(
            f"+ {len(uploads) - 3} gambar lainnya"
        )

# Pengaturan OCR
st.subheader("02 · Pengaturan OCR")

with st.expander("Pengaturan lanjutan"):
    confidence = st.slider(
        "Ambang keyakinan OCR",
        0.05,
        0.90,
        0.20,
        0.05
    )

    max_side = st.select_slider(
        "Resolusi kerja OCR",
        [1200, 1600, 2000, 2400],
        value=2000
    )

st.caption(
    "Untuk pengujian awal, gunakan satu gambar terlebih dahulu."
)

st.info(
    "Layanan MyMemory memiliki batas penggunaan gratis. "
    "Jumlah teks yang dapat diterjemahkan per hari terbatas."
)

# Mulai penerjemahan
if st.button(
    "✦ Mulai terjemahkan",
    type="primary",
    use_container_width=True,
    disabled=not uploads
):
    if len(uploads) > 20:
        st.error("Maksimal 20 gambar per batch.")

    else:
        outputs = []
        failures = []

        bar = st.progress(0)
        status = st.empty()

        for i, f in enumerate(uploads):
            status.info(
                f"Memproses {i + 1}/{len(uploads)}: {f.name}"
            )

            try:
                data, count = translate_image(
                    f.getvalue(),
                    source_language,
                    confidence,
                    max_side
                )

                ext = Path(f.name).suffix.lower()
                name = f"{Path(f.name).stem}_id{ext}"

                outputs.append({
                    "name": name,
                    "data": data,
                    "count": count
                })

            except Exception as e:
                failures.append((f.name, str(e)))

            bar.progress(
                (i + 1) / len(uploads)
            )

        status.empty()

        st.session_state["outputs"] = outputs

        if outputs:
            st.success(
                f"Berhasil memproses {len(outputs)} "
                f"dari {len(uploads)} gambar."
            )

        for name, err in failures:
            with st.expander(f"Gagal: {name}"):
                st.code(err)

# Hasil terjemahan
outputs = st.session_state.get("outputs", [])

if outputs:
    st.divider()
    st.subheader("03 · Hasil terjemahan")

    st.caption(
        "Periksa hasil terjemahan. "
        "Penempatan teks dan penghapusan teks lama "
        "belum tentu sempurna."
    )

    for i, item in enumerate(outputs):
        with st.expander(
            f"📄 {item['name']} · {item['count']} area teks",
            expanded=i == 0
        ):
            st.image(
                item["data"],
                use_container_width=True
            )

            st.download_button(
                "⬇️ Download gambar",
                item["data"],
                file_name=item["name"],
                key=f"one_{i}",
                use_container_width=True
            )

    # Buat ZIP
    buff = io.BytesIO()

    with zipfile.ZipFile(
        buff,
        "w",
        zipfile.ZIP_DEFLATED
    ) as z:
        for item in outputs:
            z.writestr(
                item["name"],
                item["data"]
            )

    st.download_button(
        "📦 Download semua hasil (ZIP)",
        buff.getvalue(),
        "manga-translator-id.zip",
        "application/zip",
        type="primary",
        use_container_width=True
    )

st.divider()

st.caption(
    "Manga Translator ID · Versi MyMemory · "
    "Gunakan hanya gambar yang Anda berhak proses."
)
