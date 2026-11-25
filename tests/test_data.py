import csv
import io
from decimal import Decimal
from zipfile import ZipFile

import pytest
from openpyxl import Workbook

from trade_catalog_kit.data import HEADERS, dimensions, read_table, validate


def as_csv(rows):
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return buffer.getvalue().encode('utf-8-sig')


def as_xlsx(rows):
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    workbook.create_sheet('Ignored').append(['Do not import'])
    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()


@pytest.mark.parametrize('encode, suffix', [(as_csv, 'csv'), (as_xlsx, 'xlsx')])
def test_standard_spreadsheet_import(encode, suffix):
    source = encode([HEADERS, ['001', '木椅', '家具', '800 x 40 cm x .75 m',
                              '100 × 50 × 20 cm', '4 lb', '', 2, 325, '蓝', '木', 'With armrest', '001.webp']])
    # All three components have explicit units when a value uses mixed units.
    invalid = validate(read_table(source, f'input.{suffix}'))
    assert 'mixing' in str(invalid.diagnostics[0])
    source = encode([HEADERS, ['001', '木椅', '家具', '800 mm x 40 cm x .75 m',
                              '100 × 50 × 20 cm', '4 lb', '', 2, 325, '蓝', '木', 'With armrest', '001.webp']])
    checked = validate(read_table(source, f'input.{suffix}'), volume=80, utilization=.8)
    assert checked.valid
    product, = checked.products
    assert (product.code, product.name, product.size, product.weight, product.cbm) == (
        '001', '木椅', '80 × 40 × 75 cm', '1.81436948 kg', Decimal('.2'))
    assert (product.quantity, product.supplied_quantity, product.cartons) == (320, 325, 2)
    assert checked.diagnostics[0].level == 'warning'


def test_mapped_headers_and_distinct_cartons():
    table = read_table(as_csv([['Item no.', 'Title', 'Dimensions', 'Carton Size'],
                                ['A01', 'Desk', '40 x 25 x 10 in', '20 x 30 x 40; 50 x 40 x 20']]), 'items.csv')
    mapping = {'code': 'Item no.', 'name': 'Title', 'size': 'Dimensions'}
    assert not validate(table).valid
    checked = validate(table, mapping)
    product, = checked.products
    assert product.size == '101.6 × 63.5 × 25.4 cm'
    assert product.cbm == Decimal('.064')
    assert product.cartons == 2
    assert product.quantity == 1009
    with pytest.raises(ValueError, match='at most one'):
        validate(table, mapping | {'name': 'Item no.'})


def test_invalid_rows_report_real_csv_line_numbers():
    table = read_table(as_csv([['Product Code', 'Product Name', 'Product Size'],
                                ['a', 'Line one\nLine two', '1 x 2 x 3'],
                                ['A', 'Duplicate', '1 x 2 x 3'],
                                ['', 'No code', '1 x 2 x 3'],
                                ['B', 'Bad size', '0 x 2 x 3'],
                                ['C', 'Extra cell', '1 x 2 x 3', 'extra']]), 'items.csv')
    result = validate(table)
    assert not result.valid
    assert [item.row for item in result.diagnostics] == [4, 5, 6, 7]
    assert 'Duplicate' in str(result.diagnostics[0])
    assert 'Missing' in str(result.diagnostics[1])
    assert 'positive' in str(result.diagnostics[2])
    assert 'beyond' in str(result.diagnostics[3])


@pytest.mark.parametrize('field,value,expected', [
    ('Cartons per Piece', '0', 'greater than zero'),
    ('Cartons per Piece', '1.5', 'whole number'),
    ('Gross Weight', 'nan', 'finite positive'),
    ('CBM', 'Infinity', 'finite positive'),
    ('40HQ Quantity', '1.25', 'whole number'),
    ('Carton Size', '1 x 2', 'three dimensions'),
])
def test_invalid_values(field, value, expected):
    source = as_csv([['sku', 'name', 'size_cm', field], ['A', 'Desk', '1 x 2 x 3', value]])
    result = validate(read_table(source, 'products.csv'))
    assert not result.valid
    assert expected in str(result.diagnostics[0])


def test_supplied_cbm_overrides_count_and_can_produce_zero_estimate():
    table = read_table(as_csv([['sku', 'name', 'size_cm', 'carton_cm', 'cbm'],
                                ['K', 'Example', '1 x 2 x 3', '1 x 2 x 3', '100']]), 'data.csv')
    result = validate(table, utilization=1)
    assert result.valid and result.products[0].quantity == 0
    assert len(result.diagnostics) == 2
    with pytest.raises(ValueError, match='Utilization'):
        validate(table, utilization=1.1)


def test_xlsx_formula_and_mismatched_carton_count():
    workbook = as_xlsx([['sku', 'name', 'size_cm', 'carton_cm', 'Cartons per Piece'],
                        ['A', '=1+1', '1 x 2 x 3', '', ''],
                        ['B', 'Desk', '1 x 2 x 3', '1 x 2 x 3; 2 x 3 x 4', '3']])
    result = validate(read_table(workbook, 'products.XLSX'))
    assert ['formulas' in str(result.diagnostics[0]), 'must equal' in str(result.diagnostics[1])] == [True, True]


def test_empty_bad_encoding_duplicate_headers_and_expanded_limit():
    with pytest.raises(ValueError, match='empty'):
        read_table(b'', 'data.csv')
    with pytest.raises(ValueError, match='UTF-8'):
        read_table(b'\xff\xff\xff', 'data.csv')
    with pytest.raises(ValueError, match='unique'):
        read_table(as_csv([['Product Code', 'Product-Code']]), 'data.csv')
    with pytest.raises(ValueError, match='valid XLSX'):
        read_table(b'bad', 'data.xlsx')
    workbook = io.BytesIO()
    with ZipFile(workbook, 'w') as archive:
        for i in range(1025):
            archive.writestr(f'{i}.txt', '')
    with pytest.raises(ValueError, match='Expanded'):
        read_table(workbook.getvalue(), 'large.xlsx')
    checked = validate(read_table(as_csv([HEADERS]), 'empty.csv'))
    assert not checked.valid and 'No product rows' in str(checked.diagnostics[0])


def test_mm_and_feet():
    assert dimensions('100 mm x 1 ft x 1 in') == (Decimal('10.0'), Decimal('30.48'), Decimal('2.54'))
