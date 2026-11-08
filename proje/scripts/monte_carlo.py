# -*- coding: utf-8 -*-
"""Monte Carlo + tornado + siralama kararliligi (2026-11-08). Girdi: ekonomi/cati_npv.csv + uretim/cati_uretim.csv.
Ortak girdiler (her turda tum catilara ayni): kur, birim maliyet, O&M, evirici, bozunma, omur, iskonto, fiyat artisi, tarife, ozgul uretim.
Cati basina girdiler (her cati ayri): engel payi, geometri kaynagina gore alan hatasi, montaj/yon, oz tuketim.
Uc kurgu: TAM (hepsi), OZ100 (oz tuketim 1), ORTAK (yalniz ortak girdiler; siralamanin yapay kararliligini gosterir).
Taban noktada npv_hesabi ile ayni sonucu verir (assert). Sabit tohum: ayni girdiyle ayni sonuc.
Cikti: Model_Verisi/ekonomi/mc_*.csv, mc_*.png
  python scripts/monte_carlo.py"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import npv_hesabi as NH

N, TOHUM = 10000, 20261108
H, E = NH.H, NH.E
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V, P0 = NH.V, NH.p
ENGEL = (0.70, 0.75, 0.85)   # Ni vd. 2024: engeller cati alaninin %14,9'u -> ust sinir ~0,85; taban ve alt: ekip defteri
YON = (0.92, 1.0, 1.0)       # dogu-bati 10 derece / guney 10 derece = 1.359/1.477 = 0,92; cati montaji 0,96 bu aralikta
OZ = (0.714, 1.0, 1.0)       # alt sinir: hafta sonu uretimi (%28,6) tamamen degersiz (saatlik PVGIS)
SD_OZGUL = 30.0 / 1477.0     # PVGIS SD_y / E_y; omur ortalamasinda SD/sqrt(T)
TAR = ('tarife_sanayi_kr', 'tarife_osb_diger_kr', 'tarife_kamu_kr')
CAP = ('capex_kucuk_USD', 'capex_orta_USD', 'capex_buyuk_USD')


def tri_inv(u, lo, m, hi):
    """Ucgen dagilim ters CDF; lo==m ya da m==hi de calisir."""
    u = np.asarray(u, float); fc = (m - lo) / (hi - lo)
    return np.where(u < fc, lo + np.sqrt(u * (hi - lo) * (m - lo)), hi - np.sqrt((1 - u) * (hi - lo) * (hi - m)))


def hesap(par, D, eng=0.75, alan=1.0, yon=1.0, oz=1.0, oz_f=1.0):
    """Cati basina (npv, yatirim). par: parametre sozlugu, D: cati dizileri."""
    kwp = D['kwp'] * eng / 0.75 * alan
    usd = np.where(kwp < NH.ESIK_KUCUK, par['capex_kucuk_USD'], np.where(kwp < NH.ESIK_BUYUK, par['capex_orta_USD'], par['capex_buyuk_USD']))
    c0 = kwp * usd * par['kur_TL_USD']
    tar = np.choose(D['g'], [par[k] for k in TAR])
    T = int(round(par['omur'])); r = par['iskonto_reel']; t = np.arange(1, T + 1)
    A = (((1 - par['bozunma']) * (1 + par['fiyat_artisi_reel'])) ** (t - 1) * (1 + r) ** -t).sum()
    B = ((1 + r) ** -t).sum()
    yuk = 1 + par['om_orani'] * B + par['evirici_orani'] * (1 + r) ** -int(round(par['evirici_yili']))
    return kwp * D['oz'] * oz_f * yon * oz * tar / 100 * A - c0 * yuk, c0


def cek(rng, cfg, D, Y):
    n = len(D['kwp'])
    u_c, u_t = rng.random(), rng.random()              # tum kademe/tarifeler ayni yonde
    par = {k: float(tri_inv(u_c, V[k][1], V[k][0], V[k][2])) if k in CAP else float(tri_inv(u_t, V[k][1], V[k][0], V[k][2])) if k in TAR
           else float(tri_inv(rng.random(), V[k][1], V[k][0], V[k][2])) for k in V}
    of = 1 + rng.normal(0, SD_OZGUL / np.sqrt(par['omur']))
    if cfg == 'ORTAK':
        return hesap(par, D, oz_f=of)
    eng = tri_inv(rng.random(n), *ENGEL)
    alan = np.ones(n)
    for ad, dizi in Y.items():
        m = D['kay'] == ad
        alan[m] = rng.choice(dizi, m.sum())
    yon = tri_inv(rng.random(n), *YON)
    oz = tri_inv(rng.random(n), *OZ) if cfg == 'TAM' else 1.0
    return hesap(par, D, eng, alan, yon, oz, of)


def main():
    u = pd.read_csv(os.path.join(H, 'uretim', 'cati_uretim.csv'))
    v = pd.read_csv(os.path.join(E, 'cati_npv.csv'))
    v = v[v.kwp_merkez > 0].merge(u[['cati_id', 'geometri_kaynagi', 'ozgul_kWh_kWp', 'kwp_merkez']].rename(columns={'kwp_merkez': 'k'}), on='cati_id')
    grup = v.tur.map({'sanayi': 0, 'sanayi_disi': 1}).fillna(2).astype(int).values
    D = dict(kwp=v.kwp_merkez.values, oz=(v.kwh_merkez / v.kwp_merkez).values, g=grup, kay=v.geometri_kaynagi.values)
    # taban dogrulama
    n0, c0 = hesap(P0, D)
    assert abs(n0.sum() / v.npv_TL.sum() - 1) < 1e-3, (n0.sum(), v.npv_TL.sum())

    # alan hatasi orneklemi (insan / kaynak), test setinden: gozlenen cati basina oranlar
    s = pd.read_csv(os.path.join(KOK, 'veri', 'elle', 'test_referans', 'iou_sonuc.csv'))
    t = s[(s.set == '1_test_referans') & (~s.supheli.astype(bool))]
    m = pd.read_csv(os.path.join(H, 'master_veriseti.csv'))
    ins = m[m.geometri_kaynagi == 'insan']
    Y = {'sam': np.clip((t.insan_px / t.sam_px).values, 0.5, 1.5),
         'ayak_izi': np.clip((ins.cati_alan_m2 / ins.alan_m2).values, 0.5, 1.5),
         'insan': np.array([1.0])}
    print('alan orani medyan/ort: sam %.3f/%.3f (n=%d), ayak_izi %.3f/%.3f (n=%d)' % (np.median(Y['sam']), Y['sam'].mean(), len(Y['sam']), np.median(Y['ayak_izi']), Y['ayak_izi'].mean(), len(Y['ayak_izi'])))

    ids = v.cati_id.values
    sanayi = np.where(grup == 0)[0]; kamu = np.where(grup == 2)[0]
    ortak_kume = {'hepsi': np.arange(len(v)), 'sanayi': sanayi, 'kamu': kamu}
    def ust(deger, kume, k):
        return kume[np.argsort(-deger[kume], kind='stable')[:k]]
    OLCUT = [('NPV', 'hepsi', 50), ('NPV', 'hepsi', 100), ('NPV', 'sanayi', 50), ('NPV', 'sanayi', 100), ('NPV', 'kamu', 20),
             ('NPV/yatirim', 'hepsi', 50), ('NPV/yatirim', 'sanayi', 50), ('NPV/yatirim', 'kamu', 20)]
    base_pi = n0 / c0
    taban = {o: set(ust(n0 if o[0] == 'NPV' else base_pi, ortak_kume[o[1]], o[2])) for o in OLCUT}
    rank = lambda x: pd.Series(x).rank(ascending=False).values
    gr_ad = v.tur.values
    ozet, kar, tum = [], [], {}
    for cfg in ('TAM', 'OZ100', 'ORTAK'):
        rng = np.random.default_rng(TOHUM)
        M = np.empty((N, len(v)), 'f8'); C = np.empty((N, len(v)), 'f8')
        for i in range(N):
            M[i], C[i] = cek(rng, cfg, D, Y)
        tot = M.sum(1)
        rec = dict(kurgu=cfg, toplam_p10=np.percentile(tot, 10) / 1e9, toplam_p50=np.percentile(tot, 50) / 1e9, toplam_p90=np.percentile(tot, 90) / 1e9,
                   toplam_ort=tot.mean() / 1e9, p_toplam_poz=(tot > 0).mean(), cati_p_poz_90=((M > 0).mean(0) >= .9).mean(), cati_p_poz_50=((M > 0).mean(0) >= .5).mean())
        for g, ad in ((grup == 0, 'sanayi'), (grup == 2, 'kamu')):
            x = M[:, g].sum(1) / 1e9
            rec.update({ad + '_p10': np.percentile(x, 10), ad + '_p50': np.percentile(x, 50), ad + '_p90': np.percentile(x, 90)})
        ozet.append(rec)
        sec = np.random.default_rng(1).choice(N, 1000, replace=False)
        for o in OLCUT:
            met, kume_ad, k = o; kume = ortak_kume[kume_ad]; ov = np.zeros(N); fr = np.zeros(len(v))
            for i in range(N):
                d = M[i] if met == 'NPV' else M[i] / C[i]
                tp = ust(d, kume, k); fr[tp] += 1; ov[i] = len(taban[o] & set(tp)) / k
            base = n0 if met == 'NPV' else base_pi
            sp = np.median([pd.Series(base[kume]).corr(pd.Series((M[i] if met == 'NPV' else M[i] / C[i])[kume]), method='spearman') for i in sec])
            fr /= N
            kar.append(dict(kurgu=cfg, olcut=met, kume=kume_ad, k=k, ort_ortusme=ov.mean(), p10_ortusme=np.percentile(ov, 10), spearman_medyan=sp,
                            cati_90_sik=int((fr >= .9).sum()), hic_girmeyen_disi=int((fr > 0).sum())))
            if cfg == 'TAM': tum[o] = fr
        if cfg == 'TAM': Mt = M
    ozet = pd.DataFrame(ozet); kar = pd.DataFrame(kar)
    # cati ciktisi
    c = v[['cati_id', 'bolge', 'tur', 'geometri_kaynagi', 'supheli', 'kwp_merkez', 'yatirim_TL', 'npv_TL']].copy()
    for q, ad in ((10, 'npv_p10'), (50, 'npv_p50'), (90, 'npv_p90')): c[ad] = np.percentile(Mt, q, axis=0).round(0)
    c['p_npv_poz'] = (Mt > 0).mean(0).round(4)
    c['ilk50_hepsi'] = tum[('NPV', 'hepsi', 50)].round(4); c['ilk100_hepsi'] = tum[('NPV', 'hepsi', 100)].round(4)
    c['ilk50_sanayi'] = np.where(grup == 0, tum[('NPV', 'sanayi', 50)], np.nan); c['ilk20_kamu'] = np.where(grup == 2, tum[('NPV', 'kamu', 20)], np.nan)
    c['ilk50_sanayi_getiri'] = np.where(grup == 0, tum[('NPV/yatirim', 'sanayi', 50)], np.nan)

    # tornado (taban tum digerleri sabit)
    B = n0.sum() / 1e9; tor = []
    def calis(ad, fa, fu, alt, ust_):
        tor.append(dict(girdi=ad, alt=alt, ust=ust_, npv_alt=fa / 1e9, npv_ust=fu / 1e9, aralik=abs(fu - fa) / 1e9))
    def sw(keys, ind):
        p = dict(P0)
        for k in keys: p[k] = V[k][ind]
        return hesap(p, D)[0].sum()
    AD = [('Elektrik fiyatı (tarife)', TAR), ('Birim yatırım maliyeti', CAP), ('Reel iskonto oranı', ('iskonto_reel',)), ('Reel fiyat artışı', ('fiyat_artisi_reel',)),
          ('Dolar kuru', ('kur_TL_USD',)), ('Sistem ömrü', ('omur',)), ('İşletme-bakım', ('om_orani',)), ('Evirici yenileme oranı', ('evirici_orani',)),
          ('Yıllık verim kaybı', ('bozunma',)), ('Evirici yenileme yılı', ('evirici_yili',))]
    for ad, ks in AD:
        calis(ad, sw(ks, 1), sw(ks, 2), V[ks[0]][1], V[ks[0]][2])
    calis('Öz tüketim oranı', hesap(P0, D, oz=OZ[0])[0].sum(), hesap(P0, D, oz=OZ[2])[0].sum(), OZ[0], OZ[2])
    calis('Engel payı', hesap(P0, D, eng=ENGEL[0])[0].sum(), hesap(P0, D, eng=ENGEL[2])[0].sum(), ENGEL[0], ENGEL[2])
    calis('Çatı yönü / montaj', hesap(P0, D, yon=YON[0])[0].sum(), hesap(P0, D, yon=YON[2])[0].sum(), YON[0], YON[2])
    tor = pd.DataFrame(tor).sort_values('aralik', ascending=False)

    # butce senaryosu (taban)
    d = pd.DataFrame(dict(id=ids, n=n0, c=c0, g=grup, kwp=D['kwp'], pi=n0 / c0))
    but = []
    def sec_(df, b):
        top = 0; idx = []
        for r in df.itertuples():
            if top + r.c <= b: top += r.c; idx.append(r.Index)
        return df.loc[idx]
    for b in (250e6, 500e6, 1000e6, 2000e6):
        for ad, q in (('NPV (mutlak)', d.sort_values('n', ascending=False)), ('NPV / yatirim', d.sort_values('pi', ascending=False)),
                      ('NPV / yatirim (yalniz sanayi)', d[d.g == 0].sort_values('pi', ascending=False))):
            x = sec_(q, b)
            but.append(dict(butce_milyon_TL=b / 1e6, siralama=ad, cati=len(x), yatirim_milyon_TL=x.c.sum() / 1e6, npv_milyon_TL=x.n.sum() / 1e6, MWp=x.kwp.sum() / 1000,
                            kamu_cati=int((x.g == 2).sum()), npv_yatirim=x.n.sum() / x.c.sum()))
    but = pd.DataFrame(but)
    # sira ozellikleri (taban)
    r = pd.DataFrame(dict(kume=['hepsi', 'sanayi', 'kamu']))
    sira = []
    for ad, m_ in ortak_kume.items():
        a, b_ = pd.Series(n0[m_]), pd.Series(v.kwh_merkez.values[m_]); c_ = pd.Series((n0 / c0)[m_])
        k = 50 if ad != 'kamu' else 20
        ort = len(set(np.argsort(-a.values)[:k]) & set(np.argsort(-b_.values)[:k]))
        ort2 = len(set(np.argsort(-c_.values)[:k]) & set(np.argsort(-b_.values)[:k]))
        sira.append(dict(kume=ad, k=k, spearman_npv_uretim=a.corr(b_, method='spearman'), spearman_getiri_uretim=c_.corr(b_, method='spearman'), ilk_k_ortak_npv=ort, ilk_k_ortak_getiri=ort2))
    sira = pd.DataFrame(sira)
    kamu_m = grup == 2; ikcu = (v.tur == 'universite').values
    ek = pd.DataFrame([dict(kalem='kamu_npv_milyon_TL', deger=n0[kamu_m].sum() / 1e6), dict(kalem='kamu_npv_ikcusuz_milyon_TL', deger=n0[kamu_m & ~ikcu].sum() / 1e6),
                       dict(kalem='kamu_gwh', deger=v.kwh_merkez.values[kamu_m].sum() / 1e6), dict(kalem='kamu_gwh_ikcusuz', deger=v.kwh_merkez.values[kamu_m & ~ikcu].sum() / 1e6)])
    girdi = pd.DataFrame([dict(parametre=k, taban=a, mc_alt=b_, mc_ust=c_, dagilim='ucgen, ortak', birim=e_, kaynak=f) for k, (a, b_, c_, e_, f) in V.items()] + [
        dict(parametre='engel_payi', taban=ENGEL[1], mc_alt=ENGEL[0], mc_ust=ENGEL[2], dagilim='ucgen, cati basina', birim='oran', kaynak='Ni vd. 2024 engel %14,9 -> 0,85 ust; defter 0,70-0,80'),
        dict(parametre='yon_montaj', taban=1, mc_alt=YON[0], mc_ust=1, dagilim='ucgen, cati basina', birim='carpan', kaynak='PVGIS dogu-bati/guney 0,92; cati montaj 0,96'),
        dict(parametre='oz_tuketim', taban=1, mc_alt=OZ[0], mc_ust=1, dagilim='ucgen, cati basina (TAM)', birim='oran', kaynak='Saatlik PVGIS: hafta sonu %28,6 (kotu sinir)'),
        dict(parametre='alan_hatasi', taban=1, mc_alt=np.nan, mc_ust=np.nan, dagilim='ampirik, cati basina', birim='carpan', kaynak='Test seti insan/SAM ve insan/ayak izi orani'),
        dict(parametre='ozgul_uretim', taban=1, mc_alt=np.nan, mc_ust=np.nan, dagilim='normal SD_y/sqrt(T), ortak', birim='carpan', kaynak='PVGIS SD_y ~30 kWh/kWp')])
    for ad, x in (('mc_ozet', ozet), ('mc_kararlilik', kar), ('mc_cati', c), ('mc_tornado', tor), ('mc_butce', but), ('mc_sira', sira), ('mc_ek', ek), ('mc_girdiler', girdi)):
        x.to_csv(os.path.join(E, ad + '.csv'), index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 240); pd.set_option('display.max_columns', 40)
    print('TABAN', round(B, 3)); print(ozet.round(3).T.to_string()); print(kar.round(3).to_string()); print(tor.round(3).to_string()); print(but.round(2).to_string()); print(sira.round(3).to_string()); print(ek.round(1).to_string())

    # grafikler
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    ALT, UST, MET, IK = '#2a78d6', '#e34948', '#0b0b0b', '#52514e'
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.edgecolor': '#c3c2b7', 'text.color': MET, 'axes.labelcolor': IK, 'xtick.color': IK, 'ytick.color': MET})
    t_ = tor.iloc[::-1]; fig, ax = plt.subplots(figsize=(6.6, 4.0), dpi=200)
    for i, r_ in enumerate(t_.itertuples()):
        ax.barh(i, r_.npv_alt - B, left=B, color=ALT, height=.62, edgecolor='#fcfcfb', linewidth=1)
        ax.barh(i, r_.npv_ust - B, left=B, color=UST, height=.62, edgecolor='#fcfcfb', linewidth=1)
    ax.set_yticks(range(len(t_))); ax.set_yticklabels(t_.girdi); ax.axvline(B, color=IK, lw=.8)
    ax.set_xlabel(('Toplam NPV (milyar TL)  ·  taban %.2f milyar TL' % B).replace('.', ',')); ax.grid(axis='x', color='#e6e5e0', lw=.6); ax.set_axisbelow(True)
    for s_ in ('top', 'right', 'left'): ax.spines[s_].set_visible(False)
    ax.tick_params(left=False)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=ALT, label='Girdi alt değerde'), Patch(color=UST, label='Girdi üst değerde')], loc='lower right', frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(E, 'mc_tornado.png'), facecolor='white'); plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.6, 2.9), dpi=200); x = Mt.sum(1) / 1e9
    ax.hist(x, bins=60, color=ALT, edgecolor='#fcfcfb', linewidth=.5); p = np.percentile(x, [10, 50, 90])
    for q, a in zip(p, ('P10', 'P50', 'P90')):
        ax.axvline(q, color=MET, lw=.8); ax.text(q, ax.get_ylim()[1] * 1.0, (' %s  %.2f' % (a, q)).replace('.', ','), ha='left', va='top', fontsize=8)
    ax.axvline(B, color=IK, lw=.8, ls='--'); ax.text(B, ax.get_ylim()[1] * .86, (' Taban %.2f' % B).replace('.', ','), ha='left', va='top', fontsize=8, color=IK)
    ax.set_xlabel('Toplam NPV (milyar TL)'); ax.set_ylabel('Simülasyon sayısı'); ax.grid(axis='y', color='#e6e5e0', lw=.6); ax.set_axisbelow(True)
    for s_ in ('top', 'right'): ax.spines[s_].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(E, 'mc_toplam_npv.png'), facecolor='white'); plt.close(fig)
    benioku()


def benioku():
    BASLIK = '## Belirsizlik: Monte Carlo (`ekonomi/mc_*.csv`)'
    bolum = (BASLIK + '\n'
             'Üretici `scripts/monte_carlo.py` (`npv_hesabi.py` ile aynı nakit akışı; taban değer doğrulanır). 10.000 tur, sabit tohum, üçgen dağılım. '
             'Ortak girdiler her turda tüm çatılar için aynı; engel payı, yön/montaj, öz tüketim ve geometri kaynağına bağlı alan hatası çatı başına ayrı çekilir. '
             'Üç kurgu: `TAM` (hepsi), `OZ100` (öz tüketim %100), `ORTAK` (yalnız ortak girdiler).\n\n'
             '- `mc_girdiler.csv`: aralıklar ve kaynakları\n'
             '- `mc_ozet.csv`: toplam, sanayi ve kamu NPV yüzdelikleri (milyar TL)\n'
             '- `mc_cati.csv`: çatı başına NPV yüzdelikleri ve P(NPV>0)\n'
             '- `mc_tornado.csv`, `mc_tornado.png`: tek girdi değişiminin toplam NPV etkisi\n'
             '- `mc_kararlilik.csv`: taban sıralamadaki ilk çatıların kalma oranı, Spearman\n'
             '- `mc_sira.csv`: NPV ve NPV/yatırım sırasının üretim sırasıyla ilişkisi\n'
             '- `mc_butce.csv`: bütçe kısıtında seçim karşılaştırması\n'
             '- `mc_ek.csv`: İKÇÜ dâhil/hariç kamu toplamları\n'
             '- `mc_toplam_npv.png`: toplam NPV dağılımı\n')
    bf = os.path.join(os.path.dirname(os.path.dirname(KOK)), 'CatiGunes_Model_Verisi', 'BENIOKU.md')
    if os.path.exists(bf):
        s = open(bf, encoding='utf-8').read()
        if BASLIK in s:
            i = s.index(BASLIK); j = s.find('\n## ', i + len(BASLIK))
            s = s[:i] + (s[j + 1:] if j >= 0 else '')
        open(bf, 'w', encoding='utf-8').write(s.rstrip('\n') + '\n\n' + bolum)


if __name__ == '__main__':
    main()
