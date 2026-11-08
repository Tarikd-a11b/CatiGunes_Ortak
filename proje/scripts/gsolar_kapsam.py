# -*- coding: utf-8 -*-
"""D6 icin aday cozum: Google Solar API cati segmenti (egim + azimut + golgeleme).

Iki asama:
  A) ANAHTARSIZ - indirilmis kapsam poligonlarindan pilot bolgenin hangi veri
     kalitesinde oldugunu dogrular. Her zaman calisir.
  B) ANAHTARLI  - GOOGLE_SOLAR_API_KEY ortam degiskeni varsa buildingInsights
     ucunu birkac Evka-5 binasi icin cagirir ve donen cati segmentlerinin
     egim/azimut degerlerini bizim SAM'den cikardigimiz mahya ekseniyle
     karsilastirir. Bu, D5'teki 180 derece belirsizligi COZER, D6'daki egim
     eksigini KAPATIR.

Kullanim:
    python scripts/gsolar_kapsam.py
    GOOGLE_SOLAR_API_KEY=... python scripts/gsolar_kapsam.py --n 5

Maliyet uyarisi: buildingInsights ucretli bir uctur (aylik ucretsiz kota var).
Once --n 3 ile deneyin; toplu kosu yapmadan once fiyatlandirmayi okuyun.
"""
import argparse, json, math, os, sys
import requests
from shapely.geometry import shape, Point

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)

KALITELER = ['HIGH', 'MEDIUM', 'BASE', 'DA']
UC = 'https://solar.googleapis.com/v1/buildingInsights:findClosest'


def kapsam_dogrula(lon, lat, ad='pilot'):
    """Noktanin hangi Google Solar veri kalitesi katmaninda oldugunu soyler."""
    p = Point(lon, lat)
    bulunan = []
    for kal in KALITELER:
        f = yol('cache', 'gsolar_%s.geojson' % kal)
        if not os.path.exists(f):
            print('  ! kapsam dosyasi yok: %s' % f)
            continue
        fc = json.load(open(f, encoding='utf-8'))
        if any(shape(x['geometry']).contains(p) for x in fc['features']):
            bulunan.append(kal)
    print('  %-14s (%.4f, %.4f) -> %s' % (ad, lon, lat, ', '.join(bulunan) or 'KAPSAM DISI'))
    return bulunan


def bina_icgorusu(lat, lon, anahtar, kalite='MEDIUM'):
    r = requests.get(UC, params={'location.latitude': round(lat, 6),
                                 'location.longitude': round(lon, 6),
                                 'requiredQuality': kalite,
                                 'key': anahtar}, timeout=60)
    if r.status_code != 200:
        return {'hata': r.status_code, 'govde': r.text[:300]}
    return r.json()


def aci_farki(a, b):
    """Iki pusula azimutu arasindaki en kisa fark (0-180)."""
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def eksen_farki(a, b):
    """Eksen karsilastirmasi: 180 derece belirsizligi yok sayar (0-90)."""
    d = aci_farki(a, b)
    return min(d, 180.0 - d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=3, help='kac bina sorulacak')
    args = ap.parse_args()

    print('=== A) Kapsam dogrulamasi (anahtarsiz) ===')
    kapsam_dogrula(27.0532, 38.5185, 'Evka-5')
    kapsam_dogrula(27.1400, 38.4200, 'Izmir merkez')
    kapsam_dogrula(32.8500, 39.9300, 'Ankara')
    kapsam_dogrula(28.9800, 41.0100, 'Istanbul')

    anahtar = os.environ.get('GOOGLE_SOLAR_API_KEY')
    if not anahtar:
        print('\n=== B) atlandi: GOOGLE_SOLAR_API_KEY tanimli degil ===')
        print('    Anahtar alindiginda:  GOOGLE_SOLAR_API_KEY=... python scripts/gsolar_kapsam.py --n 3')
        return

    catilar = json.load(open(yol('cache/evka5_sam_sonuc.json'), encoding='utf-8'))
    catilar = [c for c in catilar if c.get('azimut') is not None]
    catilar.sort(key=lambda c: -c['sam_alan'])
    ornek = catilar[:args.n]

    print('\n=== B) buildingInsights - %d bina ===' % len(ornek))
    kayit = []
    for c in ornek:
        d = bina_icgorusu(c['lat'], c['lon'], anahtar)
        if 'hata' in d:
            print('  bina %-4d HATA %s  %s' % (c['i'], d['hata'], d['govde'][:120]))
            continue
        sp = d.get('solarPotential', {})
        seg = sp.get('roofSegmentStats', [])
        if not seg:
            print('  bina %-4d segment yok' % c['i'])
            continue
        ana = max(seg, key=lambda s: s.get('stats', {}).get('areaMeters2', 0))
        g_egim = ana.get('pitchDegrees')
        g_az = ana.get('azimuthDegrees')
        g_alan = sum(s.get('stats', {}).get('areaMeters2', 0) for s in seg)
        fark = eksen_farki(c['azimut'], g_az) if g_az is not None else None
        kayit.append(dict(i=c['i'], sam_alan=c['sam_alan'], g_alan=g_alan,
                          sam_eksen=c['azimut'], g_azimut=g_az, g_egim=g_egim,
                          eksen_fark=fark, segment=len(seg),
                          kalite=d.get('imageryQuality'), tarih=d.get('imageryDate')))
        print('  bina %-4d segment=%-2d  Google: egim %5.1f  azimut %6.1f  alan %7.1f m2'
              % (c['i'], len(seg), g_egim or -1, g_az if g_az is not None else -1, g_alan))
        print('           SAM   : eksen  %6.1f  alan %7.1f m2   eksen farki %s'
              % (c['azimut'], c['sam_alan'],
                 ('%.1f derece' % fark) if fark is not None else '-'))

    if kayit:
        f = [k['eksen_fark'] for k in kayit if k['eksen_fark'] is not None]
        if f:
            print('\n  eksen farki: medyan %.1f  ort %.1f derece  (n=%d)'
                  % (sorted(f)[len(f)//2], sum(f)/len(f), len(f)))
            print('  yorum: 15 dereceden kucukse SAM mahya ekseni Google ile uyumlu demektir;')
            print('         buyukse mahya cikarimi degil, dogrudan Google azimutu kullanilmali.')
        json.dump(kayit, open(yol('cache/gsolar_ornek.json'), 'w'), ensure_ascii=False, indent=1)
        print('  -> cache/gsolar_ornek.json')


if __name__ == '__main__':
    main()
