# -*- coding: utf-8 -*-
"""Test referansi (insan cizimi) icin LabelMe klasoru hazirlar (2026-10-22).
Girdi : Desktop/CatiGunes_SAM_Birlesik/sam_girdi.csv (bolum = test_referans, 111 cati) + goruntuler/
Cikti : veri/elle/test_referans/
          goruntuler/   111 bos goruntu (maske/kutu yok), tek klasor
          konum/        ayni goruntu + hedef cati kutusu (yalniz hangi bina oldugunu gostermek icin)
          cizimler/     LabelMe JSON'lari (--output)
          cizimler_2/   ikinci bagimsiz cizim (20 cati, insanlar arasi uyum)
          liste.csv     cati_id, dosya, cift_cizim
          labels.txt    tek etiket: cati
          BENIOKU.md    cizim kilavuzu
Cift cizim catilari boyut sinifina gore orantili, sabit tohum -> her kosuda ayni.
Var olan JSON'lara dokunmaz (cizim baslamissa yeniden kosmak guvenli).
  python scripts/test_referans_paketi.py"""
import os
import ast
import shutil
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAM = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_SAM_Birlesik')
CIK = os.path.join(KOK, 'veri', 'elle', 'test_referans')
CIFT, TOHUM = 20, 42

g = pd.read_csv(os.path.join(SAM, 'sam_girdi.csv'))
t = g[g.bolum == 'test_referans'].copy()
rng = np.random.default_rng(TOHUM)
t['_r'] = rng.random(len(t))
t = t.sort_values('cati_id').reset_index(drop=True)
cift = t.groupby('alan_sinifi', group_keys=False).apply(
    lambda d: d.nsmallest(max(1, round(CIFT * len(d) / len(t))), '_r')).head(CIFT).index
t['cift_cizim'] = t.index.isin(cift)
t['dosya'] = t.goruntu.str.split('/').str[-1]

for k in ('goruntuler', 'konum', 'cizimler', 'cizimler_2'):
    os.makedirs(os.path.join(CIK, k), exist_ok=True)
for r in t.itertuples():
    kay = os.path.join(SAM, r.goruntu)
    hedef = os.path.join(CIK, 'goruntuler', r.dosya)
    if not os.path.exists(hedef): shutil.copy2(kay, hedef)
    im = Image.open(kay).convert('RGB')
    x0, y0, x1, y1 = ast.literal_eval(r.kutu_px)
    ImageDraw.Draw(im).rectangle([x0 - 6, y0 - 6, x1 + 6, y1 + 6], outline=(255, 230, 0), width=2)
    im.save(os.path.join(CIK, 'konum', r.dosya), quality=92)

t[['cati_id', 'dosya', 'bolge', 'tur', 'alan_sinifi', 'cift_cizim']].to_csv(
    os.path.join(CIK, 'liste.csv'), index=False, encoding='utf-8-sig')
with open(os.path.join(CIK, 'labels.txt'), 'w', encoding='utf-8') as f:
    f.write('__ignore__\ncati\n')
cift_ad = ', '.join(t.dosya[t.cift_cizim].str.replace('.jpg', '', regex=False))

with open(os.path.join(CIK, 'BENIOKU.md'), 'w', encoding='utf-8') as f:
    f.write(f"""# Test referansı — insan çizimi (LabelMe)

{len(t)} çatı (`bolum = test_referans`, modelde kullanılmadı) tek klasörde: `goruntuler/`.
Çizimler `cizimler/` klasörüne kaydedilir.

## Kurulum (bir kez)

    pip install labelme

## Çizim

    cd veri/elle/test_referans
    labelme goruntuler --output cizimler --labels labels.txt --nodata --autosave

1. Hangi bina? Aynı adlı dosyayı `konum/` klasöründe açın: hedef çatı sarı kutunun içinde.
   Kutu yalnız binayı bulmak için; sınırı kutuya göre değil görüntüye göre çizin.
2. **Create Polygons** (Ctrl+N) ile çatının dış sınırını köşe köşe tıklayın, ilk noktaya dönüp kapatın.
3. Etiket her zaman `cati`. Çatının tüm yüzleri (beşik/kırma iki yanı, mevcut paneller dahil) tek poligon.
4. Çatı birden fazla ayrı parçaysa her parçaya ayrı `cati` poligonu.
5. Sonraki görüntü: **D**, önceki: **A**. `--autosave` her görüntüyü `cizimler/` altına JSON olarak kaydeder.
6. SAM maskesine, önizlemelere ya da ayak izi haritasına bakmayın (çizim bağımsız olmalı).
7. Birden fazla kişi çiziyorsa aynı görüntüyü iki kişi çizmesin: işi dosya numarasına göre bölün
   (ör. "c0004–c0500 Ali"); `cizimler/` klasöründe hangi dosyanın bittiği görünür.

## İkinci bağımsız çizim (20 çatı)

`liste.csv` içinde `cift_cizim = True` olan {CIFT} çatıyı İLK çizenden FARKLI biri, onun çizimine
bakmadan yeniden çizer; çıktısı ayrı klasöre gider:

    labelme goruntuler --output cizimler_2 --labels labels.txt --nodata --autosave

Çatılar: {cift_ad}

Üretici: `scripts/test_referans_paketi.py` (sabit tohum; var olan JSON'lara dokunmaz).
""")
print(f'{len(t)} cati -> {CIK} | cift cizim {int(t.cift_cizim.sum())}:',
      t[t.cift_cizim].alan_sinifi.value_counts().to_dict())
