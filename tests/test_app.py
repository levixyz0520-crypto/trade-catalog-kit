from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples'


def test_upload_review_preview_and_download():
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
    assert not app.exception
    assert len(app.download_button) == 2
    assert not app.button

    spreadsheet = EXAMPLES / 'furniture.xlsx'
    images = [(photo.name, photo.read_bytes(), 'image/png') for photo in sorted((EXAMPLES / 'images').glob('*.png'))]
    app.file_uploader[0].upload(spreadsheet.name, spreadsheet.read_bytes())
    app.file_uploader[1].set_value(images).run()
    assert not app.exception and not app.error
    assert [metric.value for metric in app.metric] == ['4', '4 / 4']

    next(item for item in app.selectbox if item.label == 'Template').select('modern')
    next(item for item in app.text_input if item.label == 'Brand name').set_value('Buyer Demo')
    app.radio[0].set_value(4).run()
    app.button[0].click().run()
    assert not app.exception and not app.error
    assert app.download_button[-1].label == 'Download catalog PDF'
    _, contents, page_count = app.session_state['catalog_result']
    pdf = PdfReader(BytesIO(contents))
    assert page_count == len(pdf.pages) == 3
    assert 'Buyer Demo' in pdf.pages[0].extract_text()
    assert 'DEMO-004' in pdf.pages[1].extract_text()
    next(item for item in app.number_input if item.label == 'Preview page').set_value(2).run()
    assert not app.exception
    assert app.get('image')[0].proto.imgs[0].caption == 'Page 2 of 3'

    next(item for item in app.text_input if item.label == 'Brand name').set_value('New name').run()
    assert 'catalog_result' not in app.session_state
    assert len(app.download_button) == 2


def test_invalid_upload_disables_export():
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
    app.file_uploader[0].upload('sample.csv', b'Product Code,Product Name,Product Size\nA,Desk,0 x 2 x 4\n').run()
    assert not app.exception and app.error
    assert 'finite positive' in app.error[0].value
    assert len(app.download_button) == 2 and not app.button
