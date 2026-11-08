# -*- coding: utf-8 -*-
"""Kamu binalarini (okul, hastane, universite) Model_Verisi'nden ayri klasore ayirir (2026-10-17).
Kaynak: Desktop/CatiGunes_Model_Verisi (dokunulmaz) -> Desktop/CatiGunes_Kamu_Binalari (her calismada bastan kurulur).
  python scripts/kamu_klasoru.py"""
import os, shutil
import pandas as pd
import geopandas as gpd

MASA = os.path.join(os.path.expanduser('~'), 'Desktop')
KAYNAK = os.path.join(MASA, 'CatiGunes_Model_Verisi')
HEDEF = os.path.join(MASA, 'CatiGunes_Kamu_Binalari')

shutil.rmtree(HEDEF, ignore_errors=True)  # Gezgin'de aciksa klasor kilitli kalir -> icini bosalt
os.makedirs(HEDEF, exist_ok=True)
for kok, _, dosyalar in os.walk(HEDEF):  # klasorleri birak, dosyalari sil (kilitli klasor silinemiyor)
    for d in dosyalar: os.remove(os.path.join(kok, d))

# 1) catilar -> yalniz kamu
g = gpd.read_file(os.path.join(KAYNAK, 'catilar.gpkg'), layer='catilar')
# 2026-10-18 (kullanici): yalniz analize giren catilar (taban alani >= 200 m2, kapsam == 'ana'); kucukler bu klasore girmez
k = g[(g['bolge'] == 'cigli_kamu') & (g['kapsam'] == 'ana')].copy()
kucuk = int(((g['bolge'] == 'cigli_kamu') & (g['kapsam'] != 'ana')).sum())
k.to_file(os.path.join(HEDEF, 'kamu_catilari.gpkg'), layer='kamu_catilari', driver='GPKG')
t = pd.DataFrame(k.drop(columns='geometry'))
t.to_csv(os.path.join(HEDEF, 'kamu_catilari.csv'), index=False, encoding='utf-8-sig')

# 2) kurum ozeti
oz = (t.groupby(['tur', 'kurum_ad'], dropna=False)
        .agg(cati=('cati_id', 'count'), alan_m2=('alan_m2', 'sum'),
             mevcut_ges=('mevcut_ges', lambda s: s.notna().sum()),
             gorsel_sorun=('gorsel_kontrol', lambda s: s.notna().sum()))
        .reset_index().sort_values(['tur', 'alan_m2'], ascending=[True, False]))
oz['alan_m2'] = oz['alan_m2'].round(0)
oz.to_csv(os.path.join(HEDEF, 'kurum_ozeti.csv'), index=False, encoding='utf-8-sig')

# 3) cati kesitleri (kamu goruntuleri + filtreli indeks)
ks = os.path.join(HEDEF, 'cati_kesitleri')
os.makedirs(os.path.join(ks, 'kamu'), exist_ok=True)
for kes in t['kesit'].dropna():   # yalniz klasordeki catilarin goruntusu (.jpg + .jgw)
    for uz in ('.jpg', '.jgw'):
        shutil.copy(os.path.join(KAYNAK, 'cati_kesitleri', kes[:-4] + uz), os.path.join(ks, 'kamu'))
ind = pd.read_csv(os.path.join(KAYNAK, 'cati_kesitleri', 'indeks.csv'))
ind = ind[ind['osm'].isin(t['osm'])]
ind.to_csv(os.path.join(ks, 'indeks.csv'), index=False, encoding='utf-8-sig')
kb = pd.read_csv(os.path.join(KAYNAK, 'cati_kesitleri', 'kayma_bloklari.csv'))
kb.to_csv(os.path.join(ks, 'kayma_bloklari.csv'), index=False, encoding='utf-8-sig')

# 4) uretim (yalniz Cigli)
u = os.path.join(HEDEF, 'uretim'); os.makedirs(u, exist_ok=True)
shutil.copy(os.path.join(KAYNAK, 'uretim', 'cigli_saatlik_1kWp_egim10_guney.csv'), u)
for f in ('yillik_ozet.csv', 'aylik_uretim.csv'):
    d = pd.read_csv(os.path.join(KAYNAK, 'uretim', f))
    d[d['bolge'] == 'cigli'].to_csv(os.path.join(u, f), index=False, encoding='utf-8-sig')
# 2026-11-07: cati basina uretim (scripts/uretim_hesabi.py) -> yalniz kamu satirlari
cu = pd.read_csv(os.path.join(KAYNAK, 'uretim', 'cati_uretim.csv'))
cu[cu['bolge'] == 'cigli_kamu'].to_csv(os.path.join(u, 'cati_uretim.csv'), index=False, encoding='utf-8-sig')
# 2026-11-07: cati basina NPV (scripts/npv_hesabi.py) -> kamu satirlari + varsayimlar
ek = os.path.join(HEDEF, 'ekonomi'); os.makedirs(ek, exist_ok=True)
cn = pd.read_csv(os.path.join(KAYNAK, 'ekonomi', 'cati_npv.csv'))
cn[cn['bolge'] == 'cigli_kamu'].to_csv(os.path.join(ek, 'cati_npv.csv'), index=False, encoding='utf-8-sig')
shutil.copy(os.path.join(KAYNAK, 'ekonomi', 'npv_varsayimlar.csv'), ek)

# 5) tarife (kamu / ozel hizmet satirlari)
ta = pd.read_csv(os.path.join(KAYNAK, 'tarife', 'tarife_2026-04-04_duz.csv'))
ta = ta[ta['kullanici'].astype(str).str.contains('Kamu', case=False)]
os.makedirs(os.path.join(HEDEF, 'tarife'), exist_ok=True)
ta.to_csv(os.path.join(HEDEF, 'tarife', 'tarife_kamu_2026-04-04.csv'), index=False, encoding='utf-8-sig')

# 6) incelenecek (kamu)
inc = pd.read_csv(os.path.join(KAYNAK, 'incelenecek_catilar.csv'))
inc = inc[inc['cati_id'].isin(t['cati_id'])]
inc.to_csv(os.path.join(HEDEF, 'incelenecek_kamu.csv'), index=False, encoding='utf-8-sig')

# 7) tek Excel (kolay bakis)
with pd.ExcelWriter(os.path.join(HEDEF, 'kamu_binalari.xlsx')) as w:
    oz.to_excel(w, sheet_name='Kurum_ozeti', index=False)
    t.to_excel(w, sheet_name='Kamu_catilari', index=False)
    inc.to_excel(w, sheet_name='Incelenecek', index=False)
    ta.to_excel(w, sheet_name='Tarife_kamu', index=False)

# 8) BENIOKU
sayim = t.groupby('tur').agg(cati=('cati_id', 'count'), kurum=('kurum_ad', 'nunique'),
                             alan_m2=('alan_m2', 'sum')).round(0)
with open(os.path.join(HEDEF, 'BENIOKU.md'), 'w', encoding='utf-8') as f:
    f.write(f"""# Çatı GES — Kamu Binaları (Çiğli)

`CatiGunes_Model_Verisi`'nden **yalnız kamu çatıları** (okul, hastane, İKÇÜ Balatçık kampüsü) ayrıldı. **Yalnız taban alanı ≥ 200 m² çatılar** (`kapsam == 'ana'`); {kucuk} küçük çatı (kantin, kulübe vb.) bu klasörde YOK — gerekirse Model_Verisi `catilar`'da duruyorlar.
Üretici: `CatiGunes/scripts/kamu_klasoru.py` — Model_Verisi değişince yeniden çalıştırın (klasörü baştan kurar).

| Dosya | Ne |
|---|---|
| `kamu_catilari.gpkg` / `.csv` | {len(t)} kamu çatısı, hizalı geometri (EPSG:4326). Sütunlar Model_Verisi `catilar` ile aynı |
| `kurum_ozeti.csv` | kurum başına çatı sayısı, taban alanı, mevcut GES'li çatı, görsel sorunlu çatı |
| `kamu_binalari.xlsx` | kurum özeti + çatılar + incelenecekler + kamu tarifesi tek dosyada |
| `cati_kesitleri/kamu/` | çatı başına uydu görüntüsü (.jpg + .jgw, EPSG:3857); `indeks.csv` (`kutu_px` = SAM kutu istemi) |
| `uretim/` | PVGIS Çiğli: saatlik 1 kWp seri (2020–23, UTC), yıllık + aylık özet; `cati_uretim.csv` = çatı başına kWp + yıllık kWh (alt/merkez/üst; Model_Verisi BENIOKU'ya bakın) |
| `ekonomi/` | `cati_npv.csv` (kamu çatıları NPV/IRR/geri ödeme; sıralar tüm 1.085 çatı içinde) + `npv_varsayimlar.csv` |
| `tarife/tarife_kamu_2026-04-04.csv` | EPDK kamu/özel hizmet satırları (kr/kWh, vergi hariç) |
| `incelenecek_kamu.csv` | doğrulama betiğinin işaretlediği kamu çatıları |

## Sayılar
{sayim.to_markdown()}

## Dikkat
- İKÇÜ (universite) 2026-10-17 eklendi; hocanın 15.10 kararı "yalnız okul + hastane" ile çelişiyor — netleşmeli. Bu 39 çatı görsel kontrolden geçmedi; en büyüğü (42.733 m²) muhtemelen birleşik bloklar.
- Görsel kontrolü Claude yaptı; bir kişi teyit etmeli.
""")
print('tamam ->', HEDEF, '|', len(t), 'cati')
