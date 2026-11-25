# Changelog

## 0.2.0

This release requires Python 3.11+ to ship with the patched Pillow 13 image decoder.

- Import the first sheet of XLSX workbooks or UTF-8 CSV, map custom columns and report row-level issues.
- Calculate CBM for identical or distinct cartons and show theoretical 40HQ estimates alongside any supplied quantity.
- Match photographs by filename or product code. Support proportional fit, center crop, JPEG compression, white alpha compositing, and optional rembg processing.
- Generate A4 PDFs in three themes with 1, 2 or 4 products per page, branded sections, optional logos, pagination, and English or simplified Chinese labels.
- Add a Streamlit upload, review, preview and download workflow and keep the CLI available.
- Add bilingual documentation, templates, fictional examples, Docker and a CI matrix for Linux, Windows and macOS.

## 0.1.0 (initial local prototype)

- CSV specification validation and single-carton CBM calculation.
- Offline PDF rendering with two products per A4 page.
- Example data and original schematic images.
- Ten unit tests and GitHub Actions workflow configuration.
