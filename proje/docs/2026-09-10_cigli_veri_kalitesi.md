# Çiğli veri kalitesi çalışma notu — 2026-09-10

Bu oturumda iki şey yapıldı: (1) PVGIS tahmini ilk kez bağımsız bir kaynakla
doğrulandı, (2) Çiğli ölçeğine çıkmadan önce şart olan MS ↔ OSM çapraz kontrolü
koşuldu. Her ikisi de teze doğrudan girecek bulgular üretti.

Yeni betikler: `scripts/dogrulama_ges.py`, `scripts/osm_capraz_kontrol.py`
Yeni çıktılar: `cache/dogrulama_ges.csv`, `cache/osm_capraz_kontrol.csv` + `.json`,
`cache/osm_binalar_cigli.geojsonl` (30.589 OSM bina poligonu, önbellek)

---

## 1. PVGIS doğrulaması — belediyenin kendi 26 GES tesisi

İzmir BB açık veri setindeki `lisanssiz_ges.csv`, belediyenin kendi güneş
tesislerinin kurulu gücünü ve yıllık üretimini veriyor → kWh/kWp cinsinden
bağımsız bir ölçüt.

**Önce veriyi ayırmak gerekti.** 26 kaydın 14'ünde üretim = güç × 1600 *tam*
tutuyor; bunlar ölçüm değil, belediyenin sabit planlama çarpanı. Kalan 12'si
proje bazlı hesaplanmış. Karıştırılırsa doğrulama anlamsız olur.

| | kWh/kWp |
|---|---|
| PVGIS düz 0° | 1.375 |
| PVGIS güney 15° | 1.519 |
| PVGIS güney 30° (teorik en iyi) | 1.579 |
| PVGIS doğu/batı 30° | 1.280 / 1.287 |
| PVGIS kuzey 30° (en kötü) | 900 |
| **Proje bazlı 12 tesis, medyan** | **1.453** (1.316 – 1.593) |
| Belediyenin planlama kabulü (14 tesis) | 1.600 |

Sonuçlar:

- **Bandımız doğrulandı.** 12 tesisin 8'i PVGIS düz–güney30 bandının içinde.
  Medyan tesis / PVGIS düz = 1,056; medyan tesis / PVGIS güney30 = 0,920.
  Faz 2'nin üretim bandı gerçek tesislerin oturduğu aralıkla uyumlu.
- **Belediyenin 1.600 kabulü iyimser** — İzmir'de *ideal yönelimli* bir çatının
  PVGIS tahmininden (1.579) bile yüksek, gerçekleşen medyandan (%1.453) %10 üstte.
  Tezde politika bulgusu olarak yazılabilir.
- **Çiğli'de zaten bir tesis var:** Çiğli Aile Danışma Merkezi, 25,1 kW,
  1.593 kWh/kWp — proje bazlı listenin en yükseği. Çiğli analizinde referans.

Sınır: sütun başlığı "BEKLENEN YILLIK ÜRETİM". Proje bazlı 12 kayıt da tahmin
olabilir, ölçüm olmayabilir; ancak proje bazında hesaplandıkları için sabit
çarpan grubundan yöntemsel olarak farklılar. Bu sınır tezde yazılmalı.

---

## 2. MS ↔ OSM çapraz kontrolü — Çiğli 26 mahalle

### Önce: ilk koşuda bulunan ve düzeltilen hata

16 karodan biri Overpass'te 6 kez üst üste 504 verdi ve betik onu **sessizce
atladı**. O karo EVKA-2, EVKA-6, Ahmet Taner Kışlalı, Aydınlıkevler, Güzeltepe,
İnönü, Yakakent ve Harmandalı'nı kapsıyordu. Sonuç: EVKA-6 "0 OSM binası",
EVKA-2 "91 bina" göründü — bu, "OSM kapsama boşluğu" diye rapor edilseydi
tamamen yanlış bir bulgu olurdu.

Düzeltme: başarısız karo artık dörde bölünüp yeniden deneniyor (3 kademeye
kadar); hâlâ inemezse betik **tablo üretmeden duruyor** ve etkilenen mahalleleri
yazıyor. Sessiz veri kaybı bu projede tekrar eden hata tipi (Faz 2'deki min-max
kusuru da aynı aileden): sonuç makul göründüğü için fark edilmiyor.

### Bulgu A — resmî yapı sayısı hakem olarak kullanılamaz

Önceki analiz "MS ayak izi / resmî yapı" oranını veri kalitesi ölçütü olarak
kullanıyordu (Çiğli'de 0,27 – 2,97). Bu ölçüt geçersiz. Kanıt EVKA-2:

| | bina | medyan m² | toplam ha |
|---|---|---|---|
| MS ayak izi | 299 | 247 | 8,82 |
| OSM | 269 | 293 | 8,81 |
| Resmî YAPI | 1.103 | — | — |

İki bağımsız kaynak **çatı alanında %0,1 farkla** anlaşıyor (8,82 ↔ 8,81 ha),
örtüşme oranı 0,89. Buna karşılık resmî sayı 4 kat yüksek. Apartman
mahallelerinde resmî "YAPI" alanı bina değil, büyük olasılıkla bağımsız
bölüm/giriş sayıyor. Kaklıç'ta ise tersi: MS 1.880, OSM 1.429, resmî 632 —
kırsalda sera/müştemilat resmî kayıtta yok ama iki kaynakta da var.

Yani resmî sayı iki ayrı yönde, iki ayrı nedenle sapıyor; hakem olamaz.
MS/resmî ile OSM/resmî arasındaki Spearman yalnızca +0,41.

### Bulgu B — MS ayak izleri bitişik binaları birleştiriyor

**Çiğli toplamı: MS 537,9 ha, OSM 386,7 ha → MS/OSM = 1,391.**
26 mahallenin **hepsinde** oran ≥ 1,00 (1,00 – 1,97). Sistematik, rastgele değil.

Medyan bina boyutları nedeni gösteriyor:

| mahalle | MS bina / medyan | OSM bina / medyan |
|---|---|---|
| Ataşehir | 1.179 / **370 m²** | 1.694 / **114 m²** |
| Yeni Mahalle | 563 / 289 m² | 1.258 / 107 m² |
| Şirintepe | 1.066 / 135 m² | 2.353 / 59 m² |

Aynı alanda MS **daha az ve daha büyük**, OSM **daha çok ve daha küçük** poligon
görüyor. Makine üretimi ayak izlerinin bilinen hatası: bitişik nizam yapıları
tek poligona yapıştırıyor ve aradaki boşluğu da dolduruyor. Türkiye'nin bitişik
yapı dokusu bu hatanın en kötü koşulu.

Projeye üç ayrı etkisi var:
1. **Toplam çatı alanı kaynak seçimine göre %39 oynuyor.** Eğim/azimut
   belirsizliğinin (2,18×) yanına ikinci ölçülmüş hata kaynağı olarak girmeli.
2. **Bina başına atıf çöküyor** — birleşmiş poligon "bir bina" olarak
   sıralanıyor ama gerçekte 4 apartman. Ürünün çıktısı bina listesi olduğu için
   bu doğrudan ürünü bozuyor.
3. **SAM'in kutu istemi birleşmiş poligondan geliyor** → modele yanlış sınır
   veriliyor. Evka-5'teki "küçük binalarda oran 1,56" bulgusu muhtemelen bunun
   alt kümesi.

### Bulgu C — örtüşme oranı kullanılabilir bir kalite ölçütü

MS binalarının yalnızca **%57,5'i** bir OSM binasıyla örtüşüyor. İki kaynak
sadece kaç bina olduğunda değil, *hangi binaların var olduğunda* da anlaşamıyor.

Örtüşme oranı ile MS/OSM alan oranı arasında **Spearman −0,71**: örtüşmenin
düşük olduğu yerde MS alanı şişiriyor. Örtüşme ile mahalle yüzölçümü arasında
−0,58: kırsal mahallelerde durum kötüleşiyor. Yani örtüşme oranı, resmî sayının
yapamadığı şeyi yapıyor — kendi içinde tutarlı bir güvenilirlik ölçütü.

| kademe | mahalle | OSM bina | çatı ha | ort. MS/OSM |
|---|---|---|---|---|
| **A — güvenilir** (örtüşme ≥ 0,65) | 10 | 6.748 | 128,0 | 1,29 |
| **B — orta** (0,50–0,65) | 11 | 10.062 | 158,2 | 1,35 |
| **C — güvenilmez** (< 0,50) | 5 | 4.054 | 100,4 | 1,69 |

- A: Ahmet Efendi, Ahmet Taner Kışlalı, Ataşehir, Egekent, EVKA-2, EVKA-6,
  Köyiçi, Maltepe, Yeni Mahalle, İnönü
- B: Atatürk, Aydınlıkevler, Balatçık, Esentepe, EVKA-5, Güzeltepe, Harmandalı
  GMK Atatürk, Küçük Çiğli, Uğur Mumcu, Çağdaş, Şirintepe
- C: Cumhuriyet, Kaklıç, Sasalı Merkez, Yakakent, İzkent

**Not:** EVKA-5 (şimdiye kadarki tek pilot) B kademesinde, örtüşme 0,50. Faz 2
sonuçları en güvenilir mahallede üretilmemiş.

---

## 3. Açık kalan engel — görüntü kaynağı

İzmir Açık Veri portalında **ortofoto yok** (`ortofoto`, `uydu`, `wms`, `hava
fotoğrafı` aramaları 0 sonuç). Plandaki "lisansı temiz görüntü kaynağı İzmir
Açık Veri ortofoto olabilir" varsayımı geçersiz.

Çiğli ölçeği zoom-19'da kabaca 4.200 karo demek; Esri World Imagery'den bu
hacimde toplu indirme lisans açısından savunulabilir değil (D0 uyarısı).
Denenecek alternatifler: HGM Atlas WMTS, TKGM ortofoto servisi, İzmir CBS
(cbs.izmir.bel.tr — açık veri portalından ayrı). Bu oturumda üçü de hızlıca
yoklandı, sonuç alınamadı; sistemli denenmesi gerekiyor.

---

## Sıradaki iş

1. **Görüntü kaynağı çözülmeli** — segmentasyonu Çiğli ölçeğine çıkarmanın önündeki
   tek zorunlu engel bu.
2. **Ayak izi kaynağı kararı:** MS mi, OSM mi, ikisinin birleşimi mi? Bulgu B
   MS'in bitişik dokuda zayıf olduğunu gösteriyor; A kademesi mahallelerde OSM
   daha ayrıntılı. Öneri: OSM birincil, MS boşluk doldurucu — ama önce A
   kademesinde iki kaynakla paralel koşup SAM sonucunu karşılaştır.
3. **Skor formülünde kamu binası terimini ayır** (ρ = −0,47 kusuru, önceki not).
4. Google Solar API anahtarı → eğim/azimut (D5+D6).
5. Colab defteri hiç koşulmadı (D1/D2 model karşılaştırması).
