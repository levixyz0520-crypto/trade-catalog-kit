"""Compatibility interface for the original v0.1 CSV script."""

from dataclasses import dataclass
from pathlib import Path

from trade_catalog_kit.cli import main as run_cli
from trade_catalog_kit.data import Product as CatalogProduct
from trade_catalog_kit.data import dimensions as parse_dimensions
from trade_catalog_kit.data import number, read_table, validate
from trade_catalog_kit.images import ImageLibrary, inspect
from trade_catalog_kit.pdf import CatalogOptions, render_pdf, write_pdf

REQUIRED = ('sku', 'name', 'size_cm', 'image')
OPTIONAL = ('carton_cm', 'gross_kg', 'cbm', 'colors', 'notes')


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    size_cm: str
    image: Path
    carton_cm: str = ''
    gross_kg: str = ''
    cbm: str = ''
    colors: str = ''
    notes: str = ''


def dimensions(value):
    return list(map(float, parse_dimensions(value)))


def positive(value):
    return float(number(value, 'Value', 1_000_000_000))


def read_products(csv_path, image_dir):
    """Read the original CSV schema, including its mandatory Image column."""
    table = read_table(Path(csv_path))
    if set(REQUIRED) - set(table.headers):
        raise ValueError('missing columns: ' + ', '.join(sorted(set(REQUIRED) - set(table.headers))))
    validation = validate(table)
    errors = [str(item).replace('Duplicate product code', 'duplicate SKU').replace('No product', 'no product')
              for item in validation.diagnostics if item.level == 'error']
    rows = {line: dict(zip(table.headers, fields)) for line, fields in table.rows}
    library = ImageLibrary(image_dir)
    products = []
    for product in validation.products:
        cells = rows[product.row]
        try:
            if not product.image:
                raise ValueError('image must be an existing file inside image directory')
            image = library.match(product)
            if image is None:
                raise ValueError('image must be an existing file inside image directory')
            inspect(image)
            cbm = cells.get('cbm', '') or (f'{product.cbm:.6f}' if product.cbm is not None else '')
            products.append(Product(product.code, product.name, cells['size_cm'], image,
                                    product.carton, cells.get('gross_kg', ''), cbm, product.color,
                                    product.description))
        except (OSError, ValueError) as exc:
            errors.append(f'row {product.row}: {str(exc).replace("inside the image directory", "inside image directory")}')
    if errors:
        raise ValueError('\n'.join(errors))
    return products


def build_pdf(products, out, brand='PRODUCT COLLECTION'):
    catalog, photos = [], {}
    for product in products:
        photos[product.sku] = product.image
        cbm = number(product.cbm, 'CBM', 1_000_000) if product.cbm else None
        catalog.append(CatalogProduct(0, product.sku, product.name, '', product.size_cm, product.carton_cm,
                                      product.gross_kg + ' kg' if product.gross_kg else '', cbm, 1, None,
                                      None, product.colors, '', product.notes, ''))
    options = CatalogOptions(brand=brand, include_cover=False, include_back=False)
    write_pdf(out, render_pdf(catalog, photos, options))


def main(argv=None):
    return run_cli(argv, legacy=True)


if __name__ == '__main__':
    raise SystemExit(main())
