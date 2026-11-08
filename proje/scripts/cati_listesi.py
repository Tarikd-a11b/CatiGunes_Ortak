# -*- coding: utf-8 -*-
"""Analize girecek CATI listesini kurar (2026-10-15).
Sorun: kamu_okul_hastane_cigli.geojson'daki 64 kayit 64 cati DEGIL -> kampus/bahce sinirlari (amenity=school, building yok),
gercek bina poligonlari ve ayak izi olmayan noktalar karisik; bazi okullar hem kampus hem bina olarak iki kez var.
OSB listesinde de cati olmayan yapilar var (depolama tanki, sayvan, sera).

Cikti : veri/islenmis/kamu_catilari.geojson  -> her satir bir OSM bina ayak izi, hangi kuruma ait oldugu ile
        veri/islenmis/osb_catilari.geojson   -> OSB'de cati olarak analize girecek binalar (+ sektor_notu)
        veri/inceleme/cati_listesi.xlsx      -> iki liste + elenenler (neden) + kurum ozeti
Kurallar:
  kamu: kampus poligonu -> temsili noktasi kampusun icinde kalan Cigli OSM binalari; bina kaydi -> ayni OSM binasi;
        nokta -> noktayi iceren OSM binasi, yoksa noktayi iceren kampus; hicbiri yoksa 'ayak izi yok' (elle cizilecek).
        Ayni bina birden cok kayitla gelirse bir kez sayilir (adli kayit / kucuk kampus oncelikli).
  ortak eleme: man_made=storage_tank/silo/tower, building=roof (yalniz sayvan), greenhouse, kiosk/hut/shed/container,
        alan < 15 m^2 (kulube/trafo) -> elenir, nedeni yazilir. Hicbir sey silinmez; elenenler Excel'de."""
import json, math, os
import geopandas as gpd, numpy as np, pandas as pd
from shapely.geometry import shape

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = lambda *p: os.path.join(KOK, 'veri', *p)
MIN_ALAN = 30   # bekci kulubesi/trafo/WC; 30 m2 alti pratikte birkac panel
MIN_GEN = 4     # kisa kenar < 4 m: binalar arasi serit / sundurma / duvar; panel sirasi sigmaz (gozle teyit 2026-10-16)
SUT = ['osm', 'alan_m2', 'building', 'amenity', 'man_made', 'name', 'operator', 'operator:type', 'source', 'geometry']


def eleme(r):
    mm, b = r.get('man_made'), r.get('building')
    if mm in ('storage_tank', 'silo', 'tower', 'chimney', 'water_tower'): return 'cati degil: man_made=%s' % mm
    if b == 'roof': return 'cati degil: building=roof (yalniz sayvan)'
    if b == 'greenhouse': return 'cati degil: sera'
    if b in ('kiosk', 'hut', 'shed', 'container', 'cabin', 'ruins', 'construction', 'bridge', 'tent'):   # bridge/tent: 2026-10-17 IKCU kampusu
        return 'cati degil: building=%s' % b
    if r['alan_m2'] < MIN_ALAN: return 'cok kucuk (< %d m2)' % MIN_ALAN
    if r.get('kisa_m', 99) < MIN_GEN: return 'serit (kisa kenar < %d m)' % MIN_GEN
    return None


def ince(g):
    g = g[[c for c in SUT if c in g.columns]].copy()
    for c in SUT:
        if c not in g.columns: g[c] = None
    return g[SUT]


# ---------- OSB
osb = ince(gpd.read_file(V('ham', 'osm', 'binalar_ataturk_osb.geojson')))
def kisa_m(g):
    def k(p):
        c = list(p.minimum_rotated_rectangle.exterior.coords)
        return min(math.dist(c[0], c[1]), math.dist(c[1], c[2]))
    return g.to_crs(32635).geometry.apply(k).values


osb['kisa_m'] = kisa_m(osb)
osb['eleme_nedeni'] = osb.apply(eleme, axis=1)
SANAYI = ('industrial', 'manufacture', 'warehouse', 'yes')
osb['sektor_notu'] = osb.apply(lambda r: None if r['building'] in SANAYI and pd.isna(r['amenity']) else
                               'sanayi disi: %s' % ', '.join(str(x) for x in (r['building'], r['amenity'], r['name'])
                                                             if pd.notna(x)), axis=1)

# ---------- kamu
kamu = gpd.read_file(V('islenmis', 'kamu_okul_hastane_cigli.geojson'))
def etiket(r):
    e = r['etiketler']
    return json.loads(e) if isinstance(e, str) else (e or {})


kamu['kayit_turu'] = kamu.apply(lambda r: 'nokta' if r.geometry.geom_type == 'Point' else
                                'bina' if etiket(r).get('building') else 'kampus', axis=1)
cig = ince(gpd.read_file(V('ham', 'osm', 'binalar_cigli.geojson')))
temsil = cig.copy(); temsil['geometry'] = cig.geometry.representative_point()

ms = gpd.read_file(V('ham', 'ms', 'ms_binalar_cigli.geojson'))
ms['osm'] = ['ms/%d' % i for i in ms.index]          # OSM'de bina yoksa Microsoft ayak izi (kimlik: ms/<sira>)
for c in SUT:
    if c not in ms.columns: ms[c] = None
ms_temsil = ms.copy(); ms_temsil['geometry'] = ms.geometry.representative_point()


def kurum_adi(k):
    # adsiz kampus: icindeki adli kayitlardan ad al (ornek: iki okulun ortak bahcesi)
    if pd.notna(k.ad): return k.ad, False
    ic = kamu[(kamu.osm != k.osm) & kamu.ad.notna() & kamu.geometry.representative_point().within(k.geometry)]
    return (('ortak kampus: ' + ' + '.join(sorted(set(ic.ad)))), True) if len(ic) else (None, False)


aday = []   # (bina osm, kurum osm, kurum ad, tur, eslesme, kampus alani, ortak kampus mu)
kampus = kamu[kamu.kayit_turu == 'kampus']
# 2026-10-17 universite kampusu: en buyuk fakulte binalari OSM'de cizilmemis (kampuste MS 128 bin m2, OSM 61 bin m2) ->
# OSB'deki kuralla ayni: OSM binasina degmeyen, >= 100 m2 ve kisa kenari >= 8 m Microsoft binasi da aday.
# Yalniz universite: okul/hastane listesi (gozle kontrol edilmis 61 cati) degismesin.
_cig_m = cig.to_crs(32635).union_all()
_ms_m = ms.to_crs(32635)
def _kisa(g):
    c = list(g.minimum_rotated_rectangle.exterior.coords)
    return min(math.dist(c[0], c[1]), math.dist(c[1], c[2]))
# 'degmeyen' degil 'alaninin <= %20'si OSM ile ortusen': dev binanin kenarina degen kucuk OSM yapisi onu dislamasin
_ort = _ms_m.geometry.intersection(_cig_m).area / _ms_m.area
# ayrica degdigi hicbir OSM binasinin > %10'unu ortmesin (yoksa ayni cati iki kez sayilir; veri_dogrulama cift sayim kurali)
_cm = cig[['osm', 'geometry']].to_crs(32635).rename(columns={'osm': 'osm_bina'})
_j = gpd.sjoin(_ms_m[['osm', 'geometry']], _cm, predicate='intersects')
_j['pay'] = [g.intersection(_cm.geometry.loc[i]).area / _cm.geometry.loc[i].area for g, i in zip(_j.geometry, _j.index_right)]
ms_ek_uygun = set(ms.osm[(_ort <= 0.20) & (_ms_m.area >= 100) & (_ms_m.geometry.apply(_kisa) >= 8)])
# eklenen MS binasinin > %10'unu orttugu kucuk OSM yapilari (dev binanin ust/yan parcasi) ayri cati sayilmaz -> cift sayim olmasin
ms_ortulen_osm = set(_j.osm_bina[(_j.pay > 0.10) & _j.osm.isin(ms_ek_uygun)])
for _, k in kamu.iterrows():
    if k.kayit_turu == 'kampus':
        ad, ortak = kurum_adi(k)
        ic = temsil[temsil.within(k.geometry)]
        if len(ic):
            aday += [(o, k.osm, ad, k.tur, 'kampus icinde', k.geometry.area, ortak) for o in ic.osm
                     if not (k.tur == 'universite' and o in ms_ortulen_osm)]
            if k.tur == 'universite':
                mi = ms_temsil[ms_temsil.within(k.geometry) & ms_temsil.osm.isin(ms_ek_uygun)]
                aday += [(o, k.osm, ad, k.tur, "kampus icinde (OSM'de yok -> Microsoft)", k.geometry.area, ortak) for o in mi.osm]
        else:
            aday += [(o, k.osm, ad, k.tur, 'kampus icinde (OSM binasi yok -> Microsoft)', k.geometry.area, ortak)
                     for o in ms_temsil[ms_temsil.within(k.geometry)].osm]
    elif k.kayit_turu == 'bina':
        aday.append((k.osm, k.osm, k.ad, k.tur, 'bina kaydi', float('inf'), False))
    else:
        icer = cig[cig.contains(k.geometry)]
        if len(icer):
            aday.append((icer.osm.iloc[0], k.osm, k.ad, k.tur, 'nokta bina icinde', float('inf'), False))
        else:
            kk = kampus[kampus.contains(k.geometry)]
            aday.append((None, k.osm, k.ad, k.tur,
                         'nokta kampus icinde: %s' % kk.osm.iloc[0] if len(kk) else 'AYAK IZI YOK (elle cizilecek)', 0, False))

a = pd.DataFrame(aday, columns=['osm', 'kurum_osm', 'kurum_ad', 'tur', 'eslesme', '_kampus_alan', '_ortak'])
# bir bina birden cok kayittan gelirse: adli kurum, ortak olmayan kampus, en kucuk kampus (en yakin sahip), kampus yoksa bina/nokta kaydi
a['_adsiz'] = a.kurum_ad.isna()
a['_kayit_sayisi'] = a.groupby('osm').osm.transform('size')
bag = a[a.osm.notna()].sort_values(['osm', '_adsiz', '_ortak', '_kampus_alan']).drop_duplicates('osm')
bag['ayni_bina_kac_kayitta'] = bag['_kayit_sayisi']
kc = pd.concat([cig, ms[SUT]]).merge(bag.drop(columns=[c for c in bag.columns if c.startswith('_')]), on='osm', how='inner')
kc = gpd.GeoDataFrame(kc, geometry='geometry', crs=4326)
# adsiz kurum: adi bilinen ayni binadaki kayittan doldurulamadiysa 'adsiz <tur>' kalir
kc['kurum_ad'] = kc.kurum_ad.fillna('(adsiz ' + kc.tur + ' kaydi)')
kc['ayak_izi_kaynagi'] = kc.osm.str.startswith('ms/').map({True: 'Microsoft', False: 'OSM'})
kc['kisa_m'] = kisa_m(kc)
kc['eleme_nedeni'] = kc.apply(eleme, axis=1)
# elle gorsel kontrol (veri/elle/gorsel_kontrol.csv; OSB + kamu, 2026-10-16'da 1.496 cati gozden gecirildi):
#   bina_yok / cati_degil -> elenir; mevcut_ges -> 'mevcut_ges' sutunu (tam / kismi; SAM'de panel alani cikarilmali);
#   goruntu_kotu / agac_alti / sekil_uyumsuz -> 'gorsel_kontrol' sutununda isaretlenir
GK = pd.read_csv(V('elle', 'gorsel_kontrol.csv'), dtype=str).set_index('osm')


def gk_uygula(df):
    k = df.osm.map(GK.karar)
    df['mevcut_ges'] = np.where(k.eq('mevcut_ges'), df.osm.map(GK['not']).str.split(':').str[0], None)
    df['mevcut_ges'] = df.mevcut_ges.where(df.mevcut_ges.notna(), df.osm.map(GK['not']).str.extract(r'mevcut GES \((\w+)\)')[0])
    df['gorsel_kontrol'] = k.where(~k.isin(['mevcut_ges']), None)
    e = df.eleme_nedeni.isna()
    df.loc[k.eq('bina_yok') & e, 'eleme_nedeni'] = 'gorsel kontrol: bina yok (' + df.osm.map(GK['not']).fillna('') + ')'
    df.loc[k.eq('cati_degil') & e, 'eleme_nedeni'] = 'gorsel kontrol: cati degil (' + df.osm.map(GK['not']).fillna('') + ')'


gk_uygula(kc)
kc['islev_notu'] = kc.apply(lambda r: 'bina islevi: %s' % r['building'] if r['building'] not in ('yes', 'school', 'hospital') else None, axis=1)
bos_kampus = [k for _, k in kampus.iterrows() if k.osm not in set(a[a.osm.notna()].kurum_osm)]   # MS'te de yok
bina_yok = [k for _, k in kamu[kamu.kayit_turu == 'bina'].iterrows() if k.osm not in set(cig.osm)]
eksik = pd.concat([a[a.osm.isna()][['kurum_osm', 'kurum_ad', 'tur', 'eslesme']],
                   pd.DataFrame([{'kurum_osm': k.osm, 'kurum_ad': k.ad, 'tur': k.tur,
                                  'eslesme': 'kampus icinde OSM ve MS binasi yok (elle cizilecek)'} for k in bos_kampus]),
                   pd.DataFrame([{'kurum_osm': k.osm, 'kurum_ad': k.ad, 'tur': k.tur,
                                  'eslesme': 'bina kaydi Cigli bina katmaninda yok'} for k in bina_yok])])


# ---------- dogruluk: her OSM catisini Microsoft ayak izleriyle karsilastir (bagimsiz ikinci kaynak)
def ms_karsilastir(cat, msg):
    a = cat[['osm', 'geometry']].to_crs(32635); b = msg[['geometry']].to_crs(32635).reset_index(drop=True)
    j = gpd.sjoin(a, b, predicate='intersects', how='left')
    def iou(r):
        if pd.isna(r['index_right']): return 0.0
        g1, g2 = r.geometry, b.geometry.iloc[int(r['index_right'])]
        return g1.intersection(g2).area / g1.union(g2).area
    j['iou'] = j.apply(iou, axis=1)
    en = j.groupby('osm').iou.max().round(2)
    durum = pd.cut(en, [-0.01, 0.0001, 0.5, 1.01], labels=["MS'te yok", 'kismi (bitisik/bolunmus)', 'uyumlu'])
    return en, durum.astype(str)


ms_osb = gpd.read_file(V('ham', 'ms', 'ms_binalar_ataturk_osb.geojson'))
for df, msg in ((osb, ms_osb), (kc, ms)):
    o = df.ayak_izi_kaynagi.eq('OSM') if 'ayak_izi_kaynagi' in df else pd.Series(True, df.index)
    en, du = ms_karsilastir(df[o], msg)
    df['ms_iou'] = df.osm.map(en); df['ms_durum'] = df.osm.map(du)
osb['ayak_izi_kaynagi'] = 'OSM'; osb['dogrulama'] = None

# OSB sinirinda MS'te olup OSM'de HIC olmayan binalar: buyuk ve genis olanlar gercek cati (gorselle 3/3 buyuk ornek dogrulandi);
# ince seritler duvar/sundurma -> aday degil. Kural: alan >= 100 m2 ve en kisa kenar (dondurulmus dikdortgen) >= 8 m
MS_ADAY_ALAN, MS_ADAY_GEN = 100, 8
osb_sinir = gpd.GeoSeries([shape(f['geometry']) for f in json.load(open(V('ham', 'sinir', 'sinirlar.geojson'), encoding='utf-8'))['features']
                           if f['properties']['etiket'] == 'ataturk_osb'], crs=4326).to_crs(32635).iloc[0]
m = ms_osb.to_crs(32635); m = m[m.representative_point().within(osb_sinir)]
m = m[~m.intersects(osb.to_crs(32635).union_all())].copy()


def kisa_kenar(g):
    c = list(g.minimum_rotated_rectangle.exterior.coords)
    return min(math.dist(c[0], c[1]), math.dist(c[1], c[2]))


m['genislik_m'] = m.geometry.apply(kisa_kenar)
ek = m[(m.area >= MS_ADAY_ALAN) & (m.genislik_m >= MS_ADAY_GEN)].to_crs(4326)
ek = gpd.GeoDataFrame({'osm': ['ms_osb/%d' % i for i in ek.index], 'alan_m2': ek.alan_m2.round(1).values,
                       'ayak_izi_kaynagi': 'Microsoft', 'dogrulama': "OSM'de yok; Microsoft'tan eklendi (goruntuden kontrol 2026-10-16)",
                       'sektor_notu': None, 'ms_iou': 1.0, 'ms_durum': 'yalniz MS'}, geometry=ek.geometry.values, crs=4326)
osb = pd.concat([osb, ek], ignore_index=True)
osb['eleme_nedeni'] = osb.eleme_nedeni.where(osb.ayak_izi_kaynagi == 'OSM', None)
print('MS ek aday cati: %d (%.0f m2); elenen ince/kucuk MS-yalniz: %d' % (len(ek), ek.alan_m2.sum(), len(m) - len(ek)))


def ic_ice(df):
    """OSM'de buyuk binanin icine ayrica cizilmis dukkan/bolme: alaninin >%50'si daha buyuk bir catinin icinde -> cift sayim, elenir."""
    a = df[df.eleme_nedeni.isna()].to_crs(32635)
    j = gpd.sjoin(a[['osm', 'geometry']], a[['osm', 'geometry']], predicate='intersects')
    j = j[j.osm_left != j.osm_right]
    for i, r in j.iterrows():
        dis = a.loc[r.index_right]
        if dis.geometry.area > a.geometry[i].area and a.geometry[i].intersection(dis.geometry).area > 0.5 * a.geometry[i].area:
            df.loc[i, 'eleme_nedeni'] = 'baska catinin icinde (%s) -> cift sayim' % dis.osm


ic_ice(osb); ic_ice(kc)
gk_uygula(osb)
# elle ayak izi duzeltmesi (veri/elle/ayak_izi_duzeltme.csv, scripts/ayak_izi_duzeltme.py; 2026-10-22): kayik / yanlis sekilli
# poligon goruntu uzerinde yeniden cizildi. Poligon GORUNTU (Esri) cercevesinde -> cati_kesit.py bu catilari kaydirmaz
# (hizalamayi ham_wkt = eski ayak izi|eski alan ile hesaplar, diger catilar degismesin).
# Duzeltilen catida sekil_uyumsuz isareti kalkar; alan yeni poligondan hesaplanir.
AD = V('elle', 'ayak_izi_duzeltme.csv')


def ad_uygula(df):
    df['ayak_izi_duzeltme'] = None; df['ham_wkt'] = None
    if not os.path.exists(AD): return
    d = pd.read_csv(AD, dtype=str)
    d = d[d.karar.eq('duzeltildi')].drop_duplicates('osm', keep='last').set_index('osm')
    m = df.osm.isin(d.index)
    if not m.any(): return
    yeni = gpd.GeoSeries.from_wkt(df.loc[m, 'osm'].map(d.wkt).values, index=df.index[m], crs=4326)
    df.loc[m, 'ham_wkt'] = df.geometry[m].to_wkt(rounding_precision=-1)   # cati_kesit.py hizalamayi eski ayak iziyle hesaplar
    df.loc[m, 'ham_wkt'] = df.ham_wkt[m] + '|' + df.alan_m2[m].astype(str)   # + eski alan (orneklem/kume sirasi)
    df.loc[m, 'geometry'] = yeni
    df.loc[m, 'alan_m2'] = yeni.to_crs(32635).area.round(1)
    df.loc[m, 'ayak_izi_duzeltme'] = 'elle ' + df.loc[m, 'osm'].map(d.tarih).fillna('')
    df.loc[m & df.gorsel_kontrol.eq('sekil_uyumsuz'), 'gorsel_kontrol'] = None


ad_uygula(osb); ad_uygula(kc)
print('elle ayak izi duzeltmesi: OSB %d, kamu %d' % (osb.ayak_izi_duzeltme.notna().sum(), kc.ayak_izi_duzeltme.notna().sum()))

# ---------- yaz
COL = ['osm', 'alan_m2', 'building', 'amenity', 'man_made', 'name', 'operator', 'operator:type', 'source']
kamu_cat = kc[kc.eleme_nedeni.isna()]
osb_cat = osb[osb.eleme_nedeni.isna()]
kamu_cat[['osm', 'kurum_ad', 'kurum_osm', 'tur', 'eslesme', 'ayak_izi_kaynagi', 'ms_iou', 'ms_durum', 'ayni_bina_kac_kayitta', 'islev_notu', 'gorsel_kontrol', 'mevcut_ges', 'ayak_izi_duzeltme', 'ham_wkt', 'alan_m2', 'building', 'name', 'source',
          'geometry']].to_file(V('islenmis', 'kamu_catilari.geojson'), driver='GeoJSON')
osb_cat[['osm', 'ayak_izi_kaynagi', 'dogrulama', 'alan_m2', 'building', 'name', 'sektor_notu', 'ms_iou', 'ms_durum', 'gorsel_kontrol', 'mevcut_ges', 'ayak_izi_duzeltme', 'ham_wkt', 'source', 'geometry']] \
    .to_file(V('islenmis', 'osb_catilari.geojson'), driver='GeoJSON')

ozet = kamu_cat.groupby(['tur', 'kurum_ad']).agg(kayitlar=('kurum_osm', lambda s: ', '.join(sorted(set(s)))),
                                                  cati_sayisi=('osm', 'size'),
                                                              toplam_taban_m2=('alan_m2', 'sum')).reset_index()
ozet['toplam_taban_m2'] = ozet.toplam_taban_m2.round(0)
# tum catilari elenen kurum (ornek: bina yikilmis) sessizce kaybolmasin
kaybolan = kc[~kc.kurum_ad.isin(kamu_cat.kurum_ad)].drop_duplicates('kurum_ad')
eksik = pd.concat([eksik, pd.DataFrame([{'kurum_osm': r.kurum_osm, 'kurum_ad': r.kurum_ad, 'tur': r.tur,
                                         'eslesme': 'tum catilari elendi: %s -> okul tasinmis/yeniden yapiliyor olabilir, MEB ile bak' % r.eleme_nedeni}
                                        for _, r in kaybolan.iterrows()])])
elenen = pd.concat([osb[osb.eleme_nedeni.notna()].assign(bolge='OSB'),
                    kc[kc.eleme_nedeni.notna()].assign(bolge='Kamu')])
with pd.ExcelWriter(V('inceleme', 'cati_listesi.xlsx'), engine='openpyxl') as w:
    pd.DataFrame({'Sayfa': ['OSB_catilari', 'Kamu_catilari', 'Kamu_kurum_ozeti', 'Elenenler', 'Ayak_izi_yok',
                            'ms_iou / ms_durum sutunlari'],
                  'Ne': ['OSB: analize girecek bina catilari. sektor_notu dolu = sanayi disi (okul, cami, banka...) -> tuketim ayri ele alinir',
                         'Kamu: her satir bir bina ayak izi; kurum_ad hangi okul/hastaneye ait. eslesme = nasil bulundu; '
                         "ayak_izi_kaynagi Microsoft = OSM'de bina yoktu",
                         'Kurum basina cati sayisi ve toplam taban alani',
                         'Cati sayilmayanlar ve nedeni (tank, sayvan, sera, < %d m2)' % MIN_ALAN,
                         'Hicbir kaynakta bina ayak izi olmayan kayitlar -> uydu goruntusunden elle cizilecek',
                         'Dogruluk kontrolu: OSM catisinin Microsoft ayak iziyle en iyi ortusmesi (IoU, 0-1). uyumlu >= 0,5; '
                         'kismi = MS bitisik binalari birlestirmis ya da bolmus olabilir; '
                         "MS'te yok = bina yeni/yikilmis ya da OSM'de hatali -> goruntuden bakilmali"]})         .to_excel(w, sheet_name='Okuyun', index=False)
    for ad, d in (('OSB_catilari', osb_cat.drop(columns=['geometry', 'eleme_nedeni'])),
                  ('Kamu_catilari', kamu_cat.drop(columns=['geometry', 'eleme_nedeni'])),
                  ('Kamu_kurum_ozeti', ozet),
                  ('Elenenler', elenen[['bolge', 'eleme_nedeni'] + COL]),
                  ('Ayak_izi_yok', eksik)):
        d = pd.DataFrame(d); d['alan_m2'] = d['alan_m2'].round(1) if 'alan_m2' in d else None
        d = d.drop(columns=[c for c in d.columns if d[c].isna().all() and c == 'alan_m2'])
        d.to_excel(w, sheet_name=ad, index=False)
    for ws in w.sheets.values():
        ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(60, max(8, *(len(str(c.value or '')) for c in col[:300])) + 2)

print('OSB : %d bina -> %d cati, %d elendi; sanayi disi not: %d' % (len(osb), len(osb_cat), len(osb) - len(osb_cat),
                                                                   osb_cat.sektor_notu.notna().sum()))
print(osb[osb.eleme_nedeni.notna()].eleme_nedeni.value_counts().to_string())
print('Kamu: %d kayit (%s) -> %d bina eslesti, %d cati, %d elendi' % (
    len(kamu), kamu.kayit_turu.value_counts().to_dict(), len(kc), len(kamu_cat), len(kc) - len(kamu_cat)))
print(kc[kc.eleme_nedeni.notna()].eleme_nedeni.value_counts().to_string())
print('kurum sayisi:', len(ozet), ozet.groupby('tur').size().to_dict(),
      ' taban m2:', ozet.groupby('tur').toplam_taban_m2.sum().to_dict())
print('ayak izi yok / nokta:', eksik.to_dict('records'))
print('birden cok kayitta gecen bina:', int((bag.ayni_bina_kac_kayitta > 1).sum()))
for ad, d in (('OSB', osb_cat), ('Kamu', kamu_cat)):
    print('MS karsilastirma %s:' % ad, d.ms_durum.value_counts(dropna=False).to_dict(), 'medyan IoU', d.ms_iou.median(),
          '| alan payi:', (d.groupby('ms_durum').alan_m2.sum() / d.alan_m2.sum() * 100).round(1).to_dict())
