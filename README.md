# Trade Catalog Kit

An offline Python utility for small exporters, wholesalers and product teams to turn structured product specifications and local photographs into a consistent, printable A4 PDF catalog. No account, API key or paid AI service is needed.

**Status:** v0.1 prototype. The included products and drawings are illustrative, not supplier specifications or commercial photographs.

## Quick start

Requires Python 3.10 or newer. From a terminal in this folder:

```sh
python -m venv .venv
```

Activate the environment: on Windows PowerShell run `.\.venv\Scripts\Activate.ps1`; on macOS/Linux run `source .venv/bin/activate`. If PowerShell blocks activation, use `.venv\Scripts\python.exe` instead of `python` in the commands below.

```sh
python -m pip install -r requirements.txt
python catalog.py examples/products.csv --images examples/images --check
python catalog.py examples/products.csv --images examples/images --out my-catalog.pdf --brand "MY COMPANY"
python -m unittest discover -s tests -v
```

Open `my-catalog.pdf` to see the result. A sample rendered PDF is also in `examples/demo.pdf`.

## Use your own data

Copy `examples/products.csv`, edit it in Excel or a text editor, and save as CSV UTF-8. Keep the column names. Put product photographs in a folder, and supply their relative filenames in the `image` column. Image files stay local.

| Field | Required | Meaning |
| --- | --- | --- |
| sku | Yes | Unique model code (case insensitive) |
| name | Yes | English product name |
| size_cm | Yes | Three positive dimensions in centimeters, e.g. `80 x 40 x 90` |
| image | Yes | Relative PNG, JPEG or WebP image filename |
| carton_cm | No | Single carton dimensions in centimeters |
| gross_kg | No | Positive gross weight in kilograms |
| cbm | No | Positive volume in cubic meters; calculated from carton dimensions if omitted |
| colors | No | Available finishes or colors |
| notes | No | Short specification or disclaimer |

The validator rejects duplicate SKUs, missing required values, invalid dimensions/weights, unreadable images, and image paths outside the selected image directory. The PDF preserves image aspect ratio and honors EXIF orientation. Each page contains up to two product cards. Optional blank fields are omitted. A failed build does not replace an existing PDF.

## Limitations

- The current layout uses Helvetica and is intended for English/Latin text, not CJK or arbitrary Unicode scripts.
- CSV input only; Excel users can export UTF-8 CSV. The PDF layout is fixed rather than a drag-and-drop template editor.
- CBM calculation assumes a single rectangular carton. For multiple cartons per product, enter verified total CBM and omit `carton_cm` if it is not applicable. A supplied CBM is preserved, not certified or cross-checked. No container-loading optimization or freight quotation is provided.
- Images are resized and alpha-composited against white; this is not AI background removal. Use authorized images with clean backgrounds for best results.
- Long values may be rejected if they cannot fit the layout. Review every generated page and all supplier specifications before sending it to customers.
- The included CI workflow is configured but has not run on GitHub yet. Local tests were executed with Python and installed dependencies in the development environment.

## Development and contributions

Run the unit tests before submitting changes. Report reproducible issues with a minimal, anonymized CSV and sample image. Do not attach customer details, supplier price lists, account credentials or copyrighted images without permission. Suggestions for schema mappings, multilingual fonts, packaging details and accessibility are welcome.

Potential improvements: XLSX import, image-matching reports, configurable page templates, multiple-carton support, preview UI, and multi-language fonts. These are proposed features, not implemented yet.

## License

MIT. See `LICENSE`.
