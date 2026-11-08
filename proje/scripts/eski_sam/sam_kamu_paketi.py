# -*- coding: utf-8 -*-
"""SAM kamu paketi (2026-10-18): Colab'da YALNIZ kamu catilari (okul, hastane, IKCU) icin SAM kosusu.
Kaynak: Desktop/CatiGunes_Model_Verisi (catilar.csv: yalniz >= 200 m2 + cati_kesitleri/indeks.csv)
        Desktop/CatiGunes_SAM_Veriseti/tum.csv (varsa eski bolum: train/val/test_referans korunur)
Cikti : Desktop/CatiGunes_SAM_Kamu/ (+ ayni adli .zip) — CatiGunes_SAM_Veriseti ile AYNI bicim, ayni Colab defteri calisir:
  goruntuler/cNNNN.jpg, maskeler/cNNNN.png (ayak izi, 255 = cati), kamu.csv
IKCU catilari onceki SAM setinde yoktu -> bolum = 'ikcu_yeni'.
  python scripts/sam_kamu_paketi.py"""
import ast, os, shutil
from pathlib import Path
import pandas as pd, geopandas as gpd
from PIL import Image, ImageDraw
from shapely.geometry import Point

MASA = Path.home() / 'Desktop'
KAYNAK = MASA / 'CatiGunes_Model_Verisi'
HEDEF = MASA / 'CatiGunes_SAM_Kamu'
MIN_KISA_KENAR = 8

cati = pd.read_csv(KAYNAK / 'catilar.csv')
cati = cati[cati.bolge == 'cigli_kamu']
ind = pd.read_csv(KAYNAK / 'cati_kesitleri' / 'indeks.csv')
d = cati.merge(ind[['kesit', 'kutu_px', 'poligon_px', 'yer_m_px', 'uydu', 'gercek_cozunurluk_m', 'cekim_tarihi',
                    'hizalama_kazanci']], on='kesit', how='left', validate='1:1')
assert d.kutu_px.notna().all()

g = gpd.read_file(KAYNAK / 'catilar.gpkg', layer='catilar').to_crs(32635).set_index('cati_id')


def kisa_kenar(p):
    c = list(p.minimum_rotated_rectangle.exterior.coords)
    return min(Point(c[0]).distance(Point(c[1])), Point(c[1]).distance(Point(c[2])))


d['kisa_kenar_m'] = [round(kisa_kenar(g.geometry[i]), 1) for i in d.cati_id]
d['ad'] = d.cati_id.map(lambda i: f'c{int(i):04d}')
d['goruntu'] = 'goruntuler/' + d.ad + '.jpg'
d['maske'] = 'maskeler/' + d.ad + '.png'
d['alan_sinifi'] = pd.cut(d.alan_m2, [0, 200, 1000, 5000, float('inf')], labels=['<200', '200-1000', '1000-5000', '>5000']).astype(str)
d['hizalama'] = (d.hizalama_kazanci >= 1.15).map({True: 'cati_bazli', False: 'yalniz_blok'})
eski = MASA / 'CatiGunes_SAM_Veriseti' / 'tum.csv'
bolum = pd.read_csv(eski, encoding='utf-8-sig').set_index('cati_id').bolum if eski.exists() else pd.Series(dtype=str)
d['bolum'] = d.cati_id.map(bolum).fillna('ikcu_yeni')
d['deneme'] = False
neden = []
for r in d.itertuples():
    n = []
    if isinstance(r.gorsel_kontrol, str): n.append('gorsel_sorun')
    if r.kisa_kenar_m < MIN_KISA_KENAR: n.append('dar_cati_<%dm' % MIN_KISA_KENAR)
    if r.tur == 'universite': n.append('gorsel_kontrol_yapilmadi')   # IKCU 2026-10-17 eklendi, gozle bakilmadi
    neden.append(';'.join(n) or None)
d['dikkat'] = neden

# Gezgin'de aciksa klasor silinemez -> klasorleri birak, dosyalari sil
for kok, _, dosyalar in os.walk(HEDEF):
    for f in dosyalar: os.remove(os.path.join(kok, f))
(HEDEF / 'goruntuler').mkdir(parents=True, exist_ok=True); (HEDEF / 'maskeler').mkdir(exist_ok=True)
for r in d.itertuples():
    src = KAYNAK / 'cati_kesitleri' / r.kesit
    shutil.copy2(src, HEDEF / r.goruntu)
    with Image.open(src) as im: boyut = im.size
    m = Image.new('L', boyut, 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in ast.literal_eval(r.poligon_px)], fill=255)
    m.save(HEDEF / r.maske)

sut = ['cati_id', 'goruntu', 'maske', 'bolum', 'deneme', 'bolge', 'tur', 'kurum_ad', 'alan_m2', 'alan_sinifi', 'kutu_px', 'poligon_px',
       'yer_m_px', 'uydu', 'gercek_cozunurluk_m', 'cekim_tarihi', 'hizalama', 'mevcut_ges', 'gorsel_kontrol',
       'kisa_kenar_m', 'dikkat', 'kesit', 'osm', 'lon', 'lat']
d[sut].sort_values('cati_id').to_csv(HEDEF / 'kamu.csv', index=False, encoding='utf-8-sig')
(HEDEF / 'BENIOKU.md').write_text(f"""# SAM — Kamu çatıları (Çiğli)

{len(d)} kamu çatısı (taban alanı ≥ 200 m²): {d.tur.value_counts().to_dict()}. Biçim `CatiGunes_SAM_Veriseti` ile aynı;
aynı Colab defteri çalışır, yalnız 4. hücrede `CSV = "kamu.csv"` yazın.

- `bolum`: okul/hastane eski SAM setindeki bölümünü korur (train/val/test_referans/supheli); İKÇÜ = `ikcu_yeni` (önceki sette yoktu).
- `dikkat`: `gorsel_sorun` (görüntü kötü/ağaç altı/şekil uyumsuz), `dar_cati_<8m`, `gorsel_kontrol_yapilmadi` (İKÇÜ'nün tamamı —
  sonuçları gözle kontrol edin; en büyük poligon 42.733 m² muhtemelen birleşik bloklar, 4 "depo" mülkiyeti teyit edilmedi).
- `maskeler/` = ayak izi (zayıf etiket), panele uygun alan DEĞİL. Üretici `CatiGunes/scripts/sam_kamu_paketi.py`.
""", encoding='utf-8')
z = shutil.make_archive(str(HEDEF), 'zip', HEDEF)
print(len(d), d.tur.value_counts().to_dict(), d.bolum.value_counts().to_dict())
print(d.dikkat.value_counts().to_dict())
print('zip:', z, round(os.path.getsize(z) / 1e6, 1), 'MB')
