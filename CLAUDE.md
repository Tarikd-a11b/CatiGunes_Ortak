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
- Büyük veri dosyaları (gpkg, görüntü, model ağırlığı). Bunlar Drive'da durur.

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
