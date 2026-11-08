# -*- coding: utf-8 -*-
"""Cigli'nin 26 mahallesi (+ Seyrek'in bagli oldugu Menemen mahallesi) icin
OSM sinir poligonlarini ceker. Ihtiyac analizinde cati alani hesabinin temeli.

Cikti: cache/mahalle_sinirlari.geojson
"""
import csv, io, json, os, sys, time, urllib.parse
import requests
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)

UA = {'User-Agent': 'YBS-bitirme-cati-gunes/0.1 (akademik arastirma)'}
to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32635', always_xy=True).transform
CIKTI = yol('cache/mahalle_sinirlari.geojson')

# Seyrek idari bir mahalle degil; Nominatim onu bu mahallenin icinde konumluyor.
EK = [('MENEMEN', 'GAZİ MUSTAFA KEMAL')]


def nominatim(q):
    u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
        {'q': q, 'format': 'json', 'polygon_geojson': 1, 'limit': 8, 'countrycodes': 'tr'})
    r = requests.get(u, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()


def sadelestir(s):
    """Turkce duyarli karsilastirma anahtari.

    Python'da 'İ'.lower() birlesik noktali 'i̇' uretir ve duz 'i' ile eslesmez;
    bu yuzden once birlesik isaretler atilir, sonra Turkce harfler ASCII'ye indirilir.
    """
    import unicodedata
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    tr = str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')
    return s.translate(tr).lower()


def sinir_bul(ilce, mahalle):
    """Once '<mahalle> Mahallesi, <ilce>, Izmir', olmazsa sadeleştirilmiş sorgu."""
    denemeler = ['%s Mahallesi, %s, İzmir' % (mahalle.title(), ilce.title()),
                 '%s, %s, İzmir' % (mahalle.title(), ilce.title())]
    for q in denemeler:
        try:
            sonuc = nominatim(q)
        except Exception as e:
            print('      sorgu hatasi: %s' % e); time.sleep(2); continue
        time.sleep(1.2)
        uygun = [s for s in sonuc
                 if s.get('geojson', {}).get('type') in ('Polygon', 'MultiPolygon')
                 and s.get('class') == 'boundary'
                 and sadelestir(ilce) in sadelestir(s.get('display_name', ''))]
        if uygun:
            return uygun[0]
    return None


def main():
    b = list(csv.DictReader(io.open(yol('cache/acikveri/mahalle_bina_sayisi.csv'),
                                    encoding='utf-8-sig'), delimiter=';'))
    # Ilceler komut satirindan gelir; verilmezse Cigli (geriye donuk uyumluluk).
    ilceler = [a.upper() for a in sys.argv[1:]] or ['ÇİĞLİ']
    hedefler = [(i, r['MAHALLE'].strip()) for i in ilceler
                for r in b if r['ILCE'].strip() == i]
    if 'ÇİĞLİ' in ilceler:
        hedefler += EK          # Seyrek idari mahalle degil, Menemen/GMK icinde
    print('ilceler: %s' % ', '.join(ilceler))
    print('%d mahalle sinirlanacak\n' % len(hedefler))

    mevcut = {}
    if os.path.exists(CIKTI):
        for f in json.load(open(CIKTI, encoding='utf-8'))['features']:
            mevcut[(f['properties']['ilce'], f['properties']['mahalle'])] = f
        print('onbellekte %d sinir var\n' % len(mevcut))

    ozellikler = []
    for ilce, mah in hedefler:
        if (ilce, mah) in mevcut:
            ozellikler.append(mevcut[(ilce, mah)]); continue
        s = sinir_bul(ilce, mah)
        if not s:
            print('  %-38s SINIR YOK' % mah); continue
        g = shape(s['geojson'])
        alan = transform(to_utm, g).area / 1e6
        c = g.centroid
        print('  %-38s %6.2f km2   (%.5f, %.5f)' % (mah, alan, c.x, c.y))
        ozellikler.append({'type': 'Feature', 'geometry': mapping(g),
                           'properties': {'ilce': ilce, 'mahalle': mah,
                                          'osm_ad': s['display_name'], 'osm_id': s['osm_id'],
                                          'alan_km2': round(alan, 4),
                                          'merkez_lon': round(c.x, 6),
                                          'merkez_lat': round(c.y, 6)}})
        json.dump({'type': 'FeatureCollection', 'features': ozellikler},
                  open(CIKTI, 'w', encoding='utf-8'), ensure_ascii=False)

    # Dongu icindeki artimli yazim, son oge onbellekten geliyorsa onu atliyordu.
    # Bitiste her zaman tam listeyi yaz.
    json.dump({'type': 'FeatureCollection', 'features': ozellikler},
              open(CIKTI, 'w', encoding='utf-8'), ensure_ascii=False)
    print('\n-> cache/mahalle_sinirlari.geojson  (%d / %d)' % (len(ozellikler), len(hedefler)))
    eksik = [m for i, m in hedefler if not any(f['properties']['mahalle'] == m for f in ozellikler)]
    if eksik:
        print('   sinir bulunamayan: %s' % ', '.join(eksik))


if __name__ == '__main__':
    main()
