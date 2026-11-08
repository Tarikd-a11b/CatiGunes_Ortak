# 13) ÇAPRAZ DOĞRULAMALI İNCE AYAR (2026-10-25) — insan çizimli 149 çatı, 5 kat, ~25-35 dk
# Sıra: 1 -> 2 (CatiGunes_SAM_Birlesik.zip) -> 3 -> bu hücre (insan_referans.zip ister). 4-12 gerekmez.
# Yalnız SAM'in maske çözücüsü (mask_decoder, ~4M parametre) eğitilir; görüntü ve istem kodlayıcı donuk.
# Her kat: 4/5 çatıyla eğit, kalan 1/5'te ölç -> her çatı bir kez, onu hiç görmemiş modelle ölçülür.
# Hiperparametreler önceden sabit; sonuca bakıp DEĞİŞTİRME (değişirse ölçüm iyimser olur).
# Kıyas aynı çatılarda: hazır SAM vs ince ayarlı, ikisi de mevcut kural (k0 kutu, ayak izine en uygun aday)
# ile; 'kirp' = ayak iziyle kırpılmış (bugünkü üretim), 'ham' = kırpılmamış.
# Çıktı: sam_ince_ayar.zip (sonuc.csv + ozet.txt [+ TUM_VERIYLE_EGIT=True ise cozucu.pt, ~16 MB])
import os, ast, copy, io, time, zipfile, contextlib, numpy as np, pandas as pd, torch, torch.nn.functional as F
from PIL import Image
from google.colab import files

KAT, DEVIR, LR, BIRIKIM, TOHUM = 5, 15, 5e-5, 8, 0
TUM_VERIYLE_EGIT = False   # CV sonucu iyiyse True yap: 149 çatının hepsiyle eğitir, cozucu.pt de iner
os.chdir("/content")
assert os.path.isdir("/content/veri/maskeler"), "önce 2. hücre (CatiGunes_SAM_Birlesik.zip)"
assert "sam" in globals(), "önce 3. hücre (model)"
REF = "/content/insan_referans"
if not os.path.exists(REF + "/liste.csv"):
    for ad in files.upload():
        zipfile.ZipFile(ad).extractall(REF)
if os.path.exists(REF + "/insan_referans/liste.csv"):
    REF += "/insan_referans"   # alt klasörlü zip seçildiyse
assert os.path.exists(REF + "/liste.csv"), "yanlış zip: Model_Verisi/insan_referans.zip seçilmeli"

t = pd.read_csv(REF + "/liste.csv")
t = t[t.bolum != "dislandi"].reset_index(drop=True)   # dislandi: çizim ile kutu aynı binaya bakmıyor
rng = np.random.default_rng(TOHUM)
sira = np.concatenate([rng.permutation(g.index.values) for _, g in t.groupby(["tur", "sam_supheli"])])
t.loc[sira, "kat"] = np.arange(len(sira)) % KAT   # tür x şüpheli katmanlı, katlar eşit büyüklükte
t["kat"] = t.kat.astype(int)
print(len(t), "çatı;", t.bolum.value_counts().to_dict(), "| kat başına", t.kat.value_counts().sort_index().tolist())

dev = sam.device
VAR = ("o", "h", "v", "hv")   # özgün + yatay / dikey / iki yönlü ayna (çoğaltma)
def cevir(a, v):
    if "h" in v: a = a[:, ::-1]
    if "v" in v: a = a[::-1]
    return np.ascontiguousarray(a)
def kutu_cevir(k, v, H, W):
    x1, y1, x2, y2 = k
    if "h" in v: x1, x2 = W - x2, W - x1
    if "v" in v: y1, y2 = H - y2, H - y1
    return np.array([[x1, y1, x2, y2]])

# görüntü gömmeleri bir kez hesaplanır (kodlayıcı donuk) — 149 x 4 ~ 5 dk, ~2,4 GB RAM
t0, veri = time.time(), {}
for k, r in enumerate(t.itertuples(), 1):
    img = np.array(Image.open(f"{REF}/goruntuler/{r.dosya}.jpg").convert("RGB"))
    ins = np.array(Image.open(f"{REF}/insan_maske/{r.dosya}.png")) > 0
    ayak = np.array(Image.open(f"/content/veri/maskeler/{r.dosya}.png")) > 0
    assert ins.shape == img.shape[:2] == ayak.shape, r.dosya
    H, W = ins.shape
    kutu = np.array(ast.literal_eval(r.kutu_px), dtype=float)
    for v in VAR:
        predictor.set_image(cevir(img, v))
        veri[r.cati_id, v] = dict(emb=predictor.features.cpu(), insize=predictor.input_size, orig=predictor.original_size,
                                  kutu=predictor.transform.apply_boxes(kutu_cevir(kutu, v, H, W), (H, W)),
                                  ins=torch.from_numpy(cevir(ins, v)))
    veri[r.cati_id, "ayak"], veri[r.cati_id, "insan"] = ayak, ins
    if k % 25 == 0:
        print(f"gömme {k}/{len(t)}  ~{(time.time() - t0) / k:.1f} sn/çatı")

def ileri(d):
    kutu = torch.as_tensor(d["kutu"], dtype=torch.float, device=dev)
    sp, de = sam.prompt_encoder(points=None, boxes=kutu, masks=None)
    low, sk = sam.mask_decoder(image_embeddings=d["emb"].to(dev), image_pe=sam.prompt_encoder.get_dense_pe(),
                               sparse_prompt_embeddings=sp, dense_prompt_embeddings=de, multimask_output=True)
    return sam.postprocess_masks(low, d["insize"], d["orig"])[0], sk[0]   # (3,H,W) logit, (3,) skor

def kayip(lg, gt):   # SAM'deki gibi: 3 adaydan en iyisinin kaybı (BCE + Dice)
    gt = gt.to(dev).float()[None].expand_as(lg)
    bce = F.binary_cross_entropy_with_logits(lg, gt, reduction="none").mean((1, 2))
    p = lg.sigmoid()
    dice = 1 - (2 * (p * gt).sum((1, 2)) + 1) / (p.sum((1, 2)) + gt.sum((1, 2)) + 1)
    return (bce + dice).min()

def iou(a, b):
    u = (a | b).sum()
    return (a & b).sum() / u if u else np.nan

@torch.no_grad()
def tahmin(cid):   # mevcut kural: ayak izine IoU'su en yüksek aday (eşitlikte skor), sonra kırpma
    lg, sk = ileri(veri[cid, "o"])
    m, s, ayak = (lg > 0).cpu().numpy(), sk.cpu().numpy(), veri[cid, "ayak"]
    sec = m[int(np.argmax(np.array([iou(x, ayak) for x in m]) + 1e-3 * s))]
    return sec, sec & ayak

ilk = copy.deepcopy(sam.mask_decoder.state_dict())
for p in sam.parameters():
    p.requires_grad_(False)

def egit(idler, etiket):
    torch.manual_seed(TOHUM)
    sam.mask_decoder.load_state_dict(ilk)
    for p in sam.mask_decoder.parameters():
        p.requires_grad_(True)
    sam.mask_decoder.train()
    opt = torch.optim.AdamW(sam.mask_decoder.parameters(), lr=LR, weight_decay=0.01)
    ornek = [(c, v) for c in idler for v in VAR]
    t1 = time.time()
    for e in range(DEVIR):
        top = 0.0
        for k, i in enumerate(torch.randperm(len(ornek)).tolist(), 1):
            d = veri[ornek[i]]
            lg, _ = ileri(d)
            l = kayip(lg, d["ins"])
            (l / BIRIKIM).backward()
            top += l.item()
            if k % BIRIKIM == 0 or k == len(ornek):
                opt.step(); opt.zero_grad()
        if e in (0, DEVIR // 2, DEVIR - 1):
            print(f"  {etiket} devir {e + 1}/{DEVIR}  kayıp {top / len(ornek):.3f}  ({time.time() - t1:.0f} sn)")
    sam.mask_decoder.eval()
    for p in sam.mask_decoder.parameters():
        p.requires_grad_(False)

sam.mask_decoder.load_state_dict(ilk); sam.mask_decoder.eval()
once = {c: tahmin(c) for c in t.cati_id}   # hazır SAM (katlardan bağımsız)
satir = []
try:
    for k in range(KAT):
        egit(t[t.kat != k].cati_id.tolist(), f"kat {k + 1}/{KAT}")
        for r in t[t.kat == k].itertuples():
            h, (oh, ok), (ih, ik) = veri[r.cati_id, "insan"], once[r.cati_id], tahmin(r.cati_id)
            satir.append(dict(cati_id=r.cati_id, bolum=r.bolum, kat=k, tur=r.tur, sam_supheli=r.sam_supheli,
                              cizim_seti=r.cizim_seti, once_kirp=iou(ok, h), once_ham=iou(oh, h),
                              ince_kirp=iou(ik, h), ince_ham=iou(ih, h)))
    if TUM_VERIYLE_EGIT:
        egit(t.cati_id.tolist(), "tüm veri")
        torch.save(sam.mask_decoder.state_dict(), "/content/cozucu.pt")
finally:
    sam.mask_decoder.load_state_dict(ilk); sam.mask_decoder.eval()   # sonraki hücreler hazır SAM'le çalışsın

d = pd.DataFrame(satir)
d.to_csv("/content/sonuc.csv", index=False, encoding="utf-8-sig")
S = ["once_kirp", "ince_kirp", "once_ham", "ince_ham"]
oz = lambda g: pd.concat([g[S].median().rename("medyan"), g[S].mean().rename("ort"), (g[S] >= .7).mean().rename(">=0,70")], axis=1).T
fark = d.ince_kirp - d.once_kirp
try:
    from scipy.stats import wilcoxon
    p = wilcoxon(d.ince_kirp, d.once_kirp).pvalue
except Exception:
    p = float("nan")
yazi = io.StringIO()
with contextlib.redirect_stdout(yazi):
    pd.set_option("display.width", 200)
    print(f"ÇAPRAZ DOĞRULAMA: {len(d)} çatı, {KAT} kat, {DEVIR} devir, lr {LR}, çoğaltma {VAR}")
    print("\nTÜMÜ"); print(oz(d).round(3).to_string())
    for col in ("bolum", "sam_supheli", "tur"):
        for ad, g in d.groupby(col):
            print(f"\n{col} = {ad} (n={len(g)})"); print(oz(g).round(3).to_string())
    print(f"\nkırpmalı, çatı bazında: iyileşen (>+0,02) {(fark > .02).sum()}, kötüleşen (<-0,02) {(fark < -.02).sum()}, "
          f"değişmeyen {(fark.abs() <= .02).sum()}; Wilcoxon p = {p:.3g}")
    print("en çok kötüleşen 5:", d.assign(f=fark).nsmallest(5, "f")[["cati_id", "once_kirp", "ince_kirp"]].round(3).values.tolist())
    print("kontrol: hazır SAM test medyanı (kirp) yerel sam_ayar ile 0,879 olmalı ->",
          round(d[d.bolum == "test"].once_kirp.median(), 3))
print(yazi.getvalue())
open("/content/ozet.txt", "w", encoding="utf-8").write(yazi.getvalue())
with zipfile.ZipFile("/content/sam_ince_ayar.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in ("sonuc.csv", "ozet.txt") + (("cozucu.pt",) if TUM_VERIYLE_EGIT else ()):
        z.write("/content/" + f, f)
files.download("/content/sam_ince_ayar.zip")
