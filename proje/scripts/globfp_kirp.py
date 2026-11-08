# -*- coding: utf-8 -*-
"""3D-GloBFP (Che vd. 2025, grid 1148) karosunu Cigli + Ataturk OSB sinirlarina kirpar.
Girdi: veri/ham/globfp/grid1148/*.shp   Cikti: veri/ham/globfp/globfp_<bolge>.geojson"""
import json, os, glob, shapefile
from shapely.geometry import shape, mapping
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = {f['properties']['etiket']: shape(f['geometry']) for f in
     json.load(open(os.path.join(KOK, 'veri/ham/sinir/sinirlar.geojson'), encoding='utf-8'))['features']}
r = shapefile.Reader(glob.glob(os.path.join(KOK, 'veri/ham/globfp/grid1148/*.shp'))[0])
alanlar = [f[0] for f in r.fields[1:]]
print('alanlar:', alanlar, ' kayit:', len(r))
kutu = S['cigli'].bounds
out = {k: [] for k in S}
for sr in r.iterShapeRecords():
    b = sr.shape.bbox
    if b[2] < kutu[0] or b[0] > kutu[2] or b[3] < kutu[1] or b[1] > kutu[3]: continue
    g = shape(sr.shape.__geo_interface__); c = g.representative_point()
    for k, s in S.items():
        if s.contains(c):
            out[k].append({'type': 'Feature', 'geometry': mapping(g), 'properties': dict(zip(alanlar, sr.record))})
for k, v in out.items():
    json.dump({'type': 'FeatureCollection', 'features': v},
              open(os.path.join(KOK, 'veri/ham/globfp/globfp_%s.geojson' % k), 'w', encoding='utf-8'))
    print(k, len(v), 'bina; ornek:', v[0]['properties'] if v else '-')
