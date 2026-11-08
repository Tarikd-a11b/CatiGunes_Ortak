## Li, Krapf, Shi & Zhu (2023) — SolarNet
KUNYE: Li Q., Krapf S., Shi Y., Zhu X.X. (2023). SolarNet: A convolutional neural network-based framework for rooftop solar potential estimation from aerial imagery. International Journal of Applied Earth Observation and Geoinformation 116, 103098. doi:10.1016/j.jag.2022.103098 (açık erişim). TU München.
TEMA: Derin öğrenmeyle çatı yüzeyi + YÖN (azimut) çıkarımı → PV potansiyeli
AMAC: Yalnız çatı maskesi çıkarmak potansiyeli ABARTIR (yön/eğim yok sayılıyor). Hava görüntüsünden çatı yüzeylerini ve yönlerini öğrenip daha isabetli potansiyel hesaplamak; etiketleme yükünü ve sınıf dengesizliğini azaltmak.
YONTEM:
- Yeni temsil: 18 sınıf (arka plan + düz + 16 azimut) yerine 6 sınıf (arka plan, düz, K, D, G, B — her azimut sınıfı 90°'lik dilim). Gerekçe: 16 sınıflı etiketleme zahmetli ve sınıflar dengesiz (binalar mimari nedenle birkaç yöne yığılıyor).
- Çok görevli ağ: kodlayıcı ResNet34 (4 aşama + her aşamaya basic ResNet block), ASPP (atrous spatial pyramid pooling) çok ölçekli bağlam, kod çözücü; önce ÇATI MASKESİ öğreniliyor, sonra maske özelliklerle birleştirilip ÇATI GEOMETRİ HARİTASI (yön sınıfları) öğreniliyor. Kayıp L = 0,1·L_maske + L_geometri (çapraz entropi). Atlama bağlantıları.
- Potansiyel: geometri haritası vektöre çevrilir → her sınıfın alanı A_i → PVGIS bakma tablosundan sınıfa özgü yıllık ışınım G_i (eğimli sınıflar için eğim SABİT 30°) → E_i = G_i × A_i → toplam = düz + K + D + G + B.
- Karşılaştırma: U-Net, Efficient-UNet, FC-DenseNet, DeepLab V3+. Eğitim/doğrulama/test 7:1:2.
- Metrikler: IoU = TP/(TP+FP+FN), mIoU, genel doğruluk (OA); potansiyel için %RMSE.
VERI: DeepRoof (Lee vd. 2019; 6 ABD şehri, 2.274 bina) ve RID (Krapf vd. 2022; Wartenberg, Almanya, 1.880 bina) — ikisi de 18 sınıflı etiketli hava görüntüsü. Yazarlar veriyi paylaşma izinleri olmadığını belirtiyor.
BULGULAR: mIoU RID %68,59 / DeepRoof %59,70 (U-Net'ten +4,73 / +2,58; DeepLab V3+'tan +14,84 / +19,48 puan). Sınıf IoU (RID): arka plan 97, K 81, G 74, D 65, B 59, DÜZ yalnız %34,6 (en zayıf sınıf). DeepRoof'ta D ve B zayıf (az örnek). Potansiyel %RMSE: RID 15,30 (18 sınıfla 17,02), DeepRoof 21,10 (25,82). 16→4 azimut indirgemesinin yer gerçeğinde yarattığı fark yalnız %1,62 (RID) / %0,55 (DeepRoof) %RMSE → "çok ince yön sınıfı gereksiz".
EKSIKLER: Eğim tüm eğimli çatılarda 30° sabit; gölge (bina/ağaç) yok; kullanılabilir alan (baca, sıra aralığı) yok — ışınım × tüm alan, dolayısıyla "potansiyel" aslında ışınım potansiyeli; yalnız Almanya/ABD'de sınanmış; etiketli veri gerektiriyor (yazarlar da yarı denetimli öğrenmeyi gelecek iş diyor); kenarlarda sınıflandırma hataları; zaman/yıllık değişkenlik yok.
BIZIM PROJEYE:
- "Neden SolarNet gibi eğitilmiş bir model kullanmadınız?" sorusunun cevabı buradan: (1) etiketli veri gerekiyor — Türkiye için yok, onlar bile verilerini paylaşamıyor; (2) en iyi modelin mIoU'su %60–69, DÜZ çatı IoU'su %35 — Çiğli çatılarının %52'si düz/teras olduğu için bu modelin bizim bölgemizde zayıf kalacağı beklenir; (3) eğimi onlar da 30° sabit alıyor, yani eğim sorununu çözmüyor.
- 16→4 azimut indirgemesi potansiyelde yalnız ~%1–2 fark yaratıyor → bizim yüz azimutlarını 4 ana yöne (güney / doğu-batı / kuzey) indirgeyerek PVGIS sorgulamamızı destekler; ayrıntılı azimut hassasiyetine gerek yok.
- PVGIS bakma tablosu (sınıf başına tek sorgu) = bizim merkez-ızgara yaklaşımımızla aynı → literatür karşılığı.
- Çok görevli fikir (önce çatı maskesi, sonra yön) = bizim "önce SAM maskesi, sonra yüz/azimut analizi" iki aşamalı boru hattımızın derin öğrenme karşılığı.
- %RMSE metriği → bizim doğrulamada potansiyel hatası için kullanılabilecek metrik (gerçek GES tesislerinde).
- Düz çatı sınıfının her modelde en zayıf olması → bizim doğrulamada düz/teras doğruluğunun %61,5 çıkması "literatürdeki genel zorlukla tutarlı" diye yorumlanabilir.
