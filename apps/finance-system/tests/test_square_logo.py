"""Rodolfo 1546703031033405501: original square, never tight-cropped."""
import unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/root/.hermes/profiles/zeus/cache/images/img_84dc5ce056e9.webp')
class SquareLogo(unittest.TestCase):
 def test_complete_original_pixels(self):
  src=Image.open(SOURCE).convert('RGB');live=Image.open(ROOT/'public/mgs-logo.png').convert('RGB')
  self.assertEqual(live.size,src.size)
  self.assertEqual(live.width,live.height)
  self.assertEqual(live.tobytes(),src.tobytes())
 def test_display_without_cropping(self):
  for name in ['login.css','navigation.css','refinements.css']:
   text=(ROOT/'public'/name).read_text();self.assertIn('aspect-ratio:1/1',text,name);self.assertIn('object-fit:contain',text,name)
 def test_cache_version(self):
  for name in ['login.html','navigation.js']:
   self.assertIn('/mgs-logo.png?v=1546703031033405501',(ROOT/'public'/name).read_text())
if __name__=='__main__':unittest.main()
