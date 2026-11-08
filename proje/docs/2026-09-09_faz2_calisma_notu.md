# Faz 2–3 çalışma notu — 2026-09-09

Bu oturumda defterdeki (Colab'da henüz koşulmamış) hesaplar **yerelde, gerçek veriyle**
koşulur hâle getirildi ve iki metodolojik kusur bulunup düzeltildi. Ayrıca planın
1 numaralı yapısal sorununa (eğim/gölgeleme) somut bir çözüm adayı doğrulandı.

Yeni dosyalar:
- `scripts/faz2_uretim_oncelik.py` — SAM maskeleri → PVGIS üretim bandı → öncelik sıralaması
- `scripts/gsolar_kapsam.py` — Google Solar API kapsam doğrulaması + (anahtar gelince) eğim/azimut yoklaması
- `cache/faz2_tablo.csv`, `cache/faz2_sonuc.geojson`, `cache/pvgis_tablo.json`

---

## 1. Faz 2 sonucu — Evka-5 pilotu, 195 çatı

| | |
|---|---|
| Çatı sayısı (filtre sonrası) | 195 / 202 |
| Toplam çatı alanı | 108.310 m² |
| PVGIS özgül verim (Evka-5) | düz 0° **1.375** · güney 30° **1.573** · kuzey 30° **910** kWh/kWp |
| Kurulu güç bandı | 6.318 – 9.928 kWp |
| **Yıllık üretim bandı** | **6,28 – 13,65 GWh/yıl** |
| Bant genişliği | **üst/alt = 2,18×** |
| Kabaca hane eşdeğeri | ~2.768 hane (3.600 kWh/yıl kabulü) |

PVGIS kaynağı: SARAH3 + ERA5, 2005–2023, ufuk gölgesi DEM'den hesaplı (`use_horizon: true`).

### Neden 202 değil 195
`ayak_alan < 150 m²` olan binalarda SAM alanı ayak izini şişiriyor (yerel bulgu: oran 1,56).
Bu binalarda alan olarak ayak izi kullanılıyor; 25 m² altı ve 8.000 m² üstü 7 kayıt elendi.
Hangi kaynağın kullanıldığı `alan_kaynak` sütununda.

### **2,18× — projenin en dürüst tek sayısı**
Bu bant eğim + azimut bilinmediği için var. Nokta tahmin verilseydi bu belirsizlik
gizlenmiş olurdu. Bant, planın 1 numaralı yapısal sorununun **ölçülmüş hâli**:
"eğim ve gölgeleme tek uydu görüntüsünden çıkarılamaz" cümlesi artık bir iddia değil,
2,18 katlık bir hata payı. Teze bu şekilde girmeli.

Hesap yöntemi: PVGIS 202 bina için değil, mahalle merkezinde 1 (düz) + 13 (30° × 30°'lik
yön ızgarası) = **14 sorgu** ile sorulup interpolasyonla dağıtıldı. 1,2 km'lik pilot alanda
özgül verim pratikte sabit olduğu için bu geçerli ve savunulabilir bir kısayol.

---

## 2. Faz 3 sonucu — ve bulunan iki kusur

### Kusur A: min-max normalizasyon aykırı binaya teslim oluyordu
6.380 m²'lik tek bir bina (573 MWh/yıl) teknik skorun tavanını belirliyor; geri kalan
binaların %95'i 0–0,1 aralığına sıkışıyordu. Bu hâlde ağırlıklar sıralamayı
değiştiremiyor, duyarlılık analizi de yanlış olarak "sağlam" görünüyordu.
→ **Sıra-tabanlı (yüzdelik) normalizasyona geçildi**, min-max karşılaştırma için korundu.

Etkisi somut: min-max ile ilk sıra dev bina; yüzdelik ile ilk 4 sıra kamu binaları
(Gülen KORA Ortaokulu, Yıldız Tınas İzmiroğlu Anadolu Lisesi, iki isimsiz kamu yapısı,
ardından Evka-5 Sağlık Ocağı). Projenin **ayırt edici iddiası ancak bu normalizasyonla
çalışıyor** — yani bulgu "AHP ağırlıkları" değil, normalizasyon seçimi.

Aynı ağırlıkta iki normalizasyonun ilk-20'si 19/20 örtüşüyor ama **tepe sıralar tamamen
farklı** — tez metninde bu ayrım yazılmalı, tek bir Kendall tau sayısı bunu gizler.

### Kusur B: tek mahallede toplumsal katman ayrım üretmiyor
Ağırlık taraması (1,00/0,00 → 0,40/0,60) Kendall tau'yu ancak 0,84'e indiriyor.
Sebep yapısal:
1. **SEGE ilçe kademesinde** — tek mahallelik pilotta sabit, hiç ayrım üretmiyor.
2. Toplumsal katman şu an **ikili bayrak** (kamu binası mı, değil mi) ve 195 çatının
   yalnızca **5'i** kamu. 5 satırlık bir sinyal ağırlıklandırmayı anlamlı kılamaz.

**Sonuç:** projenin ana iddiası ("teknik uygunluk + toplumsal ihtiyaç") mevcut pilot
kurgusunda kanıtlanamaz. İki çıkıştan biri seçilmeli:
- **(a)** Pilotu **en az 3–4 farklı SEGE kademesinden ilçeye** yaymak (örn. Çiğli / Konak /
  Karabağlar / Çeşme) — SEGE o zaman gerçekten değişken olur. *Önerilen.*
- **(b)** Toplumsal katmanı zenginleştirmek: bina başına hizmet ettiği nüfus, öğrenci
  sayısı (MEB), bina yaşı, mahalle bazlı elektrik tüketimi.

Bu, danışmana sorulacak "pilot bölge kaç mahalle olsun?" sorusunun cevabıdır:
**tek mahalle yetmez, ve bu artık bir tahmin değil ölçülmüş bir sonuç.**

---

## 3. Google Solar API — D5/D6 için doğrulanmış çözüm adayı

`cache/gsolar_*.geojson` kapsam poligonları üzerinde nokta testi:

| Konum | Google Solar veri kalitesi |
|---|---|
| **Evka-5 (27,0532 · 38,5185)** | **MEDIUM** |
| **İzmir merkez** | **MEDIUM** |
| Ankara | kapsam dışı |
| İstanbul | kapsam dışı |

İki sonucu var:

1. **D5 (180° azimut belirsizliği) ve D6 (eğim yok) çözülebilir.**
   `buildingInsights` ucu bina başına `roofSegmentStats` döndürüyor: her segment için
   `pitchDegrees`, `azimuthDegrees`, alan ve gölgeleme. Bunlar bizde olmayan tam iki
   bileşen. 2,18× bant buna bağlı olarak daralır.
2. **İzmir pilot seçimi artık gerekçeli.** Ankara ve İstanbul kapsam dışı; İzmir
   Türkiye'de kapsanan ender illerden. Tezde "pilot neden İzmir" sorusuna verilecek
   cevap sadece "yakınlık/açık veri" değil, "Google Solar kapsamındaki nadir illerden biri".

**Yapılacak:** Google Cloud'dan Solar API anahtarı alınıp
`GOOGLE_SOLAR_API_KEY=... python scripts/gsolar_kapsam.py --n 3` koşulacak.
Betik, Google'ın azimutuyla bizim SAM mahya eksenimizi karşılaştırıp eksen farkını
raporluyor — yani aynı anda hem eksiği kapatan veri hem de SAM çıkarımının doğrulaması.

**Dikkat:** buildingInsights ücretli (aylık ücretsiz kota var). Önce 3 bina ile denenmeli,
toplu koşudan önce fiyatlandırma okunmalı. Ayrıca lisans şartları teze girmeden
okunmalı — `indir_goruntu.py` üstündeki D0 uyarısıyla aynı dikkat.

---

## 4. Bir sonraki adımlar

1. Solar API anahtarı al, `gsolar_kapsam.py --n 3` koş. (D5+D6 kapanır)
2. Pilotu çok ilçeye yay — SEGE'nin ayrım üretebilmesi için. (Faz 3'ün ön koşulu)
3. SEGE 2022 ilçe tablosunu tarayıcıdan elle indir (`sanayi.gov.tr` bot erişimini reddediyor).
4. Colab defterini koş — D1/D2 (ViT-B ve MobileSAM karşılaştırması) hâlâ koşulmadı;
   defterdeki hücrelerin `execution_count`'ları boş.
5. Kapsam kararı: mobil katman (React Native) hâlâ planda ve hâlâ akademik katkı üretmiyor.
