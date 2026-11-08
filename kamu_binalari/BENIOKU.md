# Çatı GES — Kamu Binaları (Çiğli)

`CatiGunes_Model_Verisi`'nden **yalnız kamu çatıları** (okul, hastane, İKÇÜ Balatçık kampüsü) ayrıldı. **Yalnız taban alanı ≥ 200 m² çatılar** (`kapsam == 'ana'`); 0 küçük çatı (kantin, kulübe vb.) bu klasörde YOK — gerekirse Model_Verisi `catilar`'da duruyorlar.
Üretici: `CatiGunes/scripts/kamu_klasoru.py` — Model_Verisi değişince yeniden çalıştırın (klasörü baştan kurar).

| Dosya | Ne |
|---|---|
| `kamu_catilari.gpkg` / `.csv` | 80 kamu çatısı, hizalı geometri (EPSG:4326). Sütunlar Model_Verisi `catilar` ile aynı |
| `kurum_ozeti.csv` | kurum başına çatı sayısı, taban alanı, mevcut GES'li çatı, görsel sorunlu çatı |
| `kamu_binalari.xlsx` | kurum özeti + çatılar + incelenecekler + kamu tarifesi tek dosyada |
| `cati_kesitleri/kamu/` | çatı başına uydu görüntüsü (.jpg + .jgw, EPSG:3857); `indeks.csv` (`kutu_px` = SAM kutu istemi) |
| `uretim/` | PVGIS Çiğli: saatlik 1 kWp seri (2020–23, UTC), yıllık + aylık özet; `cati_uretim.csv` = çatı başına kWp + yıllık kWh (alt/merkez/üst; Model_Verisi BENIOKU'ya bakın) |
| `ekonomi/` | `cati_npv.csv` (kamu çatıları NPV/IRR/geri ödeme; sıralar tüm 1.085 çatı içinde) + `npv_varsayimlar.csv` |
| `tarife/tarife_kamu_2026-04-04.csv` | EPDK kamu/özel hizmet satırları (kr/kWh, vergi hariç) |
| `incelenecek_kamu.csv` | doğrulama betiğinin işaretlediği kamu çatıları |

## Sayılar
| tur        |   cati |   kurum |   alan_m2 |
|:-----------|-------:|--------:|----------:|
| hastane    |      3 |       2 |     24972 |
| okul       |     48 |      35 |     38225 |
| universite |     29 |       1 |    108864 |

## Dikkat
- İKÇÜ (universite) 2026-10-17 eklendi; hocanın 15.10 kararı "yalnız okul + hastane" ile çelişiyor — netleşmeli. Bu 39 çatı görsel kontrolden geçmedi; en büyüğü (42.733 m²) muhtemelen birleşik bloklar.
- Görsel kontrolü Claude yaptı; bir kişi teyit etmeli.
