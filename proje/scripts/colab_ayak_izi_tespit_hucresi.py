# 13-HAZIRLIK) kurulum + Drive'dan CatiGunes_SAM_Birlesik.zip + model (tek hücre; ayrı defterde de çalışır)
import os, glob, zipfile, subprocess
from google.colab import drive, files
if not os.path.exists("/content/sam_vit_h_4b8939.pth"):
    subprocess.run("pip -q install git+https://github.com/facebookresearch/segment-anything.git", shell=True, check=True)
    subprocess.run("wget -q -c -P /content https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth", shell=True, check=True)
VERI = next((os.path.dirname(p) for p in glob.glob("/content/veri/**/sam_girdi.csv", recursive=True)), None)
if VERI is None:
    drive.mount("/content/drive")
    adaylar = [p for p in glob.glob("/content/drive/MyDrive/**/CatiGunes_SAM_Birlesik.zip", recursive=True)
               if os.path.getsize(p) == 57296771]
    if adaylar:
        zipfile.ZipFile(adaylar[0]).extractall("/content/veri")
    else:   # Drive'da yoksa elle seç: Desktop\CatiGunes_SAM_Birlesik.zip (2026-10-23, 57.296.771 bayt)
        for ad in files.upload():
            zipfile.ZipFile(ad).extractall("/content/veri")
    # zip kökte de olabilir, CatiGunes_SAM_Birlesik/ klasörü içinde de
    VERI = next(os.path.dirname(p) for p in glob.glob("/content/veri/**/sam_girdi.csv", recursive=True))
import torch
from segment_anything import sam_model_registry, SamPredictor
sam = sam_model_registry["vit_h"](checkpoint="/content/sam_vit_h_4b8939.pth").to("cuda")
predictor = SamPredictor(sam)
print("hazır:", torch.cuda.get_device_name(0), "| veri:", VERI)

# 13) AYAK İZİ TESPİTİ İÇİN ADAY MASKELER (2026-10-26) — 1.085 çatının hepsi, ~15-20 dk
# Soru: ayak izi binanın yalnız bir parçasını mı gösteriyor? SAM'e daha geniş alan verilince ayak izini içeren
# daha büyük, düzgün bir çatı buluyorsa ayak izi eksik. Seçim kuralı yerelde (scripts/ayak_izi_tespit.py)
# insan çizimleriyle ayarlanır. Çıktı: sam_ayak_aday.zip (tek indirme).
#   k0 = mevcut kutu   k25 / k50 = kutu her yönde %25 / %50 geniş   n = yalnız ayak izi içindeki en iç nokta (kutu yok)
import os, ast, time, zipfile, numpy as np, pandas as pd
from PIL import Image
from scipy.ndimage import distance_transform_edt
from google.colab import files
os.chdir(VERI)
df = pd.read_csv("sam_girdi.csv")
assert len(df) == 1085, f"1085 çatı bekleniyordu, {len(df)} geldi"
os.makedirs("sam_ayak_aday", exist_ok=True)
t0, yeni = time.time(), 0
for k, r in enumerate(df.itertuples(), 1):
    yol = f"sam_ayak_aday/c{r.cati_id:04d}.npz"
    if os.path.exists(yol):
        continue   # kesilirse hücreyi tekrar çalıştır, kaldığı yerden devam eder
    img = np.array(Image.open(r.goruntu).convert("RGB"))
    H, W = img.shape[:2]
    ayak = np.array(Image.open(r.maske)) > 0
    kutu = np.array(ast.literal_eval(r.kutu_px), dtype=float)
    w, h = kutu[2] - kutu[0], kutu[3] - kutu[1]
    sinir = [W - 1, H - 1, W - 1, H - 1]
    genis = lambda f: np.clip(kutu + np.array([-f * w, -f * h, f * w, f * h]), 0, sinir)
    y, x = np.unravel_index(np.argmax(distance_transform_edt(ayak)), ayak.shape)
    predictor.set_image(img)
    out = {"boyut": np.array([H, W])}
    for ad, arg in (("k0", dict(box=kutu)), ("k25", dict(box=genis(.25))), ("k50", dict(box=genis(.5))),
                    ("n", dict(point_coords=np.array([[x, y]]), point_labels=np.array([1])))):
        masks, scores, _ = predictor.predict(multimask_output=True, **arg)
        out[ad + "_m"] = np.packbits(masks, axis=-1)
        out[ad + "_s"] = scores
    np.savez_compressed(yol, **out)
    yeni += 1
    if yeni % 50 == 0:
        print(f"{k}/{len(df)}  ~{(time.time() - t0) / yeni:.1f} sn/çatı")
assert len(os.listdir("sam_ayak_aday")) == len(df), "eksik çatı var, hücreyi tekrar çalıştır"
with zipfile.ZipFile("/content/sam_ayak_aday.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir("sam_ayak_aday")):
        z.write(os.path.join("sam_ayak_aday", f))
print("bitti:", len(df), "çatı, zip %.1f MB" % (os.path.getsize("/content/sam_ayak_aday.zip") / 1e6))
files.download("/content/sam_ayak_aday.zip")
