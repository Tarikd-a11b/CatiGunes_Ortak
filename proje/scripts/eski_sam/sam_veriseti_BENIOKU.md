# Çatı GES — SAM Veri Seti

Kaynak: `Desktop\CatiGunes_Model_Verisi` · üretici: `CatiGunes/scripts/sam_veriseti.py` (tekrar çalıştırınca baştan kurar). 1.456 çatı, 1 satır = 1 çatı.

## Klasör
| Dosya | Ne |
|---|---|
| `goruntuler/cNNNN.jpg` | Uydu kesiti (NNNN = `cati_id`) |
| `maskeler/cNNNN.png` | Çatı **ayak izi** maskesi (255 = çatı), hizalanmış OSM/Microsoft poligonundan |
| `tum.csv` | Bütün çatılar + `bolum` sütunu |
| `train.csv` / `val.csv` / `test_referans.csv` / `supheli.csv` | Bölümler (aşağıda) |
| `deneme.csv` + `deneme_onizleme.jpg` | Colab'da ilk koşu için 10 çatı (kırmızı = kutu istemi, sarı = ayak izi) |
| `ozet.json` | Sayılar, test setinin katman dağılımı |

## Bölümler
| Bölüm | Çatı | Ne için |
|---|---|---|
| `train` | 1.093 | SAM ince ayarı yapılırsa eğitim. Hazır SAM kullanılırsa doğrudan çalıştırılacak çatılar |
| `val` | 195 | Ayar/eşik seçimi (multimask seçimi, skor eşiği) |
| `test_referans` | 150 | **İnsan etiketleyecek** (2 kişi, bağımsız, QGIS) → IoU + alan hatası. Katmanlı: OSB/kamu × LG03/WV02 × alan sınıfı × mevcut GES, her katmandan ≥2 |
| `supheli` | 18 | Görüntüsü kötü / ağaç altı / şekil uyumsuz → eğitim ve ölçüme girmez, sonucu ayrıca raporlanır |

Bölünme sabit tohumla (42) yapıldı; tekrar üretince aynı çıkar.

## Sütunlar
- **SAM için:** `goruntu`, `kutu_px` (`[x1, y1, x2, y2]` kutu istemi), `poligon_px` (maskeyi buna kırp), `yer_m_px` (1 piksel kaç metre → alan = piksel sayısı × yer_m_px²)
- **Yorum için:** `uydu` + `gercek_cozunurluk_m` (LG03 0,34 m / WV02 0,5 m), `cekim_tarihi`, `hizalama` (`yalniz_blok` = çatı bazında teyit edilemedi, kutu 1–2 m kayık olabilir), `mevcut_ges` (`tam` = potansiyel yok; `kismi` = panel alanını çıkar), `gorsel_kontrol`, `alan_m2` (taban alanı)
- **Bağlantı:** `cati_id`, `kesit`, `osm`, `lon`, `lat` → `CatiGunes_Model_Verisi/catilar.csv`

## ⚠️ Maskeler hakkında
`maskeler/` **çatının dış sınırıdır, "panele uygun alan" değildir.** Çatı segmentasyonu için zayıf etiket (weak label) olarak kullanılabilir. İnsan çizmedi, poligon hizalaması otomatik. `yalniz_blok` olanlarda 1–2 m kayma olabilir. Asıl başarı ölçüsü `test_referans` için insanların çizeceği "panele uygun alan" etiketleridir.

## Colab'da en kısa yol
```python
import pandas as pd, ast, numpy as np
from PIL import Image
df = pd.read_csv("deneme.csv")
for r in df.itertuples():
    img = np.array(Image.open(r.goruntu).convert("RGB"))
    kutu = np.array(ast.literal_eval(r.kutu_px))
    ayak = np.array(Image.open(r.maske)) > 0
    # predictor.set_image(img); masks, scores, _ = predictor.predict(box=kutu, multimask_output=True)
    # m = masks[scores.argmax()] & ayak ; alan_m2 = m.sum() * r.yer_m_px**2
```
