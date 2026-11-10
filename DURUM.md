# Proje durumu

Her üye kendi bölümünün en üstüne tarihli madde ekler. Başkasının bölümüne yazılmaz.

## Genel durum (8 Kasım 2026)
- **Veri aşaması bitti (30 Ekim):** 1.085 çatı, toplam çatı alanı 2.244.145 m², kullanılabilir alan 1.963.378 m².
- **Üretim ve ekonomi bitti (8 Kasım):** 1.021 çatıda 177,7 MWp, 263 GWh/yıl, yatırım 4,40 milyar TL, NPV 4,17 milyar TL.
- **Belirsizlik:** 10.000 senaryoda NPV ortanca değeri 2,47 milyar TL, senaryoların %80'i 0,71–4,47 milyar TL arasında.
- **Ara rapor:** Teslime hazır, 24 sayfa. Kapaktaki öğrenci numaraları dolacak. Teslim 13 Kasım.

## Takvim
| Tarih | İş |
|---|---|
| 11 Kasım 17:30 | TÜBİTAK 2209-A son başvuru ve danışman onayı |
| 13 Kasım | Ara rapor teslimi |
| 16–23 Kasım | TÜBİTAK 2209-A kuruluş e-imzası |
| 11 Aralık | REST API, web harita, LLM açıklama katmanı |
| 21 Aralık | Tez metni ve final teslimi |

## Açık işler
- [ ] REST API (Dorukhan)
- [ ] Web harita (Yavuz)
- [ ] LLM açıklama katmanı (Dorukhan)
- [ ] Kurulum maliyeti için gerçek firma teklifleri; bakım gideri ve iskonto oranı için kaynak (Bilal)
- [ ] Tez metni (Yiğit koordinasyonunda, herkes). 4.5 firma eşleştirmesi KARARLAR.md'deki 10 Kasım maddesine göre yazılacak
- [ ] Colab defterlerini tek akışta birleştirmek (final için)

## Bilal
- 2026-11-10: Repo herkese açık çıktı, özele çevrildi. Dört üyenin erişimi değişmedi.
- 2026-11-10: Ara rapor kaynakçası denetlendi: 36 kaynağın linki ve DOI'si çalışıyor, DOI başlıkları Crossref ile eşleşiyor. Rapor teslime hazır, yalnız kapaktaki öğrenci numaraları kaldı.
- 2026-11-10: Sonuç defteri denetlendi, hata yok. Defter hesap yapmaz, `cati_npv.csv` dosyasını gösterir; hesap `proje/scripts/uretim_hesabi.py` ve `npv_hesabi.py` dosyalarındadır. Finale not: 1.021 çatının hepsinde NPV pozitif (%100 öz tüketim varsayımı), 16 çatı 5 kWp'nin altında (uygunluk analizinde alt eşik düşünülebilir), harita rengi NPV/kWp büyük ölçüde tarife grubunu gösterir.
- 2026-11-08: Eksikler yüklendi: güncel TÜBİTAK önerisi (`raporlar/`), `CALISMA_NOTLARI.md`, `kamu_binalari/`, `proje/cizim_paketi/`, çalışma rehberi ve 2209-A belgeleri.
- 2026-11-08: Colab defterleri çıktılarıyla `proje/notebooks/colab/` altına eklendi. Dünkü sonuç defteri `sonuc_uretim_npv_harita_2026-11-07.ipynb`; açma adımları `README.md`'de.
- 2026-11-08: Üretim, NPV ve Monte Carlo tamamlandı, ara rapor teslime hazırlandı. Çıktılar `ekonomi/` ve `uretim/` klasörlerinde.

## Yiğit

## Dorukhan

## Yavuz
