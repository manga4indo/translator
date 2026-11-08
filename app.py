
import io
import zipfile

import streamlit as st
from PIL import Image

from modules.pipeline import remove_text


# --------------------------------------------------
# KONFIGURASI HALAMAN
# --------------------------------------------------

st.set_page_config(
    page_title="Manga Text Remover",
    page_icon="🧹",
    layout="wide"
)


# --------------------------------------------------
# STYLE
# --------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
    }

    h1, h2, h3 {
        color: #b8f36b;
    }

    .description {
        color: #b9c0ce;
        font-size: 15px;
    }

    div.stButton > button {
        background-color: #b8f36b;
        color: #0d1117;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        min-height: 45px;
    }

    div.stButton > button:hover {
        background-color: #a5df5d;
        color: #0d1117;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# JUDUL
# --------------------------------------------------

st.title("🧹 Manga Text Remover")

st.markdown(
    '<p class="description">'
    'Hapus teks asing dari gambar manga dan manhwa. '
    'Setelah dibersihkan, kamu bisa menerjemahkan dan '
    'menambahkan tulisan Indonesia sendiri di Photoshop.'
    '</p>',
    unsafe_allow_html=True
)

st.divider()


# --------------------------------------------------
# PENGATURAN
# --------------------------------------------------

left, right = st.columns(2)

with left:
    source_language = st.selectbox(
        "Bahasa teks pada gambar",
        [
            "English",
            "Jepang",
            "Korea",
            "Mandarin Sederhana",
            "Mandarin Tradisional"
        ]
    )

with right:
    cleaning_mode = st.selectbox(
        "Mode pembersihan",
        [
            "White Fill",
            "Inpainting"
        ],
        format_func=lambda x: (
            "White Fill - untuk balon putih"
            if x == "White Fill"
            else "Inpainting - untuk gambar kompleks"
        )
    )

if cleaning_mode == "White Fill":
    st.info(
        "White Fill akan menutup area teks dengan warna putih. "
        "Gunakan untuk tulisan di balon dialog putih."
    )
else:
    st.info(
        "Inpainting mencoba mengisi area bekas teks "
        "menggunakan piksel di sekitarnya."
    )


# --------------------------------------------------
# PENGATURAN LANJUTAN
# --------------------------------------------------

with st.expander("Pengaturan lanjutan"):
    confidence = st.slider(
        "Sensitivitas deteksi teks",
        min_value=0.05,
        max_value=0.90,
        value=0.20,
        step=0.05,
        help=(
            "Nilai lebih rendah dapat mendeteksi lebih banyak teks, "
            "tetapi bisa menghasilkan deteksi yang keliru."
        )
    )

    mask_padding = st.slider(
        "Perluasan area penghapusan",
        min_value=0,
        max_value=20,
        value=8,
        step=1,
        help=(
            "Perbesar jika masih ada pinggiran huruf yang tersisa."
        )
    )

    inpaint_radius = st.slider(
        "Ukuran perbaikan Inpainting",
        min_value=1,
        max_value=10,
        value=4,
        step=1,
        help=(
            "Pengaturan ini hanya digunakan pada mode Inpainting."
        )
    )

    max_side = st.select_slider(
        "Ukuran pemrosesan gambar",
        options=[1000, 1500, 2000, 2500, 3000],
        value=2000
    )


st.divider()


# --------------------------------------------------
# UPLOAD GAMBAR
# --------------------------------------------------

uploaded_files = st.file_uploader(
    "Upload gambar manga atau manhwa",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True
)


# --------------------------------------------------
# PROSES GAMBAR
# --------------------------------------------------

if uploaded_files:

    st.write(
        f"**Jumlah gambar:** {len(uploaded_files)}"
    )

    if st.button(
        "🧹 Mulai Hapus Teks",
        use_container_width=True
    ):

        results = []

        progress = st.progress(0)
        status = st.empty()

        for index, uploaded_file in enumerate(uploaded_files):

            status.write(
                f"Memproses {uploaded_file.name} "
                f"({index + 1}/{len(uploaded_files)})..."
            )

            try:
                image_bytes = uploaded_file.getvalue()

                cleaned_image, text_count = remove_text(
                    raw_bytes=image_bytes,
                    source_language=source_language,
                    cleaning_mode=cleaning_mode,
                    confidence_threshold=confidence,
                    max_side=max_side,
                    mask_padding=mask_padding,
                    inpaint_radius=inpaint_radius
                )

                results.append({
                    "name": uploaded_file.name,
                    "image": cleaned_image,
                    "count": text_count
                })

            except Exception as error:
                st.error(
                    f"Gagal memproses {uploaded_file.name}: {error}"
                )

            progress.progress(
                (index + 1) / len(uploaded_files)
            )

        status.success("Proses selesai!")

        st.session_state["cleaned_results"] = results


# --------------------------------------------------
# HASIL GAMBAR
# --------------------------------------------------

if "cleaned_results" in st.session_state:

    results = st.session_state["cleaned_results"]

    if results:

        st.divider()
        st.header("Hasil Pembersihan")

        for index, result in enumerate(results):

            st.subheader(result["name"])

            st.caption(
                f"Area teks terdeteksi: {result['count']}"
            )

            original_file = next(
                (
                    file
                    for file in uploaded_files
                    if file.name == result["name"]
                ),
                None
            )

            if original_file is not None:

                original_image = Image.open(
                    io.BytesIO(original_file.getvalue())
                ).convert("RGB")

                before, after = st.columns(2)

                with before:
                    st.caption("Sebelum")
                    st.image(
                        original_image,
                        use_container_width=True
                    )

                with after:
                    st.caption("Sesudah")
                    st.image(
                        result["image"],
                        use_container_width=True
                    )

            else:
                st.image(
                    result["image"],
                    use_container_width=True
                )

            output_buffer = io.BytesIO()

            result["image"].save(
                output_buffer,
                format="PNG"
            )

            st.download_button(
                label="⬇️ Download gambar bersih",
                data=output_buffer.getvalue(),
                file_name=f"cleaned_{result['name'].rsplit('.', 1)[0]}.png",
                mime="image/png",
                key=f"download_{index}",
                use_container_width=True
            )

            st.divider()

        # ------------------------------------------
        # DOWNLOAD SEMUA HASIL DALAM ZIP
        # ------------------------------------------

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
            zip_buffer,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:

            for result in results:

                image_buffer = io.BytesIO()

                result["image"].save(
                    image_buffer,
                    format="PNG"
                )

                filename = (
                    f"cleaned_{result['name'].rsplit('.', 1)[0]}.png"
                )

                zip_file.writestr(
                    filename,
                    image_buffer.getvalue()
                )

        st.download_button(
            label="📦 Download Semua Gambar (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="manga_cleaned_images.zip",
            mime="application/zip",
            use_container_width=True
        )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Manga Text Remover | OCR: EasyOCR | "
    "Image Cleaning: OpenCV"
)
