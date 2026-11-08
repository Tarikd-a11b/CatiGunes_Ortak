# -*- coding: utf-8 -*-
"""EKSIK ayak izi tespiti + SAM ile otomatik duzeltme (2026-10-26) - model egitimi yok, yalniz istem + aday secimi.
Sorun: insan cizimleriyle IoU'da SAM'in hatasi ayak izinden geliyor (ayak izi dogru: SAM 0,878; ayak izi eksik: 0,469).
OSM poligonu binanin yalniz bir parcasini gosterince kutu da kucuk kaliyor. Fikir: SAM'e daha genis alan verilince
ayak izini neredeyse tamamen iceren, daha buyuk ve duzgun (dolgun) bir cati buluyorsa ayak izi eksik; o maske alinir.
Girdi : Colab 13. hucre ciktisi sam_ayak_aday.zip (istemler k0/k25/k50/n; 12. hucrenin sam_aday.zip'i de olur: k0/k10/k0n)
        Model_Verisi/insan_referans (insan maskesi + bolum), CatiGunes_SAM_Birlesik/maskeler (ayak izi)
Kosu  : python scripts/ayak_izi_tespit.py <zip>
Yontem: ayak izi sorunlu (dislandi: ayakizi_eksik/hatali) catilar cati_id sirasiyla ikiye bolunur; esikler YALNIZ
        ayar bolumu + sorunlularin yarisinda secilir, test bolumu + diger yarida bir kez olculur.
        Temiz catilarda kural iyi sonucu bozmamali (yanlis alarm), sorunlularda IoU artmali.
Cikti : veri/elle/ayak_izi_tespit/ (ayar_tablosu.csv, test_ozet.csv, tespit.csv, maskeler/ = duzeltilen catilar)"""
import io, itertools, os, sys, zipfile
import numpy as np, pandas as pd
from PIL import Image
from scipy.spatial import ConvexHull

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASA = os.path.join(os.path.expanduser('~'), 'Desktop')
REF = os.path.join(MASA, 'CatiGunes_Model_Verisi', 'insan_referans')
SAMK = os.path.join(MASA, 'CatiGunes_SAM_Birlesik')
AYAK = os.path.join(SAMK, 'maskeler')
CIK = os.path.join(KOK, 'veri', 'elle', 'ayak_izi_tespit')
SORUNLU = ('ayakizi_eksik', 'ayakizi_hatali')
UST = 6.0   # ayak izinin 6 katindan buyuk maske: komsu bloklari / yolu da almis say
IZGARA = dict(icerme=(.85, .9, .95), dolgunluk=(.75, .85, .9), buyume=(1.15, 1.3, 1.5))


def iou(a, b):
    u = (a | b).sum()
    return (a & b).sum() / u if u else np.nan


def dolgunluk(m):
    """alan / dis bukey zarf alani: duzgun cati ~1, dal budak / L-avlu sizintisi dusuk."""
    y, x = np.nonzero(m)
    if len(x) < 10:
        return 0.0
    p = np.column_stack([x, y])
    if len(p) > 4000:
        p = p[np.random.default_rng(0).choice(len(p), 4000, replace=False)]
    try:
        return min(1.0, m.sum() / max(ConvexHull(p).volume, 1))
    except Exception:   # tek cizgi uzerindeki noktalar
        return 0.0


def insan_maskesi(d):
    """insan maskesi SAM kesitinin cercevesinde. 11 catida (2026-10-23 ayak izi duzeltmesi) kesit yeniden alindi,
    cizim eski kesitte: ayni olcek, yalniz kaydirma -> faz korelasyonuyla bulunur (eslesme ~0,999)."""
    h = np.array(Image.open(os.path.join(REF, 'insan_maske', d + '.png'))) > 0
    yeni = np.array(Image.open(os.path.join(SAMK, 'goruntuler', d + '.jpg')).convert('L'), float)
    if h.shape == yeni.shape:
        return h
    eski = np.array(Image.open(os.path.join(REF, 'goruntuler', d + '.jpg')).convert('L'), float)
    H, W = 2 * max(eski.shape[0], yeni.shape[0]), 2 * max(eski.shape[1], yeni.shape[1])
    a, b = np.zeros((H, W)), np.zeros((H, W))
    a[:eski.shape[0], :eski.shape[1]] = eski - eski.mean()
    b[:yeni.shape[0], :yeni.shape[1]] = yeni - yeni.mean()
    R = np.fft.fft2(b) * np.conj(np.fft.fft2(a))
    dy, dx = np.unravel_index(np.argmax(np.fft.ifft2(R / (np.abs(R) + 1e-9)).real), R.shape)
    dy, dx = (dy - H if dy > H // 2 else dy), (dx - W if dx > W // 2 else dx)
    out = np.zeros(yeni.shape, bool)
    y, x = np.nonzero(h)
    y, x = y + dy, x + dx
    i = (y >= 0) & (y < out.shape[0]) & (x >= 0) & (x < out.shape[1])
    out[y[i], x[i]] = True
    return out


def adaylar(z, ayak):
    """istem -> [(maske, ozellikler)]; k0 mevcut yontem icin ayri doner."""
    W = int(z['boyut'][1])
    out = {}
    for p in sorted({k[:-2] for k in z.files if k.endswith('_m')}):
        ms = np.unpackbits(z[p + '_m'], axis=-1)[..., :W].astype(bool)
        out[p] = []
        for m, s in zip(ms, z[p + '_s']):
            a = max(ayak.sum(), 1)
            kenar = m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any()
            out[p].append((m, dict(skor=float(s), alan_orani=m.sum() / a, icerme=(m & ayak).sum() / a,
                                   dolgunluk=dolgunluk(m), kenar=bool(kenar))))
    return out


def mevcut(ad, ayak):
    """bugunku SAM: k0'in ayak izine en benzeyen adayi, ayak iziyle kirpilmis."""
    m = max(ad['k0'], key=lambda t: iou(t[0], ayak) + 1e-3 * t[1]['skor'])[0]
    return m & ayak


def sec(ad, istemler, icerme, dolgunluk_, buyume):
    """kurala uyan en buyuk aday (ayak izini icerir, dolgun, kesit kenarina degmez, belirgin buyuk); yoksa None."""
    uy = [(m, o, p) for p in istemler for m, o in ad.get(p, [])
          if o['icerme'] >= icerme and o['dolgunluk'] >= dolgunluk_ and not o['kenar'] and buyume <= o['alan_orani'] <= UST]
    return max(uy, key=lambda t: t[0].sum()) if uy else None


def main(zp):
    z = zipfile.ZipFile(zp)
    kok = 'sam_ayak_aday' if any(n.startswith('sam_ayak_aday/') for n in z.namelist()) else 'sam_aday'
    dosyalar = sorted(n.split('/')[-1][:-4] for n in z.namelist() if n.endswith('.npz'))
    t = pd.read_csv(os.path.join(REF, 'liste.csv'))
    t = t[(t.bolum != 'dislandi') | t.dislama.fillna('').str.contains('|'.join(SORUNLU))].copy()
    t['sorunlu'] = t.bolum == 'dislandi'
    s = t[t.sorunlu].sort_values('cati_id')
    t.loc[s.index[::2], 'bolum'], t.loc[s.index[1::2], 'bolum'] = 'ayar', 'test'
    t = t[t.dosya.isin(dosyalar)]

    ADAY, H, A, M = {}, {}, {}, {}
    for d in dosyalar:
        a = np.array(Image.open(os.path.join(AYAK, d + '.png'))) > 0
        ADAY[d], A[d] = adaylar(np.load(io.BytesIO(z.read(f'{kok}/{d}.npz'))), a), a
        M[d] = mevcut(ADAY[d], a)
    for r in t.itertuples():
        H[r.dosya] = insan_maskesi(r.dosya)
    istem_tum = sorted({p for ad in ADAY.values() for p in ad} - {'k0'})
    istem_set = [(p,) for p in istem_tum] + [tuple(istem_tum)]

    def degerlendir(g, ist, ic, dl, bu):
        sat = []
        for r in g.itertuples():
            x = sec(ADAY[r.dosya], ist, ic, dl, bu)
            yeni = x[0] if x else M[r.dosya]
            sat.append(dict(cati_id=r.cati_id, sorunlu=r.sorunlu, tespit=x is not None,
                            iou_mevcut=iou(M[r.dosya], H[r.dosya]), iou_yeni=iou(yeni, H[r.dosya])))
        return pd.DataFrame(sat)

    def ozet(d):
        so, te = d[d.sorunlu], d[~d.sorunlu]
        return dict(n_sorunlu=len(so), yakalanan=int(so.tespit.sum()), n_temiz=len(te), yanlis_alarm=int(te.tespit.sum()),
                    sorunlu_iou_mevcut=so.iou_mevcut.median(), sorunlu_iou_yeni=so.iou_yeni.median(),
                    temiz_iou_mevcut=te.iou_mevcut.median(), temiz_iou_yeni=te.iou_yeni.median(),
                    hepsi_ort_mevcut=d.iou_mevcut.mean(), hepsi_ort_yeni=d.iou_yeni.mean())

    ay = t[t.bolum == 'ayar']
    satir = []
    for ist, ic, dl, bu in itertools.product(istem_set, *IZGARA.values()):
        satir.append(dict(istem='+'.join(ist), icerme=ic, dolgunluk=dl, buyume=bu, **ozet(degerlendir(ay, ist, ic, dl, bu))))
    tab = pd.DataFrame(satir)
    tab['kazanc'] = tab.hepsi_ort_yeni - tab.hepsi_ort_mevcut
    # once ortalama IoU kazanci; esitlikte daha az yanlis alarm
    tab = tab.sort_values(['kazanc', 'yanlis_alarm'], ascending=[False, True]).reset_index(drop=True)
    os.makedirs(os.path.join(CIK, 'maskeler'), exist_ok=True)
    tab.round(3).to_csv(os.path.join(CIK, 'ayar_tablosu.csv'), index=False, encoding='utf-8-sig')
    en = tab.iloc[0]
    ist, ic, dl, bu = tuple(en.istem.split('+')), en.icerme, en.dolgunluk, en.buyume
    pd.set_option('display.width', 220)
    print('AYAR bolumu - ilk 8 kural:\n', tab.head(8).round(3).to_string())

    te = degerlendir(t[t.bolum == 'test'], ist, ic, dl, bu)
    oz = pd.Series(ozet(te)).round(3)
    oz.to_frame('test').to_csv(os.path.join(CIK, 'test_ozet.csv'), encoding='utf-8-sig')
    print(f'\nTEST bolumu (bir kez) - kural: istem={en.istem} icerme>={ic} dolgunluk>={dl} buyume>={bu}\n', oz.to_string())
    print('test sorunlu catilar:\n', te[te.sorunlu].round(3).to_string(index=False))

    # secilen kural butun catilara: tespit listesi + duzeltilen maskeler (ayak izi yerine gececek aday)
    sat = []
    for d in dosyalar:
        x = sec(ADAY[d], ist, ic, dl, bu)
        k = [o for p in ist for _, o in ADAY[d].get(p, []) if o['icerme'] >= ic and o['alan_orani'] >= bu]
        sat.append(dict(dosya=d, cati_id=int(d[1:]), tespit=x is not None, istem=x[2] if x else '',
                        alan_orani=round(x[1]['alan_orani'], 2) if x else np.nan,
                        # buyuk aday var ama kesit kenarina degiyor: bina kesitten tasiyor, elle bak
                        kesit_yetersiz=x is None and any(o['kenar'] for o in k)))
        if x:
            Image.fromarray(x[0].astype(np.uint8) * 255).save(os.path.join(CIK, 'maskeler', d + '.png'))
    sd = pd.DataFrame(sat)
    sd.to_csv(os.path.join(CIK, 'tespit.csv'), index=False, encoding='utf-8-sig')
    print(f'\nbutun catilar ({len(sd)}): eksik ayak izi tespit {int(sd.tespit.sum())}, kesit yetersiz (elle) {int(sd.kesit_yetersiz.sum())}')


if __name__ == '__main__':
    main(sys.argv[1])
