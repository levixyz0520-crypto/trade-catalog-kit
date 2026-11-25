"""Match and prepare local or uploaded photos without changing product geometry."""

import io
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath, PureWindowsPath

from PIL import Image, ImageCms, ImageColor, ImageOps

from .data import Diagnostic

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
FORMATS = ('JPEG', 'PNG', 'WEBP')
MAX_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 24_000_000
MAX_UPLOAD_BYTES = 120 * 1024 * 1024


@dataclass(frozen=True)
class ImageOptions:
    crop: bool = False
    white: bool = True
    quality: int = 86
    remove_background: bool = False


def safe_relative(value):
    path = PurePosixPath(value.replace('\\', '/'))
    if (not path.name or path.is_absolute() or PureWindowsPath(value).drive
            or '..' in path.parts or re.search(r'[:\x00-\x1f]', value)):
        raise ValueError('Image must be a relative file inside the image directory.')
    return path


class ImageLibrary:
    def __init__(self, directory=None, uploads=()):
        self.directory = Path(directory).resolve(strict=True) if directory is not None else None
        self.by_name, self.by_code = {}, {}
        if self.directory is not None:
            if not self.directory.is_dir():
                raise ValueError('Select an image directory.')
            for path in sorted(self.directory.iterdir()):
                if path.is_file() and path.suffix.lower() in EXTENSIONS:
                    try:
                        target = path.resolve(strict=True)
                    except OSError:
                        continue
                    if target.is_relative_to(self.directory):
                        self.add(path.name, target)
        total = 0
        for name, contents in uploads:
            path = safe_relative(name)
            if len(path.parts) != 1 or path.suffix.lower() not in EXTENSIONS:
                raise ValueError('Upload JPEG, PNG or WebP files with plain filenames.')
            total += len(contents)
            if len(contents) > MAX_BYTES or total > MAX_UPLOAD_BYTES:
                raise ValueError('Upload up to 12 MiB per image and 120 MiB combined.')
            self.add(path.name, contents)

    def add(self, name, source):
        self.by_name.setdefault(name.casefold(), []).append(source)
        self.by_code.setdefault(Path(name).stem.casefold(), []).append(source)

    def match(self, product):
        if product.image:
            relative = safe_relative(product.image)
            if self.directory is not None:
                target = self.directory.joinpath(*relative.parts).resolve()
                if not target.is_relative_to(self.directory):
                    raise ValueError('Image must be inside the image directory.')
                if target.is_file():
                    return target
            candidates = self.by_name.get(relative.name.casefold(), []) if len(relative.parts) == 1 else []
        else:
            candidates = self.by_code.get(product.code.casefold(), [])
        if len(candidates) > 1:
            raise ValueError('Multiple images match. Set an unambiguous Image filename.')
        return candidates[0] if candidates else None


def open_image(source):
    if isinstance(source, Path):
        with source.open('rb') as stream:
            source = stream.read(MAX_BYTES + 1)
    if len(source) > MAX_BYTES:
        raise ValueError('Image exceeds 12 MiB.')
    try:
        image = Image.open(io.BytesIO(source), formats=FORMATS)
        if image.width * image.height > MAX_PIXELS:
            image.close()
            raise ValueError('Image exceeds 24 megapixels.')
        if getattr(image, 'n_frames', 1) != 1:
            image.close()
            raise ValueError('Use a single-frame image.')
        return image
    except (OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValueError('Image is not a readable JPEG, PNG or WebP file.') from exc


def inspect(source):
    with open_image(source) as image:
        width, height = image.size
        try:
            image.verify()
        except (OSError, SyntaxError) as exc:
            raise ValueError('Image data is damaged.') from exc
    return width, height


def match_images(products, library):
    matched, diagnostics = {}, []
    for product in products:
        try:
            source = library.match(product)
            if source is None:
                diagnostics.append(Diagnostic(product.row, f'{product.code}: no matching image.', 'warning'))
                continue
            width, height = inspect(source)
            matched[product.code] = source
            if min(width, height) < 600:
                diagnostics.append(Diagnostic(product.row, f'{product.code}: low-resolution image ({width} × {height}).', 'warning'))
        except (OSError, RuntimeError, ValueError) as exc:
            diagnostics.append(Diagnostic(product.row, f'{product.code}: {exc}'))
    return matched, tuple(diagnostics)


@lru_cache(maxsize=1)
def background_session():
    try:
        from rembg import new_session
    except ImportError as exc:
        raise ValueError('Install the optional AI extra to remove backgrounds.') from exc
    return new_session('u2netp', providers=['CPUExecutionProvider'])


def prepare(source, width, height, options=ImageOptions(), surface='#FFFFFF', max_side=1600):
    try:
        with open_image(source) as opened:
            oriented = ImageOps.exif_transpose(opened)
            photo = oriented.convert('RGBA')
            if profile := oriented.info.get('icc_profile'):
                try:
                    rgb = ImageCms.profileToProfile(oriented, io.BytesIO(profile),
                                                    ImageCms.createProfile('sRGB'), outputMode='RGB')
                    rgb.putalpha(photo.getchannel('A'))
                    photo = rgb
                except (OSError, ImageCms.PyCMSError):
                    pass  # An unreadable profile cannot be applied.
    except OSError as exc:
        raise ValueError('Image pixels could not be decoded.') from exc
    photo.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    if options.remove_background:
        try:
            session = background_session()
            from rembg import remove
            photo = remove(photo, session=session).convert('RGBA')
        except Exception as exc:
            raise ValueError(f'AI background removal failed: {exc}') from exc
    if options.crop:
        # Crop to the target aspect ratio without enlarging the original.
        scale = min(photo.width / width, photo.height / height)
        size = (max(1, round(width * scale)), max(1, round(height * scale)))
        photo = ImageOps.fit(photo, size, Image.Resampling.LANCZOS)
    background = Image.new('RGBA', photo.size, ImageColor.getrgb('#FFFFFF' if options.white else surface))
    background.alpha_composite(photo)
    stream = io.BytesIO()
    background.convert('RGB').save(stream, 'JPEG', quality=options.quality, optimize=True)
    stream.seek(0)
    return stream, photo.width, photo.height
