# Veri Doğrulama Raporu

Üretici: `CatiGunes/scripts/veri_dogrulama.py` (veriyi değiştirmez). Tarih: 2026-11-08.

**39 kural: 34 GEÇTİ · 3 UYARI · 0 HATA · 2 BİLGİ.** HATA = kullanmadan önce düzeltilmeli; UYARI = şüpheli, gözle bakılmalı (`incelenecek_catilar.csv`, 221 çatı).

## catilar

| durum | kural | sorunlu | açıklama / örnek |
|---|---|---|---|
| ✅ | cati_id tekil | 0 |  |
| ✅ | osm kimligi tekil | 0 |  |
| ✅ | gpkg ile csv ayni (satir, kimlik, alan) | 0 |  |
| ✅ | zorunlu alanlar dolu (osm, bolge, tur, alan_m2, ayak_izi_kaynagi, kesit, lon, lat) | 0 |  |
| ✅ | kamu catilarinda kurum_ad dolu | 0 |  |
| ✅ | bolge izinli degerlerde ['ataturk_osb', 'cigli_kamu'] | 0 |  |
| ✅ | tur izinli degerlerde ['hastane', 'okul', 'sanayi', 'sanayi_disi', 'universite'] | 0 |  |
| ✅ | ayak_izi_kaynagi izinli degerlerde ['Microsoft', 'OSM'] | 0 |  |
| ✅ | gorsel_kontrol izinli degerlerde ['agac_alti', 'goruntu_kotu', 'sekil_uyumsuz'] | 0 |  |
| ✅ | mevcut_ges izinli degerlerde ['kismi', 'tam'] | 0 |  |
| ✅ | bolge-tur uyumu (OSB: sanayi/sanayi_disi, kamu: okul/hastane/universite) | 0 |  |
| ✅ | OSB "sanayi disi" notu olan cati tur=sanayi_disi | 0 |  |
| ✅ | ms_iou 0-1 araliginda | 0 |  |
| ✅ | Microsoft kaynakli catilarda ms_iou = 1 | 0 |  |
| ✅ | Microsoft kaynakli OSB adaylari dogrulama notu tasiyor | 0 |  |
| ✅ | ayni kurumun catilari ayni tur | 0 |  |
| ✅ | geometri bos degil | 0 |  |
| ✅ | geometri gecerli (kendini kesmiyor) | 0 |  |
| ✅ | geometri tipi Polygon | 0 |  |
| ✅ | koordinat sistemi EPSG:4326 | 0 |  |
| ✅ | alan_m2 geometriden hesaplananla uyumlu (<%1) | 0 | en buyuk sapma %0.02 |
| ✅ | alan_m2 >= 30 (eleme esigi) | 0 |  |
| ✅ | ataturk_osb catilari kendi siniri icinde | 0 |  |
| ✅ | cigli_kamu catilari kendi siniri icinde | 0 |  |
| ✅ | lon/lat = hizali geometrinin merkezi (<1 m) | 0 |  |
| ✅ | catilar birbiriyle ortusmuyor (cift sayim; >5 m2 ve kucugun >%10) | 0 | toplam ortak alan 0 m2 |
| ✅ | serit/ince sekil yok (kisa kenar < 4 m) | 0 | duvar, sundurma ya da hatali cizim olabilir |
| ℹ️ | OSM catisinin Microsoft karsiligi var | 14 | medyan 462 m2; hepsi 2026-10-16 gorsel kontrolunden gecti (bina var) — way/503184001, way/503184003, way/503238877, way/503333813, way/503333814 |
| ✅ | indeks.csv ile catilar ayni catilari iceriyor | 0 |  |
| ✅ | kesit goruntusu var | 0 |  |
| ✅ | kesit goruntusu aciliyor | 0 |  |
| ✅ | kesit konum dosyasi (.jgw) var | 0 |  |
| ✅ | kesit boyutu indeksle ayni | 0 |  |
| ✅ | kesitte eksik karo yok | 0 | kenarda bos bant; cati kendisi tam mi bakilmali |
| ⚠️ | cati basina hizalama goruntuden dogrulandi (kazanc >= 1,15) | 134 | yalniz blok kaymasi uygulandi (241158 m2); dusuk kontrast / golge / agac — way/484820788, way/503177007, way/503177010, way/503183923, way/503183925 |
| ℹ️ | goruntu yuksek cozunurluklu (LG03 0,34 m) | 196 | 196 cati (508208 m2) WV02 0,5 m goruntude — way/503177006, way/503177007, way/503177008 |
| ⚠️ | gorsel kontrol bayragi yok (goruntu_kotu / agac_alti / sekil_uyumsuz) | 13 | SAM sonucu bu catilarda guvenilmez; Claude on karari 2026-10-21 insan teyidinden gecti — way/503238830, way/503238877, way/503398296, way/927242633, ms_osb/750 |
| ⚠️ | catida mevcut GES yok | 89 | 62 tam + 27 kismi (376138 m2); SAM maskesinden panel alani cikarilmali — way/503177007, way/503183915, way/503183918, way/503183920, way/503183923 |
| ✅ | gorsel kontrol insan tarafindan teyit edildi | 0 | 0 karar Claude tarafindan verildi (veri/elle/gorsel_kontrol.csv) |
