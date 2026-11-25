"""Streamlit interface for Trade Catalog Kit."""

from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path

import streamlit as st

from trade_catalog_kit.data import FIELDS, LABELS, auto_mapping, formatted, read_table, validate
from trade_catalog_kit.images import ImageLibrary, ImageOptions, match_images
from trade_catalog_kit.pdf import THEMES, CatalogOptions, render_pdf
from trade_catalog_kit.preview import preview_page

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / 'examples'


def digest(value):
    return sha256(value).hexdigest() if value is not None else ''


def show_diagnostics(diagnostics):
    important = [item for item in diagnostics if item.level == 'error']
    warnings = [item for item in diagnostics if item.level == 'warning']
    for items, show in ((important, st.error), (warnings, st.warning)):
        if items:
            show('\n\n'.join(str(item) for item in items[:6]))
            if len(items) > 6:
                with st.expander(f'{len(items) - 6} more {items[0].level}s'):
                    st.text('\n'.join(str(item) for item in items[6:]))


def main():
    st.set_page_config(page_title='Trade Catalog Kit', page_icon='▤', layout='wide')
    st.markdown('''<style>
        .block-container {max-width: 1120px; padding-top: 3rem;}
        .st-key-catalog_intro {border-left: 4px solid #bb5b3f; padding: .15rem 0 .15rem 1.1rem;}
        .st-key-catalog_intro h1 {font-size: clamp(2.1rem, 5vw, 3.7rem); letter-spacing: -.055em;}
        .st-key-catalog_intro p {font-size: 1.05rem;}
    </style>''', unsafe_allow_html=True)
    with st.container(key='catalog_intro'):
        st.title('Trade Catalog Kit')
        st.write('Turn your product spreadsheet and images into a PDF catalog.')

    st.header('Product files')
    left, right = st.columns(2)
    with left:
        uploaded = st.file_uploader('Product spreadsheet', type=['xlsx', 'csv'],
                                    help='Use the first sheet in Excel or a UTF-8 CSV.')
    with right:
        attachments = st.file_uploader('Product images', type=['jpg', 'jpeg', 'png', 'webp'],
                                       accept_multiple_files=True,
                                       help='Match by the Image column or a filename such as SKU-001.jpg.')
    actions = st.columns([2, 1, 1])
    demo = actions[0].checkbox('Try the included furniture example', value=False, disabled=uploaded is not None)
    actions[1].download_button('Excel template', (DEMO / 'product-template.xlsx').read_bytes(),
                               file_name='product-template.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    actions[2].download_button('CSV template', (DEMO / 'product-template.csv').read_bytes(),
                               file_name='product-template.csv', mime='text/csv')
    if uploaded is None and not demo:
        st.session_state.pop('catalog_result', None)
        return
    using_demo = uploaded is None
    filename = DEMO.joinpath('furniture.xlsx').name if using_demo else uploaded.name
    raw = (DEMO / filename).read_bytes() if using_demo else uploaded.getvalue()
    uploads = [(item.name, item.getvalue()) for item in attachments]
    try:
        table = read_table(raw, filename)
        library = ImageLibrary(DEMO / 'images' if using_demo and not uploads else None, uploads)
    except (OSError, RuntimeError, ValueError) as exc:
        st.session_state.pop('catalog_result', None)
        st.error(str(exc))
        return

    mapping = auto_mapping(table.headers)
    choices = ['', *[header for header in table.headers if header]]
    with st.expander('Column mapping and 40HQ estimate', expanded=not all(f in mapping for f in ('code', 'name', 'size'))):
        left, right = st.columns(2)
        form_key = digest(raw)[:16]
        for index, field in enumerate(FIELDS):
            column = left if index % 2 == 0 else right
            mapping[field] = column.selectbox(LABELS[field], choices, choices.index(mapping.get(field, '')),
                                              format_func=lambda value: value or 'Unused', key=f'{form_key}_{field}')
        volume = left.number_input('Available container volume (m³)', min_value=0.01, max_value=1000.0, value=76.0)
        efficiency = right.number_input('Volume utilization (%)', min_value=1, max_value=100, value=85)
        st.caption('The 40HQ estimate uses volume only. Actual loading depends on dimensions, weight and packing.')

    st.header('Data review')
    try:
        data = validate(table, mapping, volume, efficiency / 100)
    except ValueError as exc:
        st.session_state.pop('catalog_result', None)
        st.error(str(exc))
        return
    photos, image_diagnostics = match_images(data.products, library)
    show_diagnostics(data.diagnostics + image_diagnostics)
    if not data.valid or any(item.level == 'error' for item in image_diagnostics):
        st.session_state.pop('catalog_result', None)
        return
    first, second = st.columns(2)
    first.metric('Validated products', len(data.products))
    second.metric('Matched images', f'{len(photos)} / {len(data.products)}')
    st.dataframe([{'Product code': p.code, 'Product name': p.name, 'Category': p.category,
                   'CBM per piece': formatted(p.cbm) if p.cbm is not None else None,
                   '40HQ estimate': p.quantity, '40HQ supplied': p.supplied_quantity,
                   'Image matched': p.code in photos} for p in data.products], hide_index=True)

    st.header('Catalog design')
    left, right = st.columns(2)
    theme = left.selectbox('Template', list(THEMES), format_func=str.title)
    per_page = right.radio('Products per page', (1, 2, 4), index=1, horizontal=True)
    brand = left.text_input('Brand name', 'Oak & Harbor' if using_demo else 'Your brand', max_chars=100,
                            key=f'{using_demo}_brand')
    language = right.selectbox('PDF labels', ['en', 'zh'], format_func=lambda value: {'en': 'English', 'zh': '简体中文'}[value])
    title = left.text_input('Cover title', 'Furniture Collection' if using_demo else '', max_chars=120,
                            key=f'{using_demo}_title')
    accent = right.color_picker('Accent color', THEMES[theme].accent, key=f'accent_{theme}')
    with st.expander('Company pages, logo and image settings'):
        about = st.text_area('Company introduction',
                             'A fictional furniture collection demonstrating the Trade Catalog Kit workflow.' if using_demo else '',
                             max_chars=1400, key=f'{using_demo}_about')
        contact = st.text_area('Contact details', 'catalog@example.invalid' if using_demo else '',
                               max_chars=1000, key=f'{using_demo}_contact')
        back = st.text_area('Back cover message', max_chars=1000)
        left, right = st.columns(2)
        logo = left.file_uploader('Logo', type=['jpg', 'jpeg', 'png', 'webp'])
        font = right.file_uploader('Custom TrueType font', type=['ttf'])
        cover = left.checkbox('Include cover', value=True)
        back_cover = right.checkbox('Include back cover', value=True)
        crop = left.checkbox('Center-crop images to fill the frame')
        white = right.checkbox('Use white behind transparent images', value=True)
        quality = left.slider('JPEG quality', 60, 95, 86)
        ai = right.checkbox('Remove backgrounds with local AI', disabled=find_spec('rembg') is None,
                            help='Requires the optional AI extra and a model download on first use.')

    st.header('PDF preview')
    logo_data = logo.getvalue() if logo else None
    font_data = font.getvalue() if font else None
    signature = (filename, digest(raw), tuple((name, digest(blob)) for name, blob in uploads),
                 tuple(mapping.items()), volume, efficiency, brand, title, about, contact, back,
                 theme, accent, per_page, language, digest(logo_data), digest(font_data),
                 cover, back_cover, crop, white, quality, ai)
    previous = st.session_state.get('catalog_result')
    if previous and previous[0] != signature:
        st.session_state.pop('catalog_result')
    if st.button('Generate PDF preview', type='primary'):
        options = CatalogOptions(brand=brand, title=title, about=about, contact=contact, back=back,
                                 theme=theme, accent=accent, per_page=per_page, language=language,
                                 font=font_data, logo=logo_data, images=ImageOptions(crop, white, quality, ai),
                                 include_cover=cover, include_back=back_cover)
        try:
            with st.spinner('Generating catalog…'):
                contents = render_pdf(data.products, photos, options)
                _, count = preview_page(contents)
            st.session_state.catalog_result = (signature, contents, count)
        except (OSError, RuntimeError, ValueError) as exc:
            st.session_state.pop('catalog_result', None)
            st.error(str(exc))
    if 'catalog_result' in st.session_state:
        _, contents, count = st.session_state.catalog_result
        left, right = st.columns([1, 3])
        number = left.number_input('Preview page', 1, count, 1, key=f'page_{digest(contents)[:12]}') if count > 1 else 1
        left.caption(f'{count} PDF page(s)')
        left.download_button('Download catalog PDF', contents, file_name='catalog.pdf', mime='application/pdf')
        page, _ = preview_page(contents, number - 1)
        right.image(page, caption=f'Page {number} of {count}')


if __name__ == '__main__':
    main()
