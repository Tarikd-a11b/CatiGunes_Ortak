# Çiğli geneli tam koşu sonuçları (2026-09-17, Colab T4)

Kaynak: Drive'daki `CatiGunes_Cigli_Segmentasyon.ipynb` (fileId `1Dc6IBz2hIy_nuH7visUHb4GF7cFQfGY6`,
"Colab Notebooks" klasörü), oluşturma 2026-09-17T20:10, son değişiklik 2026-09-17T21:06 (~1 saat koşu).
Bu, oturtma-filtresi + alan-sınıfına-göre arama yarıçapı düzeltmelerinin (2026-09-17/18 oturumu)
uygulandığı **ilk tam Çiğli koşusu**. Kamu binası eşleştirmesi ve interaktif harita hücreleri bu
koşuda henüz yoktu (sonradan eklendi). Dosya "sadece bu yenisi kalsın" temizliği kapsamında Drive'da
çöpe taşındı; sayılar kaybolmasın diye burada arşivlendi.

## TOPLAM (yalnız oturtma_orani >= 0,4)
**18.064 çatı | 5,53 km² | 383–504 MWp | 526,3–749,2 GWh/yıl (bant 1,42×)**
Ayrı tutulan şüpheli: 2.227 çatı, 0,31 km² (doğrulamada bu bantta doğruluk %17,1, normal bantta %87,9)

26 mahalle (OSB hariç), önceki ayak izi modeli: 195,2–625,9 GWh/yıl | segmentasyon: 308,4–470,6 GWh/yıl

## Birim özeti (ilk 10, GWh merkezine göre sıralı; tam tablo aşağıda)
| birim | tür | çatı | çatı m² | şüpheli çatı | eğimli % | gölge kaybı % | MWp alt-üst | GWh alt-üst |
|---|---|---|---|---|---|---|---|---|
| Atatürk OSB | OSB | 1257 | 2.010.919 | 155 | 19,8 | 2,12 | 159,7–183,0 | 217,8–278,6 |
| Ataşehir | mahalle | 1460 | 465.465 | 141 | 47,4 | 3,28 | 30,7–42,5 | 42,7–62,7 |
| Sasalı Merkez | mahalle | 1445 | 403.124 | 125 | 47,3 | 2,49 | 25,2–35,9 | 35,4–53,7 |
| Balatçık | mahalle | 1266 | 377.197 | 166 | 37,3 | 3,43 | 26,2–34,9 | 36,2–52,2 |
| Kaklıç | mahalle | 1217 | 344.137 | 118 | 31,5 | 2,86 | 25,5–30,6 | 34,8–46,0 |
| Küçük Çiğli | mahalle | 1083 | 268.350 | 168 | 45,9 | 4,20 | 17,8–24,4 | 24,3–35,6 |
| Yeni Mahalle | mahalle | 1050 | 184.598 | 160 | 50,1 | 6,20 | 11,6–17,1 | 15,7–24,6 |
| Şirintepe | mahalle | 1580 | 145.294 | 338 | 46,0 | 4,87 | 9,7–13,0 | 13,1–19,0 |
| Maltepe | mahalle | 774 | 106.814 | 47 | 38,2 | 6,68 | 7,6–9,6 | 10,2–14,1 |
| Harmandalı GMK Atatürk | mahalle | 827 | 98.884 | 58 | 43,2 | 3,45 | 6,7–8,9 | 9,3–13,3 |

(Kalan 16 mahalle: İnönü, Güzeltepe, Uğur Mumcu, Aydınlıkevler, Köyiçi, Ahmet Taner Kışlalı, Yakakent,
Evka-5, Evka-2, Atatürk, Cumhuriyet, Esentepe, Egekent, Ahmet Efendi, Çağdaş, İzkent, Evka-6 —
1,7–10,9 GWh/yıl bandında, tam sayılar notebook çıktısında.)

Not: Sasalı Merkez ve Kaklıç plan kısıtlı (doğal sit / askerî havaalanı) — sıralamada bu uyarı taşınmalı.
Atatürk OSB tek başına Çiğli toplamının ~%37'si; sanayi çatısı, mahalle sıralamasına karıştırılmamalı.

## Ara adım çıktıları (özet)
- **Overpass:** aşırı 429/504 hatası (ilk denemede aynalardan art arda reddedildi), 3 karo dörde
  bölünerek kurtarıldı. Sonuç: 20 karo, 33.729 bina poligonu (tampon dahil), işlenecek 20.312 bina.
- **4 çekim:** LG03 20260114 (17.396 bina, güvenilir), LG05 20260219 (2.370, güvenilir),
  WV02 20251012 (502, GÜVENİLMEZ), LG02 20260120 (40, GÜVENİLMEZ); 4 bina çekime atanamadı.
- **SAM:** 1.334 kare, 20.306 maske, 839 s (T4, ~14 dk).
- **Çatı sonucu:** 20.291 çatı | OSM ayak izi 6.097.277 m² | ham SAM 7.051.510 m² | son çatı 5.841.041 m².
  SAM'siz 6 dev yapı, oturtması şüpheli 2.227 (%11,0 — önceki koşudaki %10,9 ile tutarlı).
- **Tip dağılımı:** eğimli 6.800 · karma 1.562 · muhtemelen eğimli 1.227 · düz/teras 10.498 (~%51,7).
- **Çekim bazında kayma medyanı (m):** LG02 5,88 · LG03 4,08 · LG05 1,83 · WV02 2,30.
- **Fotometrik eğim:** n=6.793, medyan 26,8°, %25–%75 15,0–54,0°, sınıra dayanan 1.941.
- **Yükseklik:** ölçüldü 9.411 · ölçülemedi 7.315 · engelli 3.019 · çekim güvenilmez 546.
  Alan sınıfı medyan yükseklik: <150 m² 8,0 m · 150-300 m² 11,1 m · 300-600 m² 17,7 m · ≥600 m² 17,7 m.
- **Yıllık gölge kaybı:** medyan %1,2, ortalama %6,2, %10 üstü 4.277 çatı, %25 üstü 1.360 çatı.
- **PVGIS:** 81 sorgu, merkez düz 1.372 kWh/kWp, birim ölçeği 0,977–1,017.

## Eksik kalan (bu koşuda yoktu, sonraki koşuda tamamlanacak)
- Kamu binası eşleştirmesi (artık ana deftere entegre, hücre 14).
- İnteraktif harita (artık ana deftere entegre, hücre 15).
- `INDIR=False` olduğu için `cigli_catilar_tum.geojson/csv` ve `cigli_birim_ozeti_tum.csv` dosyaları
  runtime diskinde kaldı, indirilemedi — bu değerler yalnız yukarıdaki özet tablo olarak kurtarıldı.
  Bina bazında ayrıntı (her çatının geometrisi, tipi, oturtma oranı vb.) kayıp; yeniden koşu gerekiyor.
