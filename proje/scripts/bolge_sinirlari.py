# -*- coding: utf-8 -*-
"""Aday pilot bolgelerin sinirlarini OSM Nominatim'den ceker, cache'e yazar.

Adaylar: Evka-5 (Cigli), Balatcik (Cigli), Seyrek (Menemen), Cigli ilcesi (tumu).
Cikti: cache/bolgeler.geojson  (her bolge bir Feature, ozelliklerde ilce/alan)
"""
import json, os, time, urllib.parse
import requests
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)

UA = {'User-Agent': 'YBS-bitirme-cati-gunes/0.1 (akademik arastirma)'}
to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32635', always_xy=True).transform

ADAYLAR = [
    # (etiket, Nominatim sorgusu, beklenen ilce, beklenen osm tipi)
    ('Evka-5',   'Evka-5 Mahallesi, Cigli, Izmir',   'Çiğli',   'suburb'),
    ('Balatcik', 'Balatcik Mahallesi, Cigli, Izmir', 'Çiğli',   'suburb'),
    ('Seyrek',   'Seyrek, Menemen, Izmir',           'Menemen', 'suburb'),
    ('Cigli',    'Cigli, Izmir',                     'Çiğli',   'ilce'),
]


def nominatim(q):
    u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
        {'q': q, 'format': 'json', 'polygon_geojson': 1, 'limit': 8, 'countrycodes': 'tr'})
    r = requests.get(u, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    ozellikler = []
    for etiket, sorgu, ilce, tip in ADAYLAR:
        print('\n--- %s  (%s)' % (etiket, sorgu))
        try:
            sonuc = nominatim(sorgu)
        except Exception as e:
            print('   HATA: %s' % e); time.sleep(1.2); continue
        adaylar = [s for s in sonuc if s.get('geojson', {}).get('type') in ('Polygon', 'MultiPolygon')]
        if not adaylar:
            print('   poligon donmedi; adaylar: %s'
                  % [s.get('display_name', '')[:60] for s in sonuc][:3])
            time.sleep(1.2); continue
        for s in adaylar[:4]:
            print('   aday: %-55s  %s/%s' % (s['display_name'][:55], s['class'], s['type']))
        s = adaylar[0]
        g = shape(s['geojson'])
        alan_km2 = transform(to_utm, g).area / 1e6
        c = g.centroid
        print('   SECILEN: %s' % s['display_name'][:70])
        print('   alan %.2f km2   merkez (%.5f, %.5f)' % (alan_km2, c.x, c.y))
        ozellikler.append({'type': 'Feature', 'geometry': mapping(g),
                           'properties': {'etiket': etiket, 'ilce': ilce, 'tip': tip,
                                          'ad': s['display_name'], 'osm_id': s['osm_id'],
                                          'alan_km2': round(alan_km2, 3),
                                          'merkez_lon': round(c.x, 6), 'merkez_lat': round(c.y, 6)}})
        time.sleep(1.2)   # Nominatim nezaket sinirlari

    json.dump({'type': 'FeatureCollection', 'features': ozellikler},
              open(yol('cache/bolgeler.geojson'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('\n-> cache/bolgeler.geojson  (%d bolge)' % len(ozellikler))


if __name__ == '__main__':
    main()
