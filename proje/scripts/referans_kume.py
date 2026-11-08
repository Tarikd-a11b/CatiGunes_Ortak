# -*- coding: utf-8 -*-
"""REFERANS KUME - SAM kalibrasyonu icin 'iki kaynagin mutabik oldugu' binalar.

NEDEN: SAM'in hatasini olcmek icin guvenilir bir cetvel lazim. Evka-5'te SAM alani
MS ayak iziyle karsilastirilmisti (medyan oran 1,21) - ama 2026-09-10 capraz kontrolu
MS'in bitisik binalari birlestirdigini olctu. Yani hatali cetvelle olculmus bir hata.
SAM'in kendi hatasi ile cetvelin hatasi ayrilamiyor.

COZUM: Insan cizimi OSM ile makine uretimi MS'in AYNI binada AYNI alani soyledigi
yerlerde cetvel supheli degildir. Bu betik o binalari secer:
    - MS poligonunun temsili noktasi bir OSM poligonunun icinde
    - iki alanin orani 1 +- ALAN_TOLERANS icinde
    - mahalle A kademesinde (ortusme >= 0.65)
Cikan kume, SAM kalibrasyonunun referansi olur. SAM SADECE burada kosulup
duzeltme fonksiyonu uydurulur; Cigli'ye o fonksiyon uygulanir.

DIKKAT: Bu 'yer gercegi' (ground truth) DEGILDIR. Iki kaynak da goruntuden turetilmis;
ayni yonde yanilmalari mumkun. Yontemleri bagimsiz oldugu icin (elle sayisallastirma
karsi makine ogrenmesi) mutabakat anlamlidir, ama tezde bu sinir yazilmali.
Onerilen ek adim: kumeden rastgele ~50 bina elle sayisallastirilip yoklanmali.

Girdiler
  cache/mahalle_sinirlari.geojson
  cache/osm_binalar_cigli.geojsonl
  cache/ms_izmir_122100310.geojsonl
  cache/bolge_modelleri.csv            (mahalle kademeleri buradan)

Cikti
  cache/referans_kume.geojsonl         eslesen bina ciftleri + iki alan
  cache/referans_kume_ozet.json        buyukluk/doku dagilimi
"""
import csv, io, json, math, os, sys, time, unicodedata
import numpy as np
from shapely.geometry import shape
from shapely.strtree import STRtree
from shapely.ops import transform
from pyproj import Transformer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)
to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32635', always_xy=True).transform

KALIBRASYON_ILCE = 'KARŞIYAKA'      # temiz doku: kalibrasyon burada
UYGULAMA_ILCE    = 'ÇİĞLİ'          # duzeltme buraya uygulanacak
ALAN_TOLERANS    = 0.15             # iki kaynak alani +- %15 icinde uyusmali
MIN_ALAN, MAX_ALAN = 25.0, 8000.0
KOMSU_YARICAP    = 15.0             # m; bu mesafedeki komsu sayisi = doku yogunlugu


def sadelestir(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')).lower()
    return ''.join(ch for ch in s if ch.isalnum())


# ---------------------------------------------------------------- kademeler
kademe = {}
for r in csv.DictReader(io.open(yol('cache/bolge_modelleri.csv'), encoding='utf-8-sig'),
                        delimiter=';'):
    kademe[(sadelestir(r['ilce']), sadelestir(r['mahalle']))] = r['kademe']

fc = json.load(open(yol('cache/mahalle_sinirlari.geojson'), encoding='utf-8'))
M = []
for f in fc['features']:
    p = f['properties']
    if p['ilce'] not in (KALIBRASYON_ILCE, UYGULAMA_ILCE):
        continue
    M.append(dict(ilce=p['ilce'], mahalle=p['mahalle'], geom=shape(f['geometry']),
                  kademe=kademe.get((sadelestir(p['ilce']), sadelestir(p['mahalle'])), '?')))
AGAC = STRtree([m['geom'] for m in M])
print('%d mahalle (%s + %s)' % (len(M), KALIBRASYON_ILCE, UYGULAMA_ILCE))


def hangi(g):
    c = g.representative_point()
    for i in AGAC.query(c):
        m = M[int(i)]
        if m['geom'].contains(c):
            return m
    return None


# ---------------------------------------------------------------- OSM
osm, osm_utm = [], []
with io.open(yol('cache/osm_binalar_cigli.geojsonl'), encoding='utf-8') as f:
    for satir in f:
        g = shape(json.loads(satir)['geometry'])
        osm.append(g)
print('OSM poligonu: %d' % len(osm))
OSM_AGAC = STRtree(osm)
osm_alan = {}


# ---------------------------------------------------------------- eslestirme
cift = []
t0 = time.time(); n = 0
with io.open(yol('cache/ms_izmir_122100310.geojsonl'), encoding='utf-8') as f:
    for satir in f:
        n += 1
        try:
            gm = shape(json.loads(satir)['geometry'])
        except Exception:
            continue
        m = hangi(gm)
        if m is None:
            continue
        a_ms = transform(to_utm, gm).area
        if not (MIN_ALAN <= a_ms <= MAX_ALAN):
            continue
        c = gm.representative_point()
        eslesen = None
        for i in OSM_AGAC.query(c):
            if osm[int(i)].contains(c):
                eslesen = int(i); break
        if eslesen is None:
            continue
        if eslesen not in osm_alan:
            osm_alan[eslesen] = transform(to_utm, osm[eslesen]).area
        a_osm = osm_alan[eslesen]
        if not (MIN_ALAN <= a_osm <= MAX_ALAN):
            continue
        oran = a_ms / a_osm
        cift.append(dict(ilce=m['ilce'], mahalle=m['mahalle'], kademe=m['kademe'],
                         lon=round(c.x, 6), lat=round(c.y, 6),
                         a_ms=round(a_ms, 1), a_osm=round(a_osm, 1),
                         oran=round(oran, 4), osm_i=eslesen))
        if n % 100000 == 0:
            print('  %d/391215 (%.0f s)' % (n, time.time() - t0))
print('ortusen MS-OSM cifti: %d  (%.0f s)' % (len(cift), time.time() - t0))

# Doku yogunlugu: KOMSU_YARICAP icindeki OSM bina sayisi (kendisi haric).
# Derece cinsinden yaricap; 38.5 enleminde boylam 1 derece ~ 87 km, enlem ~ 111 km.
# Dairenin enlem yonunde dogru olmasi yeterli (kaba doku olcusu).
print('doku yogunlugu hesaplaniyor...')
r_der = KOMSU_YARICAP / 111000.0
for c in cift:
    p = osm[c['osm_i']].representative_point()
    c['komsu'] = max(0, len(OSM_AGAC.query(p.buffer(r_der))) - 1)

# ---------------------------------------------------------------- referans kume
ref = [c for c in cift
       if c['ilce'] == KALIBRASYON_ILCE and c['kademe'] == 'A'
       and abs(c['oran'] - 1.0) <= ALAN_TOLERANS]
print('\n=== REFERANS KUME (%s, kademe A, |oran-1| <= %.2f) ==='
      % (KALIBRASYON_ILCE, ALAN_TOLERANS))
print('  bina sayisi : %d' % len(ref))
if not ref:
    sys.exit('Referans kume bos - tolerans veya kademe kosulu gozden gecirilmeli.')

a = np.array([r['a_osm'] for r in ref])
k = np.array([r['komsu'] for r in ref])
print('  alan        : medyan %.0f m2  (%.0f - %.0f)' % (np.median(a), a.min(), a.max()))
print('  komsu (%.0f m): medyan %.0f  (0 komsulu: %%%.0f)'
      % (KOMSU_YARICAP, np.median(k), 100 * (k == 0).mean()))
print('  mahalle     : %d farkli' % len({r['mahalle'] for r in ref}))

print('\n  BUYUKLUK DILIMLERI (SAM hatasi boyuta bagli - Evka-5 bulgusu)')
dilim = [(25, 75), (75, 150), (150, 300), (300, 800), (800, 8000)]
for lo, hi in dilim:
    g = [r for r in ref if lo <= r['a_osm'] < hi]
    print('    %5d - %5d m2 : %5d bina  (%%%.0f)' % (lo, hi, len(g), 100 * len(g) / len(ref)))

print('\n  DOKU DILIMLERI (komsu sayisi = bitisiklik)')
for lo, hi, ad in [(0, 1, 'mustakil'), (1, 3, 'seyrek'), (3, 6, 'orta'), (6, 999, 'sik')]:
    g = [r for r in ref if lo <= r['komsu'] < hi]
    print('    %-9s (%d-%s komsu) : %5d bina  (%%%.0f)'
          % (ad, lo, hi - 1 if hi < 999 else '+', len(g), 100 * len(g) / len(ref)))

# uygulama bolgesinin dokusu referansla ortusuyor mu?
uyg = [c for c in cift if c['ilce'] == UYGULAMA_ILCE]
print('\n=== TRANSFER EDILEBILIRLIK KONTROLU ===')
print('  Kalibrasyon kumesi ile uygulama bolgesi ayni dokuya mi sahip?')
au = np.array([c['a_osm'] for c in uyg]); ku = np.array([c['komsu'] for c in uyg])
print('  %-22s alan medyani %5.0f m2   komsu medyani %.0f'
      % (KALIBRASYON_ILCE + ' referans', np.median(a), np.median(k)))
print('  %-22s alan medyani %5.0f m2   komsu medyani %.0f'
      % (UYGULAMA_ILCE + ' tumu', np.median(au), np.median(ku)))
ort = 0
for lo, hi in dilim:
    p1 = sum(1 for r in ref if lo <= r['a_osm'] < hi) / len(ref)
    p2 = sum(1 for r in uyg if lo <= r['a_osm'] < hi) / max(len(uyg), 1)
    ort += min(p1, p2)
print('  buyukluk dagilimi ortusmesi: %%%.0f' % (100 * ort))
print('  -> Ortusme dusukse Cigli\'nin bazi bina siniflari icin kalibrasyon YOK demektir;')
print('     o dilimlerde duzeltme uygulanamaz, ayri raporlanmali.')

# ---------------------------------------------------------------- cikti
with io.open(yol('cache/referans_kume.geojsonl'), 'w', encoding='utf-8') as f:
    for r in ref:
        f.write(json.dumps({k2: v for k2, v in r.items() if k2 != 'osm_i'},
                           ensure_ascii=False) + '\n')
json.dump(dict(
    uretim=time.strftime('%Y-%m-%d %H:%M'),
    kalibrasyon_ilce=KALIBRASYON_ILCE, uygulama_ilce=UYGULAMA_ILCE,
    alan_tolerans=ALAN_TOLERANS, komsu_yaricap_m=KOMSU_YARICAP,
    ortusen_cift=len(cift), referans_bina=len(ref),
    referans_mahalle=sorted({r['mahalle'] for r in ref}),
    alan_medyan=float(np.median(a)), komsu_medyan=float(np.median(k)),
    buyukluk_dilimleri={'%d-%d' % (lo, hi): sum(1 for r in ref if lo <= r['a_osm'] < hi)
                        for lo, hi in dilim},
    dagilim_ortusmesi=round(ort, 3),
    not_='Yer gercegi degil: iki bagimsiz kaynagin mutabakati. ~50 bina elle yoklanmali.'),
    io.open(yol('cache/referans_kume_ozet.json'), 'w', encoding='utf-8'),
    ensure_ascii=False, indent=1)
print('\n-> cache/referans_kume.geojsonl  |  cache/referans_kume_ozet.json')
