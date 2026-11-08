# -*- coding: utf-8 -*-
"""Cati segmentasyonu icin tabakali dogrulama ornegi ve kontak sayfalari.

Girdi : notebooks/cigli_kosu/calisma/cikti/cigli_catilar_ornek20.geojson (540 cati)
        notebooks/cigli_kosu/calisma/karo/19_x_y.jpg (onbellekli karolar)
        cache/osm_binalar_cigli.geojsonl (OSM ayak izleri, karsilastirma icin)
Cikti : notebooks/dogrulama/sayfa_NN.png  (12 cati/sayfa, sari = model catisi, mavi = OSM ayak izi)
        notebooks/dogrulama/ornek.csv     (sira -> osm, tabaka, olculen degerler)

Notlandirma ayri adimda: ornek.csv'ye 'not' sutunu doldurulur (dogru/eksik/tasmis/yanlis),
metrikler scripts/dogrulama_metrik.py ile hesaplanir.
"""
import os, sys, json, math, random, collections

import numpy as np
import cv2
from PIL import Image

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOSU = os.path.join(KOK, 'notebooks', 'cigli_kosu', 'calisma')
GEOJSON = os.path.join(KOSU, 'cikti', 'cigli_catilar_ornek20.geojson')
KARO = os.path.join(KOSU, 'karo')
OSM = os.path.join(KOK, 'cache', 'osm_binalar_cigli.geojsonl')
CIKTI = os.path.join(KOK, 'notebooks', 'dogrulama')
Z, TS = 19, 256
HEDEF = 96          # ornek buyuklugu
SUTUN, SATIR = 4, 3
CHIP = 250          # kontak sayfasindaki her karenin kenari (piksel)
ETIKET_H = 34


def lonlat2g(lon, lat):
    n = (1 << Z) * TS
    return ((lon + 180.0) / 360.0 * n,
            (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)


def karo_oku(x, y, _onbellek={}):
    if (x, y) not in _onbellek:
        p = os.path.join(KARO, '%d_%d_%d.jpg' % (Z, x, y))
        _onbellek[(x, y)] = np.array(Image.open(p).convert('RGB')) if os.path.exists(p) else None
    return _onbellek[(x, y)]


def pencere_oku(gx0, gy0, gx1, gy1):
    gx0, gy0, gx1, gy1 = int(gx0), int(gy0), int(gx1), int(gy1)
    img = np.zeros((gy1 - gy0, gx1 - gx0, 3), np.uint8)
    kapsam = 0
    for ty in range(gy0 // TS, (gy1 - 1) // TS + 1):
        for tx in range(gx0 // TS, (gx1 - 1) // TS + 1):
            k = karo_oku(tx, ty)
            if k is None:
                continue
            sx0, sy0 = max(gx0, tx * TS), max(gy0, ty * TS)
            sx1, sy1 = min(gx1, (tx + 1) * TS), min(gy1, (ty + 1) * TS)
            img[sy0 - gy0:sy1 - gy0, sx0 - gx0:sx1 - gx0] = k[sy0 - ty * TS:sy1 - ty * TS, sx0 - tx * TS:sx1 - tx * TS]
            kapsam += (sx1 - sx0) * (sy1 - sy0)
    return img, kapsam / max((gx1 - gx0) * (gy1 - gy0), 1)


def alan_sinifi(a):
    return '<150' if a < 150 else '150-300' if a < 300 else '>=300'


def main():
    os.makedirs(CIKTI, exist_ok=True)
    veri = json.load(open(GEOJSON, encoding='utf-8'))
    catilar = veri['features']
    print('%d cati okundu' % len(catilar))

    # --- tabakalar: cekim x alan sinifi x oturtma bandi -----------------------
    tabaka = collections.defaultdict(list)
    for f in catilar:
        p = f['properties']
        t = (p['cekim'], alan_sinifi(p['alan_m2']), 'supheli' if p['oturtma_orani'] < 0.4 else 'normal')
        tabaka[t].append(f)
    print('%d tabaka' % len(tabaka))

    # Oransal dagitim, ama her tabakadan en az 3 (kucuk tabakalar da gorulsun).
    # Supheli banda bilerek fazla pay veriliyor; metrik hesabinda agirlik kullanilacak.
    rng = random.Random(20260912)
    toplam = len(catilar)
    secim = []
    for t, grup in sorted(tabaka.items()):
        pay = max(3, round(HEDEF * len(grup) / toplam))
        if t[2] == 'supheli':
            pay = max(pay, 6)
        pay = min(pay, len(grup))
        secim += [(t, f) for f in rng.sample(grup, pay)]
    rng.shuffle(secim)
    print('%d cati secildi' % len(secim))

    # --- secilenlerin OSM ayak izleri ----------------------------------------
    gerekli = {f['properties']['osm'] for _, f in secim}
    ayak = {}
    with open(OSM, encoding='utf-8') as fh:
        for satir in fh:
            if not satir.strip():
                continue
            o = json.loads(satir)
            anahtar = '%s/%s' % (o['properties']['osm_tip'], o['properties']['osm_id'])
            if anahtar in gerekli:
                ayak[anahtar] = o['geometry']['coordinates'][0]
    print('%d/%d ayak izi bulundu' % (len(ayak), len(gerekli)))

    # --- kareler --------------------------------------------------------------
    kayitlar, kareler = [], []
    for sira, (t, f) in enumerate(secim, 1):
        p = f['properties']
        halka = np.array([lonlat2g(lo, la) for lo, la in f['geometry']['coordinates'][0]])
        ay = ayak.get(p['osm'])
        ayg = np.array([lonlat2g(lo, la) for lo, la in ay]) if ay else None

        hepsi = halka if ayg is None else np.vstack([halka, ayg])
        cx, cy = hepsi[:, 0].mean(), hepsi[:, 1].mean()
        yari = max(np.ptp(hepsi[:, 0]), np.ptp(hepsi[:, 1])) / 2 + 14
        yari = max(yari, 26)
        x0, y0, x1, y1 = cx - yari, cy - yari, cx + yari, cy + yari
        img, kapsam = pencere_oku(x0, y0, x1, y1)
        if kapsam < 0.6:
            continue
        olcek = CHIP / img.shape[0]
        buyuk = cv2.resize(img, (CHIP, CHIP), interpolation=cv2.INTER_CUBIC)
        if ayg is not None:
            cv2.polylines(buyuk, [np.round((ayg - [x0, y0]) * olcek).astype(np.int32)], True, (80, 200, 255), 1, cv2.LINE_AA)
        cv2.polylines(buyuk, [np.round((halka - [x0, y0]) * olcek).astype(np.int32)], True, (255, 240, 40), 2, cv2.LINE_AA)

        kare = np.zeros((CHIP + ETIKET_H, CHIP, 3), np.uint8)
        kare[:CHIP] = buyuk
        cv2.putText(kare, '#%d  %.0f m2  ot %.2f' % (sira, p['alan_m2'], p['oturtma_orani']),
                    (4, CHIP + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        kisa = {'egimli (kiremit)': 'kiremit', 'karma (kiremit + teras)': 'karma',
                'muhtemelen egimli (kiremit disi)': 'egimli?', 'duz / teras': 'teras'}
        tip = p['tip']
        for tr, en in (('ğ', 'g'), ('ı', 'i'), ('ş', 's'), ('ç', 'c'), ('ü', 'u'), ('ö', 'o'), ('İ', 'I')):
            tip = tip.replace(tr, en)
        cv2.putText(kare, '%s  %s' % (kisa.get(tip, tip[:16]), t[0].split()[0]),
                    (4, CHIP + 29), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (170, 230, 170), 1, cv2.LINE_AA)
        kareler.append(kare)
        kayitlar.append(dict(sira=sira, osm=p['osm'], birim=p['birim'], cekim=p['cekim'],
                             tabaka_alan=t[1], tabaka_oturtma=t[2], tip=p['tip'],
                             alan_m2=p['alan_m2'], oturtma_orani=p['oturtma_orani'],
                             kiremit_payi=p['kiremit_payi'], golge_durumu=p['golge_durumu'],
                             ayak_izi_var=ay is not None, not_=''))

    # --- kontak sayfalari -----------------------------------------------------
    sayfa_boy = SUTUN * SATIR
    for s in range(0, len(kareler), sayfa_boy):
        grup = kareler[s:s + sayfa_boy]
        h = (CHIP + ETIKET_H) * SATIR
        tuval = np.full((h, CHIP * SUTUN, 3), 18, np.uint8)
        for j, kare in enumerate(grup):
            r, c = divmod(j, SUTUN)
            tuval[r * (CHIP + ETIKET_H):(r + 1) * (CHIP + ETIKET_H), c * CHIP:(c + 1) * CHIP] = kare
        ad = os.path.join(CIKTI, 'sayfa_%02d.png' % (s // sayfa_boy + 1))
        Image.fromarray(tuval).save(ad, optimize=True)
        for i, k in enumerate(kayitlar[s:s + sayfa_boy]):
            k['sayfa'] = s // sayfa_boy + 1
            k['hucre'] = i + 1
    import csv
    with open(os.path.join(CIKTI, 'ornek.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=list(kayitlar[0].keys()), delimiter=';')
        w.writeheader()
        w.writerows(kayitlar)
    print('%d kare, %d sayfa -> %s' % (len(kareler), (len(kareler) + sayfa_boy - 1) // sayfa_boy, CIKTI))
    dag = collections.Counter((k['cekim'].split()[0], k['tabaka_alan'], k['tabaka_oturtma']) for k in kayitlar)
    for t, n in sorted(dag.items()):
        print('   %-6s %-8s %-8s %3d' % (t[0], t[1], t[2], n))


if __name__ == '__main__':
    main()
