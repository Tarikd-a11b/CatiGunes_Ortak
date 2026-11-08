# -*- coding: utf-8 -*-
"""Cati basina NPV / IRR / geri odeme / LCOE (2026-11-07). Ara rapor 4.7 formulu:
  NPV_i = -C0*P_i + sum_t [ E_i (1-d)^(t-1) c - O&M - (evirici yenileme, t=T_ev) ] / (1+r)^t
REEL hesap (sabit Nisan 2026 TL'si, reel iskonto, reel fiyat artisi 0): enflasyon/kur tahmini gerekmez.
Varsayimlar (kapsam kararlari 2026-10-21/11-04):
  - %100 oz tuketim: uretimin tamami abonenin kendi tukettigi enerjiyi ikame eder -> kacinilan bedel = enerji + dagitim
    (EPDK 4 Nisan 2026 tek zamanli toplam, vergiler/KDV haric; sanayi KDV'yi indirir, kamu icin KDV haric kiyas = muhafazakar degil, raporda not)
  - yasal kurulum siniri (soezlesme gucu) UYGULANMAZ: sozlesme gucu verisi yok (tuketim kapsamdan cikti)
  - abone grubu: OSB sanayi -> OG cift terim Sanayi; kamu + OSB sanayi_disi -> OG cift terim Kamu ve Ozel Hizmetler
Her parametrenin taban degeri, Monte Carlo icin alt/ust araligi ve kaynagi: ekonomi/npv_varsayimlar.csv.
Girdi: Model_Verisi/uretim/cati_uretim.csv (scripts/uretim_hesabi.py). Cikti: Model_Verisi/ekonomi/.
  python scripts/npv_hesabi.py"""
import os
import numpy as np, pandas as pd

H = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi')
E = os.path.join(H, 'ekonomi')

# ---- varsayimlar: (taban, MC alt, MC ust, birim, kaynak)
V = {
    'kur_TL_USD':        (50.07, 46.0, 56.0, 'TL/USD', 'TCMB gosterge doviz satis 06.11.2026; aralik: yil sonu PKA beklentisi 51,5 ve +/- oynaklik'),
    'capex_kucuk_USD':   (550, 450, 850, 'USD/kWp (<100 kWp)', 'TR kurulumcu 2026 fiyatlari: 100 kW anahtar teslim 50-55 bin USD; 100 kW+ sanayi 600-850 USD/kW'),
    'capex_orta_USD':    (500, 400, 750, 'USD/kWp (100-1000 kWp)', 'TR kurulumcu 2026 fiyatlari (400-850 USD/kWp; sandvic cati ~400)'),
    'capex_buyuk_USD':   (450, 380, 650, 'USD/kWp (>=1000 kWp)', 'TR kurulumcu 2026 C&I cati 400-450 USD/kWp (MW sinifi); IRENA 2024 dunya ort. 691 USD/kW'),
    'om_orani':          (0.015, 0.010, 0.020, 'yatirimin %/yil', 'literatur tipik %1-2 (varsayim)'),
    'evirici_orani':     (0.08, 0.05, 0.12, 'yatirimin %', 'evirici yenileme tek seferlik (varsayim)'),
    'evirici_yili':      (13, 10, 15, 'yil', 'evirici omru 10-15 yil (varsayim)'),
    'bozunma':           (0.005, 0.004, 0.008, '1/yil', 'kristal Si modul garantisi ~%0,4-0,55/yil (varsayim)'),
    'omur':              (25, 20, 30, 'yil', 'modul guc garantisi 25-30 yil'),
    'iskonto_reel':      (0.08, 0.05, 0.12, '1/yil reel', 'TR ulke riski yuksek; reel sermaye maliyeti varsayimi'),
    'fiyat_artisi_reel': (0.0, -0.02, 0.02, '1/yil reel', 'tarife enflasyonla ayni hizda artar (taban); aralik varsayim'),
    'tarife_sanayi_kr':  (398.0185, 340.0, 480.0, 'kr/kWh', 'EPDK 04.04.2026 OG cift terim Sanayi, tek zamanli enerji+dagitim, vergi haric'),
    'tarife_kamu_kr':    (493.0369, 420.0, 600.0, 'kr/kWh', 'EPDK 04.04.2026 OG cift terim Kamu ve Ozel Hizmetler, tek zamanli enerji+dagitim, vergi haric'),
}
p = {k: v[0] for k, v in V.items()}
ESIK_KUCUK, ESIK_BUYUK = 100.0, 1000.0   # kWp


def capex_usd(kwp, p):
    return np.where(kwp < ESIK_KUCUK, p['capex_kucuk_USD'], np.where(kwp < ESIK_BUYUK, p['capex_orta_USD'], p['capex_buyuk_USD']))


def nakit_akisi(kwp, kwh1, tarife_kr, p):
    """Cati x yil nakit akisi matrisi (yil 0 dahil), reel TL. kwp, kwh1, tarife_kr: dizi."""
    T = int(round(p['omur'])); t = np.arange(1, T + 1)
    c0 = kwp * capex_usd(kwp, p) * p['kur_TL_USD']                                   # TL
    gelir = (kwh1[:, None] * (1 - p['bozunma']) ** (t - 1) * (tarife_kr[:, None] / 100)
             * (1 + p['fiyat_artisi_reel']) ** (t - 1))
    gider = np.repeat((c0 * p['om_orani'])[:, None], T, axis=1)
    gider[:, int(round(p['evirici_yili'])) - 1] += c0 * p['evirici_orani']
    return np.hstack([-c0[:, None], gelir - gider]), c0


def npv(akis, r):
    return akis @ (1 + r) ** -np.arange(akis.shape[1])


def irr(akis):
    """Satir basina IRR (ikiye bolme). NPV(0)<=0 ise NaN."""
    lo, hi = np.full(len(akis), -0.99), np.full(len(akis), 3.0)
    ok = npv(akis, 0.0) > 0
    for _ in range(80):
        m = (lo + hi) / 2
        pos = np.array([npv(akis[i:i + 1], m[i])[0] for i in range(len(akis))]) > 0
        lo, hi = np.where(pos, m, lo), np.where(pos, hi, m)
    return np.where(ok, (lo + hi) / 2, np.nan)


if __name__ == '__main__':
    u = pd.read_csv(os.path.join(H, 'uretim', 'cati_uretim.csv'))
    d = u[['cati_id', 'bolge', 'tur', 'panel_durumu', 'supheli', 'kwp_merkez', 'kwh_alt', 'kwh_merkez', 'kwh_ust']].copy()
    d['abone_grubu'] = np.where(d.tur == 'sanayi', 'OG cift terim Sanayi', 'OG cift terim Kamu ve Ozel Hizmetler')
    d['tarife_kr_kWh'] = np.where(d.tur == 'sanayi', p['tarife_sanayi_kr'], p['tarife_kamu_kr'])
    v = d[d.kwp_merkez > 0].copy()            # uretim yapmayan (tam GES / net alan 0) catilar ekonomiye girmez
    kwp, tar = v.kwp_merkez.values, v.tarife_kr_kWh.values
    ak, c0 = nakit_akisi(kwp, v.kwh_merkez.values, tar, p)
    v['capex_USD_kWp'] = capex_usd(kwp, p)
    v['yatirim_TL'] = c0.round(0)
    v['ilk_yil_tasarruf_TL'] = (v.kwh_merkez * tar / 100).round(0)
    v['npv_TL'] = npv(ak, p['iskonto_reel']).round(0)
    # uretim bandinin NPV'ye etkisi (kWp sabit, yalniz enerji degisir: egim/engel belirsizligi)
    for b in ('alt', 'ust'):
        v['npv_TL_uretim_' + b] = npv(nakit_akisi(kwp, v['kwh_' + b].values, tar, p)[0], p['iskonto_reel']).round(0)
    v['npv_TL_kWp'] = (v.npv_TL / kwp).round(0)
    v['irr_reel'] = irr(ak).round(4)
    net = ak[:, 1:].cumsum(axis=1) + ak[:, [0]]                       # kumulatif
    v['geri_odeme_yil'] = np.where((net >= 0).any(axis=1), (net < 0).sum(axis=1) + 1, np.nan)
    # LCOE (reel): yatirim + iskontolu giderler / iskontolu uretim
    T = int(p['omur']); t = np.arange(1, T + 1); df = (1 + p['iskonto_reel']) ** -t
    gid = c0 + (-(ak[:, 1:] - (v.kwh_merkez.values[:, None] * (1 - p['bozunma']) ** (t - 1) * tar[:, None] / 100))) @ df
    v['lcoe_TL_kWh'] = (gid / ((v.kwh_merkez.values[:, None] * (1 - p['bozunma']) ** (t - 1)) @ df)).round(3)
    v['sira_npv'] = v.npv_TL.rank(ascending=False, method='min').astype(int)
    v['sira_npv_kWp'] = v.npv_TL_kWp.rank(ascending=False, method='min').astype(int)
    v['sira_uretim'] = v.kwh_merkez.rank(ascending=False, method='min').astype(int)
    d = d.merge(v.drop(columns=d.columns.drop('cati_id')), on='cati_id', how='left')

    assert (d.loc[d.kwp_merkez > 0, 'npv_TL_uretim_alt'] <= d.loc[d.kwp_merkez > 0, 'npv_TL']).all()
    assert d.loc[d.kwp_merkez > 0, 'npv_TL'].notna().all()

    os.makedirs(E, exist_ok=True)
    d.to_csv(os.path.join(E, 'cati_npv.csv'), index=False, encoding='utf-8-sig')
    pd.DataFrame([dict(parametre=k, taban=a, mc_alt=b, mc_ust=c, birim=e, kaynak=f) for k, (a, b, c, e, f) in V.items()]) \
        .to_csv(os.path.join(E, 'npv_varsayimlar.csv'), index=False, encoding='utf-8-sig')
    g = v.groupby(['bolge', 'tur'])
    oz = g.agg(cati=('cati_id', 'count'), MWp=('kwp_merkez', 'sum'), yatirim_milyon_TL=('yatirim_TL', 'sum'),
               ilk_yil_tasarruf_milyon_TL=('ilk_yil_tasarruf_TL', 'sum'), npv_milyon_TL=('npv_TL', 'sum'),
               npv_pozitif=('npv_TL', lambda s: (s > 0).sum()))
    oz['MWp'] /= 1000
    for c in ('yatirim_milyon_TL', 'ilk_yil_tasarruf_milyon_TL', 'npv_milyon_TL'): oz[c] /= 1e6
    oz['irr_medyan'] = g.irr_reel.median(); oz['geri_odeme_medyan'] = g.geri_odeme_yil.median()
    oz['lcoe_medyan_TL_kWh'] = g.lcoe_TL_kWh.median()
    tp = v.sum(numeric_only=True)
    oz.loc[('TOPLAM', ''), :] = [len(v), tp.kwp_merkez / 1000, tp.yatirim_TL / 1e6, tp.ilk_yil_tasarruf_TL / 1e6, tp.npv_TL / 1e6,
                                 (v.npv_TL > 0).sum(), v.irr_reel.median(), v.geri_odeme_yil.median(), v.lcoe_TL_kWh.median()]
    oz = oz.round(3)
    oz.to_csv(os.path.join(E, 'npv_ozet.csv'), encoding='utf-8-sig')
    rho = v[['sira_npv', 'sira_uretim']].corr(method='spearman').iloc[0, 1]   # scipy yok -> pandas rank
    rho_k = v[['sira_npv_kWp', 'sira_uretim']].corr(method='spearman').iloc[0, 1]
    ust50 = len(set(v.nsmallest(50, 'sira_npv').cati_id) & set(v.nsmallest(50, 'sira_uretim').cati_id))
    pd.set_option('display.width', 220)
    print(oz.to_string()); print()
    print('Spearman sira (NPV ~ uretim): %.3f | (NPV/kWp ~ uretim): %.3f | ilk 50 ortak: %d' % (rho, rho_k, ust50))

    # ---- BENIOKU bolumu
    BASLIK = '## Ekonomi: çatı başına NPV (`ekonomi/cati_npv.csv`)'
    t = oz.loc['TOPLAM'].iloc[0]
    bolum = (BASLIK + '\n'
             'Üretici `scripts/npv_hesabi.py` (girdi `uretim/cati_uretim.csv`, merkez senaryo). **Reel** hesap: sabit Nisan 2026 TL, '
             'reel iskonto %%%.0f, %d yıl, bozunma %%%.1f/yıl, O&M yatırımın %%%.1f/yıl, evirici yenileme %d. yıl (%%%d). '
             'Yatırım kademeli: <100 kWp %d, 100–1.000 kWp %d, ≥1.000 kWp %d USD/kWp × %.2f TL/USD (TCMB 06.11.2026). '
             '**%%100 öz tüketim** (kaçınılan bedel = EPDK enerji + dağıtım, vergi hariç: sanayi %.2f, kamu/OSB sanayi dışı %.2f kr/kWh); '
             'yasal kurulum sınırı uygulanmadı (sözleşme gücü verisi yok). Taban + Monte Carlo aralıkları + kaynaklar: `npv_varsayimlar.csv`.\n\n'
             'Sütunlar: `yatirim_TL`, `ilk_yil_tasarruf_TL`, `npv_TL` (+ `npv_TL_uretim_alt/ust` = üretim bandı), `npv_TL_kWp`, `irr_reel`, '
             '`geri_odeme_yil` (iskontosuz), `lcoe_TL_kWh`, `sira_npv` / `sira_npv_kWp` / `sira_uretim`. Üretim yapmayan çatılarda boş.\n\n'
             'Toplam (%d çatı): yatırım **%.0f milyon TL**, ilk yıl tasarruf %.0f milyon TL, **NPV %.0f milyon TL**; '
             'NPV > 0 olan %d çatı; medyan reel IRR %%%.1f, medyan geri ödeme %.0f yıl, medyan LCOE %.2f TL/kWh. '
             'Sıralama: Spearman (NPV ~ üretim) %.3f, ilk 50 ortak %d.\n'
             % (p['iskonto_reel'] * 100, p['omur'], p['bozunma'] * 100, p['om_orani'] * 100, p['evirici_yili'], p['evirici_orani'] * 100,
                p['capex_kucuk_USD'], p['capex_orta_USD'], p['capex_buyuk_USD'], p['kur_TL_USD'], p['tarife_sanayi_kr'], p['tarife_kamu_kr'],
                t.cati, t.yatirim_milyon_TL, t.ilk_yil_tasarruf_milyon_TL, t.npv_milyon_TL, t.npv_pozitif, t.irr_medyan * 100,
                t.geri_odeme_medyan, t.lcoe_medyan_TL_kWh, rho, ust50))
    bf = os.path.join(H, 'BENIOKU.md')
    if os.path.exists(bf):
        s = open(bf, encoding='utf-8').read()
        if BASLIK in s:
            i = s.index(BASLIK); j = s.find('\n## ', i + len(BASLIK))
            s = s[:i] + (s[j + 1:] if j >= 0 else '')
        open(bf, 'w', encoding='utf-8').write(s.rstrip('\n') + '\n\n' + bolum)
