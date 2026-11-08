# -*- coding: utf-8 -*-
"""IHTIYAC ANALIZI - pilot bolge secimi icin mahalle bazli kanit tablosu.

Cigli'nin 26 mahallesi + Seyrek'in bagli oldugu Menemen/Gazi Mustafa Kemal
mahallesi icin, teknik potansiyel ile toplumsal ihtiyaci ayni tabloda toplar.

Girdiler
  cache/mahalle_sinirlari.geojson        OSM idari sinirlar
  cache/ms_izmir_122100310.geojsonl      Microsoft bina ayak izleri (391.215 bina)
  cache/acikveri/*.csv                   Izmir BB acik veri (nufus, bina, su, askida fatura)
  data/osm_izmir_kamu.json               OSM kamu binalari
  cache/gsolar_*.geojson                 Google Solar API kapsam poligonlari

Cikti
  cache/ihtiyac_analizi.csv              tam tablo
  cache/ihtiyac_analizi.json             ayni veri + meta

GOSTERGE MANTIGI
  Teknik potansiyel : cati alani, bina sayisi, kisi basi cati alani
  Toplumsal ihtiyac : askida fatura basvurusu/1000 kisi (enerji-su yoksullugu, DOGRUDAN),
                      konut su tuketimi/abone (gelir vekili, DOLAYLI), kamu binasi sayisi
  Veri uygunlugu    : Google Solar kapsami, ayak izi/resmi bina orani (kaynak eksigi olcusu)
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

ODAK = ['EVKA-5', 'BALATÇIK', 'GAZİ MUSTAFA KEMAL']     # kullanicinin sordugu adaylar
SU_YIL = None            # None = veri setindeki en son tam yil


def sadelestir(s):
    """Turkce duyarli eslestirme anahtari ('İ'.lower() birlesik nokta uretir)."""
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')).lower()
    return ''.join(ch for ch in s if ch.isalnum())


def csv_oku(p):
    return list(csv.DictReader(io.open(yol(p), encoding='utf-8-sig'), delimiter=';'))


def sayi(x, vars_=0.0):
    try:
        return float(str(x).replace('.', '').replace(',', '.')) if ',' in str(x) else float(x)
    except Exception:
        return vars_


# ============================ 1. sinirlar ====================================
fc = json.load(open(yol('cache/mahalle_sinirlari.geojson'), encoding='utf-8'))
mahalleler = []
for f in fc['features']:
    p = f['properties']
    g = shape(f['geometry'])
    mahalleler.append(dict(ilce=p['ilce'], mahalle=p['mahalle'], geom=g,
                           anahtar=(sadelestir(p['ilce']), sadelestir(p['mahalle'])),
                           alan_km2=p['alan_km2'], lon=p['merkez_lon'], lat=p['merkez_lat']))
print('%d mahalle siniri yuklendi' % len(mahalleler))
AGAC = STRtree([m['geom'] for m in mahalleler])
INDEKS = {sadelestir(m['mahalle']): m for m in mahalleler}


def bul(ilce, mahalle):
    return INDEKS.get(sadelestir(mahalle))


# ============================ 2. bina ayak izleri ============================
for m in mahalleler:
    m['ayak_n'] = 0; m['ayak_alan'] = 0.0; m['ayak_alanlar'] = []

t0 = time.time(); n = 0
with io.open(yol('cache/ms_izmir_122100310.geojsonl'), encoding='utf-8') as f:
    for satir in f:
        n += 1
        try:
            g = shape(json.loads(satir)['geometry'])
        except Exception:
            continue
        c = g.representative_point()
        for i in AGAC.query(c):
            m = mahalleler[int(i)]
            if m['geom'].contains(c):
                a = transform(to_utm, g).area
                m['ayak_n'] += 1; m['ayak_alan'] += a; m['ayak_alanlar'].append(a)
                break
        if n % 100000 == 0:
            print('   %d/391215 bina tarandi (%.0f s)' % (n, time.time() - t0))
print('ayak izi taramasi bitti: %d bina / %.0f s' % (n, time.time() - t0))

# ============================ 3. resmi istatistikler =========================
for r in csv_oku('cache/acikveri/mahalle_bina_sayisi.csv'):
    m = bul(r['ILCE'], r['MAHALLE'])
    if m and sadelestir(r['ILCE']) == sadelestir(m['ilce']):
        m['resmi_yapi'] = int(sayi(r['YAPI']))
        m['resmi_diger'] = int(sayi(r['DIGER_YAPI']))

for r in csv_oku('cache/acikveri/mahalle_nufus.csv'):
    m = bul(r['ILCE_ADI'], r['MAHALLE_ADI'])
    if m and sadelestir(r['ILCE_ADI']) == sadelestir(m['ilce']):
        m['nufus'] = int(sayi(r['NUFUS_ERKEK_TOPLAM']) + sayi(r['NUFUS_KADIN_TOPLAM']))

# --- askida fatura (enerji-su yoksullugu, mahalle kademesinde) ---
for m in mahalleler:
    m['askida_n'] = 0; m['askida_yillar'] = set()
for r in csv_oku('cache/acikveri/askida_fatura.csv'):
    m = bul(r['ILCE'], r['MAHALLE'])
    if m and sadelestir(r['ILCE']) == sadelestir(m['ilce']):
        m['askida_n'] += int(sayi(r['BASVURU_SAYISI']))
        m['askida_yillar'].add(r['TARIH'][:4])

# --- konut su tuketimi (gelir vekili) ---
yil_say = {}
kayitlar = []
with io.open(yol('cache/acikveri/mahalle_su_tuketim.csv'), encoding='utf-8-sig') as f:
    okur = csv.DictReader(f, delimiter=';')
    for r in okur:
        if r['ABONELIK_GRUBU'].strip() != 'Konut':
            continue
        m = bul(r['ILCE'], r['MAHALLE'])
        if not m or sadelestir(r['ILCE']) != sadelestir(m['ilce']):
            continue
        yil = r['YIL'].strip()
        yil_say[yil] = yil_say.get(yil, 0) + 1
        kayitlar.append((yil, m, sayi(r['ABONE_ADEDI']), sayi(r['ORTALAMA_TUKETIM'])))

if not SU_YIL:
    aylar = {}
    for yil, m, abone, tuketim in kayitlar:
        aylar.setdefault(yil, set())
    # ay bilgisi ayri tutulmadigi icin kayit yogunluguna gore tam yil secimi:
    # en yuksek kayit sayili son yil (kismi yillar belirgin sekilde dusuk kalir)
    ust = max(yil_say.values())
    tam = [y for y, n in yil_say.items() if n >= 0.9 * ust]
    SU_YIL = max(tam)
print('su tuketimi: %d konut kaydi, secilen yil %s' % (len(kayitlar), SU_YIL))
for m in mahalleler:
    m['su_abone_ay'] = 0.0; m['_su_toplam'] = 0.0
for yil, m, abone, tuketim in kayitlar:
    if yil == SU_YIL and abone > 0:
        m['su_abone_ay'] += abone        # abone-ay
        m['_su_toplam'] += tuketim       # m3 (grubun o ayki TOPLAMI)
for m in mahalleler:
    m['su_abone_basi'] = (m['_su_toplam'] / m['su_abone_ay']) if m['su_abone_ay'] else None
    m['su_abone'] = m['su_abone_ay'] / 12.0 if m['su_abone_ay'] else None

# ============================ 4. OSM kamu binalari ===========================
kamu = json.load(open(yol('data/osm_izmir_kamu.json'), encoding='utf-8'))['elements']
for m in mahalleler:
    m['kamu_n'] = 0; m['kamu_liste'] = []
for e in kamu:
    lon = e.get('lon') or (e.get('center') or {}).get('lon')
    lat = e.get('lat') or (e.get('center') or {}).get('lat')
    if lon is None:
        continue
    p = Point(lon, lat)
    for i in AGAC.query(p):
        m = mahalleler[int(i)]
        if m['geom'].contains(p):
            m['kamu_n'] += 1
            t = e.get('tags', {})
            m['kamu_liste'].append('%s:%s' % (t.get('amenity', '?'), t.get('name', '(isimsiz)')))
            break

# ============================ 5. Google Solar kapsami ========================
kapsam_katman = {}
for kal in ('HIGH', 'MEDIUM', 'BASE', 'DA'):
    p = yol('cache/gsolar_%s.geojson' % kal)
    if os.path.exists(p):
        kapsam_katman[kal] = [shape(x['geometry'])
                              for x in json.load(open(p, encoding='utf-8'))['features']]
for m in mahalleler:
    c = Point(m['lon'], m['lat'])
    m['gsolar'] = ','.join(k for k, gs in kapsam_katman.items()
                           if any(g.contains(c) for g in gs)) or 'yok'

# ============================ 6. PVGIS ozgul verim ===========================
PV_ONBELLEK = yol('cache/pvgis_mahalle.json')
pv = json.load(open(PV_ONBELLEK)) if os.path.exists(PV_ONBELLEK) else {}
for m in mahalleler:
    k = '%.3f_%.3f' % (m['lat'], m['lon'])
    if k not in pv:
        try:
            r = requests.get('https://re.jrc.ec.europa.eu/api/v5_3/PVcalc',
                             params=dict(lat=round(m['lat'], 3), lon=round(m['lon'], 3),
                                         peakpower=1, loss=14, angle=30, aspect=0,
                                         outputformat='json'), timeout=90)
            r.raise_for_status()
            pv[k] = float(r.json()['outputs']['totals']['fixed']['E_y'])
        except Exception as e:
            print('   PVGIS hata %s: %s' % (m['mahalle'], e)); pv[k] = None
        time.sleep(0.3)
    m['pvgis_guney30'] = pv[k]
json.dump(pv, open(PV_ONBELLEK, 'w'))

# ============================ 7. turetilmis gostergeler ======================
for m in mahalleler:
    nuf = m.get('nufus') or 0
    m['cati_alan_ha'] = m['ayak_alan'] / 1e4
    m['cati_kisi_basi'] = (m['ayak_alan'] / nuf) if nuf else None
    m['askida_bin_kisi'] = (1000.0 * m['askida_n'] / nuf) if nuf else None
    m['kamu_bin_kisi'] = (1000.0 * m['kamu_n'] / nuf) if nuf else None
    resmi = m.get('resmi_yapi')
    m['ayak_resmi_oran'] = (m['ayak_n'] / resmi) if resmi else None
    m['nufus_yogunluk'] = (nuf / m['alan_km2']) if m['alan_km2'] else None
    m['bina_basi_nufus'] = (nuf / m['ayak_n']) if m['ayak_n'] else None
    a = m['ayak_alanlar']
    m['ayak_medyan_m2'] = float(np.median(a)) if a else None
    # kaba uretim potansiyeli: duz cati senaryosu, %55 kullanilabilir, 6 m2/kWp
    if m['pvgis_guney30']:
        m['kWp_kaba'] = m['ayak_alan'] * 0.55 / 6.0
        m['GWh_kaba'] = m['kWp_kaba'] * m['pvgis_guney30'] * 0.874 / 1e6   # 0.874 = duz/guney30 orani
    else:
        m['kWp_kaba'] = m['GWh_kaba'] = None

# ============================ 8. rapor =======================================
def g(m, k, b='-'):
    v = m.get(k)
    return b if v is None else v

sirali = sorted(mahalleler, key=lambda m: -(m.get('askida_bin_kisi') or -1))
print('\n' + '=' * 108)
print('IHTIYAC ANALIZI - Cigli 26 mahalle + Menemen/Gazi Mustafa Kemal (Seyrek)')
print('askida fatura basvurusuna gore azalan siralama (enerji-su yoksullugu vekili)')
print('=' * 108)
bas = ('mahalle', 'nufus', 'binaOSM', 'binaRES', 'cati ha', 'm2/kisi',
       'askida', '/1000k', 'su/abone', 'kamu', 'gsolar')
print('%-26s %7s %7s %7s %8s %8s %7s %7s %9s %5s %7s' % bas)
print('-' * 108)
for m in sirali:
    yildiz = '*' if m['mahalle'] in ODAK else ' '
    print('%s%-25s %7s %7d %7s %8.1f %8s %7d %7s %9s %5d %7s' % (
        yildiz, m['mahalle'][:25], g(m, 'nufus'), m['ayak_n'], g(m, 'resmi_yapi'),
        m['cati_alan_ha'],
        ('%.1f' % m['cati_kisi_basi']) if m['cati_kisi_basi'] else '-',
        m['askida_n'],
        ('%.1f' % m['askida_bin_kisi']) if m['askida_bin_kisi'] is not None else '-',
        ('%.0f' % m['su_abone_basi']) if m['su_abone_basi'] else '-',
        m['kamu_n'], m['gsolar']))

print('\n(*) kullanicinin sordugu aday bolgeler')

# ============================ 9. cikti =======================================
sutun = ['ilce', 'mahalle', 'alan_km2', 'nufus', 'nufus_yogunluk', 'resmi_yapi', 'resmi_diger',
         'ayak_n', 'ayak_resmi_oran', 'ayak_alan', 'cati_alan_ha', 'ayak_medyan_m2',
         'cati_kisi_basi', 'bina_basi_nufus', 'askida_n', 'askida_bin_kisi',
         'su_abone', 'su_abone_basi', 'kamu_n', 'kamu_bin_kisi',
         'gsolar', 'pvgis_guney30', 'kWp_kaba', 'GWh_kaba']
with io.open(yol('cache/ihtiyac_analizi.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    f.write(';'.join(sutun) + '\n')
    for m in sirali:
        f.write(';'.join(str(m.get(s, '')).replace(';', ',') for s in sutun) + '\n')

json.dump({'olusturma': time.strftime('%Y-%m-%d'), 'su_yili': SU_YIL,
           'askida_yillar': sorted(set().union(*[m['askida_yillar'] for m in mahalleler]) or {''}),
           'mahalleler': [{s: m.get(s) for s in sutun} for m in sirali]},
          open(yol('cache/ihtiyac_analizi.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n-> cache/ihtiyac_analizi.csv  |  cache/ihtiyac_analizi.json')
