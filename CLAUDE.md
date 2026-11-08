# Çatı GES bitirme projesi: ortak ekip notları

OSB ve kamu binalarında çatı GES uygunluğu ve önceliklendirme karar destek sistemi (MIS412, İzmir Bakırçay Üniversitesi YBS). Bu repo ekipteki herkesin Claude'unun aynı bilgiyle çalışması için var.

## Oturum başında
1. `DURUM.md` ve `KARARLAR.md` dosyalarını oku.
2. API veya web harita işi yapılacaksa `API.md` dosyasını da oku.
3. `KARARLAR.md`'deki kapanmış konuları, kullanıcı açıkça istemedikçe yeniden açma veya önerme.

## Oturum sonunda
- Kullanıcıya şunu öner: yapılan işi `DURUM.md`'de kullanıcının kendi bölümünün en üstüne, tarihli tek madde olarak eklemek.
- Yalnız başkasının işini etkileyen şeyleri yaz: biten iş, değişen dosya veya veri alanı, kalan sorun. Oturum özeti yazma.
- API veya veri alanı değiştiyse `API.md` dosyasını aynı anda güncelle.
- Yeni ekip kararını `KARARLAR.md`'ye yalnız kullanıcı "ekip böyle karar verdi" derse ekle.
- Commit ve push işlemini kullanıcı isteyince yap. Commit öncesi `git pull` çalıştır.

## Bu repoya asla girmeyecekler
- API anahtarı, şifre, token (`.env`, `*_key`).
- Öğrenci numarası veya başka kişisel bilgi.
- 100 MB'tan büyük dosya (GitHub kabul etmez). SAM ağırlıkları ve `proje/cache/` bu yüzden yok; 50 MB üstü yeni dosya eklemeden önce kullanıcıya sor.

## Klasörler
- `proje/`: kodlar, notebook'lar, ham ve işlenmiş veri, belgeler (`proje/scripts/kur.py` hesap zincirini kurar).
- `model_verisi/`: son veri seti ve çıktılar (çatı geometrileri, üretim, NPV, Monte Carlo). `model_verisi/` içindeki çıktıları elle değiştirme; betiklerle üret.
- `raporlar/`: güncel ara rapor (`Bitirme_Ara_Rapor_Teslim.docx`) ve TÜBİTAK 2209-A önerisi.
- `YONTEM.md`: üretim, NPV ve Monte Carlo hesabının ayrıntısı. Bu konularda çalışmadan önce oku.
- `proje/scripts/` içindeki betiklerin bir kısmı Bilal'in bilgisayarındaki yolları ve repoda olmayan `proje/cache/` klasörünü varsayar. Yolları düzeltmeden `kur.py` zincirini çalıştırma. API ve web harita için `model_verisi/` yeterlidir.
- `kaynaklar/`: makaleler. Atıf yazmadan önce buradaki PDF'ten doğrula. Repo özel kalmalı, makaleler dışarı dağıtılmamalı.
- Word dosyaları birleştirilemez: aynı `.docx` üzerinde iki kişi aynı anda çalışmasın, başlamadan önce `DURUM.md`'ye yaz.

## Çalışma biçimi
- Dil Türkçe. Rapor dili sade olsun; ekonomi makalesi gibi yazılmasın.
- Sonuç sayısı yazarken kaynağını belirt ve ölçmeden "çalışıyor" deme.
- Başka bir üyenin bölümüne yazma, onun kodunu haber vermeden büyük ölçüde değiştirme.

## Görev dağılımı (ara rapor Tablo 18)
| Üye | Sorumluluk |
|---|---|
| Bilal Tarık Demir | Veri hattı, üretim ve NPV hesaplarının bakımı |
| Yiğit Eren Yıldırım | Belirsizlik analizinin gözden geçirilmesi, tez yazımı koordinasyonu |
| Dorukhan Turhan | Model iyileştirme, REST API ve LLM açıklama katmanı |
| Yavuz Acer | Web harita arayüzü ve kullanıcı deneyimi |
