# -*- coding: utf-8 -*-
"""Toplanti (23.10) icin tum elle cizim islerini tek pakette toplar.
Girdi : Desktop/CatiGunes_SAM_Birlesik/sam_girdi.csv + goruntuler/
        veri/ham/sam/sam_sonuc_birlesik.csv (supheli bayragi)
        veri/elle/test_referans/liste.csv (cift_cizim secimi aynen alinir)
Cikti : Desktop/Toplanti/Cizim_Paketi/
          1_test_referans/  111 cati (bolum = test_referans), etiket cati, 20 cift cizim
          2_kamu_ek/        20 kamu catisi (test disi), etiket cati
          3_supheli_ek/     30 supheli cati (test ve kamu ek disi), etiket cati
          4_panel/          27 kismi GES'li cati, etiket panel (konum'da cati siniri sari)
          gorev_dagilimi.csv  her cizim isi + onerilen pay (A-D), kisi sutunu bos
          BENIOKU.md
Secimler sabit tohumla (42). Var olan JSON'lara dokunmaz.
Ek setler (2, 3) yalniz degerlendirme icindir: ileride egitim setinden cikarilmali.
  python scripts/toplanti_cizim_paketi.py"""
import os
import ast
import shutil
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASA = os.path.join(os.path.expanduser('~'), 'Desktop')
SAM = os.path.join(MASA, 'CatiGunes_SAM_Birlesik')
CIK = os.path.join(MASA, 'Toplantı', 'Cizim_Paketi')
KAMU_EK, SUPHELI_EK, TOHUM = 20, 30, 42
PAYLAR = 'ABCD'

g = pd.read_csv(os.path.join(SAM, 'sam_girdi.csv'))
s = pd.read_csv(os.path.join(KOK, 'veri', 'ham', 'sam', 'sam_sonuc_birlesik.csv'))
g = g.merge(s[['cati_id', 'supheli']], on='cati_id', how='left')
g['dosya'] = g.goruntu.str.split('/').str[-1]
rng = np.random.default_rng(TOHUM)
g['_r'] = rng.random(len(g))

test = g[g.bolum == 'test_referans'].sort_values('cati_id')
cift = pd.read_csv(os.path.join(KOK, 'veri', 'elle', 'test_referans', 'liste.csv'))
test = test.merge(cift[['cati_id', 'cift_cizim']], on='cati_id')
kamu = g[(g.bolge == 'cigli_kamu') & (g.bolum != 'test_referans')].nsmallest(KAMU_EK, '_r')
sup = g[(g.supheli == True) & (g.bolum != 'test_referans')
        & ~g.cati_id.isin(kamu.cati_id)].nsmallest(SUPHELI_EK, '_r')
panel = g[g.mevcut_ges == 'kismi']
SETLER = [('1_test_referans', test, 'cati'), ('2_kamu_ek', kamu, 'cati'),
          ('3_supheli_ek', sup, 'cati'), ('4_panel', panel, 'panel')]


def konum(r, hedef, cati_siniri):
    im = Image.open(os.path.join(SAM, r.goruntu)).convert('RGB')
    d = ImageDraw.Draw(im)
    if cati_siniri:
        d.polygon([tuple(p) for p in ast.literal_eval(r.poligon_px)], outline=(255, 230, 0), width=2)
    else:
        x0, y0, x1, y1 = ast.literal_eval(r.kutu_px)
        d.rectangle([x0 - 6, y0 - 6, x1 + 6, y1 + 6], outline=(255, 230, 0), width=2)
    im.save(hedef, quality=92)


isler = []
for ad, t, etiket in SETLER:
    k = os.path.join(CIK, ad)
    klasorler = ('goruntuler', 'konum', 'cizimler') + (('cizimler_2',) if ad == '1_test_referans' else ())
    for x in klasorler:
        os.makedirs(os.path.join(k, x), exist_ok=True)
    t = t.sort_values('cati_id').reset_index(drop=True)
    for r in t.itertuples():
        h = os.path.join(k, 'goruntuler', r.dosya)
        if not os.path.exists(h):
            shutil.copy2(os.path.join(SAM, r.goruntu), h)
        konum(r, os.path.join(k, 'konum', r.dosya), etiket == 'panel')
    sut = ['cati_id', 'dosya', 'bolge', 'tur', 'kurum_ad', 'alan_m2', 'alan_sinifi', 'bolum', 'supheli', 'mevcut_ges']
    if ad == '1_test_referans':
        sut.append('cift_cizim')
    t[sut].to_csv(os.path.join(k, 'liste.csv'), index=False, encoding='utf-8-sig')
    with open(os.path.join(k, 'labels.txt'), 'w', encoding='utf-8') as f:
        f.write(f'__ignore__\n{etiket}\n')
    for r in t.itertuples():
        isler.append(dict(set=ad, dosya=r.dosya, cati_id=r.cati_id, cizim='1. cizim', klasor='cizimler'))
        if getattr(r, 'cift_cizim', False):
            isler.append(dict(set=ad, dosya=r.dosya, cati_id=r.cati_id, cizim='2. cizim (bagimsiz)',
                              klasor='cizimler_2'))

# Paylar: 1. cizimler sirayla A-D; 2. cizim her zaman 1. cizimi yapandan FARKLI paya
gd = pd.DataFrame(isler)
birinci = gd.cizim == '1. cizim'
gd.loc[birinci, 'pay'] = [PAYLAR[i % 4] for i in range(birinci.sum())]
ilk = gd[birinci].set_index(['set', 'dosya']).pay
gd.loc[~birinci, 'pay'] = [PAYLAR[(PAYLAR.index(ilk[(r.set, r.dosya)]) + 1) % 4]
                           for r in gd[~birinci].itertuples()]
gd['kisi'] = ''
gd.to_csv(os.path.join(CIK, 'gorev_dagilimi.csv'), index=False, encoding='utf-8-sig')
ozet = pd.crosstab(gd.set, gd.pay, margins=True, margins_name='toplam')

with open(os.path.join(CIK, 'BENIOKU.md'), 'w', encoding='utf-8') as f:
    f.write(f"""# Elle çizim paketi (LabelMe) — toplantı 23.10

| Klasör | Çatı | Etiket | Amaç |
|---|---|---|---|
| `1_test_referans` | {len(test)} (+{int(test.cift_cizim.sum())} ikinci çizim) | `cati` | Genel doğruluk (SAM ↔ insan IoU) |
| `2_kamu_ek` | {len(kamu)} | `cati` | Kamu çatıları için ayrı sonuç (testte yalnız {int((test.bolge == 'cigli_kamu').sum())} kamu var) |
| `3_supheli_ek` | {len(sup)} | `cati` | Yeşil/kırmızı bayrağının doğruluğu (testte yalnız {int((test.supheli == True).sum())} şüpheli var) |
| `4_panel` | {len(panel)} | `panel` | Kısmi GES'li çatılarda mevcut panel alanı |

Toplam {len(gd)} çizim. Önerilen dağılım (`gorev_dagilimi.csv`, `kisi` sütununu doldurun):

{ozet.to_markdown()}

## Kurulum (bir kez)

    pip install labelme

## Çizim (her klasörde aynı)

    cd <klasör>
    labelme goruntuler --output cizimler --labels labels.txt --nodata --autosave

- Hangi bina? Aynı adlı dosyayı `konum/` klasöründe açın, hedef sarı çizgiyle gösterilmiştir.
- **Ctrl+N** (Create Polygons) → köşelere tıklayın → ilk noktaya dönüp kapatın → etiketi seçin.
- **D** sonraki görüntü, **A** önceki görüntü. `--autosave` her görüntüyü `cizimler/` altına JSON olarak kaydeder.
- Yalnız size düşen dosyaları çizin (`gorev_dagilimi.csv` → pay).

### 1–3: çatı çizimi (`cati`)
- `konum/` içindeki sarı kutu yalnız binayı bulmak içindir; sınırı kutuya göre değil görüntüye göre çizin.
- Çatının tüm yüzleri (beşik/kırma çatının iki yanı, mevcut paneller dahil) tek poligon olsun.
- Çatı ayrı parçalardan oluşuyorsa her parçaya ayrı `cati` poligonu çizin.
- SAM maskesine, haritaya ya da önizlemelere bakmayın; çizim bağımsız olmalı.
- **İkinci çizim** (yalnız `1_test_referans`, `liste.csv` → `cift_cizim = True`): ilk çizenden farklı biri,
  onun çizimine bakmadan çizer. Çıktı ayrı klasöre gider:
  `labelme goruntuler --output cizimler_2 --labels labels.txt --nodata --autosave`

### 4: panel çizimi (`panel`)
- `konum/` içindeki sarı çizgi = modeldeki çatı sınırı. Yalnız bu çatının üstündeki panelleri çizin.
- Panel **grubunun dış sınırını** çizin; sıralar arasındaki boşluk içeride kalsın.
- Ayrı panel grupları için ayrı `panel` poligonları çizin.
- Panel yoksa ya da emin değilseniz boş bırakıp not alın.

## Bitince
Her kişi kendi `cizimler/` JSON'larını aynı klasöre (Drive) kopyalar; dosya adları çakışmaz.
Ek setler (2, 3) yalnız değerlendirme içindir, eğitim setinden çıkarılacak.

Üretici: `scripts/toplanti_cizim_paketi.py` (tohum {TOHUM}; var olan JSON'lara dokunmaz).
""")
print(f'{CIK}\n', ozet)
