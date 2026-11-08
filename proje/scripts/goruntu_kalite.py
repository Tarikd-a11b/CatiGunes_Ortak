# -*- coding: utf-8 -*-
"""Uydu karolarinin (Esri World Imagery z19) kalite ve gereklilik denetimi (2026-10-15).
Her karo icin:
  gereklilik : karonun ne kadari analize girecek catilarla (osb_catilari / kamu_catilari, MS ile birlesim) kaplı;
               cati yok -> 'gereksiz' (yol, bos arsa, tampon). Tampon: cati kenarindan 15 m icindeki karolar 'kenar'.
  bozukluk   : dosya acilmiyor / tek renk / "Map data not yet available" tipi gri karo / ayni icerik (sha1) tekrar
  netlik     : Laplace varyansi (dusuk = bulanik / yukari orneklenmis)
  isik       : koyu piksel orani (golge), doymus beyaz orani (parlama, beyaz cati)
  cekim      : en yakin Esri metadata noktasi (_cekim_bilgisi.json; seyrek orneklem -> sinir karolarinda yaklasik)
Cikti: veri/inceleme/goruntu_kalite.xlsx (+ ornek mozaik png'leri veri/inceleme/goruntu_ornek/)."""
import hashlib, json, math, os
import numpy as np, pandas as pd, geopandas as gpd
from PIL import Image
from shapely.geometry import Polygon

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = lambda *p: os.path.join(KOK, 'veri', *p)
G = V('ham', 'goruntu')
Z = 19
OUT = V('inceleme', 'goruntu_ornek'); os.makedirs(OUT, exist_ok=True)


def tile_poly(x, y, z=Z):
    n = 1 << z
    def ll(x, y): return x / n * 360.0 - 180.0, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    (a, b), (c, e) = ll(x, y), ll(x + 1, y + 1)
    return Polygon([(a, b), (c, b), (c, e), (a, e)])


def olc(p):
    r = {'okunuyor': True}
    try:
        im = np.asarray(Image.open(p).convert('RGB'), dtype=np.float32)
    except Exception:
        return {'okunuyor': False}
    g = im.mean(2)
    lap = g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    r.update(boyut_px='%dx%d' % (im.shape[1], im.shape[0]), dosya_kb=round(os.path.getsize(p) / 1024, 1),
             parlaklik=round(float(g.mean()), 1), kontrast_std=round(float(g.std()), 1),
             netlik_lap=round(float(lap.var()), 1),
             koyu_orani=round(float((g < 40).mean()), 3), beyaz_orani=round(float((im.min(2) > 245).mean()), 3),
             doygunluk=round(float((im.max(2) - im.min(2)).mean()), 1),
             sha1=hashlib.sha1(open(p, 'rb').read()).hexdigest())
    return r


# catilar (OSM + Cigli/OSB MS birlesimi: OSM ~4 m kayik oldugu icin her iki kaynak da sayilir)
cat = pd.concat([gpd.read_file(V('islenmis', 'osb_catilari.geojson'))[['geometry']].assign(bolge='ataturk_osb'),
                 gpd.read_file(V('islenmis', 'kamu_catilari.geojson'))[['geometry']].assign(bolge='cigli_kamu')])
cat = gpd.GeoDataFrame(cat, crs=4326).to_crs(32635)
ms = pd.concat([gpd.read_file(V('ham', 'ms', 'ms_binalar_ataturk_osb.geojson'))[['geometry']]]).to_crs(32635)
ms = ms[ms.intersects(cat[cat.bolge == 'ataturk_osb'].union_all().buffer(2))]   # yalniz analiz catisina degen MS
cati_alani = pd.concat([cat[['geometry']], ms[['geometry']]]).union_all()
cati_tampon = cat.union_all().buffer(15)
cekim = pd.DataFrame(json.load(open(os.path.join(G, '_cekim_bilgisi.json'), encoding='utf-8'))['noktalar'])

satir = []
for bolge in ('ataturk_osb', 'cigli_kamu'):
    for f in sorted(os.listdir(os.path.join(G, bolge))):
        if not f.endswith('.jpg'): continue
        _, x, y = map(int, f[:-4].split('_'))
        tp = gpd.GeoSeries([tile_poly(x, y)], crs=4326).to_crs(32635).iloc[0]
        r = {'bolge': bolge, 'karo': f, 'x': x, 'y': y}
        r['cati_kaplama'] = round(tp.intersection(cati_alani).area / tp.area, 3)
        r['cati_tamponunda'] = tp.intersects(cati_tampon)
        c = tp.centroid; ll = gpd.GeoSeries([c], crs=32635).to_crs(4326).iloc[0]
        d = (cekim.lon - ll.x) ** 2 + (cekim.lat - ll.y) ** 2
        e = cekim.loc[d.idxmin()]
        r.update(cekim_tarihi=e.cekim_tarihi, uydu=e.uydu, gercek_cozunurluk_m=float(e.cozunurluk_m),
                 lon=round(ll.x, 5), lat=round(ll.y, 5))
        r.update(olc(os.path.join(G, bolge, f)))
        satir.append(r)
df = pd.DataFrame(satir)

# bayraklar
df['tekrar_icerik'] = df.duplicated('sha1', keep=False)
lap_esik = df.netlik_lap.quantile(0.05)
def durum(r):
    if not r.okunuyor: return 'BOZUK: acilmiyor'
    if r.kontrast_std < 4: return 'BOZUK: tek renk / veri yok karosu'
    if r.tekrar_icerik: return 'SUPHELI: ayni icerik baska karoda da var'
    if r.cati_kaplama == 0 and not r.cati_tamponunda: return 'GEREKSIZ: cati yok (yol / bos arsa / tampon)'
    if r.cati_kaplama == 0: return 'KENAR: cati yok ama cati kenarina 15 m icinde (kirpma icin gerekebilir)'
    return 'GEREKLI'
df['durum'] = df.apply(durum, axis=1)
df['netlik_notu'] = np.where(df.netlik_lap < lap_esik, 'bulanik (en alttaki %5)', None)

# ornek mozaikler: her durumdan 6 karo
for d, g in df.groupby('durum'):
    s = g.sample(min(6, len(g)), random_state=0)
    im = Image.new('RGB', (256 * len(s), 256), 'white')
    for i, (_, r) in enumerate(s.iterrows()):
        try: im.paste(Image.open(os.path.join(G, r.bolge, r.karo)).convert('RGB'), (256 * i, 0))
        except Exception: pass
    im.save(os.path.join(OUT, '%s.jpg' % d.split(':')[0].lower()), quality=85)

with pd.ExcelWriter(V('inceleme', 'goruntu_kalite.xlsx'), engine='openpyxl') as w:
    oz = df.groupby(['bolge', 'durum']).agg(karo=('karo', 'size'), mb=('dosya_kb', lambda s: round(s.sum() / 1024, 1)),
                                            ort_cati_kaplama=('cati_kaplama', 'mean')).round(3).reset_index()
    oz.to_excel(w, sheet_name='Ozet', index=False)
    df.groupby(['bolge', 'cekim_tarihi', 'uydu', 'gercek_cozunurluk_m']).agg(
        karo=('karo', 'size'), medyan_netlik=('netlik_lap', 'median'), medyan_koyu=('koyu_orani', 'median')) \
        .round(3).reset_index().to_excel(w, sheet_name='Cekim', index=False)
    df.drop(columns=['sha1']).to_excel(w, sheet_name='Karolar', index=False)
    for ws in w.sheets.values():
        ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(50, max(8, *(len(str(c.value or '')) for c in col[:300])) + 2)

pd.set_option('display.width', 200)
print(oz.to_string())
print(df.groupby(['bolge', 'cekim_tarihi', 'uydu']).agg(karo=('karo', 'size'), netlik=('netlik_lap', 'median'),
                                                         koyu=('koyu_orani', 'median')).round(3).to_string())
print('netlik esigi (alt %%5): %.1f' % lap_esik, '| boyutlar:', df.boyut_px.value_counts().to_dict())
print('kaplama dagilimi (gerekli):', df[df.durum == 'GEREKLI'].cati_kaplama.describe().round(3).to_dict())
