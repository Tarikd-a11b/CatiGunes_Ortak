# -*- coding: utf-8 -*-
"""Firma -> cati eslemesinin ELLE yapilmasi (2026-10-21). Google Maps'e insan bakar, karari kendisi verir;
Google'dan hicbir veri kaydedilmez (yalniz bizim cati_id kararimiz).
  python scripts/firma_cati_onay.py sayfa            -> veri/elle/firma_cati_onay.html (tarayicida ac)
  python scripts/firma_cati_onay.py isle <csv> [..]  -> indirilen CSV(ler) -> veri/elle/firma_cati_elle.csv (birlestirir)
Sayfa: kesin_osm disindaki her TEKIL adres (sokak+kapi no) bir kart; TomTom onerisi onceden secili (icinde/yakin),
yoksa sokaga cephe veren aday catilar turuncu. 4 kisiye bolunebilir.
Sonra: python scripts/firma_cati_eslesme.py  (elle kararlar en oncelikli)"""
import json, os, sys, datetime as dt
import pandas as pd, geopandas as gpd

sys.stdout.reconfigure(encoding='utf-8')
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = lambda *p: os.path.join(KOK, 'veri', *p)
MV = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi')
ESL = V('ham', 'iaosb', 'firma_cati_eslesme.csv')
ELLE = V('elle', 'firma_cati_elle.csv')
SAYFA = V('elle', 'firma_cati_onay.html')
YOL = {'MKA': 'Mustafa Kemal Atatürk Bulvarı', 'EHC': 'Eski Havaalanı Caddesi', 'ANADOLU': 'Anadolu Caddesi'}


def sayfa():
    e = pd.read_csv(ESL, dtype=str).fillna('')
    e = e[(e.eslesme != 'kesin_osm') & (e.sokak != '') & (e.kapi_no != '')]
    kartlar = []
    for (sk, no), g in e.groupby(['sokak', 'kapi_no'], sort=False):
        ad = f"{YOL.get(sk, sk + '. Sokak')} No:{no}"
        r0 = g.iloc[0]
        tip = ('icinde' if r0.eslesme in ('geocode_rooftop', 'geocode_range_interpolated') else
               'yakin' if r0.eslesme.endswith('_yakin') else 'yok')
        kartlar.append(dict(k=f'{sk}|{no}', ad=ad, q=f'{ad}, Atatürk Organize Sanayi Bölgesi, Çiğli, İzmir',
                            firmalar=[f'{r.firma} ({r.nace})' if r.nace else r.firma for r in g.itertuples()],
                            aday=[int(x) for x in r0.aday_cati_id.split(';') if x],
                            oneri=[int(x) for x in r0.cati_id.split(';') if x] if r0.eslesme.startswith('geocode') else [],
                            tip=tip))
    kartlar.sort(key=lambda k: (k['k'].split('|')[0], int(k['k'].split('|')[1])))
    c = gpd.read_file(os.path.join(MV, 'catilar.gpkg'), layer='catilar')
    c = c[c.bolge == 'ataturk_osb'][['cati_id', 'alan_m2', 'geometry']]
    c['geometry'] = c.geometry.simplify(0.000003)
    gj = json.loads(c.to_json(drop_id=True))
    for ft in gj['features']:   # koordinat hassasiyeti ~10 cm yeter
        ft['geometry']['coordinates'] = json.loads(json.dumps(ft['geometry']['coordinates']), parse_float=lambda x: round(float(x), 6))
    sab = open(os.path.join(KOK, 'scripts', 'firma_cati_onay_sablon.html'), encoding='utf-8').read()
    html = sab.replace('/*KARTLAR*/[]', json.dumps(kartlar, ensure_ascii=False)).replace('/*CATILAR*/{}', json.dumps(gj))
    open(SAYFA, 'w', encoding='utf-8').write(html)
    print(len(kartlar), 'adres karti ->', SAYFA, '(%.1f MB)' % (os.path.getsize(SAYFA) / 1e6))


def isle(dosyalar):
    yeni = pd.concat([pd.read_csv(d, dtype=str).fillna('') for d in dosyalar])
    eski = pd.read_csv(ELLE, dtype=str).fillna('') if os.path.exists(ELLE) else yeni.iloc[:0]
    t = pd.concat([eski, yeni]).sort_values('zaman').drop_duplicates(['sokak', 'kapi_no'], keep='last')
    assert t.karar.isin(['cati', 'listede_yok', 'bulamadim']).all(), t.karar.unique()
    t.sort_values(['sokak', 'kapi_no']).to_csv(ELLE, index=False, encoding='utf-8-sig')
    print(len(yeni), 'satir islendi ->', ELLE, '| toplam', len(t), t.karar.value_counts().to_dict())


if __name__ == '__main__':
    if sys.argv[1:2] == ['sayfa']: sayfa()
    elif sys.argv[1:2] == ['isle'] and sys.argv[2:]: isle(sys.argv[2:])
    else: sys.exit(__doc__)
