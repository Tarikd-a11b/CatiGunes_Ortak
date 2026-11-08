"""Toplam cati alani sapmasinin guven araligi (2026-10-26).
Yansiz test orneklemi (1_test_referans, 111 cati): SAM alani / insan cizimi alani, cati bazinda bootstrap (10.000).
Cikti: veri/elle/test_referans/alan_guven_araligi.csv"""
import os
import numpy as np, pandas as pd

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi', 'insan_referans', 'liste.csv')
CIK = os.path.join(KOK, 'veri', 'elle', 'test_referans')
B = 10000

t = pd.read_csv(os.path.join(CIK, 'iou_sonuc.csv')).merge(pd.read_csv(REF)[['dosya', 'yer_m_px']], on='dosya')
t = t[t.set.str.startswith('1_test_referans')]
t['ins'], t['sam'] = t.insan_px * t.yer_m_px ** 2, t.sam_px * t.yer_m_px ** 2
t['temiz'] = t.set.eq('1_test_referans')
rng = np.random.default_rng(0)
satir = []
for ad, g in [('hepsi', t), ('ayak_izi_dogru', t[t.temiz])]:
    s, h = g.sam.values, g.ins.values
    i = rng.integers(0, len(g), (B, len(g)))
    oran = s[i].sum(1) / h[i].sum(1)
    satir.append(dict(grup=ad, n=len(g), sam_insan_orani=s.sum() / h.sum(),
                      ci_alt=np.percentile(oran, 2.5), ci_ust=np.percentile(oran, 97.5)))
d = pd.DataFrame(satir)
d['eksik_yuzde'] = 100 * (1 - d.sam_insan_orani)
d['eksik_ci'] = [f'%{100 * (1 - u):.1f} - %{100 * (1 - a):.1f}' for a, u in zip(d.ci_alt, d.ci_ust)]
d.round(4).to_csv(os.path.join(CIK, 'alan_guven_araligi.csv'), index=False, encoding='utf-8-sig')
print(d.round(4).to_string(index=False))
