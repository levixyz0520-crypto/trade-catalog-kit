from dataclasses import replace
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from trade_catalog_kit.images import ImageLibrary, ImageOptions, match_images, prepare, safe_relative


def photo(width=640, height=720):
    stream = BytesIO()
    im = Image.new('RGBA', (width, height))
    im.paste('#357737', (4, 4, width - 4, height - 4))
    im.save(stream, format='PNG')
    return stream.getvalue()


@pytest.mark.parametrize('name', ['../away.png', 'abc/../../away.png', '/abc.png', r'..\abc.png',
                                  r'C:\Photos\abc.png', r'\\server\dir\abc.png', 'file:stream.png'])
def test_path_is_confined_on_every_platform(name):
    with pytest.raises(ValueError, match='inside'):
        safe_relative(name)


def test_match_exact_names_and_casefolded_codes(tmp_path):
    (tmp_path / 'Sku-A.PNG').write_bytes(photo())
    (tmp_path / 'small.png').write_bytes(photo(125, 125))
    products = [SimpleNamespace(code='sku-a', row=2, image=''), SimpleNamespace(code='b', row=3, image='small.png'),
                SimpleNamespace(code='c', row=4, image='nonexistent.webp')]
    images, diagnostics = match_images(products, ImageLibrary(tmp_path))
    assert set(images) == {'sku-a', 'b'}
    assert [d.level for d in diagnostics] == ['warning', 'warning']
    assert 'low-resolution' in diagnostics[0].message and 'no matching image' in diagnostics[1].message


def test_upload_matching_ambiguity_and_invalid_images():
    original = photo()
    library = ImageLibrary(uploads=[('readable.png', original), ('readable.webp', original), ('bad.jpeg', b'broken')])
    products = [SimpleNamespace(code='readable', row=2, image=''), SimpleNamespace(code='bad', row=3, image='')]
    images, diagnostics = match_images(products, library)
    assert not images
    assert [d.level for d in diagnostics] == ['error', 'error']
    assert 'Multiple' in diagnostics[0].message and 'readable JPEG' in diagnostics[1].message
    pictures, result = match_images([SimpleNamespace(code='readable', row=2, image='Readable.PNG')], library)
    assert pictures == {'readable': original} and not result


def test_rejects_resolved_symlink_outside_image_root(tmp_path):
    image_root = tmp_path / 'images'
    image_root.mkdir()
    outside = tmp_path / 'outside.png'
    outside.write_bytes(photo())
    try:
        (image_root / 'escape.png').symlink_to(outside)
    except OSError:
        pytest.skip('Creating symlinks requires extra privileges on this Windows runner.')
    images, diagnostics = match_images([SimpleNamespace(code='x', row=2, image='escape.png')], ImageLibrary(image_root))
    assert not images and 'inside' in diagnostics[0].message


def test_contain_crop_compress_and_white_alpha_background():
    source = photo(880, 640)
    opts = ImageOptions(quality=79)
    stream, width, height = prepare(source, 100, 100, opts, max_side=440)
    assert (width, height) == (440, 320)
    with Image.open(stream) as rendered:
        assert rendered.format == 'JPEG'
        assert min(rendered.getpixel((0, 0))) > 220
    _, width, height = prepare(source, 100, 100, replace(opts, crop=True), max_side=440)
    assert (width, height) == (320, 320)
