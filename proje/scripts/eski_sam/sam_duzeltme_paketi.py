# -*- coding: utf-8 -*-
"""SAM duzeltme paketi (2026-10-22): yalniz ayak izi ELLE duzeltilen catilar icin Colab kosusu.
Koşu deterministik (17.10 ve 21.10 OSB kosulari birebir ayni) -> duzeltilmeyen catilarin sonucu degismez, hepsini
yeniden kosmaya gerek yok. Ayni model/ayar (vit_h, kutu istemi, multimask, ayak izine en yakin maske, ayak izine kirpma).
Kaynak: Desktop/CatiGunes_SAM_Veriseti (sam_veriseti_guncelle.py + sam_egitim_listesi.py sonrasi)
        Desktop/CatiGunes_Model_Verisi/catilar.csv (ayak_izi_duzeltme dolu olanlar)
Cikti : Desktop/CatiGunes_SAM_Duzeltme/ (+ .zip): goruntuler/, maskeler/, sam_duzeltme.csv, sam_duzeltme_colab.ipynb
  python scripts/sam_duzeltme_paketi.py"""
import json, os, shutil
from pathlib import Path
import pandas as pd

MASA = Path.home() / "Desktop"
SAM = MASA / "CatiGunes_SAM_Veriseti"
HEDEF = MASA / "CatiGunes_SAM_Duzeltme"

cati = pd.read_csv(MASA / "CatiGunes_Model_Verisi" / "catilar.csv")
e = pd.read_csv(SAM / "sam_egitim_200m2.csv", encoding="utf-8-sig")
d = e[e.cati_id.isin(cati.cati_id[cati.ayak_izi_duzeltme.notna()])]
if HEDEF.exists(): shutil.rmtree(HEDEF)
(HEDEF / "goruntuler").mkdir(parents=True); (HEDEF / "maskeler").mkdir()
for r in d.itertuples():
    shutil.copy2(SAM / r.goruntu, HEDEF / r.goruntu); shutil.copy2(SAM / r.maske, HEDEF / r.maske)
d.to_csv(HEDEF / "sam_duzeltme.csv", index=False, encoding="utf-8-sig")

# defter: OSB defterinden (ayni model kurulumu ve yontem), girdi/cikti adlari degisir, harita hucreleri yok
nb = json.load(open(SAM / "sam_osb_colab.ipynb", encoding="utf-8"))
h = nb["cells"]
src = lambda i: "".join(h[i]["source"])
def yaz(i, s): h[i]["source"] = s.splitlines(keepends=True); h[i]["outputs"] = [] if h[i]["cell_type"] == "code" else None
yaz(0, "# Çatı GES — SAM düzeltme koşusu (%d çatı, ayak izi elle düzeltildi 2026-10-22)\n"
       "Girdi: `CatiGunes_SAM_Duzeltme.zip` → `sam_duzeltme.csv` (OSB + kamu). Yöntem OSB koşusuyla aynı.\n"
       "Çıktı: `sam_sonuc_duzeltme.zip` (csv + maskeler + önizleme) → Claude'a ver.\n\n"
       "Sıra: 1 → 2 (zip seç) → 3 → 4 (~1-2 dk) → 5 → 6 (indir). **Defteri tek sekmede aç.**" % len(d))
h[0].pop("outputs", None)
yaz(2, src(2).replace("CatiGunes_SAM_Veriseti.zip", "CatiGunes_SAM_Duzeltme.zip")
             .replace("/content/veri/sam_egitim_200m2.csv", "/content/veri/sam_duzeltme.csv"))
s4 = src(4)
s4 = s4.replace("ATATÜRK OSB (sam_egitim_200m2.csv, bolge=ataturk_osb)", "DÜZELTİLEN ÇATILAR (sam_duzeltme.csv)")
s4 = s4.replace('df = pd.read_csv("sam_egitim_200m2.csv")\ndf = df[df.bolge == "ataturk_osb"].reset_index(drop=True)\n'
                'assert len(df) == 1001, f"OSB çatı sayısı 1001 bekleniyordu, {len(df)} geldi"',
                'df = pd.read_csv("sam_duzeltme.csv")\nassert len(df) == %d, f"%d çatı bekleniyordu, {len(df)} geldi"' % (len(d), len(d)))
s4 = s4.replace("sam_maskeler_osb", "sam_maskeler_duzeltme").replace("sam_sonuc_osb.csv", "sam_sonuc_duzeltme.csv")
assert "sam_duzeltme.csv" in s4 and "1001" not in s4, "hucre 4 sablonu degismis"
yaz(4, s4)
yaz(5, src(5).replace("en düşük kaplamalı 20 OSB çatısı", "düzeltilen çatılar (en düşük kaplamalı 20)")
             .replace("sam_egitim_200m2.csv", "sam_duzeltme.csv").replace("sam_onizleme_osb.jpg", "sam_onizleme_duzeltme.jpg"))
yaz(6, src(6).replace("OSB sonuçlarını", "Düzeltme sonuçlarını").replace("sam_sonuc_osb", "sam_sonuc_duzeltme")
             .replace("sam_onizleme_osb.jpg", "sam_onizleme_duzeltme.jpg").replace("sam_maskeler_osb", "sam_maskeler_duzeltme"))
nb["cells"] = h[:7]
json.dump(nb, open(HEDEF / "sam_duzeltme_colab.ipynb", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
z = shutil.make_archive(str(HEDEF), "zip", HEDEF)
print("%d cati (%s) -> %s (%.1f MB)" % (len(d), d.bolge.value_counts().to_dict(), z, os.path.getsize(z) / 1e6))
