import csv
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from catalog import read_products, build_pdf, dimensions, main

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.addCleanup(self.temp.cleanup)
        Image.new('RGB',(100,70),'white').save(self.root/'photo.png')
        self.csv=self.root/'products.csv'
    def write(self, rows):
        with self.csv.open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f); w.writerow(['sku','name','size_cm','image','carton_cm','gross_kg','cbm']); w.writerows(rows)
    def row(self, sku='A-01', image='photo.png', size='100 x 50 x 20', carton='100 x 50 x 20', weight='5',cbm=''):
        return [sku,'Sample',size,image,carton,weight,cbm]
    def test_cbm_and_pdf(self):
        self.write([self.row(), self.row('B-02'),self.row('C-03')]); p=read_products(self.csv,self.root); self.assertEqual(p[0].cbm,'0.100000'); out=self.root/'out.pdf';build_pdf(p,out);self.assertTrue(out.read_bytes().startswith(b'%PDF-'))
    def test_duplicate(self):
        self.write([self.row(),self.row('a-01')]);self.assertRaisesRegex(ValueError,'duplicate SKU',read_products,self.csv,self.root)
    def test_missing_image(self):
        self.write([self.row(image='missing.png')]);self.assertRaisesRegex(ValueError,'existing file',read_products,self.csv,self.root)
    def test_outside_image(self):
        self.write([self.row(image='../outside.png')]);self.assertRaisesRegex(ValueError,'inside image directory',read_products,self.csv,self.root)
    def test_invalid_dimensions(self):
        for val in ['0 x 2 x 3','nan x 2 x 3','2 x 3','-1 x 2 x 3']:
            with self.subTest(val=val): self.assertRaises(ValueError,dimensions,val)
    def test_invalid_weight(self):
        self.write([self.row(weight='inf')]);self.assertRaisesRegex(ValueError,'finite positive',read_products,self.csv,self.root)
    def test_supplied_cbm(self):
        self.write([self.row(cbm='0.123')]);self.assertEqual(read_products(self.csv,self.root)[0].cbm,'0.123')
    def test_check(self):
        self.write([self.row()]); self.assertEqual(main([str(self.csv),'--images',str(self.root),'--check']),0)
    def test_empty(self):
        self.write([]);self.assertRaisesRegex(ValueError,'no product',read_products,self.csv,self.root)
    def test_invalid_image(self):
        (self.root/'bad.png').write_bytes(b'not an image');self.write([self.row(image='bad.png')]);self.assertRaises(ValueError,read_products,self.csv,self.root)

if __name__=='__main__': unittest.main()
