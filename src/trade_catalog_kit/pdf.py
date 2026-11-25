"""Render branded catalogs with fixed page geometry and bounded text."""

import hashlib
import io
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from xml.sax.saxutils import escape

from reportlab import __file__ as reportlab_file
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from .data import formatted
from .images import ImageOptions, prepare

W, H = A4
MARGIN = 38
FONT_LOCK = RLock()
LATIN = 'CatalogLatin'
LATIN_BOLD = 'CatalogLatinBold'
CJK = 'STSong-Light'
LATIN_RUN = re.compile(r'([\x20-\x7e\xa0-\xff]+)')


@dataclass(frozen=True)
class Theme:
    accent: str
    ink: str
    muted: str
    paper: str
    surface: str
    line: str


THEMES = {
    'editorial': Theme('#AE4B35', '#262828', '#545955', '#F7F3ED', '#FFFFFF', '#DDD1C3'),
    'modern': Theme('#2559B1', '#192C47', '#53637A', '#EFF4F9', '#FFFFFF', '#C7D5E4'),
    'minimal': Theme('#2C6C52', '#21392F', '#4A6257', '#FFFFFF', '#F2F7F3', '#CFDBD3'),
}
LABELS = {
    'en': ('Product Catalog', 'About Us', 'Contact', 'Product range', 'Image unavailable',
           'Size', 'Carton', 'Gross weight', 'Volume / piece', 'Cartons / piece',
           '40HQ estimate', '40HQ supplied', 'Color', 'Material',
           '40HQ estimates use volume only. Actual loading can differ.'),
    'zh': ('产品目录', '公司介绍', '联系方式', '产品一览', '暂无图片', '产品尺寸', '包装尺寸',
           '毛重', '每件体积', '每件箱数', '40HQ 理论估算', '40HQ 提供值', '颜色', '材质',
           '40HQ 数量按体积理论估算，实际装柜量可能不同。'),
}



@dataclass(frozen=True)
class CatalogOptions:
    brand: str = 'PRODUCT COLLECTION'
    title: str = ''
    about: str = ''
    contact: str = ''
    back: str = ''
    theme: str = 'editorial'
    accent: str = ''
    per_page: int = 2
    language: str = 'en'
    font: bytes | None = None
    logo: bytes | Path | None = None
    images: ImageOptions = ImageOptions()
    include_cover: bool = True
    include_back: bool = True


class Catalog:
    def __init__(self, products, photos, options):
        if not products:
            raise ValueError('No products to render.')
        if options.theme not in THEMES or options.per_page not in (1, 2, 4) or options.language not in LABELS:
            raise ValueError('Select a supported theme, language and products per page.')
        if options.accent and not re.fullmatch(r'#[0-9a-fA-F]{6}', options.accent):
            raise ValueError('Theme color must be a six-digit hex color such as #2559B1.')
        if not options.brand.strip() or len(options.brand) > 100:
            raise ValueError('Brand must contain 1–100 characters.')
        self.products, self.photos, self.options = products, photos, options
        self.palette = THEMES[options.theme]
        self.accent = options.accent or self.palette.accent
        self.labels = LABELS[options.language]
        self.font, self.bold, self.glyphs = self.register_font()
        self.stream = io.BytesIO()
        self.canvas = Canvas(self.stream, pagesize=A4, pageCompression=1)
        self.canvas.setTitle(options.title or self.labels[0])
        self.canvas.setAuthor(options.brand)
        self.page = 0
        self.total = math.ceil(len(products) / options.per_page) + sum((options.include_cover,
                     bool(options.about), bool(options.contact), options.include_back))
        self.logo_reader = None
        if options.logo is not None:
            logo, width, height = prepare(options.logo, 100, 38, ImageOptions(white=False),
                                          self.palette.paper, max_side=600)
            self.logo_reader = (ImageReader(logo), width, height)

    def register_font(self):
        known = pdfmetrics.getRegisteredFontNames()
        fonts = Path(reportlab_file).parent / 'fonts'
        if LATIN not in known:
            pdfmetrics.registerFont(TTFont(LATIN, str(fonts / 'Vera.ttf')))
            pdfmetrics.registerFont(TTFont(LATIN_BOLD, str(fonts / 'VeraBd.ttf')))
        if self.options.font is not None:
            content = self.options.font
            if not content or len(content) > 12 * 1024 * 1024:
                raise ValueError('Choose a TrueType font of up to 12 MiB.')
            name = 'Catalog-' + hashlib.sha256(content).hexdigest()[:20]
            if name not in known:
                try:
                    pdfmetrics.registerFont(TTFont(name, io.BytesIO(content)))
                except Exception as exc:
                    raise ValueError('Unable to load this TrueType font. Use a supported .ttf font.') from exc
            return name, name, pdfmetrics.getFont(name).face.charToGlyph
        if self.options.language == 'zh':
            if CJK not in known:
                pdfmetrics.registerFont(UnicodeCIDFont(CJK))
            return CJK, CJK, None
        return LATIN, LATIN_BOLD, pdfmetrics.getFont(LATIN).face.charToGlyph

    def rect(self, x, top, width, height, fill, stroke=None, radius=0):
        self.canvas.setFillColor(HexColor(fill))
        if stroke:
            self.canvas.setStrokeColor(HexColor(stroke))
        if radius:
            self.canvas.roundRect(x, top - height, width, height, radius, fill=1, stroke=bool(stroke))
        else:
            self.canvas.rect(x, top - height, width, height, fill=1, stroke=bool(stroke))

    def rule(self, x, y, width, color):
        self.canvas.setStrokeColor(HexColor(color))
        self.canvas.line(x, y, x + width, y)

    def ink_on(self, background):
        color = HexColor(background)
        channels = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4
                    for x in (color.red, color.green, color.blue)]
        luminosity = sum(channel * weight for channel, weight in zip(channels, (.2126, .7152, .0722)))
        return '#161A1C' if luminosity > .179 else '#FFFFFF'

    def text(self, content, x, top, width, height, size, *, minimum=None, bold=False,
             color=None, label='Text'):
        if not content:
            return 0
        if self.glyphs is not None:
            missing = next((char for char in content if not char.isspace() and not self.glyphs.get(ord(char))), None)
            if missing is not None:
                raise ValueError(f'{label} contains {missing!r}, which the selected font cannot display. '
                                 'Select Chinese labels or provide a font with the required glyphs.')
        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        if self.font == CJK:
            latin = LATIN_BOLD if bold else LATIN
            lines = [f''.join(escape(run) if i % 2 == 0 else f'<font name="{latin}">{escape(run)}</font>'
                              for i, run in enumerate(LATIN_RUN.split(line))) for line in lines]
        else:
            lines = [escape(line) for line in lines]
        markup = '<br/>'.join(lines)
        minimum = size if minimum is None else minimum
        for point in range(size, minimum - 1, -1):
            style = ParagraphStyle('catalog', fontName=self.bold if bold else self.font,
                                   fontSize=point, leading=point * 1.22,
                                   textColor=HexColor(color or self.palette.ink),
                                   wordWrap='CJK' if self.options.language == 'zh' else None,
                                   splitLongWords=True)
            paragraph = Paragraph(markup, style)
            _, used = paragraph.wrap(width, height)
            if used <= height:
                paragraph.drawOn(self.canvas, x, top - used)
                return used
        raise ValueError(f'{label} exceeds the available space. Shorten it or use fewer products per page.')

    def start_page(self):
        self.page += 1
        self.rect(0, H, W, H, self.palette.paper)
        if self.options.theme == 'modern':
            self.rect(0, H, W, 9, self.accent)
        elif self.options.theme == 'editorial':
            self.rect(0, H, 10, H, self.accent)
        else:
            self.rule(MARGIN, H - 26, W - 2 * MARGIN, self.accent)

    def finish_page(self, disclaimer=False):
        self.rule(MARGIN, 45, W - 2 * MARGIN, self.palette.line)
        if disclaimer:
            self.text(self.labels[14], MARGIN, 34, W - 155, 18, 8, color=self.palette.muted)
        self.canvas.setFont(LATIN, 8)
        self.canvas.setFillColor(HexColor(self.palette.muted))
        self.canvas.drawRightString(W - MARGIN, 24, f'{self.page:02d} / {self.total:02d}')
        self.canvas.showPage()

    def fitted(self, image, x, top, width, height):
        reader, image_width, image_height = image
        ratio = min(width / image_width, height / image_height)
        render_width, render_height = image_width * ratio, image_height * ratio
        self.canvas.drawImage(reader, x + (width - render_width) / 2,
                              top - (height + render_height) / 2, render_width, render_height)

    def picture(self, product, x, top, width, height):
        self.rect(x, top, width, height, self.palette.surface)
        source = self.photos.get(product.code)
        if source is None:
            self.text(self.labels[4], x + 12, top - height / 2 + 5, width - 24, 20, 8, color=self.palette.muted)
            return
        try:
            photo, iw, ih = prepare(source, width, height, self.options.images, self.palette.surface)
        except ValueError as exc:
            raise ValueError(f'{product.code}: {exc}') from exc
        self.fitted((ImageReader(photo), iw, ih), x, top, width, height)

    def cover(self):
        self.start_page()
        o = self.options
        if self.logo_reader:
            self.fitted(self.logo_reader, MARGIN, H - 46, 100, 40)
        self.text(o.brand, MARGIN, H - 105, W - 2 * MARGIN, 40, 16, minimum=11, bold=True, label='Brand')
        title = o.title or self.labels[0]
        if o.theme == 'modern':
            self.rect(MARGIN, H - 152, W - 2 * MARGIN, 160, self.accent)
            self.text(title, MARGIN + 22, H - 186, W - 2 * MARGIN - 44, 105, 48,
                      minimum=25, bold=True, color=self.ink_on(self.accent), label='Cover title')
        else:
            self.rule(MARGIN, H - 148, 72, self.accent)
            self.text(title, MARGIN, H - 174, W - 2 * MARGIN, 118, 47, minimum=25, bold=True, label='Cover title')
        primary = next((product for product in self.products if product.code in self.photos), self.products[0])
        self.picture(primary, MARGIN, H - 335, W - 2 * MARGIN, 345)
        self.text(self.labels[3], MARGIN, 128, W - 2 * MARGIN, 27, 13, bold=True)
        self.finish_page()

    def information(self, heading, content, back=False):
        self.start_page()
        if self.logo_reader:
            self.fitted(self.logo_reader, MARGIN, H - 45, 100, 40)
        self.text(self.options.brand, MARGIN, H - 105, W - 2 * MARGIN, 40, 15,
                  minimum=11, bold=True, label='Brand')
        self.rule(MARGIN, H - 157, 72, self.accent)
        page_title = (heading if not back else self.options.title or self.labels[0])
        top = H - (275 if back else 185)
        used = self.text(page_title, MARGIN, top, W - 2 * MARGIN, 112, 39,
                         minimum=24, bold=True, label='Section title')
        body_top = top - used - 25
        self.text(content, MARGIN, body_top, W - 2 * MARGIN - 35, body_top - 70, 15,
                  minimum=10, label=heading or 'Back cover')
        self.finish_page()

    def specifications(self, product):
        labels = self.labels
        return [(label, str(value)) for label, value in zip(labels[5:14], (
            product.size, product.carton, product.weight,
            formatted(product.cbm) + (' 立方米' if self.options.language == 'zh' else ' m³')
            if product.cbm is not None else '',
            product.cartons, product.quantity, product.supplied_quantity,
            product.color, product.material)) if value is not None and value != '']

    def product_details(self, product, x, top, width, bottom, compact, columns):
        self.text(product.code, x, top, width, 24, 9, minimum=8, bold=True, label=f'{product.code} code')
        top -= 26
        used = self.text(product.name, x, top, width, 43 if compact else 58, 16 if compact else 23,
                         minimum=10, bold=True, label=f'{product.code} name')
        top -= used + 6
        if product.category:
            top -= self.text(product.category, x, top, width, 25, 9, minimum=8,
                             color=self.palette.muted, label=f'{product.code} category') + 5
        self.rule(x, top, width, self.palette.line)
        top -= 8
        values = self.specifications(product)
        col_width = (width - (columns - 1) * 12) / columns
        for offset in range(0, len(values), columns):
            heights = []
            for col, (label, value) in enumerate(values[offset:offset + columns]):
                separator = '：' if self.options.language == 'zh' else '  ·  '
                heights.append(self.text(f'{label}{separator}{value}', x + col * (col_width + 12),
                                         top, col_width, top - bottom, 8 if compact else 10,
                                         minimum=8, label=f'{product.code} {label}'))
            top -= max(heights) + 3
        if product.description:
            self.text(product.description, x, top - 5, width, top - 5 - bottom,
                      9 if compact else 11, minimum=8, color=self.palette.muted,
                      label=f'{product.code} description')

    def page_products(self, products):
        self.start_page()
        title = self.labels[3] if self.options.include_cover else self.options.brand
        self.text(title, MARGIN, H - 40, W - 2 * MARGIN, 47, 23, minimum=13, bold=True, label='Product header')
        self.rule(MARGIN, H - 86, W - 2 * MARGIN, self.accent)
        gap, top, floor = 14, H - 101, 60
        per_page = self.options.per_page
        grid_cols = 2 if per_page == 4 else 1
        grid_rows = 1 if per_page == 1 else 2
        cw = (W - 2 * MARGIN - gap * (grid_cols - 1)) / grid_cols
        ch = (top - floor - gap * (grid_rows - 1)) / grid_rows
        for index, product in enumerate(products):
            x = MARGIN + (index % grid_cols) * (cw + gap)
            y = top - (index // grid_cols) * (ch + gap)
            border = self.palette.line if self.options.theme != 'minimal' else None
            self.rect(x, y, cw, ch, self.palette.surface, border, radius=6 if self.options.theme == 'modern' else 0)
            pad = 14
            if per_page == 2:
                photo_width = cw * .42
                self.picture(product, x + pad, y - pad, photo_width, ch - 2 * pad)
                left = x + 2 * pad + photo_width
                self.product_details(product, left, y - pad, x + cw - pad - left, y - ch + pad, False, 1)
            else:
                image_height = 380 if per_page == 1 else 95
                self.picture(product, x + pad, y - pad, cw - 2 * pad, image_height)
                self.product_details(product, x + pad, y - pad - image_height - 13, cw - 2 * pad,
                                     y - ch + pad, per_page == 4, 2 if per_page == 1 else 1)
        self.finish_page(any(product.quantity is not None for product in products))

    def render(self):
        o = self.options
        if o.include_cover:
            self.cover()
        if o.about:
            self.information(self.labels[1], o.about)
        for start in range(0, len(self.products), o.per_page):
            self.page_products(self.products[start:start + o.per_page])
        if o.contact:
            self.information(self.labels[2], o.contact)
        if o.include_back:
            self.information('', o.back or o.contact, back=True)
        self.canvas.save()
        return self.stream.getvalue()


def render_pdf(products, photos, options=CatalogOptions()):
    # ReportLab TrueType fonts keep document state in shared objects.
    with FONT_LOCK:
        return Catalog(tuple(products), photos, options).render()


def write_pdf(path, contents):
    """Commit the completed PDF atomically within its destination directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.pdf', delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(contents)
        except BaseException:
            stream.close()
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
