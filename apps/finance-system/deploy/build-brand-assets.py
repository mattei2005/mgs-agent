"""Rodolfo 1546624782785716305: derive logo/favicon from original pixels only."""
from PIL import Image,ImageChops
import pathlib,json,hashlib
R=pathlib.Path(__file__).resolve().parents[1];source=pathlib.Path('/root/.hermes/profiles/zeus/cache/images/img_84dc5ce056e9.webp');im=Image.open(source).convert('RGB')
# Rodolfo 1546703031033405501 supersedes tight crop: keep the complete square.
assert im.width==im.height;box=(0,0,im.width,im.height);logo=im.copy();logo.save(R/'public/mgs-logo.png')
canvas=Image.new('RGB',(256,256),'black');fit=logo.copy();fit.thumbnail((244,244),Image.Resampling.LANCZOS);canvas.paste(fit,((256-fit.width)//2,(256-fit.height)//2));canvas.save(R/'public/favicon.ico',sizes=[(16,16),(32,32),(48,48),(64,64)])
for name,size in [('favicon-32.png',32),('apple-touch-icon.png',180)]:canvas.resize((size,size),Image.Resampling.LANCZOS).save(R/'public'/name)
assert Image.open(R/'public/favicon.ico').ico.sizes()=={(16,16),(32,32),(48,48),(64,64)}
d={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'original_size':im.size,'crop_box':box,'logo_size':logo.size,'original_pixels_preserved':True,'no_redesign':True,'files':{n:hashlib.sha256((R/'public'/n).read_bytes()).hexdigest() for n in ['mgs-logo.png','favicon.ico','favicon-32.png','apple-touch-icon.png']}}
(R/'private/origin-1546618148571058266/brand-assets.json').write_text(json.dumps(d,indent=2));print(json.dumps(d))
