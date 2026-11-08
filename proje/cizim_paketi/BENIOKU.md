# Elle çizim paketi (LabelMe) — toplantı 23.10

| Klasör | Çatı | Etiket | Amaç |
|---|---|---|---|
| `1_test_referans` | 111 (+20 ikinci çizim) | `cati` | Genel doğruluk (SAM ↔ insan IoU) |
| `2_kamu_ek` | 20 | `cati` | Kamu çatıları için ayrı sonuç (testte yalnız 11 kamu var) |
| `3_supheli_ek` | 30 | `cati` | Yeşil/kırmızı bayrağının doğruluğu (testte yalnız 11 şüpheli var) |
| `4_panel` | 27 | `panel` | Kısmi GES'li çatılarda mevcut panel alanı |

Toplam 208 çizim. Dağılım (23.10 kararı, `gorev_dagilimi.csv` → `pay`):

| Kim | Ne çizer | Çizim |
|---|---|---|
| Arkadaş | `1_test_referans` → `cizimler/` (111 çatının hepsi, 1. çizim) | 111 |
| Bilal | `2_kamu_ek` 20 + `3_supheli_ek` 30 + `4_panel` 27 | 77 |
| Bilal | `1_test_referans` → `cizimler_2/` (yalnız `liste.csv` → `cift_cizim = True` olan 20) | 20 |
| | **toplam** | **208** |

Arkadaşa yalnız `1_test_referans.zip` gönderilir; `cizimler_2/` klasörünü kullanmaz.

## Kurulum (bir kez)

    pip install labelme

## Çizim (her klasörde aynı)

    cd <klasör>
    labelme goruntuler --output cizimler --labels labels.txt --nodata --autosave

- Hangi bina? Aynı adlı dosyayı `konum/` klasöründe açın, hedef sarı çizgiyle gösterilmiştir.
- **Ctrl+N** (Create Polygons) → köşelere tıklayın → ilk noktaya dönüp kapatın → etiketi seçin.
- **D** sonraki görüntü, **A** önceki görüntü. `--autosave` her görüntüyü `cizimler/` altına JSON olarak kaydeder.
- Yalnız size düşen dosyaları çizin (`gorev_dagilimi.csv` → pay).

### 1–3: çatı çizimi (`cati`)
- `konum/` içindeki sarı kutu yalnız binayı bulmak içindir; sınırı kutuya göre değil görüntüye göre çizin.
- Çatının tüm yüzleri (beşik/kırma çatının iki yanı, mevcut paneller dahil) tek poligon olsun.
- Çatı ayrı parçalardan oluşuyorsa her parçaya ayrı `cati` poligonu çizin.
- SAM maskesine, haritaya ya da önizlemelere bakmayın; çizim bağımsız olmalı.
- **İkinci çizim** (yalnız `1_test_referans`, `liste.csv` → `cift_cizim = True`): ilk çizenden farklı biri,
  onun çizimine bakmadan çizer. Çıktı ayrı klasöre gider:
  `labelme goruntuler --output cizimler_2 --labels labels.txt --nodata --autosave`

### 4: panel çizimi (`panel`)
- `konum/` içindeki sarı çizgi = modeldeki çatı sınırı. Yalnız bu çatının üstündeki panelleri çizin.
- Panel **grubunun dış sınırını** çizin; sıralar arasındaki boşluk içeride kalsın.
- Ayrı panel grupları için ayrı `panel` poligonları çizin.
- Panel yoksa ya da emin değilseniz boş bırakıp not alın.

## Bitince
Her kişi kendi `cizimler/` JSON'larını aynı klasöre (Drive) kopyalar; dosya adları çakışmaz.
Ek setler (2, 3) yalnız değerlendirme içindir, eğitim setinden çıkarılacak.

Üretici: `scripts/toplanti_cizim_paketi.py` (tohum 42; var olan JSON'lara dokunmaz).
