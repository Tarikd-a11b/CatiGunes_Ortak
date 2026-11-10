# Ekip kararları

Buradaki konular kapanmıştır. Yeniden açmak için ekip kararı gerekir. Yeni karar en alta tarihiyle eklenir.

## Kapsam
- Pilot bölge Atatürk OSB. Kamu tarafında Çiğli'deki okullar, hastaneler ve İzmir Kâtip Çelebi Üniversitesi Balatçık kampüsü var.
- OSM'de parçalı çizildiği için listeye girmeyen 43 sanayi binası eklenmeyecek. Sonuç alt sınır olarak yorumlanır.
- Gölge ve yükseklik analizi, kamusal fayda endeksi ve firma tüketim verisi kapsamdan çıkarıldı (raporun Giriş bölümünde gerekçesi var).
- SAM ince ayarı şu an rafta. Ek deneyler için ekip kararı gerekir.
- Firma–çatı eşleştirmesi kapandı.

## Üretim
- Üretim verisi PVGIS v5.3, 2005–2023 ortalaması, %14 sistem kaybı, açık montaj, güneye 10° eğim.
- Yıllık üretim 1 kWp için Atatürk OSB'de 1.477 kWh, Çiğli'de 1.514 kWh.
- Kenar boşluğu kamuda 1,2 m, sanayide 2 m (Kutlu vd., 2022; 2 m ticari yapılar için verilmiş, sanayiye uyarlandı).
- Engel payı 0,75 ve panel gücü 0,20 kWp/m² varsayımdır. Sıra yerleşim oranı yaklaşık 0,74.
- Sözleşme gücüne bağlı yasal kurulum sınırı veri olmadığı için uygulanmadı.

## Ekonomi
- Hesap sabit fiyatlarla, 25 yıl, iskonto %8.
- Bakım gideri yıllık yatırımın %1,5'i, 13. yılda yatırımın %8'i kadar evirici yenileme, yıllık verim kaybı %0,5.
- Kurulum maliyeti 100 kWp altında 550, 100–1.000 kWp arasında 500, 1.000 kWp ve üstünde 450 USD/kWp. Kaynak firma fiyatlarına dayalı varsayımdır, yayımlı resmî seri yok.
- Dolar kuru 50,07 TL (TCMB, 6 Kasım 2026).
- Elektrik fiyatı EPDK'nın 4 Nisan 2026'dan geçerli son tarifesi. Atatürk OSB'de OSB'nin kendi dağıtım bedeli kullanılır (EPDK 14049-111).
- Üretimin tamamının binada tüketildiği varsayılır. Bu yüzden sonuç iyimserdir.
- Monte Carlo sonuçları kabul edildi.

## Teknik
- Colab yalnız SAM çatı çıkarımı için kullanıldı. Üretim ve NPV yerelde Python betikleriyle üretilir.
- Rapor biçimi: A4, Times New Roman, tablolar sayfa arasında bölünmez.

## 10 Kasım 2026
- Firma adı arayüze alınmayacak: firma verisi eksik, elle onay tamamlanmadı. OSB çatıları arayüzde ve haritada tür bazında ("sanayi") gösterilir. Final raporda 4.5 bölümü buna göre yazılacak: "Veri eksik olduğu için firma adı arayüze alınmadı, çatılar tür bazında (sanayi) gösterildi." Ara rapora dokunulmaz.
- Şüpheli işaretli 128 çatı üretimde kalır. Bu çatılarda SAM maskesi kullanılmaz: 97'sinde kayıtlı ayak izi, 31'inde insan çizimi kullanılır. Payları üretimin %5,1'i, NPV'nin %5,3'ü.
- Hocaya yalnız sonuç defteri (`proje/notebooks/colab/sonuc_uretim_npv_harita_2026-11-07.ipynb`) çıktılarıyla gönderilir. Çalıştırınca NPV 4,17 milyar TL çıkmalıdır. `tahmin_modeli.ipynb` gönderilmez: kenar boşluğunu düşmediği için üretimi yaklaşık %20 fazla bulur. `ayak_izi_tespit_colab.ipynb` denenip bırakılan yöntemdir.
- Colab defterlerinin tek akışta birleştirilmesi ara rapordan sonraki iştir (final için tekrar üretilebilirlik).
