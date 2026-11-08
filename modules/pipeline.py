import io, json, requests
import cv2, easyocr, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st

@st.cache_resource
def reader():
    # Model EasyOCR diunduh saat pemakaian pertama.
    return easyocr.Reader(["en","ja","ko","ch_sim","ch_tra"], gpu=False, verbose=False)

def translate_texts(texts, key, model):
    if not texts: return []
    prompt=("Terjemahkan teks manga berikut ke Bahasa Indonesia yang alami, ringkas, dan sesuai konteks. "
            "Pertahankan nama karakter dan urutan. Balas hanya JSON valid: "
            '{"translations":["..."]}. Jumlah hasil harus sama dengan jumlah input.')
    r=requests.post("https://api.openai.com/v1/chat/completions",
      headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
      json={"model":model,"temperature":0.2,"response_format":{"type":"json_object"},
            "messages":[{"role":"system","content":prompt},
                        {"role":"user","content":json.dumps(texts,ensure_ascii=False)}]},timeout=120)
    if r.status_code==401: raise RuntimeError("API key ditolak. Periksa key Anda.")
    if r.status_code==429: raise RuntimeError("Batas API tercapai atau billing belum aktif.")
    r.raise_for_status()
    result=json.loads(r.json()["choices"][0]["message"]["content"]).get("translations",[])
    if not isinstance(result,list) or len(result)!=len(texts): raise RuntimeError("Respons terjemahan tidak sesuai.")
    return [str(x) for x in result]

def font(size):
    for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        try: return ImageFont.truetype(p,size)
        except OSError: pass
    return ImageFont.load_default()

def wrap(draw,text,f,maxw):
    lines=[]; cur=""
    for c in text:
        test=cur+c
        if cur and draw.textbbox((0,0),test,font=f)[2]>maxw: lines.append(cur); cur=c
        else: cur=test
    if cur: lines.append(cur)
    return lines or [""]

def render(image,detections,translations):
    rgb=np.array(image.convert("RGB")); bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
    mask=np.zeros(bgr.shape[:2],np.uint8); boxes=[]
    for poly in detections:
        pts=np.asarray(poly,np.int32); cv2.fillPoly(mask,[pts],255)
        xs,ys=pts[:,0],pts[:,1]
        boxes.append((max(0,int(xs.min())),max(0,int(ys.min())),min(image.width,int(xs.max())),min(image.height,int(ys.max()))))
    if np.any(mask):
        mask=cv2.dilate(mask,np.ones((3,3),np.uint8),iterations=1)
        bgr=cv2.inpaint(bgr,mask,4,cv2.INPAINT_TELEA)
    canvas=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)); draw=ImageDraw.Draw(canvas)
    for (x1,y1,x2,y2),text in zip(boxes,translations):
        w,h=x2-x1,y2-y1
        if not text.strip() or w<3 or h<3: continue
        pad=max(2,int(min(w,h)*.06)); chosen=font(8); lines=[text]
        for size in range(max(9,int(h*.75)),7,-1):
            f=font(size); candidate=wrap(draw,text,f,max(8,w-2*pad))
            lh=max(draw.textbbox((0,0),s,font=f)[3] for s in candidate)+2
            if len(candidate)*lh<=max(8,h-2*pad): chosen,lines=f,candidate; break
        lh=max(draw.textbbox((0,0),s,font=chosen)[3] for s in lines)+2
        y=y1+max(pad,(h-len(lines)*lh)//2)
        for line in lines:
            bb=draw.textbbox((0,0),line,font=chosen); x=x1+max(pad,(w-(bb[2]-bb[0]))//2)
            draw.text((x,y),line,font=chosen,fill=(20,20,20)); y+=lh
    out=io.BytesIO(); fmt=(image.format or "PNG").upper()
    if fmt in ("JPG","JPEG"): canvas.save(out,"JPEG",quality=95,optimize=True)
    elif fmt=="WEBP": canvas.save(out,"WEBP",quality=95,method=6)
    else: canvas.save(out,"PNG",optimize=True)
    return out.getvalue()

def translate_image(raw_bytes,api_key,model,confidence_threshold=.2,max_side=2000):
    try:
        image=ImageOps.exif_transpose(Image.open(io.BytesIO(raw_bytes))); image.load()
    except Exception as e: raise ValueError(f"Gambar tidak valid: {e}")
    if image.width*image.height>40_000_000: raise ValueError("Resolusi terlalu besar (maksimal 40 megapiksel).")
    work=image.copy(); work.thumbnail((max_side,max_side))
    found=reader().readtext(np.array(work),detail=1,paragraph=False)
    sx,sy=image.width/work.width,image.height/work.height
    detections=[]; texts=[]
    for poly,text,conf in found:
        text=str(text).strip()
        if not text or float(conf)<confidence_threshold: continue
        detections.append([[int(x*sx),int(y*sy)] for x,y in poly]); texts.append(text)
    if not texts:
        out=io.BytesIO(); image.save(out,format=image.format or "PNG"); return out.getvalue(),0
    translated=translate_texts(texts,api_key,model)
    return render(image,detections,translated),len(texts)
