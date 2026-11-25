# Verification for v0.2.0

Local verification was performed on Linux on 2026-11-25. The unchanged prototype passed its ten original unit tests before development.

| Check | Observed result |
| --- | --- |
| Linux, Python 3.11.18 | 44 tests and four subtests passed after installation in a clean virtual environment. |
| Linux, Python 3.12.14 | 44 tests passed. Statement coverage was 92% for `trade_catalog_kit`. |
| Streamlit | AppTest uploaded the XLSX and four images, validated SKU matches, changed the design, generated and paged through a PDF, and checked that changes invalidate the previous download. |
| PDF layout | Reviewed the three bundled samples, encompassing 19 pages. Generated output for all 18 combinations of two languages, three themes and three product densities and rasterized a product page from each. |
| Image background removal | Ran rembg with the u2netp CPU model on the included cabinet and table images and generated a one-page PDF. |
| Docker | Built the image, started Streamlit as UID 10001, verified the sample workbook was readable and received HTTP 200 from the health endpoint. |
| Package | Built the source distribution and wheel and validated the metadata with Twine. |
| Dependencies and secrets | `pip check` found no broken requirements. An updated core and web test environment returned no known dependency vulnerabilities at audit time, and Gitleaks returned no leaks in the scanned Git content. |

The [Actions workflow](../.github/workflows/tests.yml) tests Python 3.11 and 3.12 on Linux, Windows and macOS. Look up the [run for the release commit](https://github.com/levixyz0520-crypto/trade-catalog-kit/actions) to verify hosted results.
