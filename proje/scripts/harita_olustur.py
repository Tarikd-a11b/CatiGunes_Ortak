# -*- coding: utf-8 -*-
"""Segmentasyon ciktisindan (cigli_catilar_*.geojson) interaktif Leaflet haritasi uretir.

  python scripts/harita_olustur.py [girdi.geojson] [--cikti harita.html] [--birim "Ataşehir"]

Girdi verilmezse notebooks/cigli_kosu/calisma/cikti/cigli_catilar_ornek20_kamu.geojson
kullanilir (kucuk ornek, prototip icin). Tam kosu ciktisi:
  python scripts/harita_olustur.py notebooks/cigli_tam_kosu/cikti/cigli_catilar_tum_kamu.geojson

--birim: yalniz o mahalledeki catilari cizer.

Uc katman uretilir (LayerControl ile ac/kapa):
  1. Catı tipi        - RENK_TIP sozlugundeki 4 sinifa gore renkli
  2. Oturtma guvenilirligi - oturtma_orani < ESIK_OTURTMA kirmizi, degilse yesil
  3. Kamu binalari    - yalniz kamu=True catilar, ayri renk

Onemli: her katman TEK bir folium.GeoJson cagrisiyla (bir FeatureCollection + style_function)
eklenir, catı basina ayrı GeoJson objesi ACILMAZ. 20 binin uzerinde catıda bunun farkı devasa:
ilk denemede (catı basina ayrı obje + Python'da baked renk/tooltip) 20.291 catı x 3 katman
99,97 MB'lık, tarayicida acilmasi guc bir dosya uretti. Tek-GeoJson + style_function/
GeoJsonTooltip yaklasimi aynı veriyi ~10 kat kucuk dosyada ve cok daha hizli render eder.
"""
import argparse
import json
import os

import folium

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARSAYILAN_GIRDI = os.path.join(KOK, 'notebooks', 'cigli_kosu', 'calisma', 'cikti',
                                 'cigli_catilar_ornek20_kamu.geojson')
ESIK_OTURTMA = 0.4

RENK_TIP = {
    'eğimli (kiremit)': '#FF7800',
    'karma (kiremit + teras)': '#E91E8C',
    'muhtemelen eğimli (kiremit dışı)': '#2E9E2E',
    'düz / teras': '#00AEEF',
}
RENK_GUVENILIR, RENK_SUPHELI, RENK_KAMU = '#2E9E2E', '#E53935', '#8E24AA'

TOOLTIP_ALANLAR = ['birim', 'cekim', 'tip', 'alan_m2', 'oturtma_orani', 'kWh_alt', 'kWh_ust']
TOOLTIP_BASLIK = ['birim', 'çekim', 'tip', 'alan (m²)', 'oturtma oranı', 'üretim alt (kWh)', 'üretim üst (kWh)']
TOOLTIP_ALANLAR_KAMU = TOOLTIP_ALANLAR + ['kamu_ad', 'kamu_grup', 'kamu_mulkiyet']
TOOLTIP_BASLIK_KAMU = TOOLTIP_BASLIK + ['kamu adı', 'kamu grubu', 'mülkiyet']
# harita yalnız bunları kullanıyor; segmentasyon çıktısının geri kalan ~20 alanını (yükseklik,
# gölge, eğim, SAM ham verisi...) embed etmek dosyayı gereksiz büyütür — 20 binin üzerinde
# çatıda bu fark 40 MB'tan 20'ye iner.
GEREKLI_ALANLAR = ['birim', 'cekim', 'tip', 'alan_m2', 'oturtma_orani', 'kWh_alt', 'kWh_ust',
                    'kamu', 'kamu_ad', 'kamu_grup', 'kamu_mulkiyet']


def hafiflet(features):
    return [{'type': 'Feature', 'geometry': f['geometry'],
             'properties': {k: f['properties'].get(k) for k in GEREKLI_ALANLAR}}
            for f in features]


def sinirlar(features):
    xs, ys = [], []
    for f in features:
        for halka in f['geometry']['coordinates']:
            for x, y in halka:
                xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def katman_ekle(harita, features, ad, renk_fn, alanlar=TOOLTIP_ALANLAR, basliklar=TOOLTIP_BASLIK, ac=False):
    fc = {'type': 'FeatureCollection', 'features': features}
    folium.GeoJson(
        fc, name=ad, show=ac,
        style_function=lambda feat: {
            'color': '#20303A', 'weight': 0.5, 'fillColor': renk_fn(feat['properties']), 'fillOpacity': 0.75,
        },
        highlight_function=lambda feat: {'weight': 2, 'color': '#FFD54A'},
        tooltip=folium.GeoJsonTooltip(fields=alanlar, aliases=basliklar, localize=True, sticky=True),
    ).add_to(harita)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('girdi', nargs='?', default=VARSAYILAN_GIRDI)
    ap.add_argument('--cikti', default=None)
    ap.add_argument('--birim', default=None, help='yalniz bu mahalledeki catilari ciz')
    args = ap.parse_args()

    veri = json.load(open(args.girdi, encoding='utf-8'))
    features = veri['features']
    if args.birim:
        features = [f for f in features if f['properties']['birim'] == args.birim]
        if not features:
            raise SystemExit(f"'{args.birim}' biriminde çatı bulunamadı")
    print(f'{len(features)} çatı okundu <- {os.path.basename(args.girdi)}' +
          (f" (yalnız '{args.birim}')" if args.birim else ''))
    x0, y0, x1, y1 = sinirlar(features)
    features = hafiflet(features)
    harita = folium.Map(location=[(y0 + y1) / 2, (x0 + x1) / 2], zoom_start=14, tiles=None, prefer_canvas=True)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(harita)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery', name='Uydu görüntüsü',
    ).add_to(harita)

    katman_ekle(harita, features, 'Çatı tipi', lambda p: RENK_TIP.get(p['tip'], '#999999'), ac=True)
    katman_ekle(harita, features, 'Oturtma güvenilirliği',
                lambda p: RENK_GUVENILIR if p['oturtma_orani'] >= ESIK_OTURTMA else RENK_SUPHELI)
    kamu_features = [f for f in features if f['properties'].get('kamu')]
    if kamu_features:
        katman_ekle(harita, kamu_features, f'Kamu binaları ({len(kamu_features)})', lambda p: RENK_KAMU,
                    alanlar=TOOLTIP_ALANLAR_KAMU, basliklar=TOOLTIP_BASLIK_KAMU)

    folium.LayerControl(collapsed=False).add_to(harita)
    harita.fit_bounds([[y0, x0], [y1, x1]])

    ek = f'_{args.birim.replace(" ", "_")}' if args.birim and not args.cikti else ''
    cikti = args.cikti or os.path.splitext(args.girdi)[0] + ek + '_harita.html'
    harita.save(cikti)
    print(f'-> {cikti} ({os.path.getsize(cikti) / 1e6:.2f} MB)')


if __name__ == '__main__':
    main()
