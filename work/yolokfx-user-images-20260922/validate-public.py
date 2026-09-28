#!/usr/bin/env python3
import hashlib,io,json,re,ssl,urllib.error,urllib.request
from html.parser import HTMLParser
from pathlib import Path
from PIL import Image

class TextParser(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self,data): self.parts.append(data)

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 Zeus-QA/1.0','Cache-Control':'no-cache'})
    try:
        with urllib.request.urlopen(req,timeout=30,context=ssl.create_default_context()) as r:
            return r.status,r.geturl(),r.read(),dict(r.headers.items())
    except urllib.error.HTTPError as e:
        return e.code,e.geturl(),e.read(),dict(e.headers.items())

def text(html):
    p=TextParser(); p.feed(html); return ' '.join(' '.join(p.parts).split())

base='https://yolokfx.com/quiz/us/'
image_urls=[f'https://yolokfx.com/wp-content/uploads/2026/09/yolokfx-v3-{cat}-1552164476814360629.webp' for cat in ['women','men','home','shoes','electronics','others']]
expected_labels=['Women','Men','Home','Shoes','Electronics','Others']
routes=[]
for layout in (1,2,3):
    for manager in range(1,7):
        if layout==1 and manager==4: continue
        slug=f'sh{layout}-g{manager:03d}'
        url=base+slug+'/'
        status,final,body,headers=get(url)
        assert status==200,(slug,status)
        html=body.decode('utf-8')
        visible=text(html)
        assert final==url,(slug,final)
        assert 'MGS Direct Quiz static; plugin=1.2.0' in html,slug
        if layout==3:
            assert 'Would you like to receive for free?' in visible,slug
            assert all(label in visible for label in expected_labels),slug
            assert not any(old in visible for old in ['Kids','Phones','Accessories']),slug
            assert html.count('class="mgs-dq-category"')==6,slug
            assert html.count('data-mgs-dq-cta')==7,slug
            assert all(html.count(img)==1 for img in image_urls),slug
        else:
            assert 'Get Free Products Delivered to Your Home' in visible,slug
            assert 'Would you like to get free products?' in visible,slug
            assert html.count('data-mgs-dq-cta')==2,slug
            assert not any(img in html for img in image_urls),slug
        routes.append({'slug':slug,'status':status,'final_url':final,'layout':layout,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'cache_control':headers.get('Cache-Control','')})
inactive_status,inactive_final,body,headers=get(base+'sh1-g004/')
assert inactive_status==404,inactive_status
images=[]
for url in image_urls:
    status,final,body,headers=get(url)
    assert status==200 and final==url,(url,status,final)
    assert body[:4]==b'RIFF' and body[8:12]==b'WEBP',url
    assert len(body)<=25000,(url,len(body))
    with Image.open(io.BytesIO(body)) as im:
        assert im.format=='WEBP',(url,im.format)
        width,height=im.size
    assert (width,height)==(400,400),(url,width,height)
    images.append({'url':url,'status':status,'width':width,'height':height,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'content_type':headers.get('Content-Type','')})
summary={'status':'PASS','active_routes':len(routes),'v3_routes':sum(r['layout']==3 for r in routes),'inactive_sh1_g004':inactive_status,'labels':expected_labels,'images':images,'routes':routes}
out=Path('/root/mgs-agent/work/yolokfx-user-images-20260922/public-validation.json')
out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','active_routes':len(routes),'v3_routes':6,'images':len(images),'inactive_sh1_g004':404,'path':str(out)},separators=(',',':')))
