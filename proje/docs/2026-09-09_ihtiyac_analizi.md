# Pilot bölge ihtiyaç analizi — Evka-5 / Çiğli / Seyrek / Balatçık

**Tarih:** 2026-09-09 · **Amaç:** bir sonraki toplantıda bölge seçimini kanıta bağlamak.

Sorulan dört aday için mahalle kademesinde ölçülebilir bir karşılaştırma yapıldı.
Kullanılan veriler ve üretilen betikler bu belgenin sonunda.

---

## 0. Önce üç kritik tespit

**1) Seyrek idari bir mahalle değil.** Ne İzmir BB bina sayısı, ne nüfus, ne su tüketimi,
ne askıda fatura veri setinde satırı var; OSM'de de sınır ilişkisi yok. Nominatim onu
Menemen'in **Gazi Mustafa Kemal Mahallesi** içinde konumluyor. Seyrek bir *semt*, analiz
birimi değil. Pilot olarak seçilirse resmî hiçbir mahalle istatistiği kullanılamaz —
ya bağlı olduğu mahalle üzerinden çalışılır ya da kendi sınırı elle çizilir.

**2) SEGE tablosu senin gönderdiğin PDF'in içindeydi.** Planda "sanayi.gov.tr bot erişimini
reddediyor, elle indirilmeli" diye açık iş olarak duran SEGE 2022 ilçe verisi,
`Izmir_Mevcut_Durum_Analizi` s.36–37, Tablo 1.7'de tam hâliyle var (2004 / 2017 / 2022).
30 ilçe için çıkarıldı → `cache/izka/sege_ilce.json`. **Bu tıkanıklık kapandı.**

**3) SEGE'nin ilçe kademesinde kalması artık sorun değil.** İzmir BB açık veri portalında
**mahalle kademesinde** iki ihtiyaç vekili bulundu: askıda fatura başvurusu ve konut su
tüketimi/abone. Faz 3'te bulunan "tek mahallede toplumsal katman ayrım üretmiyor" sorununun
çözümü bu — ama aşağıdaki uyarılarla.

---

## 1. Dört adayın karşılaştırması

| | **Evka-5** | **Balatçık** | **Seyrek** (Menemen/GMK) | **Çiğli** (26 mahalle) |
|---|---|---|---|---|
| Nüfus | 12.945 | 18.254 | 2.834 | 215.160 |
| MS bina ayak izi | 204 | 1.110 | 575 | 15.872 |
| Resmî yapı (İzmir BB) | 169 | 1.774 | 340 | — |
| Çatı alanı | 9,7 ha | 54,1 ha | 17,6 ha | 537,9 ha |
| **Çatı alanı / kişi** | **7,5 m²** | 29,6 m² | 61,9 m² | 25,0 m² |
| Askıda fatura /1000 kişi | 4,0 | 3,3 | 2,5 | 0,2 – 8,2 |
| Su tüketimi (m³/abone/ay) | 9,3 | 11,9 | 7,2 | 8,1 – 20,7 |
| OSM kamu binası | 5 | 12 | 0 | 80 |
| SEGE 2022 | Çiğli · 1. kademe (skor 2,046 · TR 41) | aynı | Menemen · 2. kademe (0,838 · TR 156) | 1. kademe |
| Google Solar kapsamı | MEDIUM | MEDIUM | MEDIUM | MEDIUM |
| MobileSAM CPU süresi | 0,8 dk | 4,5 dk | 2,3 dk | **64,5 dk** |
| Kaba üretim potansiyeli | 12,2 GWh/yıl | 69,5 GWh/yıl | 23,0 GWh/yıl | 687 GWh/yıl |

**Evka-5 dört aday içinde en zayıf teknik zemin:** en küçük çatı stoku ve **kişi başına en az
çatı** (7,5 m²). Yüksek katlı toplu konut dokusu; 12.945 kişi 204 binada oturuyor
(bina başına ~63 kişi). Zaten işlenmiş olması onu iyi bir **kalibrasyon/doğrulama sahası**
yapar, ama pilotun tamamı olarak dar.

**Balatçık** tek mahalle olarak en dengelisi: Evka-5'in 5,6 katı çatı alanı, 12 kamu binası
(Ataşehir'den sonra ilçenin ikincisi), 18 bin nüfus.

---

## 2. Asıl soru: hangi kapsam "ihtiyaç" değişkeninde ayrım üretiyor?

Faz 3'te bulunan sorun şuydu: ağırlıkları değiştirmek sıralamayı değiştirmiyorsa,
"toplumsal öncelik" iddiası boşta kalıyor. Ölçüldü — İzmir'in **974 mahallesi** üzerinde
(nüfus ≥ 300), askıda fatura/1000 kişi dağılımına göre:

| Senaryo | Birim | askıda/1000 aralığı | Değişkenlik (CV) | SEGE kademesi |
|---|---|---|---|---|
| A) Yalnız Evka-5 | 1 | — | **ayrım yok** | 1 |
| B) Yalnız Balatçık | 1 | — | **ayrım yok** | 1 |
| C) Yalnız Seyrek | 1 | — | **ayrım yok** | 2 |
| **D) Çiğli ilçesi** | **26** | 0,2 – 8,2 | **0,52** | 1 |
| E) Çiğli + Menemen | 78 | 0,0 – 8,5 | 0,81 | 1, 2 |
| F) Konak+Çiğli+Menemen+Bergama+Kiraz | 265 | 0,0 – 10,3 | 1,13 | 1,2,3,5 |
| G) İzmir geneli (üst sınır) | 974 | 0,0 – 12,0 | 1,21 | 1–5 |

**Sonuç:** tek mahalle sıfır ayrım üretiyor — üç adayın üçü de. Ama **Çiğli ilçesinin kendi
26 mahallesi zaten 41 kat aralık ve CV 0,52 taşıyor**, yani İzmir genelindeki değişkenliğin
%43'ü. İlçeyi terk etmeye gerek yok; **mahalleyi terk etmek yeterli.**

Bu, ilk bulgumun düzeltilmesi: sorun "tek ilçe" değil, "tek mahalle" idi.

### Adaylar İzmir dağılımının neresinde
- **Evka-5** — askıda/1000 = 4,0 → **%93 yüzdelik**
- **Balatçık** — 3,3 → %89 yüzdelik
- **Seyrek (GMK)** — 2,5 → %80 yüzdelik

Üçü de İzmir'in en ihtiyaçlı %20'lik diliminde. Aday seçimi bu açıdan isabetli.
Ayrıca **Çiğli/Güzeltepe (8,2)**, nüfusu 2.000 üstü mahalleler arasında **İzmir'in en
ihtiyaçlı ikinci mahallesi** — yani en güçlü vaka zaten aday ilçenin içinde.

---

## 3. İki bulgu — biri projenin skor formülünü doğrudan ilgilendiriyor

Çiğli'nin 26 mahallesi üzerinde sıra korelasyonu (Spearman):

| İlişki | ρ | Yorum |
|---|---|---|
| Su tüketimi/abone ↔ çatı alanı/kişi | **+0,59** | Varlıklı mahallede kişi başına daha çok çatı var |
| Askıda fatura/1000 ↔ çatı alanı/kişi | −0,19 | Zayıf, aynı yönde |
| **Askıda fatura/1000 ↔ kamu binası/1000** | **−0,47** | **İhtiyaçlı mahallede kamu binası daha az** |

**Birinci satır projenin tezini destekliyor:** çatı kaynağı gelirle birlikte artıyor.
Sunter ve ark. (Nature Sustainability, 2019) rooftop-solar eşitsizliği bulgusunun
İzmir'deki karşılığı — kaynak listesinde zaten var, artık kendi verimizle ölçtük.

**İkinci satır ise projenin skor formülünde bir hata olduğunu söylüyor.** Faz 3'te toplumsal
katman "kamu binası mı?" ikili bayrağıydı. Ama kamu binası yoğunluğu ihtiyaçla **ters**
korele: en ihtiyaçlı Güzeltepe'de 0, İnönü'de 0 kamu binası varken, düşük ihtiyaçlı
Ataşehir'de 22 var. Yani **kamu binasına öncelik veren skor, yatırımı sistematik olarak
ihtiyaçlı mahallelerden uzaklaştırıyor.** Bu, formülün düzeltilmesi gereken bir kusuru:
kamu binası ayrı bir *erişim* ekseni olarak tutulmalı, "toplumsal ihtiyaç" ile aynı terime
konmamalı.

---

## 4. Veri bütünlüğü uyarısı — pilot seçimini doğrudan etkiliyor

Microsoft ayak izi sayısı / resmî yapı sayısı oranı Çiğli içinde **0,27 ile 2,97 arasında**:

| Mahalle | oran | OSM / resmî |
|---|---|---|
| Kaklıç | 2,97 | 1.880 / 632 |
| Cumhuriyet | 2,22 | 449 / 202 |
| Sasalı Merkez | 1,42 | 2.409 / 1.702 |
| *Evka-5* | *1,21* | *204 / 169* |
| Balatçık | 0,63 | 1.110 / 1.774 |
| Yeni Mahalle | 0,43 | 563 / 1.319 |
| Küçük Çiğli | 0,34 | 746 / 2.182 |
| **Evka-2** | **0,27** | **299 / 1.103** |

İki yönlü hata: kırsal mahallelerde (Kaklıç, Sasalı) **sera/ahır/müştemilat bina sayılıyor**,
yoğun apartman mahallelerinde (Evka-2, Küçük Çiğli) **binaların çoğu kaçıyor**. Kaklıç'ın
456 m²/kişi çatı alanı bu yüzden gerçek değil.

Pilota etkisi: apartman dokulu — yani sosyal olarak asıl ilginç olan — mahalleler MS ayak
iziyle sistematik olarak eksik temsil ediliyor. Çiğli ölçeğine çıkılacaksa **OSM ile
çapraz kontrol veya ikinci bir ayak izi kaynağı zorunlu.** Evka-5'te oran 1,21 olduğu için
bu sorun şimdiye kadar görünmedi.

---

## 5. Askıda fatura verisinin sınırı (dürüst kayıt)

- Veri **fiilen 2020 yılına ait**: 5.754 kayıt 2020'de, yalnızca 11 kayıt 2021'de.
- Portal tanımı: *"Pandemi sürecinde askıya bırakılan ve askıdan alınan (ödenen) su
  faturalarının ilçe ve mahalle bazında dağılımı."* Yani **su faturası dayanışma programı**,
  doğrudan enerji yoksulluğu ölçüsü değil.
- Başvuru sayısı hem ihtiyacı hem **programdan haberdar olmayı** ölçer (seçilim yanlılığı).
- Lisans: İzmir BB Açık Veri Lisansı. Nüfus setinin lisansı "belirtilmemiş".

Bu yüzden tezde **tek başına** gelir/ihtiyaç göstergesi yapılmamalı; su tüketimi/abone
(2023, tam yıl) ile birlikte ve sınırları yazılarak kullanılmalı. Danışmana sorulacak:
mahalle kademesinde daha güncel bir yoksunluk göstergesi (ör. sosyal yardım kayıtları,
MEB ücretsiz ders kitabı/taşımalı eğitim, TEDAŞ tüketim kademesi) erişilebilir mi?

---

## 6. İZKA belgelerinden çıkan politika dayanağı

**2024-2028 İzmir Bölge Planı, Hedef 1.4 (s.65-66)** projeyi doğrudan adlandırıyor:

> "Temiz enerji üretimini desteklemeye yönelik pilot uygulamalar (enerji kooperatifleri,
> **çatı kurulumları** gibi enerji üreten sistemler) yapılacaktır."

> "hane halkının farkındalık düzeyi arttırılarak yeşil bina ve **üreten tüketici (prosumer)**
> uygulamaları yaygınlaştırılacak, ... güneş enerjisi santrali kurulumuyla ilgili
> **sübvansiyon programları** uygulanacaktır."

Yani tez, "olsa iyi olurdu" diye bir araç önermiyor; **yürürlükteki bölge planının taahhüt
ettiği bir tedbirin hedeflemesini** yapıyor. Giriş bölümünün gerekçesi bu paragraf olmalı.

Diğer kullanılabilir veriler:
- İzmir GES kurulu gücü **322,8 MW**, Türkiye'de 5. sıra, ülke toplamının %3,6'sı
  (Mevcut Durum Analizi s.248).
- Çiğli **"ağırlıklı kentsel"** ilçe kategorisinde (Bölge Planı s.90); metropoliten
  merkez alanı içinde.
- 1/25.000 Çevre Düzeni Planı **Çiğli-Menemen koridorunu** kuzey gelişme aksı olarak
  öneriyor (s.125) — iki ilçeyi birlikte almanın plan literatüründe karşılığı var.
- Çiğli nüfusu 2007→2022 %39,5, Menemen %60,1 artmış (İzmir'in en hızlısı) — yeni yapı
  stoku, çatıların yaşı görece genç.
- Çiğli'de geçici koruma altındaki nüfus 1.333 (%0,92); Konak 35.587, Karabağlar 29.971.

---

## 7. Öneri

**Pilot = Çiğli ilçesi, 26 mahalle.** Gerekçe:

1. Tek mahalle sıfır ayrım üretiyor; Çiğli'nin 26 mahallesi İzmir'deki ihtiyaç
   değişkenliğinin %43'ünü tek başına taşıyor (CV 0,52).
2. İşlem yükü gerçekçi: 15.872 bina, MobileSAM ile CPU'da **~65 dakika**. GPU gerekmiyor.
3. İzmir'in en ihtiyaçlı ikinci mahallesi (Güzeltepe) ilçenin içinde — en güçlü vaka elde.
4. Tamamı Google Solar MEDIUM kapsamında → D5/D6 çözümü tüm pilota uygulanabilir.
5. Evka-5 zaten işlenmiş; ilçe içinde **doğrulama sahası** olarak kalır, boşa gitmez.

**Menemen ikinci ilçe olarak eklenmeli** — SEGE 2. kademe getirir, değişkenliği 0,52'den
0,81'e çıkarır, Çevre Düzeni Planı'nın Çiğli-Menemen koridoruyla örtüşür ve Seyrek'i
kapsam içine alır. Maliyeti ~90 dakika ek işlem.

**Seyrek tek başına pilot olmamalı** — idari birim değil, resmî istatistiği yok.
Menemen'in içinde bir vaka olarak incelenebilir.

Karşı görüş, dürüstlük payı: Çiğli'nin tamamı **tek SEGE kademesi**. Danışman "gelişmişlik
farkı görmek istiyorum" derse Çiğli tek başına yetmez; o zaman F senaryosu (Konak + Çiğli +
Menemen + Bergama + Kiraz, CV 1,13) gerekir — ama işlem yükü ve saha bilgisi ciddi şekilde
artar.

## 8. Toplantıdan önce yapılacaklar

1. Danışmana sorulacak: gelişmişlik farkı **ilçeler arası** mı görülmeli, yoksa **mahalleler
   arası** ayrım yeterli mi? Cevap D ile F arasında seçim yaptırır.
2. Skor formülünde kamu binası terimini "toplumsal ihtiyaç"tan ayır (§3, ρ = −0,47).
3. Çiğli ölçeğine çıkmadan önce ayak izi kaynağını çapraz kontrol et (§4).
4. Google Solar API anahtarı al — pilot ne olursa olsun D5/D6 buna bağlı.

---

## Üretilen dosyalar

| Betik | Ne yapar |
|---|---|
| `scripts/acikveri_indir.py` | İzmir BB açık veri portalından 9 veri seti + lisans envanteri |
| `scripts/mahalle_sinirlari.py` | Çiğli 26 mahalle + Menemen/GMK OSM sınırları |
| `scripts/ihtiyac_analizi.py` | 391.215 ayak izini mahallelere dağıtır, tüm göstergeleri birleştirir |
| `scripts/ayrim_gucu.py` | İzmir'in 974 mahallesi üzerinde senaryo karşılaştırması |

| Çıktı | İçerik |
|---|---|
| `cache/ihtiyac_analizi.csv` | 27 mahalle × 24 gösterge |
| `cache/ayrim_gucu.csv` | 974 İzmir mahallesi, ihtiyaç vekilleri + SEGE |
| `cache/izka/sege_ilce.json` | SEGE 2004/2017/2022, 30 İzmir ilçesi |
| `cache/izka/*.txt` | İki İZKA belgesinin tam metni (534 sayfa), sayfa işaretli |
| `cache/acikveri/` | Ham veri setleri + `_envanter.json` (lisans, tarih, kaynak URL) |
