import json, os
from PIL import Image, ImageDraw
manifest="/root/mgs-agent/data/ares/creative-ops/executions/20260830T213916Z-nicolas-cc-us-en/timelines/20260830T214024Z/video-frame-sample-manifest.json"
out="/root/mgs-agent/data/ares/creative-ops/executions/20260830T213916Z-nicolas-cc-us-en/review-mosaics"
os.makedirs(out, exist_ok=True)
data=json.load(open(manifest))
index=[]
for batch_no,start in enumerate(range(0,len(data["items"]),6),1):
    items=data["items"][start:start+6]
    ims=[]
    for i,it in enumerate(items,start+1):
        im=Image.open(it["sheet"]).convert("RGB")
        band=Image.new("RGB",(im.width,42),"#111827")
        d=ImageDraw.Draw(band)
        d.text((12,10),f"ITEM {i:02d} | {it['original_filename']}",fill="white")
        canvas=Image.new("RGB",(im.width,band.height+im.height+8),"white")
        canvas.paste(band,(0,0)); canvas.paste(im,(0,band.height))
        ims.append(canvas)
    w=max(x.width for x in ims); h=sum(x.height for x in ims)
    mos=Image.new("RGB",(w,h),"white")
    y=0
    for im in ims:
        mos.paste(im,(0,y)); y+=im.height
    path=os.path.join(out,f"batch-{batch_no:02d}-items-{start+1:02d}-{start+len(items):02d}.jpg")
    mos.save(path,quality=92,optimize=True)
    index.append({"batch":batch_no,"path":path,"items":[{"index":j,"filename":x["original_filename"],"sheet":x["sheet"]} for j,x in zip(range(start+1,start+1+len(items)),items)]})
json.dump(index,open(os.path.join(out,"index.json"),"w"),indent=2)
print(json.dumps({"mosaics":len(index),"items":len(data["items"]),"out":out,"paths":[x["path"] for x in index]},indent=2))
