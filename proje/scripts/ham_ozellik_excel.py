# -*- coding: utf-8 -*-
"""Overpass HAM cevaplarini (elements[] + tags{}) inceleme icin disa aktarir.
1) Binalar icin tek ham dosya (kamu ile ayni bicim): veri/ham/osm/overpass_bina_ham_<bolge>.json
   (karo onbelleklerinden birlestirilir, bolge sinirina gore suzulur)
2) veri/inceleme/ham_ozellikler.xlsx: her eleman bir satir, HER OSM ETIKETI AYRI SUTUN
   + Etiket_sozlugu sayfasi (etiket, kac kayitta dolu, %, ornek degerler).
2026-10-15 sadelestirme: ham sayfalarda yalniz analizde kullanilan etiketler (TUT); diger ~100 etiket (odeme, telefon,
   tuvalet, marka...) yalniz sozlukte listelenir, tam hali 03_ham/osm/*.json'da. Cigli_bina sayfasi cikti
   (kamu catilari artik veri/inceleme/cati_listesi.xlsx'te)."""
import json, os, glob, collections
import pandas as pd
from shapely.geometry import shape, Point

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = lambda *p: os.path.join(KOK, 'veri', 'ham', *p)
OUT = os.path.join(KOK, 'veri', 'inceleme'); os.makedirs(OUT, exist_ok=True)
S = {f['properties']['etiket']: shape(f['geometry'])
     for f in json.load(open(H('sinir', 'sinirlar.geojson'), encoding='utf-8'))['features']}


def merkez(e):
    b = e.get('bounds')
    if b: return (b['minlon'] + b['maxlon']) / 2, (b['minlat'] + b['maxlat']) / 2
    if 'lon' in e: return e['lon'], e['lat']
    g = e.get('geometry') or []
    return (sum(p['lon'] for p in g) / len(g), sum(p['lat'] for p in g) / len(g)) if g else (None, None)


# 1) bina ham dosyalari
tum = {}
for p in glob.glob(H('osm', 'karo', '*.json')):
    for e in json.load(open(p, encoding='utf-8'))['elements']:
        tum[(e['type'], e['id'])] = e
for bolge, sinir in S.items():
    el = [e for e in tum.values() if (lambda c: c[0] is not None and sinir.contains(Point(c)))(merkez(e))]
    json.dump({'kaynak': 'Overpass API (overpass-api.de), way/rel["building"], karolardan birlestirildi',
               'indirme_tarihi': '2026-10-14', 'bolge': bolge, 'elements': el},
              open(H('osm', 'overpass_bina_ham_%s.json' % bolge), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(bolge, len(el), 'ham bina elemani')


# 2) Excel: etiketler sutun
TUT = ['building', 'amenity', 'man_made', 'name', 'operator', 'operator:type', 'source']


def tablo(elements):
    sayac = collections.Counter(k for e in elements for k in e.get('tags', {}))
    anahtarlar = TUT
    satir = []
    for e in elements:
        lon, lat = merkez(e)
        r = {'osm': '%s/%s' % (e['type'], e['id']), 'merkez_lon': round(lon, 6), 'merkez_lat': round(lat, 6)}
        r.update({k: e.get('tags', {}).get(k) for k in anahtarlar})
        satir.append(r)
    n = len(elements)
    sozluk = pd.DataFrame([{'etiket': k, 'tabloda': 'evet' if k in TUT else 'hayir (ham json)', 'dolu_kayit': c, 'doluluk_%': round(100 * c / n, 1),
                            'ornek_degerler': ' | '.join('%s (%d)' % kv for kv in collections.Counter(
                                str(e['tags'][k]) for e in elements if k in e.get('tags', {})).most_common(6))}
                           for k, c in sayac.most_common()])
    return pd.DataFrame(satir), sozluk


# kamu: yalniz kapsamdaki devlet okul + hastaneleri (2026-10-15, scripts/kamu_okul_hastane.py)
KAPSAM = {f['properties']['osm'] for f in json.load(open(os.path.join(KOK, 'veri', 'islenmis', 'kamu_okul_hastane_cigli.geojson'),
                                                          encoding='utf-8'))['features']}
kaynaklar = [('Kamu', [e for e in json.load(open(H('kamu', 'overpass_kamu_ham.json'), encoding='utf-8'))['elements']
                       if '%s/%s' % (e['type'], e['id']) in KAPSAM]),
             ('OSB_bina', json.load(open(H('osm', 'overpass_bina_ham_ataturk_osb.json'), encoding='utf-8'))['elements'])]
xp = os.path.join(OUT, 'ham_ozellikler.xlsx')
with pd.ExcelWriter(xp, engine='openpyxl') as w:
    for ad, el in kaynaklar:
        df, sz = tablo(el)
        for sayfa, d in ((ad + '_ham', df), (ad + '_etiket_sozlugu', sz)):
            d.to_excel(w, sheet_name=sayfa, index=False)
            ws = w.sheets[sayfa]; ws.freeze_panes = 'B2' if sayfa.endswith('_ham') else 'A2'
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(45, max(8, *(len(str(c.value or '')) for c in col[:300])) + 2)
        print('%-11s %6d satir, %3d etiket sutunu' % (ad, len(df), len(sz)))
print(xp)
