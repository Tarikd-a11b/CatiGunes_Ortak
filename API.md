# API ve web harita sözleşmesi

Dorukhan ve Yavuz'un aynı alan adlarıyla çalışması içindir. Veri alanları mevcut dosyalardan alınmıştır. Uç noktalar **öneridir**, ikisi anlaşınca kesinleşir. Değişiklik olursa bu dosya aynı commit'te güncellenir.

## Veri kaynakları
Veri klasörü: `CatiGunes_Model_Verisi` (Drive bağlantısı: eklenecek).

| Dosya | Satır | İçerik |
|---|---|---|
| `catilar.gpkg`, katman `cati_son` | 1.085 | Son çatı geometrisi, EPSG:4326 |
| `catilar.gpkg`, katman `uygun_alan` | 1.021 | Panel konabilecek alan, EPSG:4326 |
| `ekonomi/cati_npv.csv` | 1.085 | Çatı başına ekonomi sonuçları ve sıralar |
| `ekonomi/mc_cati.csv` | 1.021 | Çatı başına belirsizlik sonuçları |
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

## Önerilen uç noktalar
| Uç nokta | Döndürdüğü |
|---|---|
| `GET /catilar?bolge=&tur=&limit=` | GeoJSON, harita için özet alanlar |
| `GET /catilar/{cati_id}` | Tek çatının tüm alanları |
| `GET /siralama?olcut=npv\|npv_kwp\|uretim&tur=&limit=` | Sıralı liste |
| `GET /ozet` | Bölge ve tür toplamları |
| `GET /catilar/{cati_id}/aciklama` | LLM açıklama metni |

LLM katmanı yeni hesap yapmaz. Yalnız bu alanları okuyup metne çevirir ve metindeki sayılar kayıtla eşleşmelidir.
