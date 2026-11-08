# -*- coding: utf-8 -*-
"""BOLGE MODELLERI - Cigli + Karsiyaka icin uctan uca model kosusu.

Bu betik projenin uc modelini SIRAYLA kosar ve her birinin ciktisini ayri raporlar:

  MODEL 1  Cati alani      : bina ayak izi -> kullanilabilir cati alani
  MODEL 2  Uretim (fizik)  : PVGIS ozgul verim -> kWp ve kWh/yil BANDI
  MODEL 3  Oncelik (KKV)   : sira-tabanli normalizasyon + AHP agirliklari
                             -> uc EKSENLI skor + duyarlilik analizi

!! SEGMENTASYON (SAM) BU KOSUDA YOK. Cati alani ayak izinden geliyor, SAM
   maskesinden degil. Nedeni: lisansi temiz goruntu kaynagi bulunamadi
   (bkz. docs/2026-09-10_cigli_veri_kalitesi.md, bolum 3). SAM devreye girdiginde
   'alan_kaynak' sutunu degisecek, zincirin geri kalani aynen calisir.

!! ALAN BIR BANT. 2026-09-10 capraz kontrolu MS ayak izlerinin bitisik binalari
   birlestirdigini olctu (Cigli'de MS/OSM = 1,391). Bu yuzden tek bir alan degil,
   OSM (alt) - MS (ust) araligi tasiniyor. Uretim bandi = alan bandi x egim/yon bandi.

Girdiler
  cache/mahalle_sinirlari.geojson       54 mahalle siniri (Cigli 26 + Karsiyaka 27 + Menemen 1)
  cache/osm_binalar_cigli.geojsonl      OSM bina poligonlari (osm_capraz_kontrol.py uretir)
  cache/ms_izmir_122100310.geojsonl     Microsoft ayak izleri (391.215 bina)
  cache/acikveri/*.csv                  Izmir BB: nufus, bina, su, askida fatura
  cache/kamu_<ilce>.geojson             kamu binalari: cati alanli + mulkiyet
                                        siniflandirmali (scripts/kamu_binalari.py)
  cache/izka/sege_ilce.json             SEGE 2022 ilce skorlari
  cache/ses2023_ilce.csv                TUIK Sosyoekonomik Seviye 2023 (ilce)

Cikti
  cache/bolge_modelleri.csv             mahalle bazli tam tablo
  cache/bolge_modelleri.json            ayni veri + varsayimlar + meta
"""
import csv, io, json, math, os, sys, time, unicodedata
import numpy as np, requests
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from shapely.ops import transform
from pyproj import Transformer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)
to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32635', always_xy=True).transform

ILCELER = ['ÇİĞLİ', 'KARŞIYAKA']

# ---------------------------------------------------------------- varsayimlar
M2_PER_KWP   = 6.0                       # ~200 W/m2 modul verimi
KAYIP        = 14                        # PVGIS sistem kaybi %
KULLANILABILIR = {0: 0.55, 30: 0.35}     # duz cati: sira araligi+kenar / besik: tek yuz
MIN_ALAN     = 25.0                      # m2, altini ele (gurultu)
MAX_ALAN     = 8000.0                    # m2, ustunu ele (hatali dev poligon)
KAMU_YARICAP = 40.0                      # m, kamu POI'sini binaya eslestirme
HANE_TUKETIM = 1059.0 * 2.8              # kWh/yil: kisi basi mesken 1.059 kWh (MDA s.255) x hane 2,8 (BP s.89); eski kabul 3.600
ORTUSME_A, ORTUSME_B = 0.65, 0.50        # guvenilirlik kademe esikleri

# IHTIYAC ekseninin ic bilesenleri. SES ilce duzeyinde sabit oldugu icin
# (mahalle kirilimi yayimlanmiyor) agirligi bilerek kucuk tutuluyor - ekolojik
# yanilgi riski: ilce ortalamasi mahalle gercegini gizleyebiliyor.
IHTIYAC_AGIRLIK = {'askida': 0.40, 'su_ters': 0.40, 'ses_ters': 0.20}

AGIRLIK = {                              # (teknik, ihtiyac, erisim)
    'yalniz teknik':        (1.00, 0.00, 0.00),
    'AHP benzeri':          (0.50, 0.35, 0.15),
    'ihtiyac agirlikli':    (0.35, 0.50, 0.15),
    'esit':                 (0.34, 0.33, 0.33),
}
ANA = 'AHP benzeri'


def sadelestir(s):
    """Turkce duyarli eslestirme anahtari ('I'.lower() birlesik nokta uretir)."""
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')).lower()
    return ''.join(ch for ch in s if ch.isalnum())


def sayi(x, vars_=0.0):
    try:
        return float(str(x).replace('.', '').replace(',', '.')) if ',' in str(x) else float(x)
    except Exception:
        return vars_


def csv_oku(p):
    return list(csv.DictReader(io.open(yol(p), encoding='utf-8-sig'), delimiter=';'))


def baslik(n, s):
    print('\n' + '=' * 78)
    print('  %s' % s)
    print('=' * 78)


# ============================================================================
# 0. SINIRLAR
# ============================================================================
baslik(0, 'HAZIRLIK - mahalle sinirlari')
fc = json.load(open(yol('cache/mahalle_sinirlari.geojson'), encoding='utf-8'))
M = []
for f in fc['features']:
    p = f['properties']
    if p['ilce'] not in ILCELER:
        continue
    M.append(dict(ilce=p['ilce'], mahalle=p['mahalle'], geom=shape(f['geometry']),
                  km2=p['alan_km2'], lon=p['merkez_lon'], lat=p['merkez_lat'],
                  osm_n=0, osm_alan=0.0, ms_n=0, ms_alan=0.0, ms_eslesen=0,
                  kamu_n=0, kamu_liste=[]))
AGAC = STRtree([m['geom'] for m in M])
IDX = {(sadelestir(m['ilce']), sadelestir(m['mahalle'])): m for m in M}
for il in ILCELER:
    print('  %-12s %2d mahalle  %8.2f km2'
          % (il, sum(1 for m in M if m['ilce'] == il),
             sum(m['km2'] for m in M if m['ilce'] == il)))


def hangi(g):
    c = g.representative_point()
    for i in AGAC.query(c):
        m = M[int(i)]
        if m['geom'].contains(c):
            return m
    return None


def bul(ilce, mahalle):
    return IDX.get((sadelestir(ilce), sadelestir(mahalle)))


# ============================================================================
# MODEL 1 - CATI ALANI
# ============================================================================
baslik(1, 'MODEL 1 - CATI ALANI  (ayak izi -> kullanilabilir cati)')

osm = []
with io.open(yol('cache/osm_binalar_cigli.geojsonl'), encoding='utf-8') as f:
    for satir in f:
        osm.append(shape(json.loads(satir)['geometry']))
print('  OSM poligonu okundu    : %d' % len(osm))

for g in osm:
    m = hangi(g)
    if m is None:
        continue
    a = transform(to_utm, g).area
    if not (MIN_ALAN <= a <= MAX_ALAN):
        continue
    m['osm_n'] += 1; m['osm_alan'] += a

osm_agac = STRtree(osm)
t0 = time.time(); n = 0
with io.open(yol('cache/ms_izmir_122100310.geojsonl'), encoding='utf-8') as f:
    for satir in f:
        n += 1
        try:
            g = shape(json.loads(satir)['geometry'])
        except Exception:
            continue
        m = hangi(g)
        if m is None:
            continue
        a = transform(to_utm, g).area
        if not (MIN_ALAN <= a <= MAX_ALAN):
            continue
        m['ms_n'] += 1; m['ms_alan'] += a
        c = g.representative_point()
        for i in osm_agac.query(c):
            if osm[int(i)].contains(c):
                m['ms_eslesen'] += 1
                break
print('  MS ayak izi tarandi    : %d kayit, %.0f s' % (n, time.time() - t0))

# --- kademe + alan bandi ---
for m in M:
    m['ortusme'] = m['ms_eslesen'] / m['ms_n'] if m['ms_n'] else None
    m['kademe'] = ('A' if (m['ortusme'] or 0) >= ORTUSME_A else
                   'B' if (m['ortusme'] or 0) >= ORTUSME_B else 'C')
    # Alan tek sayi degil bant: OSM alt sinir, MS ust sinir (MS birlestirip sisiriyor)
    m['alan_alt'] = min(m['osm_alan'], m['ms_alan'])
    m['alan_ust'] = max(m['osm_alan'], m['ms_alan'])
    m['alan_orta'] = math.sqrt(max(m['alan_alt'], 1) * max(m['alan_ust'], 1))  # geometrik ort.
    m['alan_oran'] = (m['ms_alan'] / m['osm_alan']) if m['osm_alan'] else None

for il in ILCELER:
    g = [m for m in M if m['ilce'] == il]
    print('\n  %s' % il)
    print('    OSM bina / cati alani : %6d / %8.1f ha'
          % (sum(x['osm_n'] for x in g), sum(x['osm_alan'] for x in g) / 1e4))
    print('    MS  bina / cati alani : %6d / %8.1f ha'
          % (sum(x['ms_n'] for x in g), sum(x['ms_alan'] for x in g) / 1e4))
    print('    MS/OSM alan orani     : %6.3f' % (sum(x['ms_alan'] for x in g) /
                                                 max(sum(x['osm_alan'] for x in g), 1)))
    o = [x['ortusme'] for x in g if x['ortusme'] is not None]
    print('    ortusme medyani       : %6.3f  (kademe A/B/C = %d/%d/%d)'
          % (np.median(o), sum(1 for x in g if x['kademe'] == 'A'),
             sum(1 for x in g if x['kademe'] == 'B'),
             sum(1 for x in g if x['kademe'] == 'C')))


# ============================================================================
# MODEL 2 - URETIM (PVGIS)
# ============================================================================
baslik(2, 'MODEL 2 - URETIM  (PVGIS ozgul verim -> kWp, kWh/yil BANDI)')

PV_CACHE = yol('cache/pvgis_bolge.json')
pv = json.load(open(PV_CACHE)) if os.path.exists(PV_CACHE) else {}
yeni = 0


def ozgul(lat, lon, egim, aspect):
    """1 kWp icin yillik kWh. PVGIS aspect: 0=guney, 180=kuzey."""
    global yeni
    k = '%.3f|%.3f|%d|%d' % (lat, lon, egim, aspect)
    if k not in pv:
        r = requests.get('https://re.jrc.ec.europa.eu/api/v5_3/PVcalc',
                         params=dict(lat=round(lat, 3), lon=round(lon, 3), peakpower=1,
                                     loss=KAYIP, angle=egim, aspect=aspect,
                                     outputformat='json'), timeout=90)
        r.raise_for_status()
        pv[k] = float(r.json()['outputs']['totals']['fixed']['E_y'])
        yeni += 1
        time.sleep(0.25)
    return pv[k]


print('  mahalle basina 3 senaryo sorgulanacak (duz 0, guney 30, kuzey 30)')
for i, m in enumerate(M, 1):
    m['oz_duz']    = ozgul(m['lat'], m['lon'], 0, 0)
    m['oz_guney']  = ozgul(m['lat'], m['lon'], 30, 0)
    m['oz_kuzey']  = ozgul(m['lat'], m['lon'], 30, 180)
    if i % 10 == 0:
        print('    %d/%d ...' % (i, len(M)))
json.dump(pv, open(PV_CACHE, 'w'))
print('  PVGIS: %d yeni sorgu, %d onbellek kaydi' % (yeni, len(pv)))

for m in M:
    # ALT sinir : en kucuk alan (OSM) x egimli cati x kuzeye bakan yuz
    # UST sinir : en buyuk alan (MS)  x duz cati    x optimum yon
    kwp_alt = m['alan_alt'] * KULLANILABILIR[30] / M2_PER_KWP
    kwp_ust = m['alan_ust'] * KULLANILABILIR[0] / M2_PER_KWP
    m['kWp_alt'], m['kWp_ust'] = kwp_alt, kwp_ust
    m['kWh_alt'] = kwp_alt * m['oz_kuzey']
    m['kWh_ust'] = kwp_ust * m['oz_duz']
    # IKI AYRI MERKEZ OLCUSU - karistirilmamali:
    #  (a) bandin geometrik merkezi: ek varsayim gerektirmez, carpimsal bandin ortasi
    #  (b) en olasi yerlesim: orta alan x duz cati (Turkiye'de teras cati yaygin).
    #      Bu bandin ORTASI DEGILDIR; ust sinira yakin durur, oyle raporlanmali.
    m['kWh_gm'] = math.sqrt(max(m['kWh_alt'], 1) * m['kWh_ust'])
    kwp_olasi = m['alan_orta'] * KULLANILABILIR[0] / M2_PER_KWP
    m['kWp_olasi'] = kwp_olasi
    m['kWh_olasi'] = kwp_olasi * m['oz_duz']

for il in ILCELER:
    g = [m for m in M if m['ilce'] == il]
    alt = sum(x['kWh_alt'] for x in g); ust = sum(x['kWh_ust'] for x in g)
    gm = sum(x['kWh_gm'] for x in g); olasi = sum(x['kWh_olasi'] for x in g)
    print('\n  %s' % il)
    print('    PVGIS ozgul verim   : duz %.0f | guney30 %.0f | kuzey30 %.0f kWh/kWp (ort.)'
          % (np.mean([x['oz_duz'] for x in g]), np.mean([x['oz_guney'] for x in g]),
             np.mean([x['oz_kuzey'] for x in g])))
    print('    kurulu guc bandi    : %.0f - %.0f kWp' % (sum(x['kWp_alt'] for x in g),
                                                         sum(x['kWp_ust'] for x in g)))
    print('    YILLIK URETIM BANDI : %.2f - %.2f GWh/yil' % (alt / 1e6, ust / 1e6))
    print('      bandin geo. merkezi: %.2f GWh/yil  (ek varsayim yok)' % (gm / 1e6))
    print("      en olasi yerlesim  : %.2f GWh/yil  (teras cati; bant ortasi DEGIL,"
          " ust sinirin %%%.0f'i)" % (olasi / 1e6, 100 * olasi / ust))
    print('    bant genisligi      : %.2fx' % (ust / alt))
    print('    hane esdegeri (g.m.): ~%.0f hane' % (gm / HANE_TUKETIM))

T_alt = sum(m['kWh_alt'] for m in M); T_ust = sum(m['kWh_ust'] for m in M)
T_gm = sum(m['kWh_gm'] for m in M); T_olasi = sum(m['kWh_olasi'] for m in M)
print('\n  TOPLAM (iki ilce)     : %.2f - %.2f GWh/yil  (bant %.2fx)'
      % (T_alt / 1e6, T_ust / 1e6, T_ust / T_alt))
print('    geometrik merkez    : %.2f GWh/yil' % (T_gm / 1e6))
print('    en olasi yerlesim   : %.2f GWh/yil' % (T_olasi / 1e6))


# ============================================================================
# MODEL 3 - ONCELIK (cok kriterli karar verme)
# ============================================================================
baslik(3, 'MODEL 3 - ONCELIK  (uc eksen, sira-tabanli normalizasyon, AHP)')

# --- 3a. toplumsal veri ---
for r in csv_oku('cache/acikveri/mahalle_nufus.csv'):
    m = bul(r['ILCE_ADI'], r['MAHALLE_ADI'])
    if m:
        m['nufus'] = int(sayi(r['NUFUS_ERKEK_TOPLAM']) + sayi(r['NUFUS_KADIN_TOPLAM']))

for m in M:
    m.setdefault('nufus', 0)
    m['askida_n'] = 0
for r in csv_oku('cache/acikveri/askida_fatura.csv'):
    m = bul(r['ILCE'], r['MAHALLE'])
    if m:
        m['askida_n'] += int(sayi(r['BASVURU_SAYISI']))

# konut su tuketimi (gelir vekili): en son tam yil
kayit, yil_say = [], {}
with io.open(yol('cache/acikveri/mahalle_su_tuketim.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter=';'):
        if r['ABONELIK_GRUBU'].strip() != 'Konut':
            continue
        m = bul(r['ILCE'], r['MAHALLE'])
        if not m:
            continue
        y = r['YIL'].strip()
        yil_say[y] = yil_say.get(y, 0) + 1
        kayit.append((y, m, sayi(r['ABONE_ADEDI']), sayi(r['ORTALAMA_TUKETIM'])))
ust = max(yil_say.values())
SU_YIL = max(y for y, c in yil_say.items() if c >= 0.9 * ust)
for m in M:
    m['_ab'] = 0.0; m['_tk'] = 0.0
for y, m, ab, tk in kayit:
    if y == SU_YIL and ab > 0:
        m['_ab'] += ab; m['_tk'] += tk
for m in M:
    m['su_abone'] = m['_ab'] / 12.0 if m['_ab'] else None
    m['su_kisi'] = (m['_tk'] / m['_ab']) if m['_ab'] else None

# --- kamu binalari: ARTIK SAYIM DEGIL CATI ALANI -----------------------------
# Eski hal: data/osm_izmir_kamu.json'dan POI sayimi -> 400 m2 kres ile 6.000 m2
# spor salonu ayni agirlikta. Yeni hal: scripts/kamu_binalari.py'nin urettigi,
# cati alani hesaplanmis ve mulkiyeti siniflandirilmis kume.
# UC ONEMLI NOKTA:
#  - tesis poligonu degil ICINDEKI BINALAR sayiliyor (okul bahcesi cati degil)
#  - bir bina en fazla bir tesise sayiliyor (cok amacli bloklarda cift sayim vardi)
#  - yalnizca mulkiyet='kamu' giriyor; 'belirsiz' kamu SAYILMIYOR
for m in M:
    m['kamu_n'] = 0; m['kamu_cati'] = 0.0
    m['kamu_belirsiz_n'] = 0; m['kamu_belirsiz_cati'] = 0.0
kamu_dosya = 0
for il in ILCELER:
    p = yol('cache/kamu_%s.geojson' % sadelestir(il))
    if not os.path.exists(p):
        print('  !! %s icin kamu dosyasi YOK (once scripts/kamu_binalari.py kos)' % il)
        continue
    kamu_dosya += 1
    for f in json.load(open(p, encoding='utf-8'))['features']:
        pr = f['properties']
        m = bul(il, pr['mahalle'])
        if not m:
            continue
        if pr['mulkiyet'] == 'kamu':
            m['kamu_n'] += 1; m['kamu_cati'] += pr['cati_m2'] or 0
        elif pr['mulkiyet'] == 'belirsiz':
            m['kamu_belirsiz_n'] += 1; m['kamu_belirsiz_cati'] += pr['cati_m2'] or 0

# --- SES 2023 (ilce duzeyi) --------------------------------------------------
# Mahalle kirilimi yayimlanmiyor; ilce ortalamasi tum mahallelere ayni deger
# olarak dusuyor. Bu bir EKOLOJIK YANILGI riskidir: Karsiyaka'nin SES'i yuksek
# ama en alt gruptaki hane payi Cigli'ninkine cok yakin (%9,6 - %10,7).
# Bu yuzden agirligi kucuk tutuluyor ve etkisi ayrica raporlaniyor.
ses = {}
p = yol('cache/ses2023_ilce.csv')
if os.path.exists(p):
    for r in csv.DictReader(io.open(p, encoding='utf-8-sig'), delimiter=';'):
        if r['il'] == 'İzmir':
            ses[sadelestir(r['ilce'])] = float(r['ses'])
for m in M:
    m['ses'] = ses.get(sadelestir(m['ilce']))

for m in M:
    n = max(m['nufus'], 1)
    m['askida_bin'] = m['askida_n'] / n * 1000
    m['kamu_bin'] = m['kamu_n'] / n * 1000
    m['kamu_cati_bin'] = m['kamu_cati'] / n * 1000      # m2 kamu cati / 1000 kisi
    m['cati_kisi'] = m['alan_orta'] / n
print('  nufus verisi olan mahalle : %d/%d' % (sum(1 for m in M if m['nufus']), len(M)))
print('  su verisi (yil %s)        : %d/%d' % (SU_YIL, sum(1 for m in M if m['su_kisi']), len(M)))
print('  kamu dosyasi okunan ilce  : %d/%d' % (kamu_dosya, len(ILCELER)))
print('  kamu tesisi (mulkiyet=kamu): %d tesis, toplam cati %s m2'
      % (sum(m['kamu_n'] for m in M),
         format(int(sum(m['kamu_cati'] for m in M)), ',d').replace(',', '.')))
print('  belirsiz mulkiyet (SKORA GIRMIYOR): %d tesis, %s m2'
      % (sum(m['kamu_belirsiz_n'] for m in M),
         format(int(sum(m['kamu_belirsiz_cati'] for m in M)), ',d').replace(',', '.')))
print('  SES 2023 eslesen mahalle  : %d/%d' % (sum(1 for m in M if m['ses']), len(M)))
for il in ILCELER:
    d = [m['ses'] for m in M if m['ilce'] == il and m['ses']]
    if d:
        print('     %-11s SES %.2f (ilce duzeyi, tum mahallelere ayni deger)'
              % (il, d[0]))
print('  !! askida fatura fiilen 2020 (pandemi programi) - secilim yanliligi var,')
print('     tek basina yoksulluk olcusu degil, vekil gosterge olarak kullaniliyor.')


# --- 3b. normalizasyon ---
def spearman(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def yuzdelik(x):
    """Sira-tabanli normalizasyon. Min-max, tek bir dev mahalle yuzunden
    digerlerini 0-0.1'e sikistiriyor ve agirliklar siralamayi degistiremiyor
    (2026-09-09 bulgusu)."""
    x = np.asarray(x, float)
    s = np.empty(len(x), float)
    s[np.argsort(x, kind='mergesort')] = np.arange(len(x), dtype=float)
    for d in np.unique(x):            # esit degerler ayni yuzdeligi almali (2026-09-12)
        esit = x == d
        s[esit] = s[esit].mean()
    return s / max(len(x) - 1, 1)


kWh = [m['kWh_gm'] for m in M]   # sira-tabanli: merkez secimi siralamayi degistirmez
teknik = yuzdelik(kWh)

# IHTIYAC ekseni: askida fatura (yuksek = ihtiyac) + su tuketimi (dusuk = ihtiyac)
#                 + SES 2023 (dusuk = ihtiyac, ILCE duzeyinde sabit)
a_p = yuzdelik([m['askida_bin'] for m in M])
s_p = yuzdelik([-(m['su_kisi'] if m['su_kisi'] is not None else 0) for m in M])
ses_p = yuzdelik([-(m['ses'] if m['ses'] is not None else 0) for m in M])
ihtiyac = (IHTIYAC_AGIRLIK['askida'] * a_p + IHTIYAC_AGIRLIK['su_ters'] * s_p
           + IHTIYAC_AGIRLIK['ses_ters'] * ses_p)
ihtiyac_sessiz = 0.5 * a_p + 0.5 * s_p          # SES'siz surum, karsilastirma icin

# ERISIM ekseni AYRI. 2026-09-09'da olculdu: kamu binasi ile ihtiyac ters iliskili
# (Cigli'de rho = -0,44). Ayni terimde toplanirsa skor yatirimi ihtiyactan uzaklastiriyor.
# ARTIK SAYIM DEGIL ALAN: kamu cati m2 / 1000 kisi.
erisim = yuzdelik([m['kamu_cati_bin'] for m in M])
erisim_sayim = yuzdelik([m['kamu_bin'] for m in M])   # eski surum, karsilastirma icin

for m, t, i_, e in zip(M, teknik, ihtiyac, erisim):
    m['p_teknik'], m['p_ihtiyac'], m['p_erisim'] = float(t), float(i_), float(e)


print('\n  EKSENLER ARASI ILISKI (Spearman)')
# 2026-09-09'da Cigli tek basina rho = -0,47 vermisti. Ayni olcum iki ilce
# birlikte yapilinca ayni cikiyor mu? Olcek bagimliligi burada gorunur.
print('    --- HAM cift (2026-09-09 ile birebir ayni olcum): askida/1000 <-> kamu/1000 ---')
for _il in ILCELER + [None]:
    _g = [j for j, m in enumerate(M) if _il is None or m['ilce'] == _il]
    print('    %-11s %+.2f  (n=%d)' % (_il or 'iki ilce',
          spearman([M[j]['askida_bin'] for j in _g], [M[j]['kamu_bin'] for j in _g]), len(_g)))
_cig = [j for j, m in enumerate(M) if m['ilce'] == 'ÇİĞLİ']
_kar = [j for j, m in enumerate(M) if m['ilce'] == 'KARŞIYAKA']
_rc = spearman([M[j]['askida_bin'] for j in _cig], [M[j]['kamu_bin'] for j in _cig])
_rk = spearman([M[j]['askida_bin'] for j in _kar], [M[j]['kamu_bin'] for j in _kar])
print('    Cigli icin 2026-09-09 degeri -0,47 idi; %+.2f ile yeniden uruyor.' % _rc)
print('    Karsiyaka %+.2f -> ters iliski Cigli\'ye ozgu, evrensel degil.' % _rk)
print('    --- BILESIK ihtiyac ekseni (askida + ters su tuketimi) ile ---')
for _il in ILCELER:
    _g = [j for j, m in enumerate(M) if m['ilce'] == _il]
    print('    %-11s ihtiyac<->erisim %+.2f | su/kisi<->cati/kisi %+.2f  (n=%d)'
          % (_il, spearman(ihtiyac[_g], erisim[_g]),
             spearman([M[j]['su_kisi'] or 0 for j in _g], [M[j]['cati_kisi'] for j in _g]),
             len(_g)))
print('    --- iki ilce birlikte ---')
print('    ihtiyac <-> erisim  : %+.2f   <- ayri eksende tutulma gerekcesi'
      % spearman(ihtiyac, erisim))
print('    ihtiyac <-> teknik  : %+.2f' % spearman(ihtiyac, teknik))
print('    su/kisi <-> cati/kisi: %+.2f  (Sunter 2019 esitsizlik bulgusunun karsiligi)'
      % spearman([m['su_kisi'] or 0 for m in M], [m['cati_kisi'] for m in M]))

# --- 3c. agirlik supurmesi ---
sira = {}
for ad, (wt, wi, we) in AGIRLIK.items():
    sk = wt * teknik + wi * ihtiyac + we * erisim
    for m, s in zip(M, sk):
        m['skor_' + ad] = float(s)
    sira[ad] = [M[j]['mahalle'] + '|' + M[j]['ilce'] for j in np.argsort(-sk)]


def kendall(a, b):
    idx = {v: i for i, v in enumerate(b)}
    o = [x for x in a if x in idx]
    uy = ters = 0
    for i in range(len(o)):
        for j in range(i + 1, len(o)):
            d = idx[o[i]] - idx[o[j]]
            if d < 0: uy += 1
            elif d > 0: ters += 1
    return (uy - ters) / max(uy + ters, 1)


# --- yeni bilesenlerin siralamaya etkisi -------------------------------------
# SES eklemek ve kamu eksenini sayimdan alana cevirmek sonucu degistirdi mi?
# Degistirmiyorsa eklemenin savunulacak bir gerekcesi yok, bunu gizlememek lazim.
wt, wi, we = AGIRLIK[ANA]
ana_skor = wt * teknik + wi * ihtiyac + we * erisim


def _sira(sk):
    return [M[j]['mahalle'] + '|' + M[j]['ilce'] for j in np.argsort(-sk)]


print('\n  YENI BILESENLERIN ETKISI (%s agirlik seti)' % ANA)
_b = _sira(ana_skor)
for ad, sk in [('SES cikarilirsa', wt * teknik + wi * ihtiyac_sessiz + we * erisim),
               ('kamu ALAN yerine SAYIM', wt * teknik + wi * ihtiyac + we * erisim_sayim),
               ('ikisi de eski hali',
                wt * teknik + wi * ihtiyac_sessiz + we * erisim_sayim)]:
    _a = _sira(sk)
    print('    %-24s ilk10 ortak %2d/10  Kendall tau %+.2f'
          % (ad, len(set(_a[:10]) & set(_b[:10])), kendall(_a[:10], _b)))
print('    -> tau 1,00\'a yakinsa yeni bilesen siralamayi degistirmiyor demektir.')

print('\n  DUYARLILIK - agirliklar siralamayi degistiriyor mu?')
print('    %-20s %-10s %s' % ('agirlik seti', 'ilk10 ortak', 'Kendall tau (ANA setine gore)'))
for ad in AGIRLIK:
    ortak = len(set(sira[ad][:10]) & set(sira[ANA][:10]))
    print('    %-20s %2d/10       %+.2f' % (ad, ortak, kendall(sira[ad][:10], sira[ANA])))

print('\n  --- %s ile ilk 12 mahalle ---' % ANA)
print('  %2s %-9s %-20s %-3s %9s %7s %7s %7s' %
      ('#', 'ilce', 'mahalle', 'kad', 'GWh g.m.', 'teknik', 'ihtiyc', 'erisim'))
en = sorted(M, key=lambda m: -m['skor_' + ANA])[:12]
for i, m in enumerate(en, 1):
    print('  %2d %-9s %-20s %-3s %9.3f %7.2f %7.2f %7.2f'
          % (i, m['ilce'][:9], m['mahalle'][:20], m['kademe'], m['kWh_gm'] / 1e6,
             m['p_teknik'], m['p_ihtiyac'], m['p_erisim']))

print('\n  --- ilk 12 nasil dagiliyor ---')
for il in ILCELER:
    print('    %-12s %d/12' % (il, sum(1 for m in en if m['ilce'] == il)))
for k in 'ABC':
    print('    kademe %s     %d/12' % (k, sum(1 for m in en if m['kademe'] == k)))

# SEGE karsilastirmasi: ilce kademesi ayrim uretiyor mu?
sege = {sadelestir(r['ilce']): r for r in
        json.load(open(yol('cache/izka/sege_ilce.json'), encoding='utf-8'))}
print('\n  SEGE 2022 (ilce kademesi):')
for il in ILCELER:
    r = sege.get(sadelestir(il))
    if r:
        print('    %-12s TR sirasi %-4s skor %-7s kademe %s'
              % (il, r['s2022_tr'], r['s2022_skor'], r['s2022_kademe']))
print('    -> Iki ilce de kademe 1. SEGE bu iki ilce ARASINDA ayrim uretmiyor;')
print('       toplumsal ayrim yalnizca mahalle kademesindeki verilerden geliyor.')


# ============================================================================
# CIKTI
# ============================================================================
sut = ['ilce', 'mahalle', 'kademe', 'ortusme', 'km2', 'nufus',
       'osm_n', 'ms_n', 'osm_alan_ha', 'ms_alan_ha', 'alan_oran',
       'alan_alt_ha', 'alan_ust_ha', 'oz_duz', 'oz_guney', 'oz_kuzey',
       'kWp_alt', 'kWp_olasi', 'kWp_ust', 'MWh_alt', 'MWh_gm', 'MWh_olasi', 'MWh_ust',
       'askida_bin', 'su_kisi', 'ses', 'kamu_n', 'kamu_cati_m2', 'kamu_cati_bin',
       'kamu_belirsiz_n', 'kamu_belirsiz_cati', 'cati_kisi',
       'p_teknik', 'p_ihtiyac', 'p_erisim'] + ['skor_' + a for a in AGIRLIK]

def satir(m):
    d = dict(ilce=m['ilce'], mahalle=m['mahalle'], kademe=m['kademe'],
             ortusme=round(m['ortusme'], 3) if m['ortusme'] else '',
             km2=m['km2'], nufus=m['nufus'], osm_n=m['osm_n'], ms_n=m['ms_n'],
             osm_alan_ha=round(m['osm_alan'] / 1e4, 3), ms_alan_ha=round(m['ms_alan'] / 1e4, 3),
             alan_oran=round(m['alan_oran'], 3) if m['alan_oran'] else '',
             alan_alt_ha=round(m['alan_alt'] / 1e4, 3), alan_ust_ha=round(m['alan_ust'] / 1e4, 3),
             oz_duz=round(m['oz_duz']), oz_guney=round(m['oz_guney']), oz_kuzey=round(m['oz_kuzey']),
             kWp_alt=round(m['kWp_alt']), kWp_olasi=round(m['kWp_olasi']), kWp_ust=round(m['kWp_ust']),
             MWh_alt=round(m['kWh_alt'] / 1e3, 1), MWh_gm=round(m['kWh_gm'] / 1e3, 1),
             MWh_olasi=round(m['kWh_olasi'] / 1e3, 1), MWh_ust=round(m['kWh_ust'] / 1e3, 1),
             askida_bin=round(m['askida_bin'], 2),
             su_kisi=round(m['su_kisi'], 2) if m['su_kisi'] else '',
             ses=m['ses'], kamu_n=m['kamu_n'],
             kamu_cati_m2=round(m['kamu_cati'], 1),
             kamu_cati_bin=round(m['kamu_cati_bin'], 1),
             kamu_belirsiz_n=m['kamu_belirsiz_n'],
             kamu_belirsiz_cati=round(m['kamu_belirsiz_cati'], 1),
             cati_kisi=round(m['cati_kisi'], 2),
             p_teknik=round(m['p_teknik'], 3), p_ihtiyac=round(m['p_ihtiyac'], 3),
             p_erisim=round(m['p_erisim'], 3))
    for a in AGIRLIK:
        d['skor_' + a] = round(m['skor_' + a], 4)
    return d


satirlar = [satir(m) for m in sorted(M, key=lambda x: -x['skor_' + ANA])]
with io.open(yol('cache/bolge_modelleri.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=sut, delimiter=';')
    w.writeheader(); w.writerows(satirlar)

json.dump(dict(
    uretim=time.strftime('%Y-%m-%d %H:%M'), ilceler=ILCELER, mahalle=len(M),
    segmentasyon='YOK - cati alani ayak izinden, SAM maskesinden degil (goruntu kaynagi acik)',
    varsayimlar=dict(m2_per_kWp=M2_PER_KWP, sistem_kaybi_yuzde=KAYIP,
                     kullanilabilir_oran=KULLANILABILIR, min_alan=MIN_ALAN, max_alan=MAX_ALAN,
                     hane_tuketim=HANE_TUKETIM, su_yili=SU_YIL,
                     ortusme_esikleri=[ORTUSME_A, ORTUSME_B]),
    agirliklar={k: list(v) for k, v in AGIRLIK.items()}, ana_agirlik=ANA,
    ihtiyac_bilesen=IHTIYAC_AGIRLIK,
    kamu='mulkiyet=kamu tesislerin cati m2si; tesis poligonu degil icindeki binalar, bina basina tek sayim, belirsiz mulkiyet haric',
    ses='TUIK SES 2023, ILCE duzeyi - mahalle kirilimi yayimlanmiyor',
    toplam=dict(GWh_alt=round(T_alt / 1e6, 3), GWh_geo_merkez=round(T_gm / 1e6, 3),
                GWh_en_olasi=round(T_olasi / 1e6, 3), GWh_ust=round(T_ust / 1e6, 3),
                bant=round(T_ust / T_alt, 3)),
    satirlar=satirlar),
    io.open(yol('cache/bolge_modelleri.json'), 'w', encoding='utf-8'),
    ensure_ascii=False, indent=1)

print('\n-> cache/bolge_modelleri.csv  |  cache/bolge_modelleri.json')
