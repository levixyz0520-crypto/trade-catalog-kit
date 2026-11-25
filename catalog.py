"""Build a printable product catalogue from a CSV file and local product images."""
import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

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
    parts = re.split(r'\s*[xX×*]\s*', value.strip())
    if len(parts) != 3:
        raise ValueError('expected three dimensions, e.g. 80 x 40 x 75')
    nums = [float(x) for x in parts]
    if not all(math.isfinite(x) and x > 0 for x in nums):
        raise ValueError('dimensions must be finite and positive')
    return nums


def positive(value):
    n = float(value)
    if not math.isfinite(n) or n <= 0:
        raise ValueError('expected a finite positive number')
    return n


def read_products(csv_path, image_dir):
    """Return valid products, or raise a single error containing row diagnostics."""
    products, errors, seen = [], [], set()
    image_dir = Path(image_dir).resolve()
    with open(csv_path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError('duplicate column headers')
        missing = set(REQUIRED) - set(headers)
        if missing:
            raise ValueError('missing columns: ' + ', '.join(sorted(missing)))
        for i, row in enumerate(reader, 2):
            if None in row:
                errors.append(f'row {i}: extra CSV fields'); continue
            vals = {k: (row.get(k) or '').strip() for k in REQUIRED + OPTIONAL}
            if not any(vals.values()):
                continue
            try:
                if not all(vals[k] for k in REQUIRED):
                    raise ValueError('sku, name, size_cm and image are required')
                if vals['sku'].casefold() in seen:
                    raise ValueError('duplicate SKU: ' + vals['sku'])
                dimensions(vals['size_cm'])
                if vals['carton_cm']:
                    d = dimensions(vals['carton_cm'])
                    if not vals['cbm']:
                        vals['cbm'] = f'{math.prod(d)/1e6:.6f}'
                for k in ('gross_kg', 'cbm'):
                    if vals[k]: positive(vals[k])
                img = (image_dir / vals['image']).resolve()
                if not img.is_relative_to(image_dir) or not img.is_file():
                    raise ValueError('image must be an existing file inside image directory')
                with Image.open(img) as im:
                    if im.format not in ('JPEG', 'PNG', 'WEBP'):
                        raise ValueError('image format must be JPEG, PNG or WEBP')
                    if im.width * im.height > 40_000_000:
                        raise ValueError('image exceeds 40 megapixels')
                    im.verify()
                for k, limit in {'sku':40,'name':100,'size_cm':60,'carton_cm':60,'gross_kg':20,'cbm':20,'colors':120,'notes':180}.items():
                    if len(vals[k]) > limit:
                        raise ValueError(f'{k} exceeds {limit} characters')
                vals['image'] = img
                products.append(Product(**vals)); seen.add(vals['sku'].casefold())
            except (ValueError, OSError, Image.DecompressionBombError) as e:
                errors.append(f'row {i}: {e}')
    if errors:
        raise ValueError('\n'.join(errors))
    if not products:
        raise ValueError('no product rows found')
    return products


def paragraph(c, text, x, top, width, font_size, color, max_height, bold=False):
    # Fit within the allotted height; never silently cut off text.
    for size in range(font_size, 6, -1):
        style = ParagraphStyle('field', fontName='Helvetica-Bold' if bold else 'Helvetica', fontSize=size, leading=size*1.22, textColor=color, splitLongWords=True)
        p = Paragraph(escape(text), style)
        _, h = p.wrap(width, max_height)
        if h <= max_height:
            p.drawOn(c, x, top-h)
            return h
    raise ValueError('text does not fit catalogue layout: ' + text[:50])


def build_pdf(products, out, brand='PRODUCT COLLECTION'):
    """Generate two cards per A4 page. Write atomically only after success."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    with tempfile.NamedTemporaryFile(dir=out.parent, suffix='.pdf', delete=False) as f:
        temp = Path(f.name)
    try:
        c = canvas.Canvas(str(temp), pagesize=A4)
        c.setTitle(brand + ' | Product Catalog')
        W,H = A4
        dark = colors.HexColor('#202C3B'); muted = colors.HexColor('#516174'); line = colors.HexColor('#DCE2E9')
        margin = 36; gap = 18; cardw = (W-2*margin-gap)/2; bottom=60; top=H-116
        count = math.ceil(len(products)/2)
        for page in range(count):
            c.setFillColor(dark)
            paragraph(c,brand,margin,H-42,W-2*margin,23,dark,34,True)
            c.setFont('Helvetica',10); c.setFillColor(muted); c.drawString(margin,H-88,'PRODUCT CATALOG  /  SPECIFICATIONS')
            c.setStrokeColor(line); c.line(margin,H-100,W-margin,H-100)
            for j,p in enumerate(products[page*2:page*2+2]):
                x=margin+j*(cardw+gap); inner=x+14; iw=cardw-28
                c.setStrokeColor(line); c.roundRect(x,bottom,cardw,top-bottom,9,stroke=1,fill=0)
                paragraph(c,p.sku,inner,top-18,iw,18,dark,42,True)
                paragraph(c,p.name,inner,top-64,iw,13,muted,48)
                # EXIF orientation, alpha composite, contain without cropping.
                with Image.open(p.image) as source:
                    im=ImageOps.exif_transpose(source).convert('RGBA')
                    im.thumbnail((1400,1400))
                    bg=Image.new('RGBA',im.size,'white'); bg.alpha_composite(im); im=bg.convert('RGB')
                    imw,imh=im.size; boxh=230; ratio=min(iw/imw,boxh/imh); dw,dh=imw*ratio,imh*ratio
                    c.drawImage(ImageReader(im),inner+(iw-dw)/2,top-118-boxh+(boxh-dh)/2,dw,dh)
                y=top-366
                for label,value in [('Product size (cm)',p.size_cm),('Carton size (cm)',p.carton_cm),('Gross weight (kg)',p.gross_kg),('Volume (m3)',p.cbm),('Colors',p.colors),('Notes',p.notes)]:
                    if not value: continue
                    c.setStrokeColor(line); c.line(inner,y,inner+iw,y)
                    y-=8
                    h=paragraph(c,label,inner,y,iw,9,muted,14); y-=h+3
                    h=paragraph(c,value,inner,y,iw,11,dark,42); y-=h+10
                    if y<bottom+6: raise ValueError(f'{p.sku}: specifications exceed available space')
            c.setFont('Helvetica',9); c.setFillColor(muted); c.drawString(margin,35,'Specifications supplied by catalog author'); c.drawRightString(W-margin,35,f'{page+1:02d} / {count:02d}'); c.showPage()
        c.save(); temp.replace(out)
    finally:
        temp.unlink(missing_ok=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path); parser.add_argument('--images',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=Path('catalog.pdf')); parser.add_argument('--brand',default='PRODUCT COLLECTION'); parser.add_argument('--check',action='store_true',help='validate without generating PDF')
    args=parser.parse_args(argv)
    try:
        products=read_products(args.csv,args.images)
        if not args.check:
            if args.out.suffix.lower() != '.pdf' or args.out.resolve() in {args.csv.resolve(), *(p.image for p in products)}:
                raise ValueError('output must be a separate .pdf file')
            build_pdf(products,args.out,args.brand)
        print(f'Validated {len(products)} product(s)' + ('' if args.check else f'; wrote {args.out}'))
        return 0
    except (ValueError,OSError,csv.Error) as exc:
        print(f'Error: {exc}',file=sys.stderr); return 1

if __name__=='__main__':
    raise SystemExit(main())
