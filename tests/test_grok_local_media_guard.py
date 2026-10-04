"""Native wrapper functions; bootstrap omitted for offline unit import only."""
import ast
import io
import os
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image

source=Path('/root/mgs-agent/scripts/mgs-grok-generate.py')
tree=ast.parse(source.read_text())
tree.body=[n for n in tree.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='_bootstrap_active_hermes')]
mod=types.ModuleType('grok_guard')
mod.__file__=str(source)
exec(compile(tree,str(source),'exec'),mod.__dict__)

class MediaGuardTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.mkdtemp(prefix='grok-media-guard-',dir=os.environ['TMPDIR'])
        self.root=Path(self.directory)/'media';self.root.mkdir()
        self.image=self.root/'reference.png';Image.new('RGB',(2,2)).save(self.image)
        self.outside=Path(self.directory)/'outside.png';Image.new('RGB',(2,2)).save(self.outside)
    def roots(self):
        return patch.object(mod,'_media_roots',return_value=[self.root])
    def test_non_media_outside_is_rejected(self):
        with self.assertRaises((ValueError,RuntimeError)):
            mod._image_ref(str(self.outside))
    def test_missing_file_rejected(self):
        with self.assertRaises((ValueError,RuntimeError)):
            mod._image_ref(str(self.root/'missing.png'))
    def test_text_disguised_as_image_rejected(self):
        fake=self.root/'fake.png';fake.write_text('synthetic non-image only')
        with self.roots(), self.assertRaises((ValueError,RuntimeError)):
            mod._image_ref(str(fake))
    def test_allowed_valid_image_with_verified_roundtrip(self):
        with self.roots():
            ref=mod._image_ref(str(self.image))
        self.assertTrue(ref.startswith('data:image/png;base64,'))
    def test_symlink_escape_rejected(self):
        link=self.root/'link.png';link.symlink_to(self.outside)
        with self.roots(),self.assertRaises((ValueError,RuntimeError)):
            mod._image_ref(str(link))
    def test_remote_reference_is_preserved(self):
        self.assertEqual(mod._image_ref('https://example.com/reference.png'),'https://example.com/reference.png')
    def test_invalid_file_stops_before_credentials(self):
        args=SimpleNamespace(profile='ares',model='grok-imagine-video',prompt='synthetic',duration=2,aspect_ratio='1:1',resolution='720p',image_url=str(self.outside),reference_image_url=[])
        with patch.object(mod,'_set_profile'),patch.object(mod,'_creds',side_effect=AssertionError('credential access forbidden')) as creds:
            with self.assertRaises((ValueError,RuntimeError)):
                mod.video(args)
            creds.assert_not_called()
    def test_reference_list_is_checked_before_credentials(self):
        args=SimpleNamespace(profile='ares',model='grok-imagine-video',prompt='synthetic',duration=2,aspect_ratio='1:1',resolution='720p',image_url=None,reference_image_url=[str(self.outside)])
        with patch.object(mod,'_set_profile'),patch.object(mod,'_creds',side_effect=AssertionError('credential access forbidden')) as creds:
            with self.assertRaises((ValueError,RuntimeError)):
                mod.video(args)
            creds.assert_not_called()

if __name__=='__main__':unittest.main()
