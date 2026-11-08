# -*- coding: utf-8 -*-
"""Colab defteri icin mahalle bazli GIRDI tablosu.

Agir cografi adimlar (MS 150 MB tarama, OSM Overpass, kamu eslestirme) yerelde
kaldi. Bu betik onlarin mahalle ozetini + ham toplumsal veriyi tek tabloya
yazar; defter Model 1-3'u bu tablodan bastan hesaplar.

Cikti: cache/colab_girdi.csv  (53 satir, ';' ayracli, UTF-8)
"""
import csv, io, json, os, unicodedata

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)

def sadelestir(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')).lower()
    return ''.join(ch for ch in s if ch.isalnum())

def sayi(x, vars_=0.0):
    try:
        return float(str(x).replace('.', '').replace(',', '.')) if ',' in str(x) else float(x)
    except Exception:
        return vars_

def anahtar(il, mh): return (sadelestir(il), sadelestir(mh))

model = list(csv.DictReader(io.open(yol('cache/bolge_modelleri.csv'), encoding='utf-8-sig'), delimiter=';'))
R = {anahtar(r['ilce'], r['mahalle']): dict(r) for r in model}

for f in json.load(open(yol('cache/mahalle_sinirlari.geojson'), encoding='utf-8'))['features']:
    p = f['properties']; k = anahtar(p['ilce'], p['mahalle'])
    if k in R:
        R[k]['lat'], R[k]['lon'] = p['merkez_lat'], p['merkez_lon']

pv = json.load(open(yol('cache/pvgis_bolge.json')))
for r in R.values():
    for ad, (e, a) in dict(oz_duz=(0, 0), oz_guney=(30, 0), oz_kuzey=(30, 180)).items():
        r[ad] = pv['%.3f|%.3f|%d|%d' % (r['lat'], r['lon'], e, a)]

for r in R.values(): r['askida_n'] = 0
for a in csv.DictReader(io.open(yol('cache/acikveri/askida_fatura.csv'), encoding='utf-8-sig'), delimiter=';'):
    k = anahtar(a['ILCE'], a['MAHALLE'])
    if k in R: R[k]['askida_n'] += int(sayi(a['BASVURU_SAYISI']))

kayit, yil_say = [], {}
for s in csv.DictReader(io.open(yol('cache/acikveri/mahalle_su_tuketim.csv'), encoding='utf-8-sig'), delimiter=';'):
    if s['ABONELIK_GRUBU'].strip() != 'Konut': continue
    k = anahtar(s['ILCE'], s['MAHALLE'])
    if k not in R: continue
    y = s['YIL'].strip(); yil_say[y] = yil_say.get(y, 0) + 1
    kayit.append((y, k, sayi(s['ABONE_ADEDI']), sayi(s['ORTALAMA_TUKETIM'])))
ust = max(yil_say.values())
SU_YIL = max(y for y, c in yil_say.items() if c >= 0.9 * ust)
ab = {k: 0.0 for k in R}; tk = {k: 0.0 for k in R}
for y, k, a_, t_ in kayit:
    if y == SU_YIL and a_ > 0: ab[k] += a_; tk[k] += t_
for k, r in R.items():
    r['su_kisi'] = tk[k] / ab[k] if ab[k] else ''

sut = ['ilce', 'mahalle', 'kademe', 'ortusme', 'km2', 'nufus', 'lat', 'lon',
       'osm_n', 'ms_n', 'osm_m2', 'ms_m2', 'oz_duz', 'oz_guney', 'oz_kuzey',
       'askida_n', 'su_kisi', 'ses', 'kamu_n', 'kamu_m2', 'belirsiz_n', 'belirsiz_m2']
with io.open(yol('cache/colab_girdi.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(sut)
    for r in model:
        x = R[anahtar(r['ilce'], r['mahalle'])]
        w.writerow([x['ilce'], x['mahalle'], x['kademe'], x['ortusme'], x['km2'], x['nufus'],
                    round(x['lat'], 5), round(x['lon'], 5), x['osm_n'], x['ms_n'],
                    round(float(x['osm_alan_ha']) * 1e4), round(float(x['ms_alan_ha']) * 1e4),
                    x['oz_duz'], x['oz_guney'], x['oz_kuzey'], x['askida_n'],
                    round(x['su_kisi'], 4) if x['su_kisi'] != '' else '', x['ses'],
                    x['kamu_n'], x['kamu_cati_m2'], x['kamu_belirsiz_n'], x['kamu_belirsiz_cati']])
print('su yili', SU_YIL, '| satir', len(model))
