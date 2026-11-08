# Eski SAM paket üreticileri (2026-10-22'de emekli)

Bu betikler ayrı paketler üretiyordu: `CatiGunes_SAM_Veriseti` (OSB + okul/hastane), `CatiGunes_SAM_Kamu` (80 kamu),
`CatiGunes_SAM_Duzeltme` (24 düzeltilen çatı), `harita_ek_kamu.zip`. Paketler 2026-10-22'de silindi; hepsinin yerini
`scripts/sam_birlesik_paketi.py` → `Desktop/CatiGunes_SAM_Birlesik.zip` + tek Colab defteri `sam_birlesik_colab.ipynb` aldı.
Bölüm (train/val/test_referans) kaydı artık `veri/elle/sam_bolum.csv`.

Bu betikler silinen klasörlere bağlı olduğu için ÇALIŞMAZ; yalnız yöntem kaydı olarak duruyor.
Uyarı: `sam_veriseti.py` bölümleri sabit tohumla SIFIRDAN böler → test_referans değişir.
