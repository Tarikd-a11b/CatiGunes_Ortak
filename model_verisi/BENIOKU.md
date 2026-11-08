# Çatı GES — Model Verisi

Modelde kullanılacak **ana veri setleri, tek yerde**. Üretici: `CatiGunes/scripts/model_verisi.py` (kaynak veriye dokunmaz; yeniden çalıştırınca klasörü baştan kurar). İlk indirilen ham veri `CatiGunes/veri/ham/`, insan kararları `CatiGunes/veri/elle/`; bu klasörü ham veriden baştan kurmak için `python scripts/kur.py`.

| Dosya | Ne | Kullanım |
|---|---|---|
| `catilar.gpkg` (katman `catilar`) / `catilar.csv` | **Analize girecek çatılar, tek tablo** — 1085 çatı | ana tablo |
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

|                                |   cati |          alan_m2 |
|:-------------------------------|-------:|-----------------:|
| ('ataturk_osb', 'sanayi')      |    997 |      2.23045e+06 |
| ('ataturk_osb', 'sanayi_disi') |      8 |  12847           |
| ('cigli_kamu', 'hastane')      |      3 |  24972           |
| ('cigli_kamu', 'okul')         |     48 |  38225           |
| ('cigli_kamu', 'universite')   |     29 | 108864           |

PVGIS yıllık üretim (kWh/kWp, 2005–2023 ort.; saatlik seri 2020–23). `*_cati` = panel çatıya yakın montaj (sıcak, ~%4 düşük), diğerleri açık saha montajı. `dogu_bati_10` = doğu ve batı yüzün ortalaması. Saatlik seri **UTC** (TSİ = UTC+3); tarife dilimleriyle eşlerken çevirin.
| bolge       |   bati_10 |   dogu_10 |   dogu_bati_10 |   egim10_guney |   egim10_guney_cati |   egim15_guney |   optimum |
|:------------|----------:|----------:|---------------:|---------------:|--------------------:|---------------:|----------:|
| ataturk_osb |   1359.01 |   1359.82 |        1359.42 |        1477.09 |             1420.2  |        1515.96 |   1580.18 |
| cigli       |   1392.4  |   1390.32 |        1391.36 |        1514    |             1454.97 |        1554.75 |   1623.7  |

## Bilinen eksikler
Ölçülmüş GES üretimi (doğrulama seti tahmin), GES maliyeti, MEB-Sağlık resmî listeleri yok (tüketim / sözleşme gücü 2026-10-21'de kapsamdan çıkarıldı). Görsel kontrol: Claude ön karar verdi (1.496 çatı, 2026-10-16), kararlı 196 çatı 2026-10-21'de insan teyidinden geçti (`CatiGunes/veri/elle/gorsel_kontrol.csv`). Doğruluk denetimi: `DOGRULAMA_RAPORU.md`.

## Son çatı geometrisi (`catilar.gpkg` katman `cati_son`)
Her çatı için panele esas çatı poligonu; `geometry` (katman `catilar`) ayak izi olarak kalır. Öncelik: **insan** çizimi (LabelMe, `veri/elle/insan_cizimleri.geojson`) > **sam** (şüpheli değilse) > **ayak_izi**. Komşu çatının ayak izinin >%15'ini kaplayan insan çizimi kullanılmaz. Sütunlar: `geometri_kaynagi`, `cati_alan_m2` (UTM 35N), `geometri_notu` (ayakizi_eksik / ayakizi_hatali / bina_belirsiz / SAM şüpheli). Dağılım: ayak_izi 97, insan 160, sam 828.

**Panel düşülmüş alan** (katman `uygun_alan`, sütunlar `panel_durumu`, `uygun_alan_m2`): mevcut GES tam → 0; kısmi → elle çizilen panelsiz alan (`veri/elle/panelsiz_cizimleri.geojson`) ∩ son çatı; kısmi ama çizim yok → çatının tamamı (`kismi_panel_cizilmedi`, dikkat); c0157 ve c0319 görselle neredeyse tam dolu bulundu → tam sayıldı. PVGIS/NPV hesabında `uygun_alan_m2` kullanılmalı.

**Ana tablo** (`master_veriseti.csv`): `catilar.csv` + SAM metrikleri (`sam_alan_m2`, `kaplama`, `tasma`, `iou_ayak`, `guven`, `supheli`, `sam_kosu`); `sam_guncel` = False ise ayak izi SAM koşusundan sonra düzeltildi, SAM değerleri eski. Tek satır = tek çatı; web ve NPV için bu tablo kullanılır (alan: `cati_alan_m2`, potansiyel: `uygun_alan_m2`).

## Çatı başına üretim (`uretim/cati_uretim.csv`)
Üretici `scripts/uretim_hesabi.py` (temel: ekip arkadaşının `tahmin_modeli.ipynb`). Zincir: `uygun_alan` poligonu (mevcut GES düşülmüş) → kenar boşluğu kadar içeri tampon (kamu 1,2 m, sanayi 2,0 m) = `net_alan_m2` → × engel payı (0,70–0,80) × sıra gölgesi kaplama oranı (21 Aralık 10:00 gölgesiz; 10° → %72.5, 15° → %63.4) / cos(eğim) = modül alanı → × 0,20 kWp/m² = kWp → × PVGIS özgül üretim (PVcalc, SARAH3 2005–2023, kayıp %14, açık saha montaj, güney). Tüm çatılar **düz, güneye eğik sehpa** varsayımıyla (çatı tipi/yön verisi yok; doğu-batı yönlü eğimli çatıda özgül üretim ~%8 düşük, `yillik_ozet.csv`).

Sütunlar: `kwp_*`, `kwh_*` (yıllık) → `alt`/`ust` = {10°, 15°} × {0,70, 0,80} senaryolarının en küçüğü/büyüğü, `merkez` = 10° + engel 0,75 (NPV / Monte Carlo tabanı). `ozgul_kWh_kWp` = merkez senaryonun PVGIS değeri. Yıllar arası sapma (PVGIS SD_y) ve defterin kendi ışınım motoruyla çapraz kontrol: `ozgul_uretim_kontrol.csv` (defter PVGIS'ten ~%2 düşük).

Toplam (1085 çatı, 1021 üretim yapan): **178 MWp, 263 GWh/yıl** merkez; bant 225–281 GWh/yıl. Ayrıntı `uretim_ozet.csv`.

## Ekonomi: çatı başına NPV (`ekonomi/cati_npv.csv`)
Üretici `scripts/npv_hesabi.py` (girdi `uretim/cati_uretim.csv`, merkez senaryo). **Reel** hesap: sabit Nisan 2026 TL, reel iskonto %8, 25 yıl, bozunma %0.5/yıl, O&M yatırımın %1.5/yıl, evirici yenileme 13. yıl (%8). Yatırım kademeli: <100 kWp 550, 100–1.000 kWp 500, ≥1.000 kWp 450 USD/kWp × 50.07 TL/USD (TCMB 06.11.2026). **%100 öz tüketim** (kaçınılan bedel, vergi hariç: OSB sanayi 334.70, OSB sanayi dışı 369.94 [EPDK enerji + Atatürk OSB dağıtımı, 14049-111], Çiğli kamu 493.04 kr/kWh); yasal kurulum sınırı uygulanmadı (sözleşme gücü verisi yok). Taban + Monte Carlo aralıkları + kaynaklar: `npv_varsayimlar.csv`.

Sütunlar: `yatirim_TL`, `ilk_yil_tasarruf_TL`, `npv_TL` (+ `npv_TL_uretim_alt/ust` = üretim bandı), `npv_TL_kWp`, `irr_reel`, `geri_odeme_yil` (iskontosuz), `lcoe_TL_kWh`, `sira_npv` / `sira_npv_kWp` / `sira_uretim`. Üretim yapmayan çatılarda boş.

Toplam (1021 çatı): yatırım **4403 milyon TL**, ilk yıl tasarruf 918 milyon TL, **NPV 4167 milyon TL**; NPV > 0 olan 1021 çatı; medyan reel IRR %15.3, medyan geri ödeme 7 yıl, medyan LCOE 2.16 TL/kWh. Sıralama: Spearman (NPV ~ üretim) 0.989, ilk 50 ortak 43.

## Belirsizlik: Monte Carlo (`ekonomi/mc_*.csv`)
Üretici `scripts/monte_carlo.py` (`npv_hesabi.py` ile aynı nakit akışı; taban değer doğrulanır). 10.000 tur, sabit tohum, üçgen dağılım. Ortak girdiler her turda tüm çatılar için aynı; engel payı, yön/montaj, öz tüketim ve geometri kaynağına bağlı alan hatası çatı başına ayrı çekilir. Üç kurgu: `TAM` (hepsi), `OZ100` (öz tüketim %100), `ORTAK` (yalnız ortak girdiler).

- `mc_girdiler.csv`: aralıklar ve kaynakları
- `mc_ozet.csv`: toplam, sanayi ve kamu NPV yüzdelikleri (milyar TL)
- `mc_cati.csv`: çatı başına NPV yüzdelikleri ve P(NPV>0)
- `mc_tornado.csv`, `mc_tornado.png`: tek girdi değişiminin toplam NPV etkisi
- `mc_kararlilik.csv`: taban sıralamadaki ilk çatıların kalma oranı, Spearman
- `mc_sira.csv`: NPV ve NPV/yatırım sırasının üretim sırasıyla ilişkisi
- `mc_butce.csv`: bütçe kısıtında seçim karşılaştırması
- `mc_ek.csv`: İKÇÜ dâhil/hariç kamu toplamları
- `mc_toplam_npv.png`: toplam NPV dağılımı
