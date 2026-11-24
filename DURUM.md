# Proje durumu

Her üye kendi bölümünün en üstüne tarihli madde ekler. Başkasının bölümüne yazılmaz.

## Genel durum (8 Kasım 2026)
- **Veri aşaması bitti (30 Ekim):** 1.085 çatı, toplam çatı alanı 2.244.145 m², kullanılabilir alan 1.963.378 m².
- **Üretim ve ekonomi bitti (8 Kasım):** 1.021 çatıda 177,7 MWp, 263 GWh/yıl, yatırım 4,40 milyar TL, NPV 4,17 milyar TL.
- **Belirsizlik:** 10.000 senaryoda NPV ortanca değeri 2,47 milyar TL, senaryoların %80'i 0,71–4,47 milyar TL arasında.
- **Ara rapor:** Teslim edildi, hoca onayladı (14 Kasım). İngilizcesi `raporlar/Bitirme_Interim_Report_EN.docx/.pdf`, ödev sistemine bir kişinin yüklemesi yeterli.

## Takvim
| Tarih | İş |
|---|---|
| 11 Kasım 17:30 | TÜBİTAK 2209-A son başvuru ve danışman onayı |
| 13 Kasım | Ara rapor teslimi |
| 16–23 Kasım | TÜBİTAK 2209-A kuruluş e-imzası |
| 11 Aralık | REST API, web harita, LLM açıklama katmanı |
| 21 Aralık | Proje raporu ve final teslimi |

## Açık işler
- [ ] REST API (Dorukhan)
- [ ] Web harita (Yavuz)
- [ ] LLM açıklama katmanı (Dorukhan)
- [ ] Kurulum maliyeti için gerçek firma teklifleri; bakım gideri ve iskonto oranı için kaynak (Bilal)
- [ ] Proje raporu metni (Yiğit koordinasyonunda, herkes). 4.5 firma eşleştirmesi KARARLAR.md'deki 10 Kasım maddesine göre yazılacak
- [ ] Colab defterlerini tek akışta birleştirmek (final için)

## Bilal
- 2026-11-14: Hoca ara raporu onayladı; "tez yazımı" geçen yerlerin "proje raporu yazımı" olmasını ve İngilizcesinin ödeve yüklenmesini istedi. `raporlar/Bitirme_Ara_Rapor_Teslim.docx` düzeltildi (§6, §7, Şekil 3 Gantt), İngilizcesi `raporlar/Bitirme_Interim_Report_EN.docx` ve `.pdf` eklendi (28 sf, şekiller İngilizce). Repodaki kopyalarda öğrenci numarası yok; ödeve yüklenecek numaralı hali Bilal'de. Finalde "tez" değil "proje raporu" dili kullanılacak.
- 2026-11-10: Repo herkese açık çıktı, özele çevrildi. Dört üyenin erişimi değişmedi.
- 2026-11-10: Ara rapor kaynakçası denetlendi: 36 kaynağın linki ve DOI'si çalışıyor, DOI başlıkları Crossref ile eşleşiyor. Rapor teslime hazır, yalnız kapaktaki öğrenci numaraları kaldı.
- 2026-11-10: Sonuç defteri denetlendi, hata yok. Defter hesap yapmaz, `cati_npv.csv` dosyasını gösterir; hesap `proje/scripts/uretim_hesabi.py` ve `npv_hesabi.py` dosyalarındadır. Finale not: 1.021 çatının hepsinde NPV pozitif (%100 öz tüketim varsayımı), 16 çatı 5 kWp'nin altında (uygunluk analizinde alt eşik düşünülebilir), harita rengi NPV/kWp büyük ölçüde tarife grubunu gösterir.
- 2026-11-08: Eksikler yüklendi: güncel TÜBİTAK önerisi (`raporlar/`), `CALISMA_NOTLARI.md`, `kamu_binalari/`, `proje/cizim_paketi/`, çalışma rehberi ve 2209-A belgeleri.
- 2026-11-08: Colab defterleri çıktılarıyla `proje/notebooks/colab/` altına eklendi. Dünkü sonuç defteri `sonuc_uretim_npv_harita_2026-11-07.ipynb`; açma adımları `README.md`'de.
- 2026-11-08: Üretim, NPV ve Monte Carlo tamamlandı, ara rapor teslime hazırlandı. Çıktılar `ekonomi/` ve `uretim/` klasörlerinde.

## Yiğit
- 2026-11-24: Uygunluk sonucu 1.085 çatının tamamı için üretildi: `model_verisi/uygunluk/cati_uygunluk.csv` (betik `proje/uygunluk_modeli/predict_all_roofs.py`), alanlar `API.md`'de. RF, XGBoost ve Extra Trees üçü birden yazıldı, ana model kararı hocada. Uygun değil sayısı: RF 152, XGBoost 224, Extra Trees 235, kural 147 (çatı olmayan 2 kayıt hariç). Test skorları değişmedi.
- 2026-11-24: Uygunluk modeli (aşama 1, "panel kurulabilir mi?") `proje/uygunluk_modeli/` altına eklendi: kod, girdi verisi, 200 elle etiketli eğitim çatısı, 111 test etiketi ve sonuçlar. Ana sonuç (110 test çatısı, 15 tohum ortalaması): RF macro F1 0.854, "uygun değil" F1 0.756; kural (tam dolu GES veya net alan < 100 m²) 0.867 / 0.778; fark anlamlı değil. 100 m² eşiği ekip kararı değil, yalnız karşılaştırma için. Kurulum `requirements.txt` ile (scikit-learn sürümü RF sonucunu değiştiriyor). Bilal'e veri notu: çatı olmayan kayıtlar 1076 ve 1391. ExtraTrees (öneride yok, ek karşılaştırma) macro F1 0.895, "uygun değil" F1 0.829 ile kuralın üstünde ve sonucu tohumdan bağımsız; ana model olarak kullanılması hocanın incelemesine bağlı.

## Dorukhan

## Yavuz
