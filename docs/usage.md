# Advanced usage

## Map an existing spreadsheet

The mapping file uses catalog field names on the left and the source headers on the right. Use `null` to ignore an otherwise automatically matched header. Other standard columns remain mapped automatically.

```json
{
  "Product Code": "Item No.",
  "Product Name": "Item Description",
  "Product Size": "Dimensions",
  "Image": "Photo File"
}
```

```sh
trade-catalog products.xlsx --mapping fields.json --images photos --check
```

## Calculate packaging

For two identical `100 × 50 × 20 cm` cartons, set Cartons per Piece to `2`. The total is `0.2 m³` per unit. For `125 × 42 × 12 cm; 43 × 22 × 12 cm`, set Cartons per Piece to `2` or leave it blank. The sum is `0.074352 m³`. An explicitly supplied CBM takes precedence. A difference over 5% from the computed carton volume triggers a warning. Small discrepancies can result from rounded input.

The published 40HQ estimate reflects volume only. For example, `--container-volume 80 --utilization 0.8` and `0.2 m³` per piece yield 320 pieces. Confirm physical packing with your logistics provider before using an estimate for an order or shipment.

## Prepare photos and PDF text

- Use `SKU-001.jpg` with an empty Image field to match `SKU-001`. An explicit `photo.jpg` takes precedence. The CLI accepts explicit paths relative to the image directory, including subfolders. The web interface matches uploaded base filenames.
- Correct ambiguous matches by entering a filename including its extension. Rotate and crop source photos deliberately. EXIF orientation is respected and valid color profiles are converted to sRGB where supported. White background fills transparent pixels. Use the optional AI mode to segment an opaque background.
- Use `--about`, `--contact`, `--back`, `--logo`, `--accent` and `--title` to brand a PDF. With Python 3.11+ and the optional AI extra installed, `--remove-background` uses the local rembg CPU model. The first download is from the model provider. Keep crop/AI disabled to retain full image framing and background.
- The built-in Chinese PDF font depends on the reader's CID font support. For consistent appearance and Unicode coverage, supply a licensed TrueType font via `--font path/to/font.ttf`. The same uploaded font is used for headings and body text. Bidirectional and complex-script shaping are outside the supported scope.
- Input limits are 16 MiB per spreadsheet, 5,000 data rows and 100 columns, 64 MiB expanded XLSX data, 12 MiB and 24 megapixels per image, and 120 MiB across web image uploads. Large image-heavy catalogs require more memory. Divide large collections by category if needed.

## Example workflows

- **Furniture exporter** — Use the included furniture workbook to reproduce the sample catalog. Check the bench's two distinct cartons, then replace the fictional data with approved model codes and photos.
- **Manufacturer** — Map an existing specification sheet to the catalog columns and keep the consistent field names in a small mapping JSON. Validate first before exporting a revised product line.
- **Wholesale or e-commerce supplier** — Build a four-up line sheet with the Modern template. Use an approved product image per model and print one copy to check the small type at A4 scale.
