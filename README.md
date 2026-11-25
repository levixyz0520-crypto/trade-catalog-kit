# Trade Catalog Kit

Turn an Excel or CSV product list and local images into a branded A4 PDF catalog. Trade Catalog Kit is a Python tool for exporters, manufacturers and wholesalers. Use the Streamlit interface for uploads and page previews, or the CLI for repeatable catalog builds. The core workflow runs locally without an account or paid API.

[中文说明](README_CN.md) · [Excel template](examples/product-template.xlsx) · [CSV template](examples/product-template.csv) · [Sample catalog](examples/demo.pdf)

## Run on Windows or macOS

Install Python 3.11 or later. Download and extract the repository source and open a terminal in that folder. Python 3.12 is used in the Docker example and is a good starting point.

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[web]"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

**macOS and Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install '.[web]'
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

Open `http://127.0.0.1:8501`. Start with **Try the included furniture example**, or upload your spreadsheet and product images. Review warnings and field mappings, choose a template, and set branding and company details. Select **Generate PDF preview**, check each page, then download the PDF. Press Ctrl+C in the terminal to stop the app.

| Example | Format | Use case |
| --- | --- | --- |
| [Editorial](examples/demo.pdf) | Two products per page, English | Share a furniture assortment with buyers. |
| [Modern](examples/demo-modern.pdf) | Four products per page, English | Send a compact wholesale line sheet. |
| [Minimal](examples/demo-minimal.pdf) | One product per page, simplified Chinese labels | Highlight individual products and their specifications. |

The sample company, products, contact details and specifications are fictional. The furniture images are original illustrations. See [sample asset provenance](assets/README.md).

## Command line

Install just the core package with `python -m pip install .`. Run it from the activated environment or replace `python` with the virtual environment's Python path above.

```sh
python -m trade_catalog_kit examples/furniture.xlsx --images examples/images --check
python -m trade_catalog_kit examples/furniture.xlsx --images examples/images --theme modern --per-page 4 --brand "Oak & Harbor" --out collection.pdf
python -m trade_catalog_kit --help
```

`trade-catalog` is equivalent when the environment's executables are on `PATH`. The v0.1 `python catalog.py examples/products.csv --images examples/images --out catalog.pdf` workflow and old CSV field names remain usable from the source folder after installing the package.

## Spreadsheet fields

Use UTF-8 CSV or the first worksheet of an `.xlsx` file. Put headers in the first row. Store codes with leading zeroes as Excel text. Replace formulas with their values before importing. Standard headers below are recognized automatically, and the web app or `--mapping fields.json` can map custom headers.

| Field | Entry |
| --- | --- |
| Product Code | Required, unique without regard to case. |
| Product Name | Required. |
| Product Size | Required. Example `80 × 40 × 90 cm`. |
| Category | Optional group or collection. |
| Carton Size | Optional. Use `;` between different carton sizes per unit. |
| Gross Weight | Optional in kg, g or lb. Default kg. |
| CBM | Optional total packed m³ per piece. A supplied value takes precedence. |
| Cartons per Piece | Optional positive integer. If carton sizes are supplied, defaults to the number of sizes listed. |
| 40HQ Quantity | Optional nonnegative integer. Shown separately as a supplied value. |
| Color, Material, Description | Optional product details. |
| Image | Optional filename. Leave blank to match by product code. |

Dimensions support `mm`, `cm`, `m`, `in` and `ft`. Bare numbers default to cm, and `800 × 400 × 900 mm` applies the unit to all three values. Write each unit when mixing units. A single carton size is multiplied by Cartons per Piece. Distinct sizes are added together, and an explicitly supplied carton count must match the number of sizes.

40HQ estimates are `floor(available m³ × utilization ÷ CBM per piece)`, with defaults of 76 m³ and 85%. Volume, dimensions, stackability, payload and handling constraints affect real loading. Use this number only as a theoretical volume estimate. The PDF labels estimates and shows supplied quantities separately. Change the assumptions in the app or via `--container-volume` and `--utilization`.

JPEG, PNG and WebP are accepted. Missing images get a placeholder and warning. `--strict-images` makes omissions fatal. The default fits images proportionally. Enable center crop only when cropping is acceptable. Transparency can be composited over white or theme color. For offline AI background removal, use `python -m pip install '.[web,ai]'` on Python 3.11+ in a supported rembg environment. The first run downloads the CPU model, then images can be processed locally. Review cutout edges before sharing.

English and simplified Chinese PDF labels are included. Product text is taken from the spreadsheet. For other scripts or font portability, choose an embeddable TrueType font covering all text. Complex-script shaping and automatic translation are outside this version. If a field exceeds the page layout, shorten it or choose fewer products per page.

See [advanced usage](docs/usage.md) for mappings, sizing examples and upload limits. See [deployment](docs/deployment.md) for Docker and Streamlit Community Cloud. Use [GitHub Issues](https://github.com/levixyz0520-crypto/trade-catalog-kit/issues) for feedback and [the security policy](SECURITY.md) for private reports.

## Development

```sh
python -m pip install '.[web,test]'
python -m pytest --cov=trade_catalog_kit
python -m build
```

[Contributing](CONTRIBUTING.md) · [Verification](docs/testing.md) · [Changelog](CHANGELOG.md) · [Roadmap](docs/roadmap.md) · [MIT License](LICENSE)
