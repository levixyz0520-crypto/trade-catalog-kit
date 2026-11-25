"""Read catalog files and validate their product and packaging specifications."""

import csv
import io
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from defusedxml.common import DefusedXmlException
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

HEADERS = (
    'Product Code', 'Product Name', 'Category', 'Product Size', 'Carton Size',
    'Gross Weight', 'CBM', 'Cartons per Piece', '40HQ Quantity', 'Color',
    'Material', 'Description', 'Image',
)
FIELDS = (
    'code', 'name', 'category', 'size', 'carton', 'weight', 'cbm', 'cartons',
    'quantity', 'color', 'material', 'description', 'image',
)
LABELS = dict(zip(FIELDS, HEADERS))
LEGACY = {'sku': 'code', 'size_cm': 'size', 'carton_cm': 'carton',
          'gross_kg': 'weight', 'colors': 'color', 'notes': 'description'}
MAX_FILE = 16 * 1024 * 1024
MAX_ROWS = 5001
MAX_COLUMNS = 100
REQUIRED = ('code', 'name', 'size')


def key(text):
    return re.sub(r'[\s_-]+', ' ', text.strip().casefold())


ALIASES = {key(label): field for field, label in LABELS.items()}
ALIASES.update({key(alias): field for alias, field in LEGACY.items()})
ALIASES.update({key(field): field for field in FIELDS})


@dataclass(frozen=True)
class Diagnostic:
    row: int | None
    message: str
    level: str = 'error'

    def __str__(self):
        return f'Row {self.row}: {self.message}' if self.row else self.message


@dataclass(frozen=True)
class Table:
    headers: tuple[str, ...]
    rows: tuple[tuple[int, tuple[str, ...]], ...]
    formulas: frozenset[tuple[int, int]] = frozenset()


@dataclass(frozen=True)
class Product:
    row: int
    code: str
    name: str
    category: str
    size: str
    carton: str
    weight: str
    cbm: Decimal | None
    cartons: int | None
    quantity: int | None
    supplied_quantity: int | None
    color: str
    material: str
    description: str
    image: str


@dataclass(frozen=True)
class Validation:
    products: tuple[Product, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def valid(self):
        return bool(self.products) and not any(d.level == 'error' for d in self.diagnostics)


def as_text(value):
    return '' if value is None else str(value).strip()


def read_table(source: Path | bytes, filename: str = '') -> Table:
    """Read UTF-8 CSV or the first worksheet of an XLSX file."""
    if isinstance(source, Path):
        filename = source.name
        with source.open('rb') as stream:
            source = stream.read(MAX_FILE + 1)
    if len(source) > MAX_FILE:
        raise ValueError('Spreadsheet exceeds 16 MiB.')
    suffix = Path(filename).suffix.lower()
    rows, formulas = [], set()
    try:
        if suffix == '.csv':
            with io.TextIOWrapper(io.BytesIO(source), encoding='utf-8-sig', newline='') as stream:
                reader = csv.reader(stream, strict=True)
                while True:
                    line = reader.line_num + 1
                    values = next(reader, None)
                    if values is None:
                        break
                    append_row(rows, line, values)
        elif suffix == '.xlsx':
            with ZipFile(io.BytesIO(source)) as archive:
                entries = archive.infolist()
                if len(entries) > 1024 or sum(member.file_size for member in entries) > 64 * 1024 * 1024:
                    raise ValueError('Expanded workbook exceeds the XLSX size limit.')
            workbook = load_workbook(io.BytesIO(source), read_only=True, keep_links=False)
            try:
                if not workbook.worksheets:
                    raise ValueError('Workbook has no worksheets.')
                sheet = workbook.worksheets[0]
                # Bound iteration explicitly even if the worksheet reports invalid dimensions.
                sheet.reset_dimensions()
                for line, cells in enumerate(sheet.iter_rows(), 1):
                    values = [cell.value for cell in cells]
                    while values and values[-1] is None:
                        values.pop()
                    append_row(rows, line, values)
                    formulas.update((line, i) for i, cell in enumerate(cells) if cell.data_type in {'f', 'e'})
            finally:
                workbook.close()
        else:
            raise ValueError('Choose a .csv or .xlsx file.')
    except (UnicodeError, csv.Error, BadZipFile, InvalidFileException, DefusedXmlException,
            KeyError, SyntaxError, OverflowError, TypeError) as exc:
        raise ValueError(f'Cannot read {suffix.upper()} file. Use UTF-8 CSV or a valid XLSX workbook.') from exc
    if not rows:
        raise ValueError('Spreadsheet is empty.')
    headers = tuple(rows[0][1])
    nonempty = [key(header) for header in headers if header]
    if not nonempty or len(nonempty) != len(set(nonempty)):
        raise ValueError('Use nonempty, unique names for all columns you want to import.')
    if any(line == 1 for line, _ in formulas):
        raise ValueError('Column headers must be plain text.')
    return Table(headers, tuple(rows[1:]), frozenset(formulas))


def append_row(rows, line, values):
    if len(rows) >= MAX_ROWS or len(values) > MAX_COLUMNS:
        raise ValueError(f'Spreadsheet limit is {MAX_ROWS - 1} data rows and {MAX_COLUMNS} columns.')
    rows.append((line, tuple(map(as_text, values))))


def auto_mapping(headers):
    mapping = {}
    for header in headers:
        field = ALIASES.get(key(header))
        if field and field not in mapping:
            mapping[field] = header
    return mapping


def number(value, label, maximum):
    try:
        result = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError(f'{label} must be a finite positive number.') from exc
    if not result.is_finite() or not Decimal('0.000000000001') <= result <= maximum:
        raise ValueError(f'{label} must be a finite positive number between 0.000000000001 and {maximum}.')
    return result


def formatted(value):
    return f'{value.normalize():f}'


UNITS = {'mm': Decimal('0.1'), 'cm': Decimal(1), 'm': Decimal(100),
         'in': Decimal('2.54'), 'ft': Decimal('30.48')}
DIMENSION = re.compile(r'([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*(mm|cm|m|in|ft)?', re.I)


def dimensions(value):
    parts = re.split(r'\s*[x×*]\s*', value.strip(), flags=re.I)
    parsed = [DIMENSION.fullmatch(part) for part in parts]
    if len(parsed) != 3 or not all(parsed):
        raise ValueError('Enter three dimensions, e.g. 80 x 40 x 75 cm. Units: mm, cm, m, in, ft.')
    last_unit = parsed[-1][2]
    units = [item[2].lower() if item[2] else None for item in parsed]
    explicit = set(units) - {None}
    if None in units and len(explicit) > 1:
        raise ValueError('Specify every unit when mixing dimensions.')
    fallback = last_unit.lower() if last_unit else next(iter(explicit), 'cm')
    values = tuple(number(item[1], 'Dimension', 100_000) * UNITS[unit or fallback]
                   for item, unit in zip(parsed, units))
    if any(not Decimal('0.001') <= value <= 100_000 for value in values):
        raise ValueError('Each dimension must be between 0.001 and 100,000 cm.')
    return values


def dimension_text(values):
    return ' × '.join(map(formatted, values)) + ' cm'


def packaging(value, count):
    groups = value.split(';')
    total = Decimal(0)
    for group in groups:
        length, width, height = dimensions(group)
        total += length * width * height / 1_000_000
    if len(groups) == 1:
        return total * count
    if len(groups) != count:
        raise ValueError('For different cartons, Cartons per Piece must equal the number of carton sizes.')
    return total


def whole(value, label, maximum=1_000_000_000):
    if re.fullmatch(r'0(?:\.0+)?', value):
        return 0
    result = number(value, label, maximum)
    if result != result.to_integral_value():
        raise ValueError(f'{label} must be a whole number.')
    return int(result)


def weight_kg(value):
    match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*(kg|g|lb|lbs)?', value, re.I)
    if not match:
        raise ValueError('Gross Weight must be a finite positive number in kg, g or lb.')
    factor = {'kg': Decimal(1), 'g': Decimal('0.001'), 'lb': Decimal('0.45359237'),
              'lbs': Decimal('0.45359237')}
    return formatted(number(match[1], 'Gross Weight', 1_000_000) * factor[(match[2] or 'kg').lower()]) + ' kg'


def validate(table, overrides=None, volume='76', utilization='0.85') -> Validation:
    usable = number(volume, 'Container volume', 1000) * number(utilization, 'Utilization', 1)
    mapping = auto_mapping(table.headers)
    mapping.update(overrides or {})
    mapping = {field: header for field, header in mapping.items() if header}
    if set(mapping) - set(FIELDS) or set(mapping.values()) - set(table.headers):
        raise ValueError('Column mapping refers to an unknown field or header.')
    if len(set(mapping.values())) != len(mapping):
        raise ValueError('Map each source column to at most one catalog field.')
    missing = [LABELS[field] for field in REQUIRED if field not in mapping]
    if missing:
        return Validation((), (Diagnostic(None, 'Map required columns: ' + ', '.join(missing)),))
    indices = {field: table.headers.index(header) for field, header in mapping.items()}
    products, diagnostics, seen = [], [], set()
    for line, cells in table.rows:
        if not any(cells):
            continue
        if any(cells[len(table.headers):]):
            diagnostics.append(Diagnostic(line, 'Row has cells beyond the header.'))
            continue
        row = {field: cells[index] if index < len(cells) else '' for field, index in indices.items()}
        if not any(row.values()):
            continue
        values = {field: row.get(field, '') for field in FIELDS}
        duplicate = values['code'].casefold() in seen
        if values['code']:
            seen.add(values['code'].casefold())
        try:
            if any((line, idx) in table.formulas for idx in indices.values()):
                raise ValueError('Replace formulas and Excel errors with plain values in mapped columns.')
            blank = [LABELS[field] for field in REQUIRED if not values[field]]
            if blank:
                raise ValueError('Missing required values: ' + ', '.join(blank))
            if duplicate:
                raise ValueError('Duplicate product code: ' + values['code'])
            products.append(parse_product(line, values, usable, diagnostics))
        except ValueError as exc:
            diagnostics.append(Diagnostic(line, str(exc)))
    if not products and not diagnostics:
        diagnostics.append(Diagnostic(None, 'No product rows found.'))
    return Validation(tuple(products), tuple(diagnostics))


def parse_product(line, values, usable, diagnostics):
    lengths = {'code': 60, 'name': 150, 'category': 80, 'size': 90, 'carton': 400,
               'weight': 40, 'cbm': 40, 'cartons': 20, 'quantity': 20, 'color': 120,
               'material': 120, 'description': 600, 'image': 260}
    for field, limit in lengths.items():
        value = values[field]
        if len(value) > limit or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', value):
            raise ValueError(f'{LABELS[field]} exceeds {limit} characters or contains control characters.')
    size = dimension_text(dimensions(values['size']))
    carton = values['carton']
    count = whole(values['cartons'], 'Cartons per Piece', 10_000) if values['cartons'] else (
        len(carton.split(';')) if carton else None)
    if count == 0:
        raise ValueError('Cartons per Piece must be greater than zero.')
    weight = weight_kg(values['weight']) if values['weight'] else ''
    calculated = packaging(carton, count) if carton else None
    cbm = number(values['cbm'], 'CBM', 1_000_000) if values['cbm'] else calculated
    supplied = whole(values['quantity'], '40HQ Quantity') if values['quantity'] else None
    quantity = int(usable // cbm) if cbm else None
    if calculated and values['cbm'] and abs(cbm - calculated) > calculated * Decimal('0.05'):
        diagnostics.append(Diagnostic(line, 'Supplied CBM differs from carton calculation by over 5%. Supplied CBM is used.', 'warning'))
    if supplied is not None and quantity is not None and supplied != quantity:
        diagnostics.append(Diagnostic(line, 'Supplied 40HQ quantity differs from the volume estimate. Both are shown.', 'warning'))
    if cbm and cbm > usable:
        diagnostics.append(Diagnostic(line, 'One unit exceeds the adjusted container volume.', 'warning'))
    return Product(line, values['code'], values['name'], values['category'], size, carton, weight,
                   cbm, count, quantity, supplied, values['color'], values['material'],
                   values['description'], values['image'])
