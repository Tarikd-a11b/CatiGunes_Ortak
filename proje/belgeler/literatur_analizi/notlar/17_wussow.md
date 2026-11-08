## Wussow, Zanocco, Wang, Prabha, Flora, Neumann, Majumdar & Rajagopal (2024) — Konut dışı güneş ve enerji adaletsizliği
KUNYE: Wussow M. vd. (2024). Exploring the potential of non-residential solar to tackle energy injustice. Nature Energy 9, 654–663. doi:10.1038/s41560-024-01485-y. Stanford Üniv. + Freiburg Üniv.
TEMA: Kamu/ticari/sanayi (büyük bina) çatılarının dezavantajlı topluluklara hizmeti — KAMU BİNASI EKSENİMİZİN en güçlü dayanağı
AMAC: ABD'de konut DIŞI (ticari, sanayi, okul, kamu, çok aileli konut üzeri topluluk sistemleri; 10–1.000 kW) güneş kurulumlarında da konuttaki gibi eşitsizlik olup olmadığını ölçmek; büyük bina çatılarının dezavantajlı toplulukların (DAC) elektrik ihtiyacının ne kadarını karşılayabileceğini göstermek.
YONTEM:
- DeepSolar güncellemesi: ~230 milyon hava görüntüsü, Vision Transformer (sınıflama) + SegFormer (segmentasyon); 2022'ye kadar 2,3 milyon PV'li bina; panel alanı × 200 W/m² = kapasite.
- Microsoft Open Buildings ayak izleri (bina büyüklük sınıfları); ABD Justice40 dezavantajlı topluluk (DAC) sınıflaması (gelir eşiği + iklim/enerji/sağlık/konut/kirlilik/ulaşım/su yüklerinden biri; ya da eğitim eşiği + işgücü yükü) — nüfusun %33'ü, nüfus sayım bölgelerinin %36'sı DAC; NREL ışınım ve elektrik fiyatı API'si; DSIRE politika veritabanı.
- Güneş eşitlik açığı (SEG): göreli = (μ_DAC / μ_nonDAC − 1) × 100; güven aralığı 100.000 bootstrap.
- Sürücüler: negatif binom sayım regresyonu (PV'li bina sayısı), eyalet sabit etkileri, eyalet düzeyinde kümelenmiş standart hata; bağımsız değişkenler [0,1]'e normalize.
- Potansiyel senaryosu: >1.000 m² ayak izli büyük binalar; ayak izinin %10 / %25 / %40'ı panele uygun; 200 W/m²; aylık üretim ↔ konut elektrik talebi.
- Sağlamlık: Berkeley Lab "Tracking the Sun" verisiyle karşılaştırma; PG&E şebeke topolojisiyle doğrulama.
VERI: 72.739 nüfus sayım bölgesi (26.372 DAC).
BULGULAR:
- DAC'lerde konut dışı güneş %38 (≈%37) daha az, KONUT güneşi %67 daha az → konut dışında açık %77 daha küçük; toplam açık %56. Açık çoğunlukla "daha az bina" kaynaklı, sistem büyüklüğünden değil.
- Eyalet farklılığı: konutta −%81 (NY) ile −%49 arası (tutarlı); konut dışında −%66 (Pennsylvania) ile +%34 (Utah/Hawaii'de DAC'ler DAHA FAZLA) → konut dışı politika ile yönlendirilebilir.
- Zaman: toplam açık 2006 %48 → 2022 %56 (büyüdü); konut açığı 2008 zirvesi %80 → 2022 %67 (hedefli programların etkisi olabilir); konut dışı açık %24 → %38 (büyüdü).
- Regresyon: DAC göstergesi kontrollere rağmen anlamlı negatif (açıklanamayan eşitsizlik); ışınım, nüfus, elektrik fiyatı, politika sayısı pozitif; nüfus yoğunluğu negatif; konut PV'si 100–300 m² (müstakil ev) sayısıyla, konut dışı PV >1.000 m² bina sayısıyla güçlü ilişkili; finansal teşvikler konut dışında daha etkili.
- Bina türü kırılımında (market zincirleri, depolar, bankalar, HASTANELER, İTFAİYE, fabrikalar, EĞİTİM tesisleri) ortalama açık −%29 → bina kullanım farkı açığı tek başına açıklamıyor.
- POTANSİYEL: %25 ayak izi kullanımında DAC'lerin %63'ü (%10'da %29, %40'ta %77) büyük bina çatılarıyla yıllık konut talebinin ≥%20'sini karşılayabilir; mayısta %30, ocakta %13. DAC'lerin %93'ünde konut dışı PV'nin LCOE'si konut elektrik tarifesinin altında. Batarya (kW başına 600 Wh) sistem maliyetini %50, LCOE'yi 4 cent/kWh artırıyor.
- AMPİRİK BULGU: büyük binalarda mevcut kurulumlar ayak izinin ortalama %20'sini kaplıyor (çeyrekler arası %5–29) — net metering sistemi talebe göre küçük tutmaya itiyor.
- Öneriler: topluluk mikro-şebekeleri, topluluk güneş abonelikleri (kiracı/düşük gelirli), bataryalı dayanıklılık (hastane, itfaiye, market, toplum merkezleri), yeni ticari binalarda "mikro-şebekeye hazır" yapı yönetmeliği, zamana göre değişen tarife.
EKSIKLER: Yalnız korelasyon (nedensellik yok); DAC tanımı ABD'ye özgü ve zamanla değişiyor; 2016–2022 arası doğrusal ara değer; potansiyel senaryosu kaba (tek W/m², ayak izi oranı varsayımsal); kurulumların hangi haneye fayda sağladığı ölçülmüyor.
BIZIM PROJEYE:
- Kamu binası ekseninin bilimsel gerekçesi: konut dışı (okul, hastane, itfaiye, kamu) çatılar eşitsizliği azaltmak için KONUTTAN DAHA ETKİLİ bir kaldıraç (açık %38 vs %67). Tezde "neden okul/sağlık binası?" sorusunun cevabı.
- Dayanıklılık argümanı: bataryalı kamu binası PV'si kesintide kritik hizmetleri (sağlık, itfaiye, afet toplanma) sürdürür → İzmir deprem/afet bağlamında (plan belgelerindeki "afet işlevli kamu binaları" katmanı önerimizle birleşir) çok güçlü ek gerekçe.
- UYARI — kullanılabilir alan: ampirik olarak büyük binalarda panel ayak izinin ~%20'si (talep sınırlı). Bizim 0,55/0,70 katsayılarımız TEKNİK üst sınır; fiilî kurulum çok daha düşük olabilir. EPDK "sözleşme gücü" tavanı (belediye/sanayi 2×, diğer 1×) de aynı yönde sınırlayıcı → min(alan tabanlı, tavan) kuralını uygulamanın ampirik dayanağı.
- Senaryo tasarımı (%10/%25/%40 kullanım) → bizim kamu binası potansiyeli için 3 senaryolu raporlama.
- Metrik: Güneş Eşitlik Açığı (göreli fark, bootstrap GA) → Çiğli'de mevcut GES verisi toplanırsa "ihtiyaçlı vs diğer mahalle" açığı bu formülle ölçülebilir; ρ'larımıza bootstrap GA ekleme önerisinin (wiki) ikinci dayanağı.
- Negatif binom sayım regresyonu + bina büyüklük sınıfları → ileride mahalle bazında mevcut PV sayısını açıklayan model için hazır tasarım.
- Microsoft Open Buildings kullanımı → bizim MS↔OSM çapraz kontrolümüzün (MS'in bitişik binaları birleştirmesi) bu tür çalışmalarda da hata kaynağı olduğunu not et.
