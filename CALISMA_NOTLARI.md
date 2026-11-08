# Çalışma notları

Projenin geçmişinde öğrenilenler: yazılı karar listesinde olmayan çalışma kuralları, denenip bırakılanlar ve yeniden koşarken çıkan tuzaklar. Güncel durum için `DURUM.md`, kapanmış ekip kararları için `KARARLAR.md` esastır; çelişki olursa onlar geçerlidir.

## Veri kuralları
- 200 m² altındaki çatılar listede yok (`MIN_GES_ALAN=200`, 18 Ekim).
- `cati_id` kalıcıdır (`proje/veri/elle/cati_id_kayit.csv`). Çıkan numara boş kalır, yeni çatı en büyük numaranın bir üstünü alır.
- Çatı geometrisinde öncelik insan çizimi, sonra SAM, sonra ayak izidir.
- Komşu çatının %15'inden fazlasına taşan insan çizimi uygulanmaz. OSM'de parçalı çizilmiş binalar birleştirilmez, bu yüzden çatı sayısı değişmez.
- Mevcut GES'li çatılar veride ve haritada kalır (`panel_durumu`), yalnız potansiyel, kWp ve NPV hesabında düşülür. Potansiyel için `uygun_alan_m2` kullanılır.
- Kurumlardan veri talep yazısı gönderilmeyecek (21 Ekim): OSB tüketimi ve sözleşme gücü, MEB ve Sağlık listeleri, EPİAŞ üyeliği iptal. Kurulum maliyeti için firma teklifi `DURUM.md`'de ayrı açık iştir.
- Temel üretim açık montaj (1 kWp için Atatürk OSB'de 1.477 kWh). Çatı montajı varsayımı (1.420 kWh) alt değerdir.

## Danışman geri bildirimleri (Emine Uçar)
- 15 Ekim: Gölge analizi ve toplumsal ihtiyaç endeksi kapsamdan çıktı.
- 16 Ekim, teklif yorumları: Önceki çalışmalar "-mıştır", kendi çalışmamız "-acaktır / hedeflenmektedir" kipiyle yazılsın; metin yapay zekâ dili taşımasın.
- 2209-A önerisi için de aynı uyarı geldi: Herkes kendi bölümünü kendi diliyle yazsın.

## Segmentasyon kalitesi
- Yansız test (111 çatı): SAM/insan toplam alan oranı 0,975, %95 güven aralığı 0,935–1,021 (`proje/veri/elle/test_referans/alan_guven_araligi.csv`).
- Ayak izi doğru olan 98 çatıda IoU ortancası 0,878. İki insan çizimi arasında 0,935.

## Denenip bırakılanlar (yeniden önermeyin)
| Deneme | Sonuç |
|---|---|
| SAM ince ayarı | Hücre hazır (`proje/scripts/colab_sam_ince_ayar_hucresi.py`), gerçek koşu yapılmadı, rafta |
| 16 çatıda yaklaşık 10 piksel kaydırma | SAM ortancası 0,151'den 0,144'e indi, benimsenmedi |
| SAM ile otomatik eksik ayak izi tespiti | Testte 1/11 yakaladı, 97 temiz çatıda 21 yanlış alarm, IoU 0,879'dan 0,803'e düştü |
| Kırpmasız SAM | Yalnız +0,016 kazanç, uygulanmadı |
| 23 sorunlu çatının elle düzeltmesi | 24 Ekim'de yapıldı, tekrar çizdirmeyin; önce `proje/veri/elle/ayak_izi_duzeltme.csv` |

196 kartlık görsel kontrol GES panel kontrolüdür, firma–çatı onayı değildir.

## Yeniden koşarken tuzaklar
- `proje/scripts/kur.py` veri klasörünü baştan kurar ve `veri/inceleme` ile `veri/islenmis` klasörlerini siler; oraya kalıcı dosya koymayın.
- `ayak_izi_duzeltme.py isle` tekrar çalıştırılamaz, tek kez çalışır.
- `sam_veriseti.py` yeniden koşulursa test bölümü değişir.
- `cati_geometri.py` çizimleri Bilal'in masaüstündeki `Toplantı\Cizim_Paketi` yolundan okur. Repodaki kopya `proje/cizim_paketi/`; yeniden koşacaksanız yolu değiştirin.
- Colab'da defteri tek sekmede açın; iki sekmede kaydetme çakışır ve eski hücre dosyayı bozabilir.
- Colab'da SAM ayar hücresinden sonra ana akışa geçmeden **Çalışma zamanı > Bağlantıyı kes ve sil** yapın; yoksa eski veri kalır ve 4. hücre 1.085 kontrolünde durur.
- Colab'da `/content` oturumla silinir. Sonuçları indirmeden oturumu kapatmayın (`INDIR=True` ya da Drive).

## Eski belgeler
`proje/belgeler/eski/` içindeki sayılar o günün durumunu gösterir (ör. 112 şüpheli çatı; son değer 128). Güncel kaynak olarak kullanmayın.
