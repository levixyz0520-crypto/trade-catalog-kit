from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest
from PIL import ImageStat
from pypdf import PdfReader
from reportlab import __file__ as reportlab_path

from trade_catalog_kit.cli import main
from trade_catalog_kit.data import read_table, validate
from trade_catalog_kit.images import ImageLibrary, match_images
from trade_catalog_kit.pdf import CatalogOptions, render_pdf
from trade_catalog_kit.preview import preview_page

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples'


@pytest.fixture(scope='module')
def demo():
    data = validate(read_table(EXAMPLES / 'furniture.xlsx'))
    photos, _ = match_images(data.products, ImageLibrary(EXAMPLES / 'images'))
    return data.products, photos


@pytest.mark.parametrize('theme,per_page,count', [('editorial', 1, 8), ('modern', 2, 6), ('minimal', 4, 5)])
def test_pdf_pages_draw_and_keep_product_data_on_the_right_page(demo, theme, per_page, count):
    products, photos = demo
    options = CatalogOptions(brand='Sample & Co.', about='Our furniture', contact='hello@example.invalid',
                             theme=theme, accent='#234567', per_page=per_page,
                             logo=ROOT / 'assets' / 'demo-logo.png')
    contents = render_pdf(products, photos, options)
    document = PdfReader(BytesIO(contents))
    assert len(document.pages) == count
    assert 'Product Catalog' in document.pages[0].extract_text()
    assert 'Our furniture' in document.pages[1].extract_text()
    assert 'hello@example.invalid' in document.pages[-2].extract_text()
    assert 'hello@example.invalid' in document.pages[-1].extract_text()
    for page_index in range(2, count - 2):
        page = document.pages[page_index]
        text = page.extract_text()
        expected = products[(page_index - 2) * per_page:(page_index - 1) * per_page]
        for item in expected:
            assert item.name in " ".join(text.split()) and item.code in text
        for item in (p for p in products if p not in expected):
            assert item.code not in text
        assert 'estimates use volume only' in text
        assert len(page.images) == len(expected)
        assert f'{page_index + 1:02d} / {count:02d}' in text
        raster, total = preview_page(contents, page_index)
        assert total == count and raster.width > 700 and max(ImageStat.Stat(raster).stddev) > 10


def test_pdf_chinese_and_custom_font(demo):
    products, photos = demo
    first = replace(products[0], name='家具柜')
    zh = render_pdf([first], photos, CatalogOptions(brand='橡木贸易', language='zh', per_page=1))
    assert '家具柜' in PdfReader(BytesIO(zh)).pages[1].extract_text()
    assert preview_page(zh, 1)[0].width > 700
    vera = Path(reportlab_path).parent / 'fonts' / 'Vera.ttf'
    font = vera.read_bytes()
    opts = CatalogOptions(brand='Établissement', font=font, include_back=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        files = list(pool.map(lambda _: render_pdf(products[:1], photos, opts), range(3)))
    assert all('Établissement' in PdfReader(BytesIO(data)).pages[0].extract_text() for data in files)
    with pytest.raises(ValueError, match='cannot display'):
        render_pdf([first], photos, opts)


def test_pdf_reports_invalid_layout_and_empty_input(demo):
    products, photos = demo
    with pytest.raises(ValueError, match='No products'):
        render_pdf([], photos)
    with pytest.raises(ValueError, match='available space'):
        render_pdf([replace(products[0], description='Long line\n' * 65)], photos, CatalogOptions(per_page=4))
    with pytest.raises(ValueError, match='six-digit'):
        render_pdf(products, photos, CatalogOptions(accent='red'))


def test_cli_check_generation_and_atomic_failure(tmp_path):
    args = [str(EXAMPLES / 'furniture.xlsx'), '--images', str(EXAMPLES / 'images')]
    target = tmp_path / 'catalog.pdf'
    assert main([*args, '--out', str(target), '--check']) == 0
    assert not target.exists()
    assert main([*args, '--per-page', '4', '--out', str(target)]) == 0
    saved = target.read_bytes()
    assert main([*args, '--out', str(target), '--accent', '#00000']) == 1
    assert target.read_bytes() == saved
    assert main([*args, '--out', str(EXAMPLES / 'furniture.xlsx')]) == 1
    assert main([str(EXAMPLES / 'furniture.xlsx'), '--strict-images', '--check']) == 1


def test_cli_mapping_and_missing_image_placeholder(tmp_path):
    source = tmp_path / 'local.csv'
    source.write_text('Part,Description,Dimensions\nA,Sample,1 x 2 x 3\n', encoding='utf-8')
    mapping = tmp_path / 'map.json'
    mapping.write_text('{"Product Code": "Part", "Product Name": "Description", "Product Size": "Dimensions", "Description": null}')
    output = tmp_path / 'catalog.pdf'
    assert main([str(source), '--mapping', str(mapping), '--out', str(output)]) == 0
    assert 'Image unavailable' in PdfReader(output).pages[1].extract_text()
