# Test referansı — insan çizimi (LabelMe)

111 çatı (`bolum = test_referans`, modelde kullanılmadı) tek klasörde: `goruntuler/`.
Çizimler `cizimler/` klasörüne kaydedilir.

## Kurulum (bir kez)

    pip install labelme

## Çizim

    cd veri/elle/test_referans
    labelme goruntuler --output cizimler --labels labels.txt --nodata --autosave

1. Hangi bina? Aynı adlı dosyayı `konum/` klasöründe açın: hedef çatı sarı kutunun içinde.
   Kutu yalnız binayı bulmak için; sınırı kutuya göre değil görüntüye göre çizin.
2. **Create Polygons** (Ctrl+N) ile çatının dış sınırını köşe köşe tıklayın, ilk noktaya dönüp kapatın.
3. Etiket her zaman `cati`. Çatının tüm yüzleri (beşik/kırma iki yanı, mevcut paneller dahil) tek poligon.
4. Çatı birden fazla ayrı parçaysa her parçaya ayrı `cati` poligonu.
5. Sonraki görüntü: **D**, önceki: **A**. `--autosave` her görüntüyü `cizimler/` altına JSON olarak kaydeder.
6. SAM maskesine, önizlemelere ya da ayak izi haritasına bakmayın (çizim bağımsız olmalı).
7. Birden fazla kişi çiziyorsa aynı görüntüyü iki kişi çizmesin: işi dosya numarasına göre bölün
   (ör. "c0004–c0500 Ali"); `cizimler/` klasöründe hangi dosyanın bittiği görünür.

## İkinci bağımsız çizim (20 çatı)

`liste.csv` içinde `cift_cizim = True` olan 20 çatıyı İLK çizenden FARKLI biri, onun çizimine
bakmadan yeniden çizer; çıktısı ayrı klasöre gider:

    labelme goruntuler --output cizimler_2 --labels labels.txt --nodata --autosave

Çatılar: c0009, c0032, c0101, c0191, c0240, c0360, c0408, c0483, c0505, c0595, c0598, c0727, c0997, c1141, c1158, c1226, c1307, c1329, c1334, c1446

Üretici: `scripts/test_referans_paketi.py` (sabit tohum; var olan JSON'lara dokunmaz).
