"""Render PDF pages for the optional browser interface."""

from threading import Lock

import pypdfium2

PDFIUM_LOCK = Lock()


def preview_page(contents, index=0):
    with PDFIUM_LOCK, pypdfium2.PdfDocument(contents) as document:
        page = document.get_page(index)
        try:
            bitmap = page.render(scale=1.35)
            try:
                return bitmap.to_pil().copy(), len(document)
            finally:
                bitmap.close()
        finally:
            page.close()
