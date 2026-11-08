# -*- coding: utf-8 -*-
"""SAM girdilerinin (catilar.gpkg + cati_kesitleri/) kural tabanli dogruluk denetimi (2026-10-16).
Uretim / tarife / firma verisi simdilik kapsam disi (kullanici: once SAM verisi).
model_verisi.py'den SONRA calistirilir; veriyi degistirmez, yalniz raporlar:
  DOGRULAMA_RAPORU.md       her kural: GECTI / UYARI / HATA + sayi + ornek kimlikler
  incelenecek_catilar.csv   uyari alan catilar (cati_id, osm, sorun) -> gozle kontrol listesi
Durumlar: HATA = veri yanlis/tutarsiz, kullanmadan once duzeltilmeli; UYARI = supheli, gozle bakilmali; GECTI."""
import os
import numpy as np, pandas as pd, geopandas as gpd
from PIL import Image

H = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi')
P = lambda *p: os.path.join(H, *p)
sonuc, incele = [], []


def kural(veri, ad, kotu, durum_kotu='HATA', ornek=None, aciklama=''):
    """kotu: sorunlu kayit sayisi (0 -> GECTI)."""
    kotu = int(kotu)
    ornek = ', '.join(map(str, list(ornek)[:5])) if ornek is not None and kotu else ''
    sonuc.append({'veri': veri, 'kural': ad, 'durum': 'GECTI' if kotu == 0 else durum_kotu,
                  'sorunlu': kotu, 'ornek': ornek, 'aciklama': aciklama})


def isaretle(df, sorun):
    for r in df.itertuples(): incele.append({'cati_id': r.cati_id, 'osm': r.osm, 'sorun': sorun})


# ================= 1) catilar
c = gpd.read_file(P('catilar.gpkg'), layer='catilar')
s = gpd.read_file(P('catilar.gpkg'), layer='sinirlar')
csv = pd.read_csv(P('catilar.csv'))
u = c.to_crs(32635)
V = 'catilar'
kural(V, 'cati_id tekil', c.cati_id.duplicated().sum())
kural(V, 'osm kimligi tekil', c.osm.duplicated().sum(), ornek=c.osm[c.osm.duplicated()])
kural(V, 'gpkg ile csv ayni (satir, kimlik, alan)', int(len(c) != len(csv)) + int((c.osm.values != csv.osm.values).sum())
      + int((~np.isclose(c.alan_m2.values, csv.alan_m2.values)).sum()))
zor = ['osm', 'bolge', 'tur', 'alan_m2', 'ayak_izi_kaynagi', 'kesit', 'lon', 'lat']
kural(V, 'zorunlu alanlar dolu (%s)' % ', '.join(zor), c[zor].isna().any(axis=1).sum())
kural(V, 'kamu catilarinda kurum_ad dolu', (c.bolge.eq('cigli_kamu') & c.kurum_ad.isna()).sum())
alan = {'bolge': {'ataturk_osb', 'cigli_kamu'}, 'tur': {'sanayi', 'sanayi_disi', 'okul', 'hastane', 'universite'},
        'ayak_izi_kaynagi': {'OSM', 'Microsoft'}, 'gorsel_kontrol': {'goruntu_kotu', 'agac_alti', 'sekil_uyumsuz'},
        'mevcut_ges': {'tam', 'kismi'}}
for k, d in alan.items():
    x = c[k].dropna(); kural(V, '%s izinli degerlerde %s' % (k, sorted(d)), (~x.isin(d)).sum(), ornek=x[~x.isin(d)].unique())
kural(V, 'bolge-tur uyumu (OSB: sanayi/sanayi_disi, kamu: okul/hastane/universite)',
      ((c.bolge == 'ataturk_osb') & ~c.tur.isin(['sanayi', 'sanayi_disi'])).sum()
      + ((c.bolge == 'cigli_kamu') & ~c.tur.isin(['okul', 'hastane', 'universite'])).sum())
kural(V, 'OSB "sanayi disi" notu olan cati tur=sanayi_disi',
      (c['not'].fillna('').str.startswith('sanayi disi') & (c.tur != 'sanayi_disi')).sum())
kural(V, 'ms_iou 0-1 araliginda', (~c.ms_iou.dropna().between(0, 1)).sum())
kural(V, 'Microsoft kaynakli catilarda ms_iou = 1', ((c.ayak_izi_kaynagi == 'Microsoft') & (c.ms_iou.round(2) != 1)).sum())
kural(V, 'Microsoft kaynakli OSB adaylari dogrulama notu tasiyor',
      ((c.ayak_izi_kaynagi == 'Microsoft') & (c.bolge == 'ataturk_osb') & c.dogrulama.isna()).sum())
kurum_tur = c[c.bolge == 'cigli_kamu'].groupby('kurum_ad').tur.nunique()
kural(V, 'ayni kurumun catilari ayni tur', (kurum_tur > 1).sum(), ornek=kurum_tur[kurum_tur > 1].index)

# geometri
kural(V, 'geometri bos degil', (c.geometry.isna() | c.is_empty).sum())
kural(V, 'geometri gecerli (kendini kesmiyor)', (~c.is_valid).sum(), ornek=c.osm[~c.is_valid])
kural(V, 'geometri tipi Polygon', (c.geom_type != 'Polygon').sum())
kural(V, 'koordinat sistemi EPSG:4326', int(c.crs.to_epsg() != 4326))
fark = (u.area - c.alan_m2).abs() / c.alan_m2
kural(V, 'alan_m2 geometriden hesaplananla uyumlu (<%1)', (fark > 0.01).sum(), ornek=c.osm[fark > 0.01],
      aciklama='en buyuk sapma %%%.2f' % (fark.max() * 100))
kural(V, 'alan_m2 >= 30 (eleme esigi)', (c.alan_m2 < 30).sum())
sb = s.to_crs(32635).set_index('etiket').geometry
for b, e in (('ataturk_osb', 'ataturk_osb'), ('cigli_kamu', 'cigli')):
    x = u[u.bolge == b]; disari = ~x.centroid.within(sb[e])
    kural(V, '%s catilari kendi siniri icinde' % b, disari.sum(), ornek=x.osm[disari])
nokta = gpd.points_from_xy(c.lon, c.lat, crs=4326).to_crs(32635)
uzak = gpd.GeoSeries(nokta, index=c.index).distance(u.geometry.centroid) > 1
kural(V, 'lon/lat = hizali geometrinin merkezi (<1 m)', uzak.sum(), ornek=c.osm[uzak])
# cift sayim: catilar arasi ortusme
j = gpd.sjoin(u[['cati_id', 'osm', 'geometry']], u[['cati_id', 'geometry']], predicate='intersects')
j = j[j.cati_id_left < j.cati_id_right]
if len(j):
    gi = u.set_index('cati_id').geometry
    j['ortak'] = [gi[a].intersection(gi[b]).area for a, b in zip(j.cati_id_left, j.cati_id_right)]
    j['kucuk'] = [min(gi[a].area, gi[b].area) for a, b in zip(j.cati_id_left, j.cati_id_right)]
    ciddi = j[(j.ortak > 5) & (j.ortak / j.kucuk > 0.10)]
else:
    ciddi = j
kural(V, 'catilar birbiriyle ortusmuyor (cift sayim; >5 m2 ve kucugun >%10)', len(ciddi), 'HATA',
      ornek=['%d~%d (%.0f m2)' % (a, b, o) for a, b, o in zip(ciddi.cati_id_left, ciddi.cati_id_right, ciddi.ortak)],
      aciklama='toplam ortak alan %.0f m2' % (ciddi.ortak.sum() if len(ciddi) else 0))
for a, b in zip(ciddi.cati_id_left, ciddi.cati_id_right):
    isaretle(c[c.cati_id.isin([a, b])], 'ortusme: %d ile %d' % (a, b))
# sekil: kisa kenar (minimum donuk dikdortgen) -> duvar / sundurma serit
def kisa_kenar(g):
    r = g.minimum_rotated_rectangle; x, y = r.exterior.coords.xy
    k = [np.hypot(x[i + 1] - x[i], y[i + 1] - y[i]) for i in range(2)]
    return min(k)
kk = u.geometry.apply(kisa_kenar)
ince = c[kk < 4]
kural(V, 'serit/ince sekil yok (kisa kenar < 4 m)', len(ince), 'UYARI', ornek=ince.osm,
      aciklama='duvar, sundurma ya da hatali cizim olabilir')
isaretle(ince, 'ince sekil (kisa kenar <4 m)')
iou0 = c[(c.bolge == 'ataturk_osb') & (c.ayak_izi_kaynagi == 'OSM') & (c.ms_iou == 0)]
kural(V, 'OSM catisinin Microsoft karsiligi var', len(iou0), 'BILGI', ornek=iou0.osm,
      aciklama='medyan %.0f m2; hepsi 2026-10-16 gorsel kontrolunden gecti (bina var)' % iou0.alan_m2.median())

# kesitler
idx = pd.read_csv(P('cati_kesitleri', 'indeks.csv'))
kural(V, 'indeks.csv ile catilar ayni catilari iceriyor', len(set(idx.osm) ^ set(c.osm)))
yok, jgw_yok, boyut, acilmaz = [], [], [], []
ik = idx.set_index('kesit')
for k in c.kesit:
    f = P('cati_kesitleri', k)
    if not os.path.exists(f): yok.append(k); continue
    if not os.path.exists(f[:-4] + '.jgw'): jgw_yok.append(k)
    try:
        w, h = Image.open(f).size
        if (w, h) != (ik.loc[k, 'genislik_px'], ik.loc[k, 'yukseklik_px']): boyut.append(k)
    except Exception:
        acilmaz.append(k)
kural(V, 'kesit goruntusu var', len(yok), ornek=yok)
kural(V, 'kesit goruntusu aciliyor', len(acilmaz), ornek=acilmaz)
kural(V, 'kesit konum dosyasi (.jgw) var', len(jgw_yok), ornek=jgw_yok)
kural(V, 'kesit boyutu indeksle ayni', len(boyut), ornek=boyut)
ek = idx[idx.eksik_karo > 0]
kural(V, 'kesitte eksik karo yok', len(ek), 'UYARI', ornek=ek.osm, aciklama='kenarda bos bant; cati kendisi tam mi bakilmali')
isaretle(c[c.osm.isin(ek.osm)], 'kesitte eksik karo')
# hizalama: yuksek kazanc = kenarlar net oturdu (gozle teyit 2026-10-16: 38 catinin hepsi dogru yerde);
# asil risk ince ayarin HIC dogrulanamamasi (kazanc < 1,15 -> yalniz blok kaymasi)
zayif = idx[idx.hizalama_kazanci < 1.15]
kural(V, 'cati basina hizalama goruntuden dogrulandi (kazanc >= 1,15)', len(zayif), 'UYARI', ornek=zayif.osm,
      aciklama='yalniz blok kaymasi uygulandi (%.0f m2); dusuk kontrast / golge / agac' % zayif.alan_m2.sum())
isaretle(c[c.osm.isin(zayif.osm)], 'hizalama dogrulanamadi (kazanc <1,15)')
wv = idx[idx.uydu == 'WV02']
kural(V, 'goruntu yuksek cozunurluklu (LG03 0,34 m)', len(wv), 'BILGI', ornek=wv.osm.head(3),
      aciklama='%d cati (%.0f m2) WV02 0,5 m goruntude' % (len(wv), wv.alan_m2.sum()))
gk = c[c.gorsel_kontrol.notna()]
kural(V, 'gorsel kontrol bayragi yok (goruntu_kotu / agac_alti / sekil_uyumsuz)', len(gk), 'UYARI', ornek=gk.osm,
      aciklama='SAM sonucu bu catilarda guvenilmez; Claude on karari 2026-10-21 insan teyidinden gecti')
for v_, g_ in gk.groupby('gorsel_kontrol'): isaretle(g_, 'gorsel kontrol: %s' % v_)
mg = c[c.mevcut_ges.notna()]
kural(V, 'catida mevcut GES yok', len(mg), 'UYARI', ornek=mg.osm,
      aciklama='%d tam + %d kismi (%.0f m2); SAM maskesinden panel alani cikarilmali' % (
          (mg.mevcut_ges == 'tam').sum(), (mg.mevcut_ges == 'kismi').sum(), mg.alan_m2.sum()))
for v_, g_ in mg.groupby('mevcut_ges'): isaretle(g_, 'mevcut GES (%s)' % v_)
gkc = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'veri', 'elle', 'gorsel_kontrol.csv'))
kural(V, 'gorsel kontrol insan tarafindan teyit edildi', gkc.kontrol_eden.str.contains('Claude').sum(), 'UYARI',
      aciklama='%d karar Claude tarafindan verildi (veri/elle/gorsel_kontrol.csv)' % gkc.kontrol_eden.str.contains('Claude').sum())

# ================= rapor
r = pd.DataFrame(sonuc)
inc = pd.DataFrame(incele).groupby(['cati_id', 'osm'], as_index=False).sorun.agg('; '.join)
inc.to_csv(P('incelenecek_catilar.csv'), index=False, encoding='utf-8-sig')
oz = r.durum.value_counts()
md = ['# Veri Doğrulama Raporu', '',
      'Üretici: `CatiGunes/scripts/veri_dogrulama.py` (veriyi değiştirmez). Tarih: %s.' % pd.Timestamp.now().strftime('%Y-%m-%d'), '',
      '**%d kural: %d GEÇTİ · %d UYARI · %d HATA · %d BİLGİ.** HATA = kullanmadan önce düzeltilmeli; UYARI = şüpheli, gözle bakılmalı (`incelenecek_catilar.csv`, %d çatı).' % (
          len(r), oz.get('GECTI', 0), oz.get('UYARI', 0), oz.get('HATA', 0), oz.get('BILGI', 0), len(inc)), '']
for v, g in r.groupby('veri', sort=False):
    md += ['## %s' % v, '', '| durum | kural | sorunlu | açıklama / örnek |', '|---|---|---|---|']
    for x in g.itertuples():
        md.append('| %s | %s | %d | %s |' % ({'GECTI': '✅', 'UYARI': '⚠️', 'HATA': '❌', 'BILGI': 'ℹ️'}[x.durum], x.kural, x.sorunlu,
                                            ' — '.join(y for y in (x.aciklama, x.ornek) if y)))
    md.append('')
open(P('DOGRULAMA_RAPORU.md'), 'w', encoding='utf-8').write('\n'.join(md))
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 90)
print(r[r.durum != 'GECTI'].to_string()); print(oz.to_dict(), '| incelenecek cati:', len(inc))
