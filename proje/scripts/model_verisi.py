# -*- coding: utf-8 -*-
"""Modelde kullanilacak ANA veri setlerini tek klasorde toplar: Desktop/CatiGunes_Model_Verisi (2026-10-15).
Kaynak dosyalara dokunmaz; yalniz kopyalar / bicim donusturur. Yeniden calistirinca klasoru bastan kurar.
  catilar.gpkg            katman 'catilar' (OSB + kamu tek tablo, HIZALANMIS geometri) + 'sinirlar'
  catilar.csv             ayni tablo geometrisiz (Excel/pandas icin)
  uretim/                 PVGIS: saatlik 1 kWp uretim (csv), yillik/aylik ozet (csv)
  tarife/                 EPDK tarife tablosu
  firmalar/               IAOSB firma listesi (NACE)
  dogrulama/              Izmir BB GES'leri (kWh/kWp dogrulamasi)
  cati_kesitleri/         SAM girdisi: cati basina goruntu + indeks.csv
  BENIOKU.md"""
import json, os, shutil
import numpy as np, pandas as pd, geopandas as gpd
from shapely import affinity

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = lambda *p: os.path.join(KOK, 'veri', *p)
H = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi')
import time
for _ in range(10):   # Windows (Gezgin/indeksleyici) bos klasoru kisa sure kilitleyebiliyor -> tekrar dene
    if not os.path.exists(H): break
    shutil.rmtree(H, ignore_errors=True); time.sleep(1)
for d in ('uretim', 'tarife', 'firmalar', 'dogrulama'): os.makedirs(os.path.join(H, d), exist_ok=True)
if os.path.exists(os.path.join(H, 'cati_kesitleri')): shutil.rmtree(os.path.join(H, 'cati_kesitleri'), ignore_errors=True)

# ---- 1) catilar: tek tablo, hizalanmis geometri
idx = pd.read_csv(V('islenmis', 'cati_kesitleri', 'indeks.csv'))
osb = gpd.read_file(V('islenmis', 'osb_catilari.geojson'))
kamu = gpd.read_file(V('islenmis', 'kamu_catilari.geojson'))
# OSB icindeki sanayi disi binalar (anaokulu, poliklinik, itfaiye, banka, cami...) ayri tur: tuketim profili farkli
osb = osb.assign(bolge='ataturk_osb', tur=osb.sektor_notu.fillna('').str.startswith('sanayi disi').map({True: 'sanayi_disi', False: 'sanayi'}),
                 kurum_ad=None,
                 not_=osb.sektor_notu.fillna('') + osb.dogrulama.fillna(''))
kamu = kamu.assign(bolge='cigli_kamu', not_=kamu.islev_notu, dogrulama=None)
# 2026-10-17: universite catilari sona -> onceki 1.456 catinin cati_id'si degismez (SAM sonuclari cati_id ile bagli)
kamu = pd.concat([kamu[kamu.tur != 'universite'], kamu[kamu.tur == 'universite']], ignore_index=True)
SUT = ['osm', 'bolge', 'tur', 'kurum_ad', 'alan_m2', 'ayak_izi_kaynagi', 'ms_iou', 'mevcut_ges', 'gorsel_kontrol', 'ayak_izi_duzeltme', 'dogrulama', 'not_', 'geometry']
cat = gpd.GeoDataFrame(pd.concat([osb[SUT], kamu[SUT]], ignore_index=True), crs=4326).rename(columns={'not_': 'not'})
cat['not'] = cat['not'].replace('', None)
cat.loc[cat.ayak_izi_kaynagi == 'Microsoft', 'ms_iou'] = 1.0   # Microsoft'tan alinan cati kendisiyle birebir
k = idx.set_index('osm')
cat['kesit'] = cat.osm.map(k.kesit)
cat['dogu_m'] = cat.osm.map(k.blok_kayma_dogu_m + k.ince_dogu_m)
cat['kuzey_m'] = cat.osm.map(k.blok_kayma_kuzey_m + k.ince_kuzey_m)
cat.loc[cat.ayak_izi_duzeltme.notna(), ['dogu_m', 'kuzey_m']] = 0.0   # elle duzeltilen poligon zaten goruntu cercevesinde
u = cat.to_crs(32635)
u['geometry'] = [affinity.translate(g, dx, dy) for g, dx, dy in zip(u.geometry, u.dogu_m.fillna(0), u.kuzey_m.fillna(0))]
cat['geometry'] = u.to_crs(4326).geometry.values
m = u.geometry.centroid.to_crs(4326)   # merkez metrik sistemde hesaplanir
cat['lon'] = m.x.round(6).values; cat['lat'] = m.y.round(6).values
# 2026-10-17: cati_id KALICI (SAM veri seti / Colab sonuclari cati_id ile bagli) -> veri/elle/cati_id_kayit.csv.
# Kayittaki cati eski numarasini korur; cikarilan catinin numarasi bos kalir; yeni cati max+1 alir ve kayda eklenir.
KAYIT = V('elle', 'cati_id_kayit.csv')
kayit = pd.read_csv(KAYIT) if os.path.exists(KAYIT) else pd.DataFrame(columns=['osm', 'cati_id'])
yeni = [o for o in cat.osm if o not in set(kayit.osm)]
if yeni:
    bas = int(kayit.cati_id.max()) + 1 if len(kayit) else 1
    kayit = pd.concat([kayit, pd.DataFrame({'osm': yeni, 'cati_id': range(bas, bas + len(yeni))})], ignore_index=True)
    kayit.to_csv(KAYIT, index=False)
cat.insert(0, 'cati_id', cat.osm.map(kayit.set_index('osm').cati_id).astype(int))
cat = cat.sort_values('cati_id').reset_index(drop=True)
# 2026-10-18 (ekip karari): taban alani < 200 m2 cati GES analizine girmez (kulube, kantin, trafo, buyuk catinin OSM parcasi).
# Esik degistirilebilir; cati_id kalici kayittan geldigi icin SAM baglantisi bozulmaz.
MIN_GES_ALAN = 200
cat.insert(cat.columns.get_loc('alan_m2') + 1, 'kapsam',
           np.where(cat.alan_m2 >= MIN_GES_ALAN, 'ana', 'kucuk_%d_alti' % MIN_GES_ALAN))
# 2026-10-18 (kullanici): kucuk catilar hic ise yaramayacak -> tablodan CIKARILIR (cati_id kayitta kalir, numaralari bos kalir)
KUCUK_SAYI = int((cat.kapsam != 'ana').sum())
cat = cat[cat.kapsam == 'ana'].reset_index(drop=True)
cat = cat.drop(columns=['dogu_m', 'kuzey_m'])
gp = os.path.join(H, 'catilar.gpkg')
cat.to_file(gp, layer='catilar', driver='GPKG')
gpd.read_file(V('ham', 'sinir', 'sinirlar.geojson')).to_file(gp, layer='sinirlar', driver='GPKG')
cat.drop(columns='geometry').to_csv(os.path.join(H, 'catilar.csv'), index=False, encoding='utf-8-sig')

# ---- 2) uretim (PVGIS) -> csv
P = V('ham', 'pvgis')
yillik, aylik = [], []
for b in ('ataturk_osb', 'cigli'):
    h = pd.DataFrame(json.load(open(os.path.join(P, b + '_saatlik_egim10_guney.json')))['outputs']['hourly'])
    h['zaman_utc'] = pd.to_datetime(h.time, format='%Y%m%d:%H%M')
    h[['zaman_utc', 'P', 'Gb(i)', 'Gd(i)', 'Gr(i)', 'T2m', 'WS10m']].rename(columns={'P': 'uretim_W_per_kWp'}) \
        .to_csv(os.path.join(H, 'uretim', '%s_saatlik_1kWp_egim10_guney.csv' % b), index=False)
    for senaryo, f in (('egim10_guney', '_pv_egim10_guney'), ('egim15_guney', '_pv_egim15_guney'),
                       ('egim10_guney_cati', '_pv_egim10_guney_cati'),
                       ('optimum', '_pv_optimum'), ('dogu_10', '_pv_dogu_bati_10'), ('bati_10', '_pv_bati_10')):
        j = json.load(open(os.path.join(P, b + f + '.json')))
        t = j['outputs']['totals']; t = t.get('fixed', t)
        yillik.append({'bolge': b, 'senaryo': senaryo, 'E_y_kWh_per_kWp': t.get('E_y'), 'H_y_kWh_m2': t.get('H(i)_y'),
                       'kayip_toplam_%': t.get('l_total')})
        for m in (j['outputs']['monthly'].get('fixed', j['outputs']['monthly'])):
            aylik.append({'bolge': b, 'senaryo': senaryo, 'ay': m['month'], 'E_m_kWh_per_kWp': m.get('E_m')})
# dogu-bati sistem = dogu ve bati yuzeyin ortalamasi
yillik, aylik = pd.DataFrame(yillik), pd.DataFrame(aylik)
yillik = pd.concat([yillik, yillik[yillik.senaryo.isin(['dogu_10', 'bati_10'])].groupby('bolge', as_index=False)
                    .mean(numeric_only=True).assign(senaryo='dogu_bati_10')]).round(2)
aylik = pd.concat([aylik, aylik[aylik.senaryo.isin(['dogu_10', 'bati_10'])].groupby(['bolge', 'ay'], as_index=False)
                   .mean(numeric_only=True).assign(senaryo='dogu_bati_10')]).round(2)
yillik.to_csv(os.path.join(H, 'uretim', 'yillik_ozet.csv'), index=False)
aylik.to_csv(os.path.join(H, 'uretim', 'aylik_uretim.csv'), index=False)

# ---- 3) diger tablolar
shutil.copy2(V('ham', 'tarife', 'epdk_tarife_2026-04-04.xlsx'), os.path.join(H, 'tarife'))
# EPDK tablosu birlesik hucreli -> duz tablo (kr/kWh; guc bedeli kr/kW/ay). Saat dilimleri TSI (PVGIS UTC!)
t = pd.read_excel(V('ham', 'tarife', 'epdk_tarife_2026-04-04.xlsx'), header=None).iloc[4:29, 1:11]
t.columns = ['sistem', 'terim', 'kullanici', 'tek_zamanli', 'gunduz', 'puant', 'gece', 'dagitim', 'guc_kr_kw_ay', 'reaktif_kr_kvarh']
t.loc[t.index[0], ['sistem', 'terim']] = ['Iletim', 'Iletim']
t[['sistem', 'terim']] = t[['sistem', 'terim']].ffill()
t = t[t.kullanici.notna()]
for c in ('sistem', 'terim', 'kullanici'): t[c] = t[c].str.strip()
t['tek_zamanli_toplam'] = (t.tek_zamanli + t.dagitim).round(4)
t.to_csv(os.path.join(H, 'tarife', 'tarife_2026-04-04_duz.csv'), index=False, encoding='utf-8-sig')
shutil.copy2(V('ham', 'iaosb', 'iaosb_firmalar.csv'), os.path.join(H, 'firmalar'))
# firma -> cati eslemesi scripts/firma_cati_eslesme.py ile ayrica uretilir (Google'a gider, zincirde degil)
if os.path.exists(V('ham', 'iaosb', 'firma_cati_eslesme.csv')):
    shutil.copy2(V('ham', 'iaosb', 'firma_cati_eslesme.csv'), os.path.join(H, 'firmalar'))
# IBB listesindeki uretimler BEKLENEN (proje) degerleri, OLCUM DEGIL; 14'u guc x 1600 planlama carpani; 5'i ihalede (henuz yok)
d = pd.read_csv(V('ham', 'dogrulama', 'dogrulama_ges.csv'), sep=';')
d['deger_turu'] = d.tur.map({'planlama_kabulu': 'planlama_carpani_1600', 'proje_bazli': 'beklenen_proje_degeri'})
d['faaliyette'] = ~d.aciklama.str.contains('İhale', case=False)
d.rename(columns={'ozgul': 'ozgul_kWh_per_kWp'}).drop(columns=['tur']).to_csv(
    os.path.join(H, 'dogrulama', 'dogrulama_ges.csv'), index=False, encoding='utf-8-sig')
shutil.copytree(V('islenmis', 'cati_kesitleri'), os.path.join(H, 'cati_kesitleri'), dirs_exist_ok=True)
# kesitler + indeks de yalniz tablodaki catilar
ki = pd.read_csv(os.path.join(H, 'cati_kesitleri', 'indeks.csv'))
for kes in ki.loc[~ki.osm.isin(cat.osm), 'kesit']:
    for uz in ('.jpg', '.jgw'):
        f = os.path.join(H, 'cati_kesitleri', kes[:-4] + uz)
        if os.path.exists(f): os.remove(f)
ki[ki.osm.isin(cat.osm)].to_csv(os.path.join(H, 'cati_kesitleri', 'indeks.csv'), index=False)

o = cat.groupby(['bolge', 'tur']).agg(cati=('cati_id', 'size'), alan_m2=('alan_m2', 'sum')).round(0)
yo = yillik
open(os.path.join(H, 'BENIOKU.md'), 'w', encoding='utf-8').write('''# Çatı GES — Model Verisi

Modelde kullanılacak **ana veri setleri, tek yerde**. Üretici: `CatiGunes/scripts/model_verisi.py` (kaynak veriye dokunmaz; yeniden çalıştırınca klasörü baştan kurar). İlk indirilen ham veri `CatiGunes/veri/ham/`, insan kararları `CatiGunes/veri/elle/`; bu klasörü ham veriden baştan kurmak için `python scripts/kur.py`.

| Dosya | Ne | Kullanım |
|---|---|---|
| `catilar.gpkg` (katman `catilar`) / `catilar.csv` | **Analize girecek çatılar, tek tablo** — {n} çatı | ana tablo |
| `cati_kesitleri/` | çatı başına uydu görüntüsü + `indeks.csv` (`kutu_px` = SAM kutu istemi) | segmentasyon |
| `uretim/` | PVGIS: `*_saatlik_1kWp_egim10_guney.csv` (2020–23 saatlik, W/kWp, UTC), `yillik_ozet.csv`, `aylik_uretim.csv`; `cati_uretim.csv` + `uretim_ozet.csv` (çatı başına üretim, `uretim_hesabi.py`; aşağıda) | üretim, öz tüketim, NPV |
| `ekonomi/` | `cati_npv.csv` + `npv_ozet.csv` + `npv_varsayimlar.csv` (çatı başına NPV, `npv_hesabi.py`; aşağıda) | sıralama, Monte Carlo |
| `tarife/tarife_2026-04-04_duz.csv` (+ orijinal xlsx) | EPDK tarifeleri, düz tablo (kr/kWh, vergi hariç; `tek_zamanli_toplam` = enerji + dağıtım). Saat dilimleri TSİ | NPV |
| `firmalar/iaosb_firmalar.csv` | 775 OSB firması (NACE, adres; `;` ayraçlı) | sektör → tüketim |
| `firmalar/firma_cati_eslesme.csv` | 764 firma → `cati_id` (eslesme: kesin_osm / geocode_* / sokak_aday / sokak_osmde_yok); koordinat yok | firma ↔ çatı |
| `dogrulama/dogrulama_ges.csv` | İzmir BB'nin 26 GES'i. **Değerler BEKLENEN üretim, ölçüm DEĞİL** (`deger_turu`; 14'ü güç×1600 çarpanı, 5'i ihalede `faaliyette=False`) | yalnız tutarlılık karşılaştırması |

## catilar sütunları
`cati_id` · `osm` (kaynak kimliği; `ms_…` = Microsoft) · `bolge` (ataturk_osb / cigli_kamu) · `tur` (sanayi / sanayi_disi / okul / hastane / universite (İzmir Kâtip Çelebi Üniv., 2026-10-17 eklendi); sanayi_disi = OSB içindeki anaokulu, poliklinik, itfaiye, banka, cami vb.) · `kurum_ad` (kamu) · `alan_m2` (taban alanı) · `kapsam` (hepsi **ana**: taban alanı < 200 m² çatılar — kulübe/kantin/trafo/büyük çatının parçası — 2026-10-18 ekip kararıyla tablodan çıkarıldı; `cati_id` numaraları kalıcı, çıkanların numarası boş) · `ayak_izi_kaynagi` (OSM / Microsoft) · `ms_iou` (Microsoft ile örtüşme, 0–1) · `mevcut_ges` (tam / kismi: çatıda zaten panel var — SAM alanından panel kısmı çıkarılmalı, tam ise potansiyel yok) · `gorsel_kontrol` (goruntu_kotu / agac_alti / sekil_uyumsuz) · `ayak_izi_duzeltme` (dolu = ayak izi görüntü üzerinde elle düzeltildi, `veri/elle/ayak_izi_duzeltme.csv`; alan yeni poligondan) · `dogrulama` (OSB: Microsoft'tan eklenen aday, görüntüden teyit) · `not` (sanayi dışı işlev vb.) · `kesit` (cati_kesitleri içindeki görüntü) · `lon`, `lat`

**Geometri hizalanmıştır** (uydu görüntüsüne oturtuldu; ham OSM 1–4 m kayıktı). Koordinat EPSG:4326; alan için EPSG:32635'e çevirin.

{ozet}

PVGIS yıllık üretim (kWh/kWp, 2005–2023 ort.; saatlik seri 2020–23). `*_cati` = panel çatıya yakın montaj (sıcak, ~%4 düşük), diğerleri açık saha montajı. `dogu_bati_10` = doğu ve batı yüzün ortalaması. Saatlik seri **UTC** (TSİ = UTC+3); tarife dilimleriyle eşlerken çevirin.
{yil}

## Bilinen eksikler
Ölçülmüş GES üretimi (doğrulama seti tahmin), GES maliyeti, MEB-Sağlık resmî listeleri yok (tüketim / sözleşme gücü 2026-10-21'de kapsamdan çıkarıldı). Görsel kontrol: Claude ön karar verdi (1.496 çatı, 2026-10-16), kararlı 196 çatı 2026-10-21'de insan teyidinden geçti (`CatiGunes/veri/elle/gorsel_kontrol.csv`). Doğruluk denetimi: `DOGRULAMA_RAPORU.md`.
'''.format(n=len(cat), ozet=o.to_markdown(), yil=yo.pivot(index='bolge', columns='senaryo', values='E_y_kWh_per_kWp').to_markdown()))

boyut = sum(os.path.getsize(os.path.join(a, f)) for a, _, fs in os.walk(H) for f in fs) / 1e6
print(o.to_string()); print(yo.to_string()); print('->', H, '%.0f MB' % boyut)
