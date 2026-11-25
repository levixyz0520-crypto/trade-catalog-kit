"""Regenerate the original demonstration art, templates and catalogs."""

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from PIL import Image, ImageDraw

from trade_catalog_kit.data import HEADERS, read_table, validate
from trade_catalog_kit.images import ImageLibrary, ImageOptions, match_images
from trade_catalog_kit.pdf import CatalogOptions, render_pdf, write_pdf

EXAMPLES = Path(__file__).resolve().parent
INSTRUCTIONS = (
    'Required. Enter a unique code as text, e.g. 001-F.', 'Required. Enter the product name.',
    'Optional. Group or collection name.', 'Required. Example: 80 x 40 x 90 cm.',
    'Optional. Separate different carton sizes with semicolons.', 'Optional. Use kg, g or lb. Default kg.',
    'Optional. Total cubic metres per piece. Calculated if blank and carton sizes exist.',
    'Optional. Repeat a single carton size, or supply one size per carton.',
    'Optional. Source quantity. The tool calculates and labels a separate theoretical estimate.',
    'Optional. Product finishes or colors.', 'Optional. Main materials.',
    'Optional. Short description. Dense layouts have less room.',
    'Optional. Image filename. If blank, match by product code.',
)
PRODUCTS = (
    ('DEMO-001', 'Arc Storage Cabinet', 'Storage', '80 × 40 × 90 cm', '92 × 45 × 18 cm', '24 kg', '', '1', '',
     'Warm white / oak', 'Oak veneer, steel', 'A two-door cabinet for compact living spaces.', 'cabinet.png'),
    ('DEMO-002', 'Cove Side Table', 'Occasional tables', '45 × 45 × 50 cm', '53 × 50 × 12 cm', '8 kg', '', '1', '',
     'Natural oak', 'Oak veneer, solid wood', 'A compact side table with a square top.', 'table.png'),
    ('DEMO-003', 'Ridge Dining Bench', 'Seating', '1.2 × .36 × .45 m', '125 × 42 × 12 cm; 43 × 22 × 12 cm',
     '39 lb', '', '2', '', 'Smoked oak', 'Solid wood, steel', 'Ships in separate top and frame cartons.', ''),
    ('DEMO-004', 'Dune Open Shelf', 'Storage', '900 × 325 × 1020 mm', '98 × 36 × 14 cm', '17.5 kg', '', '1', '',
     'Sage / oak', 'Powder-coated steel, veneer', 'An open three-tier shelf for retail displays.', ''),
)


def workbook(path, rows):
    book = Workbook()
    sheet = book.active
    sheet.title = 'Products'
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    for index, instruction in enumerate(INSTRUCTIONS, 1):
        cell = sheet.cell(1, index)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='28425C')
        cell.alignment = Alignment(vertical='center')
        cell.comment = Comment(instruction, 'Trade Catalog Kit')
        sheet.column_dimensions[get_column_letter(index)].width = (45 if index in (5, 12) else 22)
    sheet.column_dimensions['A'].number_format = '@'
    for index in range(2, 502):
        sheet.cell(index, 1).number_format = '@'
    sheet.row_dimensions[1].height = 28
    sheet.freeze_panes = 'C2'
    guide = book.create_sheet('Guide')
    guide.append(['Column', 'How to fill it'])
    for header, instruction in zip(HEADERS, INSTRUCTIONS):
        guide.append([header, instruction])
    guide.column_dimensions['A'].width = 24
    guide.column_dimensions['B'].width = 90
    book.save(path)


def demonstration_art():
    folder = EXAMPLES / 'images'
    art = Image.new('RGB', (1000, 760), '#FFFFFF')
    draw = ImageDraw.Draw(art)
    draw.ellipse((110, 563, 908, 644), fill='#EFE8DF')
    for x, y in ((740, 308), (725, 391), (265, 457), (157, 408)):
        draw.polygon([(x, y), (x + 31, y - 6), (x + 27, y + 171), (x - 5, y + 179)], fill='#394241')
    draw.polygon([(138, 348), (672, 229), (865, 301), (321, 425)], fill='#BB9371')
    draw.polygon([(138, 348), (321, 425), (321, 452), (138, 375)], fill='#A37B5C')
    draw.polygon([(321, 425), (865, 301), (865, 332), (321, 452)], fill='#87634E')
    for shift in range(8, 39, 9):
        draw.line([(163 + shift * 4, 349 + shift), (655 + shift * 4, 235 + shift)], fill='#AC8465', width=2)
    art.save(folder / 'DEMO-003.png', optimize=True)

    art = Image.new('RGB', (1000, 760), '#FFFFFF')
    draw = ImageDraw.Draw(art)
    draw.ellipse((115, 570, 902, 658), fill='#EDEFE9')
    for x, y in ((587, 108), (753, 160)):
        draw.line((x, y, x, y + 435), fill='#58716A', width=16)
    for y in (185, 355, 525):
        draw.polygon([(235, y + 24), (588, y - 53), (765, y + 13), (411, y + 92)], fill='#C2A587')
        draw.polygon([(235, y + 24), (411, y + 92), (411, y + 113), (235, y + 45)], fill='#9F856B')
        draw.polygon([(411, y + 92), (765, y + 13), (765, y + 34), (411, y + 113)], fill='#AD9176')
    for x, y in ((236, 188), (412, 252)):
        draw.line((x, y, x, y + 426), fill='#58716A', width=16)
    art.save(folder / 'DEMO-004.png', optimize=True)

    logo = Image.new('RGBA', (171, 70), (255, 255, 255, 0))
    draw = ImageDraw.Draw(logo)
    for offset in (15, 88):
        draw.rectangle((offset, 13, offset + 48, 57), width=4, outline='#635B51')
        draw.line((offset, 55, offset + 45, 14), fill='#AE4B35', width=4)
    logo.save(EXAMPLES.parent / 'assets' / 'demo-logo.png', optimize=True)


def main():
    demonstration_art()
    for base, rows in (('product-template', ()), ('furniture', PRODUCTS)):
        with (EXAMPLES / f'{base}.csv').open('w', encoding='utf-8-sig', newline='') as stream:
            csv.writer(stream, lineterminator='\n').writerows((HEADERS, *rows))
        workbook(EXAMPLES / f'{base}.xlsx', rows)
    data = validate(read_table(EXAMPLES / 'furniture.xlsx'))
    assert data.valid, data.diagnostics
    pictures, diagnostics = match_images(data.products, ImageLibrary(EXAMPLES / 'images'))
    assert not diagnostics, diagnostics
    for theme, per_page, language, brand, title, about, contact in (
        ('editorial', 2, 'en', 'Oak & Harbor', 'Furniture Collection',
         'A fictional furniture range for compact living and retail displays.\n\n'
         'This sample demonstrates how product dimensions, packaging and authorized images can appear together in a buyer-facing catalog.',
         'Sample contact\ncatalog@example.invalid'),
        ('modern', 4, 'en', 'Oak & Harbor', 'Furniture Collection',
         'A fictional furniture range for compact living and retail displays.', 'catalog@example.invalid'),
        ('minimal', 1, 'zh', '橡木港', '家具产品目录', '这是用于展示目录生成流程的虚构家具系列。', '示例邮箱：catalog@example.invalid'),
    ):
        options = CatalogOptions(brand=brand, title=title, about=about, contact=contact,
                                 theme=theme, per_page=per_page, language=language,
                                 logo=EXAMPLES.parent / 'assets' / 'demo-logo.png',
                                 images=ImageOptions(white=theme != 'minimal'))
        filename = 'demo.pdf' if theme == 'editorial' else f'demo-{theme}.pdf'
        write_pdf(EXAMPLES / filename, render_pdf(data.products, pictures, options))


if __name__ == '__main__':
    main()
