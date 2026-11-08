# Derin inceleme — Pino-Gallardo, Bastida-Molina, Gómez-Navarro & Montagud-Montalvá (2026)

**Künye:** Towards realistic urban rooftop solar photovoltaic large-scale planning: integrating AI-based roof detection, 3D geometry, and energy modelling. *Engineering Science and Technology, an International Journal* 80, 102437. doi:10.1016/j.jestch.2026.102437. Çevrimiçi yayın 23.06.2026, CC BY-NC-ND, 18 sayfa.
**Bağlam:** SDEWES 2025 (Dubrovnik) bildirisinin (SDEWES2025.00243) genişletilmiş sürümü, özel sayıda yayımlandı. Ekip Universitat Politècnica de València'dan (UPV). Aynı ekibin Valencia hakkında önceki çalışmaları var: Gómez-Navarro 2021, Cuesta-Fernández 2023, Illa Perduda [31]. Yani tek seferlik bir makale değil, süren bir araştırma hattı.

## 1. Sorun ve iddia
- Sorun: Basit yöntemler (alan × ortalama verim) potansiyeli abartıyor. Tespit, geometri ve PV tasarımı birbirinden kopuk yapılıyor.
- Saptanan 3 boşluk: (I) uçtan uca bütünleşik akış yok, (II) otomatik tespit ile PV tasarımı birbirine bağlanmıyor, (III) ölçeklenebilirlik ve yeniden üretilebilirlik zayıf.
- 4 katkı: uçtan uca yöntem · yapay zekâ + CBS + LiDAR birlikte · otomatik ve gerçekçi panel yerleşimi + yıllık üretim · modüler ve tekrarlanabilir yapı.
- Tablo 1'de 16 çalışmayı karşılaştırıyorlar. Hiçbirinde "AI + LiDAR + detaylı PV tasarımı + ölçeklenebilirlik" bir arada yok. Kendilerini bu boşluğa yerleştiriyorlar.

## 2. Veri
| Katman | Kaynak | Çözünürlük / not |
|---|---|---|
| Ortofoto | PNOA (CNIG), 4 mozaik | 0,25 m/piksel |
| LiDAR | PNOA 2015, 46 karo (2×2 km) | **0,5 nokta/m²** (seyrek) |
| Ayak izi + tipoloji + yapısal durum | Kadastro (Inspire Downloader) | "harabe" sınıfı var |
| Mahalle sınırı | Belediye açık veri | 87 birim |
| Üretim | PVGIS API | konfigürasyon başına sorgu |
Donanım: i9-13900KF, 32 GB RAM, RTX 3060 12 GB. Yalnız açık veri ve özgür yazılım kullanılmış.

## 3. Yöntem (5 modül)
1. **GeoDataPrep:** Koordinat sistemi denetimi yapılıyor. LiDAR'dan DEM, eğim ve bakı katmanları türetiliyor. Şehir mahallelere bölünüyor. **Ayak izinden kutu istemi (bounding box)** üretiliyor.
2. **RoofScan:** SAM ince ayarla eğitiliyor. Pozitif sınıf **engelsiz, PV'ye uygun çatı yüzeyi**. Maskeler morfolojik aşınma/genişletme ile temizlenip vektöre çevriliyor, sonra ayak iziyle kesiştiriliyor.
   - Eğitim verisi: 36 elle etiketli 1280×1280 çift. Döndürme/aynalama ile 108'e çıkarılıyor. 9 çift doğrulamaya ayrılıyor.
   - Test: 12 adet 512×512 karo (LabelMe ile etiketlenmiş). **Kutu istemi yer gerçeğinden türetiliyor.**
   - Hazır SAM: IoU 0,13 · F1 0,22 · kesinlik 0,33 · duyarlılık 0,19 · doğruluk 0,61.
   - İnce ayarlı SAM: IoU 0,52 · F1 0,68 · kesinlik 0,53 · **duyarlılık 0,96** · doğruluk 0,71.
   - Bilinçli tercih: duyarlılık yüksek tutuluyor, yanlış pozitifleri sonraki filtrelerin temizlemesi bekleniyor.
3. **SolarCompute:** LiDAR'da her ayak izinde düzlem tespiti yapılıyor, düzlem başına eğim ve bakı çıkıyor. GRASS `r.sun.insoltime` ile 365 günlük ışınım haritası üretilip yıllık ortalamaya indiriliyor. **Binalar arası dinamik gölge yok**, yalnız arazi gölgesi var.
4. **PVLayout (filtre zinciri, bu sırayla):**
   1. 0,60 m çevre bakım koridoru
   2. Işınım ≥ 1.000 kWh/m²·yıl (IDAE)
   3. Yükseklik ≥ 5 m
   4. Kadastroda "harabe" olanlar elenir
   5. Eğim ≤ 40° (Teknik Yapı Kodu)
   6. Eğim > 3° ise kuzeye bakan yüzler elenir
   7. Alan ≥ 10 m² (eğimli çatıda gerçek alana çevrilerek)

   **Yerleşim:**
   - Eğimli çatı: panel çatı düzlemine yatırılıyor, yön optimizasyonu yapılmıyor.
   - Düz çatı: önce 35° güney deneniyor. Sonra {20°, 35°} × azimut 90–270° (15° adım) = 26 konfigürasyon taranıyor. Sıra aralığı d = h / tan(61° − φ). Her konfigürasyon PVGIS'e soruluyor, **en yüksek yıllık üretimi veren** seçiliyor.
   - Paneller arası boşluk 5 cm.
5. **DataIntegrator:** Bina bazında CSV, mahalle özetleri, genel özet ve CBS katmanları üretiyor.

Yapısal uygunluk dolaylı yoldan ele alınıyor: "harabe" eleniyor, PV yükünün 15–30 kg/m² olduğu ve normal tasarım payı içinde kaldığı varsayılıyor (NREL). Sonuç bölümünde bu değer 12–20 kg/m² olarak geçiyor, yeşil çatıda ise 60–150 kg/m².

## 4. Bulgular
**Alan hunisi:**
| Aşama | m² | Toplam çatıya oranı |
|---|---|---|
| Toplam çatı | 18.405.212 | %100 |
| Engelsiz yüzey (SAM) | 8.937.088 | %48,6 |
| Tüm filtrelerden sonra uygun | 2.670.079 | **%14,6** (engelsizin ~%30'u) |
- Sonuç: 342.785 modül · 173 MW · 270 GWh/yıl (≈1.561 kWh/kWp, modül başına ≈505 W).
- Uygun alanın kullanım türüne göre dağılımı: konut %69 · **kamu %15** · ticaret %6.
- Düz çatıların ortalama %79,8'i uygun. Ciutat Universitària'da %96,9, tarihî El Mercat'ta %42.
- Modüllerin %78'i düz çatılarda. Yalnız %1,4'ü "optimum" açıda (35° ve güney). **Az sayıda optimum açılı panel yerine çok sayıda optimum olmayan panel toplamda daha fazla enerji üretiyor.**
- En yüksek mahalleler Benimamet (8,39 MW), Benicalap (8,02) ve La Carrasca (6,57). En düşük El Mercat (0,38 MW).
- m²/kWp karşılaştırması: İspanya 5,86 · Illa Perduda 7,22 · Lizbon 8,61 · Ludwigsburg 16,89 · İsviçre 19,28.

## 5. Eleştirel okuma (notlarda olmayan, tam metinden çıkan tespitler)
1. **Denklem 1 ters yazılmış.** Makalede A = B·cos θ ("düzeltilmiş alan = izdüşüm × cos θ") yazıyor. Eğimli yüzeyin gerçek alanı izdüşümden büyüktür, yani A = B / cos θ olmalı. Formül uygulandığı haliyle kullanıldıysa eğimli çatı alanı küçülmüş, yani muhafazakâr bir sapma var. Atıf yaparken doğru formülü kullan, makaledekini kopyalama.
2. **Mahalle ortalamaları 87 mahalleyle tutmuyor.** Bildirilen ortalamalar 4.738 modül, 2,40 MW, 3,75 GWh ve 37.059 m². Toplamlardan geri hesaplanınca hep **~72 mahalle** çıkıyor (342.785/4.738 = 72,3; 173/2,40 = 72,1; 2.670.079/37.059 = 72,0). 15 mahallenin neden dışarıda kaldığı (veri eksikliği, kırsal alan?) açıklanmamış.
3. **Mahalle alanları iki yerde farklı veriliyor.** §4.1'de Benicalap 130.626 m², Benimamet 118.817 m². §4.2'de aynı mahalleler için "toplam uygun alan" 331.409 ve 312.084 m². İki rakam arasında 2,5 kat fark var ve hangisinin hangi alan olduğu tanımlanmamış.
4. **Kendi m²/kWp oranlarını vermiyorlar.** Hesaplayınca 2.670.079 m² / 173.000 kWp = **15,4 m²/kWp** çıkıyor. Bu değer Tablo 5'teki aralığın üst ucunda (5,86–19,28). Aynı şehirdeki Illa Perduda çalışmasının 7,22'sinin iki katı. "Literatürle tutarlı" deniyor ama aralık 3,3 kat geniş olduğu için bu ifade fazla bir şey söylemiyor.
5. **SAM testi iyimser.** Kutu istemleri gerçek akıştaki kadastro ayak izinden değil, **yer gerçeği maskesinden** türetilmiş. Sahada kutu ile çatı tam örtüşmeyeceği için başarım düşer. Test seti küçük: 12 karo, ~3 milyon piksel. Bina sayısı ve güven aralığı verilmemiş.
6. **Hazır SAM'in 0,13 IoU'su yanıltıcı olabilir.** Bu sonuç bir model sınırından çok **görev tanımı uyuşmazlığından** kaynaklanıyor olabilir. Hedef "engelsiz yüzey" iken hazır SAM kutu içinde en belirgin nesneyi seçiyor. Duyarlılığın 0,19 olması kutunun sadece küçük bir parçasını seçtiğini gösteriyor. Hangi çoklu-maske çıktısının alındığı da yazılmamış.
7. **İnce ayarın ayrıntıları yok.** SAM sürümü (ViT-B/L/H), epoch sayısı, öğrenme oranı, kayıp fonksiyonu ve dondurulan katmanlar belirtilmemiş. "Yeniden üretilebilir" iddiası depoya [26] dayanıyor ama metin tek başına yeniden üretime yetmiyor.
8. **Gölge konusunda kendi içinde çelişki var.** §2.3.2'de "binalar arası gölge modellenmiyor" deniyor. Sonuç bölümünde ise "kentsel gölge etkilerini hesaba katan yüksek çözünürlüklü ışınım haritaları" deniyor. Doğrusu §2.3.2'deki ifade.
9. **LiDAR çok seyrek.** 0,5 nokta/m² ile 10 m²'lik bir çatı düzleminde ~5 nokta kalıyor, küçük çatılarda düzlem tespiti güvenilmez. Ayrıca LiDAR 2015 tarihli, ortofotonun yılı ise belirtilmemiş. Arada yıkılan veya yeni yapılan binalar uyumsuzluk yaratır.
10. **"Kuzeye bakan" tanımlanmamış.** Azimut aralığı verilmemiş (örneğin 270–90°? 292,5–67,5°?).
11. **Belirsizlik analizi yalnız sözel.** Duyarlılık analizi ve bant verilmemiş, sayısal belirsizlik "gelecek çalışma"ya bırakılmış.
12. **Ekonomi, şebeke ve toplumsal boyut yok.** "Mahallelerin önceliklendirilmesine destek" deniyor ama sıralama yalnız teknik büyüklüğe göre yapılıyor.

## 6. Bizim projeye çevirisi
**Ortak noktalar:** Ayak izinden kutu istemiyle SAM · ayak iziyle kesişim · PVGIS ile konfigürasyon taraması · mahalle bazında raporlama · kamu payının ayrıca gösterilmesi.

**Farklarımız (özgünlük):**
| | Pino-Gallardo 2026 | Bizim proje (Çiğli) |
|---|---|---|
| 3B veri | LiDAR (Türkiye'de açık LiDAR yok) | Yok → gölgeden yükseklik + fotometrik eğim bandı |
| SAM | İnce ayarlı (36 etiket) | Sıfır atış, eğitim yok |
| Binalar arası gölge | Yok | Var |
| Belirsizlik | Sözel | Bant (alt–üst) |
| Önceliklendirme | Teknik büyüklük | Uygunluk + toplumsal ihtiyaç (iki katmanlı KDS) |
| Açıklama | Metin özeti | LLM açıklaması (karar vermiyor) |

**Tezde kullanılabilecek özgünlük cümlesi:**
> "Ayak izinden türetilen kutu istemiyle SAM kullanımı Pino-Gallardo vd. (2026) tarafından LiDAR ve ince ayarlı model ile gösterilmiştir. Bu çalışma aynı istem stratejisini açık LiDAR verisinin bulunmadığı bir bağlamda, ince ayar gerektirmeden uygular; eksik 3B bilgiyi gölge tabanlı yükseklik ve eğim bandıyla telafi eder ve teknik potansiyeli toplumsal öncelik katmanıyla birleştirir."

**Yapılacaklar (öncelik sırasıyla):**
1. **Çiğli için aynı alan hunisini çıkar:** toplam çatı → (engel payı düşülmüş) → filtre sonrası uygun alan. Valencia'nın %14,6'sıyla yan yana koy. Jürinin ilk soracağı karşılaştırma bu olacak.
2. **Sıkı filtre senaryosunu kodla.** Eşikler bu makaleden atıflı alınabilir: 0,6 m koridor · ≥1.000 kWh/m² · ≥5 m yükseklik · ≤40° · >3° ise kuzey eleme · ≥10 m². Mevcut sonucu "teknik üst sınır", sıkı filtre sonucunu "gerçekçi alt sınır" olarak sun.
3. **IoU ölçümünü aynı protokolle yap:** LabelMe ile elle çizim, pikselde IoU/F1/kesinlik/duyarlılık. Kutuları **gerçek akıştaki ayak izinden** üret, yani onlardan daha dürüst bir test kur. Bu farkı tezde açıkça belirt.
4. Eğim düzeltmesinde **B / cos θ** kullan ve dipnotta makaledeki yazım hatasına değinmeden doğru formülü kaynakla (örneğin trigonometri ya da Freitas 2015).
5. Sıra aralığı: Çiğli'de (φ ≈ 38,5°) d ≈ 2,41·h. Düz çatı kullanılabilirlik katsayımız 0,55'i bununla sına.
6. "Çok panel > optimum açı" bulgusu düz çatıda düşük eğim / yatay alt bant kullanımımızı destekliyor.
7. Kamu payını Valencia'nın %15'iyle karşılaştır.

**Jürinin sorabileceği sorular ve hazır cevaplar:**
- *"Bu yöntem zaten yayımlanmış değil mi?"* → Evet, istem stratejisi yayımlanmış. Bu yöntemin meşruiyetini gösteriyor. Bizim katkımız LiDAR'sız bağlam, gölge/yükseklik ve toplumsal katman.
- *"Neden ince ayar yapmadınız?"* → Etiketli Türkiye verisi yok. Amacımız sıfır atışın sınırlarını ölçmek. Ayrıca bizim hedefimiz çatı sınırı, onlarınki engelsiz yüzey; bu yüzden 0,13 değeri bize doğrudan uygulanamaz. Bunu IoU ölçerek göstereceğiz (yapılacak 3).
- *"Potansiyeliniz Valencia'nın 7–10 katı yoğunlukta, neden?"* → Bizim değerimiz engel ve filtre öncesi teknik üst sınır. Sıkı filtre senaryosu ile aradaki fark kapanıyor (yapılacak 1–2).

## 7. Atatürk OSB pilotuna bağlantı (2026-10-01)
**Mevcut OSB sonucu (Çiğli koşusu, 2026-09-12):** 1.412 çatı · 2,12 km² · eğimli çatı payı yalnız %19,2 · gölge kaybı %2,27 · 169–193 MWp · 230–294 GWh/yıl. Brüt çatı başına yoğunluk 11,0–12,5 m²/kWp. Valencia'da bu değer 106 m²/kWp.

**Pino parametreleriyle kaba "gerçekçi" kontrol:** 2,12 km² × (1 − engel payı 0,15–0,25) × düz çatı uygunluk oranı 0,798 × Valencia'daki uygun alan yoğunluğu 0,0648 kWp/m² = **~82–93 MWp**. Bu, mevcut üst sınırımızın yaklaşık yarısı. Hesap kaba ve yalnız büyüklük mertebesini kontrol etmek için.

**Doğrudan aktarılabilenler:**
- Düz çatı yerleşim algoritması: eğim taraması + IDAE sıra aralığı + PVGIS ile en yüksek üretimin seçilmesi. OSB'nin ~%81'i düz çatı.
- "Çok panel > optimum açı" bulgusu: büyük düz çatılarda düşük eğim ya da doğu-batı sık dizilim.
- Huni tablosu ve bina bazında CSV: OSB yönetimine firma/parsel düzeyinde çıktı verilebilir.
- Yükseklik ≥5 m filtresi OSB'de sorun yaratmaz. "Harabe" filtresinin OSB'deki karşılığı atıl veya inşaat halindeki tesisler.

**Aktarılamayanlar / uyarılar:**
- **Yapısal yük varsayımı:** "15–30 kg/m² normal güvenlik payı içinde" varsayımı betonarme konut için. Hafif çelik sac sanayi çatısı için geçerli değil; tezde açık sınırlılık olarak yazılmalı.
- **3° kuralı:** Trapez sac çatılar genelde 3–10° eğimli. Pino'nun kuralı bunları "eğimli" sayar ve kuzey yarıyı siler. Bu iki senaryo olarak hesaplanmalı.
- **Engeller:** OSB'de ışıklık bantları, havalandırma ve baca var; bizde engel tespiti yok. OSB için en büyük belirsizlik bu.
- **Yansıtıcı malzeme:** Pino ince ayar gerekçesi olarak parlak/yansıtıcı malzemeyi gösteriyor. Sac çatılarda sıfır atış SAM başarımı OSB'de ayrıca ölçülmeli.
- Mevcut haritada boyalı sacın kiremit olarak etiketlenmesi hatası OSB'de eğim sınıflamasını doğrudan bozuyor.

**Özgünlük:** Pino sektör dağılımı veriyor (konut/kamu/ticari/tarım) ama sanayi ayrı bir kategori değil ve OSB yok. Sanayi bölgesi ölçeğinde SAM tabanlı, LiDAR'sız ve mevzuat tavanlı (EPDK, sanayide 2× sözleşme gücü) bir çalışma, bu makalenin dokunmadığı bir alan.
