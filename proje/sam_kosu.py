# -*- coding: utf-8 -*-
"""D1-B: MS ayak izini kutu-yonlendirmesi olarak verip SAM ile cati maskesi cikarir.
Cikti: her bina icin SAM alani, ayak izi alani, azimut, mahya uzunlugu."""
import numpy as np, json, time, math
from PIL import Image
from shapely.geometry import shape, Polygon
from shapely.ops import transform
from pyproj import Transformer
from sam_lib import MobileSAM, lonlat2px, px2lonlat, MPP

T = 1024; OVER = 256
to_utm = Transformer.from_crs('EPSG:4326','EPSG:32635',always_xy=True).transform

def azimut_ve_uzunluk(mask):
    """Maskenin minimum donmus dikdortgeninden mahya yonu + kenarlar."""
    import cv2
    c,_ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not c: return None
    big = max(c, key=cv2.contourArea)
    (cx,cy),(w,h),ang = cv2.minAreaRect(big)
    uzun, kisa = max(w,h), min(w,h)
    # uzun kenarin yonu = mahya; catinin bakis yonu buna dik
    if h > w: ang += 90.0
    mahya = ang % 180.0                    # 0=dogu-bati, 90=kuzey-guney
    bakis = (mahya + 90.0) % 180.0         # cati yuzeyinin baktigi eksen
    # guneye en yakin azimut (0=kuzey, 180=guney)
    a1, a2 = bakis, (bakis+180)%360
    az = min((a1,a2), key=lambda a: min(abs(a-180), 360-abs(a-180)))
    return dict(azimut=az, uzun=uzun*MPP, kisa=kisa*MPP,
                doluluk=float(cv2.contourArea(big)/max(uzun*kisa,1)))

def main():
    m = MobileSAM()
    im = Image.open('cache/evka5_mozaik.jpg').convert('RGB')
    W,H = im.size
    fc = json.load(open('cache/evka5_ms_binalar.geojson',encoding='utf-8'))

    binalar=[]
    for i,f in enumerate(fc['features']):
        ring=f['geometry']['coordinates'][0]
        px=[lonlat2px(p[0],p[1]) for p in ring]
        X=[p[0] for p in px]; Y=[p[1] for p in px]
        binalar.append(dict(i=i, box=(min(X),min(Y),max(X),max(Y)),
                            ayak=transform(to_utm, shape(f['geometry'])).area,
                            ring=ring))

    step = T-OVER
    tiles=[(x,y) for y in range(0,max(H-T,0)+step,step) for x in range(0,max(W-T,0)+step,step)]
    tiles=[(min(x,W-T),min(y,H-T)) for x,y in tiles]
    print(f'{len(binalar)} bina, {len(tiles)} kare')

    atanan={}
    for b in binalar:
        x0,y0,x1,y1=b['box']
        for (tx,ty) in tiles:
            if x0>tx+8 and y0>ty+8 and x1<tx+T-8 and y1<ty+T-8:
                bx,by=(x0+x1)/2,(y0+y1)/2
                d=(bx-(tx+T/2))**2+(by-(ty+T/2))**2
                if b['i'] not in atanan or d<atanan[b['i']][1]:
                    atanan[b['i']]=((tx,ty),d)
    print(f'kareye atanabilen bina: {len(atanan)}/{len(binalar)}')

    grup={}
    for i,((t),_) in atanan.items(): grup.setdefault(t,[]).append(i)
    ind={b['i']:b for b in binalar}
    sonuc=[]; t0=time.time(); enc_s=0.0
    for n,(t,idx) in enumerate(sorted(grup.items()),1):
        tx,ty=t
        crop=np.array(im.crop((tx,ty,tx+T,ty+T)))
        te=time.time(); emb=m.embed(crop,normalize=True); enc_s+=time.time()-te
        for i in idx:
            b=ind[i]; x0,y0,x1,y1=b['box']
            mask,iou=m.box(emb,(x0-tx,y0-ty,x1-tx,y1-ty),(T,T))
            if mask.sum()<40: continue
            g=azimut_ve_uzunluk(mask)
            ys_,xs_=np.nonzero(mask)
            lon,lat=px2lonlat(xs_.mean()+tx, ys_.mean()+ty)
            r=dict(i=i, sam_alan=float(mask.sum())*MPP**2, ayak_alan=b['ayak'],
                   iou=iou, lon=lon, lat=lat)
            if g: r.update(g)
            sonuc.append(r)
        if n%5==0 or n==len(grup): print(f'  {n}/{len(grup)} kare, {len(sonuc)} bina, {time.time()-t0:.0f}s')
    json.dump(sonuc,open('cache/evka5_sam_sonuc.json','w'))
    print(f'\nTOPLAM {time.time()-t0:.1f} s | kodlayici {enc_s:.1f} s | '
          f'bina basina {(time.time()-t0)/max(len(sonuc),1)*1000:.0f} ms')
    return sonuc

if __name__=='__main__':
    main()
