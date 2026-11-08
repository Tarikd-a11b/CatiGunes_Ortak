# -*- coding: utf-8 -*-
"""Gorsel kontrol kararlarinin INSAN onayi (2026-10-16).
  python scripts/gorsel_onay.py sayfa          -> veri/elle/gorsel_onay.html (tarayicida ac, cevrimdisi calisir)
  python scripts/gorsel_onay.py isle <csv>     -> sayfadan indirilen CSV'yi veri/elle/gorsel_kontrol.csv'ye isler
Sayfa: gorsel_kontrol.csv'deki her karar (Claude) + kontrol icin 40 rastgele "temiz" cati.
Elenen catilarin kesiti son halde olmadigi icin goruntu ham karolardan uretilir (ham geometri + blok kaymasi);
kalan catilar icin hizali son hal geometrisi kullanilir."""
import base64, io, json, math, os, sys
import pandas as pd, geopandas as gpd
from PIL import Image, ImageDraw
from shapely import affinity

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = lambda *p: os.path.join(KOK, 'veri', *p)
MV = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi')
GK = V('elle', 'gorsel_kontrol.csv')
KARARLAR = ['sorun_yok', 'mevcut_ges_tam', 'mevcut_ges_kismi', 'bina_yok', 'cati_degil', 'goruntu_kotu', 'agac_alti', 'sekil_uyumsuz']
Z, R = 19, 6378137.0
N = 256 * 2 ** Z


def px(lon, lat):
    x = (lon + 180) / 360 * N
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * N
    return x, y


def kesit(g, klasor, tampon_m=18, boy=300):
    ring = list((g if g.geom_type == 'Polygon' else max(g.geoms, key=lambda q: q.area)).exterior.coords)
    p = [px(x, y) for x, y in ring]; xs, ys = zip(*p)
    t = tampon_m / (2 * math.pi * R * math.cos(math.radians(g.centroid.y)) / N)
    x0, y0, x1, y1 = int(min(xs) - t), int(min(ys) - t), int(max(xs) + t) + 1, int(max(ys) + t) + 1
    im = Image.new('RGB', (x1 - x0, y1 - y0), (40, 40, 40))
    for tx in range(x0 // 256, x1 // 256 + 1):
        for ty in range(y0 // 256, y1 // 256 + 1):
            f = os.path.join(V('ham', 'goruntu', klasor), '%d_%d_%d.jpg' % (Z, tx, ty))
            if os.path.exists(f): im.paste(Image.open(f).convert('RGB'), (tx * 256 - x0, ty * 256 - y0))
    d = ImageDraw.Draw(im); q = [(x - x0, y - y0) for x, y in p]
    d.line(q + [q[0]], fill=(255, 0, 255), width=2)
    im.thumbnail((boy, boy))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=80)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


def sayfa():
    gk = pd.read_csv(GK, dtype=str)
    cat = gpd.read_file(os.path.join(MV, 'catilar.gpkg'), layer='catilar')
    cat['mg'] = cat.mevcut_ges
    temiz = cat[cat.gorsel_kontrol.isna() & cat.mevcut_ges.isna()].sample(40, random_state=7)
    # ham geometriler (elenenler icin) + blok kaymasi (LG03 varsayimi; gorsel kontrol icin yeterli)
    ham = pd.concat([gpd.read_file(V('ham', 'osm', 'binalar_ataturk_osb.geojson'))[['osm', 'geometry']].assign(b='osb'),
                     gpd.read_file(V('ham', 'osm', 'binalar_cigli.geojson'))[['osm', 'geometry']].assign(b='kamu')])
    mo = gpd.read_file(V('ham', 'ms', 'ms_binalar_ataturk_osb.geojson')); mo['osm'] = ['ms_osb/%d' % i for i in mo.index]
    mc = gpd.read_file(V('ham', 'ms', 'ms_binalar_cigli.geojson')); mc['osm'] = ['ms/%d' % i for i in mc.index]
    ham = gpd.GeoDataFrame(pd.concat([ham, mo[['osm', 'geometry']].assign(b='osb'), mc[['osm', 'geometry']].assign(b='kamu')]),
                           crs=4326).drop_duplicates('osm').set_index('osm')
    kb = pd.read_csv(os.path.join(MV, 'cati_kesitleri', 'kayma_bloklari.csv'))
    kb = kb[kb.uydu == 'LG03'].set_index(['bolge', 'ayak_izi']).loc[:, ['dogu_m', 'kuzey_m']]
    ci = cat.set_index('osm')
    kayit = []
    satirlar = [(r.osm, r.karar, r['not'] if isinstance(r['not'], str) else '') for _, r in gk.iterrows()] + \
               [(o, 'sorun_yok', 'kontrol orneklemi: Claude sorun gormedi') for o in temiz.osm]
    for o, k, nt in satirlar:
        if k == 'mevcut_ges': k = 'mevcut_ges_kismi' if nt.startswith('kismi') else 'mevcut_ges_tam'
        if o in ci.index:
            g, b, durum = ci.at[o, 'geometry'], ('osb' if ci.at[o, 'bolge'] == 'ataturk_osb' else 'kamu'), 'listede'
            ek = ci.at[o, 'kurum_ad'] if isinstance(ci.at[o, 'kurum_ad'], str) else ci.at[o, 'tur']
            alan = ci.at[o, 'alan_m2']
        elif o in ham.index:
            g, b, durum = ham.at[o, 'geometry'], ham.at[o, 'b'], 'elendi'
            src = 'Microsoft' if o.startswith('ms') else 'OSM'
            s = kb.loc[(b, src)] if (b, src) in kb.index else pd.Series({'dogu_m': 0, 'kuzey_m': 0})
            u = gpd.GeoSeries([g], crs=4326).to_crs(32635).iloc[0]
            g = gpd.GeoSeries([affinity.translate(u, s.dogu_m, s.kuzey_m)], crs=32635).to_crs(4326).iloc[0]
            ek, alan = '', gpd.GeoSeries([u], crs=32635).area.iloc[0]
        else:
            print('geometri bulunamadi:', o); continue
        kayit.append({'osm': o, 'claude': k, 'not': nt, 'bolge': b, 'durum': durum, 'ek': ek, 'alan': round(float(alan)),
                      'img': kesit(g, 'ataturk_osb' if b == 'osb' else 'cigli_kamu')})
    html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gorsel_onay_sablon.html'), encoding='utf-8').read()
    html = html.replace('/*VERI*/[]', json.dumps(kayit, ensure_ascii=False)).replace('/*KARARLAR*/[]', json.dumps(KARARLAR))
    out = V('elle', 'gorsel_onay.html')
    open(out, 'w', encoding='utf-8').write(html)
    print('%d kart (%d karar + %d kontrol orneklemi) -> %s (%.1f MB)' % (
        len(kayit), len(gk), len(temiz), out, os.path.getsize(out) / 1e6))


def isle(yol):
    """Sayfadan indirilen CSV: osm, claude, insan, insan_not, kontrol_eden, tarih."""
    o = pd.read_csv(yol, dtype=str).fillna('')
    gk = pd.read_csv(GK, dtype=str).fillna('')
    eski = gk.set_index('osm')
    yeni = []
    for _, r in o.iterrows():
        k = r.insan or r.claude
        karar, nt = k, eski.at[r.osm, 'not'] if r.osm in eski.index else ''
        if k.startswith('mevcut_ges_'):
            karar = 'mevcut_ges'; nt = ('tam: catinin cogu panelli' if k.endswith('tam') else 'kismi: catinin bir bolumu panelli')
        if r.insan_not: nt = (nt + ' | ' if nt else '') + 'insan: ' + r.insan_not
        if karar == 'sorun_yok': continue           # kayit olusturmaz (varsa siler)
        yeni.append({'osm': r.osm, 'karar': karar, 'not': nt, 'kontrol_eden': r.kontrol_eden, 'tarih': r.tarih})
    kalan = gk[~gk.osm.isin(o.osm)]                  # sayfada olmayan eski kararlar oldugu gibi kalir
    son = pd.concat([kalan, pd.DataFrame(yeni)], ignore_index=True)
    son.to_csv(GK, index=False, encoding='utf-8')
    deg = (o.insan != '') & (o.insan != o.claude)
    print('islendi: %d kart, %d degistirildi, %d onaylandi -> %s' % (len(o), deg.sum(), (~deg).sum(), GK))
    print('simdi: python scripts/kur.py  (son hali yeni kararlarla yeniden kurar)')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'isle': isle(sys.argv[2])
    else: sayfa()
