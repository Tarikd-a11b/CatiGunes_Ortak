# -*- coding: utf-8 -*-
"""Kayik / yanlis sekilli ayak izlerinin goruntu uzerinde ELLE duzeltilmesi (2026-10-22).
  python scripts/ayak_izi_duzeltme.py sayfa          -> veri/elle/ayak_izi_duzeltme.html (tarayicida ac, cevrimdisi calisir)
  python scripts/ayak_izi_duzeltme.py isle <csv..>   -> sayfadan indirilen CSV'leri veri/elle/ayak_izi_duzeltme.csv'ye isler
Neden: SAM koşusunda (OSB 1.001 + kamu 80) bazi catilarda sorun SAM degil ayak izi poligonu: goruntuye gore kayik,
iki catinin arasina dusmus, avlu/sundurma iceriyor. Bu catilarda SAM puanlari (kaplama/tasma) yaniltici.
Sayfa: Model_Verisi kesitinin uzerinde mevcut (hizali) poligon; kisi 'dogru' der, poligonu kaydirir ya da yeniden cizer.
Cikti poligonu GORUNTU (Esri) cercevesindedir -> cati_listesi.py geometriyi degistirir, cati_kesit.py bu catilari kaydirmaz.
Adaylar: OSB SAM (2026-10-17/21 kosusu) tasma > 0,2 olan 38 cati + Model_Verisi'nde kalan sekil_uyumsuz isaretliler
+ kamu SAM degerlendirmesinde (2026-10-18) ayak izi kayik bulunan 3 cati. Once Claude'un gozle supheli buldugu 11 cati."""
import base64, csv, io, json, math, os, sys
from datetime import date
import pandas as pd, geopandas as gpd
from PIL import Image
from shapely.geometry import Polygon

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = lambda *p: os.path.join(KOK, 'veri', *p)
MV = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi')
CIKTI = V('elle', 'ayak_izi_duzeltme.csv')
R = 6378137.0

ONCE = ['way/503349290', 'way/865661863', 'way/865661868', 'way/867759563', 'way/871788788', 'ms_osb/305',
        'ms_osb/733', 'way/879934579', 'way/879934560', 'ms_osb/750', 'way/927242530']
KAMU_KAYIK = ['way/926752786', 'way/661706992', 'ms/13923']
SAM_TASMA = ['ms_osb/733', 'way/503346879', 'ms_osb/305', 'way/879934584', 'way/503345419', 'way/503336080', 'way/879934560',
             'way/879934579', 'way/927242607', 'way/867759563', 'way/871788788', 'way/503404894', 'way/927242648',
             'way/503238938', 'way/503183978', 'way/865661868', 'way/927242647', 'way/927242670', 'way/877563353',
             'way/503349290', 'way/867759565', 'way/503345420', 'way/503238921', 'way/927242592', 'way/503346885',
             'way/927242468', 'way/873213201', 'way/927242649', 'way/503402486', 'way/868369010', 'ms_osb/203',
             'way/927242681', 'way/927242686', 'way/927242599', 'way/927242646', 'way/927242530', 'ms_osb/750',
             'way/865661863']


def sayfa():
    cat = pd.read_csv(os.path.join(MV, 'catilar.csv'), dtype={'osm': str})
    idx = pd.read_csv(os.path.join(MV, 'cati_kesitleri', 'indeks.csv')).set_index('osm')
    aday = list(dict.fromkeys(ONCE + KAMU_KAYIK + cat.osm[cat.gorsel_kontrol.eq('sekil_uyumsuz')].tolist() + SAM_TASMA))
    ci = cat.set_index('osm'); kayit = []
    for o in aday:
        if o not in idx.index: print('kesit yok, atlandi:', o); continue
        r = idx.loc[o]
        im = Image.open(os.path.join(MV, 'cati_kesitleri', r.kesit)).convert('RGB')
        b = io.BytesIO(); im.save(b, 'JPEG', quality=88)
        c = ci.loc[o] if o in ci.index else None
        kayit.append({'osm': o, 'cati_id': int(c.cati_id) if c is not None else None, 'bolge': r.bolge,
                      'ad': (c.kurum_ad if c is not None and isinstance(c.kurum_ad, str) else ''),
                      'alan': float(r.alan_m2), 'mpp': float(r.yer_m_px), 'w': im.width, 'h': im.height,
                      'poly': json.loads(r.poligon_px), 'once': o in ONCE or o in KAMU_KAYIK,
                      'gk': (c.gorsel_kontrol if c is not None and isinstance(c.gorsel_kontrol, str) else ''),
                      'img': 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()})
    sab = open(os.path.join(KOK, 'scripts', 'ayak_izi_duzeltme_sablon.html'), encoding='utf-8').read()
    out = V('elle', 'ayak_izi_duzeltme.html')
    open(out, 'w', encoding='utf-8').write(sab.replace('/*VERI*/[]', json.dumps(kayit, ensure_ascii=False)))
    print('%d cati -> %s (%.1f MB)' % (len(kayit), out, os.path.getsize(out) / 1e6))


def px_lonlat(kesit, pts):
    """kesit pikseli -> lon/lat. .jgw: piksel MERKEZI; poligon_px kose tabanli (cati_kesit.py) -> yarim piksel geri."""
    a, _, _, e, c, f = [float(x) for x in open(os.path.join(MV, 'cati_kesitleri', kesit[:-4] + '.jgw')).read().split()]
    out = []
    for x, y in pts:
        mx, my = c - a / 2 + x * a, f - e / 2 + y * e
        out.append((round(math.degrees(mx / R), 8), round(math.degrees(math.atan(math.sinh(my / R))), 8)))
    return out


CAKISMA_ESIK = 0.15   # duzeltilen poligonun ya da komsunun >%15'i ortusuyorsa duzeltme uygulanmaz


def cakisma(d, idx):
    """2026-10-22 (kullanici: "binalar yan yana, catilar buyumesin"): duzeltilen poligon komsu catiya tasmamali (cift sayim).
    Komsunun ya da kendisinin > CAKISMA_ESIK kadari ortusuyorsa -> karar 'cakisma' (uygulanmaz, cati eski haliyle kalir);
    daha kucuk ortusmede komsu poligon kesilerek cikarilir (kenar payi)."""
    hiz = {o: Polygon(px_lonlat(k, json.loads(p))) for o, k, p in zip(idx.index, idx.kesit, idx.poligon_px)}
    hiz = gpd.GeoSeries(hiz, crs=4326).to_crs(32635)
    duz = d.karar.eq('duzeltildi') & d.osm.isin(hiz.index)   # Model_Verisi'nden cikmis cati (or. <200 m2) atlanir
    for _ in range(2):   # cakisma'ya dusenler komsu olarak eski haline doner -> bir tur daha kontrol
        yeni = gpd.GeoSeries.from_wkt(d.wkt[duz].values, index=d.osm[duz].values, crs=4326).to_crs(32635)
        komsu = hiz.copy(); komsu.loc[yeni.index] = yeni.values
        for o, g in yeni.items():
            k = komsu.drop(o); k = k[k.intersects(g)]
            pay = [(g.intersection(h).area, h.area) for h in k]
            if any(a > CAKISMA_ESIK * min(g.area, b) for a, b in pay):
                j = d.index[d.osm.eq(o)][0]
                d.loc[j, 'karar'] = 'cakisma'; d.loc[j, 'not'] = 'komsu catiya tasiyor, uygulanmadi (%s)' % ', '.join(
                    '%s %%%d' % (n, 100 * a / min(g.area, b)) for n, (a, b) in zip(k.index, pay) if a > 1)
                duz = d.karar.eq('duzeltildi') & d.osm.isin(hiz.index)   # Model_Verisi'nden cikmis cati (or. <200 m2) atlanir
    yeni = gpd.GeoSeries.from_wkt(d.wkt[duz].values, index=d.osm[duz].values, crs=4326).to_crs(32635)
    komsu = hiz.copy(); komsu.loc[yeni.index] = yeni.values
    for o, g in yeni.items():
        k = komsu.drop(o); k = k[k.intersects(g)]
        if len(k) and g.intersection(k.union_all()).area > 1:
            g2 = g.difference(k.union_all())
            g2 = max(g2.geoms, key=lambda q: q.area) if g2.geom_type == 'MultiPolygon' else g2
            d.loc[d.osm.eq(o), 'wkt'] = gpd.GeoSeries([g2], crs=32635).to_crs(4326).iloc[0].wkt
    print('cakisma (uygulanmadi): %s' % d.osm[d.karar.eq('cakisma')].tolist())
    return d


def isle(dosyalar):
    idx = pd.read_csv(os.path.join(MV, 'cati_kesitleri', 'indeks.csv')).set_index('osm')
    eski = pd.read_csv(CIKTI, dtype=str) if os.path.exists(CIKTI) else pd.DataFrame(columns=['osm', 'karar', 'wkt', 'not', 'kontrol_eden', 'tarih'])
    yeni = []
    for f in dosyalar:
        for r in csv.DictReader(open(f, encoding='utf-8-sig')):
            if r['karar'] not in ('dogru', 'duzeltildi'): continue
            wkt = ''
            if r['karar'] == 'duzeltildi':
                pts = json.loads(r['poligon_px'])
                g = Polygon(px_lonlat(idx.loc[r['osm'], 'kesit'], pts))
                if not g.is_valid or len(pts) < 3: print('GECERSIZ poligon, atlandi:', r['osm']); continue
                wkt = g.wkt
            yeni.append({'osm': r['osm'], 'karar': r['karar'], 'wkt': wkt, 'not': r.get('not', ''),
                         'kontrol_eden': r.get('kontrol_eden', ''), 'tarih': r.get('tarih') or date.today().isoformat()})
    d = pd.concat([eski, pd.DataFrame(yeni)]).drop_duplicates('osm', keep='last')
    d = cakisma(d, idx)
    d.to_csv(CIKTI, index=False, encoding='utf-8')
    print('%d yeni kayit; toplam %s -> %s' % (len(yeni), d.karar.value_counts().to_dict(), CIKTI))
    # alan degisimi raporu
    cat = gpd.read_file(os.path.join(MV, 'catilar.gpkg'), layer='catilar').set_index('osm')
    for r in d[d.karar.eq('duzeltildi')].itertuples():
        yeni_a = gpd.GeoSeries.from_wkt([r.wkt], crs=4326).to_crs(32635).area.iloc[0]
        print('  %-16s alan %7.1f -> %7.1f m2' % (r.osm, cat.alan_m2.get(r.osm, float('nan')), yeni_a))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sayfa': sayfa()
    elif len(sys.argv) > 2 and sys.argv[1] == 'isle': isle(sys.argv[2:])
    else: print(__doc__)
