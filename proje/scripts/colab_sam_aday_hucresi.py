# 12) SAM AYARI İÇİN ADAY MASKELER (2026-10-24) — insan çizimli 178 çatı, ~3-5 dk
# Sıra: 1 -> 2 (CatiGunes_SAM_Birlesik.zip) -> 3 -> bu hücre. 4-11 gerekmez.
# Her çatı için 3 istem x SAM'in 3 aday maskesi KIRPILMADAN kaydedilir; seçim kuralı yerelde
# (scripts/sam_ayar.py) insan çizimleriyle denenir. Çıktı: sam_aday.zip (tek indirme).
#   k0  = mevcut kutu        k10 = kutu her yönde %10 geniş        k0n = kutu + kutu merkezine pozitif nokta
import os, ast, time, zipfile, numpy as np, pandas as pd
from PIL import Image
from google.colab import files
os.chdir("/content/veri")
IDS = [4, 6, 7, 8, 9, 10, 15, 17, 25, 32, 33, 35, 36, 37, 45, 48, 56, 64, 75, 76, 79, 80, 90, 100, 101, 107, 113, 114,
       118, 125, 139, 140, 141, 144, 150, 157, 158, 159, 160, 171, 176, 190, 191, 224, 236, 240, 248, 253, 286, 316, 319,
       326, 329, 338, 360, 381, 392, 408, 412, 418, 427, 432, 434, 437, 441, 442, 447, 453, 457, 459, 465, 466, 467, 468,
       483, 485, 487, 505, 508, 514, 519, 528, 533, 557, 560, 568, 587, 595, 598, 602, 611, 625, 643, 647, 654, 657, 684,
       700, 711, 712, 727, 743, 755, 791, 828, 833, 857, 897, 919, 949, 986, 997, 998, 1001, 1004, 1055, 1056, 1057, 1063,
       1068, 1074, 1076, 1080, 1100, 1106, 1124, 1132, 1141, 1158, 1163, 1164, 1186, 1205, 1225, 1226, 1229, 1254, 1280,
       1293, 1307, 1317, 1324, 1329, 1334, 1341, 1358, 1395, 1397, 1398, 1399, 1400, 1402, 1404, 1414, 1415, 1417, 1423,
       1427, 1438, 1440, 1443, 1444, 1445, 1446, 1448, 1449, 1450, 1455, 1457, 1458, 1459, 1460, 1463, 1468, 1470, 1476,
       1488, 1495]
df = pd.read_csv("sam_girdi.csv").set_index("cati_id")
assert set(IDS) <= set(df.index), "sam_girdi.csv'de olmayan çatı var: yanlış zip?"
os.makedirs("sam_aday", exist_ok=True)
t0 = time.time()
for k, cid in enumerate(IDS, 1):
    yol = f"sam_aday/c{cid:04d}.npz"
    if os.path.exists(yol):
        continue   # kesilirse hücreyi tekrar çalıştır, kaldığı yerden devam eder
    r = df.loc[cid]
    img = np.array(Image.open(r.goruntu).convert("RGB"))
    H, W = img.shape[:2]
    kutu = np.array(ast.literal_eval(r.kutu_px), dtype=float)
    w, h = kutu[2] - kutu[0], kutu[3] - kutu[1]
    k10 = np.clip(kutu + np.array([-.1 * w, -.1 * h, .1 * w, .1 * h]), 0, [W - 1, H - 1, W - 1, H - 1])
    merkez = np.array([[(kutu[0] + kutu[2]) / 2, (kutu[1] + kutu[3]) / 2]])
    predictor.set_image(img)
    out = {"boyut": np.array([H, W])}
    for ad, arg in (("k0", dict(box=kutu)), ("k10", dict(box=k10)),
                    ("k0n", dict(box=kutu, point_coords=merkez, point_labels=np.array([1])))):
        masks, scores, _ = predictor.predict(multimask_output=True, **arg)
        out[ad + "_m"] = np.packbits(masks, axis=-1)
        out[ad + "_s"] = scores
    np.savez_compressed(yol, **out)
    if k % 25 == 0:
        print(f"{k}/{len(IDS)}  ~{(time.time() - t0) / k:.1f} sn/çatı")
assert len(os.listdir("sam_aday")) == len(IDS), "eksik çatı var, hücreyi tekrar çalıştır"
with zipfile.ZipFile("/content/sam_aday.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir("sam_aday")):
        z.write(os.path.join("sam_aday", f))
print("bitti:", len(IDS), "çatı, zip %.1f MB" % (os.path.getsize("/content/sam_aday.zip") / 1e6))
files.download("/content/sam_aday.zip")
