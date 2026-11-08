# -*- coding: utf-8 -*-
"""Colab defterini uretir: notebooks/CatiGunes_Cigli_Segmentasyon.ipynb

EVKA-5 pilot defterinin (defter_segmentasyon.py) Cigli geneline olceklenmis hali:
26 mahalle + Ataturk OSB, 4 ayri uydu cekimi, karo bazli okuma, GPU'da yillik golge.

  python scripts/defter_cigli_segmentasyon.py              -> ciktisiz defter
  python scripts/defter_cigli_segmentasyon.py --kos 20     -> birim basina 20 binalik ornekle yerelde calistirir
"""
import glob, json, os, shutil, sys, time
import nbformat as nbf

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)

ONCEKI = open(yol('cache', 'cigli_onceki_model_gomulu.json'), encoding='utf-8').read()
KAMU_GOMULU = open(yol('cache', 'kamu_cigli.geojson'), encoding='utf-8').read()

hucreler = []
def md(s): hucreler.append(nbf.v4.new_markdown_cell(s.strip('\n')))
def kod(s): hucreler.append(nbf.v4.new_code_cell(s.strip('\n')))

md(r'''
# Çiğli geneli çatı segmentasyonu, gölge ve çatı geometrisi

EVKA-5 pilotunda sınanan yöntemin Çiğli'nin **26 mahallesine ve Atatürk OSB'ye** uygulanmış hali.

**Pilottan farkı**
* Çiğli tek bir uydu görüntüsü değil: meta veriye göre **dört ayrı çekimden** (farklı uydu ve tarih) oluşuyor. Güneş yönü, güneş yüksekliği ve çatı kayması her çekim için ayrı ölçülür. Gölge yönü güvenilir ölçülemeyen çekimde yükseklik ve eğim hesaplanmaz, nedeni yazılır.
* Görüntü tek mozaik olarak belleğe alınmaz; karolar diske iner, her binanın çevresi gerektiğinde birleştirilir.
* Yıllık komşu gölgesi GPU'da, 2 m'lik ızgarada hesaplanır.
* Uzun adımlar ara sonuçlarını `calisma/ara/` klasörüne yazar; oturum kapanmadıysa hücre yeniden çalıştırıldığında kaldığı yerden devam eder.

**Çalıştırma:** Çalışma zamanı türü **T4 GPU** → Tümünü çalıştır. Toplam süre görüntü indirme hızına bağlı olarak yaklaşık 45–90 dakika.

**Görüntü lisansı:** Esri World Imagery karoları bu çalışmada Çiğli ölçeğinde (~9 bin karo) indiriliyor. Bu kullanım teknik deneme niteliğindedir; tezde ve yayında lisanslı bir görüntü kaynağıyla yinelenmesi gerekir.

**Hızlı deneme:** Kurulum hücresinde `ORNEK_BINA = 20` yapılırsa her birimden 20 bina işlenir (~10 dakika).
''')

md(r'''
## 0 · Kurulum ve ayarlar
''')

kod(r'''
import sys, os, subprocess, json, math, time, re, pickle, unicodedata, collections
COLAB = 'google.colab' in sys.modules
if COLAB:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'segment-anything'], check=False)

import numpy as np
import cv2
import requests
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
from functools import lru_cache
import concurrent.futures as cf
import torch
from shapely.geometry import shape, box, Point, Polygon, LineString
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree

ORNEK_BINA = None          # sayı verilirse her birimden o kadar bina işlenir; None = Çiğli'nin tamamı
HEDEF_KAMU = False         # True: yalnız kamu tesislerine (okul, sağlık ocağı, muhtarlık…) düşen binalar
KAMU_ETIKET = ([('amenity', x) for x in ('school', 'kindergarten', 'college', 'university', 'hospital',
                                         'clinic', 'doctors', 'townhall', 'courthouse', 'police',
                                         'fire_station', 'post_office', 'community_centre', 'social_facility',
                                         'library', 'arts_centre', 'theatre', 'animal_shelter', 'marketplace')]
               + [('building', x) for x in ('school', 'kindergarten', 'university', 'hospital', 'civic',
                                            'government', 'public', 'sports_hall')]
               + [('healthcare', 'centre'), ('office', 'government'),
                  ('leisure', 'sports_centre'), ('leisure', 'stadium')])   # kamu_binalari.py ile aynı küme
Z, TS = 19, 256
ESIK_VARSAYILAN = 114.0    # EVKA-5 pilotunun parlaklık eşiği; çekim eşiği ölçülemezse kullanılır

GPU = torch.cuda.is_available()
CIHAZ = 'cuda' if GPU else 'cpu'
print('Colab:', COLAB, '| cihaz:', torch.cuda.get_device_name(0) if GPU else 'CPU', '| kip:', 'kamu tesisleri' if HEDEF_KAMU else (ORNEK_BINA or 'tüm Çiğli'))
CALISMA = 'calisma'
for d in ('karo', 'modeller', 'cikti', 'ara'):
    os.makedirs(f'{CALISMA}/{d}', exist_ok=True)
ETIKET = 'kamu' if HEDEF_KAMU else ('tum' if ORNEK_BINA is None else f'ornek{ORNEK_BINA}')
UA = {'User-Agent': 'YBS-bitirme-cati-gunes/1.0 (akademik arastirma)'}
plt.rcParams.update({'figure.dpi': 100, 'axes.titlesize': 10})


def sadelestir(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')).lower()
    return ''.join(ch for ch in s if ch.isalnum())


def ara_kaydet(ad, nesne):
    with open(f'{CALISMA}/ara/{ad}_{ETIKET}.pkl', 'wb') as f:
        pickle.dump(nesne, f)


def ara_yukle(ad):
    p = f'{CALISMA}/ara/{ad}_{ETIKET}.pkl'
    return pickle.load(open(p, 'rb')) if os.path.exists(p) else None
''')

md(r'''
## 1 · Birimler: Çiğli'nin mahalleleri ve Atatürk OSB

Sınırlar OpenStreetMap idari sınır ilişkilerinden (admin_level 8) üretilir. OSM'de Atatürk Organize Sanayi Bölgesi ayrı bir birim olarak tanımlı; önceki mahalle modelinde yoktu, burada sanayi çatıları için ayrı raporlanır.
''')

kod(r'''
AYNALAR = ('https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter',
           'https://maps.mail.ru/osm/tools/overpass/api/interpreter', 'https://overpass.kumi.systems/api/interpreter')


def overpass(sorgu, deneme=6):
    for i in range(deneme):
        uc = AYNALAR[i % len(AYNALAR)]
        try:
            r = requests.post(uc, data={'data': sorgu}, headers=UA, timeout=240)
            if r.status_code == 200:
                return r.json()
            print(f'  {uc.split("/")[2]} HTTP {r.status_code}')
        except requests.RequestException as e:
            print(f'  {uc.split("/")[2]} {type(e).__name__}')
        time.sleep(10 * (i + 1))
    return None


d = overpass("""[out:json][timeout:180];
area["boundary"="administrative"]["admin_level"="6"]["name"="Çiğli"]->.ilce;
rel(area.ilce)["boundary"="administrative"]["admin_level"="8"];
out geom;""")
assert d, 'Overpass yanıt vermedi; hücreyi yeniden çalıştırın'
BIRIMLER = []
for e in d['elements']:
    cizgi = [LineString([(p['lon'], p['lat']) for p in m['geometry']]) for m in e.get('members', [])
             if m.get('type') == 'way' and m.get('role') in ('outer', '') and 'geometry' in m]
    pg = list(polygonize(unary_union(cizgi)))
    if not pg:
        continue
    ad = e['tags'].get('name', '?')
    BIRIMLER.append(dict(ad=ad.replace(' Mahallesi', ''), tur='OSB' if 'Sanayi' in ad else 'mahalle', geom=unary_union(pg)))
BIRIMLER.sort(key=lambda b: (b['tur'], b['ad']))
CIGLI = unary_union([b['geom'] for b in BIRIMLER])
LON_C, LAT_C = CIGLI.centroid.x, CIGLI.centroid.y
MPP = 156543.03392 * math.cos(math.radians(LAT_C)) / (1 << Z)
KM2 = 111.32 * math.cos(math.radians(LAT_C)) * 110.57
print(f"{sum(b['tur'] == 'mahalle' for b in BIRIMLER)} mahalle + {sum(b['tur'] == 'OSB' for b in BIRIMLER)} OSB | "
      f"toplam {CIGLI.area * KM2:.1f} km² | {MPP:.3f} m/piksel")
fig, ax = plt.subplots(figsize=(8, 5))
for b in BIRIMLER:
    for p in getattr(b['geom'], 'geoms', [b['geom']]):
        ax.fill(*p.exterior.xy, color='#C9A227' if b['tur'] == 'OSB' else '#DDE6E4', ec='#3F4D55', lw=0.6)
    c = b['geom'].representative_point()
    ax.text(c.x, c.y, b['ad'], fontsize=6, ha='center')
ax.set_aspect(1 / math.cos(math.radians(LAT_C))); ax.axis('off')
ax.set_title('Çiğli birimleri (sarı: Atatürk OSB)', loc='left')
plt.show()
''')

md(r'''
## 2 · Bina ayak izleri: OpenStreetMap

Çiğli sınırının 300 m çevresi dahil indirilir; sınır dışındaki binalar yalnızca gölge engeli olarak kullanılır. Yoğun karolar Overpass'te zaman aşımına düşerse dörde bölünür; inemeyen karo sessizce atlanmaz, hücre durur.
''')

kod(r'''
def lonlat2g(lon, lat):
    n = (1 << Z) * TS
    return (lon + 180.0) / 360.0 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def g2lonlat(gx, gy):
    n = (1 << Z) * TS
    return gx / n * 360.0 - 180.0, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * gy / n))))


def poligon_alan(g):
    x, y = g[:, 0] - g[:, 0].mean(), g[:, 1] - g[:, 1].mean()
    return abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2


PAY = 0.003
TAMPON = CIGLI.buffer(PAY)
x0, y0, x1, y1 = TAMPON.bounds
kuyruk = []
for lat in np.arange(y0, y1, 0.04):
    for lon in np.arange(x0, x1, 0.04):
        k = (float(lon), float(lat), float(min(lon + 0.04, x1)), float(min(lat + 0.04, y1)))
        if TAMPON.intersects(box(*k)):
            kuyruk.append((k, 0))
elemanlar, basarisiz = {}, []
TESIS_GEOM = []
if HEDEF_KAMU:
    # KISA YOL: ilçenin ~79 bin binasını taramak yerine önce kamu tesisleri çekilir,
    # sonra yalnız onların çevresindeki binalar indirilir. İlçe geneli karo taraması
    # atlanır (kuyruk boşaltılır); Overpass yükü ~80 sorgudan ~12 sorguya iner.
    if 'KAMU_VERI' in globals():
        # Gömülü veri (scripts/defter_kamu.py): cache/kamu_cigli.geojson tesisleri + OSM bina önbelleğinden
        # tesis çevresindeki binalar, Overpass çıktısıyla aynı biçimde. Overpass'e hiç gidilmez.
        import base64, gzip
        _v = json.loads(gzip.decompress(base64.b64decode(KAMU_VERI)))
        kj = {'elements': _v['tesisler']}
        for el in _v['binalar']:
            elemanlar[(el['type'], el['id'])] = el
        print(f"gömülü veri kullanılıyor ({_v['meta']})")
    else:
        _parca = []
        for _k, _v in KAMU_ETIKET:
            for _t in ('node', 'way', 'relation'):
                _parca.append(f'{_t}["{_k}"="{_v}"](area.ilce);')
        kj = overpass('[out:json][timeout:240];area["boundary"="administrative"]["admin_level"="6"]["name"="Çiğli"]->.ilce;('
                      + ''.join(_parca) + ');out geom;')
        assert kj, 'kamu tesisi sorgusu başarısız'
    odak = []
    for e in kj['elements']:
        if e['type'] == 'node':
            TESIS_GEOM.append(Point(e['lon'], e['lat']))
            odak.append((e['lat'], e['lon'], 60.0))
            continue
        g = e.get('geometry') or [q for m in e.get('members', []) if m.get('role') in ('outer', '')
                                  for q in m.get('geometry', [])]
        if len(g) < 4:
            continue
        try:
            pg = Polygon([(q['lon'], q['lat']) for q in g])
        except Exception:
            continue
        if not pg.is_valid or pg.area <= 0:
            continue
        TESIS_GEOM.append(pg)
        bx = pg.bounds
        yari = max(111320 * (bx[3] - bx[1]), 111320 * math.cos(math.radians(LAT_C)) * (bx[2] - bx[0])) / 2
        odak.append((pg.centroid.y, pg.centroid.x, min(max(yari + 80, 80), 400)))
    # around: filtresi Overpass'te pahalı (birleşik 15'li/5'li sorgular 504 veriyordu).
    # Bunun yerine her tesisin çevresi kutuya çevrilir, üst üste binen kutular birleştirilir
    # ve aşağıdaki karo kuyruğuna verilir: kutu sorgusu dizinden okunur, zaman aşımında dörde bölünür.
    _kutular = [box(lo - r / (111320 * math.cos(math.radians(la))), la - r / 111320,
                    lo + r / (111320 * math.cos(math.radians(la))), la + r / 111320) for la, lo, r in odak]
    _birlesik = unary_union(_kutular)
    kuyruk = [] if elemanlar else [(tuple(float(v) for v in p.bounds), 0) for p in getattr(_birlesik, 'geoms', [_birlesik])]
    print(f'{len(TESIS_GEOM)} kamu tesisi | {len(odak)} tesis çevresi | {len(elemanlar)} gömülü bina | '
          f'{len(kuyruk)} Overpass kutusu (ilçe taraması atlandı)')
toplam = len(kuyruk)
while kuyruk:
    (a, b_, c, e_), der = kuyruk.pop(0)
    j = overpass(f'[out:json][timeout:180];(way["building"]({b_},{a},{e_},{c});relation["building"]({b_},{a},{e_},{c}););out geom qt;', deneme=3)
    if j is None:
        if der >= 3:
            basarisiz.append((a, b_, c, e_))
            continue
        mx, my = (a + c) / 2, (b_ + e_) / 2
        kuyruk = [((a, b_, mx, my), der + 1), ((mx, b_, c, my), der + 1), ((a, my, mx, e_), der + 1), ((mx, my, c, e_), der + 1)] + kuyruk
        print('  zaman aşımı: karo dörde bölündü')
        continue
    for el in j['elements']:
        elemanlar[(el['type'], el['id'])] = el
    time.sleep(1)
assert not basarisiz, f'{len(basarisiz)} Overpass karosu inmedi: {basarisiz}'

birim_agac = STRtree([b['geom'] for b in BIRIMLER])
BINALAR = []
for (tip, kimlik), e in elemanlar.items():
    halkalar = [e.get('geometry', [])] if tip == 'way' else \
        [m['geometry'] for m in e.get('members', []) if m.get('role') == 'outer' and 'geometry' in m]
    for g in halkalar:
        if len(g) < 4 or (g[0]['lat'], g[0]['lon']) != (g[-1]['lat'], g[-1]['lon']):
            continue
        ll = np.array([(p['lon'], p['lat']) for p in g])
        gp = np.array([lonlat2g(lo, la) for lo, la in ll])
        alan = poligon_alan(gp) * MPP ** 2
        if alan < 25 or alan > 60000:
            continue
        c = Point(ll[:-1, 0].mean(), ll[:-1, 1].mean())
        birim = next((BIRIMLER[int(i)]['ad'] for i in birim_agac.query(c) if BIRIMLER[int(i)]['geom'].contains(c)), None)
        BINALAR.append(dict(osm=f'{tip}/{kimlik}', g=gp, ayak_alan=float(alan), birim=birim, lon=c.x, lat=c.y))

for b in BINALAR:
    b['analiz'] = b['birim'] is not None
if ORNEK_BINA:
    for ad in {b['birim'] for b in BINALAR if b['birim']}:
        grup = [b for b in BINALAR if b['birim'] == ad]
        mlon, mlat = np.median([b['lon'] for b in grup]), np.median([b['lat'] for b in grup])
        grup.sort(key=lambda b: (b['lon'] - mlon) ** 2 + (b['lat'] - mlat) ** 2)
        for b in grup[ORNEK_BINA:]:
            b['analiz'] = False
if HEDEF_KAMU:
    tesisler = TESIS_GEOM
    bina_nokta = [Point(b['lon'], b['lat']) for b in BINALAR]
    bina_geom = [Polygon([g2lonlat(float(x), float(y)) for x, y in b['g']]) for b in BINALAR]
    nokta_agac, geom_agac = STRtree(bina_nokta), STRtree(bina_geom)
    hedef = set()
    for gt in tesisler:
        if gt.geom_type == 'Polygon':
            hedef |= {int(i) for i in nokta_agac.query(gt) if gt.contains(bina_nokta[int(i)])}
        else:
            ic = {int(i) for i in geom_agac.query(gt) if bina_geom[int(i)].contains(gt)}
            if not ic:
                yakin = [(bina_geom[int(i)].distance(gt), int(i)) for i in geom_agac.query(gt.buffer(30 / 111320))]
                ic = {min(yakin)[1]} if yakin else set()
            hedef |= ic
    for _i, b in enumerate(BINALAR):
        b['analiz'] = b['analiz'] and _i in hedef
    print(f'{len(tesisler)} kamu tesisi -> {len(hedef)} bina hedeflendi')
ANALIZ = [i for i, b in enumerate(BINALAR) if b['analiz']]
KUTU_AGAC = STRtree([box(*b['g'].min(0), *b['g'].max(0)) for b in BINALAR])


def komsular(gx0, gy0, gx1, gy1):
    return [int(i) for i in KUTU_AGAC.query(box(gx0, gy0, gx1, gy1))]


print(f'{toplam} Overpass karosu | {len(BINALAR)} bina poligonu (tampon dahil) | işlenecek {len(ANALIZ)} bina')
print(pd.Series([BINALAR[i]['birim'] for i in ANALIZ]).value_counts().rename('bina').to_frame().T.to_string())
''')

md(r'''
## 3 · Uydu çekimleri

Esri Wayback'in en yeni sürümündeki meta veri katmanından, Çiğli'yi kesen çekim poligonları alınır. Her bina, merkezinin düştüğü çekime atanır.
''')

kod(r'''
cfg = requests.get('https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json', timeout=60).json()
surum = max(cfg.values(), key=lambda v: re.search(r'(\d{4}-\d{2}-\d{2})', v['itemTitle']).group(1))
info = requests.get(surum['metadataLayerUrl'], params={'f': 'json'}, timeout=60).json()
katman = next(l['id'] for l in info['layers'] if l['name'].startswith('30cm'))
bx = CIGLI.bounds
yanit = requests.get(f"{surum['metadataLayerUrl']}/{katman}/query", timeout=240, params=dict(
    geometry=f'{bx[0]},{bx[1]},{bx[2]},{bx[3]}', geometryType='esriGeometryEnvelope', inSR=4326, outSR=4326,
    spatialRel='esriSpatialRelIntersects', outFields='SRC_DATE,SRC_DESC,SRC_RES,NICE_NAME',
    returnGeometry='true', f='geojson')).json()
parcalar = collections.defaultdict(list)
bilgi = {}
for f in yanit['features']:
    p = f['properties']
    kod_ = f"{p['SRC_DESC']} {p['SRC_DATE']}"
    parcalar[kod_].append(shape(f['geometry']))
    bilgi[kod_] = dict(uydu=p['SRC_DESC'], tarih=str(p['SRC_DATE']), cozunurluk=p['SRC_RES'], urun=p.get('NICE_NAME'))
CEKIMLER = [dict(kod=k, geom=unary_union(v), **bilgi[k]) for k, v in parcalar.items()]
cekim_agac = STRtree([c['geom'] for c in CEKIMLER])
for b in BINALAR:
    pt = Point(b['lon'], b['lat'])
    b['cekim'] = next((CEKIMLER[int(i)]['kod'] for i in cekim_agac.query(pt) if CEKIMLER[int(i)]['geom'].contains(pt)), None)
tablo = pd.DataFrame([dict(çekim=c['kod'], uydu=c['uydu'], tarih=c['tarih'], çözünürlük_m=c['cozunurluk'],
                           işlenecek_bina=sum(1 for i in ANALIZ if BINALAR[i]['cekim'] == c['kod'])) for c in CEKIMLER])
print(surum['itemTitle'])
print(tablo[tablo['işlenecek_bina'] > 0].sort_values('işlenecek_bina', ascending=False).to_string(index=False))
print('çekime atanamayan bina:', sum(1 for i in ANALIZ if BINALAR[i]['cekim'] is None))
''')

md(r'''
## 4 · Karolar: indirme ve okuma

Birinci aşamada binaların (12 m payla) kapladığı karolar iner. Gölge boyu için gereken, gölge yönündeki karolar güneş yönü ölçüldükten sonra ikinci aşamada iner.
''')

kod(r'''
URL = 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'


def karo_yolu(x, y):
    return f'{CALISMA}/karo/{Z}_{x}_{y}.jpg'


def karo_indir(xy):
    p = karo_yolu(*xy)
    if os.path.exists(p) and os.path.getsize(p) > 1000:
        return True
    for _ in range(3):
        try:
            r = requests.get(URL.format(z=Z, x=xy[0], y=xy[1]), headers=UA, timeout=45)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(p, 'wb') as f:
                    f.write(r.content)
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False


def karolari_indir(karolar, etiket):
    karolar = list(karolar)
    eksik = [k for k in karolar if not (os.path.exists(karo_yolu(*k)) and os.path.getsize(karo_yolu(*k)) > 1000)]
    t0 = time.time()
    print(f'{etiket}: {len(karolar)} karo, indirilecek {len(eksik)}')
    for tur in range(4):
        if not eksik:
            break
        with cf.ThreadPoolExecutor(12) as ex:
            sonuc = list(ex.map(karo_indir, eksik))
        eksik = [k for k, ok in zip(eksik, sonuc) if not ok]
        if eksik:
            print(f'  tur {tur + 1}: {len(eksik)} karo inmedi, bekleyip yeniden deneniyor')
            time.sleep(30)
    assert not eksik, f'{len(eksik)} karo inmedi; hücreyi yeniden çalıştırın'
    print(f'  tamam ({time.time() - t0:.0f} s)')


def kutu_karolar(gx0, gy0, gx1, gy1):
    return {(x, y) for x in range(int(gx0 // TS), int(gx1 // TS) + 1) for y in range(int(gy0 // TS), int(gy1 // TS) + 1)}


@lru_cache(maxsize=2000)
def karo_oku(x, y):
    p = karo_yolu(x, y)
    return np.array(Image.open(p).convert('RGB')) if os.path.exists(p) else None


def pencere_oku(gx0, gy0, gx1, gy1):
    gx0, gy0, gx1, gy1 = int(gx0), int(gy0), int(gx1), int(gy1)
    img = np.zeros((gy1 - gy0, gx1 - gx0, 3), np.uint8)
    var = np.zeros((gy1 - gy0, gx1 - gx0), bool)
    for ty in range(gy0 // TS, (gy1 - 1) // TS + 1):
        for tx in range(gx0 // TS, (gx1 - 1) // TS + 1):
            k = karo_oku(tx, ty)
            if k is None:
                continue
            sx0, sy0 = max(gx0, tx * TS), max(gy0, ty * TS)
            sx1, sy1 = min(gx1, (tx + 1) * TS), min(gy1, (ty + 1) * TS)
            img[sy0 - gy0:sy1 - gy0, sx0 - gx0:sx1 - gx0] = k[sy0 - ty * TS:sy1 - ty * TS, sx0 - tx * TS:sx1 - tx * TS]
            var[sy0 - gy0:sy1 - gy0, sx0 - gx0:sx1 - gx0] = True
    return img, var


def poligon_maske(g, gx0, gy0, h, w):
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.round(g - [gx0, gy0]).astype(np.int32)], 1)
    return m.astype(bool)


PAY_PX = 12 / MPP
KAROLAR1 = set()
for i in ANALIZ:
    g = BINALAR[i]['g']
    KAROLAR1 |= kutu_karolar(*(g.min(0) - PAY_PX), *(g.max(0) + PAY_PX))
karolari_indir(sorted(KAROLAR1), 'Aşama 1 · bina karoları')
''')

md(r'''
## 5 · Çekim bazında güneş geometrisi ve çatı kayması

Her çekim için binaların en yoğun olduğu en fazla 8 pencerede (1024 px):
1. Parlaklık eşiği (Otsu) çekimin kendi görüntüsünden bulunur.
2. **Gölge yönü:** taban ayak izleri her yöne kaydırılır, gölgeyle en çok çakışan yön seçilir. Ölçüt, tepe yönü ile **tam ters yönün** oranıdır: 2,0'ın altındaysa çekim *güvenilmez* sayılır. (Yoğun dokuda her yönde gölge bulunduğu için tepe/medyan oranı yanıltıcı; EVKA-5 pilotunda güvenilir çıkan LG03 çekimi bu ölçütle yanlışlıkla elenmişti.)
3. **Güneş yüksekliği:** çekim tarihinde (± 7 gün) güneşin bu azimuta geldiği an.
4. **Çatı kayması:** ayak izi ile kiremit rengi arasındaki çapraz korelasyon.
''')

kod(r'''
def parlaklik(img):
    return 0.299 * img[..., 0].astype(np.float32) + 0.587 * img[..., 1] + 0.114 * img[..., 2]


def golge_maskesi(img, var, esik):
    f = img.astype(np.float32)
    y = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
    mavilik = f[..., 2] / (f.sum(-1) + 1e-6)
    s = ((y < esik) & (mavilik > 0.30)) | (y < 62)
    s = cv2.morphologyEx(s.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    return s & var


def kiremit_hsv(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    return ((hsv[..., 0] < 14) | (hsv[..., 0] > 170)) & (hsv[..., 1] > 70) & (hsv[..., 2] > 90)


def kaydir(M, dx, dy):
    out = np.zeros_like(M)
    h, w = M.shape
    if abs(dx) >= w or abs(dy) >= h:
        return out
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    out[yd, xd] = M[ys, xs]
    return out


def gunes_konumu(utc, lat, lon):
    """NOAA yaklaşımı (~0,1°). Dönüş: azimut (0 = kuzey, saat yönü), yükseklik; derece."""
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


PENCERE = 1024
CEKIM_PARAM = ara_yukle('cekim_param') or {}
GORSEL = {}
for ck in CEKIMLER:
    uyeler = [i for i, b in enumerate(BINALAR) if b['cekim'] == ck['kod']]
    n_analiz = sum(1 for i in uyeler if BINALAR[i]['analiz'])
    if n_analiz == 0 or ck['kod'] in CEKIM_PARAM:
        continue
    say = collections.Counter((int(BINALAR[i]['g'][:, 0].mean() // PENCERE), int(BINALAR[i]['g'][:, 1].mean() // PENCERE)) for i in uyeler)
    aday = sorted([k for k, n in say.items() if n >= 6], key=lambda k: say[k])
    if len(aday) > 8:   # en yoğun doku yerine üst-orta yoğunluk: bitişik binalar gölge yönünü bulanıklaştırıyor
        bas = max(int(len(aday) * 0.7) - 4, 0)
        aday = aday[bas:bas + 8]
    pencereler = aday
    if not pencereler:
        CEKIM_PARAM[ck['kod']] = dict(guvenilir=False, neden='yoğun pencere yok', esik=ESIK_VARSAYILAN, kayma=(0, 0), n=n_analiz)
        continue
    karolar = set()
    for px_, py_ in pencereler:
        karolar |= kutu_karolar(px_ * PENCERE, py_ * PENCERE, (px_ + 1) * PENCERE - 1, (py_ + 1) * PENCERE - 1)
    karolari_indir(sorted(karolar), f'{ck["kod"]} örnek pencereleri')
    veri = []
    for px_, py_ in pencereler:
        img, var = pencere_oku(px_ * PENCERE, py_ * PENCERE, (px_ + 1) * PENCERE, (py_ + 1) * PENCERE)
        veri.append((px_ * PENCERE, py_ * PENCERE, img, var))
    ornek = np.concatenate([parlaklik(img)[var][::7] for _, _, img, var in veri]).clip(0, 255).astype(np.uint8)
    esik = float(cv2.threshold(ornek.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[0])
    Fd, Sd, Vd, kor = [], [], [], None
    for gx0, gy0, img, var in veri:
        F = np.zeros((PENCERE, PENCERE), np.uint8)
        for j in komsular(gx0, gy0, gx0 + PENCERE, gy0 + PENCERE):
            cv2.fillPoly(F, [np.round(BINALAR[j]['g'] - [gx0, gy0]).astype(np.int32)], 1)
        S = golge_maskesi(img, var, esik)
        Fd.append(cv2.resize(F, (PENCERE // 4,) * 2, interpolation=cv2.INTER_NEAREST).astype(bool))
        Sd.append(cv2.resize(S.astype(np.uint8), (PENCERE // 4,) * 2, interpolation=cv2.INTER_AREA) > 0.5)
        Vd.append(cv2.resize(var.astype(np.uint8), (PENCERE // 4,) * 2, interpolation=cv2.INTER_NEAREST).astype(bool))
        k2 = cv2.resize((kiremit_hsv(img) & var).astype(np.float32), (PENCERE // 2,) * 2, interpolation=cv2.INTER_AREA)
        f2 = cv2.resize(F.astype(np.float32), (PENCERE // 2,) * 2, interpolation=cv2.INTER_AREA)
        if k2.sum() > 50:
            k2 -= k2.mean(); f2 -= f2.mean()
            c_ = np.real(np.fft.ifft2(np.fft.fft2(k2) * np.conj(np.fft.fft2(f2))))
            kor = c_ if kor is None else kor + c_
        if ck['kod'] not in GORSEL:
            GORSEL[ck['kod']] = (gx0, gy0, img, S)

    def yon_skoru(az):
        t = n = 0
        for f, s, v in zip(Fd, Sd, Vd):
            for r_m in (5, 10, 15):
                r = r_m / (MPP * 4)
                K = kaydir(f, int(round(r * math.sin(math.radians(az)))), int(round(-r * math.cos(math.radians(az))))) & ~f & v
                n += K.sum()
                t += (K & s).sum()
        return t / max(n, 1)

    kaba = np.array([(az, yon_skoru(az)) for az in range(0, 360, 5)])
    a0 = kaba[kaba[:, 1].argmax(), 0]
    ince = np.array([(az, yon_skoru(az)) for az in np.arange(a0 - 6, a0 + 6.1, 0.5)])
    golge_yonu = float(ince[ince[:, 1].argmax(), 0]) % 360
    gunes_az = (golge_yonu + 180) % 360
    oran = float(ince[:, 1].max() / max(np.median(kaba[:, 1]), 1e-6))
    zit_oran = float(ince[:, 1].max() / max(yon_skoru((golge_yonu + 180) % 360), 1e-6))
    kayma = (0, 0)
    if kor is not None:
        r_ = int(15 / (MPP * 2))
        bolge = np.zeros_like(kor, bool)
        bolge[:r_, :r_] = bolge[:r_, -r_:] = bolge[-r_:, :r_] = bolge[-r_:, -r_:] = True
        iy, ix = np.unravel_index(np.argmax(np.where(bolge, kor, -np.inf)), kor.shape)
        kayma = (int((ix if ix < kor.shape[1] // 2 else ix - kor.shape[1]) * 2), int((iy if iy < kor.shape[0] // 2 else iy - kor.shape[0]) * 2))
    d0 = np.datetime64(f"{ck['tarih'][:4]}-{ck['tarih'][4:6]}-{ck['tarih'][6:8]}")
    anlar = []
    for gun in (d0 - np.timedelta64(7, 'D'), d0, d0 + np.timedelta64(7, 'D')):
        t = np.arange(gun, gun + np.timedelta64(24, 'h'), np.timedelta64(1, 'm'))
        az, el = gunes_konumu(t, LAT_C, LON_C)
        q = el > 5
        fark = np.abs((az[q] - gunes_az + 180) % 360 - 180)
        j = int(np.argmin(fark))
        anlar.append((str(t[q][j])[:16], float(el[q][j]), float(fark[j])))
    # Güvenilirlik ölçütü: gölge yönü ile TAM TERS yön arasındaki fark. Yoğun dokuda her yönde
    # gölge bulunduğu için "tepe/medyan" oranı yanıltıcı; ters yön fiziksel referanstır.
    guvenilir = len(veri) >= 2 and zit_oran >= 2.0 and max(a[2] for a in anlar) <= 3
    neden = '' if guvenilir else ('tek pencere' if len(veri) < 2 else 'gölge yönü belirsiz' if zit_oran < 2.0 else 'azimut bu tarihte oluşmuyor')
    CEKIM_PARAM[ck['kod']] = dict(guvenilir=guvenilir, neden=neden, esik=esik, golge_yonu=golge_yonu, gunes_az=gunes_az,
                                  ux=math.sin(math.radians(golge_yonu)), uy=-math.cos(math.radians(golge_yonu)),
                                  e_lo=min(a[1] for a in anlar), e_hi=max(a[1] for a in anlar), kayma=kayma, oran=oran,
                                  zit_oran=zit_oran, yerel_saat=str(np.datetime64(anlar[1][0]) + np.timedelta64(3, 'h'))[11:16],
                                  pencere=len(veri), n=n_analiz, anlar=anlar, kaba=kaba)
    print(f"{ck['kod']}: gölge {golge_yonu:.1f}° güneş {gunes_az:.1f}° (tepe/ters {zit_oran:.2f}, tepe/medyan {oran:.2f}) | "
          f"yerel ~{CEKIM_PARAM[ck['kod']]['yerel_saat']}, güneş yüksekliği {CEKIM_PARAM[ck['kod']]['e_lo']:.1f}–{CEKIM_PARAM[ck['kod']]['e_hi']:.1f}° | "
          f"kayma {kayma[0] * MPP:+.1f} m D, {kayma[1] * MPP:+.1f} m G | {'güvenilir' if guvenilir else 'GÜVENİLMEZ: ' + neden}")
ara_kaydet('cekim_param', CEKIM_PARAM)

gecerli = [k for k, p in CEKIM_PARAM.items() if 'kaba' in p]
if gecerli:
    fig = plt.figure(figsize=(3.3 * len(gecerli), 3.4))
    for n, k in enumerate(gecerli, 1):
        p = CEKIM_PARAM[k]
        ax = fig.add_subplot(1, len(gecerli), n, projection='polar')
        ax.set_theta_zero_location('N'); ax.set_theta_direction(-1)
        ax.plot(np.radians(np.r_[p['kaba'][:, 0], p['kaba'][0, 0]]), np.r_[p['kaba'][:, 1], p['kaba'][0, 1]], color='#0E6B67' if p['guvenilir'] else '#A8650F')
        ax.set_title(f"{k}\n{'güvenilir' if p['guvenilir'] else 'güvenilmez'}", fontsize=9)
        ax.set_yticklabels([])
    plt.tight_layout(); plt.show()
if GORSEL:
    fig, axs = plt.subplots(1, len(GORSEL), figsize=(4.2 * len(GORSEL), 4.2), dpi=72)
    for ax, (k, (gx0, gy0, img, S)) in zip(np.atleast_1d(axs), GORSEL.items()):
        g = img.copy()
        g[S] = (g[S] * 0.4 + np.array([0, 90, 255]) * 0.6).astype(np.uint8)
        ax.imshow(g); ax.set_title(f'{k}: gölge maskesi', loc='left'); ax.axis('off')
    plt.tight_layout(); plt.show()
''')

md(r'''
## 6 · Aşama 2 karolar: gölge tarafı

Güvenilir çekimlerdeki her bina için, taban ayak izinin gölge yönünde 80 m ötesine kadar olan karolar iner.
''')

kod(r'''
KAROLAR2 = set()
for i in ANALIZ:
    p = CEKIM_PARAM.get(BINALAR[i]['cekim'])
    if not p or not p['guvenilir']:
        continue
    g = BINALAR[i]['g']
    gmin, gmax = g.min(0) - PAY_PX, g.max(0) + PAY_PX
    for t in np.arange(0, 82 / MPP, 200):
        dx, dy = p['ux'] * t, p['uy'] * t
        KAROLAR2 |= kutu_karolar(gmin[0] + dx, gmin[1] + dy, gmax[0] + dx, gmax[1] + dy)
    dx, dy = p['ux'] * 82 / MPP, p['uy'] * 82 / MPP
    KAROLAR2 |= kutu_karolar(gmin[0] + dx, gmin[1] + dy, gmax[0] + dx, gmax[1] + dy)
karolari_indir(sorted(KAROLAR2 - KAROLAR1), 'Aşama 2 · gölge tarafı')
print(f'toplam karo: {len(KAROLAR1 | KAROLAR2)}')
''')

md(r'''
## 7 · Çatı segmentasyonu: SAM ViT-B

Her bina, çekiminin çatı kaymasıyla kaydırılmış ayak izinden bir kutu istemi alır. 1024 px'lik kareler 768 px adımla yerleşir; bina tam içine sığan, merkezine en yakın kareye atanır. 1000 px'ten büyük yapılar (dev sanayi salonları) SAM'e verilmez, çatıları ayak izinden alınır.
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


def cati_kaymasi(i):
    p = CEKIM_PARAM.get(BINALAR[i]['cekim'])
    return np.array(p['kayma'] if p else (0, 0), float)


GRUP, BUYUK = collections.defaultdict(list), []
for i in ANALIZ:
    g = BINALAR[i]['g'] + cati_kaymasi(i)
    x0, y0 = g.min(0); x1, y1 = g.max(0)
    if x1 - x0 > 1000 or y1 - y0 > 1000:
        BUYUK.append(i)
        continue
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    en_iyi = None
    for ax_ in {math.floor((cx - 512) / 768) * 768, math.ceil((cx - 512) / 768) * 768}:
        for ay_ in {math.floor((cy - 512) / 768) * 768, math.ceil((cy - 512) / 768) * 768}:
            if x0 > ax_ + 8 and y0 > ay_ + 8 and x1 < ax_ + 1016 and y1 < ay_ + 1016:
                d_ = (cx - ax_ - 512) ** 2 + (cy - ay_ - 512) ** 2
                if en_iyi is None or d_ < en_iyi[1]:
                    en_iyi = ((int(ax_), int(ay_)), d_)
    GRUP[en_iyi[0] if en_iyi else (int(cx - 512), int(cy - 512))].append(i)

SAM_MASKE = ara_yukle('sam') or {}
bekleyen = [(k, v) for k, v in sorted(GRUP.items(), key=lambda kv: (kv[0][1], kv[0][0])) if any(i not in SAM_MASKE for i in v)]
print(f'{sum(map(len, GRUP.values()))} bina {len(GRUP)} kareye atandı | SAM dışı büyük yapı {len(BUYUK)} | kalan kare {len(bekleyen)}')
t0 = time.time()
for n, ((ax_, ay_), idx) in enumerate(bekleyen, 1):
    kare, _ = pencere_oku(ax_, ay_, ax_ + 1024, ay_ + 1024)
    PRED.set_image(kare)
    for s in range(0, len(idx), 64):
        alt = idx[s:s + 64]
        kutular = []
        for i in alt:
            g = BINALAR[i]['g'] + cati_kaymasi(i)
            x0, y0 = g.min(0); x1, y1 = g.max(0)
            pad = 0.08 * max(x1 - x0, y1 - y0) + 3
            kutular.append([x0 - ax_ - pad, y0 - ay_ - pad, x1 - ax_ + pad, y1 - ay_ + pad])
        kt = PRED.transform.apply_boxes_torch(torch.tensor(kutular, dtype=torch.float, device=CIHAZ), kare.shape[:2])
        with torch.no_grad():
            mk, skor, _ = PRED.predict_torch(point_coords=None, point_labels=None, boxes=kt, multimask_output=False)
        mk = mk[:, 0].cpu().numpy()
        skor = skor[:, 0].cpu().numpy()
        for j, i in enumerate(alt):
            ys, xs = np.nonzero(mk[j])
            if len(xs) < 30:
                continue
            ya, yb, xa, xb = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            SAM_MASKE[i] = dict(x=int(ax_ + xa), y=int(ay_ + ya), h=int(yb - ya), w=int(xb - xa),
                                bit=np.packbits(mk[j, ya:yb, xa:xb]), skor=float(skor[j]))
    if n % 100 == 0 or n == len(bekleyen):
        gecen = time.time() - t0
        print(f'  {n}/{len(bekleyen)} kare | {len(SAM_MASKE)} maske | {gecen:.0f} s | kalan ~{gecen / n * (len(bekleyen) - n) / 60:.0f} dk')
        ara_kaydet('sam', SAM_MASKE)
ara_kaydet('sam', SAM_MASKE)
''')

md(r'''
## 8 · Çatı maskesi, tipi, yüzleri ve deneysel eğim

Her bina için tek pencere okunur ve pilot defterdeki adımlar sırayla uygulanır:
* **Bina bazında oturtma:** kaydırılmış ayak izi, ayak izi alanı sınıfına göre ±3,5–8 m içinde çatı kanıtıyla en çok örtüştüğü yere taşınır (şablon eşleştirme); merkezden uzak çözüm cezalandırılır, böylece komşu çatıya atlamaz. Arama yarıçapı sınıf başına ölçekli çünkü çatı kayması bina yüksekliğiyle orantılı: aynı çekimde yoğun alçak dokuda 1–3 m, apartman bölgelerinde (≥300 m²) 7 m ölçüldü — küçük binada (<150 m²) sabit ±8 m'lik geniş pencere gereksiz arama alanı açıp komşu çatıya kaymayı kolaylaştırıyordu (doğrulamadaki en zayıf halka). Son çatı maskesi = SAM maskesi ∩ oturtulmuş ayak izi.
* **Tip:** Lab kırmızılığıyla kiremit payı; kiremit yoksa güneşe bakan ve karşı yüzün parlaklık farkı.
* **Yüzler ve azimut:** kırma çatı varsayımıyla dört yüz; güneye en yakın yüz ve doğu/batı yüzlerinin payı.
* **Eğim (deneysel):** yüz parlaklıklarından, yalnızca güvenilir çekimlerde; bina başına kullanılmaz.
''')

kod(r'''
TIPLER = ['eğimli (kiremit)', 'karma (kiremit + teras)', 'muhtemelen eğimli (kiremit dışı)', 'düz / teras']
EGIMLI = TIPLER[:3]
def alan_sinifi_ayak(a):
    return 0 if a < 150 else 1 if a < 300 else 2 if a < 600 else 3


# arama yarıçapı da bina yüksekliğiyle orantılı olmalı: EVKA-5'te 8 m yalnız apartman sınıfında
# (≥300 m², yükseklik 16-23 m) ölçüldü; küçük binada (<150 m², yükseklik ~8 m) aynı geniş pencere
# gereksiz VE riskli — dogrulama_metrik.py'de en zayıf halka (<150 m² %72,6) kısmen bu yüzden:
# şablon eşleştirme dar dokuda komşu çatıya kayabiliyor. Ayak izi alanı sınıfına göre daralt/genişlet.
ARAMA_M_SINIF = [3.5, 5.0, 7.0, 8.0]
ARAMA_PX_SINIF = [max(1, int(round(m_ / MPP))) for m_ in ARAMA_M_SINIF]
ARAMA = max(ARAMA_PX_SINIF)   # pencere okuma ve MESAFE2 üst sınırı, gerçek arama sınıf başına daraltılır
CEZA = 0.15                   # merkezden uzak çözümü cezalandır (komşu çatıya kaymayı önler)
_ry, _rx = np.mgrid[-ARAMA:ARAMA + 1, -ARAMA:ARAMA + 1]
MESAFE2 = (_ry ** 2 + _rx ** 2) / ARAMA ** 2
BETALAR = np.arange(5, 60.5, 0.5)
LIN_KATSAYI = np.array([0.2126, 0.7152, 0.0722], np.float32)


def pusula(nx, ny):
    return math.degrees(math.atan2(nx, -ny)) % 360


def acifark(a, b):
    d_ = abs(a - b) % 360
    return min(d_, 360 - d_)


def yuzlere_bol(geo, secim=None):
    cnts, _ = cv2.findContours(geo.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rect = cv2.minAreaRect(max(cnts, key=cv2.contourArea))
    kose = cv2.boxPoints(rect)
    c = np.array(rect[0])
    ys, xs = np.nonzero(geo if secim is None else secim)
    uzak, az = [], []
    for k in range(4):
        a, b_ = kose[k], kose[(k + 1) % 4]
        e = b_ - a
        nrm = np.array([e[1], -e[0]], np.float64)
        nrm /= np.linalg.norm(nrm) + 1e-9
        if np.dot(nrm, (a + b_) / 2 - c) < 0:
            nrm = -nrm
        uzak.append(np.abs((xs - a[0]) * nrm[0] + (ys - a[1]) * nrm[1]))
        az.append(pusula(*nrm))
    return ys, xs, np.argmin(np.stack(uzak), 0), az


def egim_coz(yuzler, prm):
    """Ağırlıklı en küçük kareler: parlaklık = A·max(0, cos(geliş)) + D; tüm eğimler için kapalı çözüm."""
    az = np.radians([v[0] for v in yuzler])
    n = np.array([v[1] for v in yuzler], float)
    I = np.array([v[2] for v in yuzler])
    gs = math.radians(prm['gunes_az'])
    b_ = np.radians(BETALAR)[:, None]
    cozum = []
    for e in (prm['e_lo'], prm['e_hi']):
        el = math.radians(e)
        c = np.maximum(0, math.sin(el) * np.cos(b_) + math.cos(el) * np.sin(b_) * np.cos(gs - az)[None, :])
        Sc, Scc, ScI = (n * c).sum(1), (n * c * c).sum(1), (n * c * I).sum(1)
        Sw, SI = n.sum(), (n * I).sum()
        det = Scc * Sw - Sc ** 2
        with np.errstate(divide='ignore', invalid='ignore'):
            A = (ScI * Sw - Sc * SI) / det
            D = (Scc * SI - Sc * ScI) / det
            res = (n * (A[:, None] * c + D[:, None] - I) ** 2).sum(1)
        ok = (det > 1e-12) & (A > 0) & (D >= 0) & np.isfinite(res)
        if not ok.any():
            return None
        cozum.append(float(BETALAR[np.argmin(np.where(ok, res, np.inf))]))
    return min(cozum), max(cozum)


CATILAR = ara_yukle('catilar') or {}
t0 = time.time()
kalan = [i for i in ANALIZ if i not in CATILAR]
for n_, i in enumerate(kalan, 1):
    b = BINALAR[i]
    prm = CEKIM_PARAM.get(b['cekim'])
    guv = bool(prm and prm['guvenilir'])
    k0 = cati_kaymasi(i)
    esik = prm['esik'] if prm else ESIK_VARSAYILAN
    g0 = b['g'] + k0
    tx0, ty0 = np.floor(g0.min(0)).astype(int)
    tx1, ty1 = np.ceil(g0.max(0)).astype(int) + 1
    pad = ARAMA + 6
    x0, y0, x1, y1 = tx0 - pad, ty0 - pad, tx1 + pad, ty1 + pad
    img, var = pencere_oku(x0, y0, x1, y1)
    h, w = y1 - y0, x1 - x0
    sm = SAM_MASKE.get(i)
    sam = np.zeros((h, w), bool)
    if sm:
        m = np.unpackbits(sm['bit'])[:sm['h'] * sm['w']].reshape(sm['h'], sm['w']).astype(bool)
        ax0, ay0 = sm['x'] - x0, sm['y'] - y0
        bx0, by0, bx1, by1 = max(ax0, 0), max(ay0, 0), min(ax0 + sm['w'], w), min(ay0 + sm['h'], h)
        if bx1 > bx0 and by1 > by0:
            sam[by0:by1, bx0:bx1] = m[by0 - ay0:by1 - ay0, bx0 - ax0:bx1 - ax0]
    S = golge_maskesi(img, var, esik)
    y = parlaklik(img)
    kanit = (sam if sm else var) & ~S & ((y > 0.8 * esik) | kiremit_hsv(img))
    sablon = poligon_maske(g0, tx0, ty0, ty1 - ty0, tx1 - tx0).astype(np.float32)
    arama_i = ARAMA_PX_SINIF[alan_sinifi_ayak(b['ayak_alan'])]
    R = cv2.matchTemplate(kanit.astype(np.float32), sablon, cv2.TM_CCORR)
    bolge = R[pad - arama_i:pad + arama_i + 1, pad - arama_i:pad + arama_i + 1]
    mesafe2_i = MESAFE2[ARAMA - arama_i:ARAMA + arama_i + 1, ARAMA - arama_i:ARAMA + arama_i + 1]
    ekay = np.zeros(2)
    if bolge.size and bolge.max() > 0:
        dy, dx = np.unravel_index(np.argmax(bolge - CEZA * sablon.sum() * mesafe2_i), bolge.shape)
        ekay = np.array([dx - arama_i, dy - arama_i], float)
    gc = g0 + ekay
    m_son = poligon_maske(gc, x0, y0, h, w)
    cati = (sam if sm else m_son) & cv2.dilate(m_son.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    n_cati = int(cati.sum())
    if n_cati * MPP ** 2 < 15:
        continue
    kay = dict(gc=gc, sam=bool(sm), alan=n_cati * MPP ** 2, sam_alan=float(sam.sum() * MPP ** 2),
               oturtma=float((kanit & m_son).sum() / max(m_son.sum(), 1)), kayma_m=float(np.hypot(*(k0 + ekay)) * MPP),
               anlik_golge=float((S & cati).sum() / n_cati))
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).astype(np.int16)
    kir = ((lab[..., 1] - 128) > 8) & ((lab[..., 2] - 128) > 5) & (lab[..., 0] > 50)
    kay['kiremit_payi'] = float((kir & cati).sum() / n_cati)
    kay['yuz_kontrast'] = None
    ic = cv2.erode(cati.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    if guv and ic.sum() >= 80:
        ys, xs, et, az = yuzlere_bol(ic)
        I = [np.median(y[ys[et == k], xs[et == k]]) if (et == k).sum() > 20 else np.nan for k in range(4)]
        gk = int(np.argmin([acifark(a, prm['gunes_az']) for a in az]))
        kk = int(np.argmin([acifark(a, prm['golge_yonu']) for a in az]))
        if gk != kk and not (np.isnan(I[gk]) or np.isnan(I[kk])):
            kay['yuz_kontrast'] = float((I[gk] - I[kk]) / (I[gk] + I[kk] + 1e-6))
    kp, kt = kay['kiremit_payi'], kay['yuz_kontrast']
    kay['tip'] = (TIPLER[0] if kp >= 0.25 else TIPLER[1] if kp >= 0.08
                  else TIPLER[2] if (kt is not None and kt >= 0.15) else TIPLER[3])
    if kay['tip'] in EGIMLI:
        secim = cati & kir if kp >= 0.08 else cati
        if secim.sum() >= 60:
            ys, xs, et, az = yuzlere_bol(cati, secim)
            lin = ((img.astype(np.float32) / 255.0) ** 2.2) @ LIN_KATSAYI
            yuzler = [(az[k], int((et == k).sum()), float(np.median(lin[ys[et == k], xs[et == k]])))
                      for k in range(4) if (et == k).sum() >= 25]
            if yuzler:
                toplam_n = sum(v[1] for v in yuzler)
                guney = min(yuzler, key=lambda v: acifark(v[0], 180))
                kay['pv_yuz_az'] = guney[0]
                kay['pay_guney'] = guney[1] / toplam_n
                kay['pay_gdb'] = sum(v[1] for v in yuzler if acifark(v[0], 0) > 45) / toplam_n
                if guv and len(yuzler) >= 3:
                    sonuc_ = egim_coz(yuzler, prm)
                    if sonuc_:
                        kay['egim_foto_lo'], kay['egim_foto_hi'] = sonuc_
    CATILAR[i] = kay
    if n_ % 3000 == 0 or n_ == len(kalan):
        gecen = time.time() - t0
        print(f'  {n_}/{len(kalan)} bina | {len(CATILAR)} çatı | {gecen:.0f} s | kalan ~{gecen / n_ * (len(kalan) - n_) / 60:.0f} dk')
        ara_kaydet('catilar', CATILAR)
ara_kaydet('catilar', CATILAR)

df = pd.DataFrame([dict(birim=BINALAR[i]['birim'], cekim=BINALAR[i]['cekim'], **{k: v for k, v in c.items() if k != 'gc'}) for i, c in CATILAR.items()])
print(f"{len(df)} çatı | OSM ayak izi {sum(BINALAR[i]['ayak_alan'] for i in CATILAR):,.0f} m² | ham SAM {df['sam_alan'].sum():,.0f} m² | son çatı {df['alan'].sum():,.0f} m²".replace(',', '.'))
print(f"SAM'siz (büyük yapı ya da maske yok): {(~df['sam']).sum()} | oturtması şüpheli (< 0,4): {(df['oturtma'] < 0.4).sum()}")
print(df.pivot_table(index='tip', columns='cekim', values='alan', aggfunc='count', fill_value=0).reindex(TIPLER).fillna(0).astype(int).to_string())
print('çekim bazında tabandan çatıya kayma (m, medyan):', df.groupby('cekim')['kayma_m'].median().round(2).to_dict())
eg = df.dropna(subset=['egim_foto_lo']) if 'egim_foto_lo' in df else df.iloc[0:0]
if len(eg):
    orta = (eg['egim_foto_lo'] + eg['egim_foto_hi']) / 2
    print(f'fotometrik eğim (n={len(eg)}): medyan {orta.median():.1f}° | %25 {orta.quantile(.25):.1f}° | %75 {orta.quantile(.75):.1f}° | '
          f'sınıra dayanan {((eg["egim_foto_lo"] <= 5.5) | (eg["egim_foto_hi"] >= 59.5)).sum()}')
RENK = {TIPLER[0]: (255, 120, 0), TIPLER[1]: (255, 0, 255), TIPLER[2]: (0, 220, 0), TIPLER[3]: (0, 200, 255)}
if GORSEL:
    fig, axs = plt.subplots(1, len(GORSEL), figsize=(4.2 * len(GORSEL), 4.2), dpi=72)
    for ax, (k, (gx0, gy0, img, _)) in zip(np.atleast_1d(axs), GORSEL.items()):
        g = img.copy()
        for i in komsular(gx0, gy0, gx0 + PENCERE, gy0 + PENCERE):
            if i in CATILAR:
                cv2.polylines(g, [np.round(CATILAR[i]['gc'] - [gx0, gy0]).astype(np.int32)], True, RENK[CATILAR[i]['tip']], 3)
        ax.imshow(g); ax.set_title(f'{k}: çatı tipi', loc='left'); ax.axis('off')
    plt.tight_layout(); plt.show()
''')

md(r'''
## 9 · Bina yüksekliği: gölge boyundan

Yalnızca güneş geometrisi güvenilir çekimlerde. Hesap 0,47 m'lik (2×) küçültülmüş pencerede, gölge yönündeki şeritte yapılır. Gölge başka bir binaya çarparsa *engelli*, görüntü eksikse *görüntü yok* sayılır.
''')

kod(r'''
DSY = 2
cek5 = np.ones((5, 5), np.uint8)
YUKSEK = ara_yukle('yukseklik') or {}
t0 = time.time()
kalan = [i for i in CATILAR if i not in YUKSEK]
for n_, i in enumerate(kalan, 1):
    b = BINALAR[i]
    p = CEKIM_PARAM.get(b['cekim'])
    if not p or not p['guvenilir']:
        YUKSEK[i] = dict(durum='çekim güvenilmez')
        continue
    g = b['g']
    L = 82 / MPP
    gmin, gmax = g.min(0), g.max(0)
    x0 = int(min(gmin[0], gmin[0] + p['ux'] * L)) - 10
    x1 = int(max(gmax[0], gmax[0] + p['ux'] * L)) + 10
    y0 = int(min(gmin[1], gmin[1] + p['uy'] * L)) - 10
    y1 = int(max(gmax[1], gmax[1] + p['uy'] * L)) + 10
    img, var = pencere_oku(x0, y0, x1, y1)
    h, w = y1 - y0, x1 - x0
    S = golge_maskesi(img, var, p['esik'])
    diger = np.zeros((h, w), np.uint8)
    for j in komsular(x0, y0, x1, y1):
        if j != i:
            cv2.fillPoly(diger, [np.round(BINALAR[j]['g'] - [x0, y0]).astype(np.int32)], 1)
    kendi_tam = poligon_maske(g, x0, y0, h, w).astype(np.uint8)
    boyut = (max(w // DSY, 1), max(h // DSY, 1))
    tm = cv2.resize(kendi_tam, boyut, interpolation=cv2.INTER_NEAREST).astype(bool)
    kendi = cv2.dilate(tm.astype(np.uint8), cek5).astype(bool)
    dig = cv2.dilate(cv2.resize(diger, boyut, interpolation=cv2.INTER_NEAREST), cek5).astype(bool) & ~kendi
    Sd = cv2.resize(S.astype(np.uint8), boyut, interpolation=cv2.INTER_AREA) > 0.5
    Vd = cv2.resize(var.astype(np.uint8), boyut, interpolation=cv2.INTER_NEAREST).astype(bool)
    L_, basladi, kotu, durum = 0.0, False, 0.0, 'ölçülemedi'
    for r_m in np.arange(1.0, 81.0, 1.0):
        r = r_m / (MPP * DSY)
        K = kaydir(tm, int(round(r * p['ux'])), int(round(r * p['uy']))) & ~kendi
        if K.sum() < 5:
            continue
        if (K & ~Vd).sum() > 0.2 * K.sum():
            durum = 'görüntü yok'
            break
        serbest = K & ~dig
        if serbest.sum() < 0.4 * K.sum():
            if basladi:
                durum = 'engelli'
                break
            continue
        v = (serbest & Sd).sum() / serbest.sum()
        if v >= 0.45:
            basladi, L_, kotu = True, r_m, 0.0
        elif basladi:
            kotu += 1.0
            if kotu > 2.5:
                break
        elif r_m > 8:
            break
    kay = dict(golge_boyu=L_, durum=durum)
    if L_ > 0 and durum not in ('engelli', 'görüntü yok'):
        L2 = L_ + 4 * MPP
        kay.update(durum='ölçüldü', yukseklik_lo=L2 * math.tan(math.radians(p['e_lo'])), yukseklik_hi=L2 * math.tan(math.radians(p['e_hi'])))
    YUKSEK[i] = kay
    if n_ % 5000 == 0 or n_ == len(kalan):
        gecen = time.time() - t0
        print(f'  {n_}/{len(kalan)} | {gecen:.0f} s | kalan ~{gecen / n_ * (len(kalan) - n_) / 60:.0f} dk')
        ara_kaydet('yukseklik', YUKSEK)
ara_kaydet('yukseklik', YUKSEK)


def alan_sinifi(a):
    return 0 if a < 150 else 1 if a < 300 else 2 if a < 600 else 3


SINIF_AD = ['< 150 m²', '150–300 m²', '300–600 m²', '≥ 600 m²']
dy_ = pd.DataFrame([dict(cekim=BINALAR[i]['cekim'], sinif=SINIF_AD[alan_sinifi(CATILAR[i]['alan'])], **v) for i, v in YUKSEK.items()])
print(dy_['durum'].value_counts().to_string())
olc = dy_[dy_['durum'] == 'ölçüldü']
if len(olc):
    ozet = olc.groupby('sinif').agg(n=('golge_boyu', 'size'), yukseklik_alt=('yukseklik_lo', 'median'), yukseklik_ust=('yukseklik_hi', 'median')).reindex(SINIF_AD)
    print(ozet.round(1).to_string())
    print(olc.groupby('cekim')[['yukseklik_lo', 'yukseklik_hi']].median().round(1).to_string())
''')

md(r'''
## 10 · Yıllık komşu gölgelenmesi (GPU)

Tüm binalar (tampon dahil) 2 m'lik yükseklik ızgarasına dökülür. Ölçülen yükseklik yoksa, ölçülenlerin alan sınıfı medyanı kullanılır. 2026'nın her ayının 21'inde 30 dakikada bir güneş konumu için her çatı hücresinden güneşe doğru ışın izlenir; kayıp açık gök doğrudan ışınımıyla ağırlıklandırılır. Ağaçlar, çatı üstü yapılar ve arazi dahil değildir.
''')

kod(r'''
HUCRE = 2.0
olcum = [(CATILAR[i]['alan'], (v['yukseklik_lo'] + v['yukseklik_hi']) / 2) for i, v in YUKSEK.items() if v.get('durum') == 'ölçüldü']
genel_medyan = float(np.median([h for _, h in olcum])) if olcum else 12.0
sinif_medyan = {s: float(np.median([h for a, h in olcum if alan_sinifi(a) == s])) if any(alan_sinifi(a) == s for a, _ in olcum) else genel_medyan for s in range(4)}
print('alan sınıfı medyan yükseklik (m):', {SINIF_AD[k]: round(v, 1) for k, v in sinif_medyan.items()})
for i, b in enumerate(BINALAR):
    v = YUKSEK.get(i, {})
    if v.get('durum') == 'ölçüldü':
        b['yukseklik'], b['yukseklik_kaynak'] = (v['yukseklik_lo'] + v['yukseklik_hi']) / 2, 'gölge'
    else:
        b['yukseklik'] = sinif_medyan[alan_sinifi(CATILAR[i]['alan'] if i in CATILAR else b['ayak_alan'])]
        b['yukseklik_kaynak'] = 'sınıf medyanı'

tum = np.concatenate([b['g'] for b in BINALAR])
GX0, GY0 = tum.min(0) - 50
olcek = MPP / HUCRE
nx, ny = int((tum[:, 0].max() - GX0) * olcek) + 60, int((tum[:, 1].max() - GY0) * olcek) + 60
Hm = np.zeros((ny, nx), np.float32)
for i in sorted(range(len(BINALAR)), key=lambda k: BINALAR[k]['yukseklik']):
    cv2.fillPoly(Hm, [np.round((BINALAR[i]['g'] - [GX0, GY0]) * olcek).astype(np.int32)], float(BINALAR[i]['yukseklik']))
xs_l, ys_l, kid_l = [], [], []
for i in CATILAR:
    p = np.round((BINALAR[i]['g'] - [GX0, GY0]) * olcek).astype(np.int32)
    a, b_ = p.min(0), p.max(0) + 1
    m = np.zeros((b_[1] - a[1], b_[0] - a[0]), np.uint8)
    cv2.fillPoly(m, [p - a], 1)
    yy, xx = np.nonzero(m)
    if len(xx) == 0:
        yy, xx = np.array([0]), np.array([0])
    xs_l.append(xx + a[0]); ys_l.append(yy + a[1]); kid_l.append(np.full(len(xx), i, np.int64))
XS, YS, KID = np.concatenate(xs_l), np.concatenate(ys_l), np.concatenate(kid_l)
print(f'yükseklik ızgarası {nx} x {ny} ({nx * ny / 1e6:.0f} M hücre) | çatı hücresi {len(XS):,}'.replace(',', '.'))

anlar = []
for ay in range(1, 13):
    t = np.datetime64('2026-%02d-21T00:00' % ay) + np.arange(0, 24 * 60, 30).astype('timedelta64[m]')
    az, el = gunes_konumu(t, LAT_C, LON_C)
    q = el > 3
    dni = 1353 * 0.7 ** ((1 / np.sin(np.radians(el[q]))) ** 0.678)
    anlar += [(a_, e_, w_, ay) for a_, e_, w_ in zip(az[q], el[q], dni * np.sin(np.radians(el[q])))]

Ht = torch.from_numpy(Hm).to(CIHAZ)
X = torch.from_numpy(XS.astype(np.float32)).to(CIHAZ)
Y = torch.from_numpy(YS.astype(np.float32)).to(CIHAZ)
HZ = Ht[torch.from_numpy(YS).long().to(CIHAZ), torch.from_numpy(XS).long().to(CIHAZ)]
kayip = torch.zeros(len(XS), device=CIHAZ)
aylik_pay = np.zeros(12); aylik_agirlik = np.zeros(12)
hmax = float(Hm.max())
t0 = time.time()
for n_, (a_, e_, w_, ay) in enumerate(anlar, 1):
    dx, dy = math.sin(math.radians(a_)), -math.cos(math.radians(a_))
    te = math.tan(math.radians(e_))
    dmax = min(200.0, hmax / max(te, 1e-3) + HUCRE)
    golgeli = torch.zeros(len(XS), dtype=torch.bool, device=CIHAZ)
    for d_ in np.arange(HUCRE, dmax, HUCRE):
        px_ = torch.round(X + dx * d_ / HUCRE).long()
        py_ = torch.round(Y + dy * d_ / HUCRE).long()
        ok = (px_ >= 0) & (px_ < nx) & (py_ >= 0) & (py_ < ny)
        he = Ht[py_.clamp(0, ny - 1), px_.clamp(0, nx - 1)] * ok
        golgeli |= he > HZ + d_ * te + 0.5
    kayip += float(w_) * golgeli.float()
    aylik_pay[ay - 1] += w_ * float(golgeli.float().mean())
    aylik_agirlik[ay - 1] += w_
    if n_ % 70 == 0 or n_ == len(anlar):
        print(f'  {n_}/{len(anlar)} güneş konumu | {time.time() - t0:.0f} s')
agirlik_toplam = sum(a[2] for a in anlar)
KID_t = torch.from_numpy(KID).to(CIHAZ)
tekil, ters = torch.unique(KID_t, return_inverse=True)
toplam_k = torch.zeros(len(tekil), device=CIHAZ).index_add_(0, ters, kayip)
say_k = torch.zeros(len(tekil), device=CIHAZ).index_add_(0, ters, torch.ones_like(kayip))
for i, v in zip(tekil.cpu().numpy(), (toplam_k / say_k / agirlik_toplam).cpu().numpy()):
    CATILAR[int(i)]['yillik_golge_kaybi'] = float(v)
kay_ = np.array([c.get('yillik_golge_kaybi', 0.0) for c in CATILAR.values()])
print(f'yıllık doğrudan ışınım gölge kaybı: medyan %{100 * np.median(kay_):.1f} | ortalama %{100 * kay_.mean():.1f} | '
      f'%10 üstü {(kay_ > 0.10).sum()} çatı | %25 üstü {(kay_ > 0.25).sum()} çatı')
del Ht, X, Y, HZ, kayip
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={'width_ratios': [1.4, 1]})
lon_ = [BINALAR[i]['lon'] for i in CATILAR]; lat_ = [BINALAR[i]['lat'] for i in CATILAR]
sc = ax[0].scatter(lon_, lat_, c=100 * kay_, s=2, cmap='YlOrRd', vmin=0, vmax=20)
for b in BIRIMLER:
    for p in getattr(b['geom'], 'geoms', [b['geom']]):
        ax[0].plot(*p.exterior.xy, color='#9AA6AD', lw=0.5)
ax[0].set_aspect(1 / math.cos(math.radians(LAT_C))); ax[0].axis('off')
plt.colorbar(sc, ax=ax[0], shrink=0.7, label='yıllık gölge kaybı (%)')
ax[0].set_title('Çatı başına komşu gölgesi', loc='left')
ax[1].bar(range(1, 13), 100 * aylik_pay / np.maximum(aylik_agirlik, 1e-9), color='#A8650F')
ax[1].set_xticks(range(1, 13)); ax[1].set_xlabel('ay'); ax[1].set_ylabel('çatı hücrelerinde ortalama kayıp (%)')
ax[1].set_title('Aylara göre', loc='left'); ax[1].spines[['top', 'right']].set_visible(False)
plt.tight_layout(); plt.show()
''')

md(r'''
## 11 · Üretim: PVGIS ile çatı başına bant

| Çatı | Kurulu güç | Özgül verim | Bant |
|---|---|---|---|
| Düz / teras | alan × 0,55 / 6 m² | PVGIS 0° ile 30° güney | alt: 0°, üst: 30° |
| Eğimli | yüz alanı × 0,70 / 6 m² | yüzün azimutu, 17–33° eğim | alt: yalnız güneye en yakın yüz, üst: güney + doğu + batı |

Eğim ve azimut yapılandırmaları Çiğli merkezinde sorgulanır; her birimin kendi düz çatı verimi ile merkez arasındaki oran uygulanır. Gölge kaybı yalnız doğrudan ışınıma (yıllık ışınımın ~%65'i) uygulanır.
''')

kod(r'''
PV_ONBELLEK = {}


def pvgis(lat, lon, egim, aspect):
    anahtar = (round(lat, 3), round(lon, 3), int(round(egim)), int(aspect))
    if anahtar not in PV_ONBELLEK:
        for deneme in range(5):
            try:
                r = requests.get('https://re.jrc.ec.europa.eu/api/v5_3/PVcalc', timeout=90, params=dict(
                    lat=anahtar[0], lon=anahtar[1], peakpower=1, loss=14, angle=anahtar[2], aspect=anahtar[3], outputformat='json'))
                r.raise_for_status()
                PV_ONBELLEK[anahtar] = float(r.json()['outputs']['totals']['fixed']['E_y'])
                break
            except (requests.RequestException, KeyError, ValueError):
                time.sleep(5 * (deneme + 1))
        else:
            raise RuntimeError(f'PVGIS yanıt vermedi: {anahtar}')
        time.sleep(0.3)
    return PV_ONBELLEK[anahtar]


def pv_merkez(egim, aspect):
    return pvgis(LAT_C, LON_C, egim, aspect)


MERKEZ_DUZ = pv_merkez(0, 0)
BIRIM_OLCEK = {}
for b in BIRIMLER:
    c = b['geom'].representative_point()
    BIRIM_OLCEK[b['ad']] = pvgis(c.y, c.x, 0, 0) / MERKEZ_DUZ
EGIM_BANDI = (17, 33)
M2_KWP, DUZ_ORAN, YUZ_ORAN, DOGRUDAN_PAY = 6.0, 0.55, 0.70, 0.65
DOGU_BATI = (pv_merkez(25, -90) + pv_merkez(25, 90)) / 2
for i, c in CATILAR.items():
    olc_ = BIRIM_OLCEK.get(BINALAR[i]['birim'], 1.0)
    kay_e = c.get('yillik_golge_kaybi', 0.0) * DOGRUDAN_PAY
    if c['tip'] in EGIMLI and 'pv_yuz_az' in c:
        asp = int(round((c['pv_yuz_az'] - 180) / 15) * 15)
        v = [pv_merkez(e, asp) for e in EGIM_BANDI]
        c['kWp_alt'] = c['alan'] * c['pay_guney'] * YUZ_ORAN / M2_KWP
        c['kWp_ust'] = c['alan'] * c['pay_gdb'] * YUZ_ORAN / M2_KWP
        c['kWh_alt'] = c['kWp_alt'] * min(v) * olc_ * (1 - kay_e)
        c['kWh_ust'] = (c['alan'] * YUZ_ORAN / M2_KWP) * (c['pay_guney'] * max(v) + max(c['pay_gdb'] - c['pay_guney'], 0) * DOGU_BATI) * olc_ * (1 - kay_e)
    else:
        c['kWp_alt'] = c['kWp_ust'] = c['alan'] * DUZ_ORAN / M2_KWP
        c['kWh_alt'] = c['kWp_alt'] * MERKEZ_DUZ * olc_ * (1 - kay_e)
        c['kWh_ust'] = c['kWp_ust'] * pv_merkez(30, 0) * olc_ * (1 - kay_e)
print(f'{len(PV_ONBELLEK)} PVGIS sorgusu | merkez düz {MERKEZ_DUZ:.0f} kWh/kWp | birim ölçeği {min(BIRIM_OLCEK.values()):.3f}–{max(BIRIM_OLCEK.values()):.3f}')
''')

md(r'''
## 12 · Birim özeti ve önceki ayak izi modeliyle karşılaştırma

Önceki model (`bolge_modelleri.py`) çatı alanını OSM–Microsoft ayak izi bandından, eğim ve azimutu senaryo olarak alıyordu. Burada aynı mahalleler için segmentasyon, tip, yüz yönü ve komşu gölgesi dahil edilmiş bant yan yana gösterilir.
''')

kod(r'''
# dogrulama_metrik.py (540 çatılık örnek, 2026-09-12): oturtma_orani < 0,4 bandında doğruluk %17,1,
# normal bantta %87,9 — bu bayrak ayırıcı. Üretim toplamları yalnız güvenilir çatılardan hesaplanır,
# şüpheliler ayrı adet/m² olarak gösterilir, sessizce toplama karışmaz.
ESIK_OTURTMA = 0.4
ONCEKI = json.loads("""__ONCEKI__""")
ONCEKI = {sadelestir(k): v for k, v in ONCEKI.items()}
satirlar = []
for b in BIRIMLER:
    idx = [i for i in CATILAR if BINALAR[i]['birim'] == b['ad']]
    if not idx:
        continue
    tum_cs = [CATILAR[i] for i in idx]
    cs = [c for c in tum_cs if c['oturtma'] >= ESIK_OTURTMA]
    supheli = [c for c in tum_cs if c['oturtma'] < ESIK_OTURTMA]
    if not cs:
        continue
    alan = sum(c['alan'] for c in cs)
    tip_pay = collections.Counter()
    for c in cs:
        tip_pay[c['tip']] += c['alan']
    onc = ONCEKI.get(sadelestir(b['ad']))
    satirlar.append({
        'birim': b['ad'], 'tür': b['tur'], 'çatı': len(cs), 'çatı m²': alan,
        'şüpheli çatı': len(supheli), 'şüpheli m²': sum(c['alan'] for c in supheli),
        'eğimli %': 100 * sum(tip_pay[t] for t in EGIMLI) / alan,
        'gölge kaybı %': 100 * np.average([c.get('yillik_golge_kaybi', 0) for c in cs], weights=[c['alan'] for c in cs]),
        'MWp alt': sum(c['kWp_alt'] for c in cs) / 1e3, 'MWp üst': sum(c['kWp_ust'] for c in cs) / 1e3,
        'GWh alt': sum(c['kWh_alt'] for c in cs) / 1e6, 'GWh üst': sum(c['kWh_ust'] for c in cs) / 1e6,
        'önceki GWh alt': onc[2] / 1e3 if onc else np.nan, 'önceki GWh üst': onc[3] / 1e3 if onc else np.nan,
        'önceki kademe': onc[0] if onc else '',
    })
OZET = pd.DataFrame(satirlar).set_index('birim')
OZET['GWh merkez'] = np.sqrt(OZET['GWh alt'] * OZET['GWh üst'])
OZET = OZET.sort_values('GWh merkez', ascending=False)
toplam = OZET[['çatı', 'çatı m²', 'şüpheli çatı', 'şüpheli m²', 'MWp alt', 'MWp üst', 'GWh alt', 'GWh üst', 'önceki GWh alt', 'önceki GWh üst']].sum()
print(OZET.round(2).to_string())
print(f"\nTOPLAM (yalnız oturtma_orani >= {ESIK_OTURTMA}): {int(toplam['çatı'])} çatı | {toplam['çatı m²'] / 1e6:.2f} km² | "
      f"{toplam['MWp alt']:.0f}–{toplam['MWp üst']:.0f} MWp | {toplam['GWh alt']:.1f}–{toplam['GWh üst']:.1f} GWh/yıl "
      f"(bant {toplam['GWh üst'] / toplam['GWh alt']:.2f}×)")
print(f"AYRI TUTULDU — oturtması şüpheli: {int(toplam['şüpheli çatı'])} çatı, {toplam['şüpheli m²'] / 1e6:.2f} km² "
      f"(doğrulamada bu bantta doğruluk %17,1, normal bantta %87,9 — üretim toplamına dahil edilmedi)")
mah = OZET[OZET['tür'] == 'mahalle']
if mah['önceki GWh alt'].notna().any():
    print(f"26 mahalle, önceki ayak izi modeli: {mah['önceki GWh alt'].sum():.1f}–{mah['önceki GWh üst'].sum():.1f} GWh/yıl | "
          f"segmentasyon: {mah['GWh alt'].sum():.1f}–{mah['GWh üst'].sum():.1f} GWh/yıl")
    if ORNEK_BINA:
        print('!! Örnek kipinde yalnız birim başına', ORNEK_BINA, 'bina işlendi; önceki modelle toplam karşılaştırması anlamlı değil.')
    if HEDEF_KAMU:
        print('!! Kamu kipinde yalnız kamu tesislerine düşen binalar işlendi; birim toplamları ve önceki modelle karşılaştırma GEÇERSİZ.')

fig, ax = plt.subplots(1, 2, figsize=(14, 7.5), gridspec_kw={'width_ratios': [1.1, 1]})
deger = OZET['GWh merkez']
norm = plt.Normalize(0, deger.max())
for b in BIRIMLER:
    renk = plt.cm.YlOrBr(norm(deger.get(b['ad'], 0)))
    for p in getattr(b['geom'], 'geoms', [b['geom']]):
        ax[0].fill(*p.exterior.xy, color=renk, ec='#3F4D55', lw=0.5)
    if b['ad'] in deger.index[:8]:
        c = b['geom'].representative_point()
        ax[0].text(c.x, c.y, b['ad'], fontsize=7, ha='center')
ax[0].set_aspect(1 / math.cos(math.radians(LAT_C))); ax[0].axis('off')
plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap='YlOrBr'), ax=ax[0], shrink=0.6, label='GWh/yıl (bant merkezi)')
ax[0].set_title('Çatı güneş üretimi, birim bazında', loc='left')
sirali = mah.sort_values('GWh merkez')
yk = np.arange(len(sirali))
ax[1].hlines(yk + 0.18, sirali['GWh alt'], sirali['GWh üst'], color='#0E6B67', lw=4, label='segmentasyon (bu defter)')
ax[1].hlines(yk - 0.18, sirali['önceki GWh alt'], sirali['önceki GWh üst'], color='#C3CBD0', lw=4, label='önceki ayak izi modeli')
ax[1].set_yticks(yk, sirali.index, fontsize=8)
ax[1].set_xlabel('GWh/yıl'); ax[1].legend(frameon=False, loc='lower right')
ax[1].set_title('Mahalle bantları', loc='left'); ax[1].spines[['top', 'right']].set_visible(False)
plt.tight_layout(); plt.show()
''')

md(r'''
## 13 · Dışa aktarım
''')

kod(r'''
kayitlar, ozellikler = [], []
for i, c in CATILAR.items():
    b = BINALAR[i]
    v = YUKSEK.get(i, {})
    sat = dict(osm=b['osm'], birim=b['birim'], cekim=b['cekim'], tip=c['tip'], sam=c['sam'], alan_m2=round(c['alan'], 1),
               oturtma_orani=round(c['oturtma'], 3), kiremit_payi=round(c['kiremit_payi'], 3),
               pv_yuz_azimut=c.get('pv_yuz_az'), pay_guney=c.get('pay_guney'), pay_guney_dogu_bati=c.get('pay_gdb'),
               egim_foto_lo=c.get('egim_foto_lo'), egim_foto_hi=c.get('egim_foto_hi'),
               golge_durumu=v.get('durum'), golge_boyu_m=v.get('golge_boyu'),
               yukseklik_lo=v.get('yukseklik_lo'), yukseklik_hi=v.get('yukseklik_hi'),
               yukseklik_model=round(b['yukseklik'], 1), yukseklik_kaynak=b['yukseklik_kaynak'],
               anlik_golge_payi=round(c['anlik_golge'], 3), yillik_golge_kaybi=round(c.get('yillik_golge_kaybi', 0.0), 4),
               kWp_alt=round(c['kWp_alt'], 2), kWp_ust=round(c['kWp_ust'], 2), kWh_alt=round(c['kWh_alt']), kWh_ust=round(c['kWh_ust']))
    kayitlar.append(sat)
    halka = [[round(v_, 7) for v_ in g2lonlat(float(x), float(y))] for x, y in c['gc']]
    if halka[0] != halka[-1]:
        halka.append(halka[0])
    ozellikler.append({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [halka]},
                       'properties': {k: (float(v_) if isinstance(v_, (np.floating,)) else v_) for k, v_ in sat.items()}})
meta = dict(surum=surum['itemTitle'], ornek_bina=ORNEK_BINA, egim_bandi=list(EGIM_BANDI), dogrudan_pay=DOGRUDAN_PAY,
            cekimler={k: {kk: (vv if not isinstance(vv, np.ndarray) else None) for kk, vv in p.items() if kk != 'kaba'} for k, p in CEKIM_PARAM.items()})
with open(f'{CALISMA}/cikti/cigli_catilar_{ETIKET}.geojson', 'w', encoding='utf-8') as f:
    json.dump({'type': 'FeatureCollection', 'meta': meta, 'features': ozellikler}, f, ensure_ascii=False, default=float)
pd.DataFrame(kayitlar).to_csv(f'{CALISMA}/cikti/cigli_catilar_{ETIKET}.csv', sep=';', index=False, encoding='utf-8-sig')
OZET.round(3).to_csv(f'{CALISMA}/cikti/cigli_birim_ozeti_{ETIKET}.csv', sep=';', encoding='utf-8-sig')
for ad in os.listdir(f'{CALISMA}/cikti'):
    print(f'{ad:45s} {os.path.getsize(f"{CALISMA}/cikti/{ad}") / 1e6:6.2f} MB')
INDIR = False
if INDIR and COLAB:
    from google.colab import files
    for ad in os.listdir(f'{CALISMA}/cikti'):
        files.download(f'{CALISMA}/cikti/{ad}')
''')

md(r'''
## 14 · Kamu binası eşleştirme

`cache/kamu_cigli.geojson` (166 tesis: eğitim, sağlık, idari, spor, sosyal-kültür) bu deftere gömülü olarak geliyor — Overpass'e ayrıca gidilmiyor. Her çatı, merkezinin hangi tesis poligonuna düştüğüne (okul çok binalı olabilir, hepsi işaretlenir) ya da hangi nokta tesise en yakın olduğuna (30 m içinde, zayıf kanıt) bakılarak `kamu`/`kamu_grup`/`kamu_tur`/`kamu_ad`/`kamu_mulkiyet` alanlarıyla etiketlenir. Mülkiyetin 166 tesisin 77'sinde 'belirsiz', 22'sinde 'özel' olduğu unutulmamalı — üretim tablosu 'özel'i dışarıda bırakır. Yöntem `scripts/kamu_cati_eslestir.py` ile birebir aynı, burada aynı `ozellikler` listesi üzerinde çalışır.
''')

kod(r'''
KAMU_TESISLER = json.loads("""__KAMU__""")['features']
_agac_geo = [shape(f['geometry']) for f in ozellikler]
_agac = STRtree(_agac_geo)
_merkez = [g.centroid for g in _agac_geo]
_NOKTA_MESAFE_M, _DERECE = 30.0, 1 / 111320.0

for f in ozellikler:
    f['properties'].update(kamu=False, kamu_grup=None, kamu_tur=None, kamu_ad=None,
                           kamu_mulkiyet=None, kamu_eslesme=None, kamu_osm=None)

_eslesen_tesis, _catisiz_tesis = 0, []
for t in KAMU_TESISLER:
    p = t['properties']
    g = shape(t['geometry'])
    bulunan = []
    if t['geometry']['type'] == 'Polygon':
        for i in _agac.query(g):
            i = int(i)
            if g.contains(_merkez[i]):
                bulunan.append((i, 'poligon'))
    else:
        for i in _agac.query(g):
            i = int(i)
            if _agac_geo[i].contains(g):
                bulunan.append((i, 'nokta-ic'))
        if not bulunan:
            yakin = [(_agac_geo[int(i)].distance(g), int(i)) for i in _agac.query(g.buffer(_NOKTA_MESAFE_M * _DERECE))]
            if yakin:
                _, i = min(yakin)
                bulunan.append((i, 'nokta-yakin'))
    if not bulunan:
        _catisiz_tesis.append(p.get('ad'))
        continue
    _eslesen_tesis += 1
    for i, nasil in bulunan:
        pr = ozellikler[i]['properties']
        if pr['kamu'] and pr['kamu_eslesme'] == 'poligon' and nasil != 'poligon':
            continue
        pr.update(kamu=True, kamu_grup=p.get('grup'), kamu_tur=p.get('tur'), kamu_ad=p.get('ad'),
                  kamu_mulkiyet=p.get('mulkiyet'), kamu_eslesme=nasil,
                  kamu_osm='%s/%s' % (p.get('osm_tip'), p.get('osm_id')))

_kamu_tum = [f for f in ozellikler if f['properties']['kamu']]
_kamu_iyi = [f for f in _kamu_tum if f['properties']['oturtma_orani'] >= ESIK_OTURTMA]
print(f'{_eslesen_tesis} tesis çatıyla eşleşti, {len(_catisiz_tesis)} tesis çatısız kaldı')
print(f'{len(_kamu_tum)} çatı kamu işaretlendi (%{100 * len(_kamu_tum) / len(ozellikler):.1f}) | '
      f'oturtma güvenilir: {len(_kamu_iyi)} çatı, {len(_kamu_tum) - len(_kamu_iyi)} şüpheli ayrı tutuldu')


def _topla(kume):
    return (len(kume), sum(f['properties']['alan_m2'] for f in kume), sum(f['properties']['kWp_alt'] for f in kume),
            sum(f['properties']['kWh_alt'] for f in kume) / 1e6, sum(f['properties']['kWh_ust'] for f in kume) / 1e6)


print('\nGRUBA GÖRE (yalnız oturtma güvenilir):')
for grup in sorted({f['properties']['kamu_grup'] for f in _kamu_iyi}):
    n, a, kwp, lo, hi = _topla([f for f in _kamu_iyi if f['properties']['kamu_grup'] == grup])
    print(f'  {grup:14s} {n:5d} çatı  {a:10,.0f} m²  {kwp:8.1f} kWp  {lo:.3f}-{hi:.3f} GWh/yıl'.replace(',', '.'))
n, a, kwp, lo, hi = _topla(_kamu_iyi)
print(f'  {"TOPLAM":14s} {n:5d} çatı  {a:10,.0f} m²  {kwp:8.1f} kWp  {lo:.3f}-{hi:.3f} GWh/yıl'.replace(',', '.'))

print('\nMÜLKİYETE GÖRE (özel olanlar üretim hesabına girmemeli):')
for m in sorted({f['properties']['kamu_mulkiyet'] for f in _kamu_iyi}):
    n, a, kwp, lo, hi = _topla([f for f in _kamu_iyi if f['properties']['kamu_mulkiyet'] == m])
    print(f'  {m:10s} {n:4d} çatı  {a:9,.0f} m²  {kwp:7.1f} kWp'.replace(',', '.'))

print('\nEN BÜYÜK 10 KAMU ÇATISI (güvenilir):')
for f in sorted(_kamu_iyi, key=lambda f: -f['properties']['alan_m2'])[:10]:
    p = f['properties']
    print(f"  {(p['kamu_ad'] or '?')[:42]:42s} {p['kamu_grup']:9s} {p['alan_m2']:7.0f} m²  "
          f"{p['kWp_alt']:6.1f} kWp  {p['kWh_alt']/1e3:5.0f}-{p['kWh_ust']/1e3:5.0f} MWh/yıl  ot {p['oturtma_orani']:.2f}")

_kendi = collections.defaultdict(float)
for f in _kamu_iyi:
    _kendi[f['properties']['kamu_osm']] += f['properties']['alan_m2']
_onceki_m2 = {'%s/%s' % (t['properties']['osm_tip'], t['properties']['osm_id']): t['properties'].get('cati_m2') for t in KAMU_TESISLER}
_ciftler = [(k, v, _onceki_m2[k]) for k, v in _kendi.items() if _onceki_m2.get(k)]
if _ciftler:
    _oranlar = sorted(v / o for _, v, o in _ciftler)
    print(f'\nÇAPRAZ KONTROL (segmentasyon çatı m² / kamu_binalari.py ayak izi m²): n={len(_ciftler)} | '
          f'medyan {_oranlar[len(_oranlar)//2]:.2f} | ortalama {sum(_oranlar)/len(_oranlar):.2f}')
if _catisiz_tesis:
    print('\nçatısı bulunamayan tesisler (ilk 10):', ', '.join(x or '?' for x in _catisiz_tesis[:10]))

with open(f'{CALISMA}/cikti/cigli_catilar_{ETIKET}_kamu.geojson', 'w', encoding='utf-8') as _f:
    json.dump({'type': 'FeatureCollection', 'meta': meta, 'features': ozellikler}, _f, ensure_ascii=False, default=float)
pd.DataFrame([f['properties'] for f in ozellikler]).to_csv(f'{CALISMA}/cikti/cigli_catilar_{ETIKET}_kamu.csv', sep=';', index=False, encoding='utf-8-sig')
print(f"\n-> cigli_catilar_{ETIKET}_kamu.geojson / .csv (kamu alanları eklenmiş, tüm {len(ozellikler)} çatı)")
INDIR_KAMU = True
if INDIR_KAMU and COLAB:
    from google.colab import files
    files.download(f'{CALISMA}/cikti/cigli_catilar_{ETIKET}_kamu.geojson')
    files.download(f'{CALISMA}/cikti/cigli_catilar_{ETIKET}_kamu.csv')
''')

md(r'''
## 15 · İnteraktif harita

Her çatı için tip, oturtma güvenilirliği ve kamu binası bilgisini gösteren tek bir HTML dosyası — internet gerekmeden tarayıcıda açılır, Çiğli genelinde tek tek çatı sınırlarını görmek için (hücre 5/8'deki örnek karolardan farklı olarak burada tüm birimler var). Kamu katmanı bir önceki hücrede eşleştirildiği için burada dolu gelir.
''')

kod(r'''
if COLAB:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'folium'], check=False)
import folium

RENK_TIP = {
    'eğimli (kiremit)': '#FF7800', 'karma (kiremit + teras)': '#E91E8C',
    'muhtemelen eğimli (kiremit dışı)': '#2E9E2E', 'düz / teras': '#00AEEF',
}
RENK_GUVENILIR, RENK_SUPHELI, RENK_KAMU = '#2E9E2E', '#E53935', '#8E24AA'
_TOOLTIP_ALAN = ['birim', 'cekim', 'tip', 'alan_m2', 'oturtma_orani', 'kWh_alt', 'kWh_ust']
_TOOLTIP_BASLIK = ['birim', 'çekim', 'tip', 'alan (m²)', 'oturtma oranı', 'üretim alt (kWh)', 'üretim üst (kWh)']
_TOOLTIP_ALAN_KAMU = _TOOLTIP_ALAN + ['kamu_ad', 'kamu_grup', 'kamu_mulkiyet']
_TOOLTIP_BASLIK_KAMU = _TOOLTIP_BASLIK + ['kamu adı', 'kamu grubu', 'mülkiyet']
# yalnız bunlar kullanılıyor; segmentasyon çıktısının geri kalan ~20 alanını (yükseklik, gölge,
# eğim, SAM ham verisi...) embed etmek dosyayı gereksiz büyütür.
_GEREKLI_ALAN = ['birim', 'cekim', 'tip', 'alan_m2', 'oturtma_orani', 'kWh_alt', 'kWh_ust',
                 'kamu', 'kamu_ad', 'kamu_grup', 'kamu_mulkiyet']


def _hafiflet(feats):
    return [{'type': 'Feature', 'geometry': f['geometry'],
             'properties': {k: f['properties'].get(k) for k in _GEREKLI_ALAN}} for f in feats]


def _katman_ekle(harita, feats, ad, renk_fn, alanlar=_TOOLTIP_ALAN, basliklar=_TOOLTIP_BASLIK, ac=False):
    # TEK folium.GeoJson çağrısı + style_function: çatı başına ayrı GeoJson objesi açmak
    # (ilk denemede yapıldığı gibi) 20 binin üzerinde çatıda 100 MB'a varan bir dosya üretti;
    # tek katman + stil fonksiyonu aynı veriyi ~5 kat küçük dosyada, çok daha hızlı render eder.
    fc = {'type': 'FeatureCollection', 'features': feats}
    folium.GeoJson(
        fc, name=ad, show=ac,
        style_function=lambda feat: {'color': '#20303A', 'weight': 0.5, 'fillColor': renk_fn(feat['properties']), 'fillOpacity': 0.75},
        highlight_function=lambda feat: {'weight': 2, 'color': '#FFD54A'},
        tooltip=folium.GeoJsonTooltip(fields=alanlar, aliases=basliklar, localize=True, sticky=True),
    ).add_to(harita)


xs = [x for f in ozellikler for x, _ in f['geometry']['coordinates'][0]]
ys = [y for f in ozellikler for _, y in f['geometry']['coordinates'][0]]
hx0, hy0, hx1, hy1 = min(xs), min(ys), max(xs), max(ys)
_hafif = _hafiflet(ozellikler)
harita = folium.Map(location=[(hy0 + hy1) / 2, (hx0 + hx1) / 2], zoom_start=13, tiles=None, prefer_canvas=True)
folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(harita)
folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                  attr='Esri World Imagery', name='Uydu görüntüsü').add_to(harita)
_katman_ekle(harita, _hafif, 'Çatı tipi', lambda p: RENK_TIP.get(p['tip'], '#999999'), ac=True)
_katman_ekle(harita, _hafif, 'Oturtma güvenilirliği',
             lambda p: RENK_GUVENILIR if p['oturtma_orani'] >= ESIK_OTURTMA else RENK_SUPHELI)
_kamu_hafif = [f for f in _hafif if f['properties'].get('kamu')]
if _kamu_hafif:
    _katman_ekle(harita, _kamu_hafif, f'Kamu binaları ({len(_kamu_hafif)})', lambda p: RENK_KAMU,
                 alanlar=_TOOLTIP_ALAN_KAMU, basliklar=_TOOLTIP_BASLIK_KAMU)
folium.LayerControl(collapsed=False).add_to(harita)
harita.fit_bounds([[hy0, hx0], [hy1, hx1]])
HARITA_YOLU = f'{CALISMA}/cikti/cigli_catilar_{ETIKET}_harita.html'
harita.save(HARITA_YOLU)
print(f'harita: {HARITA_YOLU} ({os.path.getsize(HARITA_YOLU) / 1e6:.2f} MB, {len(ozellikler)} çatı)')
INDIR_HARITA = True
if INDIR_HARITA and COLAB:
    from google.colab import files
    files.download(HARITA_YOLU)
''')

md(r'''
## 16 · Sınırlılıklar

* **Görüntü:** Esri World Imagery; Çiğli dört ayrı çekimden (farklı uydu, tarih ve çözünürlük) oluşuyor. Karoların bu ölçekte kullanımı teknik deneme niteliğinde; lisanslı kaynakla yinelenmeli.
* **Doğrulama (ön ölçüm, 2026-09-12):** 540 çatılık örnek koşu üzerinde 9 tabakalı (çekim × alan × oturtma) n=109 görsel denetim yapıldı: tabaka ağırlıklı doğruluk **%82,3** (belirsizler hata sayılırsa) – **%90,6** (belirsizler hariç). `oturtma_orani < 0,4` bandında doğruluk %17,1, normal bantta %87,9 → **bu bayrak ayırıcı, şüpheli çatılar ayrı raporlanmalı.** Zayıf halkalar: <150 m² %72,6 · düz/teras %61,5 · LG05 %56,2 (n=12). Notlar model tarafından verildi; tez için bağımsız insan etiketlemesi gerekir (`scripts/dogrulama_ornek.py` + `scripts/dogrulama_metrik.py`, kontak sayfaları `notebooks/dogrulama/`). Yükseklik ve çatı tipi için ayrı doğrulama hâlâ yok.
* **Güvenilmez çekim:** Gölge yönü ölçülemeyen çekimlerde yükseklik ölçülmez, sınıf medyanı kullanılır; kiremit dışı eğimli sınıf ve fotometrik eğim o çekimlerde üretilmez.
* **Eğim:** Tek görüntüden ölçülemez; üretimde 17–33° bandı kullanıldı. Google Solar API ya da LiDAR ile doğrulanmalı.
* **Çatı oturtma:** Çok yüksek binalarda kayma ±8 m'lik aramayı aşabilir; `oturtma_orani` < 0,4 olan çatılar şüpheli sayılmalı (koyu çatılarda bu ölçüt de yanılabilir).
* **Büyük yapılar:** 1000 px'ten (≈ 230 m) büyük yapılar SAM'e verilmedi; çatıları oturtulmuş ayak izinden.
* **Gölgelenme:** Ağaçlar, çatı üstü yapılar ve arazi yok; binalar tek yükseklikte blok. Tampon dışındaki yapılar engel olarak yok.
* **Üretim:** Kullanılabilir oranlar, doğrudan ışınım payı ve eğim bandı varsayım; sonuçlar bant olarak okunmalı.
''')

nb = nbf.v4.new_notebook(cells=hucreler, metadata={
    'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'},
    'language_info': {'name': 'python'},
    'accelerator': 'GPU',
    'colab': {'provenance': [], 'toc_visible': True, 'gpuType': 'T4'},
})
for c in nb.cells:
    if c.cell_type == 'code':
        c.source = c.source.replace('__ONCEKI__', ONCEKI).replace('__KAMU__', KAMU_GOMULU)
hedef = yol('notebooks', 'CatiGunes_Cigli_Segmentasyon.ipynb')
nbf.write(nb, hedef)
print('defter:', hedef, os.path.getsize(hedef), 'bayt')

if '--kos' in sys.argv:
    from nbclient import NotebookClient
    try:
        ornek = int(sys.argv[sys.argv.index('--kos') + 1])
    except (IndexError, ValueError):
        ornek = 20
    dizin = yol('notebooks', 'cigli_kosu')
    os.makedirs(os.path.join(dizin, 'calisma', 'modeller'), exist_ok=True)
    os.makedirs(os.path.join(dizin, 'calisma', 'karo'), exist_ok=True)
    kaynak = yol('notebooks', 'seg_kosu', 'calisma', 'modeller', 'sam_vit_b_01ec64.pth')
    hedef_ag = os.path.join(dizin, 'calisma', 'modeller', 'sam_vit_b_01ec64.pth')
    if os.path.exists(kaynak) and not os.path.exists(hedef_ag):
        shutil.copy(kaynak, hedef_ag)
    for f in glob.glob(yol('cache', 'evka5', '19_*.jpg')) + glob.glob(yol('notebooks', 'seg_kosu', 'calisma', 'karo', '19_*.jpg')):
        h_ = os.path.join(dizin, 'calisma', 'karo', os.path.basename(f))
        if not os.path.exists(h_):
            shutil.copy(f, h_)
    kosu = nbf.read(hedef, as_version=4)
    kamu_kip = '--kamu' in sys.argv
    for c in kosu.cells:
        if c.cell_type != 'code':
            continue
        if kamu_kip:
            c.source = c.source.replace('HEDEF_KAMU = False', 'HEDEF_KAMU = True')
        elif 'ORNEK_BINA = None' in c.source:
            c.source = c.source.replace('ORNEK_BINA = None', f'ORNEK_BINA = {ornek}')
    t0 = time.time()
    try:
        NotebookClient(kosu, timeout=7200, kernel_name='python3', resources={'metadata': {'path': dizin}}).execute()
    finally:
        ciktili = yol('notebooks', 'CatiGunes_Cigli_Segmentasyon_ornek_ciktili.ipynb')
        nbf.write(kosu, ciktili)
        print('ciktili:', ciktili, '| sure %.0f s' % (time.time() - t0))
        for i, c in enumerate(kosu.cells):
            if c.cell_type != 'code':
                continue
            for o in c.get('outputs', []):
                if o.get('output_type') == 'stream':
                    print('--- [%d] %s' % (i, o['text'][-3000:]))
                elif o.get('output_type') in ('execute_result', 'display_data'):
                    dd = o.get('data', {})
                    if 'image/png' in dd:
                        print('--- [%d] grafik %d kB' % (i, len(dd['image/png']) // 1024))
                    elif 'text/plain' in dd:
                        print('--- [%d] %s' % (i, dd['text/plain'][:2000]))
                elif o.get('output_type') == 'error':
                    print('--- [%d] HATA %s: %s' % (i, o['ename'], o['evalue']))
