## Osco vd. (2023) — SAM'in uzaktan algılamada sıfırdan tek örneğe performansı
KUNYE: Osco L.P., Wu Q., de Lemos E.L., Gonçalves W.N., Ramos A.P.M., Li J., Marcato Junior J. (2023). The Segment Anything Model (SAM) for remote sensing applications: From zero to one shot. International Journal of Applied Earth Observation and Geoinformation 124, 103540. doi:10.1016/j.jag.2023.103540; arXiv:2306.16623 (incelenen: arXiv v2, 31.10.2023). Açık kaynak: segment-geospatial (samgeo) paketi.
TEMA: SAM'in hava/uydu görüntüsünde istem türüne (kutu / nokta / metin) ve çözünürlüğe göre sistematik değerlendirmesi — bizim istem seçimimizin ve çözünürlük sınırlılığımızın en doğrudan kanıtı
AMAC: SAM'in uzaktan algılama görüntülerinde (İHA, uçak, uydu) sıfır atış (zero-shot) başarısını istem türüne ve mekânsal çözünürlüğe göre ölçmek; metin isteminden otomatik seçilen tek örnekle (one-shot) iyileştirme önermek.
YONTEM:
- 11 veri seti, 3 platform: İHA (0,01–0,09 m; ağaç, ev, tarla, bina, araç), uçak (0,20–0,45 m; ağaç, araç, göl), uydu (0,30 m LoveDA ve 0,50 m SkySat; çok sınıflı: bina, yol, su, çorak, orman, tarla). Toplam >90 GB, >10.000 görüntü; yer gerçeği uzmanlarca üretilmiş.
- SAM ViT-H (en büyük model), samgeo aracı. İstemler: genel (istemsiz otomatik), kutu (nesne şekil dosyasından), nokta (merkez), metin (GroundingDINO + SAM = Grounded-SAM; kutu ve metin eşikleri veri setine göre deneme-yanılmayla).
- Tek örnek: PerSAM ve PerSAM-F (SAM dondurulur, yalnız 2 parametre ~10 sn ince ayar; çok ölçekli maske); yenilik: tek örneği insan yerine METİN İSTEMİNİN en yüksek skorlu nesnesinden otomatik seçmek. Kayıp Dice + sigmoid focal, kosinüs öğrenme oranı, 1000 epoch.
- Metrikler: Dice, IoU, piksel doğruluğu, TPR, FPR. Donanım: RTX 3090 24 GB.
BULGULAR (sıfır atış, IoU):
- İHA ev 0,04 m: KUTU 0,863 (en iyi) · nokta 0,548 · metin 0,798 → geometrisi belirgin, büyük nesnelerde (ev/bina) kutu en iyisi.
- İHA bina 0,09 m: kutu 0,535 · nokta 0,528 · metin 0,509 (hepsi orta).
- Uydu çok sınıflı 0,30 m: kutu 0,225 · NOKTA 0,567 · metin 0,510; 0,50 m: kutu 0,150 · nokta 0,378 · metin 0,340. Uyduda kutu istemi SINIR AŞIYOR (fazla yanlış pozitif), nokta en iyi.
- Çözünürlük 30 cm'nin üstüne çıkınca başarı belirgin düşüyor (SAM yüksek çözünürlüklü görüntülerle eğitildi).
- Kutu istemiyle küçük nesnelerde SAM GÖLGEYİ de nesneye katıyor (boyutu abartıyor); küçük/düzensiz nesnelerde ve düşük çözünürlüklü uyduda KOPUK SAHTE BİLEŞENLER üretiyor; yol-kaldırım gibi benzer malzemeli bitişik yüzeyleri ayırmakta zorlanıyor.
- Metin istemi genelde en zayıf, özellikle düşük çözünürlükte (GroundingDINO kuş bakışı görüntüyü tanımıyor).
- Tek örnek (PerSAM-F) tüm veri setlerinde sıfır atıştan iyi: İHA bina 0,535→0,669; uydu 0,30 m 0,567→0,680; metinle otomatik tek örnek insan örneğine yakın.
EKSIKLER: Sınırlı bölgesel çeşitlilik (Brezilya ağırlıklı); eşikler elle deneme-yanılmayla; uyduda çok sınıflı problem ile İHA'da ikili problem doğrudan karşılaştırılamıyor; ÇATI özelinde değerlendirme yok; kutu istemi uydu görüntüsünde nesnenin kendi şekil dosyasından alınmış (kutu = nesnenin çevreleyen dikdörtgeni) ama kutuyla birlikte ek süzgeç (ör. ayak iziyle kesişim) denenmemiş; çok spektral bantlar kapsam dışı.
BIZIM PROJEYE — DİKKAT, NÜANSLI:
- Önceki "Osco kutu istemini destekliyor" ifademiz DÜZELTİLMELİ: Osco, BİNA/EV gibi geometrisi belirgin nesnelerde (yüksek çözünürlükte) kutunun en iyi olduğunu, ama 0,3–0,5 m UYDU görüntüsünde kutunun sınırı aştığını ve noktanın daha iyi olduğunu buluyor. Bizim görüntümüz 0,234–0,34 m (WV02 0,5 m) → tam bu sınırda.
- Bu bulgu bizim tasarımımızı aslında DOĞRULUYOR: ham SAM maskemiz ayak izinden 1,21× büyük çıktı (kutu taşması + cephe + gölge) ve biz bunu "SAM ∩ oturtulmuş ayak izi" kesişimiyle düzelttik → son çatı ≈ ayak izi × 1,00. Tezde şöyle yazılmalı: "Osco vd. (2023) uydu çözünürlüğünde kutu isteminin nesne sınırını aşma eğiliminde olduğunu göstermiştir; bu nedenle SAM çıktısı ayak iziyle kesiştirilerek kısıtlanmıştır."
- Önerilen iyileştirme: kutu + merkez NOKTA istemini birlikte vermek (SAM ikisini birlikte kabul ediyor); küçük çatılarda (<150 m², doğrulamada en zayıf %72,6) özellikle denenebilir.
- 30 cm üstü çözünürlükte düşüş → WV02 (0,5 m) çekimindeki 502 binanın ayrıca raporlanması ve sınırlılıklarda "çözünürlük 30 cm eşiğinin çevresinde" notu.
- Gölgenin maskeye katılması → bizim gölge maskesiyle SAM maskesini ayrıştırmamız gerekçelendi; doğrulamada "taşmış" sınıfının kaynağı.
- PerSAM-F tek örnek ince ayarı (2 parametre, 10 sn) → etiketli veri olmadan düşük maliyetli iyileştirme yolu; ilerisi için öneri. samgeo paketi alternatif araç olarak anılabilir.
