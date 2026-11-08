# -*- coding: utf-8 -*-
"""SAM egitimi icin cati listesi (2026-10-18, ekip karari): yalniz taban alani >= 200 m2 (Model_Verisi kapsam == 'ana').
Girdi : Desktop/CatiGunes_SAM_Veriseti/tum.csv (goruntu/maske/bolum) + Desktop/CatiGunes_Model_Verisi/catilar.gpkg (kapsam)
Cikti : Desktop/CatiGunes_SAM_Veriseti/sam_egitim_200m2.csv  (bolum korunur: test_referans sabit kalir)
egitim_uygun = False (satir silinmez, dislama_nedeni yazilir):
  - supheli bolumu / gorsel_kontrol isareti (goruntu kotu, agac alti, sekil uyumsuz) -> etiket guvenilmez
  - dar_cati: dondurulmus dikdortgen kisa kenari < 8 m -> gozle: cogu buyuk catinin kenar seridi / sundurma (zayif etiket yanlis)
Bilgi sutunlari (dislamaz): mevcut_ges (tam: GES potansiyeli yok ama cati sinirini ogrenmek icin gecerli), hizalama.
  python scripts/sam_egitim_listesi.py"""
import os
import pandas as pd, geopandas as gpd
from shapely.geometry import Point

MASA = os.path.join(os.path.expanduser('~'), 'Desktop')
SAM = os.path.join(MASA, 'CatiGunes_SAM_Veriseti')
MIN_KISA_KENAR = 8

g = gpd.read_file(os.path.join(MASA, 'CatiGunes_Model_Verisi', 'catilar.gpkg'), layer='catilar')
u = g.to_crs(32635)


def kisa_kenar(p):
    c = list(p.minimum_rotated_rectangle.exterior.coords)
    return min(Point(c[0]).distance(Point(c[1])), Point(c[1]).distance(Point(c[2])))


g['kisa_kenar_m'] = [round(kisa_kenar(p), 1) for p in u.geometry]
g = g[g.kapsam == 'ana']

t = pd.read_csv(os.path.join(SAM, 'tum.csv'), encoding='utf-8-sig')
d = t.merge(g[['cati_id', 'osm', 'kapsam', 'kisa_kenar_m']], on=['cati_id', 'osm'], how='inner')
neden = []
for r in d.itertuples():
    n = []
    if r.bolum == 'supheli' or isinstance(r.gorsel_kontrol, str): n.append('gorsel_sorun')
    if r.kisa_kenar_m < MIN_KISA_KENAR: n.append('dar_cati_<%dm' % MIN_KISA_KENAR)
    neden.append(';'.join(n) or None)
d['dislama_nedeni'] = neden
d['egitim_uygun'] = d.dislama_nedeni.isna()
d.sort_values('cati_id').to_csv(os.path.join(SAM, 'sam_egitim_200m2.csv'), index=False, encoding='utf-8-sig')

eksik = g[~g.cati_id.isin(d.cati_id)]
print('tum.csv %d -> >=200 m2: %d | egitim_uygun: %d' % (len(t), len(d), d.egitim_uygun.sum()))
print(d.groupby(['bolum', 'egitim_uygun']).size().unstack(fill_value=0).to_string())
print(d.dislama_nedeni.value_counts().to_string())
print('Model_Verisi ana olup SAM setinde olmayan: %d (%s)' % (len(eksik), eksik.tur.value_counts().to_dict()))
