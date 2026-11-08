# -*- coding: utf-8 -*-
"""FAZ 2-3: SAM cati maskelerinden uretim potansiyeli (PVGIS) ve oncelik siralamasi.

Girdi : cache/evka5_sam_sonuc.json  (202 bina, sam_alan / ayak_alan / azimut / lon-lat)
        data/osm_izmir_kamu.json    (Izmir geneli OSM kamu binalari)
Cikti : cache/faz2_tablo.csv, cache/faz2_sonuc.geojson, cache/pvgis_tablo.json

YONTEM NOTLARI (teze girecek, gizlenmeyecek varsayimlar)
 1. EGIM elimizde yok (D6 acik). Nokta tahmin yerine SENARYO BANDI uretiliyor:
    duz cati 0 derece / besik cati 30 derece.
 2. AZIMUT'ta 180 derece belirsizlik var (D5). Egimli senaryoda binanin iki olasi
    yonu de PVGIS'e soruluyor, sonuc alt-ust bant olarak veriliyor.
 3. PVGIS ozgul verimi (kWh/kWp) 1.2 km'lik pilot alanda pratikte sabittir; bu yuzden
    202 bina icin degil, mahalle merkezinde (egim x yon) izgarasi icin sorulup
    interpolasyonla dagitiliyor. Sorgu sayisi 14, bina basina degil.
 4. ALAN: SAM kucuk binalarda ayak izini sisiriyor (yerel bulgu, oran 1.56). Esik
    altinda ayak izi alani, ustunde SAM alani kullaniliyor; secim sutunda raporlanir.
"""
import json, math, os, time
import numpy as np, requests

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)

# --- 1. varsayimlar -----------------------------------------------------------
M2_PER_KWP     = 6.0        # ~200 W/m2 modul
KAYIP          = 14         # PVGIS sistem kaybi %
KULLANILABILIR = {0: 0.55, 30: 0.35}   # duz: sira araligi+kenar / besik: tek yuz
ALAN_ESIK      = 150.0      # m2; altinda SAM sisiriyor -> ayak izi kullan
MIN_ALAN       = 25.0       # m2; altini eleriz (gurultu)
MAX_ALAN       = 8000.0
KAMU_MESAFE    = 40.0       # m; kamu POI'sini catiya eslestirme yaricapi
HANE_TUKETIM   = 3600.0     # kWh/yil, kaba kabul

# --- 2. veri ------------------------------------------------------------------
catilar = json.load(open(yol('cache/evka5_sam_sonuc.json'), encoding='utf-8'))
print('SAM sonucu: %d bina' % len(catilar))

def alan_sec(c):
    """Boyut kosullu alan secimi (yontem notu 4)."""
    if c['ayak_alan'] < ALAN_ESIK:
        return c['ayak_alan'], 'ayak_izi'
    return c['sam_alan'], 'sam'

kayit = []
for c in catilar:
    a, kaynak = alan_sec(c)
    if not (MIN_ALAN <= a <= MAX_ALAN):
        continue
    kayit.append(dict(i=c['i'], lon=c['lon'], lat=c['lat'], alan=a, alan_kaynak=kaynak,
                      sam_alan=c['sam_alan'], ayak_alan=c['ayak_alan'], iou=c['iou'],
                      azimut=c.get('azimut'), doluluk=c.get('doluluk')))
print('alan filtresinden gecen: %d  (elenen %d)' % (len(kayit), len(catilar) - len(kayit)))

MERKEZ_LON = float(np.mean([k['lon'] for k in kayit]))
MERKEZ_LAT = float(np.mean([k['lat'] for k in kayit]))

# --- 3. PVGIS izgarasi --------------------------------------------------------
PVGIS = 'https://re.jrc.ec.europa.eu/api/v5_3/PVcalc'
PV_CACHE = yol('cache/pvgis_tablo.json')

def pvgis_ozgul(lat, lon, egim, aspect):
    """1 kWp icin yillik kWh (PVGIS aspect: 0=guney, -90=dogu, +90=bati)."""
    r = requests.get(PVGIS, params=dict(lat=round(lat, 4), lon=round(lon, 4), peakpower=1,
                     loss=KAYIP, angle=egim, aspect=aspect, outputformat='json'), timeout=90)
    r.raise_for_status()
    return float(r.json()['outputs']['totals']['fixed']['E_y'])

if os.path.exists(PV_CACHE):
    IZGARA = {tuple(float(x) for x in k.split('|')): v
              for k, v in json.load(open(PV_CACHE)).items()}
    print('PVGIS izgarasi onbellekten: %d nokta' % len(IZGARA))
else:
    IZGARA = {}
    t0 = time.time()
    IZGARA[(0.0, 0.0)] = pvgis_ozgul(MERKEZ_LAT, MERKEZ_LON, 0, 0)
    print('  PVGIS egim  0 (yonsuz)   -> %.0f kWh/kWp' % IZGARA[(0.0, 0.0)])
    for asp in range(-180, 181, 30):
        v = pvgis_ozgul(MERKEZ_LAT, MERKEZ_LON, 30, asp)
        IZGARA[(30.0, float(asp))] = v
        print('  PVGIS egim 30 aspect %+4d -> %.0f kWh/kWp' % (asp, v))
    json.dump({'%s|%s' % k: v for k, v in IZGARA.items()}, open(PV_CACHE, 'w'))
    print('PVGIS izgarasi %d sorgu / %.0f s' % (len(IZGARA), time.time() - t0))

def sar(a):
    """Aciyi -180..180 araligina getirir."""
    return ((a + 180.0) % 360.0) - 180.0

def ozgul(egim, aspect):
    if egim == 0:
        return IZGARA[(0.0, 0.0)]
    a = sar(aspect)
    dusuk = math.floor(a / 30.0) * 30.0
    t = (a - dusuk) / 30.0
    v0 = IZGARA[(float(egim), sar(dusuk))]
    v1 = IZGARA[(float(egim), sar(dusuk + 30.0))]
    return v0 * (1 - t) + v1 * t

# --- 4. bina bazinda uretim ---------------------------------------------------
for k in kayit:
    kwp_duz = k['alan'] * KULLANILABILIR[0] / M2_PER_KWP
    k['kWp_duz'] = kwp_duz
    k['kWh_duz'] = kwp_duz * ozgul(0, 0)

    kwp_eg = k['alan'] * KULLANILABILIR[30] / M2_PER_KWP
    k['kWp_egimli'] = kwp_eg
    if k['azimut'] is None:
        k['kWh_egimli_alt'] = k['kWh_egimli_ust'] = kwp_eg * ozgul(30, 0)
        k['azimut_a'] = k['azimut_b'] = None
    else:
        a1 = k['azimut'] % 360.0               # pusula azimutu (0=kuzey, 180=guney)
        a2 = (a1 + 180.0) % 360.0
        v1 = kwp_eg * ozgul(30, a1 - 180.0)    # PVGIS aspect = pusula - 180
        v2 = kwp_eg * ozgul(30, a2 - 180.0)
        k['azimut_a'], k['azimut_b'] = a1, a2
        k['kWh_egimli_alt'], k['kWh_egimli_ust'] = min(v1, v2), max(v1, v2)

    k['kWh_alt']  = min(k['kWh_duz'], k['kWh_egimli_alt'])
    k['kWh_ust']  = max(k['kWh_duz'], k['kWh_egimli_ust'])
    k['kWh_orta'] = 0.5 * (k['kWh_alt'] + k['kWh_ust'])

# --- 5. kamu binasi eslestirmesi ---------------------------------------------
kamu_ham = json.load(open(yol('data/osm_izmir_kamu.json'), encoding='utf-8'))['elements']
LON0 = min(k['lon'] for k in kayit) - 0.002; LON1 = max(k['lon'] for k in kayit) + 0.002
LAT0 = min(k['lat'] for k in kayit) - 0.002; LAT1 = max(k['lat'] for k in kayit) + 0.002

OZEL_TIP = {'school': 'okul', 'kindergarten': 'anaokulu', 'hospital': 'hastane',
            'clinic': 'saglik', 'doctors': 'saglik', 'pharmacy': 'eczane',
            'townhall': 'belediye', 'community_centre': 'toplum merkezi',
            'library': 'kutuphane', 'university': 'universite', 'college': 'okul',
            'social_facility': 'sosyal tesis'}

def poi_konum(e):
    if e['type'] == 'node':
        return e.get('lon'), e.get('lat')
    c = e.get('center') or {}
    return c.get('lon'), c.get('lat')

kamu = []
for e in kamu_ham:
    lon, lat = poi_konum(e)
    if lon is None or not (LON0 <= lon <= LON1 and LAT0 <= lat <= LAT1):
        continue
    t = e.get('tags', {})
    tur = OZEL_TIP.get(t.get('amenity')) or OZEL_TIP.get(t.get('healthcare')) or t.get('amenity')
    kamu.append(dict(lon=lon, lat=lat, tur=tur, ad=t.get('name', '(isimsiz)')))
print('pilot alandaki OSM kamu POI: %d' % len(kamu))

MDEG_LAT = 111320.0
MDEG_LON = 111320.0 * math.cos(math.radians(MERKEZ_LAT))
for k in kayit:
    k['kamu'] = 0; k['kamu_tur'] = ''; k['kamu_ad'] = ''
eslesen = 0
for p in kamu:
    en_iyi, en_kisa = None, 1e9
    for k in kayit:
        d = math.hypot((k['lon'] - p['lon']) * MDEG_LON, (k['lat'] - p['lat']) * MDEG_LAT)
        if d < en_kisa:
            en_kisa, en_iyi = d, k
    if en_iyi is not None and en_kisa <= KAMU_MESAFE:
        en_iyi['kamu'] = 1
        en_iyi['kamu_tur'] = (en_iyi['kamu_tur'] + ',' + str(p['tur'])).strip(',')
        en_iyi['kamu_ad'] = (en_iyi['kamu_ad'] + ' | ' + str(p['ad'])).strip(' |')
        eslesen += 1
print('kamu POI %d cati ile eslesti (%d cati kamu isaretli)'
      % (eslesen, sum(k['kamu'] for k in kayit)))

# --- 6. oncelik skoru + duyarlilik -------------------------------------------
def normalize(x):
    x = np.asarray(x, float); r = x.max() - x.min()
    return np.zeros_like(x) if r == 0 else (x - x.min()) / r

def yuzdelik(x):
    """Sira-tabanli (yuzdelik) normalizasyon. Min-max, tek bir dev cati yuzunden
    binalarin %95'ini 0-0.1 araligina sikistiriyor; agirliklar o zaman siralamayi
    degistiremiyor ve duyarlilik analizi yanlis olarak 'saglam' gorunuyor."""
    x = np.asarray(x, float)
    sira = np.empty(len(x), float)
    sira[np.argsort(x)] = np.arange(len(x))
    return sira / max(len(x) - 1, 1)

kWh = [k['kWh_orta'] for k in kayit]
teknik_mm = normalize(kWh)
teknik = yuzdelik(kWh)            # birincil: sira-tabanli
toplum = np.array([float(k['kamu']) for k in kayit])
for k, a, b in zip(kayit, teknik, teknik_mm):
    k['teknik_yuzdelik'] = float(a); k['teknik_minmax'] = float(b)

AGIRLIK = {'sadece teknik (1.00/0.00)':    (1.00, 0.00),
           'AHP benzeri (0.60/0.40)':      (0.60, 0.40),
           'esit (0.50/0.50)':             (0.50, 0.50),
           'toplum agirlikli (0.40/0.60)': (0.40, 0.60)}

siralamalar = {}
for ad, (wt, ws) in AGIRLIK.items():
    skor = wt * teknik + ws * toplum
    for k, s in zip(kayit, skor):
        k['skor_' + ad] = float(s)
    siralamalar[ad] = [kayit[j]['i'] for j in np.argsort(-skor)]

def kendall_tau(a, b):
    """a listesindeki ogelerin b'deki sirasina gore uyum katsayisi."""
    idx = {v: i for i, v in enumerate(b)}
    ort = [x for x in a if x in idx]
    n = len(ort); uy = ters = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = idx[ort[i]] - idx[ort[j]]
            if s < 0: uy += 1
            elif s > 0: ters += 1
    return (uy - ters) / max(uy + ters, 1)

# --- 7. rapor -----------------------------------------------------------------
alan = np.array([k['alan'] for k in kayit])
T_alt = sum(k['kWh_alt'] for k in kayit)
T_ust = sum(k['kWh_ust'] for k in kayit)
T_ort = sum(k['kWh_orta'] for k in kayit)
print('\n=== FAZ 2 - URETIM POTANSIYELI (Evka-5 pilot) ===')
print('  cati sayisi          : %d' % len(kayit))
print('  toplam cati alani    : {:,.0f} m2'.format(alan.sum()))
print('  PVGIS ozgul verim    : duz(0) %.0f | guney(30) %.0f | kuzey(30) %.0f kWh/kWp'
      % (ozgul(0, 0), ozgul(30, 0), ozgul(30, 180)))
print('  kurulu guc bandi     : %.0f - %.0f kWp'
      % (sum(k['kWp_egimli'] for k in kayit), sum(k['kWp_duz'] for k in kayit)))
print('  yillik uretim bandi  : %.2f - %.2f GWh/yil' % (T_alt / 1e6, T_ust / 1e6))
print('  bant genisligi       : ust/alt = %.2fx  <- egim+yon belirsizliginin bedeli'
      % (T_ust / T_alt))
print('  ~%.0f hane esdegeri (%.0f kWh/yil kabulu)' % (T_ort / HANE_TUKETIM, HANE_TUKETIM))

print('\n=== FAZ 3 - ONCELIK: agirliklar listeyi degistiriyor mu? ===')
ad0 = 'AHP benzeri (0.60/0.40)'
ilk20 = {ad: s[:20] for ad, s in siralamalar.items()}
print('  normalizasyon: sira-tabanli (yuzdelik)')
for ad in AGIRLIK:
    ortak = len(set(ilk20[ad]) & set(ilk20[ad0]))
    print('  %-30s ilk-20 ortak=%2d/20  tau=%+.2f'
          % (ad, ortak, kendall_tau(ilk20[ad], siralamalar[ad0])))

# ayni sweep, min-max normalizasyonla: normalizasyon secimi sonucu degistiriyor mu?
sira_mm = {}
for ad, (wt, ws) in AGIRLIK.items():
    s = wt * teknik_mm + ws * toplum
    sira_mm[ad] = [kayit[j]['i'] for j in np.argsort(-s)]
print('  normalizasyon: min-max (karsilastirma)')
for ad in AGIRLIK:
    ortak = len(set(sira_mm[ad][:20]) & set(sira_mm[ad0][:20]))
    print('  %-30s ilk-20 ortak=%2d/20  tau=%+.2f'
          % (ad, ortak, kendall_tau(sira_mm[ad][:20], sira_mm[ad0])))
ortak_norm = len(set(ilk20[ad0]) & set(sira_mm[ad0][:20]))
print('  >> AYNI agirlikta iki normalizasyon ilk-20 ortak = %d/20 '
      '(normalizasyon secimi agirliklardan daha belirleyici olabilir)' % ortak_norm)

print('\n  --- %s ilk 10 ---' % ad0)
en = sorted(kayit, key=lambda k: -k['skor_' + ad0])[:10]
print('  %2s %8s %13s %5s  %s' % ('#', 'alan m2', 'kWh/yil orta', 'kamu', 'ad'))
for n, k in enumerate(en, 1):
    print('  %2d %8.0f %13.0f %5s  %s'
          % (n, k['alan'], k['kWh_orta'], 'EVET' if k['kamu'] else '-', k['kamu_ad'][:44]))

# --- 8. cikti -----------------------------------------------------------------
sutun = ['i', 'lon', 'lat', 'alan', 'alan_kaynak', 'sam_alan', 'ayak_alan', 'iou',
         'azimut_a', 'azimut_b', 'kWp_duz', 'kWh_duz', 'kWp_egimli',
         'kWh_egimli_alt', 'kWh_egimli_ust', 'kWh_alt', 'kWh_orta', 'kWh_ust',
         'kamu', 'kamu_tur', 'kamu_ad'] + ['skor_' + a for a in AGIRLIK]
with open(yol('cache/faz2_tablo.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    f.write(';'.join(sutun) + '\n')
    for k in sorted(kayit, key=lambda k: -k['skor_' + ad0]):
        f.write(';'.join(str(k.get(s, '')).replace(';', ',') for s in sutun) + '\n')

ozellik = [{'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [k['lon'], k['lat']]},
            'properties': {s: k.get(s) for s in sutun}} for k in kayit]
json.dump({'type': 'FeatureCollection', 'features': ozellik},
          open(yol('cache/faz2_sonuc.geojson'), 'w', encoding='utf-8'), ensure_ascii=False)
print('\n-> cache/faz2_tablo.csv  |  cache/faz2_sonuc.geojson  |  cache/pvgis_tablo.json')
