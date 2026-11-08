## Chaudhry, Qureshi, Jabbar & Taj (2024) — Gölge boyundan bina yüksekliği
KUNYE: Chaudhry S., Qureshi M., Jabbar S., Taj M. (2024). Building height estimation using shadow length in satellite imagery. arXiv:2411.09411 (ön baskı, hakem sürecinden geçtiği belirtilmemiş). LUMS Computer Vision and Graphics Lab, Pakistan. Kod: github.com/nullptr-code/building-height-model
TEMA: Tek (monoküler) uydu görüntüsünden gölgeyle bina yüksekliği — bizim 9. adımımızın doğrudan karşılığı
AMAC: Stereo/çok bakışlı ya da SAR/LiDAR verisi olmadan, tek bir optik uydu görüntüsünde gölge boyunu ölçüp güneş yükseklik açısıyla bina yüksekliğini hesaplamak; derin öğrenmeyle analitik formülü birleştirmek.
YONTEM:
- Üç yükseklik yöntemi ailesi (Hartley & Zisserman): radyal kayma, paralaks (stereo), GÖLGE — gölge yöntemi tek görüntüyle çalışan tek yöntem.
- Formül: H = S_l × tan(σ) (S_l gölge boyu, σ güneş yükseklik açısı; güneş konumu Reda & Andreas 2004 SPA algoritması).
- Adımlar: (1) değiştirilmiş YOLOv7 ile bina + gölgesinin kutusu, (2) kırpılıp 50×50'ye küçültülen görüntüde ResNet18 regresyonla gölge boyu, (3) analitik formülle yükseklik; "gölge tabanlı yükseklik kaybı" ile hata önce analitik modelden sonra ağdan geri yayılıyor (hibrit öğrenme).
- Veri: "42 Çin şehri" veri seti genişletildi (400×400 px = 1.000×1.000 m karolar → ~2,5 m/piksel); kat sayısı × 3 m = yükseklik etiketi; 2.704 görüntüde ~50.000 binaya elle kutu + gölge boyu etiketi (DarkLabel + kendi araçları).
- ÇEKİM SAATİ SORUNU: Google Earth görüntüsünde yalnız TARİH var, saat yok → güneş yükseklik açısı bilinemiyor → yer gerçeği yüksekliğe en az hatayı veren saati MİNİMİZASYONLA seçmişler.
- Gürültü temizliği: >30 m binalar 30 m'de kesildi (büyük hata); 3–9 m binalarda ≥50 birim gölge işaretlenenler atıldı; test için analitik formül hatası ≤2,5 m olan binalar seçildi (≤30 m, ~5.000 örnek).
- Eğitim: L1 kayıp, Adam, öğrenme oranı 1e-4, ağırlık azaltma 1e-5.
BULGULAR: RMSE 3,84 m (gölge boyu RMSE 4,4 m); çok bakışlı/çok spektral yöntemlerden iyi (MM3Net 6,26 m, Stereollax 5,74, Random Forest 7,46). Veri setinin ham hali üzerinde ortalama hata ~10 m (3–4 kat). 12–30 m aralığında hata küçük; 3–9 m binalarda gürültülü; >30 m çok büyük hata. Örnek: Jin Mao Kulesi gerçek 420 m, gölgeden 430 m.
EKSIKLER: Etiket kat×3 m yaklaşımı (gürültülü); test setini analitik hatası küçük binalardan seçmek sonucu İYİMSER yapıyor; çekim saati bilinmediği için yer gerçeğine göre ayarlanmış — gerçek uygulamada bu mümkün değil; yalnız Çin; gölgenin başka bina/ağaç üstüne düştüğü (engelli) durumlar ele alınmamış; hakemli yayın değil.
BIZIM PROJEYE:
- 9. adımımızın (gölge boyundan yükseklik) literatürdeki doğrudan karşılığı ve formül dayanağı: H = L·tan(σ).
- Onlar çekim saatini bilmediği için yer gerçeğinden "uydurmak" zorunda kalmış; BİZ güneş azimutunu gölgelerden ÖLÇÜYOR, yüksekliği çekim tarihi ±7 gün ile NOAA/pvlib güneş konumundan buluyoruz (tepe/ters oran ≥ 2,0 güvenilirlik ölçütüyle) → yer gerçeği olmadan çalışan bir yöntem; tezde bu farkı "katkı" olarak yaz.
- Hata büyüklüğü referansı: derin öğrenmeyle bile RMSE ~3,8 m (seçilmiş binalarda), ham veride ~10 m → bizim alan sınıfı medyanlarımızın (8 / 11 / 17,7 m) bina bazında değil sınıf bazında kullanılması doğru bir ihtiyat.
- "Engelli" gölgeler (başka binaya düşen) onların da çözmediği sorun → bizim "engelli: 3.019 bina" kategorimizin gerekçesi.
- Doğrulama önerisi: Çiğli'de kat sayısı bilinen örnek binalarla (OSM building:levels etiketi ya da saha gözlemi, kat × 3 m) yükseklik tahminimizi karşılaştır; RMSE raporla — bu makaleyle kıyaslanabilir bir sayı verir.
