# -*- coding: utf-8 -*-
"""Her analiz catisi icin SAM'e hazir, konumlu goruntu kesiti uretir (2026-10-15).
Neden: ham veri 256 px'lik konumsuz z19 karolari; buyuk catilar 10+ karoya bolunuyor, karolarin ~%35'i yol/bos arsa,
OSM ayak izleri goruntuye gore ~4 m guneybatiya kayik (bkz. cati_listesi.py MS karsilastirmasi).
Yontem:
  1) goruntu blogu (uydu: LG03 2026-01 / WV02 2025-10) x ayak izi kaynagi basina sistematik kaymayi DOGRUDAN Esri
     goruntusunden olc: orneklem catilarda poligon sinirini goruntu kenarlarina oturtan kaydirmanin medyani.
     (Ilk deneme MS'e gore kaydirmakti; MS Bing goruntusune gore cizildigi icin Esri'de kuzeye fazla kaciyordu.)
  1b) her catiya +-3 m ince ayar (cok katli binada egik bakis kaymasi); kazanc < %15 ise ince ayar yok.
  2) kaydirilmis catinin sinir kutusu + TAMPON_M tampon -> z19 global piksel penceresi -> karolardan birlestir -> kirp.
  3) her kesite .jgw (world file, EPSG:3857) -> QGIS'te konumlu acilir.
Cikti: veri/islenmis/cati_kesitleri/<bolge>/<id>.jpg + .jgw
       veri/islenmis/cati_kesitleri/indeks.csv  (kesit, kutu_px = SAM kutu istemi, poligon_px, m/px, cekim, eksik karo)
       veri/islenmis/cati_kesitleri/kontrol_ornek.jpg (kaydirilmis poligonlar goruntu ustunde)"""
import json, math, os
import numpy as np, pandas as pd, geopandas as gpd
from PIL import Image, ImageDraw
from shapely import affinity

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = lambda *p: os.path.join(KOK, 'veri', *p)
Z, TAMPON_M = 19, 15
N = 256 * (1 << Z)                               # z19 global piksel genisligi
R = 6378137.0
OUT = V('islenmis', 'cati_kesitleri')
KARO = [V('ham', 'goruntu', 'ataturk_osb'), V('ham', 'goruntu', 'cigli_kamu')]


def px(lon, lat):
    return ((lon + 180) / 360 * N,
            (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * N)


def kayma(cat, ms):
    """OSM catisi -> en cok ortusen MS binasi; boyut orani 0,8-1,25 olanlarda merkez farki medyani (m, EPSG:32635)."""
    a = cat.to_crs(32635); b = ms.to_crs(32635).reset_index(drop=True)
    j = gpd.sjoin(a[['osm', 'geometry']], b[['geometry']], predicate='intersects')
    j['mg'] = b.geometry.iloc[j.index_right.values].values
    j['ov'] = [g.intersection(h).area for g, h in zip(j.geometry, j.mg)]
    j = j.sort_values('ov').drop_duplicates('osm', keep='last')
    j['oran'] = gpd.GeoSeries(j.mg).area.values / j.geometry.area.values
    j = j[(j.oran > 0.8) & (j.oran < 1.25)]
    dx = gpd.GeoSeries(j.mg).centroid.x.values - j.geometry.centroid.x.values
    dy = gpd.GeoSeries(j.mg).centroid.y.values - j.geometry.centroid.y.values
    return float(np.median(dx)), float(np.median(dy)), len(j)


def karo_ac(x, y, onbellek={}):
    # HATA DUZELTMESI (2026-10-16): onbellek eskiden karo yuklendikten SONRA temizleniyordu -> yeni karo da siliniyor,
    # fonksiyon None donuyor, kesitte sahte "eksik karo" (siyah kare) cikiyordu. Temizlik artik yuklemeden once.
    if (x, y) in onbellek: return onbellek[(x, y)]
    if len(onbellek) > 400: onbellek.clear()
    im = None
    for d in KARO:
        p = os.path.join(d, '%d_%d_%d.jpg' % (Z, x, y))
        if os.path.exists(p): im = Image.open(p).convert('RGB'); break
    onbellek[(x, y)] = im
    return im


def yerel_hizala(im, poly, max_px):
    """Poligon sinirini goruntudeki kenarlara oturtan kaydirmayi arar (+-max_px). Puan = sinir boyunca ortalama gradyan.
    Cok katli binada cati, uydunun egik bakisi yuzunden ayak izine gore kayar; sabit kayma yetmez."""
    g = np.asarray(im.convert('L'), dtype=np.float32)
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]; gy[1:-1, :] = g[2:, :] - g[:-2, :]
    mag = np.hypot(gx, gy)
    mask = Image.new('L', im.size, 0); ImageDraw.Draw(mask).line(poly + [poly[0]], fill=1, width=3)
    ys, xs = np.nonzero(np.asarray(mask))
    if len(xs) < 20: return 0, 0, 1.0
    def puan(dx, dy):
        x, y = xs + dx, ys + dy
        ok = (x >= 0) & (y >= 0) & (x < g.shape[1]) & (y < g.shape[0])
        return mag[y[ok], x[ok]].mean() if ok.mean() > 0.9 else 0
    p0 = puan(0, 0); en = (p0, 0, 0)
    for dy in range(-max_px, max_px + 1, 2):
        for dx in range(-max_px, max_px + 1, 2):
            v = puan(dx, dy)
            if v > en[0]: en = (v, dx, dy)
    return en[1], en[2], (en[0] / p0 if p0 else 1.0)


YEREL_MAX_M, INCE_MAX_M, YEREL_ESIK = 8, 3, 1.15   # blok olcumu +-8 m, cati basina ince ayar +-3 m; puan %15'ten az artarsa kaydirma

catilar = {'osb': gpd.read_file(V('islenmis', 'osb_catilari.geojson')),
           'kamu': gpd.read_file(V('islenmis', 'kamu_catilari.geojson'))}
msler = {'osb': gpd.read_file(V('ham', 'ms', 'ms_binalar_ataturk_osb.geojson')),
         'kamu': gpd.read_file(V('ham', 'ms', 'ms_binalar_cigli.geojson'))}
cekim = pd.DataFrame(json.load(open(V('ham', 'goruntu', '_cekim_bilgisi.json'), encoding='utf-8'))['noktalar'])

def kesit(g):
    """catinin z19 piksel halkasi + tamponlu goruntu kesiti."""
    ring = [px(x, y) for x, y in (g.exterior.coords if g.geom_type == 'Polygon' else max(g.geoms, key=lambda q: q.area).exterior.coords)]
    xs, ys = zip(*ring)
    mpp = 2 * math.pi * R * math.cos(math.radians(g.centroid.y)) / N    # yer metresi / piksel
    t = TAMPON_M / mpp
    x0, y0, x1, y1 = int(min(xs) - t), int(min(ys) - t), int(math.ceil(max(xs) + t)), int(math.ceil(max(ys) + t))
    im = Image.new('RGB', (x1 - x0, y1 - y0)); eksik = 0
    for tx in range(x0 // 256, x1 // 256 + 1):
        for ty in range(y0 // 256, y1 // 256 + 1):
            k = karo_ac(tx, ty)
            if k is None: eksik += 1; continue
            im.paste(k, (tx * 256 - x0, ty * 256 - y0))
    return ring, mpp, (x0, y0, x1, y1), im, eksik


def blok(lon, lat):
    d = (cekim.lon - lon) ** 2 + (cekim.lat - lat) ** 2
    return cekim.loc[d.idxmin()]


def kaydir(cat, dogu, kuzey):
    u = cat.to_crs(32635)
    u['geometry'] = [affinity.translate(g, dogu, kuzey) for g in u.geometry]
    return u.to_crs(4326).geometry.values


satir, ornek, kayma_tablo = [], [], []
for bolge, cat in catilar.items():
    os.makedirs(os.path.join(OUT, bolge), exist_ok=True)
    for f in os.listdir(os.path.join(OUT, bolge)):   # elenen catilarin eski kesitleri kalmasin
        if f.endswith(('.jpg', '.jgw')): os.remove(os.path.join(OUT, bolge, f))
    cat = cat.copy()
    cat['uydu'] = [blok(g.centroid.x, g.centroid.y).uydu for g in cat.geometry]
    # 2026-10-17: universite kampusu (OSB'nin kuzeyi) ayri blok -> Cigli okul/hastane blok kaymasi ve orneklemi degismez
    cat['grup'] = np.where(cat['tur'].eq('universite'), 'universite', 'genel') if 'tur' in cat else 'genel'
    # 2026-10-22: elle duzeltilen ayak izi zaten goruntu cercevesinde. Hizalama (blok + ince + kume) ESKI ayak iziyle
    # aynen hesaplanir -> diger catilarin kaymasi degismez; duzeltilmis poligon yalniz en sonda, kaydirilmadan konur.
    elle = cat.ham_wkt.notna() if 'ham_wkt' in cat else pd.Series(False, cat.index)
    elle_geo = cat.geometry[elle].copy()
    elle_alan = cat.alan_m2[elle].copy()
    cat.loc[elle, 'geometry'] = gpd.GeoSeries.from_wkt(cat.ham_wkt[elle].str.split('|').str[0], crs=4326).values
    cat.loc[elle, 'alan_m2'] = cat.ham_wkt[elle].str.split('|').str[1].astype(float)
    msx, msy, n = kayma(cat[cat.ayak_izi_kaynagi == 'OSM'], msler[bolge])
    # 1. asama: goruntu blogu (uydu) basina OSM -> Esri kaymasi, dogrudan goruntuden (kenar hizalama, +-YEREL_MAX_M)
    #    MS'ten olculen kayma (msx, msy) yalniz bilgi: MS Bing goruntusune gore cizilmis, Esri'ye degil.
    blok_kayma = {}
    for (uydu, kaynak, grup), gr in cat.groupby(['uydu', 'ayak_izi_kaynagi', 'grup']):
        orn = gr[gr.alan_m2 > 150].sample(min(250, (gr.alan_m2 > 150).sum()), random_state=0)
        ol = []
        for g in orn.geometry:
            ring, mpp, (x0, y0, _, _), im, _ = kesit(g)
            ldx, ldy, kaz = yerel_hizala(im, [(x - x0, y - y0) for x, y in ring], int(YEREL_MAX_M / mpp))
            if kaz >= YEREL_ESIK: ol.append((ldx * mpp, -ldy * mpp))
        bd, bk = (float(np.median([o[0] for o in ol])), float(np.median([o[1] for o in ol]))) if len(ol) >= 10 else (0.0, 0.0)
        blok_kayma[(uydu, kaynak, grup)] = (bd, bk)
        kayma_tablo.append({'bolge': bolge, 'grup': grup, 'uydu': uydu, 'ayak_izi': kaynak, 'ornek': len(orn), 'gecerli': len(ol),
                            'dogu_m': round(bd, 2), 'kuzey_m': round(bk, 2), 'ms_bing_kaymasi': '%+.1f / %+.1f' % (msx, msy)})
        print('%s/%s %s %s: blok kaymasi dogu %+.2f kuzey %+.2f m (%d/%d gecerli); MS(Bing) kaymasi %+.2f %+.2f' % (
            bolge, grup, uydu, kaynak, bd, bk, len(ol), len(orn), msx, msy))
    for (uydu, kaynak, grup), gr in cat.groupby(['uydu', 'ayak_izi_kaynagi', 'grup']):
        cat.loc[gr.index, 'geometry'] = kaydir(gr, *blok_kayma[(uydu, kaynak, grup)])
    # 2. asama: her cati icin kucuk yerel duzeltme (+-INCE_MAX_M), metre cinsinden olc
    ince = {}
    for i, r in cat.iterrows():
        ring, mpp, (x0, y0, _, _), im, _ = kesit(r.geometry)
        ldx, ldy, kaz = yerel_hizala(im, [(x - x0, y - y0) for x, y in ring], int(INCE_MAX_M / mpp))
        ince[i] = (ldx * mpp, -ldy * mpp, kaz) if kaz >= YEREL_ESIK else (0.0, 0.0, kaz)
    # 2b. bitisik binalar (<1 m) tek yapi: goruntude birlikte kayarlar -> kume icinde ORTAK ince kayma
    #     (kumenin guvenilir en buyuk catisinin kaymasi). Ayri ayri kaydirmak binalari birbirine bindiriyordu (32 ortusme).
    u = cat.to_crs(32635)
    j = gpd.sjoin(u[['geometry']].assign(geometry=u.buffer(1.0)), u[['geometry']], predicate='intersects')
    ata = {i: i for i in u.index}
    def kok(i):
        while ata[i] != i: ata[i] = ata[ata[i]]; i = ata[i]
        return i
    for a_, b_ in zip(j.index, j.index_right): ata[kok(a_)] = kok(b_)
    kume = pd.Series({i: kok(i) for i in u.index})
    son = {}
    for k_, uyeler in kume.groupby(kume):
        uy = sorted(uyeler.index, key=lambda i: -cat.at[i, 'alan_m2'])
        guv = [i for i in uy if ince[i][2] >= YEREL_ESIK]
        dd = ince[guv[0]][:2] if guv else (0.0, 0.0)
        for i in uy: son[i] = dd
    # 2c. yine de yeni ortusme dogarsa (farkli kaynak/blok komsulari) o catilar yalniz blok kaymasiyla kalir
    def kaymis():
        return gpd.GeoSeries([affinity.translate(g, *son[i]) for i, g in zip(u.index, u.geometry)], index=u.index, crs=32635)
    ham_ort = set()
    jj = gpd.sjoin(u[['geometry']], u[['geometry']], predicate='intersects')
    for a_, b_ in zip(jj.index, jj.index_right):
        if a_ < b_ and u.geometry[a_].intersection(u.geometry[b_]).area > 5: ham_ort.add((a_, b_))
    for _ in range(5):
        k_ = kaymis(); jj = gpd.sjoin(k_.to_frame('geometry'), k_.to_frame('geometry'), predicate='intersects')
        yeni = [(a_, b_) for a_, b_ in zip(jj.index, jj.index_right)
                if a_ < b_ and (a_, b_) not in ham_ort and k_[a_].intersection(k_[b_]).area > 5]
        if not yeni: break
        for a_, b_ in yeni: son[a_] = son[b_] = (0.0, 0.0)
    print('%s: %d kume (%d cok binali), kalan yeni ortusme %d, ham ortusme %d' % (
        bolge, kume.nunique(), (kume.value_counts() > 1).sum(), len(yeni), len(ham_ort)))
    for i in elle_geo.index: cat.at[i, 'geometry'] = elle_geo[i]; cat.at[i, 'alan_m2'] = elle_alan[i]; son[i] = (0.0, 0.0)
    for i, r in cat.iterrows():
        g = r.geometry
        ring, mpp, (x0, y0, x1, y1), im, eksik = kesit(g)
        kaz = ince[i][2]; ldx, ldy = son[i][0] / mpp, -son[i][1] / mpp
        once = [(x - x0, y - y0) for x, y in ring]
        ring = [(x + ldx, y + ldy) for x, y in ring]; xs, ys = zip(*ring)
        kid = r.osm.replace('/', '_')
        p = os.path.join(OUT, bolge, kid + '.jpg'); im.save(p, quality=95)
        # world file: EPSG:3857 metre; piksel boyu (Web Mercator metresi) = 2*pi*R/N
        wm = 2 * math.pi * R / N
        open(p[:-4] + '.jgw', 'w').write('%.10f\n0\n0\n%.10f\n%.4f\n%.4f\n' % (
            wm, -wm, x0 * wm - math.pi * R + wm / 2, math.pi * R - y0 * wm - wm / 2))
        poly = [(round(x - x0, 1), round(y - y0, 1)) for x, y in ring]
        e = blok(g.centroid.x, g.centroid.y); bd, bk = blok_kayma[(r.uydu, r.ayak_izi_kaynagi, r.grup)]
        satir.append({'bolge': bolge, 'osm': r.osm, 'kesit': '%s/%s.jpg' % (bolge, kid), 'alan_m2': r.alan_m2,
                      'ayak_izi_kaynagi': r.ayak_izi_kaynagi,
                      'blok_kayma_dogu_m': round(bd, 2), 'blok_kayma_kuzey_m': round(bk, 2),
                      'ince_dogu_m': round(ldx * mpp, 2), 'ince_kuzey_m': round(-ldy * mpp, 2), 'hizalama_kazanci': round(kaz, 2), 'kume_bina': int((kume == kume[i]).sum()),
                      'genislik_px': x1 - x0, 'yukseklik_px': y1 - y0, 'yer_m_px': round(mpp, 4),
                      'kutu_px': [round(min(xs) - x0, 1), round(min(ys) - y0, 1), round(max(xs) - x0, 1), round(max(ys) - y0, 1)],
                      'poligon_px': json.dumps(poly), 'eksik_karo': eksik,
                      'cekim_tarihi': e.cekim_tarihi, 'uydu': e.uydu, 'gercek_cozunurluk_m': float(e.cozunurluk_m)})
        if 600 < r.alan_m2 < 4000 and sum(o[3] == bolge for o in ornek) < 6:
            ornek.append((im.copy(), once, poly, bolge))

idx = pd.DataFrame(satir)
idx.to_csv(os.path.join(OUT, 'indeks.csv'), index=False, encoding='utf-8')
# kontrol paneli
pan = Image.new('RGB', (4 * 320, 3 * 320), 'white')
for i, (im, once, poly, _) in enumerate(ornek):   # sari: blok kaymasi, mor: + cati basina ince ayar
    d = ImageDraw.Draw(im); d.line(once + [once[0]], fill=(255, 230, 0), width=2); d.line(poly + [poly[0]], fill=(255, 0, 255), width=3)
    im.thumbnail((320, 320)); pan.paste(im, ((i % 4) * 320, (i // 4) * 320))
pan.save(os.path.join(OUT, 'kontrol_ornek.jpg'), quality=85)
mb = sum(os.path.getsize(os.path.join(OUT, k)) for k in idx.kesit) / 1e6
pd.DataFrame(kayma_tablo).to_csv(os.path.join(OUT, 'kayma_bloklari.csv'), index=False, encoding='utf-8')
print(idx.groupby('bolge')[['ince_dogu_m', 'ince_kuzey_m']].describe().round(2).T.to_string())
print('kesit %d (%s), eksik karolu %d, toplam %.1f MB; boyut px medyan %d, max %d' % (
    len(idx), idx.bolge.value_counts().to_dict(), (idx.eksik_karo > 0).sum(), mb,
    idx.genislik_px.median(), idx[['genislik_px', 'yukseklik_px']].max().max()))
