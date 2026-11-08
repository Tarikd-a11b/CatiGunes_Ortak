## Wang (2024) — SolarSAM
KUNYE: Wang G. (2024). SolarSAM: Building-scale photovoltaic potential assessment based on Segment Anything Model (SAM) and remote sensing for emerging city. Renewable Energy (2024). doi:10.1016/j.renene.2024.120156; açık sürüm arXiv:2407.00296 (40 s.). Kod: github.com/REAILAB/SolarSAM. Tek yazar, Northwest A&F Univ., Çin.
TEMA: SAM'in çatı PV potansiyeline uygulandığı ilk çalışma — projenin ana teknik referansı
AMAC: 3B şehir verisi olmayan "gelişmekte olan şehir" (Zibo, Shandong) için yalnız uydu görüntüsüyle bina entegre PV (çatı + cephe + pencere) potansiyeli, ekonomisi (LCOE) ve karbon azaltımını hesaplamak; bina türünü de ayırt etmek.
YONTEM:
- Görüntü: Google Earth'ten web kazıma, 500 m irtifa mercek → 149.420 karo (karo başına 39.920 m², ölçek 1:1110) = "Zibo24" veri seti.
- 6 bina sınıfı: apartman (≤7 kat), müstakil ev, merkez/ticari, fabrika, yüksek katlı, diğer.
- SAM + CLIP metin kodlayıcı ile METİN İSTEMİ: en iyi istem "Roofs of [bina sınıfı] from satellite", en iyi kutu eşiği 0,25. 100 elle etiketli karo ile istem mühendisliği + hiper parametre seçimi.
- Alan: maske pikseli × ölçek faktörü S → A_i; kullanılabilir alan AAPV = A × (A/RA) × K_mapping; çatı için A/RA = 1. K_mapping: fabrika 0,80 · ev 0,70 · merkez 0,65 · apartman 0,60 · yüksek kat 0,50 · diğer 0,40. Cephe ve pencere için bina türüne göre cephe/çatı oranı.
- Üretim: pvlib + yerel iklim (ışınım, sıcaklık, konum, güneş açısı).
- Ekonomi: LCOE, r = 0,05, n = 25 yıl, maliyet = kurulum + işletme-bakım + ÇATI/CEPHE KİRASI (C_rent). Karbon: 0,6838 kg CO₂/kWh (Çin şebekesi).
- Metrikler: piksel doğruluğu (PA), IoU.
VERI: Google Earth uydu görüntüsü (kazıma; lisans sorunu tartışılmıyor), Zibo iklim verisi, Çin şebeke emisyon faktörü, yerel maliyetler.
BULGULAR: IoU yalnız %28,6–36,2 (apartman 36,2, ev 28,6, merkez 30,2, fabrika 31,2, yüksek kat 31,1). Yine de şehir geneli BIPV potansiyeli ~101 TWh/yıl = tüketimin 2,5 katı (tüketim 2022'de 41,63 TWh). Çatı PV her bina türünde en ekonomik (LCOE ≤ 0,20 CNY/kWh ≈ 0,028 $/kWh; fabrika en düşük 0,18). Apartman ve yüksek katlıda cephe PV potansiyeli çatıyı aşıyor. Yıllık karbon azaltımı 7,08×10⁷ t CO₂.
EKSIKLER:
- Segmentasyon çok zayıf (IoU ~0,3; özel bina segmentasyon modelleri 0,70–0,85 alıyor) → 101 TWh'lik sonuç bu zayıf zemin üzerine kurulu.
- METİN İSTEMİ: SAM'in kendi yazarları metinden maskeyi "keşifsel, tam güvenilir değil" diye niteliyor.
- Doğrulama yalnız 100 etiketli karoda; üretim ya da gerçek tesislerle karşılaştırma YOK.
- Eğim bina bazında hiç hesaplanmıyor (K_mapping ile ikame).
- Panel verisinde tutarsızlık: 2,23 m²'de 46,3 W = 20,8 W/m² (gerçek c-Si 190–230 W/m²) → kapasite rakamları güvenilmez.
- Gölge yok; bina yüksekliği bilinmiyor (cephe potansiyeli için kritikken).
- Web kazıma lisans sorunu tartışılmıyor.
- Toplumsal boyut HİÇ yok.
- Tek yazar, hakem sürecinden geçmiş ama doğrulama düzeyi zayıf.
BIZIM PROJEYE:
- Tezin temel konumlandırması: "SolarSAM'ı taklit etmedik, zayıf halkasını (metin istemi) değiştirdik" → OSM ayak izinden türetilen KUTU istemi. SAM makalesi kutuyu birinci sınıf istem sayıyor; Osco vd. 2023 de kutu isteminin daha iyi olduğunu gösteriyor.
- Bizim doğrulama yöntemimiz (109 çatı tabakalı örneklem + 26 gerçek GES ile PVGIS kontrolü) SolarSAM'ınkinden kapsamlı → karşılaştırma tablosu yap.
- K_mapping tablosu: eğim bilinmediğinde bina türüne göre kullanılabilir alan katsayısı — bizim sabit 0,55/0,70 yerine bina türüne (OSB fabrika 0,80, apartman 0,60 vb.) göre katsayı alternatifi; duyarlılık analizine ekle. Özellikle "apartman 0,60 — asansör kulesi, su deposu, baca" gerekçesi Türkiye apartman çatısına çok uyuyor.
- Ekonomide ÇATI KİRASI kalemi: kamu binası dışındaki çatılarda (kiralık çatı modeli) Faz 4'e eklenebilir.
- Karbon faktörü: Türkiye şebeke emisyon faktörü (ETKB/TEİAŞ yayımlıyor) ile CO₂ azaltımı hesaplanabilir — LLM raporuna ek çıktı.
- W/m² tutarsızlığı uyarısı: panel güç yoğunluğunu literatürden doğrula (bizim 6 m²/kWp ≈ 167 W/m² brüt, makul).
