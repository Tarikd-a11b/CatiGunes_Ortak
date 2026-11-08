# -*- coding: utf-8 -*-
"""BIRLESIK SAM paketi + Colab defteri (2026-10-22): OSB + kamu (okul, hastane, IKCU) tek veri seti, tek defter.
Onceki ayri paketlerin yerini aldi (2026-10-22 silindi; ureticileri scripts/eski_sam/): CatiGunes_SAM_Veriseti,
CatiGunes_SAM_Kamu, CatiGunes_SAM_Duzeltme, harita_ek*.zip. Ayak izi elle duzeltmeleri (veri/elle/ayak_izi_duzeltme.csv) Model_Verisi
uzerinden gelir: goruntu/maske/kutu yeni kesitten, haritada kayma 0 (poligon zaten goruntu cercevesinde).
Kaynak: Desktop/CatiGunes_Model_Verisi (catilar.gpkg/csv, cati_kesitleri/)  — once kur.py
        veri/elle/sam_bolum.csv (bolum kaydi: train/val/test_referans/supheli KORUNUR)
        veri/ham/sam/sam_sonuc_birlesik.csv (+ maskeler) — onceki kosular (sam_sonuc_birlestir.py)
Cikti : Desktop/CatiGunes_SAM_Birlesik/ (+ .zip) ve icinde sam_birlesik_colab.ipynb
  sam_girdi.csv        1 satir = 1 cati (SAM girdisi + egitim_uygun / dislama_nedeni)
  georef.csv           harita icin kesit world file + hizali / ham ayak izi WKT
  sinirlar.geojson     Ataturk OSB + Cigli + IKCU kampusu
  onceki/              onceki SAM sonuclari (defter varsayilan olarak bunlari alir, yalniz eksikleri kosar)
  python scripts/sam_birlesik_paketi.py"""
import ast, json, os, shutil
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from PIL import Image, ImageDraw
from shapely import affinity
from shapely.geometry import Point

KOK = Path(__file__).resolve().parent.parent
MASA = Path.home() / 'Desktop'
KAYNAK = MASA / 'CatiGunes_Model_Verisi'
HEDEF = MASA / 'CatiGunes_SAM_Birlesik'
SAMHAM = KOK / 'veri' / 'ham' / 'sam'
MIN_KISA_KENAR = 8

# ---------- 1) catilar + kesit bilgisi
g = gpd.read_file(KAYNAK / 'catilar.gpkg', layer='catilar')
ind = pd.read_csv(KAYNAK / 'cati_kesitleri' / 'indeks.csv')
d = g.merge(ind[['kesit', 'kutu_px', 'poligon_px', 'yer_m_px', 'uydu', 'gercek_cozunurluk_m', 'cekim_tarihi', 'hizalama_kazanci',
                 'blok_kayma_dogu_m', 'blok_kayma_kuzey_m', 'ince_dogu_m', 'ince_kuzey_m', 'kume_bina']],
            on='kesit', how='left', validate='1:1')
assert d.kutu_px.notna().all(), 'indekste esi olmayan cati var'
u = d.to_crs(32635)


def kisa_kenar(p):
    c = list(p.minimum_rotated_rectangle.exterior.coords)
    return min(Point(c[0]).distance(Point(c[1])), Point(c[1]).distance(Point(c[2])))


d['kisa_kenar_m'] = [round(kisa_kenar(p), 1) for p in u.geometry]
d['ad'] = d.cati_id.map(lambda i: f'c{int(i):04d}')
d['goruntu'] = 'goruntuler/' + d.ad + '.jpg'
d['maske'] = 'maskeler/' + d.ad + '.png'
d['alan_sinifi'] = pd.cut(d.alan_m2, [0, 200, 1000, 5000, np.inf], labels=['<200', '200-1000', '1000-5000', '>5000']).astype(str)
elle = d.ayak_izi_duzeltme.notna()
d['hizalama'] = np.where(elle, 'elle_duzeltildi', np.where(d.hizalama_kazanci >= 1.15, 'cati_bazli', 'yalniz_blok'))
# bolum KALICI kayittan (veri/elle/sam_bolum.csv; 2026-10-17 bolunmesi, test_referans sabit): yeni cati 'yeni' / 'ikcu_yeni' alir, kayda eklenir
BOLUM = KOK / 'veri' / 'elle' / 'sam_bolum.csv'
kayit = pd.read_csv(BOLUM)
d['bolum'] = d.cati_id.map(kayit.set_index('cati_id').bolum)
yeni = d.bolum.isna()
d.loc[yeni, 'bolum'] = np.where(d.tur[yeni] == 'universite', 'ikcu_yeni', 'yeni')
if yeni.any():
    pd.concat([kayit, pd.DataFrame(d.loc[yeni, ['cati_id', 'osm', 'bolum']])]).sort_values('cati_id').to_csv(BOLUM, index=False)
neden = []
for r in d.itertuples():
    n = []
    if r.bolum == 'supheli' or isinstance(r.gorsel_kontrol, str): n.append('gorsel_sorun')
    if r.kisa_kenar_m < MIN_KISA_KENAR: n.append('dar_cati_<%dm' % MIN_KISA_KENAR)
    if r.tur == 'universite': n.append('gorsel_kontrol_yapilmadi')   # IKCU 2026-10-17 eklendi, gozle bakilmadi
    neden.append(';'.join(n) or None)
d['dislama_nedeni'] = neden
d['egitim_uygun'] = d.dislama_nedeni.isna() & d.bolum.isin(['train', 'val', 'test_referans'])
# 2026-10-26 mevcut GES: tum catilar SAM'e girer (cati alani + web gosterimi, panel_durumu ile filtre); potansiyel icin
# ayri uygun alan: tam_dolu -> 0, kismi -> SAM maskesi ∩ elle cizilen panelsiz alan
# (panel_durumu cati_geometri.py'den; panelsiz = veri/elle/panelsiz_cizimleri.geojson)
d['panel_durumu'] = d.cati_id.map(pd.read_csv(KAYNAK / 'catilar.csv').set_index('cati_id').panel_durumu).fillna('panel_yok')
pz = gpd.read_file(KOK / 'veri' / 'elle' / 'panelsiz_cizimleri.geojson').dissolve('cati_id').geometry
d['panelsiz'] = np.where(d.panel_durumu.eq('kismi_panel_dusuldu') & d.cati_id.isin(pz.index), 'panelsiz/' + d.ad + '.png', '')
assert not (d.panel_durumu.eq('kismi_panel_dusuldu') & d.panelsiz.eq('')).any(), 'kismi panelli catinin panelsiz cizimi yok'
R = 6378137.0

# ---------- 2) dosyalar (Gezgin'de aciksa klasor silinemez -> dosyalari sil)
if HEDEF.exists():
    for kok, _, dosyalar in os.walk(HEDEF):
        for f in dosyalar: os.remove(os.path.join(kok, f))
for k in ('goruntuler', 'maskeler', 'panelsiz', 'onceki/sam_maskeler'): (HEDEF / k).mkdir(parents=True, exist_ok=True)


def lonlat_px(kesit, geom):
    """lon/lat poligon(lar) -> kesit pikseli (ayak_izi_duzeltme.px_lonlat'in tersi; kose tabanli)."""
    a, _, _, e, c, f = [float(x) for x in open(KAYNAK / 'cati_kesitleri' / (kesit[:-4] + '.jgw')).read().split()]
    out = []
    for p in getattr(geom, 'geoms', [geom]):
        out.append([((np.radians(x) * R - c) / a + .5, (R * np.log(np.tan(np.pi / 4 + np.radians(y) / 2)) - f) / e + .5)
                    for x, y in p.exterior.coords])
    return out


for r in d.itertuples():
    src = KAYNAK / 'cati_kesitleri' / r.kesit
    shutil.copy2(src, HEDEF / r.goruntu)
    with Image.open(src) as im: boyut = im.size
    m = Image.new('L', boyut, 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in ast.literal_eval(r.poligon_px)], fill=255)
    m.save(HEDEF / r.maske)
    if r.panelsiz:
        m = Image.new('L', boyut, 0)
        for p in lonlat_px(r.kesit, pz.loc[r.cati_id]): ImageDraw.Draw(m).polygon(p, fill=255)
        m.save(HEDEF / r.panelsiz)
sut = ['cati_id', 'goruntu', 'maske', 'bolum', 'egitim_uygun', 'dislama_nedeni', 'bolge', 'tur', 'kurum_ad', 'alan_m2', 'alan_sinifi',
       'kutu_px', 'poligon_px', 'yer_m_px', 'uydu', 'gercek_cozunurluk_m', 'cekim_tarihi', 'hizalama', 'mevcut_ges', 'panel_durumu',
       'panelsiz', 'gorsel_kontrol', 'ayak_izi_duzeltme', 'ayak_izi_kaynagi', 'kisa_kenar_m', 'kesit', 'osm', 'lon', 'lat']
pd.DataFrame(d[sut]).sort_values('cati_id').to_csv(HEDEF / 'sam_girdi.csv', index=False, encoding='utf-8-sig')

# ---------- 3) harita: georef + sinirlar (eski harita_ek*.zip ile ayni sutunlar)
d['kayma_dogu_m'] = np.where(elle, 0.0, (d.blok_kayma_dogu_m + d.ince_dogu_m).round(2))   # elle: zaten goruntu cercevesinde
d['kayma_kuzey_m'] = np.where(elle, 0.0, (d.blok_kayma_kuzey_m + d.ince_kuzey_m).round(2))
jgw = [[float(x) for x in open(KAYNAK / 'cati_kesitleri' / (k[:-4] + '.jgw')).read().split()] for k in d.kesit]
d['jgw_a'], d['jgw_e'], d['jgw_c'], d['jgw_f'] = zip(*[(v[0], v[3], v[4], v[5]) for v in jgw])
ham = [affinity.translate(p, -dx, -dy) for p, dx, dy in zip(u.geometry, d.kayma_dogu_m, d.kayma_kuzey_m)]
d['wkt_hizali'] = d.geometry.to_wkt()
d['wkt_ham'] = gpd.GeoSeries(ham, crs=32635).to_crs(4326).to_wkt().values
gsut = ['cati_id', 'bolge', 'tur', 'alan_m2', 'ayak_izi_kaynagi', 'ms_iou', 'gorsel_kontrol', 'kayma_dogu_m', 'kayma_kuzey_m',
        'blok_kayma_dogu_m', 'blok_kayma_kuzey_m', 'ince_dogu_m', 'ince_kuzey_m', 'hizalama_kazanci', 'kume_bina',
        'jgw_a', 'jgw_e', 'jgw_c', 'jgw_f', 'wkt_hizali', 'wkt_ham']
pd.DataFrame(d[gsut]).sort_values('cati_id').to_csv(HEDEF / 'georef.csv', index=False)
s = gpd.read_file(KOK / 'veri' / 'ham' / 'sinir' / 'sinirlar.geojson')
s = s[s.etiket.isin(['ataturk_osb', 'cigli'])]
k = gpd.read_file(KOK / 'veri' / 'ham' / 'kamu' / 'ikcu_kampus_osm.geojson')
k = k[k.osm == 'relation/6904659'][['osm', 'geometry']].assign(etiket='ikcu_kampus', ad='İzmir Kâtip Çelebi Üniversitesi Balatçık')
sinir = pd.concat([s[['etiket', 'osm', 'ad', 'geometry']], k[['etiket', 'osm', 'ad', 'geometry']]], ignore_index=True)
(HEDEF / 'sinirlar.geojson').write_text(gpd.GeoDataFrame(sinir, crs=4326).to_json(ensure_ascii=False), encoding='utf-8')

# ---------- 4) onceki sonuclar (ayni yontem: vit_h, kutu istemi, multimask, ayak izine en yakin, ayak izine kirpma)
o = pd.read_csv(SAMHAM / 'sam_sonuc_birlesik.csv')
o = o[o.cati_id.isin(d.cati_id)]
# ayak izi sonradan degisen (or. 2026-10-24 elle duzeltilen 10) catinin eski SAM sonucu alinmaz -> Colab yeniden kosar
yeni_alan = d.set_index('cati_id').apply(lambda r: (np.array(Image.open(HEDEF / r.maske)) > 0).sum() * r.yer_m_px ** 2, axis=1)
degisen = (o.ayak_izi_m2 - o.cati_id.map(yeni_alan)).abs() > .02 * o.ayak_izi_m2
print('ayak izi degistigi icin yeniden kosulacak:', sorted(o.cati_id[degisen]))
o = o[~degisen]
for r in o.itertuples(): shutil.copy2(SAMHAM / r.maske_dosyasi, HEDEF / 'onceki' / 'sam_maskeler' / f'c{r.cati_id:04d}.png')
o = o.assign(maske_dosyasi=['sam_maskeler/c%04d.png' % i for i in o.cati_id])
o[['cati_id', 'maske_dosyasi', 'sam_alan_m2', 'ayak_izi_m2', 'kaplama', 'tasma', 'iou_ayak', 'guven', 'secilen_maske', 'kosu']] \
    .to_csv(HEDEF / 'onceki' / 'sam_sonuc.csv', index=False)

# ---------- 5) defter + BENIOKU
H = []
def md(s): H.append({'cell_type': 'markdown', 'metadata': {}, 'source': s.strip('\n').splitlines(keepends=True)})
def kod(s): H.append({'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [], 'source': s.strip('\n').splitlines(keepends=True)})
N = len(d)
md(f"""
# Çatı GES — SAM segmentasyonu, BİRLEŞİK (Atatürk OSB + Çiğli kamu, {N} çatı)
Girdi: `CatiGunes_SAM_Birlesik.zip` (tek dosya: görüntüler, ayak izi maskeleri, `sam_girdi.csv`, harita bilgisi, önceki sonuçlar).
Ayak izleri 2026-10-22 elle düzeltilmiş haliyle ({int(elle.sum())} çatı, `hizalama = elle_duzeltildi`).

**Çalışma zamanı → T4 GPU.** Sıra: 1 → 2 (zip seç) → 3 → 4 → 5 → 6 (indir) → 7 (harita indir) → 8 (poligon indir). Multimask karşılaştırması: 1 → 2 → 3 → 9 → 10 → 11.
4. hücrede `YENIDEN_HEPSI = False` (varsayılan): önceki sonuçlar alınır, yalnız eksik çatılar koşulur (birkaç dk).
`True`: {N} çatının hepsi baştan (~40 dk; kesilirse 4'ü tekrar çalıştır, kaldığı yerden devam eder). **Defteri tek sekmede aç.**
""")
kod("""
# 1) GPU + SAM kurulumu ve model indirme
!nvidia-smi --query-gpu=name,memory.total --format=csv
!pip -q install git+https://github.com/facebookresearch/segment-anything.git folium rasterio
# model her zaman /content'e iner (-c: yarım kaldıysa tamamlar, tam ise atlar)
!wget -q -c -P /content https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth
!ls -la /content/*.pth
print("kurulum ve model indirme tamam")
""")
kod("""
# 2) Veriyi yükle: CatiGunes_SAM_Birlesik.zip (zaten açıldıysa atlar)
from google.colab import files
import zipfile, os
os.chdir("/content")
if not os.path.exists("/content/veri/sam_girdi.csv"):
    yuklenen = files.upload()
    for ad in yuklenen:
        zipfile.ZipFile(ad).extractall("/content/veri")
os.chdir("/content/veri")
assert os.path.exists("sam_girdi.csv"), "yanlış zip: CatiGunes_SAM_Birlesik.zip seçilmeli"
print(sorted(f for f in os.listdir(".") if not f.startswith(("goruntuler", "maskeler"))))
""")
kod("""
# 3) Modeli yükle
import torch
from segment_anything import sam_model_registry, SamPredictor
cihaz = "cuda" if torch.cuda.is_available() else "cpu"
sam = sam_model_registry["vit_h"](checkpoint="/content/sam_vit_h_4b8939.pth").to(cihaz)
predictor = SamPredictor(sam)
print("model hazır:", cihaz)
""")
kod(f"""
# 4) Kutu istemiyle segmentasyon — OSB + kamu (sam_girdi.csv)
import os, ast, time, shutil, numpy as np, pandas as pd
from PIL import Image
os.chdir("/content/veri")
YENIDEN_HEPSI = False   # True: hepsi baştan; False: onceki/ sonuçları alınır, yalnız eksikler koşulur
df = pd.read_csv("sam_girdi.csv")
assert len(df) == {N}, f"{N} çatı bekleniyordu, {{len(df)}} geldi"
CIKTI = "sam_sonuc.csv"
os.makedirs("sam_maskeler", exist_ok=True)
if YENIDEN_HEPSI and os.path.exists(CIKTI) and not os.path.exists(".yeniden_basladi"):
    os.remove(CIKTI)
if YENIDEN_HEPSI: open(".yeniden_basladi", "w").close()
if not YENIDEN_HEPSI and not os.path.exists(CIKTI):
    shutil.copy("onceki/sam_sonuc.csv", CIKTI)
    for f in os.listdir("onceki/sam_maskeler"): shutil.copy(os.path.join("onceki/sam_maskeler", f), "sam_maskeler")
    print("önceki sonuçlar alındı")
bitmis = set(pd.read_csv(CIKTI).cati_id) if os.path.exists(CIKTI) else set()
kalan = df[~df.cati_id.isin(bitmis)]
print(f"{{len(df)}} çatı, {{len(bitmis & set(df.cati_id))}} bitmiş, {{len(kalan)}} kalan")
sonuc, t0, BUGUN = [], time.time(), time.strftime("colab_%Y-%m-%d")
def yaz():
    global sonuc
    if sonuc:
        pd.DataFrame(sonuc).to_csv(CIKTI, mode="a", header=not os.path.exists(CIKTI), index=False)
        sonuc = []
for k, r in enumerate(kalan.itertuples(), 1):
    img = np.array(Image.open(r.goruntu).convert("RGB"))
    kutu = np.array(ast.literal_eval(r.kutu_px), dtype=float)
    ayak = np.array(Image.open(r.maske)) > 0
    predictor.set_image(img)
    masks, scores, _ = predictor.predict(box=kutu, multimask_output=True)
    iou = [(mm & ayak).sum() / max((mm | ayak).sum(), 1) for mm in masks]
    i = int(np.argmax(np.array(iou) + 1e-3 * scores))
    ham = masks[i]; m = ham & ayak
    px2 = r.yer_m_px ** 2
    Image.fromarray((m * 255).astype(np.uint8)).save(f"sam_maskeler/c{{r.cati_id:04d}}.png")
    sonuc.append(dict(cati_id=r.cati_id, maske_dosyasi=f"sam_maskeler/c{{r.cati_id:04d}}.png",
        sam_alan_m2=round(m.sum() * px2, 1), ayak_izi_m2=round(ayak.sum() * px2, 1),
        kaplama=round(m.sum() / max(ayak.sum(), 1), 3), tasma=round((ham & ~ayak).sum() / max(ham.sum(), 1), 3),
        iou_ayak=round(float(iou[i]), 3), guven=round(float(scores[i]), 3), secilen_maske=i, kosu=BUGUN))
    if k % 50 == 0:
        yaz(); h = (time.time() - t0) / k
        print(f"{{k}}/{{len(kalan)}}  ~{{h:.1f}} sn/çatı, kalan ~{{h*(len(kalan)-k)/60:.0f}} dk")
yaz()
if os.path.exists(".yeniden_basladi"): os.remove(".yeniden_basladi")
res = pd.read_csv(CIKTI).drop_duplicates("cati_id", keep="last")
res = res[res.cati_id.isin(df.cati_id)]
res.to_csv(CIKTI, index=False)
assert set(res.cati_id) == set(df.cati_id), "sonuç dosyasında eksik çatı var"
# mevcut GES: SAM maskesi çatının tamamı (gösterim, panel_durumu ile filtrelenir); potansiyel için uygun alan ayrı:
# tamamen panelli → 0, kısmi panelli → SAM maskesi ∩ elle çizilen panelsiz alan
os.makedirs("uygun_maskeler", exist_ok=True)
tablo = df.set_index("cati_id")
uygun = {{}}
for q in res.itertuples():
    r = tablo.loc[q.cati_id]
    m = np.array(Image.open(q.maske_dosyasi)) > 0
    if r.panel_durumu == "tam_dolu":
        m[:] = False
    elif isinstance(r.panelsiz, str) and r.panelsiz:
        m &= np.array(Image.open(r.panelsiz)) > 0
    Image.fromarray((m * 255).astype(np.uint8)).save(f"uygun_maskeler/c{{q.cati_id:04d}}.png")
    uygun[q.cati_id] = round(m.sum() * r.yer_m_px ** 2, 1)
res["uygun_dosyasi"] = ["uygun_maskeler/c%04d.png" % i for i in res.cati_id]
res["uygun_alan_m2"] = res.cati_id.map(uygun)
# şüpheli kuralı (tüm koşularda aynı): kaplama < 0,7 | taşma > 0,3 | güven < 0,85 | şüpheli bölüm | görsel sorun
s = df.drop(columns=["goruntu", "maske"]).merge(res, on="cati_id")
dk = s.dislama_nedeni.fillna("").astype(str)
s["supheli"] = ((s.kaplama < 0.7) | (s.tasma > 0.3) | (s.guven < 0.85) | (s.bolum == "supheli") | dk.str.contains("gorsel_sorun"))
s.to_csv("sam_sonuc_tam.csv", index=False)
print("bitti:", len(s), "çatı | şüpheli:", int(s.supheli.sum()), "| koşu:", s.kosu.value_counts().to_dict())
print("SAM çatı %.0f m² / ayak izi %.0f m² = %%%.1f | panel düşülmüş uygun alan %.0f m²" % (
    s.sam_alan_m2.sum(), s.ayak_izi_m2.sum(), 100*s.sam_alan_m2.sum()/s.ayak_izi_m2.sum(), s.uygun_alan_m2.sum()))
s.groupby(["bolge", "panel_durumu"]).agg(cati=("cati_id", "size"), kaplama_medyan=("kaplama", "median"),
    sam_m2=("sam_alan_m2", "sum"), uygun_m2=("uygun_alan_m2", "sum"), supheli=("supheli", "sum")).round(3)
""")
kod("""
# 5) Görsel kontrol: en düşük kaplamalı 20 çatı (kırmızı kutu, sarı ayak izi, mavi SAM)
import matplotlib.pyplot as plt
tablo = pd.read_csv("sam_girdi.csv").set_index("cati_id")
goster = s.nsmallest(20, "kaplama")
sut = 5; sat = (len(goster) + sut - 1) // sut
fig, ax = plt.subplots(sat, sut, figsize=(4 * sut, 4 * sat))
for a, q in zip(ax.flat, goster.itertuples()):
    r = tablo.loc[q.cati_id]
    img = np.array(Image.open(r.goruntu).convert("RGB"))
    m = np.array(Image.open(q.maske_dosyasi)) > 0
    a.imshow(img); a.imshow(np.ma.masked_where(~m, m), alpha=0.45, cmap="winter")
    x1, y1, x2, y2 = ast.literal_eval(r.kutu_px)
    a.add_patch(plt.Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, ec="red", lw=1.5))
    p = np.array(ast.literal_eval(r.poligon_px)); a.plot(p[:, 0], p[:, 1], c="yellow", lw=1)
    a.set_title(f"c{q.cati_id:04d} {q.bolge[:5]} {q.tur} {int(q.ayak_izi_m2)}m² kap={q.kaplama}", fontsize=8,
                color="red" if q.supheli else "black")
    a.axis("off")
for a in list(ax.flat)[len(goster):]: a.axis("off")
plt.tight_layout(); plt.savefig("sam_onizleme.jpg", dpi=110); plt.show()
""")
kod("""
# 6) Sonuçları indir: sam_sonuc_tam.csv + maskeler + önizleme
import os, zipfile
from google.colab import files
os.chdir("/content/veri")
with zipfile.ZipFile("/content/sam_sonuc_birlesik.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in ["sam_sonuc_tam.csv", "sam_onizleme.jpg"]:
        if os.path.exists(f): z.write(f)
    for k in ("sam_maskeler", "uygun_maskeler"):
        for f in sorted(os.listdir(k)):
            z.write(os.path.join(k, f))
files.download("/content/sam_sonuc_birlesik.zip")
""")
kod("""
# 7) Harita (OSB + kamu): ham → hizalı ayak izi, kayma okları, oturtma güveni, SAM maskesi
import os, numpy as np, pandas as pd, geopandas as gpd, folium
from PIL import Image
from google.colab import files
from shapely import wkt
from shapely.ops import unary_union
from shapely.geometry import shape, LineString
from rasterio.features import shapes
from affine import Affine
os.chdir("/content/veri")
g = pd.read_csv("georef.csv")
s = pd.read_csv("sam_sonuc_tam.csv")
d = s.merge(g.drop(columns=["bolge", "tur", "alan_m2", "ayak_izi_kaynagi", "gorsel_kontrol"]), on="cati_id", how="left")
assert d.jgw_a.notna().all(), "georef'te eşi olmayan çatı var"
d["kayma_m"] = np.hypot(d.kayma_dogu_m, d.kayma_kuzey_m).round(2)
d["oturtma"] = np.select([d.hizalama == "elle_duzeltildi", d.hizalama_kazanci >= 1.5, d.hizalama_kazanci >= 1.15],
                         ["elle düzeltildi", "yüksek", "orta"], "düşük (yalnız blok)")
d["supheli"] = d["supheli"].map({True: "EVET", False: "hayır"})
for c in ["dislama_nedeni", "mevcut_ges", "kurum_ad", "panel_durumu"]: d[c] = d[c].fillna("").astype(str)
geo = []
for r in d.itertuples():
    m = np.array(Image.open(r.maske_dosyasi)) > 0   # çatının tamamı; panel bilgisi panel_durumu / uygun_alan_m2
    aff = Affine(r.jgw_a, 0, r.jgw_c - r.jgw_a / 2, 0, r.jgw_e, r.jgw_f - r.jgw_e / 2)
    p = [shape(gm) for gm, v in shapes(m.astype(np.uint8), mask=m, transform=aff) if v == 1]
    geo.append(unary_union(p).simplify(0.3) if p else None)
alanlar = ["cati_id", "bolge", "tur", "kurum_ad", "alan_sinifi", "alan_m2", "sam_alan_m2", "kaplama", "iou_ayak", "guven",
           "supheli", "dislama_nedeni", "oturtma", "hizalama_kazanci", "kayma_m", "ayak_izi_kaynagi", "uydu", "mevcut_ges",
           "panel_durumu", "uygun_alan_m2"]
etiket = ["çatı", "bölge", "tür", "kurum", "alan sınıfı", "ayak izi m²", "SAM m²", "kaplama", "IoU", "SAM skoru",
          "şüpheli", "dikkat", "oturtma", "hizalama kazancı", "kayma m", "ayak izi kaynağı", "uydu", "mevcut GES",
          "panel durumu", "uygun alan m²"]
sam_g = gpd.GeoDataFrame(d[alanlar], geometry=geo, crs=3857).dropna(subset=["geometry"]).to_crs(4326)
hizali = gpd.GeoDataFrame(d[alanlar], geometry=d.wkt_hizali.map(wkt.loads), crs=4326)
ham = gpd.GeoDataFrame(d[["cati_id", "ayak_izi_kaynagi"]], geometry=d.wkt_ham.map(wkt.loads), crs=4326)
ok = gpd.GeoDataFrame(d[["cati_id", "kayma_m", "kayma_dogu_m", "kayma_kuzey_m", "oturtma"]],
                      geometry=[LineString([a.centroid, b.centroid]) for a, b in zip(ham.geometry, hizali.geometry)], crs=4326)
ok = ok[ok.kayma_m >= 0.5]
sinir = gpd.read_file("sinirlar.geojson")
x1, y1, x2, y2 = hizali.total_bounds
m = folium.Map(location=[(y1 + y2) / 2, (x1 + x2) / 2], zoom_start=13, max_zoom=21, tiles=None)
folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                 attr="Esri World Imagery", name="Uydu (Esri)", max_zoom=21, max_native_zoom=19).add_to(m)
folium.TileLayer("OpenStreetMap", name="Harita (OSM)", show=False).add_to(m)   # varsayilan altlik uydu
SR = {"ataturk_osb": ("Atatürk OSB sınırı", "#ff3b30"), "cigli": ("Çiğli ilçe sınırı", "#ff9f0a"), "ikcu_kampus": ("İKÇÜ kampüsü", "#bf5af2")}
for e, (ad, renk) in SR.items():
    folium.GeoJson(sinir[sinir.etiket == e], name=ad, style_function=lambda f, c=renk: {"color": c, "weight": 3, "fill": False}).add_to(m)
OTR = {"elle düzeltildi": "#64d2ff", "yüksek": "#34c759", "orta": "#ffd60a", "düşük (yalnız blok)": "#ff3b30"}
folium.GeoJson(ham, name="Ham ayak izi (hizalama öncesi)", show=False,
               style_function=lambda f: {"color": "#d1d1d6", "weight": 1.5, "dashArray": "4 4", "fill": False}).add_to(m)
folium.GeoJson(ok, name="Kayma okları (≥0,5 m)",
               style_function=lambda f: {"color": "#ffffff" if f["properties"]["kayma_m"] < 2 else
                                         "#ffd60a" if f["properties"]["kayma_m"] < 4 else "#ff3b30", "weight": 2.5},
               tooltip=folium.GeoJsonTooltip(fields=["cati_id", "kayma_m", "kayma_dogu_m", "kayma_kuzey_m"],
                                             aliases=["çatı", "kayma m", "doğu m", "kuzey m"])).add_to(m)
for b, ad in (("ataturk_osb", "SAM maskesi — OSB"), ("cigli_kamu", "SAM maskesi — kamu")):
    folium.GeoJson(sam_g[sam_g.bolge == b], name=ad,
                   style_function=lambda f: {"color": "#ff2d55" if f["properties"]["supheli"] == "EVET" else "#0a84ff",
                                             "fillColor": "#ff2d55" if f["properties"]["supheli"] == "EVET" else "#0a84ff",
                                             "weight": 1, "fillOpacity": 0.45},
                   tooltip=folium.GeoJsonTooltip(fields=alanlar, aliases=etiket)).add_to(m)
folium.GeoJson(hizali, name="Hizalı ayak izi (oturtma güveni rengi)",
               style_function=lambda f: {"color": OTR[f["properties"]["oturtma"]], "weight": 2, "fill": False},
               tooltip=folium.GeoJsonTooltip(fields=alanlar, aliases=etiket)).add_to(m)
folium.LayerControl(collapsed=False).add_to(m)
m.get_root().html.add_child(folium.Element(\"\"\"
<div style="position:fixed;bottom:24px;left:12px;z-index:9999;background:#fff;padding:8px 12px;border-radius:6px;
font:12px sans-serif;line-height:1.7;box-shadow:0 1px 4px rgba(0,0,0,.3)">
<b>Oturtma güveni</b> (hizalı ayak izi çizgisi)<br>
<span style="color:#34c759">■</span> yüksek: kazanç ≥ 1,5 &nbsp; <span style="color:#d4a800">■</span> orta: 1,15–1,5<br>
<span style="color:#ff3b30">■</span> düşük: yalnız blok kayması &nbsp; <span style="color:#64d2ff">■</span> elle düzeltildi<br>
<b>SAM</b> <span style="color:#0a84ff">■</span> maske &nbsp; <span style="color:#ff2d55">■</span> şüpheli maske<br>
<b>Ham ayak izi</b> gri kesik · <b>Kayma oku</b> beyaz &lt;2 m, sarı 2–4, kırmızı &gt;4</div>\"\"\"))
m.save("sam_haritasi.html")
sam_g.to_file("sam_poligonlari.geojson", driver="GeoJSON")
print(d.groupby(["bolge", "oturtma"]).agg(cati=("cati_id", "size"), kayma_ort_m=("kayma_m", "mean"),
      kaplama_ort=("kaplama", "mean"), supheli=("supheli", lambda x: (x == "EVET").sum())).round(2))
files.download("sam_haritasi.html")
m
""")
kod("""
# 8) SAM poligonlarını indir (ayrı hücre: Chrome aynı anda iki indirmeyi engelliyor)
from google.colab import files
import os; os.chdir("/content/veri")
files.download("sam_poligonlari.geojson")
""")
md("""
---
## Multimask karşılaştırması (2026-10-22)
Soru: beşik / kırma çatıda SAM tek yüzü mü seçiyor, maskeleri birleştirmek düzeltir mi? **Sıra: 1 → 2 → 3 → 9 → 10 → 11** (4–8 gerekmez; yaptıysan da sorun yok).
Her çatıda SAM'in 3 aday maskesi ayrı ölçülür ve 3 yöntem karşılaştırılır:
- **A — mevcut**: ayak izine en çok benzeyen tek maske (şimdiki yöntem)
- **U — hepsinin birleşimi**: 3 maskenin birleşimi
- **S — seçici birleşim**: yalnız ayak izinin dışına %30'dan az taşan maskelerin birleşimi (yol / komşu bina girmesin); hiçbiri uymazsa A

Kapsam (`KAPSAM`): şüpheliler + 150 rastgele temiz çatı (kontrol: birleşim iyi sonuçları bozuyor mu?) ~10 dk; `"hepsi"` 1.085 çatı ~40 dk.
Çıktı: `sam_multimask.zip` (tablo + S maskesi kırpılmış ve **kırpılmamış** hali → taşma ilk kez görünür).
""")
kod("""
# 9) Multimask koşusu (3. hücre: model yüklü olmalı)
import os, ast, time, numpy as np, pandas as pd
from PIL import Image
os.chdir("/content/veri")
KAPSAM = "supheli+kontrol"   # ya da "hepsi"
TASMA_ESIK = 0.3
df = pd.read_csv("sam_girdi.csv")
if os.path.exists("sam_sonuc_tam.csv"):
    onc = pd.read_csv("sam_sonuc_tam.csv")
else:   # 4. hücre çalışmadıysa önceki sonuçlardan
    onc = df.merge(pd.read_csv("onceki/sam_sonuc.csv"), on="cati_id")
    dk = onc.dislama_nedeni.fillna("").astype(str)
    onc["supheli"] = ((onc.kaplama < 0.7) | (onc.tasma > 0.3) | (onc.guven < 0.85) | (onc.bolum == "supheli")
                      | dk.str.contains("gorsel_sorun"))
kontrol = set(onc[~onc.supheli].sample(150, random_state=0).cati_id)
secim = df if KAPSAM == "hepsi" else df[df.cati_id.isin(set(onc.cati_id[onc.supheli]) | kontrol)]
grup = onc.set_index("cati_id").supheli.map({True: "supheli", False: "temiz"})
CIKTI = "sam_multimask.csv"
os.makedirs("sam_maskeler_mm/kirpilmis", exist_ok=True); os.makedirs("sam_maskeler_mm/ham", exist_ok=True)
bitmis = set(pd.read_csv(CIKTI).cati_id) if os.path.exists(CIKTI) else set()
kalan = secim[~secim.cati_id.isin(bitmis)]
print(f"{len(secim)} çatı ({KAPSAM}), {len(bitmis)} bitmiş, {len(kalan)} kalan")

def olc(ham, ayak, px2):
    m = ham & ayak
    return dict(alan=round(m.sum() * px2, 1), kaplama=round(m.sum() / max(ayak.sum(), 1), 3),
                tasma=round((ham & ~ayak).sum() / max(ham.sum(), 1), 3),
                iou=round((ham & ayak).sum() / max((ham | ayak).sum(), 1), 3))
sonuc, t0 = [], time.time()
def yaz():
    global sonuc
    if sonuc:
        pd.DataFrame(sonuc).to_csv(CIKTI, mode="a", header=not os.path.exists(CIKTI), index=False); sonuc = []
for k, r in enumerate(kalan.itertuples(), 1):
    img = np.array(Image.open(r.goruntu).convert("RGB"))
    kutu = np.array(ast.literal_eval(r.kutu_px), dtype=float)
    ayak = np.array(Image.open(r.maske)) > 0
    px2 = r.yer_m_px ** 2
    predictor.set_image(img)
    masks, scores, _ = predictor.predict(box=kutu, multimask_output=True)
    iou = [(mm & ayak).sum() / max((mm | ayak).sum(), 1) for mm in masks]
    i = int(np.argmax(np.array(iou) + 1e-3 * scores))
    satir = dict(cati_id=r.cati_id, grup=grup.get(r.cati_id, "temiz"), secilen=i)
    for j, mm in enumerate(masks):
        o = olc(mm, ayak, px2)
        satir.update({f"m{j}_kaplama": o["kaplama"], f"m{j}_tasma": o["tasma"], f"m{j}_skor": round(float(scores[j]), 3)})
    uygun = [mm for mm in masks if (mm & ~ayak).sum() / max(mm.sum(), 1) <= TASMA_ESIK]
    yontem = {"A": masks[i], "U": masks.any(axis=0), "S": np.logical_or.reduce(uygun) if uygun else masks[i]}
    for ad, ham in yontem.items():
        satir.update({f"{ad}_{a}": v for a, v in olc(ham, ayak, px2).items()})
    s_ham = yontem["S"]
    Image.fromarray(((s_ham & ayak) * 255).astype(np.uint8)).save(f"sam_maskeler_mm/kirpilmis/c{r.cati_id:04d}.png")
    Image.fromarray((s_ham * 255).astype(np.uint8)).save(f"sam_maskeler_mm/ham/c{r.cati_id:04d}.png")
    sonuc.append(satir)
    if k % 25 == 0:
        yaz(); h = (time.time() - t0) / k
        print(f"{k}/{len(kalan)}  ~{h:.1f} sn/çatı, kalan ~{h*(len(kalan)-k)/60:.0f} dk")
yaz()
mm = pd.read_csv(CIKTI).drop_duplicates("cati_id", keep="last")
mm = mm[mm.cati_id.isin(secim.cati_id)]
assert set(mm.cati_id) == set(secim.cati_id), "eksik çatı var"
print("bitti:", len(mm), mm.grup.value_counts().to_dict())
""")
kod("""
# 10) Karşılaştırma: A (mevcut) / U (hepsi) / S (seçici birleşim)
import os, ast, numpy as np, pandas as pd, matplotlib.pyplot as plt
from PIL import Image
os.chdir("/content/veri")
mm = pd.read_csv("sam_multimask.csv").drop_duplicates("cati_id", keep="last").reset_index(drop=True)
def iyi(p): return (mm[f"{p}_kaplama"] >= 0.7) & (mm[f"{p}_tasma"] <= 0.3)
ozet = []
for g, gg in mm.groupby("grup"):
    for p in "AUS":
        ozet.append(dict(grup=g, yontem=p, cati=len(gg), kaplama_medyan=gg[f"{p}_kaplama"].median(),
                         tasma_medyan=gg[f"{p}_tasma"].median(), iou_medyan=gg[f"{p}_iou"].median(),
                         kural_gecen=int(iyi(p)[gg.index].sum()), alan_m2=round(gg[f"{p}_alan"].sum())))
print(pd.DataFrame(ozet).round(3).to_string(index=False))
sup = mm[(mm.grup == "supheli") & (mm.A_kaplama < 0.7)]
print(f"kaplama < 0,7 olan şüpheli {len(sup)} çatı: S ile kurala uyan {int(iyi('S')[sup.index].sum())}, U ile {int(iyi('U')[sup.index].sum())}")
tem = mm[mm.grup == "temiz"]
print(f"temiz {len(tem)} çatı: kurala uymaz hale gelen S ile {int((~iyi('S')[tem.index]).sum())}, U ile {int((~iyi('U')[tem.index]).sum())}")
# görsel: S'nin kaplamayı en çok artırdığı 15 çatı — sol A (mevcut), sağ S (mavi: ayak izi içi, kırmızı: taşma)
tablo = pd.read_csv("sam_girdi.csv").set_index("cati_id")
goster = mm.assign(fark=mm.S_kaplama - mm.A_kaplama).nlargest(15, "fark")
fig, ax = plt.subplots(len(goster), 2, figsize=(7, 3.3 * len(goster)), squeeze=False)
for (a1, a2), q in zip(ax, goster.itertuples()):
    r = tablo.loc[q.cati_id]
    img = np.array(Image.open(r.goruntu).convert("RGB")); ayak = np.array(Image.open(r.maske)) > 0
    s_ham = np.array(Image.open(f"sam_maskeler_mm/ham/c{q.cati_id:04d}.png")) > 0
    yol = f"sam_maskeler/c{q.cati_id:04d}.png"
    ma = np.array(Image.open(yol if os.path.exists(yol) else "onceki/" + yol)) > 0
    p = np.array(ast.literal_eval(r.poligon_px))
    for a, baslik in ((a1, f"c{q.cati_id:04d} A kap={q.A_kaplama}"), (a2, f"S kap={q.S_kaplama} taş={q.S_tasma}")):
        a.imshow(img); a.plot(p[:, 0], p[:, 1], c="yellow", lw=1); a.set_title(baslik, fontsize=8); a.axis("off")
    a1.imshow(np.ma.masked_where(~ma, ma), alpha=0.45, cmap="winter")
    a2.imshow(np.ma.masked_where(~(s_ham & ayak), s_ham), alpha=0.45, cmap="winter")
    a2.imshow(np.ma.masked_where(~(s_ham & ~ayak), s_ham), alpha=0.6, cmap="autumn")
plt.tight_layout(); plt.savefig("sam_multimask_onizleme.jpg", dpi=90); plt.show()
""")
kod("""
# 11) Multimask sonuçlarını indir
import os, zipfile
from google.colab import files
os.chdir("/content/veri")
with zipfile.ZipFile("/content/sam_multimask.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in ["sam_multimask.csv", "sam_multimask_onizleme.jpg"]:
        if os.path.exists(f): z.write(f)
    for kok, _, dosyalar in os.walk("sam_maskeler_mm"):
        for f in sorted(dosyalar): z.write(os.path.join(kok, f))
files.download("/content/sam_multimask.zip")
""")
nb = {'cells': H, 'metadata': {'accelerator': 'GPU', 'colab': {'provenance': [], 'gpuType': 'T4'},
      'kernelspec': {'display_name': 'Python 3', 'name': 'python3'}, 'language_info': {'name': 'python'}},
      'nbformat': 4, 'nbformat_minor': 0}
json.dump(nb, open(HEDEF / 'sam_birlesik_colab.ipynb', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

(HEDEF / 'BENIOKU.md').write_text(f"""# Çatı GES — Birleşik SAM veri seti (OSB + kamu)

{N} çatı (taban alanı ≥ 200 m²): {d.bolge.value_counts().to_dict()} · tür {d.tur.value_counts().to_dict()}.
Ayak izleri 2026-10-22 elle düzeltilmiş haliyle ({int(elle.sum())} çatı `hizalama = elle_duzeltildi`). Üretici `CatiGunes/scripts/sam_birlesik_paketi.py`.
Colab: `sam_birlesik_colab.ipynb` (tek defter; bu zip'i tek kez yükle).

| Dosya | Ne |
|---|---|
| `goruntuler/cNNNN.jpg` | Uydu kesiti (NNNN = `cati_id`) |
| `maskeler/cNNNN.png` | Ayak izi maskesi (255 = çatı) — zayıf etiket, panele uygun alan DEĞİL |
| `panelsiz/cNNNN.png` | Kısmi GES'li çatıda elle çizilen panelsiz (kullanılabilir) alan; SAM maskesi bununla kesilir |
| `sam_girdi.csv` | 1 satır = 1 çatı: `kutu_px` (SAM kutu istemi), `poligon_px`, `yer_m_px` (alan = piksel × yer_m_px²), `bolum`, `egitim_uygun`, `dislama_nedeni` |
| `georef.csv`, `sinirlar.geojson` | Harita (defter hücre 7) |
| `onceki/` | Önceki SAM sonuçları (aynı yöntem); defter varsayılan olarak bunları alır, yalnız eksikleri koşar |

- `bolum`: train / val / test_referans / supheli eski setten KORUNDU (test_referans = insan etiketi için sabit 150); sonradan eklenenler `ikcu_yeni` (İKÇÜ), `yeni`.
- `dislama_nedeni`: `gorsel_sorun` (görüntü kötü / ağaç altı / şekil uyumsuz), `dar_cati_<8m`, `gorsel_kontrol_yapilmadi` (İKÇÜ). `egitim_uygun` = neden yok ve train/val/test bölümünde.
- Mevcut GES (2026-10-26): bütün çatılar SAM'e girer; `sam_maskeler/` + `sam_alan_m2` = çatının tamamı (gösterim; web'de
  `panel_durumu` ile filtrelenir). Potansiyel için `uygun_maskeler/` + `uygun_alan_m2`: `tam_dolu` → 0, `kismi_panel_dusuldu`
  → SAM maskesi ∩ `panelsiz/`. Harita ve geojson'da ikisi de var. Ayak izi
  değişen çatıların önceki SAM sonucu alınmadı (yeniden koşulur).
- Şüpheli kuralı: kaplama < 0,7 | taşma > 0,3 | güven < 0,85 | şüpheli bölüm | görsel sorun. Puanlar ayak izine göre, gerçek doğruluk değil.
""", encoding='utf-8')
z = shutil.make_archive(str(HEDEF), 'zip', HEDEF)
print('%d cati %s | bolum %s' % (N, d.bolge.value_counts().to_dict(), d.bolum.value_counts().to_dict()))
print('egitim_uygun %d | dislama %s' % (d.egitim_uygun.sum(), d.dislama_nedeni.value_counts().to_dict()))
print('onceki sonuc %d, eksik (Colab kosacak) %d | elle duzeltilen %d' % (len(o), N - len(o), elle.sum()))
print('zip:', z, round(os.path.getsize(z) / 1e6, 1), 'MB')
