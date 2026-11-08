# -*- coding: utf-8 -*-
"""Colab defterini uretir: notebooks/CatiGunes_Segmentasyon_Golge_Egim.ipynb

Cati segmentasyonu (SAM) + gorüntüden golge + gunes geometrisi + bina yuksekligi +
cati tipi/yuzleri/azimut + deneysel egim + yillik komsu golgelemesi + PVGIS uretimi.
Yontemler 2026-09-11 prototipleriyle (scratchpad/seg/p1..p9) EVKA-5 uzerinde sinandi.

  python scripts/defter_segmentasyon.py          -> ciktisiz defter
  python scripts/defter_segmentasyon.py --kos    -> yerelde calistirir (karolar cache/evka5'ten kopyalanir)
"""
import glob, os, shutil, sys
import nbformat as nbf

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)

hucreler = []
def md(s): hucreler.append(nbf.v4.new_markdown_cell(s.strip('\n')))
def kod(s): hucreler.append(nbf.v4.new_code_cell(s.strip('\n')))

md(r'''
# Çatı segmentasyonu, gölge ve çatı geometrisi: EVKA-5 pilotu (Çiğli)

Bu defter tek bir uydu görüntüsünden şunları çıkarır:

| Adım | Çıktı | Ne kadar güvenilir? |
|---|---|---|
| Gölge maskesi | Görüntüdeki gölgeli pikseller | Bina gölgelerini iyi yakalar; koyu bitki örtüsü karışabilir |
| Güneş geometrisi | Çekim anındaki güneş azimutu ve yüksekliği | Azimut gölgelerden **ölçülür**; yükseklik meta veri tarihiyle hesaplanır |
| Çatı segmentasyonu | Bina başına çatı maskesi ve alanı | SAM + OSM ayak izi; cephe payı ayıklanır |
| Çatı tipi | Kiremitli eğimli / karma / düz | Kiremit rengi güvenilir; kiremit dışı eğimli çatılar belirsiz |
| Çatı yüzleri ve azimut | Güneye en yakın yüzün yönü ve payı | Kırma çatı varsayımıyla |
| Eğim | Fotometrik tahmin | **Deneysel.** Bina başına güvenilir değil, dağılım olarak raporlanır |
| Bina yüksekliği | Gölge boyundan | Bant olarak; engellenen gölgelerde ölçülemez |
| Yıllık gölgelenme | Komşu binaların çatıya yıl boyu gölgesi | Basit blok model; ağaçlar yok |
| Üretim | PVGIS ile kWp ve kWh/yıl bandı | Önceki mahalle modelinden ayrıntılı, yine bant |

**Çalıştırma:** Çalışma zamanı → Çalışma zamanı türünü değiştir → **T4 GPU** → Tümünü çalıştır. GPU yoksa CPU'da da çalışır, SAM adımı ~10 dakika sürer.

**Görüntü lisansı:** Esri World Imagery karoları yalnızca bu pilot mahallede (374 karo) teknik deneme için kullanılıyor. Çiğli ölçeğine çıkmadan önce lisanslı bir görüntü kaynağı gerekiyor.
''')

md(r'''
## 0 · Kurulum
''')

kod(r'''
import sys, os, subprocess, json, math, time, re
COLAB = 'google.colab' in sys.modules
if COLAB:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'segment-anything'], check=False)

import numpy as np
import cv2
import requests
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import torch

GPU = torch.cuda.is_available()
CIHAZ = 'cuda' if GPU else 'cpu'
print('Colab:', COLAB, '| cihaz:', torch.cuda.get_device_name(0) if GPU else 'CPU')
CALISMA = 'calisma'
for d in ('karo', 'modeller', 'cikti'):
    os.makedirs(f'{CALISMA}/{d}', exist_ok=True)
UA = {'User-Agent': 'YBS-bitirme-cati-gunes/1.0 (akademik arastirma)'}
plt.rcParams.update({'figure.dpi': 110, 'axes.titlesize': 10})
''')

md(r'''
## 1 · Görüntü: Esri World Imagery, zoom 19

EVKA-5 pilot mozaiği, önceki deneylerle aynı 17 × 22 karo.
''')

kod(r'''
Z, TS = 19, 256
X0, Y0, NX, NY = 301535, 201262, 17, 22


def tile2deg(x, y, z=Z):
    n = 1 << z
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n)))), x / n * 360 - 180


NW_LAT, NW_LON = tile2deg(X0, Y0)
SE_LAT, SE_LON = tile2deg(X0 + NX, Y0 + NY)
LAT_C, LON_C = (NW_LAT + SE_LAT) / 2, (NW_LON + SE_LON) / 2
MPP = 156543.03392 * math.cos(math.radians(LAT_C)) / (1 << Z)


def lonlat2px(lon, lat):
    n = (1 << Z) * TS
    return (lon + 180) / 360 * n - X0 * TS, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n - Y0 * TS


def px2lonlat(px, py):
    n = (1 << Z) * TS
    lon = (px + X0 * TS) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (py + Y0 * TS) / n))))
    return lon, lat


URL = 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
import concurrent.futures as cf


def karo_indir(xy):
    x, y = xy
    p = f'{CALISMA}/karo/{Z}_{x}_{y}.jpg'
    if os.path.exists(p) and os.path.getsize(p) > 1000:
        return True
    for _ in range(3):
        try:
            r = requests.get(URL.format(z=Z, x=x, y=y), headers=UA, timeout=45)
            if r.status_code == 200 and len(r.content) > 1000:
                open(p, 'wb').write(r.content)
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False


isler = [(x, y) for y in range(Y0, Y0 + NY) for x in range(X0, X0 + NX)]
with cf.ThreadPoolExecutor(8) as ex:
    tamam = sum(ex.map(karo_indir, isler))
assert tamam == len(isler), f'{len(isler) - tamam} karo inmedi; hücreyi yeniden çalıştırın'

IMG = np.zeros((NY * TS, NX * TS, 3), np.uint8)
for j, y in enumerate(range(Y0, Y0 + NY)):
    for i, x in enumerate(range(X0, X0 + NX)):
        IMG[j * TS:(j + 1) * TS, i * TS:(i + 1) * TS] = np.array(Image.open(f'{CALISMA}/karo/{Z}_{x}_{y}.jpg').convert('RGB'))
H, W = IMG.shape[:2]
print(f'mozaik {W} x {H} px | {MPP:.3f} m/piksel | {W * MPP:.0f} x {H * MPP:.0f} m | merkez {LAT_C:.5f}, {LON_C:.5f}')
''')

md(r'''
### Görüntünün çekim tarihi

Esri Wayback yapılandırmasındaki en yeni sürümün meta veri katmanından alınır. Tarih, gölgelerden ölçülen güneş azimutunu güneş yüksekliğine çevirmek için gerekiyor.
''')

kod(r'''
def goruntu_meta(lon, lat):
    cfg = requests.get('https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json', timeout=60).json()
    surum = max(cfg.values(), key=lambda v: re.search(r'(\d{4}-\d{2}-\d{2})', v['itemTitle']).group(1))
    info = requests.get(surum['metadataLayerUrl'], params={'f': 'json'}, timeout=60).json()
    katman = next(l['id'] for l in info['layers'] if l['name'].startswith('30cm'))
    r = requests.get(f"{surum['metadataLayerUrl']}/{katman}/query", timeout=60, params=dict(
        geometry=f'{lon},{lat}', geometryType='esriGeometryPoint', inSR=4326, spatialRel='esriSpatialRelIntersects',
        outFields='SRC_DATE,SRC_DESC,NICE_NAME,SRC_RES', returnGeometry='false', f='json')).json()
    a = r['features'][0]['attributes']
    return dict(surum=surum['itemTitle'], tarih=str(a['SRC_DATE']), uydu=a['SRC_DESC'], urun=a['NICE_NAME'],
                cozunurluk_m=a['SRC_RES'])


try:
    META = goruntu_meta(LON_C, LAT_C)
except Exception as e:
    META = None
    print('Meta veri alınamadı:', type(e).__name__, e)
META
''')

md(r'''
## 2 · Bina ayak izleri: OpenStreetMap
''')

kod(r'''
SORGU = f"""[out:json][timeout:180];
(way["building"]({SE_LAT},{NW_LON},{NW_LAT},{SE_LON});
 relation["building"]({SE_LAT},{NW_LON},{NW_LAT},{SE_LON}););
out geom;"""
veri = None
for sunucu in ('https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'):
    for deneme in range(3):
        try:
            r = requests.post(sunucu, data={'data': SORGU}, headers=UA, timeout=240)
            if r.status_code == 200:
                veri = r.json()
                break
            print(sunucu, 'HTTP', r.status_code)
        except requests.RequestException as e:
            print(sunucu, type(e).__name__)
        time.sleep(15)
    if veri:
        break
assert veri, 'Overpass yanıt vermedi; biraz sonra hücreyi yeniden çalıştırın'

BINALAR = []
for e in veri['elements']:
    if e['type'] == 'way':
        halkalar = [e.get('geometry', [])]
    else:
        halkalar = [m['geometry'] for m in e.get('members', []) if m.get('role') == 'outer' and 'geometry' in m]
    for g in halkalar:
        if len(g) < 4 or (g[0]['lat'], g[0]['lon']) != (g[-1]['lat'], g[-1]['lon']):
            continue
        px = np.array([lonlat2px(p['lon'], p['lat']) for p in g], np.float32)
        c = px.mean(0)
        if not (0 <= c[0] < W and 0 <= c[1] < H):
            continue
        alan = cv2.contourArea(px) * MPP ** 2
        if alan < 25:
            continue
        BINALAR.append(dict(osm=f"{e['type']}/{e['id']}", px=px, ayak_alan=float(alan)))
print(len(BINALAR), 'bina poligonu | toplam ayak izi %.0f m2' % sum(b['ayak_alan'] for b in BINALAR))
''')

md(r'''
## 3 · Gölge maskesi

Üç indeks denendi (prototip): Tsai HSI oranı bitki örtüsünü de gölge sayıyor, NSVDI çoğunlukla bitki örtüsünü işaretliyor. En temiz sonuç **göreli koyuluk + mavilik** kuralı: gölgeler gökyüzü ışığıyla aydınlandığı için mavimsi olur. Buna çim ve ağaç üzerindeki çok koyu gölgeler için ikinci bir kural eklendi.
''')

kod(r'''
ORNEK1 = (slice(2400, 3000), slice(1800, 2600))
ORNEK2 = (slice(3600, 4200), slice(800, 1600))


def boya(img, maske, renk, alfa=0.55):
    out = img.copy()
    out[maske] = (out[maske] * (1 - alfa) + np.array(renk) * alfa).astype(np.uint8)
    return out


def ciz(resimler, basliklar, en=15, boy=5.5):
    fig, ax = plt.subplots(1, len(resimler), figsize=(en, boy), dpi=72)
    for a, r, b in zip(np.atleast_1d(ax), resimler, basliklar):
        a.imshow(r)
        a.set_title(b, loc='left')
        a.axis('off')
    plt.tight_layout()
    plt.show()


def golge_maskesi(img):
    f = img.astype(np.float32) / 255.0
    y8 = ((0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]) * 255).astype(np.uint8)
    esik, _ = cv2.threshold(y8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mavilik = f[..., 2] / (f.sum(-1) + 1e-6)
    s = ((y8 < esik) & (mavilik > 0.30)) | (y8 < 62)
    s = cv2.morphologyEx(s.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    return s, float(esik)


S, OTSU = golge_maskesi(IMG)
Y8 = cv2.cvtColor(IMG, cv2.COLOR_RGB2GRAY)
print(f'gölgeli piksel oranı %{100 * S.mean():.1f} | parlaklık eşiği (Otsu) {OTSU:.0f}')
ciz([IMG[ORNEK1], boya(IMG[ORNEK1], S[ORNEK1], (0, 90, 255))], ['Görüntü (örnek bölge)', 'Gölge maskesi (mavi)'])
''')

md(r'''
## 4 · Güneş geometrisi: gölgelerden azimut, tarihten yükseklik

Bina ayak izleri her yöne sırayla kaydırılır; kaydırılan bölgenin en çok gölgeyle çakıştığı yön **gölge yönüdür**, güneş bunun tam tersindedir. Bu ölçüm saat bilgisi gerektirmez. Yükseklik için meta veri tarihinde güneşin bu azimuta geldiği an bulunur.
''')

kod(r'''
F_TABAN = np.zeros((H, W), np.uint8)
for b in BINALAR:
    cv2.fillPoly(F_TABAN, [np.round(b['px']).astype(np.int32)], 1)


def kaydir(M, dx, dy):
    out = np.zeros_like(M)
    h, w = M.shape
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    out[yd, xd] = M[ys, xs]
    return out


DS = 4
Fd = cv2.resize(F_TABAN, (W // DS, H // DS), interpolation=cv2.INTER_NEAREST).astype(bool)
Sd = cv2.resize(S.astype(np.uint8), (W // DS, H // DS), interpolation=cv2.INTER_AREA) > 0.5


def yon_skoru(az):
    t = n = 0
    for r_m in (6, 12, 18):
        r = r_m / (MPP * DS)
        K = kaydir(Fd, int(round(r * math.sin(math.radians(az)))), int(round(-r * math.cos(math.radians(az))))) & ~Fd
        n += K.sum()
        t += (K & Sd).sum()
    return t / max(n, 1)


kaba = np.array([(az, yon_skoru(az)) for az in range(0, 360, 5)])
a0 = kaba[kaba[:, 1].argmax(), 0]
ince = np.array([(az, yon_skoru(az)) for az in np.arange(a0 - 6, a0 + 6.1, 0.5)])
GOLGE_YONU = float(ince[ince[:, 1].argmax(), 0]) % 360
GUNES_AZ = (GOLGE_YONU + 180) % 360


def gunes_konumu(utc, lat, lon):
    """NOAA yaklaşımı (~0,1°). utc: datetime64 dizisi. Dönüş: azimut (0=K, saat yönü), yükseklik; derece."""
    t = (np.asarray(utc, 'datetime64[s]') - np.datetime64('2000-01-01T12:00:00')).astype(float) / 86400.0
    L = np.radians((280.460 + 0.9856474 * t) % 360)
    g = np.radians((357.528 + 0.9856003 * t) % 360)
    lam = L + np.radians(1.915) * np.sin(g) + np.radians(0.020) * np.sin(2 * g)
    eps = np.radians(23.439 - 4e-7 * t)
    ra = np.arctan2(np.cos(eps) * np.sin(lam), np.cos(lam))
    dec = np.arcsin(np.sin(eps) * np.sin(lam))
    Hs = np.radians(((18.697374558 + 24.06570982441908 * t) % 24) * 15 + lon) - ra
    fi = np.radians(lat)
    el = np.arcsin(np.sin(fi) * np.sin(dec) + np.cos(fi) * np.cos(dec) * np.cos(Hs))
    az = np.arctan2(-np.sin(Hs), np.tan(dec) * np.cos(fi) - np.sin(fi) * np.cos(Hs))
    return np.degrees(az) % 360, np.degrees(el)


if META and META.get('tarih') not in (None, 'None'):
    d0 = np.datetime64(f"{META['tarih'][:4]}-{META['tarih'][4:6]}-{META['tarih'][6:8]}")
    GUNLER = [d0 - np.timedelta64(7, 'D'), d0, d0 + np.timedelta64(7, 'D')]
else:
    GUNLER = [np.datetime64('2025-12-01'), np.datetime64('2026-01-15'), np.datetime64('2026-02-28')]
ANLAR = []
for gun in GUNLER:
    t = np.arange(gun + np.timedelta64(3, 'h'), gun + np.timedelta64(15, 'h'), np.timedelta64(1, 'm'))
    az, el = gunes_konumu(t, LAT_C, LON_C)
    q = el > 0
    i = np.argmin(np.abs(az[q] - GUNES_AZ))
    ANLAR.append((str(gun), str(t[q][i])[11:16], float(el[q][i])))
E_LO, E_HI = min(a[2] for a in ANLAR), max(a[2] for a in ANLAR)
E_ORTA = ANLAR[1][2]

print(f'gölge yönü {GOLGE_YONU:.1f}° -> GÜNEŞ AZİMUTU {GUNES_AZ:.1f}° | en iyi yönde çakışma {ince[:, 1].max():.2f}, medyan yönde {np.median(kaba[:, 1]):.2f}')
for gun, saat, el in ANLAR:
    print(f'  {gun}: güneş bu azimutta UTC {saat}, yükseklik {el:.1f}°')
print(f'  kullanılan yükseklik bandı {E_LO:.1f}–{E_HI:.1f}° (meta veri tarihi ± 7 gün)')

fig = plt.figure(figsize=(4.2, 4.2))
ax = fig.add_subplot(projection='polar')
ax.set_theta_zero_location('N'); ax.set_theta_direction(-1)
ax.plot(np.radians(np.r_[kaba[:, 0], kaba[0, 0]]), np.r_[kaba[:, 1], kaba[0, 1]], color='#0E6B67')
ax.annotate('gölge', xy=(math.radians(GOLGE_YONU), kaba[:, 1].max()), color='#A8650F')
ax.set_title('Yöne göre gölge çakışması', loc='left')
plt.show()
''')

md(r'''
## 5 · Ayak izi ile çatı arasındaki kayma

Uydu dik değil eğik baktığı için yüksek binaların çatısı tabanından kaymış görünür; aradaki şerit, gölgede kalan cephedir. OSM ayak izi tabana oturur. Kayma, ayak izi maskesi ile çatı kanıtı (kiremit rengi) arasındaki çapraz korelasyonun tepe noktasından ölçülür.
''')

kod(r'''
HSV = cv2.cvtColor(IMG, cv2.COLOR_RGB2HSV)
KIREMIT_HSV = (((HSV[..., 0] < 14) | (HSV[..., 0] > 170)) & (HSV[..., 1] > 70) & (HSV[..., 2] > 90))
ds = 2
Fk = cv2.resize(F_TABAN.astype(np.float32), (W // ds, H // ds), interpolation=cv2.INTER_AREA)
Kk = cv2.resize(KIREMIT_HSV.astype(np.float32), (W // ds, H // ds), interpolation=cv2.INTER_AREA)
Fk -= Fk.mean(); Kk -= Kk.mean()
kor = np.real(np.fft.ifft2(np.fft.fft2(Kk) * np.conj(np.fft.fft2(Fk))))
r = 40
bolge = np.zeros_like(kor, bool)
bolge[:r, :r] = bolge[:r, -r:] = bolge[-r:, :r] = bolge[-r:, -r:] = True
iy, ix = np.unravel_index(np.argmax(np.where(bolge, kor, -np.inf)), kor.shape)
KAYMA = ((ix if ix < kor.shape[1] // 2 else ix - kor.shape[1]) * ds, (iy if iy < kor.shape[0] // 2 else iy - kor.shape[0]) * ds)
del Fk, Kk, kor
for b in BINALAR:
    b['px_cati0'] = b['px'] + np.array(KAYMA, np.float32)
print(f'çatı, ayak izine göre {KAYMA[0] * MPP:+.1f} m doğu, {KAYMA[1] * MPP:+.1f} m güney kaymış ({math.hypot(*KAYMA) * MPP:.1f} m)')
a, b_ = IMG[ORNEK1].copy(), IMG[ORNEK1].copy()
o = np.array([ORNEK1[1].start, ORNEK1[0].start], np.float32)
for b in BINALAR:
    cv2.polylines(a, [np.round(b['px'] - o).astype(np.int32)], True, (255, 255, 0), 2)
    cv2.polylines(b_, [np.round(b['px_cati0'] - o).astype(np.int32)], True, (255, 255, 0), 2)
ciz([a, b_], ['OSM ayak izi (tabana oturuyor)', 'Kaydırılmış ayak izi (çatıya oturuyor)'])
''')

md(r'''
## 6 · Çatı segmentasyonu: SAM ViT-B

Her bina için kaydırılmış ayak izinden bir kutu istemi verilir. SAM maskesi çatıyla birlikte cepheyi de alabildiği için son çatı maskesi, **SAM maskesi ile bina bazında çatıya oturtulmuş ayak izinin kesişimidir.** Bina bazında oturtma, çatı kanıtıyla (gölgesiz, parlak ya da kiremit renkli SAM pikselleri) ±4 m aramayla yapılır.
''')

kod(r'''
from segment_anything import sam_model_registry, SamPredictor

AGIRLIK = f'{CALISMA}/modeller/sam_vit_b_01ec64.pth'
if not os.path.exists(AGIRLIK):
    with requests.get('https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth', stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(AGIRLIK + '.part', 'wb') as f:
            for parca in r.iter_content(1 << 20):
                f.write(parca)
    os.replace(AGIRLIK + '.part', AGIRLIK)
PRED = SamPredictor(sam_model_registry['vit_b'](checkpoint=AGIRLIK).to(CIHAZ).eval())

T, ORT = 1024, 256
adim = T - ORT
kareler = sorted({(min(x, W - T), min(y, H - T)) for y in range(0, H, adim) for x in range(0, W, adim)})
grup = {}
for i, b in enumerate(BINALAR):
    p = b['px_cati0']
    x0, y0 = p.min(0); x1, y1 = p.max(0)
    en_iyi = None
    for tx, ty in kareler:
        if x0 > tx + 8 and y0 > ty + 8 and x1 < tx + T - 8 and y1 < ty + T - 8:
            d = ((x0 + x1) / 2 - tx - T / 2) ** 2 + ((y0 + y1) / 2 - ty - T / 2) ** 2
            if en_iyi is None or d < en_iyi[1]:
                en_iyi = ((tx, ty), d)
    if en_iyi:
        grup.setdefault(en_iyi[0], []).append(i)
print(sum(map(len, grup.values())), 'bina', len(grup), 'kareye atandı')

SAM_MASKE = {}
t0 = time.time()
for n, ((tx, ty), idx) in enumerate(sorted(grup.items()), 1):
    kare = IMG[ty:ty + T, tx:tx + T]
    PRED.set_image(kare)
    kutular = []
    for i in idx:
        p = BINALAR[i]['px_cati0']
        x0, y0 = p.min(0); x1, y1 = p.max(0)
        pad = 0.08 * max(x1 - x0, y1 - y0) + 3
        kutular.append([x0 - tx - pad, y0 - ty - pad, x1 - tx + pad, y1 - ty + pad])
    kt = PRED.transform.apply_boxes_torch(torch.tensor(kutular, dtype=torch.float, device=CIHAZ), kare.shape[:2])
    with torch.no_grad():
        mk, skor, _ = PRED.predict_torch(point_coords=None, point_labels=None, boxes=kt, multimask_output=False)
    mk = mk[:, 0].cpu().numpy()
    skor = skor[:, 0].cpu().numpy()
    for j, i in enumerate(idx):
        ys, xs = np.nonzero(mk[j])
        if len(xs) < 30:
            continue
        SAM_MASKE[i] = dict(x=int(xs.min() + tx), y=int(ys.min() + ty), skor=float(skor[j]),
                            m=mk[j, ys.min():ys.max() + 1, xs.min():xs.max() + 1])
    if n % 10 == 0 or n == len(grup):
        print(f'  {n}/{len(grup)} kare | {len(SAM_MASKE)} maske | {time.time() - t0:.0f} s')
''')

kod(r'''
def pencere(px, pad_m):
    pad = int(pad_m / MPP)
    x0, y0 = np.floor(px.min(0)).astype(int) - pad
    x1, y1 = np.ceil(px.max(0)).astype(int) + pad
    return max(int(x0), 0), max(int(y0), 0), min(int(x1), W), min(int(y1), H)


def poligon_maske(px, x0, y0, h, w):
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.round(px - [x0, y0]).astype(np.int32)], 1)
    return m.astype(bool)


ARAMA, ADIM = int(4 / MPP), 2
CATILAR = []
t0 = time.time()
for i, sm in SAM_MASKE.items():
    b = BINALAR[i]
    p = b['px_cati0']
    x0, y0, x1, y1 = pencere(p, 8)
    h, w = y1 - y0, x1 - x0
    sam = np.zeros((h, w), bool)
    mh, mw = sm['m'].shape
    ax0, ay0 = sm['x'] - x0, sm['y'] - y0
    bx0, by0, bx1, by1 = max(ax0, 0), max(ay0, 0), min(ax0 + mw, w), min(ay0 + mh, h)
    if bx1 <= bx0 or by1 <= by0:
        continue
    sam[by0:by1, bx0:bx1] = sm['m'][by0 - ay0:by1 - ay0, bx0 - ax0:bx1 - ax0]
    kanit = sam & ~S[y0:y1, x0:x1] & ((Y8[y0:y1, x0:x1] > 0.8 * OTSU) | KIREMIT_HSV[y0:y1, x0:x1])
    en_iyi, ekay = -1e18, (0, 0)
    for dy in range(-ARAMA, ARAMA + 1, ADIM):
        for dx in range(-ARAMA, ARAMA + 1, ADIM):
            m = poligon_maske(p + np.array([dx, dy], np.float32), x0, y0, h, w)
            s = (kanit & m).sum() - 0.5 * (m & ~kanit).sum()
            if s > en_iyi:
                en_iyi, ekay = s, (dx, dy)
    px_cati = p + np.array(ekay, np.float32)
    m_son = poligon_maske(px_cati, x0, y0, h, w)
    cati = sam & cv2.dilate(m_son.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    if cati.sum() * MPP ** 2 < 15:
        continue
    CATILAR.append(dict(i=i, osm=b['osm'], x0=x0, y0=y0, cati=cati, px_cati=px_cati,
                        oturtma=float((kanit & m_son).sum() / max(m_son.sum(), 1)),
                        kayma_m=math.hypot(KAYMA[0] + ekay[0], KAYMA[1] + ekay[1]) * MPP,
                        alan=float(cati.sum() * MPP ** 2), sam_alan=float(sam.sum() * MPP ** 2),
                        ayak_alan=b['ayak_alan'], sam_skor=sm['skor'],
                        anlik_golge=float((S[y0:y1, x0:x1] & cati).sum() / cati.sum())))
print(f'{len(CATILAR)} çatı | {time.time() - t0:.0f} s')
print(f"oturtması şüpheli çatı (poligonun %40'ından azı çatı kanıtı taşıyor): {sum(c['oturtma'] < 0.4 for c in CATILAR)}")
ozet = pd.DataFrame({
    'toplam m²': [sum(c['ayak_alan'] for c in CATILAR), sum(c['sam_alan'] for c in CATILAR), sum(c['alan'] for c in CATILAR)],
}, index=['OSM ayak izi', 'ham SAM maskesi (çatı + cephe)', 'son çatı maskesi'])
ozet['ayak izine oran'] = ozet['toplam m²'] / ozet['toplam m²'].iloc[0]
display(ozet.round(2)) if 'display' in dir() else print(ozet.round(2))

a, b_ = IMG[ORNEK1].copy(), IMG[ORNEK1].copy()
oy, ox = ORNEK1[0].start, ORNEK1[1].start
for c in CATILAR:
    sm = SAM_MASKE[c['i']]
    hh, ww = sm['m'].shape
    ya, xa = sm['y'] - oy, sm['x'] - ox
    ys0, xs0 = max(ya, 0), max(xa, 0)
    ys1, xs1 = min(ya + hh, a.shape[0]), min(xa + ww, a.shape[1])
    if ys1 > ys0 and xs1 > xs0:
        mm = sm['m'][ys0 - ya:ys1 - ya, xs0 - xa:xs1 - xa]
        a[ys0:ys1, xs0:xs1][mm] = (a[ys0:ys1, xs0:xs1][mm] * 0.5 + np.array([0, 255, 120]) * 0.5).astype(np.uint8)
    hh, ww = c['cati'].shape
    ya, xa = c['y0'] - oy, c['x0'] - ox
    ys0, xs0 = max(ya, 0), max(xa, 0)
    ys1, xs1 = min(ya + hh, b_.shape[0]), min(xa + ww, b_.shape[1])
    if ys1 > ys0 and xs1 > xs0:
        mm = c['cati'][ys0 - ya:ys1 - ya, xs0 - xa:xs1 - xa]
        b_[ys0:ys1, xs0:xs1][mm] = (b_[ys0:ys1, xs0:xs1][mm] * 0.5 + np.array([255, 140, 0]) * 0.5).astype(np.uint8)
ciz([a, b_], ['Ham SAM maskesi: çatı + gölgedeki cephe', 'Son çatı maskesi'])
''')

md(r'''
## 7 · Çatı tipi

* **Kiremit payı:** Lab renk uzayında kırmızılık (a\* > 8) ve sarılık (b\* > 5) taşıyan çatı pikselleri. ≥ %25 ise eğimli kiremit, %8–25 ise karma (kiremitli kırma çatı + orta teras).
* **Yüz parlaklık farkı:** Kırma çatının güneşe bakan yüzü karşı yüzden parlaktır; düz çatıda fark sıfıra yakındır. Kiremit rengi yoksa ve fark ≥ 0,15 ise *muhtemelen eğimli (kiremit dışı)*. Prototipte bu ölçütün kırmızı kiremitli çatılarda bile tutarsız olduğu görüldü; bu sınıf belirsiz kabul edilmelidir.
''')

kod(r'''
LAB = cv2.cvtColor(IMG, cv2.COLOR_RGB2LAB).astype(np.int16)
KIREMIT = ((LAB[..., 1] - 128) > 8) & ((LAB[..., 2] - 128) > 5) & (LAB[..., 0] > 50)
del LAB


def pusula(nx, ny):
    """Görüntü vektörü (x = doğu, y = güney) -> pusula azimutu (0 = kuzey, saat yönü)."""
    return math.degrees(math.atan2(nx, -ny)) % 360


def acifark(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def yuzlere_bol(geo, secim=None):
    """Kırma çatı varsayımı: her piksel en yakın saçak kenarının yüzüne aittir."""
    cnts, _ = cv2.findContours(geo.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rect = cv2.minAreaRect(max(cnts, key=cv2.contourArea))
    kose = cv2.boxPoints(rect)
    c = np.array(rect[0])
    ys, xs = np.nonzero(geo if secim is None else secim)
    uzak, az = [], []
    for k in range(4):
        a, b = kose[k], kose[(k + 1) % 4]
        e = b - a
        nrm = np.array([e[1], -e[0]], np.float64)
        nrm /= np.linalg.norm(nrm) + 1e-9
        if np.dot(nrm, (a + b) / 2 - c) < 0:
            nrm = -nrm
        uzak.append(np.abs((xs - a[0]) * nrm[0] + (ys - a[1]) * nrm[1]))
        az.append(pusula(*nrm))
    return ys, xs, np.argmin(np.stack(uzak), 0), az, rect


for c in CATILAR:
    y0, x0 = c['y0'], c['x0']
    h, w = c['cati'].shape
    c['kiremit_payi'] = float((KIREMIT[y0:y0 + h, x0:x0 + w] & c['cati']).sum() / c['cati'].sum())
    c['yuz_kontrast'] = None
    ic = cv2.erode(c['cati'].astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    if ic.sum() >= 80:
        ys, xs, et, az, _ = yuzlere_bol(ic)
        Ysub = Y8[y0:y0 + h, x0:x0 + w]
        I = [np.median(Ysub[ys[et == k], xs[et == k]]) if (et == k).sum() > 20 else np.nan for k in range(4)]
        g = int(np.argmin([acifark(a, GUNES_AZ) for a in az]))
        k_ = int(np.argmin([acifark(a, GOLGE_YONU) for a in az]))
        if g != k_ and not (np.isnan(I[g]) or np.isnan(I[k_])):
            c['yuz_kontrast'] = float((I[g] - I[k_]) / (I[g] + I[k_] + 1e-6))
    kp, kt = c['kiremit_payi'], c['yuz_kontrast']
    c['tip'] = ('eğimli (kiremit)' if kp >= 0.25 else 'karma (kiremit + teras)' if kp >= 0.08
                else 'muhtemelen eğimli (kiremit dışı)' if (kt is not None and kt >= 0.15) else 'düz / teras')

TIPLER = ['eğimli (kiremit)', 'karma (kiremit + teras)', 'muhtemelen eğimli (kiremit dışı)', 'düz / teras']
RENK = {TIPLER[0]: (255, 120, 0), TIPLER[1]: (255, 0, 255), TIPLER[2]: (0, 220, 0), TIPLER[3]: (0, 200, 255)}
df_tip = pd.DataFrame([(c['tip'], c['alan']) for c in CATILAR], columns=['tip', 'alan'])
tip_ozet = df_tip.groupby('tip')['alan'].agg(['count', 'sum']).reindex(TIPLER).fillna(0)
tip_ozet.columns = ['çatı sayısı', 'toplam alan m²']
print(tip_ozet.round(0))
g1, g2 = IMG[ORNEK1].copy(), IMG[ORNEK2].copy()
for c in CATILAR:
    for g, o in ((g1, ORNEK1), (g2, ORNEK2)):
        cv2.polylines(g, [np.round(c['px_cati'] - [o[1].start, o[0].start]).astype(np.int32)], True, RENK[c['tip']], 3)
ciz([g1, g2], ['Çatı tipi: turuncu kiremit, mor karma, yeşil kiremit dışı eğimli, mavi düz', 'İkinci örnek bölge'])
''')

md(r'''
## 8 · Çatı yüzleri, azimut ve deneysel eğim

**Azimut:** Dik bakışta beşik çatının iki yüzü ayırt edilemez (180° belirsizlik). Kırma çatı varsayımıyla çatı dört yüze bölünür; her yüzün yönü çatının saçak kenarından gelir. Güneş panelleri için güneye en yakın yüz ve doğu/batı yüzleri kullanılır.

**Eğim (deneysel):** Işık yüzeye ne kadar dik gelirse yüz o kadar parlak görünür. Yüz parlaklıkları, güneş geometrisi ve bilinmeyen *albedo*, *dağınık ışık*, *eğim* ile modellenip en küçük kareler yöntemiyle çözülür. Görüntü ürünü ton eşlemeli olduğu için sonuç sistematik sapma taşır; bina başına değil dağılım olarak raporlanır.
''')

kod(r'''
LIN = (IMG.astype(np.float32) / 255.0) ** 2.2
YLIN = 0.2126 * LIN[..., 0] + 0.7152 * LIN[..., 1] + 0.0722 * LIN[..., 2]
del LIN
EGIMLI = TIPLER[:3]


def cos_gelis(beta, az_f, e):
    b, a, el = math.radians(beta), math.radians(az_f), math.radians(e)
    return math.sin(el) * math.cos(b) + math.cos(el) * math.sin(b) * math.cos(math.radians(GUNES_AZ) - a)


for c in CATILAR:
    if c['tip'] not in EGIMLI:
        continue
    y0, x0 = c['y0'], c['x0']
    h, w = c['cati'].shape
    secim = c['cati'] & KIREMIT[y0:y0 + h, x0:x0 + w] if c['kiremit_payi'] >= 0.08 else c['cati']
    if secim.sum() < 60:
        continue
    ys, xs, et, az, rect = yuzlere_bol(c['cati'], secim)
    yuzler = [dict(az=az[k], n=int((et == k).sum()), I=float(np.median(YLIN[y0:y0 + h, x0:x0 + w][ys[et == k], xs[et == k]])))
              for k in range(4) if (et == k).sum() >= 25]
    if not yuzler:
        continue
    toplam = sum(y['n'] for y in yuzler)
    guney = min(yuzler, key=lambda y: acifark(y['az'], 180))
    c['pv_yuz_az'] = guney['az']
    c['pay_guney'] = guney['n'] / toplam
    c['pay_guney_dogu_bati'] = sum(y['n'] for y in yuzler if acifark(y['az'], 0) > 45) / toplam
    c['mahya_ekseni'] = (rect[2] + (90 if rect[1][0] < rect[1][1] else 0)) % 180
    if len(yuzler) >= 3:
        I = np.array([y['I'] for y in yuzler])
        wt = np.sqrt([y['n'] for y in yuzler])
        cozum = {}
        for e in (E_LO, E_HI):
            en_iyi = None
            for beta in np.arange(5, 60.5, 0.5):
                cc = np.array([max(0.0, cos_gelis(beta, y['az'], e)) for y in yuzler])
                X = np.column_stack([cc, np.ones(len(cc))])
                coef, *_ = np.linalg.lstsq(X * wt[:, None], I * wt, rcond=None)
                if coef[0] <= 0 or coef[1] < 0:
                    continue
                res = float(np.sum((wt * (X @ coef - I)) ** 2) / np.sum(wt ** 2))
                if en_iyi is None or res < en_iyi[1]:
                    en_iyi = (float(beta), res)
            if en_iyi:
                cozum[e] = en_iyi[0]
        if len(cozum) == 2:
            c['egim_foto_lo'], c['egim_foto_hi'] = min(cozum.values()), max(cozum.values())

eg = [c for c in CATILAR if 'egim_foto_lo' in c]
orta = np.array([(c['egim_foto_lo'] + c['egim_foto_hi']) / 2 for c in eg])
sinir = sum(1 for c in eg if c['egim_foto_lo'] <= 5.5 or c['egim_foto_hi'] >= 59.5)
pv = np.array([c['pv_yuz_az'] for c in CATILAR if 'pv_yuz_az' in c])
print(f'eğimli çatı: {sum(c["tip"] in EGIMLI for c in CATILAR)} | yüzlere bölünebilen {len(pv)}')
print(f'güneye en yakın yüzün azimutu: medyan {np.median(pv):.0f}° | %{100 * np.mean([acifark(a, 180) <= 45 for a in pv]):.0f}\'i güney ±45° içinde')
print(f'bu yüzün çatıdaki payı: medyan %{100 * np.median([c["pay_guney"] for c in CATILAR if "pay_guney" in c]):.0f} | '
      f'güney + doğu + batı yüzleri: %{100 * np.median([c["pay_guney_dogu_bati"] for c in CATILAR if "pay_guney_dogu_bati" in c]):.0f}')
if len(orta):
    print(f'fotometrik eğim (n={len(eg)}): medyan {np.median(orta):.1f}° | %25 {np.percentile(orta, 25):.1f}° | %75 {np.percentile(orta, 75):.1f}° | 5° ya da 60° sınırına dayanan {sinir}')

fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
ax[0].hist(orta, bins=np.arange(0, 62.5, 2.5), color='#0E6B67')
ax[0].axvspan(17, 33, color='#A8650F', alpha=0.15, label='varsayılan bant 17–33°')
ax[0].set_xlabel('fotometrik eğim (°)'); ax[0].set_ylabel('çatı'); ax[0].legend(frameon=False)
ax[0].set_title('Deneysel eğim tahmini: dağılım', loc='left')
ax[1].hist(pv, bins=np.arange(90, 272.5, 7.5), color='#2F6DB5')
ax[1].set_xlabel('güneye en yakın yüzün azimutu (°)'); ax[1].set_title('Panel için kullanılacak yüzün yönü', loc='left')
for a in ax:
    a.spines[['top', 'right']].set_visible(False)
plt.tight_layout(); plt.show()
''')

md(r'''
**Eğim kararı.** Fotometrik tahminin bina başına dağılımı çok geniş ve bir kısmı arama sınırına dayanıyor; bina başına eğim olarak kullanılmıyor. Üretim hesabında eğimli çatılar için **17–33°** bandı varsayılıyor. Türkiye'de kiremit çatılarda yaygın uygulamanın %30–35 eğim (≈ 17–19°) çevresinde olduğu belirtiliyor; bu değerin kaynağı tez için ayrıca doğrulanmalı. Kesin eğim için yükseklik verisi (Google Solar API, LiDAR ya da stereo görüntü) gerekir.
''')

md(r'''
## 9 · Bina yüksekliği: gölge boyundan

Taban ayak izi gölge yönünde adım adım kaydırılır; kaydırılan bölgenin gölgeli kaldığı en uzak mesafe gölge boyudur. Yükseklik = gölge boyu × tan(güneş yüksekliği). Gölge başka bir binaya çarpıyorsa ölçüm *engelli* sayılır ve yükseklik verilmez.
''')

kod(r'''
cekirdek = np.ones((9, 9), np.uint8)
gy_ = math.radians(GOLGE_YONU)
ux, uy = math.sin(gy_), -math.cos(gy_)
t0 = time.time()
for c in CATILAR:
    tb = BINALAR[c['i']]['px']
    bx0, by0, bx1, by1 = pencere(tb, 90)
    tm8 = poligon_maske(tb, bx0, by0, by1 - by0, bx1 - bx0).astype(np.uint8)
    tm = tm8.astype(bool)
    kendi = cv2.dilate(tm8, cekirdek).astype(bool)
    diger = cv2.dilate(F_TABAN[by0:by1, bx0:bx1], cekirdek).astype(bool) & ~kendi
    Sc = S[by0:by1, bx0:bx1]
    L, basladi, kotu, engel = 0.0, False, 0.0, False
    for r_m in np.arange(0.5, 80, 0.5):
        r = r_m / MPP
        K = kaydir(tm, int(round(r * ux)), int(round(r * uy))) & ~kendi
        if K.sum() < 10:
            continue
        serbest = K & ~diger
        if serbest.sum() < 0.4 * K.sum():
            if basladi:
                engel = True
                break
            continue
        v = (serbest & Sc).sum() / serbest.sum()
        if v >= 0.45:
            basladi, L, kotu = True, r_m, 0.0
        elif basladi:
            kotu += 0.5
            if kotu > 2.5:
                break
        elif r_m > 8:
            break
    c['golge_boyu'], c['golge_engel'] = L, engel
    if L > 0 and not engel:
        L2 = L + 4 * MPP
        c['yukseklik_lo'] = L2 * math.tan(math.radians(E_LO))
        c['yukseklik_hi'] = L2 * math.tan(math.radians(E_HI))
print(f'{time.time() - t0:.0f} s')

olculen = [c for c in CATILAR if 'yukseklik_lo' in c]
print(f'ölçülen {len(olculen)} | engelli {sum(c["golge_engel"] for c in CATILAR)} | ölçülemeyen {sum(1 for c in CATILAR if c["golge_boyu"] == 0)}')


def alan_sinifi(a):
    return 0 if a < 150 else 1 if a < 300 else 2 if a < 600 else 3


SINIF_AD = ['< 150 m²', '150–300 m²', '300–600 m²', '≥ 600 m²']
rows = []
for s_ in range(4):
    v = [c for c in olculen if alan_sinifi(c['alan']) == s_]
    if v:
        rows.append(dict(çatı_alanı=SINIF_AD[s_], n=len(v),
                         yükseklik_alt=np.median([c['yukseklik_lo'] for c in v]),
                         yükseklik_üst=np.median([c['yukseklik_hi'] for c in v])))
yuk_ozet = pd.DataFrame(rows).set_index('çatı_alanı')
yuk_ozet['kat (≈3 m)'] = (yuk_ozet['yükseklik_alt'] / 3).round(1).astype(str) + '–' + (yuk_ozet['yükseklik_üst'] / 3).round(1).astype(str)
print(yuk_ozet.round(1))
if len(olculen) > 10:
    yat = np.array([c['kayma_m'] for c in olculen])
    hh_ = np.array([(c['yukseklik_lo'] + c['yukseklik_hi']) / 2 for c in olculen])
    rho = np.corrcoef(pd.Series(yat).rank(), pd.Series(hh_).rank())[0, 1]
    print(f'çatı kayması / gölge yüksekliği medyan {np.median(yat / hh_):.2f} | Spearman {rho:+.2f} '
          '(yüksek bina daha çok kaymalı; zayıf ilişki bina bazında oturtmanın ±4 m gürültüsünü gösterir)')
''')

md(r'''
## 10 · Yıllık komşu gölgelenmesi

Binalar, gölge boyundan gelen yükseklikleriyle 1 m'lik bir blok modele dökülür. Ölçülemeyen binalara kendi alan sınıfının medyan yüksekliği verilir. 2026'nın her ayının 21'inde 30 dakikada bir güneş konumu için, her çatı hücresinden güneşe doğru ışın izlenir. Güneşi kesen daha yüksek bir yapı varsa hücre gölgededir. Kayıp, açık gök doğrudan ışınımıyla ağırlıklandırılır.

Sınırlar: ağaçlar ve arazi yok (uzak arazi gölgesi PVGIS'in ufuk hesabında zaten var), çatı üstü yapılar yok, her bina tek yükseklikte.
''')

kod(r'''
HUCRE = 1.0
olcek = MPP / HUCRE
gx, gy = int(W * MPP / HUCRE), int(H * MPP / HUCRE)
sinif_medyan = {}
for s_ in range(4):
    v = [(c['yukseklik_lo'] + c['yukseklik_hi']) / 2 for c in olculen if alan_sinifi(c['alan']) == s_]
    sinif_medyan[s_] = float(np.median(v)) if v else float(np.median([(c['yukseklik_lo'] + c['yukseklik_hi']) / 2 for c in olculen]))
cati_idx = {c['i']: c for c in CATILAR}
for i, b in enumerate(BINALAR):
    c = cati_idx.get(i)
    if c is not None and 'yukseklik_lo' in c:
        b['yukseklik'] = (c['yukseklik_lo'] + c['yukseklik_hi']) / 2
        b['yukseklik_kaynak'] = 'gölge'
    else:
        b['yukseklik'] = sinif_medyan[alan_sinifi(c['alan'] if c else b['ayak_alan'])]
        b['yukseklik_kaynak'] = 'sınıf medyanı'

Hm = np.zeros((gy, gx), np.float32)
kimlik = -np.ones((gy, gx), np.int32)
for i, b in enumerate(BINALAR):
    m = poligon_maske(b['px'] * olcek, 0, 0, gy, gx)
    Hm[m] = np.maximum(Hm[m], b['yukseklik'])
    if i in cati_idx:
        kimlik[m] = i
ys, xs = np.nonzero(kimlik >= 0)
hz, kid = Hm[ys, xs], kimlik[ys, xs]

anlar, agirlik, aylar = [], [], []
for ay in range(1, 13):
    t = np.datetime64('2026-%02d-21T00:00' % ay) + np.arange(0, 24 * 60, 30).astype('timedelta64[m]')
    az, el = gunes_konumu(t, LAT_C, LON_C)
    q = el > 3
    dni = 1353 * 0.7 ** ((1 / np.sin(np.radians(el[q]))) ** 0.678)
    for a_, e_, w_ in zip(az[q], el[q], dni * np.sin(np.radians(el[q]))):
        anlar.append((a_, e_)); agirlik.append(w_); aylar.append(ay)
agirlik, aylar = np.array(agirlik), np.array(aylar)

t0 = time.time()
golgeli = np.zeros((len(anlar), len(ys)), bool)
for n, (a_, e_) in enumerate(anlar):
    dx_, dy_ = math.sin(math.radians(a_)), -math.cos(math.radians(a_))
    te = math.tan(math.radians(e_))
    dmax = min(200.0, (Hm.max() - hz.min()) / max(te, 1e-3) + 1)
    s_ = np.zeros(len(ys), bool)
    for d in np.arange(HUCRE, dmax, HUCRE):
        px_ = np.round(xs + dx_ * d / HUCRE).astype(np.int32)
        py_ = np.round(ys + dy_ * d / HUCRE).astype(np.int32)
        ok = (px_ >= 0) & (px_ < gx) & (py_ >= 0) & (py_ < gy)
        he = np.zeros(len(ys), np.float32)
        he[ok] = Hm[py_[ok], px_[ok]]
        s_ |= he > hz + d * te + 0.5
    golgeli[n] = s_
print(f'{len(anlar)} güneş konumu | {len(ys)} çatı hücresi | ışın izleme {time.time() - t0:.0f} s')

kayip_hucre = (golgeli * agirlik[:, None]).sum(0) / agirlik.sum()
for i in np.unique(kid):
    cati_idx[int(i)]['yillik_golge_kaybi'] = float(kayip_hucre[kid == i].mean())
kayip = np.array([c.get('yillik_golge_kaybi', 0.0) for c in CATILAR])
print(f'doğrudan ışınımda yıllık gölge kaybı: medyan %{100 * np.median(kayip):.1f} | ortalama %{100 * kayip.mean():.1f} | '
      f'%10 üstü {(kayip > 0.10).sum()} çatı | %25 üstü {(kayip > 0.25).sum()} çatı')
aylik = [(golgeli[aylar == ay] * agirlik[aylar == ay][:, None]).sum(0).mean() / agirlik[aylar == ay].sum() for ay in range(1, 13)]

fig, ax = plt.subplots(1, 2, figsize=(12, 5.5), gridspec_kw={'width_ratios': [1.25, 1]})
taban = np.where(Hm > 0, 0.82, 0.97)
harita = np.dstack([taban] * 3)
renk = plt.cm.YlOrRd(np.clip(kayip_hucre / 0.3, 0, 1))[:, :3]
renk[kayip_hucre < 0.005] = [0.55, 0.78, 0.60]
harita[ys, xs] = renk
ax[0].imshow(harita)
ax[0].set_title('Yıllık gölge kaybı: yeşil ≈ 0, sarı → kırmızı %0–30', loc='left')
ax[0].axis('off')
ax[1].bar(range(1, 13), 100 * np.array(aylik), color='#A8650F')
ax[1].set_xticks(range(1, 13))
ax[1].set_xlabel('ay'); ax[1].set_ylabel('çatı hücrelerinde ortalama kayıp (%)')
ax[1].set_title('Aylara göre komşu gölgesi', loc='left')
ax[1].spines[['top', 'right']].set_visible(False)
plt.tight_layout(); plt.show()
''')

md(r'''
## 11 · Üretim: PVGIS ile bina başına bant

| Çatı | Kurulu güç | Özgül verim | Bant |
|---|---|---|---|
| Düz / teras | alan × 0,55 / 6 m² | PVGIS 0° ile 30° güney | alt: 0°, üst: 30° |
| Eğimli | yüz alanı × 0,70 / 6 m² | PVGIS, yüzün azimutu, 17–33° eğim | alt: yalnız güneye en yakın yüz, üst: güney + doğu + batı yüzleri |

Gölge kaybı yalnız doğrudan ışınımı etkiler; İzmir'de yıllık ışınımın yaklaşık %65'inin doğrudan bileşen olduğu varsayılır. Düz çatılarda kullanılabilir oran önceki modelle aynı tutuldu.
''')

kod(r'''
PV_ONBELLEK = {}


def pvgis(egim, aspect):
    anahtar = (round(egim), int(aspect))
    if anahtar not in PV_ONBELLEK:
        for deneme in range(4):
            try:
                r = requests.get('https://re.jrc.ec.europa.eu/api/v5_3/PVcalc', timeout=90, params=dict(
                    lat=round(LAT_C, 4), lon=round(LON_C, 4), peakpower=1, loss=14, angle=anahtar[0],
                    aspect=anahtar[1], outputformat='json'))
                r.raise_for_status()
                PV_ONBELLEK[anahtar] = float(r.json()['outputs']['totals']['fixed']['E_y'])
                break
            except (requests.RequestException, KeyError, ValueError):
                time.sleep(5 * (deneme + 1))
        else:
            raise RuntimeError(f'PVGIS yanıt vermedi: {anahtar}')
        time.sleep(0.3)
    return PV_ONBELLEK[anahtar]


EGIM_BANDI = (17, 33)
M2_KWP, DUZ_ORAN, YUZ_ORAN, DOGRUDAN_PAY = 6.0, 0.55, 0.70, 0.65
for c in CATILAR:
    kayip_enerji = c.get('yillik_golge_kaybi', 0.0) * DOGRUDAN_PAY
    if c['tip'] in EGIMLI and 'pv_yuz_az' in c:
        asp = int(round((c['pv_yuz_az'] - 180) / 15) * 15)
        verim = [pvgis(e, asp) for e in EGIM_BANDI]
        c['kWp_alt'] = c['alan'] * c['pay_guney'] * YUZ_ORAN / M2_KWP
        c['kWp_ust'] = c['alan'] * c['pay_guney_dogu_bati'] * YUZ_ORAN / M2_KWP
        dogu_bati = np.mean([pvgis(np.mean(EGIM_BANDI), -90), pvgis(np.mean(EGIM_BANDI), 90)])
        pay_db = max(c['pay_guney_dogu_bati'] - c['pay_guney'], 0)
        c['kWh_alt'] = c['kWp_alt'] * min(verim) * (1 - kayip_enerji)
        c['kWh_ust'] = (c['alan'] * YUZ_ORAN / M2_KWP) * (c['pay_guney'] * max(verim) + pay_db * dogu_bati) * (1 - kayip_enerji)
    else:
        c['kWp_alt'] = c['kWp_ust'] = c['alan'] * DUZ_ORAN / M2_KWP
        c['kWh_alt'] = c['kWp_alt'] * pvgis(0, 0) * (1 - kayip_enerji)
        c['kWh_ust'] = c['kWp_ust'] * pvgis(30, 0) * (1 - kayip_enerji)
print(f'{len(PV_ONBELLEK)} PVGIS sorgusu')

sonuc = pd.DataFrame([{
    'osm': c['osm'], 'tip': c['tip'], 'alan_m2': c['alan'], 'oturtma_orani': c['oturtma'], 'kiremit_payi': c['kiremit_payi'],
    'pv_yuz_azimut': c.get('pv_yuz_az'), 'pay_guney': c.get('pay_guney'),
    'egim_foto_lo': c.get('egim_foto_lo'), 'egim_foto_hi': c.get('egim_foto_hi'),
    'golge_boyu_m': c['golge_boyu'], 'golge_engel': c['golge_engel'],
    'yukseklik_lo': c.get('yukseklik_lo'), 'yukseklik_hi': c.get('yukseklik_hi'),
    'yukseklik_model': BINALAR[c['i']]['yukseklik'], 'yukseklik_kaynak': BINALAR[c['i']]['yukseklik_kaynak'],
    'anlik_golge_payi': c['anlik_golge'], 'yillik_golge_kaybi': c.get('yillik_golge_kaybi', 0.0),
    'kWp_alt': c['kWp_alt'], 'kWp_ust': c['kWp_ust'], 'kWh_alt': c['kWh_alt'], 'kWh_ust': c['kWh_ust'],
} for c in CATILAR])
tablo = sonuc.groupby('tip')[['alan_m2', 'kWp_alt', 'kWp_ust', 'kWh_alt', 'kWh_ust']].sum().reindex(TIPLER).fillna(0)
tablo.loc['TOPLAM'] = tablo.sum()
tablo[['kWh_alt', 'kWh_ust']] /= 1e6
tablo = tablo.rename(columns={'alan_m2': 'çatı m²', 'kWh_alt': 'GWh/yıl alt', 'kWh_ust': 'GWh/yıl üst'})
print(tablo.round(2))
print(f"özgül verim örnekleri: düz 0° {pvgis(0, 0):.0f} | 30° güney {pvgis(30, 0):.0f} | 17° güney {pvgis(17, 0):.0f} kWh/kWp")
''')

md(r'''
## 12 · Sonuç haritası ve dışa aktarım
''')

kod(r'''
def harita(bolge):
    g = IMG[bolge].copy()
    o = np.array([bolge[1].start, bolge[0].start], np.float32)
    for c in CATILAR:
        pc = np.round(c['px_cati'] - o).astype(np.int32)
        cv2.polylines(g, [pc], True, RENK[c['tip']], 3)
        mx, my = pc.mean(0)
        if 'pv_yuz_az' in c:
            a = math.radians(c['pv_yuz_az'])
            cv2.arrowedLine(g, (int(mx), int(my)), (int(mx + 22 * math.sin(a)), int(my - 22 * math.cos(a))), (255, 255, 0), 2, tipLength=0.35)
        yazi = f"{100 * c.get('yillik_golge_kaybi', 0):.0f}%"
        cv2.putText(g, yazi, (int(mx) - 18, int(my) + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 4)
        cv2.putText(g, yazi, (int(mx) - 18, int(my) + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return g


ciz([harita(ORNEK1), harita(ORNEK2)],
    ['Çatı tipi (kontur), panel yüzü (sarı ok), yıllık gölge kaybı (%)', 'İkinci örnek bölge'])

ozellikler = []
for c, (_, satir) in zip(CATILAR, sonuc.iterrows()):
    halka = [list(px2lonlat(float(x), float(y))) for x, y in c['px_cati']]
    if halka[0] != halka[-1]:
        halka.append(halka[0])
    ozellikler.append({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [halka]},
                       'properties': {k: (None if (isinstance(v, float) and math.isnan(v)) else (v.item() if hasattr(v, 'item') else v))
                                      for k, v in satir.items()}})
meta = dict(goruntu=META, gunes_azimutu=GUNES_AZ, gunes_yuksekligi_bandi=[E_LO, E_HI], kayma_px=[int(v) for v in KAYMA],
            egim_bandi=list(EGIM_BANDI), dogrudan_pay=DOGRUDAN_PAY)
json.dump({'type': 'FeatureCollection', 'meta': meta, 'features': ozellikler},
          open(f'{CALISMA}/cikti/evka5_catilar.geojson', 'w', encoding='utf-8'), ensure_ascii=False)
sonuc.round(4).to_csv(f'{CALISMA}/cikti/evka5_catilar.csv', sep=';', index=False, encoding='utf-8-sig')
print('Yazıldı:', f'{CALISMA}/cikti/evka5_catilar.geojson', 've .csv |', len(sonuc), 'çatı')
INDIR = False
if INDIR and COLAB:
    from google.colab import files
    files.download(f'{CALISMA}/cikti/evka5_catilar.geojson')
''')

md(r'''
## 13 · Sınırlılıklar

* **Görüntü:** Tek bir kış görüntüsü (meta veriye göre Maxar, Ocak 2026). Esri karolarının bu kullanımı yalnızca teknik deneme içindir; Çiğli ölçeği için lisanslı kaynak gerekir.
* **Doğrulama yok:** Çatı maskeleri, tipler ve yükseklikler elle etiketlenmiş bir referansla karşılaştırılmadı. "Model %X doğru" denemez; sonraki adım en az 150 binalık elle etiketli örnek.
* **Eğim:** Tek görüntüden ölçülemez. Fotometrik tahmin yalnızca dağılım düzeyinde bilgi verir; üretimde varsayılan bant kullanıldı. Google Solar API (İzmir kapsamda, anahtar bekleniyor) ya da LiDAR ile doğrulanmalı.
* **Kiremit dışı eğimli çatılar:** Renk ipucu olmadığında sınıflandırma belirsiz.
* **Çatı oturtma:** Çok yüksek binalarda çatı kayması bina bazında aranan ±4 m'yi aşabiliyor; kontur boş zemine düşebilir. `oturtma_orani` < 0,4 olan çatılar şüpheli sayılmalı (koyu renkli çatılarda bu ölçüt de yanılabilir).
* **Yükseklik:** Gölge maskesinin koyu bitki örtüsünü karıştırması ve komşu engeller ölçümü bozar; bant ±1 kat mertebesinde okunmalı.
* **Gölgelenme:** Ağaçlar, çatı üstü yapılar ve arazi dahil değil; binalar tek yükseklikte blok.
* **Üretim:** Kullanılabilir oranlar ve doğrudan ışınım payı varsayım; sonuçlar bant olarak raporlanmalı.
''')

nb = nbf.v4.new_notebook(cells=hucreler, metadata={
    'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'},
    'language_info': {'name': 'python'},
    'accelerator': 'GPU',
    'colab': {'provenance': [], 'toc_visible': True, 'gpuType': 'T4'},
})
os.makedirs(yol('notebooks'), exist_ok=True)
hedef = yol('notebooks', 'CatiGunes_Segmentasyon_Golge_Egim.ipynb')
nbf.write(nb, hedef)
print('defter:', hedef, os.path.getsize(hedef), 'bayt')

if '--kos' in sys.argv:
    from nbclient import NotebookClient
    kosu_dizin = yol('notebooks', 'seg_kosu')
    os.makedirs(os.path.join(kosu_dizin, 'calisma', 'karo'), exist_ok=True)
    for f in glob.glob(yol('cache', 'evka5', '19_*.jpg')):
        hedef_karo = os.path.join(kosu_dizin, 'calisma', 'karo', os.path.basename(f))
        if not os.path.exists(hedef_karo):
            shutil.copy(f, hedef_karo)
    kosu = nbf.read(hedef, as_version=4)
    t0 = __import__('time').time()
    try:
        NotebookClient(kosu, timeout=5400, kernel_name='python3', resources={'metadata': {'path': kosu_dizin}}).execute()
    finally:
        ciktili = yol('notebooks', 'CatiGunes_Segmentasyon_Golge_Egim_ciktili.ipynb')
        nbf.write(kosu, ciktili)
        print('ciktili defter:', ciktili, '| sure %.0f s' % (__import__('time').time() - t0))
        for i, c in enumerate(kosu.cells):
            if c.cell_type != 'code':
                continue
            for o in c.get('outputs', []):
                if o.get('output_type') == 'stream':
                    print('--- [%d] %s' % (i, o['text'][-2500:]))
                elif o.get('output_type') in ('execute_result', 'display_data'):
                    d = o.get('data', {})
                    if 'image/png' in d:
                        print('--- [%d] grafik %d kB' % (i, len(d['image/png']) // 1024))
                    elif 'text/plain' in d:
                        print('--- [%d] %s' % (i, d['text/plain'][:2000]))
                elif o.get('output_type') == 'error':
                    print('--- [%d] HATA %s: %s' % (i, o['ename'], o['evalue']))
