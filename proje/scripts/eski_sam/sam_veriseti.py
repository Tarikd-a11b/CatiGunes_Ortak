"""SAM veri seti: Model_Verisi'nden Colab'a yüklenecek düz bir paket kurar.

Kaynak: Desktop/CatiGunes_Model_Verisi (catilar.csv + cati_kesitleri/indeks.csv)
Çıktı : Desktop/CatiGunes_SAM_Veriseti/ (+ aynı adlı .zip)
  goruntuler/cNNNN.jpg   uydu kesiti
  maskeler/cNNNN.png     çatı ayak izi maskesi (poligon_px'ten, 255 = çatı)
  tum.csv                1 satır = 1 çatı, bolum sütunuyla
  train/val/test_referans/deneme/supheli.csv
Kaynağa dokunmaz; tekrar çalıştırınca klasörü baştan kurar.
"""
import ast
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

KAYNAK = Path.home() / "Desktop" / "CatiGunes_Model_Verisi"
HEDEF = Path.home() / "Desktop" / "CatiGunes_SAM_Veriseti"
TOHUM = 42
TEST_N = 150
VAL_ORAN = 0.15

cati = pd.read_csv(KAYNAK / "catilar.csv")
ind = pd.read_csv(KAYNAK / "cati_kesitleri" / "indeks.csv")
d = cati.merge(
    ind[["kesit", "kutu_px", "poligon_px", "yer_m_px", "genislik_px", "yukseklik_px",
         "uydu", "gercek_cozunurluk_m", "cekim_tarihi", "hizalama_kazanci", "eksik_karo"]],
    on="kesit", how="left", validate="1:1")
assert d["kutu_px"].notna().all(), "indekste eşi olmayan çatı var"

d["ad"] = d["cati_id"].map(lambda i: f"c{int(i):04d}")
d["goruntu"] = "goruntuler/" + d["ad"] + ".jpg"
d["maske"] = "maskeler/" + d["ad"] + ".png"
d["grup"] = np.where(d["bolge"] == "cigli_kamu", "kamu", "osb")
d["alan_sinifi"] = pd.cut(d["alan_m2"], [0, 200, 1000, 5000, np.inf],
                          labels=["<200", "200-1000", "1000-5000", ">5000"])
d["ges"] = d["mevcut_ges"].fillna("yok")
d["hizalama"] = np.where(d["hizalama_kazanci"] >= 1.15, "cati_bazli", "yalniz_blok")

# --- bölümler ---
d["bolum"] = ""
supheli = d["gorsel_kontrol"].notna()
d.loc[supheli, "bolum"] = "supheli"
uygun = d[~supheli].copy()
uygun["katman"] = (uygun["grup"] + "|" + uygun["uydu"] + "|"
                   + uygun["alan_sinifi"].astype(str) + "|" + (uygun["ges"] != "yok").astype(str))

# test_referans: her katmandan en az 2 (varsa), kalanı orantılı → insan etiketleyecek
rng = np.random.default_rng(TOHUM)
secilen = []
for _, g in uygun.groupby("katman"):
    secilen += list(g.sample(min(2, len(g)), random_state=TOHUM).index)
kalan = uygun.drop(secilen)
ek = TEST_N - len(secilen)
if ek > 0:
    secilen += list(kalan.groupby("katman", group_keys=False)
                    .apply(lambda g: g.sample(frac=ek / len(kalan), random_state=TOHUM))
                    .index)
    eksik = TEST_N - len(secilen)
    if eksik > 0:
        secilen += list(uygun.drop(secilen).sample(eksik, random_state=TOHUM).index)
secilen = secilen[:TEST_N]
d.loc[secilen, "bolum"] = "test_referans"

kalan = uygun.drop(secilen)
val = kalan.groupby("katman", group_keys=False).apply(
    lambda g: g.sample(frac=VAL_ORAN, random_state=TOHUM)).index
d.loc[val, "bolum"] = "val"
d.loc[(d["bolum"] == "") , "bolum"] = "train"

# deneme: Colab'da ilk koşu için 10 çatı — farklı gruplardan 8 + şüpheliden 2
deneme = []
for anahtar in [("osb", "LG03", "<200"), ("osb", "LG03", "1000-5000"), ("osb", "LG03", ">5000"),
                ("osb", "WV02", "200-1000"), ("osb", "WV02", ">5000"),
                ("kamu", "LG03", "200-1000"), ("kamu", "LG03", "1000-5000")]:
    g = d[(d["bolum"] == "val") & (d["grup"] == anahtar[0]) & (d["uydu"] == anahtar[1])
          & (d["alan_sinifi"].astype(str) == anahtar[2]) & (d["ges"] == "yok")]
    if len(g):
        deneme.append(g.sample(1, random_state=TOHUM).index[0])
g = d[(d["bolum"] == "val") & (d["ges"] == "kismi")]
if len(g):
    deneme.append(g.sample(1, random_state=TOHUM).index[0])
deneme += list(d[d["bolum"] == "supheli"].sample(2, random_state=TOHUM).index)
d["deneme"] = d.index.isin(deneme)

# --- dosyalar ---
if HEDEF.exists():
    shutil.rmtree(HEDEF)
(HEDEF / "goruntuler").mkdir(parents=True)
(HEDEF / "maskeler").mkdir()

for r in d.itertuples():
    kaynak_jpg = KAYNAK / "cati_kesitleri" / r.kesit
    shutil.copy2(kaynak_jpg, HEDEF / r.goruntu)
    with Image.open(kaynak_jpg) as im:
        boyut = im.size
    m = Image.new("L", boyut, 0)
    pts = [tuple(p) for p in ast.literal_eval(r.poligon_px)]
    ImageDraw.Draw(m).polygon(pts, fill=255)
    m.save(HEDEF / r.maske)

sutunlar = ["cati_id", "goruntu", "maske", "bolum", "deneme", "bolge", "tur", "kurum_ad",
            "alan_m2", "alan_sinifi", "kutu_px", "poligon_px", "yer_m_px",
            "uydu", "gercek_cozunurluk_m", "cekim_tarihi", "hizalama",
            "mevcut_ges", "gorsel_kontrol", "kesit", "osm", "lon", "lat"]
tum = d[sutunlar].sort_values("cati_id")
tum.to_csv(HEDEF / "tum.csv", index=False, encoding="utf-8-sig")
for b in ["train", "val", "test_referans", "supheli"]:
    tum[tum["bolum"] == b].to_csv(HEDEF / f"{b}.csv", index=False, encoding="utf-8-sig")
tum[tum["deneme"]].to_csv(HEDEF / "deneme.csv", index=False, encoding="utf-8-sig")

# önizleme: deneme çatıları, kutu (kırmızı) + ayak izi (sarı)
kartlar = []
for r in d[d["deneme"]].sort_values("cati_id").itertuples():
    im = Image.open(HEDEF / r.goruntu).convert("RGB")
    dr = ImageDraw.Draw(im)
    dr.rectangle(ast.literal_eval(r.kutu_px), outline=(255, 0, 0), width=2)
    dr.line([tuple(p) for p in ast.literal_eval(r.poligon_px)], fill=(255, 220, 0), width=2)
    im.thumbnail((300, 300))
    kart = Image.new("RGB", (300, 320), "white")
    kart.paste(im, (0, 0))
    ImageDraw.Draw(kart).text((4, 304), f"{r.ad} {r.tur} {r.uydu} {int(r.alan_m2)} m2 {r.bolum}",
                              fill="black")
    kartlar.append(kart)
if kartlar:
    sut = 5
    sat = (len(kartlar) + sut - 1) // sut
    pano = Image.new("RGB", (300 * sut, 320 * sat), "white")
    for i, k in enumerate(kartlar):
        pano.paste(k, ((i % sut) * 300, (i // sut) * 320))
    pano.save(HEDEF / "deneme_onizleme.jpg", quality=88)

ozet = {
    "toplam": int(len(tum)),
    "bolum": tum["bolum"].value_counts().to_dict(),
    "deneme": int(tum["deneme"].sum()),
    "test_referans_katman": {
        "|".join(map(str, k)): int(v) for k, v in
        d[d["bolum"] == "test_referans"]
        .groupby(["grup", "uydu", "alan_sinifi", "ges"], observed=True).size().items()},
}
(HEDEF / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2), encoding="utf-8")
shutil.copy2(Path(__file__).with_name("sam_veriseti_BENIOKU.md"), HEDEF / "BENIOKU.md")
zip_yol = shutil.make_archive(str(HEDEF), "zip", HEDEF)
print(json.dumps(ozet, ensure_ascii=False, indent=2))
print("zip:", zip_yol)
