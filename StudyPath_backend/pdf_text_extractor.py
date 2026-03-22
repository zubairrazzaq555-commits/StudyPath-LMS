import io
from typing import Tuple, Optional

def _try_imports():
    try:
        import pdfplumber
    except Exception:  # pragma: no cover - runtime guard
        pdfplumber = None
    try:
        from pdf2image import convert_from_path
    except Exception:  # pragma: no cover - runtime guard
        convert_from_path = None
    try:
        import pytesseract
    except Exception:  # pragma: no cover - runtime guard
        pytesseract = None
    try:
        from PIL import Image
    except Exception:  # pragma: no cover - runtime guard
        Image = None
    return pdfplumber, convert_from_path, pytesseract, Image


def extract_text_from_pdf(
    pdf_path: str,
    ocr_threshold: int = 200,
    tesseract_cmd: Optional[str] = None,
    poppler_path: Optional[str] = None,
) -> Tuple[str, bool]:
    """
    Extract text from a PDF file. First attempts a fast text extraction using
    `pdfplumber`. If the extracted text is shorter than `ocr_threshold`, it
    falls back to OCR using `pdf2image` + `pytesseract`.

    Returns a tuple (text, used_ocr) where `used_ocr` is True when OCR was used.

    Notes for Windows:
    - Install Tesseract and set `tesseract_cmd` to the tesseract.exe path if not
      on PATH (e.g. r"C:\Program Files\Tesseract-OCR\tesseract.exe").
    - Install Poppler and pass `poppler_path` to the bin folder.
    - Required Python packages: `pdfplumber`, `pdf2image`, `pytesseract`, `Pillow`.
    """
    pdfplumber, convert_from_path, pytesseract, Image = _try_imports()

    text_chunks = []
    used_ocr = False

    # Try fast text extraction first
    if pdfplumber is not None:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text_chunks.append(page_text)
        except Exception:
            # If pdfplumber fails, we'll fall back to OCR below
            text_chunks = []

    text = "\n".join(text_chunks).strip()

    if len(text) >= ocr_threshold:
        return text, used_ocr

    # Fallback to OCR
    if convert_from_path is None or pytesseract is None or Image is None:
        raise RuntimeError(
            "OCR fallback requested but required packages are not installed: "
            "pdf2image, pytesseract or Pillow."
        )

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    images = convert_from_path(pdf_path, dpi=300, fmt='png', poppler_path=poppler_path)
    ocr_texts = []
    for img in images:
        try:
            ocr_page = pytesseract.image_to_string(img)
        except Exception:
            # If pytesseract fails on a PIL Image, try converting to bytes then retry
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            pil_img = Image.open(buf)
            ocr_page = pytesseract.image_to_string(pil_img)
        ocr_texts.append(ocr_page)

    full_ocr_text = "\n".join(ocr_texts).strip()
    used_ocr = True

    # Prefer OCR output if it gives more content
    if len(full_ocr_text) > len(text):
        return full_ocr_text, used_ocr
    return text, used_ocr


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Extract text from PDF with OCR fallback')
    parser.add_argument('pdf', help='Path to PDF file')
    parser.add_argument('--tesseract-cmd', help='Path to tesseract executable', default=None)
    parser.add_argument('--poppler-path', help='Path to poppler bin folder (Windows)', default=None)
    parser.add_argument('--threshold', help='Min chars to consider non-OCR', type=int, default=200)
    args = parser.parse_args()

    text, used_ocr = extract_text_from_pdf(
        args.pdf, ocr_threshold=args.threshold, tesseract_cmd=args.tesseract_cmd, poppler_path=args.poppler_path
    )
    print('USED_OCR:', used_ocr)
    print('---BEGIN TEXT---')
    print(text)
    print('---END TEXT---')
