# -*- coding: utf-8 -*-
"""Evka-5 icin Esri World Imagery karolarini indirip tek mozaige birlestirir.
D0 NOTU: Esri World Imagery teknik deneme icin kullaniliyor; tez icin lisans sartlari
okunmali (bkz. veri envanteri)."""
import math, os, io, requests, concurrent.futures as cf
from PIL import Image

Z = 19
LAT0, LAT1 = 38.512044, 38.523119
LON0, LON1 = 27.047680, 27.058656
OUT = 'cache/evka5'
os.makedirs(OUT, exist_ok=True)
H = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
URL = 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'

def deg2tile(lat, lon, z):
    n = 1 << z
    x = int((lon + 180.0) / 360.0 * n)
    lr = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lr)) / math.pi) / 2.0 * n)
    return x, y

def tile2deg(x, y, z):
    n = 1 << z
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon

x0, y0 = deg2tile(LAT1, LON0, Z)   # kuzeybati
x1, y1 = deg2tile(LAT0, LON1, Z)   # guneydogu
xs, ys = range(x0, x1 + 1), range(y0, y1 + 1)
print(f'zoom {Z}: {len(xs)} x {len(ys)} = {len(xs)*len(ys)} karo')

def fetch(xy):
    x, y = xy
    p = f'{OUT}/{Z}_{x}_{y}.jpg'
    if os.path.exists(p) and os.path.getsize(p) > 1000:
        return xy, True
    try:
        r = requests.get(URL.format(z=Z, x=x, y=y), headers=H, timeout=45)
        if r.status_code == 200 and len(r.content) > 1000:
            open(p, 'wb').write(r.content)
            return xy, True
    except Exception:
        pass
    return xy, False

jobs = [(x, y) for y in ys for x in xs]
ok = 0
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for xy, good in ex.map(fetch, jobs):
        ok += good
print(f'indirilen: {ok}/{len(jobs)}')

# mozaik
TS = 256
W, Hh = len(xs) * TS, len(ys) * TS
mos = Image.new('RGB', (W, Hh))
for j, y in enumerate(ys):
    for i, x in enumerate(xs):
        p = f'{OUT}/{Z}_{x}_{y}.jpg'
        if os.path.exists(p):
            try: mos.paste(Image.open(p), (i * TS, j * TS))
            except Exception: pass
mos.save('cache/evka5_mozaik.jpg', quality=92)

# cozunurluk ve cografi referans
lat_c = (LAT0 + LAT1) / 2
mpp = 156543.03392 * math.cos(math.radians(lat_c)) / (1 << Z)
nw_lat, nw_lon = tile2deg(x0, y0, Z)
se_lat, se_lon = tile2deg(x1 + 1, y1 + 1, Z)
print(f'mozaik: {W} x {Hh} px   ~{mpp:.3f} m/piksel   {W*mpp:.0f} x {Hh*mpp:.0f} m')
print(f'kapsam: lat {se_lat:.6f}..{nw_lat:.6f}  lon {nw_lon:.6f}..{se_lon:.6f}')
import json
json.dump({'zoom':Z,'x0':x0,'y0':y0,'nx':len(xs),'ny':len(ys),'tile':TS,
           'nw_lat':nw_lat,'nw_lon':nw_lon,'se_lat':se_lat,'se_lon':se_lon,
           'm_per_px':mpp,'w':W,'h':Hh},
          open('cache/evka5_mozaik_ref.json','w'))
print('-> cache/evka5_mozaik.jpg  +  evka5_mozaik_ref.json')
