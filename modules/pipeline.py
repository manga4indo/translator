
import io
import requests
import cv2
import easyocr
import numpy as np
import time

from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st


# OCR: memilih bahasa sesuai pilihan pengguna
@st.cache_resource
def reader(source_language):
    languages = {
        "English": ["en"],
        "Jepang": ["ja", "en"],
        "Korea": ["ko", "en"],
        "Mandarin Sederhana": ["ch_sim", "en"],
        "Mandarin Tradisional": ["ch_tra", "en"],
    }

    return easyocr.Reader(
        languages[source_language],
        gpu=False,
        verbose=False
    )


# Kode bahasa untuk MyMemory
SOURCE_CODES = {
    "English": "en",
    "Jepang": "ja",
    "Korea": "ko",
    "Mandarin Sederhana": "zh-CN",
    "Mandarin Tradisional": "zh-TW",
}


# Memecah teks agar tidak melebihi batas 500 byte
def split_text(text, max_bytes=450):
    parts = []
    current = ""

    for char in text:
        if len((current + char).encode("utf-8")) > max_bytes:
            if current:
                parts.append(current)
            current = char
        else:
            current += char

    if current:
        parts.append(current)

    return parts


# Terjemahan gratis menggunakan MyMemory
def translate_one(text, source_code):
    url = "https://api.mymemory.translated.net/get"

    response = requests.get(
        url,
        params={
            "q": text,
            "langpair": f"{source_code}|id",
        },
        timeout=45
    )

    response.raise_for_status()
    result = response.json()

    if result.get("responseStatus") != 200:
        detail = result.get("responseDetails", "Terjemahan gagal.")
        raise RuntimeError(str(detail))

    translated = result.get("responseData", {}).get(
        "translatedText", ""
    )

    if not translated:
        raise RuntimeError("Layanan tidak memberikan hasil terjemahan.")

    return translated


def translate_texts(texts, source_language):
    source_code = SOURCE_CODES[source_language]
    translations = []

    for text in texts:
        parts = split_text(text)
        translated_parts = []

        for part in parts:
            translated_parts.append(
                translate_one(part, source_code)
            )
            time.sleep(0.2)

        translations.append("".join(translated_parts))

    return translations


# Font bawaan
def font(size):
    paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass

    return ImageFont.load_default()


# Membungkus teks agar muat dalam kotak
def wrap(draw, text, selected_font, max_width):
    lines = []
    current = ""

    for char in text:
        test = current + char

        if (
            current
            and draw.textbbox(
                (0, 0), test, font=selected_font
            )[2] > max_width
        ):
            lines.append(current)
            current = char
        else:
            current = test

    if current:
        lines.append(current)

    return lines or [""]


# Menghapus teks lama dan menggambar terjemahan
def render(image, detections, translations):
    rgb = np.array(image.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    mask = np.zeros(bgr.shape[:2], np.uint8)
    boxes = []

    for polygon in detections:
        points = np.asarray(polygon, np.int32)
        cv2.fillPoly(mask, [points], 255)

        xs = points[:, 0]
        ys = points[:, 1]

        boxes.append((
            max(0, int(xs.min())),
            max(0, int(ys.min())),
            min(image.width, int(xs.max())),
            min(image.height, int(ys.max()))
        ))

    if np.any(mask):
        mask = cv2.dilate(
            mask,
            np.ones((3, 3), np.uint8),
            iterations=1
        )

        bgr = cv2.inpaint(
            bgr,
            mask,
            4,
            cv2.INPAINT_TELEA
        )

    canvas = Image.fromarray(
        cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    )

    draw = ImageDraw.Draw(canvas)

    for (x1, y1, x2, y2), text in zip(boxes, translations):
        width = x2 - x1
        height = y2 - y1

        if not text.strip() or width < 3 or height < 3:
            continue

        padding = max(2, int(min(width, height) * 0.06))
        chosen_font = font(8)
        lines = [text]

        for size in range(max(9, int(height * 0.75)), 7, -1):
            selected_font = font(size)

            candidate = wrap(
                draw,
                text,
                selected_font,
                max(8, width - 2 * padding)
            )

            line_height = max(
                draw.textbbox(
                    (0, 0), line, font=selected_font
                )[3]
                for line in candidate
            ) + 2

            if len(candidate) * line_height <= max(
                8, height - 2 * padding
            ):
                chosen_font = selected_font
                lines = candidate
                break

        line_height = max(
            draw.textbbox(
                (0, 0), line, font=chosen_font
            )[3]
            for line in lines
        ) + 2

        y = y1 + max(
            padding,
            (height - len(lines) * line_height) // 2
        )

        for line in lines:
            box = draw.textbbox(
                (0, 0), line, font=chosen_font
            )

            x = x1 + max(
                padding,
                (width - (box[2] - box[0])) // 2
            )

            draw.text(
                (x, y),
                line,
                font=chosen_font,
                fill=(20, 20, 20)
            )

            y += line_height

    output = io.BytesIO()
    image_format = (image.format or "PNG").upper()

    if image_format in ("JPG", "JPEG"):
        canvas.save(output, "JPEG", quality=95, optimize=True)
    elif image_format == "WEBP":
        canvas.save(output, "WEBP", quality=95, method=6)
    else:
        canvas.save(output, "PNG", optimize=True)

    return output.getvalue()


# Fungsi utama penerjemahan gambar
def translate_image(
    raw_bytes,
    source_language,
    confidence_threshold=0.2,
    max_side=2000
):
    try:
        image = ImageOps.exif_transpose(
            Image.open(io.BytesIO(raw_bytes))
        )
        image.load()

    except Exception as error:
        raise ValueError(f"Gambar tidak valid: {error}")

    if image.width * image.height > 40_000_000:
        raise ValueError(
            "Resolusi terlalu besar (maksimal 40 megapiksel)."
        )

    work = image.copy()
    work.thumbnail((max_side, max_side))

    found = reader(source_language).readtext(
        np.array(work),
        detail=1,
        paragraph=False
    )

    scale_x = image.width / work.width
    scale_y = image.height / work.height

    detections = []
    texts = []

    for polygon, text, confidence in found:
        text = str(text).strip()

        if not text or float(confidence) < confidence_threshold:
            continue

        detections.append([
            [int(x * scale_x), int(y * scale_y)]
            for x, y in polygon
        ])

        texts.append(text)

    if not texts:
        output = io.BytesIO()
        image.save(output, format=image.format or "PNG")
        return output.getvalue(), 0

    translated = translate_texts(
        texts,
        source_language
    )

    return render(
        image,
        detections,
        translated
    ), len(texts)
