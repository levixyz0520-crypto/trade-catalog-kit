"""Command-line entry point for checking spreadsheets and generating catalogs."""

import argparse
import json
import sys
from pathlib import Path

from .data import FIELDS, LABELS, key, read_table, validate
from .images import ImageLibrary, ImageOptions, match_images
from .pdf import LABELS as PDF_LABELS
from .pdf import THEMES, CatalogOptions, render_pdf, write_pdf


def read_mapping(path):
    if path is None:
        return {}
    contents = path.read_bytes()
    if len(contents) > 64 * 1024:
        raise ValueError('Mapping JSON must be at most 64 KiB.')
    raw = json.loads(contents)
    if not isinstance(raw, dict):
        raise ValueError('Mapping JSON must be an object of catalog fields and source headers.')
    fields = {key(field): field for field in FIELDS}
    fields.update({key(label): field for field, label in LABELS.items()})
    result = {}
    for field, header in raw.items():
        mapped = fields.get(key(field))
        if not mapped or mapped in result or not (header is None or isinstance(header, str)):
            raise ValueError(f'Invalid mapping for {field!r}.')
        result[mapped] = header
    return result


def parser_for(legacy):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spreadsheet', type=Path, help='UTF-8 CSV or XLSX')
    parser.add_argument('--images', type=Path, required=legacy, help='local image directory')
    parser.add_argument('--out', type=Path, default=Path('catalog.pdf'))
    parser.add_argument('--check', action='store_true', help='validate data and images without generating a PDF')
    parser.add_argument('--mapping', type=Path, help='JSON from catalog field names to input headers')
    parser.add_argument('--container-volume', default='76', help='base available container volume in m³')
    parser.add_argument('--utilization', default='0.85', help='volume utilization, fraction from 0 to 1')
    parser.add_argument('--brand', default='PRODUCT COLLECTION')
    parser.add_argument('--title', default='')
    parser.add_argument('--about', default='')
    parser.add_argument('--contact', default='')
    parser.add_argument('--back', default='')
    parser.add_argument('--logo', type=Path)
    parser.add_argument('--font', type=Path, help='custom TrueType .ttf font, embedded in PDF')
    parser.add_argument('--language', choices=PDF_LABELS, default='en')
    parser.add_argument('--theme', choices=THEMES, default='editorial')
    parser.add_argument('--accent', default='', help='theme color in #RRGGBB form')
    parser.add_argument('--per-page', type=int, choices=(1, 2, 4), default=2)
    parser.add_argument('--no-cover', action='store_true')
    parser.add_argument('--no-back', action='store_true')
    parser.add_argument('--crop', action='store_true', help='center-crop photos to fill their slots')
    parser.add_argument('--theme-background', action='store_true', help='composite transparency over the theme surface')
    parser.add_argument('--jpeg-quality', type=int, choices=range(60, 96), default=86, metavar='60–95')
    parser.add_argument('--remove-background', action='store_true', help='use optional offline rembg processing')
    parser.add_argument('--strict-images', action='store_true', help='treat missing product images as errors')
    return parser


def main(argv=None, *, legacy=False):
    args = parser_for(legacy).parse_args(argv)
    try:
        data = validate(read_table(args.spreadsheet), read_mapping(args.mapping), args.container_volume, args.utilization)
        library = ImageLibrary(args.images)
        matched, image_diagnostics = match_images(data.products, library)
        diagnostics = data.diagnostics + image_diagnostics
        for item in diagnostics:
            print(f'{item.level.title()}: {item}', file=sys.stderr)
        if (not data.valid or any(item.level == 'error' for item in image_diagnostics)
                or ((legacy or args.strict_images) and len(matched) != len(data.products))):
            return 1
        if not args.check:
            inputs = [args.spreadsheet, args.mapping, args.font, args.logo,
                      *(value for value in matched.values() if isinstance(value, Path))]
            if args.out.suffix.lower() != '.pdf' or args.out.resolve() in {
                path.resolve() for path in inputs if path is not None
            }:
                raise ValueError('Output must be a separate .pdf file.')
            font = None
            if args.font:
                with args.font.open('rb') as stream:
                    font = stream.read(12 * 1024 * 1024 + 1)
            images = ImageOptions(args.crop, not args.theme_background, args.jpeg_quality, args.remove_background)
            options = CatalogOptions(brand=args.brand, title=args.title, about=args.about, contact=args.contact,
                                     back=args.back, theme=args.theme, accent=args.accent, per_page=args.per_page,
                                     language=args.language, font=font, logo=args.logo, images=images,
                                     include_cover=not (legacy or args.no_cover),
                                     include_back=not (legacy or args.no_back))
            write_pdf(args.out, render_pdf(data.products, matched, options))
        print(f'Validated {len(data.products)} product(s)' + ('' if args.check else f'; wrote {args.out}'))
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
