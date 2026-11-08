# -*- coding: utf-8 -*-
"""SAM kosularini tek sonuc tablosunda birlestirir (2026-10-22).
Kosular (veri/ham/sam/): osb_2026-10-17 (1.456 cati, OSB kismi gecerli; 21.10 OSB kosusu birebir ayni)
                         kamu_2026-10-21 (80 kamu catisi)
                         duzeltme_2026-10-22 (ayak izi elle duzeltilen 24 cati; bunlarda eski sonuc gecersiz)
Oncelik: multimask S kurali (asagida) > birlesik > duzeltme > kamu > osb. Yalniz Model_Verisi'ndeki (>= 200 m2) catilar; maske_dosyasi veri/ham/sam'a gore.
Cikti : veri/ham/sam/sam_sonuc_birlesik.csv
  python scripts/sam_sonuc_birlestir.py"""
import os
import pandas as pd

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAM = os.path.join(KOK, 'veri', 'ham', 'sam')
MV = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi')
KOSU = [('birlesik_2026-10-22', 'sam_sonuc_tam.csv'),   # birlesik defter: 1.085 cati, en guncel (oncekiler + 5 yeni)
        ('duzeltme_2026-10-22', 'sam_sonuc_duzeltme.csv'), ('kamu_2026-10-21', 'sam_sonuc_kamu.csv'),
        ('osb_2026-10-17', 'sam_sonuc.csv')]
MULTIMASK = True   # False: multimask S kuralini uygulama (yalniz tek maske, A)
SUT = ['cati_id', 'kosu', 'maske_dosyasi', 'sam_alan_m2', 'ayak_izi_m2', 'kaplama', 'tasma', 'iou_ayak', 'guven',
       'secilen_maske', 'supheli']

cat = pd.read_csv(os.path.join(MV, 'catilar.csv'))
duz = set(cat.cati_id[cat.ayak_izi_duzeltme.notna()])
parca = []
for klasor, ad in KOSU:
    s = pd.read_csv(os.path.join(SAM, klasor, ad)).assign(kosu=klasor)
    s['maske_dosyasi'] = klasor + '/' + s.maske_dosyasi
    if klasor not in ('birlesik_2026-10-22', 'duzeltme_2026-10-22'): s = s[~s.cati_id.isin(duz)]   # eski ayak iziyle kosulmus -> gecersiz
    # supheli kurali her kosuda ayni (kaplama < 0,7 | tasma > 0,3 | guven < 0,85); 17.10 kosusunda bolum/gorsel isareti de vardi
    if 'supheli' not in s: s['supheli'] = False
    s['supheli'] = (s.kaplama < 0.7) | (s.tasma > 0.3) | (s.guven < 0.85) | s.supheli.astype(bool)
    parca.append(s[SUT])
s = pd.concat(parca).drop_duplicates('cati_id', keep='first')
# multimask (22.10, supheliler + 150 temiz kontrol): kaplama < 0,7 ise ve S (tasmasi <= 0,3 maskelerin birlesimi) daha iyiyse S.
# Kontrolde 0 temiz cati bozuldu; kaplama < 0,7 olan her cati olculdu. Guven A maskesinin skoru olarak kalir.
MM = 'multimask_2026-10-22'
if MULTIMASK:
    mm = pd.read_csv(os.path.join(SAM, MM, 'sam_multimask.csv')).drop_duplicates('cati_id', keep='last').set_index('cati_id')
    s = s.set_index('cati_id')
    k = mm.index[mm.index.isin(s.index)]
    k = k[(s.loc[k, 'kaplama'] < 0.7) & (mm.loc[k, 'S_kaplama'] > s.loc[k, 'kaplama']) & (mm.loc[k, 'S_tasma'] <= 0.3)]
    kural = lambda d: (d.kaplama < 0.7) | (d.tasma > 0.3) | (d.guven < 0.85)
    isaret = s.loc[k, 'supheli'].astype(bool) & ~kural(s.loc[k])   # gorsel / bolum isareti, olcumden bagimsiz
    s.loc[k, ['sam_alan_m2', 'kaplama', 'tasma', 'iou_ayak']] = mm.loc[k, ['S_alan', 'S_kaplama', 'S_tasma', 'S_iou']].values
    s.loc[k, 'maske_dosyasi'] = [f'{MM}/sam_maskeler_mm/kirpilmis/c{i:04d}.png' for i in k]
    s['secilen_maske'] = s.secilen_maske.astype(object); s.loc[k, 'secilen_maske'] = 'S'   # 0-2 = tek maske
    s.loc[k, 'kosu'] = MM
    s['supheli'] = s.supheli.astype(bool)
    s.loc[k, 'supheli'] = kural(s.loc[k]) | isaret
    s = s.reset_index()
    print('multimask S uygulanan: %d cati' % len(k))
s = cat[['cati_id', 'osm', 'bolge', 'tur', 'alan_m2', 'mevcut_ges', 'gorsel_kontrol', 'ayak_izi_duzeltme']].merge(s, on='cati_id', how='inner')
s.sort_values('cati_id').to_csv(os.path.join(SAM, 'sam_sonuc_birlesik.csv'), index=False, encoding='utf-8')
eksik = cat[~cat.cati_id.isin(s.cati_id)]
print('birlesik %d cati %s | kosu %s' % (len(s), s.bolge.value_counts().to_dict(), s.kosu.value_counts().to_dict()))
print('supheli: %d (%%%.1f) %s' % (s.supheli.sum(), 100 * s.supheli.mean(), s.groupby('bolge').supheli.sum().to_dict()))
print('SAM / ayak izi alan: %%%.1f (temiz %%%.1f)' % (100 * s.sam_alan_m2.sum() / s.ayak_izi_m2.sum(),
      100 * s[~s.supheli].sam_alan_m2.sum() / s[~s.supheli].ayak_izi_m2.sum()))
print("Model_Verisi'nde SAM sonucu olmayan: %d %s" % (len(eksik), eksik.tur.value_counts().to_dict()))
