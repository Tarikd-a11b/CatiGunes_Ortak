# =====================================================================
# CATI SONUCLARI (uretim + NPV) — Colab hucresi (2026-11-07)
# Once Colab'in sol panelinden (Dosyalar) su iki dosyayi /content'e yukleyin:
#   Desktop\CatiGunes_Model_Verisi\ekonomi\cati_npv.csv
#   Desktop\CatiGunes_Model_Verisi\master_veriseti.csv
# Sonra bu hucreyi calistirin. Kaynak: scripts/uretim_hesabi.py + scripts/npv_hesabi.py
# =====================================================================
import pandas as pd, folium, branca.colormap as cm
from IPython.display import display

n = pd.read_csv('/content/cati_npv.csv')
m = pd.read_csv('/content/master_veriseti.csv')[['cati_id', 'kurum_ad', 'lon', 'lat', 'cati_alan_m2', 'uygun_alan_m2', 'geometri_kaynagi']]
d = n.merge(m, on='cati_id', how='left')

# 1) ozet
print('Uretim yapan cati:', d.npv_TL.notna().sum(), '/', len(d))
print('Toplam: %.1f MWp | %.0f GWh/yil | yatirim %.2f milyar TL | NPV %.2f milyar TL'
      % (d.kwp_merkez.sum() / 1e3, d.kwh_merkez.sum() / 1e6, d.yatirim_TL.sum() / 1e9, d.npv_TL.sum() / 1e9))

# 2) tablo: NPV'ye gore ilk 20 (siralamayi degistirmek icin 'sira_npv_kWp' ya da 'sira_uretim')
SIRALA = 'sira_npv'
gor = ['cati_id', 'tur', 'kurum_ad', 'uygun_alan_m2', 'kwp_merkez', 'kwh_merkez', 'yatirim_TL', 'npv_TL',
       'npv_TL_kWp', 'irr_reel', 'geri_odeme_yil', 'sira_npv', 'sira_npv_kWp', 'sira_uretim']
display(d.dropna(subset=['npv_TL']).sort_values(SIRALA)[gor].head(20).style.format(
    {'uygun_alan_m2': '{:,.0f}', 'kwp_merkez': '{:,.1f}', 'kwh_merkez': '{:,.0f}', 'yatirim_TL': '{:,.0f}',
     'npv_TL': '{:,.0f}', 'npv_TL_kWp': '{:,.0f}', 'irr_reel': '{:.1%}', 'geri_odeme_yil': '{:.0f}'}))

# 3) tek cati sorgusu: CATI = <cati_id>
CATI = None
if CATI is not None:
    display(d[d.cati_id == CATI].T)

# 4) harita: nokta boyutu ~ kWp, renk = NPV/kWp (TL); GES ile dolu catilar gri
v = d.dropna(subset=['lat'])
renk = cm.LinearColormap(['#d73027', '#fee08b', '#1a9850'], vmin=v.npv_TL_kWp.quantile(.05), vmax=v.npv_TL_kWp.quantile(.95),
                         caption='NPV / kWp (TL, reel)')
h = folium.Map(location=[v.lat.mean(), v.lon.mean()], zoom_start=14, tiles='Esri.WorldImagery')
# Kucuk noktalar tiklanabilsin: once gorunmez genis tiklama alanlari (en altta), sonra gercek noktalar
# buyukten kucuge (kucukler ustte). Noktaya basinca o cati acilir; genis alan yalniz bosluga basinca devreye girer.
TIKLAMA_PX = 12
v = v.assign(yaricap=(v.kwp_merkez ** .5 / 3).clip(5, 14).fillna(5)).sort_values('yaricap', ascending=False)

def bilgi(r):
    yok = pd.isna(r.npv_TL)
    return folium.Popup(('<b>c%04d</b> %s %s<br>' % (r.cati_id, r.tur, '' if pd.isna(r.kurum_ad) else r.kurum_ad)) +
                        ('mevcut GES / uygun alan yok' if yok else
                         'uygun alan %s m²<br>%.1f kWp · %s kWh/yıl<br>yatırım %s TL<br>NPV %s TL (%s TL/kWp)<br>IRR %%%.1f · geri ödeme %d yıl<br>sıra: NPV %d · üretim %d'
                         % (f'{r.uygun_alan_m2:,.0f}', r.kwp_merkez, f'{r.kwh_merkez:,.0f}', f'{r.yatirim_TL:,.0f}',
                            f'{r.npv_TL:,.0f}', f'{r.npv_TL_kWp:,.0f}', r.irr_reel * 100, r.geri_odeme_yil, r.sira_npv, r.sira_uretim)),
                        max_width=300)

for r in v.itertuples():
    folium.CircleMarker([r.lat, r.lon], radius=max(r.yaricap, TIKLAMA_PX), stroke=False, fill=True,
                        fill_color='#000', fill_opacity=0, popup=bilgi(r)).add_to(h)
for r in v.itertuples():
    folium.CircleMarker([r.lat, r.lon], radius=r.yaricap, color='#999' if pd.isna(r.npv_TL) else renk(r.npv_TL_kWp),
                        fill=True, fill_opacity=.85, weight=1, popup=bilgi(r)).add_to(h)
renk.add_to(h)
display(h)
