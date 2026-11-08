## Chen, Wang & Li (2025) — Lanzhou Yeni Bölgesi, sanayi vs konut çatısı
KUNYE: Chen Y., Wang S., Li T. (2025). Analysis of rooftop photovoltaic potential and electricity planning in Lanzhou urban areas. Buildings 15(13), 2207. doi:10.3390/buildings15132207 (MDPI, açık erişim, CC BY). Gansu Mühendislik Danışmanlık Grubu + Wuhan Bilim ve Teknoloji Üniv.
TEMA: Derin öğrenmeyle çatı + panel yerleştirme simülasyonu + BÖLGESEL ELEKTRİK TALEBİYLE eşleştirme; sanayi ve konut binalarını ayrı değerlendirme
AMAC: Potansiyeli yalnız hesaplamak değil, bölgenin elektrik yük yapısıyla (sanayi/konut tüketimi) ve gerçek kurulum kısıtlarıyla (sıra aralığı, engeller) birleştirerek PV planlamasına yol göstermek; sanayi ile konut çatılarını ayrı modellemek.
YONTEM:
- Görüntü: ESRI uydu haritası (World Imagery) QGIS ile 100×100 m karolara (2000×2000 px → ~0,05 m/piksel olarak dışa aktarılmış, asıl çözünürlük belirtilmemiş) bölünmüş; çalışma alanı 8.774 karo = 87,74 km².
- Arazi kullanım vektöriyle binalar SANAYİ ve SİVİL (konut/ticari/ofis) diye önceden ayrılıyor → iki ayrı model.
- Model: U²-Net (iki katmanlı U yapısı, belirginlik/salient nesne tespiti; 6 aşamalı kodlayıcı, 5 aşamalı kod çözücü); öğrenme oranı 0,001, 200 epoch, batch 4. Etiket: LabelMe ile "çatı / arka plan"; eğitim 173+217, test 32+35 görüntü (KÜÇÜK).
- Metrikler: maxFβ (β² = 0,3) ve MAE.
- PV yerleştirme: OpenCV tabanlı panel "simülasyon dolgusu" ile çatıya sığan en fazla panel alanı.
- Işınım: Global Solar Atlas'tan bölge merkezinin tek değeri (1.605,6 kWh/m²·yıl); potansiyel P = A × S_y; PV potansiyeli P_PV = A_PV × S_y × η (polikristal %15).
- Talep: Lanzhou il yıllıklarından sanayi/konut elektrik tüketimi (2020–2024), nüfus ve sanayi payına göre Yeni Bölge'ye ölçeklenmiş.
- Potansiyel sınıflaması: karolar yüzdeliklere göre yüksek (>%75), orta (%25–75), düşük (<%25).
BULGULAR: maxFβ sanayi 0,889, sivil 0,846 (sanayi çatısı düzenli dikdörtgen ve büyük → daha kolay). Panel yerleştirilebilir alan oranı sanayide %62,84, sivilde %51,24. PV potansiyeli sanayi 293,6 GWh, sivil 223,2 GWh. Sanayi PV'si sanayi tüketiminin %75,17'sini, sivil PV konut tüketiminin 5,28 katını karşılıyor → öneri: SANAYİ çatısına öncelik; konutta talep kadar kurulum; eski binalar kapsam dışı; depolama önerisi.
EKSIKLER: Çok küçük etiketli veri seti (~390 eğitim görüntüsü); tek ışınım değeri (mekânsal farklılık yok); eğim, yön, gölge yok (bina aralıkları büyük diye gölge yok sayılmış); verim sadeliği (%15 ve başka kayıp yok — PR yok, ki bu Zhong'un 0,80'inden farklı); sivil binaları konut/ticari olarak ayırmıyor; ekonomi ve toplumsal boyut yok; talep tahmini kaba ölçekleme.
BIZIM PROJEYE:
- Sanayi/konut ayrımı: sanayi çatısının hem segmentasyonda hem kullanılabilir alanda farklı davrandığını gösteriyor (maxFβ 0,889 vs 0,846; kullanılabilir alan %63 vs %51) → bizim Atatürk OSB'yi ayrı raporlama kararımızı destekliyor; OSB için ayrı kullanılabilir alan katsayısı (~0,63 ve SolarSAM fabrika 0,80) uygulanabilir.
- Talep eşleştirme fikri: potansiyeli bölgenin tüketimiyle karşılaştırma ("karşılama oranı") → bizim mahalle bazında hane tüketimi (2.965 kWh/hane) karşılama oranımızın literatür karşılığı. Konut PV'sinin konut talebini 5 kat aşması → "konutta tüketim kadar kur" argümanı; EPDK'nın saatlik mahsuplaşma ve öz tüketim kuralıyla birlikte Türkiye için daha da geçerli.
- Yüzdelik tabanlı potansiyel sınıflaması (yüksek/orta/düşük) → bizim sıra-yüzdelik normalizasyonumuzla uyumlu, harita katmanında kademe gösterimi için kullanılabilir.
- Karşıt argüman olarak: bu çalışma önceliği yalnız teknik potansiyel + talebe göre veriyor (sanayi önce); bizim toplumsal katmanımız tam bu "sanayi/en verimli çatı önce" mantığına alternatif — tezde kontrast olarak kullan.
