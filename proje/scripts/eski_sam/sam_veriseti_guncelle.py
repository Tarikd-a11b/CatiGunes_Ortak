# -*- coding: utf-8 -*-
"""SAM veri setini elle ayak izi duzeltmesinden sonra YERINDE gunceller (2026-10-22).
Neden: sam_veriseti.py bolumleri (train/val/test_referans) sabit tohumla SIFIRDAN boler -> yeniden kosarsa test seti
degisir, eski SAM sonuclari ve elle cizim plani kopar. Bu betik yalniz duzeltilen catilara dokunur:
  goruntuler/cNNNN.jpg + maskeler/cNNNN.png yeni kesitten, tum.csv satiri (alan, kutu_px, poligon_px, gorsel_kontrol...)
  sekil_uyumsuz yuzunden 'supheli' bolumundeki cati, isareti kalktiysa 'train'e gecer (test/val degismez).
Ardindan: python scripts/sam_egitim_listesi.py  ve  python scripts/sam_duzeltme_paketi.py
  python scripts/sam_veriseti_guncelle.py"""
import ast, shutil
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image, ImageDraw

KAYNAK = Path.home() / "Desktop" / "CatiGunes_Model_Verisi"
HEDEF = Path.home() / "Desktop" / "CatiGunes_SAM_Veriseti"

cati = pd.read_csv(KAYNAK / "catilar.csv")
ind = pd.read_csv(KAYNAK / "cati_kesitleri" / "indeks.csv").set_index("kesit")
tum = pd.read_csv(HEDEF / "tum.csv", encoding="utf-8-sig")
duz = cati[cati.ayak_izi_duzeltme.notna()]
gecen = []
for r in duz.itertuples():
    j = tum.index[tum.osm.eq(r.osm)]
    assert len(j) == 1, r.osm
    j = j[0]; k = ind.loc[r.kesit]; t = tum.loc[j]
    shutil.copy2(KAYNAK / "cati_kesitleri" / r.kesit, HEDEF / t.goruntu)
    with Image.open(HEDEF / t.goruntu) as im: boyut = im.size
    m = Image.new("L", boyut, 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in ast.literal_eval(k.poligon_px)], fill=255)
    m.save(HEDEF / t.maske)
    tum.loc[j, ["alan_m2", "kutu_px", "poligon_px", "yer_m_px", "gorsel_kontrol", "kesit", "lon", "lat"]] = [
        r.alan_m2, k.kutu_px, k.poligon_px, k.yer_m_px, r.gorsel_kontrol, r.kesit, r.lon, r.lat]
    tum.loc[j, "hizalama"] = "elle_duzeltildi"
    if t.bolum == "supheli" and not isinstance(r.gorsel_kontrol, str):
        tum.loc[j, "bolum"] = "train"; gecen.append(int(t.cati_id))
tum["alan_sinifi"] = pd.cut(tum["alan_m2"], [0, 200, 1000, 5000, np.inf],
                            labels=["<200", "200-1000", "1000-5000", ">5000"]).astype(str)
tum.to_csv(HEDEF / "tum.csv", index=False, encoding="utf-8-sig")
for b in ["train", "val", "test_referans", "supheli"]:
    tum[tum["bolum"] == b].to_csv(HEDEF / f"{b}.csv", index=False, encoding="utf-8-sig")
print("guncellenen %d cati; supheli -> train: %s" % (len(duz), gecen))
print(tum.bolum.value_counts().to_dict())
