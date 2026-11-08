# -*- coding: utf-8 -*-
"""Colab kamu SAM haritasi icin ek paket (2026-10-18): Desktop/harita_ek_kamu.zip
  georef.csv       -> 17.10 harita_ek.zip ile AYNI sutunlar (kamu catilari, Model_Verisi'ndeki >= 200 m2)
                      jgw_* = kesit world file (EPSG:3857, piksel MERKEZI), wkt_hizali = Model_Verisi geometrisi,
                      wkt_ham = hizali geometri toplam kaymanin (blok + ince) tersi kadar geri otelenmis hali
  sinirlar.geojson -> Cigli ilce siniri + IKCU Balatcik kampusu (etiket: cigli / ikcu_kampus)
  python scripts/harita_ek_kamu.py"""
import json, os, zipfile
from pathlib import Path
import pandas as pd, geopandas as gpd
from shapely import affinity

KOK = Path(__file__).resolve().parent.parent
MASA = Path.home() / 'Desktop'
KAYNAK = MASA / 'CatiGunes_Model_Verisi'

g = gpd.read_file(KAYNAK / 'catilar.gpkg', layer='catilar')
g = g[g.bolge == 'cigli_kamu'].copy()
ind = pd.read_csv(KAYNAK / 'cati_kesitleri' / 'indeks.csv').set_index('osm')
for c in ('blok_kayma_dogu_m', 'blok_kayma_kuzey_m', 'ince_dogu_m', 'ince_kuzey_m', 'hizalama_kazanci', 'kume_bina'):
    g[c] = g.osm.map(ind[c])
g['kayma_dogu_m'] = (g.blok_kayma_dogu_m + g.ince_dogu_m).round(2)
g['kayma_kuzey_m'] = (g.blok_kayma_kuzey_m + g.ince_kuzey_m).round(2)

# world file: A, D, B, E, C, F
jgw = []
for k in g.kesit:
    v = [float(x) for x in open(KAYNAK / 'cati_kesitleri' / (k[:-4] + '.jgw')).read().split()]
    jgw.append(dict(jgw_a=v[0], jgw_e=v[3], jgw_c=v[4], jgw_f=v[5]))
g = pd.concat([g.reset_index(drop=True), pd.DataFrame(jgw)], axis=1)
g = gpd.GeoDataFrame(g, geometry='geometry', crs=4326)

u = g.to_crs(32635)
ham = [affinity.translate(p, -dx, -dy) for p, dx, dy in zip(u.geometry, g.kayma_dogu_m, g.kayma_kuzey_m)]
g['wkt_hizali'] = g.geometry.to_wkt()
g['wkt_ham'] = gpd.GeoSeries(ham, crs=32635).to_crs(4326).to_wkt().values

sut = ['cati_id', 'bolge', 'tur', 'alan_m2', 'ayak_izi_kaynagi', 'ms_iou', 'gorsel_kontrol', 'kayma_dogu_m', 'kayma_kuzey_m',
       'blok_kayma_dogu_m', 'blok_kayma_kuzey_m', 'ince_dogu_m', 'ince_kuzey_m', 'hizalama_kazanci', 'kume_bina',
       'jgw_a', 'jgw_e', 'jgw_c', 'jgw_f', 'wkt_hizali', 'wkt_ham']
geo = pd.DataFrame(g[sut]).sort_values('cati_id')

s = gpd.read_file(KOK / 'veri' / 'ham' / 'sinir' / 'sinirlar.geojson')
s = s[s.etiket == 'cigli']
k = gpd.read_file(KOK / 'veri' / 'ham' / 'kamu' / 'ikcu_kampus_osm.geojson')
k = k[k.osm == 'relation/6904659'][['osm', 'geometry']].assign(etiket='ikcu_kampus', ad='İzmir Kâtip Çelebi Üniversitesi Balatçık')
sinir = pd.concat([s[['etiket', 'osm', 'ad', 'geometry']], k[['etiket', 'osm', 'ad', 'geometry']]], ignore_index=True)

z = MASA / 'harita_ek_kamu.zip'
with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as f:
    f.writestr('georef.csv', geo.to_csv(index=False))
    f.writestr('sinirlar.geojson', gpd.GeoDataFrame(sinir, crs=4326).to_json(ensure_ascii=False))
print(len(geo), geo.tur.value_counts().to_dict(), '| sinir:', sinir.etiket.tolist(), '|', z, round(os.path.getsize(z) / 1e3), 'KB')
