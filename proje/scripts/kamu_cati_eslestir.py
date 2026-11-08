# -*- coding: utf-8 -*-
"""Kamu tesis katmanini segmentasyon cati ciktisina baglar.

Girdi : notebooks/.../cigli_catilar_*.geojson  (segmentasyondan cikan cati poligonlari)
        cache/kamu_cigli.geojson               (166 tesis: 131 poligon + 35 nokta)
Cikti : <girdi>_kamu.geojson / .csv  -> her catiya kamu alanlari eklenmis
        ekrana kamu cati ozeti (grup bazinda adet, m2, kWp, GWh)

Eslestirme:
  poligon tesis -> merkezi tesis poligonu icinde kalan TUM catilar (okul 3 binali olabilir)
  nokta tesis   -> noktayi iceren cati; yoksa 30 m icindeki en yakin cati (zayif kanit)

Sutunlar: kamu (bool), kamu_grup, kamu_tur, kamu_ad, kamu_mulkiyet, kamu_eslesme, kamu_osm

Not: mulkiyet alani kamu_binalari.py'den gelir ve 166 tesisin 77'sinde 'belirsiz'.
Uretim/oncelik hesabinda 'kamu' ve 'belirsiz' ayri raporlanmali; 'ozel' disarida birakilmali.
"""
import os, sys, json, csv, io, collections

from shapely.geometry import shape, Point
from shapely.strtree import STRtree

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARSAYILAN = os.path.join(KOK, 'notebooks', 'cigli_kosu', 'calisma', 'cikti', 'cigli_catilar_ornek20.geojson')
KAMU = os.path.join(KOK, 'cache', 'kamu_cigli.geojson')
NOKTA_MESAFE_M = 30.0
DERECE = 1 / 111320.0          # kabaca metre -> derece (enlem); Cigli icin yeterli
# dogrulama_metrik.py (540 catilik ornek, 2026-09-12): oturtma_orani < 0,4 bandinda dogruluk %17,1,
# normal bantta %87,9 -> uretim/oncelik tablolari yalniz guvenilir catilardan hesaplanir.
ESIK_OTURTMA = 0.4


def main():
    girdi = sys.argv[1] if len(sys.argv) > 1 else VARSAYILAN
    veri = json.load(open(girdi, encoding='utf-8'))
    catilar = veri['features']
    geo = [shape(f['geometry']) for f in catilar]
    agac = STRtree(geo)
    merkez = [g.centroid for g in geo]
    print('%d cati okundu  <- %s' % (len(catilar), os.path.basename(girdi)))

    tesisler = json.load(open(KAMU, encoding='utf-8'))['features']
    print('%d kamu tesisi okundu (%d poligon, %d nokta)'
          % (len(tesisler), sum(1 for t in tesisler if t['geometry']['type'] == 'Polygon'),
             sum(1 for t in tesisler if t['geometry']['type'] == 'Point')))

    for f in catilar:
        f['properties'].update(kamu=False, kamu_grup=None, kamu_tur=None, kamu_ad=None,
                               kamu_mulkiyet=None, kamu_eslesme=None, kamu_osm=None)

    eslesen_tesis, catisiz_tesis = 0, []
    for t in tesisler:
        p = t['properties']
        g = shape(t['geometry'])
        bulunan = []
        if t['geometry']['type'] == 'Polygon':
            for i in agac.query(g):
                i = int(i)
                if g.contains(merkez[i]):
                    bulunan.append((i, 'poligon'))
        else:
            for i in agac.query(g):
                i = int(i)
                if geo[i].contains(g):
                    bulunan.append((i, 'nokta-ic'))
            if not bulunan:
                yakin = [(geo[int(i)].distance(g), int(i)) for i in agac.query(g.buffer(NOKTA_MESAFE_M * DERECE))]
                if yakin:
                    d, i = min(yakin)
                    bulunan.append((i, 'nokta-yakin'))
        if not bulunan:
            catisiz_tesis.append(p.get('ad'))
            continue
        eslesen_tesis += 1
        for i, nasil in bulunan:
            pr = catilar[i]['properties']
            # Bir cati birden fazla tesise dusebilir (ic ice poligonlar): poligon kanidi nokta kanidini yener
            if pr['kamu'] and pr['kamu_eslesme'] == 'poligon' and nasil != 'poligon':
                continue
            pr.update(kamu=True, kamu_grup=p.get('grup'), kamu_tur=p.get('tur'), kamu_ad=p.get('ad'),
                      kamu_mulkiyet=p.get('mulkiyet'), kamu_eslesme=nasil,
                      kamu_osm='%s/%s' % (p.get('osm_tip'), p.get('osm_id')))

    kamu_catilar_tum = [f for f in catilar if f['properties']['kamu']]
    kamu_catilar = [f for f in kamu_catilar_tum if f['properties']['oturtma_orani'] >= ESIK_OTURTMA]
    supheli_kamu = [f for f in kamu_catilar_tum if f['properties']['oturtma_orani'] < ESIK_OTURTMA]
    print('\n%d tesis catiyla eslesti, %d tesis bu ornekte catisiz kaldi' % (eslesen_tesis, len(catisiz_tesis)))
    print('%d cati kamu olarak isaretlendi (%.1f%%)' % (len(kamu_catilar_tum), 100 * len(kamu_catilar_tum) / max(len(catilar), 1)))
    print('  -> asagidaki tablolar yalniz oturtma_orani >= %.1f olan %d catiyi kapsiyor; %d cati supheli oldugu icin ayri tutuldu (toplam alanlari %.0f m2)'
          % (ESIK_OTURTMA, len(kamu_catilar), len(supheli_kamu), sum(f['properties']['alan_m2'] for f in supheli_kamu)))

    def topla(kume):
        return (len(kume),
                sum(f['properties']['alan_m2'] for f in kume),
                sum(f['properties']['kWp_alt'] for f in kume),
                sum(f['properties']['kWh_alt'] for f in kume) / 1e6,
                sum(f['properties']['kWh_ust'] for f in kume) / 1e6)

    print('\nGRUBA GORE')
    print('   %-14s %5s %10s %9s %16s' % ('grup', 'cati', 'cati m2', 'kWp alt', 'GWh/yil bandi'))
    for grup in sorted({f['properties']['kamu_grup'] for f in kamu_catilar}):
        n, a, kwp, lo, hi = topla([f for f in kamu_catilar if f['properties']['kamu_grup'] == grup])
        print('   %-14s %5d %10.0f %9.1f   %6.3f-%6.3f' % (grup, n, a, kwp, lo, hi))
    n, a, kwp, lo, hi = topla(kamu_catilar)
    print('   %-14s %5d %10.0f %9.1f   %6.3f-%6.3f' % ('TOPLAM', n, a, kwp, lo, hi))

    print('\nMULKIYETE GORE (ozel olanlar uretim hesabina girmemeli)')
    for m in sorted({f['properties']['kamu_mulkiyet'] for f in kamu_catilar}):
        n, a, kwp, lo, hi = topla([f for f in kamu_catilar if f['properties']['kamu_mulkiyet'] == m])
        print('   %-10s %4d cati  %9.0f m2  %7.1f kWp' % (m, n, a, kwp))

    print('\nESLESME KANITI')
    for e, n in collections.Counter(f['properties']['kamu_eslesme'] for f in kamu_catilar).most_common():
        print('   %-12s %4d' % (e, n))

    print('\nEN BUYUK 10 KAMU CATISI')
    for f in sorted(kamu_catilar, key=lambda f: -f['properties']['alan_m2'])[:10]:
        p = f['properties']
        print('   %-42s %-9s %7.0f m2  %6.1f kWp  %5.0f-%5.0f MWh/yil  ot %.2f'
              % ((p['kamu_ad'] or '?')[:42], p['kamu_grup'], p['alan_m2'], p['kWp_alt'],
                 p['kWh_alt'] / 1e3, p['kWh_ust'] / 1e3, p['oturtma_orani']))

    # kamu_binalari.py kendi cati_m2 tahminiyle capraz kontrol
    kendi = collections.defaultdict(float)
    for f in kamu_catilar:
        kendi[f['properties']['kamu_osm']] += f['properties']['alan_m2']
    onceki = {'%s/%s' % (t['properties']['osm_tip'], t['properties']['osm_id']): t['properties'].get('cati_m2')
              for t in tesisler}
    ciftler = [(k, v, onceki[k]) for k, v in kendi.items() if onceki.get(k)]
    if ciftler:
        oranlar = sorted(v / o for _, v, o in ciftler)
        ort = sum(oranlar) / len(oranlar)
        print('\nCAPRAZ KONTROL: segmentasyon cati m2 / kamu_binalari.py ayak izi m2')
        print('   n=%d tesis | medyan %.2f | ortalama %.2f | %%25 %.2f | %%75 %.2f'
              % (len(ciftler), oranlar[len(oranlar) // 2], ort,
                 oranlar[len(oranlar) // 4], oranlar[3 * len(oranlar) // 4]))

    kok, _ = os.path.splitext(girdi)
    with io.open(kok + '_kamu.geojson', 'w', encoding='utf-8') as fh:
        json.dump(veri, fh, ensure_ascii=False)
    alanlar = list(catilar[0]['properties'].keys())
    with io.open(kok + '_kamu.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=alanlar, delimiter=';')
        w.writeheader()
        for f in catilar:
            w.writerow(f['properties'])
    print('\n-> %s_kamu.geojson / .csv' % os.path.basename(kok))
    if catisiz_tesis:
        print('   bu ornekte catisi bulunamayan tesisler (ilk 10):', ', '.join(x or '?' for x in catisiz_tesis[:10]))


if __name__ == '__main__':
    main()
