# CatiGunes web veritabanı (v4)

Web haritası ve REST API'nin okuduğu PostgreSQL + PostGIS veritabanı. Veri `CatiGunes_Ortak/model_verisi/` klasöründen yüklenir.

## Tablolar

| Tablo | Satır (ara rapor verisi) | İçerik |
|---|---|---|
| `bolge` | 2 | Atatürk OSB ve Çiğli kamu: sınır poligonu, 1 kWp yıllık üretim |
| `tarama` | 1 | Bir veri yüklemesi. Aynı bölge yeniden taranırsa yeni satır eklenir, eskisi kalır |
| `cati` | 1.085 | Çatının değişmeyen kimliği: OSM numarası, bölge, tür, kurum adı |
| `cati_sonuc` | 1.085 | Çatının o taramadaki geometrisi, kullanılabilir alanı, kWp, kWh, NPV ve Monte Carlo aralığı |
| `cati_aciklama` | 10 | LLM yorumu (özet, sıra nedeni, belirsizlik, veri güvenilirliği). Şimdilik 10 deneme çatısında; `aciklama_uret.py` ile üretilir |

| Görünüm | İçerik |
|---|---|
| `v_cati` | Her çatının en güncel hali ve sıraları (`sira_npv`, `sira_uretim`, `sira_npv_kwp`, `sira_grup`). API ve harita bunu okur |
| `v_ozet` | Bölge × tür toplamları |

Sıralar tabloda saklanmaz, `v_cati` içinde güncel veriden hesaplanır. Yeni tarama yüklenince kendiliğinden güncellenir.

Tamamen panelli 64 çatıda `kwp` ve `kwh_yil` 0, ekonomi alanları NULL ve sıra yok. Harita bunları "mevcut GES" diye göstermeli.

## Kurulum

`uygulama/kur.bat` veritabanını kurar ve `yedek/catigunes_web.sql` dökümünü yükler (bkz. `uygulama/README.md`). Elle kurmak için:

```
docker exec catigunes_db psql -U postgres -c "CREATE DATABASE catigunes_web"
docker exec -i catigunes_db psql -U postgres -d catigunes_web -v ON_ERROR_STOP=1 < sema.sql
```

## Veri yükleme

```
python yukle.py ..\..\model_verisi <tarama_kodu> "aciklama" > yukleme.sql
docker exec -i catigunes_db psql -U postgres -d catigunes_web -v ON_ERROR_STOP=1 < yukleme.sql
```

Aynı tarama kodu tekrar yüklenmez. Düzeltilmiş veriyi aynı kodla yeniden yüklemek için `--yenile` eklenir; bu o taramanın sonuçlarını ve LLM açıklamalarını siler.

Python dışında paket gerekmez (veritabanı sürücüsü kullanılmaz).

## Örnek sorgular

```sql
-- Harita: en güncel çatılar
SELECT cati_id, tur, kwp, npv_tl, sira_grup, ST_AsGeoJSON(geom) FROM v_cati;

-- Sanayi öncelik listesi (ilk 20)
SELECT * FROM v_cati WHERE grup = 'sanayi' ORDER BY sira_grup LIMIT 20;

-- Bir çatının tüm taramalardaki hali
SELECT t.kod, s.uygun_alan_m2, s.panel_durumu, s.npv_tl
FROM cati_sonuc s JOIN tarama t USING (tarama_id) WHERE s.cati_id = 47 ORDER BY t.tarama_id;
```
