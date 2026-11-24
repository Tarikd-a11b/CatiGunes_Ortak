# API ve web harita sözleşmesi

Dorukhan ve Yavuz'un aynı alan adlarıyla çalışması içindir. Veri alanları mevcut dosyalardan alınmıştır. Uç noktalar **öneridir**, ikisi anlaşınca kesinleşir. Değişiklik olursa bu dosya aynı commit'te güncellenir.

## Veri kaynakları
Veri klasörü: bu repoda `model_verisi/`.

| Dosya | Satır | İçerik |
|---|---|---|
| `catilar.gpkg`, katman `cati_son` | 1.085 | Son çatı geometrisi, EPSG:4326 |
| `catilar.gpkg`, katman `uygun_alan` | 1.021 | Panel konabilecek alan, EPSG:4326 |
| `ekonomi/cati_npv.csv` | 1.085 | Çatı başına ekonomi sonuçları ve sıralar |
| `ekonomi/mc_cati.csv` | 1.021 | Çatı başına belirsizlik sonuçları |
| `uygunluk/cati_uygunluk.csv` | 1.085 | Çatı başına uygunluk sonucu ("panel kurulabilir mi?") |
| `uretim/cati_uretim.csv` | 1.085 | Alan ve üretim |
| `firmalar/firma_cati_eslesme.csv` | | Firma–çatı eşleşmesi |

Tüm dosyalar `cati_id` (tam sayı) ile birleşir.

## Değerler
| Alan | Değerler |
|---|---|
| `bolge` | `ataturk_osb` (1.005), `cigli_kamu` (80) |
| `tur` | `sanayi` (997), `okul` (48), `universite` (29), `sanayi_disi` (8), `hastane` (3) |
| `panel_durumu` | `panel_yok` (996), `tam_dolu` (64), `kismi_panel_dusuldu` (25) |
| `geometri_kaynagi` | `sam` (828), `insan` (160), `ayak_izi` (97) |
| `supheli` | `true` (128), `false` (957) |

## Arayüzde gösterilecek ana alanlar
| Alan | Birim | Anlamı |
|---|---|---|
| `cati_alan_m2`, `uygun_alan_m2` | m² | Çatı alanı, kullanılabilir alan |
| `kwp_merkez` | kWp | Kurulu güç (temel senaryo) |
| `kwh_merkez` | kWh/yıl | Yıllık üretim |
| `yatirim_TL` | TL | Kurulum maliyeti |
| `npv_TL` | TL | Net bugünkü değer |
| `geri_odeme_yil` | yıl | Geri ödeme süresi |
| `sira_npv`, `sira_npv_kWp`, `sira_uretim` | sıra | Çatının sıralamadaki yeri |
| `npv_p10`, `npv_p50`, `npv_p90` | TL | Belirsizlik aralığı (`mc_cati.csv`) |
| `p_npv_poz` | oran | Senaryolarda NPV'nin pozitif çıkma payı |
| `ilk50_hepsi` | oran | Senaryolarda ilk 50'de kalma payı |

## Boş değerler
- `tam_dolu` olan 64 çatıda `kwp_merkez` 0'dır; ekonomi alanları ve sıralar boştur (NaN). API bunları `null` döndürmeli.
- Harita bu çatıları "mevcut GES, potansiyel yok" olarak göstermeli. Sıfır NPV gibi göstermemeli.
- Bu 64 çatı `uygun_alan` katmanında ve `mc_cati.csv`'de yoktur.

## Uygunluk alanları (`uygunluk/cati_uygunluk.csv`)
Betikle üretilir: `proje/uygunluk_modeli/predict_all_roofs.py`. Elle değiştirilmez.

| Alan | Değer | Anlamı |
|---|---|---|
| `p_uygun_rf`, `p_uygun_xgb`, `p_uygun_et` | 0–1 | Random Forest / XGBoost / Extra Trees'e göre "uygun" olasılığı |
| `uygun_rf`, `uygun_xgb`, `uygun_et` | 1 / 0 | Karar (olasılık ≥ 0,5 ise 1) |
| `uygun_kural` | 1 / 0 | Kural sonucu (tam dolu GES veya net alan < 100 m²), yalnız karşılaştırma |
| `karar_kaynagi` | `model`, `kural_tam_dolu_GES` | Tam dolu GES'li 64 çatıda karar kuraldan gelir, olasılık boştur |
| `etiket_kumesi` | `egitim`, `test`, `yok`, `cati_degil` | Çatı elle etiketlendi mi |
| `el_etiketi` | 1 / 0 / boş | Elle verilen etiket |
| `cati_degil` | true / false | Etiketlemede çatı olmadığı görülen kayıtlar (1076, 1391) |

- Ana modelin hangisi olacağı (RF mi Extra Trees mi) hocanın incelemesinde. Karar çıkana kadar arayüz ikisinden birini sabit kullanmasın, alan adını tek yerden değiştirilebilir tutsun.
- `cati_degil` true olan kayıtlar haritada uygunluk rengiyle gösterilmemeli.
- Eğitim çatılarındaki model tahmini, modelin bu çatıları görmüş olması nedeniyle başarı göstergesi değildir.

## Önerilen uç noktalar
| Uç nokta | Döndürdüğü |
|---|---|
| `GET /catilar?bolge=&tur=&limit=` | GeoJSON, harita için özet alanlar |
| `GET /catilar/{cati_id}` | Tek çatının tüm alanları |
| `GET /siralama?olcut=npv\|npv_kwp\|uretim&tur=&limit=` | Sıralı liste |
| `GET /ozet` | Bölge ve tür toplamları |
| `GET /catilar/{cati_id}/aciklama` | LLM açıklama metni |

LLM katmanı yeni hesap yapmaz. Yalnız bu alanları okuyup metne çevirir ve metindeki sayılar kayıtla eşleşmelidir.
