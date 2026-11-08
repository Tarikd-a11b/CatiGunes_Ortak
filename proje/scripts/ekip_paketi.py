# -*- coding: utf-8 -*-
"""Ekibe gonderilecek veri paketini kurar: paket/CatiGunes_Veri_<tarih>/ + .zip
  01_harita/catigunes_veri.gpkg   QGIS'te tek dosya, tum vektor katmanlar (EPSG:4326)
  01_harita/onizleme_haritasi.html tarayicida acilir, kurulum gerekmez
  02_tablolar/                    Excel'ler (ham_ozellikler, bina_verileri)
  03_ham/                         veri/ham (karo onbellegi ve 208 kayitlik ham kamu listesi haric)
  04_kamu_secimi/                 kapsamdaki devlet okul + hastaneleri, MEB kontrol listesi
  05_cati_kesitleri/              her analiz catisi icin konumlu, hizalanmis goruntu kesiti + indeks.csv (SAM girdisi)
2026-10-15 kapsam: golge ve toplumsal ihtiyac katmani projeden cikti -> GloBFP + sosyal + mahalle pakette yok.
  MANIFEST.csv                    eksiksiz geldigini dogrulamak icin (dosya, boyut, sha256)"""
import datetime, hashlib, json, os, shutil, sys, zipfile
import geopandas as gpd, pandas as pd

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(KOK, 'veri')
TARIH = datetime.date.today().isoformat()
AD = 'CatiGunes_Veri_%s%s' % (TARIH, ('_' + sys.argv[1]) if len(sys.argv) > 1 else '')   # ek: ayni gun ikinci surum
P = os.path.join(KOK, 'paket', AD)
if os.path.exists(P): shutil.rmtree(P)
for d in ('01_harita', '02_tablolar', '03_ham', '04_kamu_secimi'): os.makedirs(os.path.join(P, d))

# ---- 1) GeoPackage
gp = os.path.join(P, '01_harita', 'catigunes_veri.gpkg')
def gj(*p): return gpd.read_file(os.path.join(V, 'ham', *p))
katman = {
    'sinirlar': gj('sinir', 'sinirlar.geojson'),
    'osb_binalari_osm': gj('osm', 'binalar_ataturk_osb.geojson'),
    'cigli_binalari_osm': gj('osm', 'binalar_cigli.geojson'),
    'osb_catilari': gpd.read_file(os.path.join(V, 'islenmis', 'osb_catilari.geojson')),
    'kamu_catilari': gpd.read_file(os.path.join(V, 'islenmis', 'kamu_catilari.geojson')),
    'kamu_okul_hastane': gpd.read_file(os.path.join(V, 'islenmis', 'kamu_okul_hastane_cigli.geojson')),
    'kamu_kontrol_meb': gpd.read_file(os.path.join(V, 'islenmis', 'kamu_belirsiz_kontrol.geojson')),
    'osb_binalari_ms': gj('ms', 'ms_binalar_ataturk_osb.geojson'),
    'cigli_binalari_ms': gj('ms', 'ms_binalar_cigli.geojson'),
}
for ad, g in katman.items():
    if 'etiketler' in g.columns: g = g.drop(columns='etiketler')   # ic ice dict; ham etiketler 04_kamu_secimi'nde
    g = g.set_crs(4326, allow_override=True)
    # GPKG sutun adlari: ':' sorun cikarmasin diye '_' yap; tekrar edenleri ele
    g.columns = [c.replace(':', '_') if c != 'geometry' else c for c in g.columns]
    g.columns = ['kaynak_fid' if c.lower() == 'fid' else c for c in g.columns]   # GPKG 'fid'i kendisi kullaniyor
    g = g.loc[:, ~pd.Index([c.lower() for c in g.columns]).duplicated()]       # GPKG sutun adi buyuk/kucuk harf duyarsiz
    g.to_file(gp, layer=ad, driver='GPKG')
    print('gpkg %-24s %6d' % (ad, len(g)))
# firma tablosu da gpkg'ye (geometrisiz)
pd.read_csv(os.path.join(V, 'ham', 'iaosb', 'iaosb_firmalar.csv'), sep=';', dtype=str) \
    .pipe(lambda d: gpd.GeoDataFrame(d)).to_file(gp, layer='iaosb_firmalar', driver='GPKG')

# ---- 2) onizleme haritasi (Leaflet, veri gomulu)
def hafif(g, sut):
    g = g[[c for c in sut if c in g.columns] + ['geometry']].copy()
    g['geometry'] = g.geometry.simplify(0.000005)
    return json.loads(g.to_json(drop_id=True))
veri = {
    'sinir': hafif(katman['sinirlar'], ['etiket', 'ad', 'alan_km2']),
    'osb': hafif(katman['osb_binalari_osm'], ['osm', 'alan_m2', 'building', 'name']),
    'kamu': hafif(katman['kamu_okul_hastane'], ['osm', 'ad', 'tur', 'gerekce']),
}
html = open(os.path.join(KOK, 'scripts', 'sablon_onizleme.html'), encoding='utf-8').read()
html = html.replace('/*VERI*/null', json.dumps(veri, ensure_ascii=False)).replace('{{TARIH}}', TARIH)
open(os.path.join(P, '01_harita', 'onizleme_haritasi.html'), 'w', encoding='utf-8').write(html)

# ---- 3) tablolar, ham, kod
for f in os.listdir(os.path.join(V, 'inceleme')):
    src = os.path.join(V, 'inceleme', f)
    if f.startswith('~$'): continue                                   # acik Excel kilit dosyasi
    (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, os.path.join(P, '02_tablolar', f))
shutil.copy2(os.path.join(V, 'elle', 'gorsel_kontrol.csv'), os.path.join(P, '02_tablolar', 'gorsel_kontrol.csv'))
# SAM'e hazir cati kesitleri (scripts/cati_kesit.py)
shutil.copytree(os.path.join(V, 'islenmis', 'cati_kesitleri'), os.path.join(P, '05_cati_kesitleri'))
# ham karolardan yalniz cati iceren / cati kenarindakiler (scripts/goruntu_kalite.py 'GEREKSIZ' olanlar pakete girmez)
_gk = pd.read_excel(os.path.join(V, 'inceleme', 'goruntu_kalite.xlsx'), sheet_name='Karolar')
GEREKSIZ_KARO = set(_gk.loc[_gk.durum.str.startswith('GEREKSIZ'), 'karo'])
atla = {os.path.join('osm', 'karo'), 'kamu'}   # kamu: 208 kayitlik ham liste ozel kurumlari da iceriyor
for kok, dirs, files in os.walk(os.path.join(V, 'ham')):
    rel = os.path.relpath(kok, os.path.join(V, 'ham'))
    if any(rel == a or rel.startswith(a + os.sep) for a in atla): continue
    if rel == os.path.join('iaosb', 'firma'): continue           # 775 ham html sayfasi, csv'de ozeti var
    os.makedirs(os.path.join(P, '03_ham', rel), exist_ok=True)
    for f in files:
        if rel.startswith('goruntu') and f in GEREKSIZ_KARO: continue
        shutil.copy2(os.path.join(kok, f), os.path.join(P, '03_ham', rel, f))
for f in os.listdir(os.path.join(V, 'islenmis')):
    if f.startswith('kamu_') and 'catilari' not in f: shutil.copy2(os.path.join(V, 'islenmis', f), os.path.join(P, '04_kamu_secimi', f))
shutil.copy2(os.path.join(V, 'envanter.json'), os.path.join(P, '03_ham', 'envanter.json'))
shutil.copy2(os.path.join(KOK, 'scripts', 'BENIOKU_paket.md'), os.path.join(P, '00_BENIOKU.md'))

# ---- 4) manifest
satir = []
for kok, _, files in os.walk(P):
    for f in files:
        p = os.path.join(kok, f); h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        satir.append({'dosya': os.path.relpath(p, P).replace(os.sep, '/'), 'bayt': os.path.getsize(p), 'sha256': h})
pd.DataFrame(sorted(satir, key=lambda r: r['dosya'])).to_csv(os.path.join(P, 'MANIFEST.csv'), index=False)

# ---- 5) zip
zp = P + '.zip'
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for kok, _, files in os.walk(P):
        for f in files:
            p = os.path.join(kok, f); z.write(p, os.path.join(AD, os.path.relpath(p, P)))
print('dosya %d, toplam %.0f MB, zip %.0f MB -> %s' % (
    len(satir) + 1, sum(r['bayt'] for r in satir) / 1e6, os.path.getsize(zp) / 1e6, zp))
