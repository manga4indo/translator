
import io

import cv2
import easyocr
import numpy as np
import streamlit as st
from PIL import Image


# Bahasa OCR yang didukung
LANGUAGES = {
    "English": ["en"],
    "Jepang": ["ja", "en"],
    "Korea": ["ko", "en"],
    "Mandarin Sederhana": ["ch_sim", "en"],
    "Mandarin Tradisional": ["ch_tra", "en"],
}


@st.cache_resource
def get_reader(source_language):
    """
    Memuat OCR reader dan menyimpannya di cache
    agar tidak perlu mengunduh model setiap gambar.
    """
    if source_language not in LANGUAGES:
        raise ValueError("Bahasa sumber tidak didukung.")

    return easyocr.Reader(
        LANGUAGES[source_language],
        gpu=False,
        verbose=False
    )


def resize_image(image, max_side=2000):
    """
    Mengecilkan gambar yang terlalu besar agar
    pemrosesan lebih ringan.
    """
    height, width = image.shape[:2]

    largest_side = max(height, width)

    if largest_side <= max_side:
        return image, 1.0

    scale = max_side / largest_side

    new_width = int(width * scale)
    new_height = int(height * scale)

    resized = cv2.resize(
        image,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA
    )

    return resized, scale


def create_text_mask(
    image_shape,
    detections,
    mask_padding=8
):
    """
    Membuat mask berdasarkan area teks yang ditemukan OCR.
    Mask diperlebar agar sisa pinggiran huruf ikut terhapus.
    """
    height, width = image_shape[:2]

    mask = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    for detection in detections:
        if len(detection) < 3:
            continue

        bbox, text, confidence = detection

        if not text or confidence < 0.20:
            continue

        polygon = np.array(
            bbox,
            dtype=np.int32
        )

        polygon[:, 0] = np.clip(
            polygon[:, 0], 0, width - 1
        )

        polygon[:, 1] = np.clip(
            polygon[:, 1], 0, height - 1
        )

        cv2.fillPoly(
            mask,
            [polygon],
            255
        )

    if mask_padding > 0 and np.any(mask):
        kernel_size = mask_padding * 2 + 1

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (kernel_size, kernel_size)
        )

        mask = cv2.dilate(
            mask,
            kernel,
            iterations=1
        )

    return mask


def clean_with_white_fill(image, mask):
    """
    Mengisi area teks dengan warna putih.
    Cocok untuk balon dialog berlatar putih.
    """
    result = image.copy()

    result[mask > 0] = (255, 255, 255)

    return result


def clean_with_inpainting(image, mask, radius=4):
    """
    Menghapus area teks dan memperkirakan
    isi area tersebut dari piksel di sekitarnya.
    """
    result = cv2.inpaint(
        image,
        mask,
        radius,
        cv2.INPAINT_TELEA
    )

    return result


def remove_text(
    raw_bytes,
    source_language,
    cleaning_mode,
    confidence_threshold=0.20,
    max_side=2000,
    mask_padding=8,
    inpaint_radius=4
):
    """
    Fungsi utama:
    1. Membaca gambar.
    2. Mendeteksi teks menggunakan EasyOCR.
    3. Membuat mask.
    4. Membersihkan teks menggunakan mode pilihan.
    5. Mengembalikan gambar hasil.
    """

    # Buka gambar
    pil_image = Image.open(
        io.BytesIO(raw_bytes)
    ).convert("RGB")

    original_image = np.array(pil_image)

    original_height, original_width = original_image.shape[:2]

    # Perkecil gambar jika terlalu besar
    working_image, scale = resize_image(
        original_image,
        max_side=max_side
    )

    # Muat OCR
    reader = get_reader(source_language)

    # Deteksi teks
    detections = reader.readtext(
        working_image,
        detail=1,
        paragraph=False
    )

    # Filter berdasarkan tingkat keyakinan OCR
    filtered_detections = [
        item
        for item in detections
        if len(item) >= 3
        and item[1]
        and item[2] >= confidence_threshold
    ]

    # Buat mask
    mask = create_text_mask(
        working_image.shape,
        filtered_detections,
        mask_padding=mask_padding
    )

    # Bersihkan gambar
    if cleaning_mode == "White Fill":
        cleaned = clean_with_white_fill(
            working_image,
            mask
        )

    elif cleaning_mode == "Inpainting":
        cleaned = clean_with_inpainting(
            working_image,
            mask,
            radius=inpaint_radius
        )

    else:
        raise ValueError("Mode pembersihan tidak dikenal.")

    # Kembalikan ke ukuran asli jika sebelumnya diperkecil
    if scale != 1.0:
        cleaned = cv2.resize(
            cleaned,
            (original_width, original_height),
            interpolation=cv2.INTER_CUBIC
        )

    # Hitung jumlah area teks yang terdeteksi
    text_count = len(filtered_detections)

    # Konversi ke PIL
    result_image = Image.fromarray(cleaned)

    return result_image, text_count
