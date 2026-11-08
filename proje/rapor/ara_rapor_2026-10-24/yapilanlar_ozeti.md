# Yapılanlar özeti — 24 Ekim 2026 (Claude, otomatik çalışma)

Değerlendirme raporu: `cati_segmentasyon_degerlendirme.pdf` (bu klasörde, 3 sayfa).

## 1. Colab koşusu (SAM ayar deneyi) — TAMAM
- Defter: Drive `sam_birlesik_colab.ipynb`. **En üste yeni bir hücre eklendi** ("12) SAM AYARI ICIN ADAY MASKELER"); diğer hücrelere dokunulmadı.
- Colab Drive'a erişim izni istedi; **izin verilmedi** (senin adına OAuth izni vermiyorum). Onun yerine yalnızca gereken veri (sam_girdi.csv + 178 görüntü, 2 parça zip) Colab dosya paneline yüklendi.
- T4 GPU, 178 çatı × 3 istem × 3 aday maske, ~7 dk. Çıktı `Downloads\sam_aday.zip` → kalıcı kopya `CatiGunes\veri\ham\sam\ayar_2026-10-24\sam_aday.zip`.
- Doğrulama: mevcut kural bu koşuda test medyanı 0,879 verdi, önceki ölçüm 0,878 → tutarlı.

## 2. Sonuçların değerlendirmesi
- Test seti 98 çatı: **SAM↔insan medyan IoU 0,878, %88'i ≥ 0,70**; insan↔insan 0,935.
- Ayar deneyi: **kazancın kaynağı maskeyi ayak izine kırpmamak** (+0,016 IoU, %95 GA 0,007–0,025; 32 iyileşen / 13 kötüleşen). Merkez noktası tek başına etkisiz. Okullarda en iyi: kutu %10 geniş (medyan 0,681 → 0,768, ama n=9).
- Bu kural **uygulanmadı** — tüm çatılarda yeniden koşu + komşu taşma kontrolü gerekir; kazanç küçük; karar model ekibinin.

## 3. Panel düşümü — TAMAM
- 4_panel setindeki elle çizilmiş **panelsiz alan** çizimleri kullanıldı (yeşil = çatı, sarı = panel olmayan kısım; görselle doğrulandı).
- Kurallar: mevcut GES tam (62 çatı) → kullanılabilir alan 0; kısmi + çizim var (25) → panelsiz alan ∩ çatı; kısmi ama çizim yok (2: c0157, c0319) → çatının tamamı, işaretli.
- Model_Verisi: yeni katman `uygun_alan`, yeni sütunlar `panel_durumu`, `uygun_alan_m2`. Toplam kullanılabilir alan **1,97 km²** (çatı 2,24 km²). Kısmi 25 çatıda alan %29 azaldı.
- **PVGIS/NPV hesabı artık `uygun_alan_m2` ile yapılmalı.**

## 4. Yol üstünde bulunan ve düzeltilen hatalar
- **c1307**: yeniden çizimde komşu (panelli) bina çizilmişti, kayıtlı çatı soldaki şerit. Kural eklendi: kendi ayak izinin <%5'ine dokunan insan çizimi kullanılmaz (c1307 ve c0447 böyle ayıklandı).
- **IoU betiği tutarsızlığı**: 5_ikinci_cizim'den test setine giren çatılarda yeniden çizim uygulanmıyordu (c0598, c0997, c1307). Düzeltildi; test 98 çatı, medyan 0,878.
- Ayak izi düzeltme listesi artık betikten üretiliyor (önce elle üretilmişti): 24 çatı (eksik 15, hatalı 8, belirsiz 1).
- insan_referans paketi Windows klasör kilidi yüzünden bir kez hata verdi → tekrar deneme eklendi.

## 5. Değişen / eklenen dosyalar
| Dosya | Ne |
|---|---|
| `scripts/cati_geometri.py` | panelsiz alan aktarımı + panel düşümü + yanlış bina kuralı + kilit düzeltmesi |
| `scripts/cizim_iou.py` | 5_ikinci yeniden çizim düzeltmesi + düzeltme listesi üretimi |
| `scripts/sam_ayar.py` | yeni: kural ayarı (ayar'da seç, test'te karşılaştır) |
| `scripts/colab_sam_aday_hucresi.py`, `colab_sam_aday_tek_hucre.py` | Colab hücresi (kayıt) |
| `scripts/ara_rapor_pdf.py` | yeni: PDF raporu (sayılar dosyalardan okunur) |
| `veri/elle/panelsiz_cizimleri.geojson` | yeni: 25 panelsiz alan çizimi |
| `veri/elle/test_referans/sam_ayar_sonuc.csv` | yeni: 30 kural × çatı IoU |
| `Desktop/CatiGunes_Model_Verisi/` | catilar.gpkg (+`uygun_alan`), catilar.csv, BENIOKU.md, insan_referans/ |
| `veri_dogrulama.py` | koşuldu: 34 geçti, 0 hata |

## 6. Onayından sonra yapılanlar (24 Ekim, 2. tur)
1. **Ayak izi düzeltmesi uygulandı**: 23 çatı (c0485 belirsiz hariç) `scripts/ayak_izi_duzeltme.py isle` ile işlendi → **10 düzeltildi, 13 uygulanmadı** (insan çizimi komşu OSM kaydının >%15'ine taşıyor = bina OSM'de parçalı çizilmiş; çift sayım kuralı). Betikte küçük hata düzeltildi: Model_Verisi'nden çıkmış eski kayıt (way/877563353, <200 m²) çakışma kontrolünü çökertiyordu. Yedek: scratchpad `ayak_izi_duzeltme_yedek.csv`.
2. **c0157, c0319**: görüntülere bakıldı, çatıların neredeyse tamamı panelli (kalan şerit ışıklık/oluklu kenar) → **tam sayıldı** (uygun alan 0). `cati_geometri.py` içinde `KISMI_TAM_SAYILAN`.
3. `kur.py` tüm zincir yeniden koşuldu: **34 geçti, 0 hata**. Kullanılabilir alan **1,963 km²** (tam GES 64 çatı, kısmi-düşülmüş 25).
4. Colab: yeni hücre defterin **en sonuna** taşındı, kaydedildi.
5. PDF güncellendi (tablo durumu + sıradaki adımlar).

## 7. Açık kalanlar
- Komşu kayda taşan **13 çatı**: senin kararınla birleştirilmedi — çatı sayısı veriden geldiği gibi kalır, bu çatılarda eski ayak izi kullanılır.
- Düzeltilen 10 çatıda SAM metrikleri (kaplama vb.) eski ayak izine göre hesaplı kalıyor; `sam_veriseti.py` bilerek yeniden koşulmadı (test bölümünü değiştirir).
- **Kırpmasız SAM** kararı (model ekibi).
