# İnsan referansı (SAM ayarı / değerlendirme)

`goruntuler/cNNNN.jpg` = SAM girdisiyle aynı kesit; `insan_maske/cNNNN.png` = LabelMe insan çizimi (255 = çatı). `liste.csv`: `bolum` **ayar** (kural/ince ayar burada denenir), **test** (yalnız son ölçüm — ayara KULLANMA), **dislandi** (insan ile kayıt aynı binaya bakmıyor; `dislama` sütunu). `kutu_px` = SAM'e verilen kutu.

Dağılım: test 97, ayar 52, dislandi 28. Üretici: `scripts/cati_geometri.py`.
