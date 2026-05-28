import pytesseract
from PIL import Image, ImageOps, ImageFilter
import re

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def preprocess_image(image_path):
    image = Image.open(image_path)

    image = ImageOps.exif_transpose(image)
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.SHARPEN)

    width, height = image.size
    image = image.resize((width * 2, height * 2))

    return image


def clean_text(text):
    text = text.replace("|", " ")
    text = text.replace("_", " ")
    text = text.replace(":", " : ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_after_label(text, labels):
    for label in labels:
        pattern = rf"{label}\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ0-9\.\,\-\s\/]+)"
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            value = match.group(1).strip()
            value = re.split(
                r"FECHA|ORIGEN|DESTINO|PRODUCTO|ORDEN|PESO|CONSTANCIA",
                value,
                flags=re.IGNORECASE
            )[0].strip()

            return value

    return ""


def extract_date(text):
    patterns = [
        r"\d{2}/\d{2}/\d{4}",
        r"\d{2}-\d{2}-\d{4}",
        r"\d{4}-\d{2}-\d{2}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()

    return ""


def extract_weight(text):
    patterns = [
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:KG|KGS|TON|TM|LB|LBS)?)",
        r"PESO\s*ENTREGADO\s*[:\-]?\s*(\d+[\,\.]?\d*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ""


def process_document(image_path):
    image = preprocess_image(image_path)

    text = pytesseract.image_to_string(
        image,
        lang="spa",
        config="--psm 6"
    )

    normalized = clean_text(text)

    fecha = extract_after_label(normalized, [
        "fecha",
        "f[eé]cha"
    ]) or extract_date(normalized)

    origen = extract_after_label(normalized, [
        "origen",
        "procedencia",
        "planta origen",
        "lugar origen"
    ])

    destino = extract_after_label(normalized, [
        "destino",
        "lugar destino",
        "lugar de entrega",
        "entrega"
    ])

    producto = extract_after_label(normalized, [
        "producto",
        "material",
        "mercancia",
        "mercancía",
        "descripcion producto",
        "descripción producto"
    ])

    no_orden_carga = extract_after_label(normalized, [
        "no\.?\s*orden\s*de\s*carga",
        "orden\s*de\s*carga",
        "orden\s*carga",
        "orden"
    ])

    peso_entregado = extract_after_label(normalized, [
        "peso\s*entregado",
        "peso\s*neto",
        "peso"
    ]) or extract_weight(normalized)

    no_constancia_viaje = extract_after_label(normalized, [
        "no\.?\s*constancia\s*de\s*viaje",
        "constancia\s*de\s*viaje",
        "constancia\s*viaje",
        "viaje"
    ])

    return {
        "fecha": fecha,
        "origen": origen,
        "destino": destino,
        "producto": producto,
        "no_orden_carga": no_orden_carga,
        "peso_entregado": peso_entregado,
        "no_constancia_viaje": no_constancia_viaje,
        "raw_text": text
    }