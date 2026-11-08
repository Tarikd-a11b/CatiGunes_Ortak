# -*- coding: utf-8 -*-
"""SAM maske SECIM KURALI ayari (2026-10-24) - model egitimi yok, yalniz istem + aday secimi.
Girdi : Colab 12. hucre ciktisi sam_aday.zip (insan cizimli 178 cati, 3 istem x 3 aday, kirpilmamis)
        Model_Verisi/insan_referans (insan maskesi + bolum), CatiGunes_SAM_Birlesik/maskeler (ayak izi)
Kosu  : python scripts/sam_ayar.py <sam_aday.zip>
Yontem: kurallar YALNIZ 'ayar' bolumunde siralanir, en iyisi secilir; 'test' bolumunde mevcut kural ile karsilastirilir
        (test yalniz bir kez, sonda olculur - ayar icin kullanilmaz). Cikti veri/elle/test_referans/sam_ayar_sonuc.csv"""
import io, os, sys, zipfile
import numpy as np, pandas as pd
from PIL import Image

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASA = os.path.join(os.path.expanduser('~'), 'Desktop')
REF = os.path.join(MASA, 'CatiGunes_Model_Verisi', 'insan_referans')
AYAK = os.path.join(MASA, 'CatiGunes_SAM_Birlesik', 'maskeler')
CIK = os.path.join(KOK, 'veri', 'elle', 'test_referans', 'sam_ayar_sonuc.csv')
TASMA = 0.3


def iou(a, b):
    u = (a | b).sum()
    return (a & b).sum() / u if u else np.nan


def kurallar(z, ayak):
    """kural adi -> maske. z: npz (istem -> 3 aday + skor)."""
    W = int(z['boyut'][1])
    out = {}
    for p in ('k0', 'k10', 'k0n'):
        m = np.unpackbits(z[p + '_m'], axis=-1)[..., :W].astype(bool)
        s = z[p + '_s']
        ai = [iou(x, ayak) for x in m]
        tas = [(x & ~ayak).sum() / max(x.sum(), 1) for x in m]
        uygun = [x for x, t in zip(m, tas) if t <= TASMA]
        aday = {'ayak_iou': m[int(np.argmax(np.array(ai) + 1e-3 * s))],   # mevcut yontem (k0 + kirpma = bugunku SAM)
                'skor': m[int(np.argmax(s))],
                'buyuk': m[int(np.argmax([x.sum() for x in m]))],
                'birlesim': m.any(0),
                'secici_birlesim': np.logical_or.reduce(uygun) if uygun else m[int(np.argmax(ai))]}
        for a, x in aday.items():
            out[f'{p}|{a}|ham'] = x
            out[f'{p}|{a}|kirp'] = x & ayak
    return out


def main(zp):
    t = pd.read_csv(os.path.join(REF, 'liste.csv'))
    t = t[t.bolum != 'dislandi']
    z = zipfile.ZipFile(zp)
    satir = []
    for r in t.itertuples():
        n = np.load(io.BytesIO(z.read(f'sam_aday/{r.dosya}.npz')))
        h = np.array(Image.open(os.path.join(REF, 'insan_maske', r.dosya + '.png'))) > 0
        a = np.array(Image.open(os.path.join(AYAK, r.dosya + '.png'))) > 0
        for k, m in kurallar(n, a).items():
            satir.append(dict(cati_id=r.cati_id, bolum=r.bolum, tur=r.tur, sam_supheli=r.sam_supheli, kural=k, iou=iou(m, h)))
    d = pd.DataFrame(satir)
    d.to_csv(CIK, index=False, encoding='utf-8-sig')
    oz = lambda g: pd.Series(dict(n=len(g), medyan=g.iou.median(), ort=g.iou.mean(), ge070=(g.iou >= .7).mean()))
    MEVCUT = 'k0|ayak_iou|kirp'
    ay = d[d.bolum == 'ayar'].groupby('kural').apply(oz, include_groups=False).sort_values(['ort', 'medyan'], ascending=False)
    pd.set_option('display.width', 200)
    print('AYAR bolumu (n=%d cati) - ilk 10 kural + mevcut:' % d[d.bolum == 'ayar'].cati_id.nunique())
    print(pd.concat([ay.head(10), ay.loc[[MEVCUT]]]).round(3).to_string())
    en = ay.index[0]
    te = d[(d.bolum == 'test') & d.kural.isin([MEVCUT, en])]
    print('\nTEST bolumu: mevcut (%s) vs secilen (%s)' % (MEVCUT, en))
    print(te.groupby('kural').apply(oz, include_groups=False).round(3).to_string())
    print(te.groupby(['tur', 'kural']).apply(oz, include_groups=False).round(3).to_string())
    print(te.groupby(['sam_supheli', 'kural']).apply(oz, include_groups=False).round(3).to_string())


if __name__ == '__main__':
    main(sys.argv[1])
