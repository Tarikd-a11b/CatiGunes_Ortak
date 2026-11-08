# -*- coding: utf-8 -*-
"""Cati basina yillik GES uretim potansiyeli (2026-11-07). Temel: ekip arkadasinin tahmin_modeli.ipynb'i
(kenar boslugu -> engel payi -> sira golgesi GCR -> kWp -> kWh, alt/ust bant), guncel veriye uyarlandi:
  - alan: catilar.gpkg katman 'uygun_alan' (son cati geometrisi; mevcut GES dusulmus) -- maske/SAM alani DEGIL
  - kenar boslugu: poligonu iceri tamponlama (defterdeki distance_transform >= kenar ile ayni is)
  - ozgul uretim: PVGIS 5.3 PVcalc (SARAH3 2005-2023, kayip %14, sicaklik dahil), bolge kendi noktasiyla
  - capraz kontrol: defterin kendi isinim motoru (izotropik POA + sicaklik + PR) ayni PVGIS TMY ile
Cikti: Desktop/CatiGunes_Model_Verisi/uretim/cati_uretim.csv (+ uretim_ozet.csv). Sentetik veri yolu YOK:
ham PVGIS dosyasi eksikse durur (python scripts/uygulama_veri_indir.py pvgis).
  python scripts/uretim_hesabi.py"""
import json, os, sys
import numpy as np, pandas as pd, geopandas as gpd

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(KOK, 'veri', 'ham', 'pvgis')
H = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi')

# ---- varsayimlar (defterle ayni; kaynak/ekip karari raporda yazilmali)
PANEL_VERIM = 0.20             # kWp/m2 = 0,20 (200 W/m2 modul)
PANEL_BOY_M = 1.7              # egim yonundeki modul boyu (sira araligi)
KENAR_M = {'okul': 1.2, 'hastane': 1.2, 'universite': 1.2}   # kamu; digerleri (sanayi, sanayi_disi) 2,0 m
KENAR_VARSAYILAN_M = 2.0
EGIMLER = (10, 15)             # duz cati, guneye egik sehpa
ENGEL_PAYI = (0.70, 0.80)      # kullanilabilir oran (Ni vd. 2024 ~0,80; ekip karari)
GOLGE_SAATI = 10.0             # 21 Aralik, sira golgesinin dusmedigi en erken gunes saati
PR = 0.80                      # yalniz capraz kontrol motoru
SICAKLIK_KATSAYI, HUCRE_ISINMA, ALBEDO = -0.004, 0.03, 0.20
BOLGE_PVGIS = {'ataturk_osb': 'ataturk_osb', 'cigli_kamu': 'cigli'}


def oku(ad):
    f = os.path.join(P, ad + '.json')
    if not os.path.exists(f):
        sys.exit('HATA: %s yok -> python scripts/uygulama_veri_indir.py pvgis' % f)
    return json.load(open(f, encoding='utf-8'))


def gcr(beta, lat):
    """21 Aralik GOLGE_SAATI'nde sira golgesi dusmeyen aralikla yatay kaplama orani L cosB / D (defter)."""
    d, phi, w = np.radians(-23.45), np.radians(lat), np.radians(15 * (GOLGE_SAATI - 12))
    sin_alt = np.sin(phi) * np.sin(d) + np.cos(phi) * np.cos(d) * np.cos(w)
    alt = np.arcsin(sin_alt)
    az = np.arccos(np.clip((sin_alt * np.sin(phi) - np.sin(d)) / (np.cos(alt) * np.cos(phi)), -1, 1))
    b = np.radians(beta)
    D = PANEL_BOY_M * np.cos(b) + max(PANEL_BOY_M * np.sin(b) / np.tan(alt) * np.cos(az), 0)
    return float(PANEL_BOY_M * np.cos(b) / D)


def defter_ozgul(tmy, lat, lon, beta):
    """Defterin isinim motoru (Duffie-Beckman, izotropik + albedo, sicaklik, PR) -> kWh/kWp/yil."""
    t = pd.DataFrame(tmy['outputs']['tmy_hourly'])
    idx = pd.to_datetime(t['time(UTC)'], format='%Y%m%d:%H%M')
    n = idx.dt.dayofyear.values
    B = np.radians(360 / 365 * (n - 81))
    eot = 9.87 * np.sin(2 * B) - 7.53 * np.cos(B) - 1.5 * np.sin(B)
    t_gunes = (idx.dt.hour.values + 0.5 + 3) % 24 + (4 * (lon - 45.0) + eot) / 60
    d = np.radians(23.45 * np.sin(np.radians(360 / 365 * (284 + n))))
    w, phi, b = np.radians(15 * (t_gunes - 12)), np.radians(lat), np.radians(beta)
    cz = np.sin(phi) * np.sin(d) + np.cos(phi) * np.cos(d) * np.cos(w)
    ct = np.maximum(0, np.sin(d) * np.sin(phi - b) + np.cos(d) * np.cos(phi - b) * np.cos(w))   # guneye bakan (gamma=0)
    g = t['Gb(n)'].values * ct + t['Gd(h)'].values * (1 + np.cos(b)) / 2 + ALBEDO * t['G(h)'].values * (1 - np.cos(b)) / 2
    g = np.where(cz > 0, g, 0.0)
    sic = 1 + SICAKLIK_KATSAYI * (t['T2m'].values + HUCRE_ISINMA * g - 25)
    return float((g * sic).sum() / 1000 * PR), float(g.sum() / 1000)


# ---- 1) bolge basina ozgul uretim (PVGIS) + defter motoru capraz kontrolu
ozgul, kontrol = {}, []
for bolge, ad in BOLGE_PVGIS.items():
    for beta in EGIMLER:
        j = oku('%s_pv_egim%d_guney' % (ad, beta))
        tot = j['outputs']['totals']['fixed']
        ozgul[(bolge, beta)] = tot['E_y']
        loc = j['inputs']['location']
        e_d, poa_d = defter_ozgul(oku(ad + '_tmy'), loc['latitude'], loc['longitude'], beta)
        kontrol.append(dict(bolge=bolge, egim=beta, pvgis_kWh_kWp=tot['E_y'], pvgis_yillar_arasi_sd=tot['SD_y'],
                            pvgis_poa_kWh_m2=tot['H(i)_y'], defter_kWh_kWp=round(e_d, 1), defter_poa_kWh_m2=round(poa_d, 1),
                            fark_yuzde=round((e_d / tot['E_y'] - 1) * 100, 1),
                            gcr=round(gcr(beta, loc['latitude']), 3), lat=loc['latitude']))
kontrol = pd.DataFrame(kontrol)

# ---- 2) cati basina alan zinciri
cat = pd.read_csv(os.path.join(H, 'master_veriseti.csv'))
uyg = gpd.read_file(os.path.join(H, 'catilar.gpkg'), layer='uygun_alan').to_crs(32635).set_index('cati_id')
lat_b = kontrol.groupby('bolge').lat.first()
satir = []
for r in cat.itertuples():
    kenar = KENAR_M.get(r.tur, KENAR_VARSAYILAN_M)
    geom = uyg.geometry.get(r.cati_id)
    net = 0.0 if geom is None or geom.is_empty else max(geom.buffer(-kenar, join_style='mitre').area, 0.0)
    sen = []   # (egim, engel, kWp, kWh)
    for beta in EGIMLER:
        g = gcr(beta, lat_b[r.bolge])
        for eng in ENGEL_PAYI:
            A = net * eng * g / np.cos(np.radians(beta))          # egik modul alani
            kwp = A * PANEL_VERIM
            sen.append((beta, eng, kwp, kwp * ozgul[(r.bolge, beta)]))
    a = np.array(sen)
    # merkez senaryo: 10 derece, engel 0,75 (alt/ust bandin ortasi; NPV ve Monte Carlo icin baz)
    gm = gcr(10, lat_b[r.bolge]); kwp_m = net * 0.75 * gm / np.cos(np.radians(10)) * PANEL_VERIM
    satir.append(dict(cati_id=r.cati_id, bolge=r.bolge, tur=r.tur, panel_durumu=r.panel_durumu,
                      geometri_kaynagi=r.geometri_kaynagi, supheli=r.supheli,
                      cati_alan_m2=r.cati_alan_m2, uygun_alan_m2=r.uygun_alan_m2, kenar_m=kenar, net_alan_m2=round(net, 1),
                      kwp_alt=round(a[:, 2].min(), 1), kwp_merkez=round(kwp_m, 1), kwp_ust=round(a[:, 2].max(), 1),
                      kwh_alt=round(a[:, 3].min()), kwh_merkez=round(kwp_m * ozgul[(r.bolge, 10)]),
                      kwh_ust=round(a[:, 3].max()), ozgul_kWh_kWp=ozgul[(r.bolge, 10)]))
d = pd.DataFrame(satir)

# ---- 3) tutarlilik: uygun alan 0 olan catida uretim 0; net <= uygun; bant sirali
assert len(d) == len(cat) == d.cati_id.nunique()
assert (d.net_alan_m2 <= d.uygun_alan_m2 + 0.5).all()
assert ((d.uygun_alan_m2 > 0) | (d.kwh_ust == 0)).all()
assert ((d.kwh_alt <= d.kwh_merkez) & (d.kwh_merkez <= d.kwh_ust)).all()

os.makedirs(os.path.join(H, 'uretim'), exist_ok=True)
d.to_csv(os.path.join(H, 'uretim', 'cati_uretim.csv'), index=False, encoding='utf-8-sig')
oz = d.groupby(['bolge', 'tur']).agg(cati=('cati_id', 'count'), uretim_yapan=('kwh_merkez', lambda s: (s > 0).sum()),
                                      uygun_alan_m2=('uygun_alan_m2', 'sum'), net_alan_m2=('net_alan_m2', 'sum'),
                                      kwp_alt=('kwp_alt', 'sum'), kwp_merkez=('kwp_merkez', 'sum'), kwp_ust=('kwp_ust', 'sum'),
                                      MWh_alt=('kwh_alt', 'sum'), MWh_merkez=('kwh_merkez', 'sum'), MWh_ust=('kwh_ust', 'sum'))
for c in ('MWh_alt', 'MWh_merkez', 'MWh_ust'): oz[c] = oz[c] / 1000
oz.loc[('TOPLAM', ''), :] = oz.sum()
oz = oz.round(0)
oz.to_csv(os.path.join(H, 'uretim', 'uretim_ozet.csv'), encoding='utf-8-sig')
kontrol.to_csv(os.path.join(H, 'uretim', 'ozgul_uretim_kontrol.csv'), index=False)
pd.set_option('display.width', 200)
print(kontrol.to_string(index=False)); print(); print(oz.to_string())

# ---- 4) BENIOKU bolumu (yeniden calistirinca eskisinin yerine yazilir)
BASLIK = '## Çatı başına üretim (`uretim/cati_uretim.csv`)'
t = oz.loc['TOPLAM'].iloc[0]
bolum = (BASLIK + '\n'
 'Üretici `scripts/uretim_hesabi.py` (temel: ekip arkadaşının `tahmin_modeli.ipynb`). Zincir: `uygun_alan` poligonu '
 '(mevcut GES düşülmüş) → kenar boşluğu kadar içeri tampon (kamu 1,2 m, sanayi 2,0 m) = `net_alan_m2` → × engel payı (0,70–0,80) '
 '× sıra gölgesi kaplama oranı (21 Aralık 10:00 gölgesiz; 10° → %%%.1f, 15° → %%%.1f) / cos(eğim) = modül alanı → × 0,20 kWp/m² = kWp '
 '→ × PVGIS özgül üretim (PVcalc, SARAH3 2005–2023, kayıp %%14, açık saha montaj, güney). Tüm çatılar **düz, güneye eğik sehpa** varsayımıyla '
 '(çatı tipi/yön verisi yok; doğu-batı yönlü eğimli çatıda özgül üretim ~%%8 düşük, `yillik_ozet.csv`).\n\n'
 'Sütunlar: `kwp_*`, `kwh_*` (yıllık) → `alt`/`ust` = {10°, 15°} × {0,70, 0,80} senaryolarının en küçüğü/büyüğü, '
 '`merkez` = 10° + engel 0,75 (NPV / Monte Carlo tabanı). `ozgul_kWh_kWp` = merkez senaryonun PVGIS değeri. '
 'Yıllar arası sapma (PVGIS SD_y) ve defterin kendi ışınım motoruyla çapraz kontrol: `ozgul_uretim_kontrol.csv` '
 '(defter PVGIS\'ten ~%%2 düşük).\n\n'
 'Toplam (%d çatı, %d üretim yapan): **%.0f MWp, %.0f GWh/yıl** merkez; bant %.0f–%.0f GWh/yıl. Ayrıntı `uretim_ozet.csv`.\n'
 % (gcr(10, lat_b.iloc[0]) * 100, gcr(15, lat_b.iloc[0]) * 100, t.cati, t.uretim_yapan, t.kwp_merkez / 1000,
    t.MWh_merkez / 1000, t.MWh_alt / 1000, t.MWh_ust / 1000))
bf = os.path.join(H, 'BENIOKU.md')
if os.path.exists(bf):
    s = open(bf, encoding='utf-8').read()
    if BASLIK in s:   # eski bolumu bir sonraki '## ' basligina kadar sil
        i = s.index(BASLIK); j = s.find('\n## ', i + len(BASLIK))
        s = s[:i] + (s[j + 1:] if j >= 0 else '')
    open(bf, 'w', encoding='utf-8').write(s.rstrip('\n') + '\n\n' + bolum)
