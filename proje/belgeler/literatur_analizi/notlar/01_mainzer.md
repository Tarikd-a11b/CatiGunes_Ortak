## Mainzer, Killinger, McKenna & Fichtner (2017) — Freiburg
KUNYE: Mainzer K., Killinger S., McKenna R., Fichtner W. (2017). Assessment of rooftop photovoltaic potentials at the urban level using publicly available geodata and image recognition techniques. Solar Energy 155, 561–573. doi:10.1016/j.solener.2017.06.065. (İncelenen: KIT yazar ön baskısı)
TEMA: Görüntüden çatı PV potansiyeli — en yakın yöntem öncülü
AMAC: 3B şehir modeli / LiDAR olmadan, YALNIZ açık veriyle (OSM + hava fotoğrafı + ışınım verisi) bina ölçeğinde çatı PV potansiyeli çıkarmak; küçük belediyelerin karar vericilerine araç sunmak. "Kalan (henüz kullanılmamış) ekonomik potansiyel"i bulmak.
YONTEM (9 adım, her bina için):
1. Ayak izi: OSM 'building' etiketi, Overpass API. Duvar azimutları → olası mahya yönleri (mahya duvara paralel varsayımı). >3.000 m² taban → düz çatı (ofis/fabrika) varsayımı, 2–3. adım atlanıyor.
2. Kısmi çatı yüzeyleri: Bing Maps ortofotosu ayak iziyle kırpılıyor → bilateral filtre → renk filtresi (R 0,75 / G 0 / B 0,25 ağırlık) → histogram eşitleme → Canny kenar → Hough doğru dönüşümü → mantık filtreleri (duvara çok yakın/paralel olmayan çizgiler atılır, kesik çizgiler birleşir) → uzunluk + iki yarı arasındaki parlaklık farkının ağırlıklı toplamıyla mahya seçimi. Bulunamazsa eşikler kademeli düşürülüyor. Binaların %27'sinde mahya bulunamadı → düz çatı ya da "en uzun duvara paralel, ikiye böl" yedek yöntemi.
3. Eğim: görüntüden ÇIKARILAMIYOR → Baden-Württemberg LiDAR'ından (3.002.943 bina) uydurulan N(37°, 15°) normal dağılımından çekiliyor. Mahyası bulunmayan binalar, "binaların ~%9'u düz çatılı" istatistiğine göre RASTGELE çekilişle düz/eğimli sınıflanıyor.
4. Çatı üstü nesneler: kontur tespiti (Suzuki-Abe) + Douglas-Peucker poligon sadeleştirme → baca/pencere boyut-şekil ölçütüyle kullanılabilir alandan çıkarılıyor (sabit kullanım katsayısı yerine).
5. Modül yerleşimi: gerçek çatı şekline tek tek modül sığdırma (eğimli çatıda modüller arası 10 cm; düz çatıda güneye 30° eğik, sıralar arası 2× modül yüksekliği boşluk).
   + Genel düzeltme: tespit edilemeyen engeller, statik uygunsuzluk, tarihî yapı (Almanya'da binaların %3,5'i), BİNA GÖLGESİ (yoğun dokuda %14–21 kayıp, Takebayashi 2015), ağaç gölgesi → toplam potansiyel SABİT %30 düşürülüyor (Nowak 2002 %40 kullanmış).
6. Işınım: Grena (2012) güneş konumu + CAMS (Copernicus) yatay direkt/yaygın ışınım; 15 dakikalık çözünürlük. Hesap yükü nedeniyle çatılar 144 yönelim sınıfına (16 azimut × 9 eğim) ayrılıp her sınıf için bir kez hesaplanıyor.
7. Elektrik: sıcaklık, ışınım ve yük oranına bağlı doğrusal olmayan modül + evirici verim modeli (Huld 2010 vb.).
8. Ekonomi: LCOE = indirgenmiş (yatırım+işletme) / indirgenmiş üretim (bozulma d ile) → maliyet-potansiyel eğrisi (CPC); ekonomik potansiyel = LCOE eşiği altındakiler.
9. Mevcut PV tespiti: AlexNet benzeri CNN (Deeplearning4j, 72×72 girdi, 2 sınıf), 2.934 elle etiketli çatı (%80/%20), %90 olasılık eşiği üstü "zaten kullanılmış".
MODEL/TEKNOLOJI: Java (RE³ASON kent enerji sistemi modeli), OpenCV, Deeplearning4j CNN, Overpass API, Bing Maps.
VERI: OSM ayak izleri; Bing Maps hava fotoğrafı; CAMS ışınım + sıcaklık; LiDAR (yalnız eğim dağılımını kurmak ve doğrulama için); Freiburg 3B şehir modeli (doğrulama, 191.335 kısmi çatı); Almanya PV sicili (EnergyMap).
BULGULAR: Freiburg 49.573 bina → teknik potansiyel 524 GWh/yıl, 85 GWh/yıl'ı "zaten kullanılmış"; LCOE 9–29 €ct/kWh. Azimut doğrulaması 26.412 eşleşen binada: ~%70 doğru; hataların ~%20'si ±90° (yanlış duvara paralel mahya), ~%5'i ±45° (kırma çatı); hatalar SİMETRİK → yıllık toplamda birbirini götürüyor, sistematik sapma yok. Sokak dokusu azimut dağılımını belirliyor (Mooswald: sapma std 5°, Herdern 30°) → aynı alan farklı üretim. Mevcut PV CNN doğruluğu %90,97 (precision 91,9, recall 91,0, F1 91,1). Hesap maliyeti: Freiburg 30 saat, 80 GB RAM.
EKSIKLER (yazarların kendisi + bizim gözlem):
- Eğim tamamen varsayım (dağılımdan rastgele çekim) → bina bazında belirsizlik yüksek, yalnız toplamda anlamlı.
- Düz/eğimli ayrımı kısmen RASTGELE çekilişle yapılıyor — savunması zayıf.
- Bina gölgesi hesaplanmıyor, sabit %30 indirimle geçiştiriliyor.
- Karmaşık geometride (T, L biçimli) mahya yöntemi çöküyor; segmentasyonu "gelecek iş" olarak öneriyorlar.
- Doğrulama referansı (3B model) da hatalı; yalnız binaların yarısı eşleşebildi.
- CNN yalnız 3 Alman bölgesinden eğitildi; PV ile güneş kollektörünü ayıramıyor; tüm çatıyı "kullanılmış" sayınca kullanılmış potansiyeli abartıyor (85 vs sicil 35 GWh).
- Toplumsal boyut YOK; öncelik yalnız LCOE'ye göre.
- Şebeke entegrasyonu/depolama maliyeti yok → iyimser.
BIZIM PROJEYE:
- Tezde "en yakın öncül" olarak konumla: aynı felsefe (açık ayak izi + görüntü, LiDAR yok). Farklarımız: (a) SAM ile piksel düzeyi segmentasyon (onların "gelecek iş" dediği şey), (b) gölgeleri güneş yönü ÖLÇMEK ve bina yüksekliği çıkarmak için kullanmamız (onlar yüksekliği hiç bilmiyor), (c) bina gölgesini sabit %30 yerine ışın izlemeyle hesaplamamız, (d) toplumsal katman.
- Azimut doğruluğu %70 = görüntüden yön çıkarmanın literatürdeki tavanı → bizim eğim/yönü BANT olarak vermemizin savunması. Hataların simetrik olup toplamda sönümlenmesi argümanını biz de kullanabiliriz (bina bazında değil mahalle bazında raporlama).
- 144 yönelim sınıfı fikri = bizim "PVGIS'i merkezde eğim×yön ızgarasında sorgula" yaklaşımımızın aynısı → yöntem kararımızın literatür karşılığı.
- Düz çatıda 30° güney + sıra arası 2× modül yüksekliği kabulü → bizim DUZ_ORAN 0,55 katsayısını bununla gerekçelendir/kontrol et.
- >3.000 m² = düz çatı sezgisi → OSB'deki tip sınıflandırma hatamız için basit bir düzeltme kuralı olabilir (bizde turuncu/pembe fabrika çatıları).
- Mevcut PV tespiti (CNN) → Çiğli'de "zaten panel olan çatıları" düşmüyoruz; açık iş olarak ekle (Sunter'in kurulu/potansiyel oranı için de gerekli).
- LCOE ve maliyet-potansiyel eğrisi → Faz 4 ekonomi modeli için hazır çerçeve.
- Tarihî/tescilli yapı dışlaması → İzmir'de sit/tescil katmanı (Sasalı doğal sit ile birlikte) plan kısıtı olarak eklenebilir.
