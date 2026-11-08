# Çatı GES — Veri Paketi

Kapsam: **Atatürk OSB** (pilot, sanayi çatıları) + **Çiğli'deki devlet okulları ve devlet hastaneleri**.
Amaç: bu çatıların güneş paneline uygunluğunu analiz etmek. **Gölge analizi ve toplumsal ihtiyaç endeksi kapsam dışı** (15 Ekim 2026 hoca kararı) — bu yüzden bina yüksekliği ve mahalle/sosyal veriler pakette yok.
İndirme tarihi: 14 Ekim 2026, kamu seçimi 15 Ekim 2026. Koordinatlar her yerde **WGS84 (EPSG:4326)**, alanlar m².

## Önce şunu aç
1. **`01_harita/onizleme_haritasi.html`** → çift tıkla, tarayıcıda açılır. Uydu görüntüsü üstünde OSB binaları ve okul/hastaneler; binaya tıklayınca tüm özellikleri görünür. (İnternet gerekir.)
2. **`01_harita/catigunes_veri.gpkg`** → QGIS'e sürükle-bırak. Tüm katmanlar tek dosyada.
3. **`02_tablolar/cati_listesi.xlsx`** → **analize girecek çatılar**: OSB 1.447 çatı, kamu 62 çatı (2 hastane + 36 okul). Modeli bu listeyle kurun.
4. **`05_cati_kesitleri/`** → **SAM girdisi**: her çatı için hizalanmış görüntü kesiti + `indeks.csv` (kutu istemi piksel olarak hazır). Ham karolarla uğraşmayın.

## Klasörler

### 01_harita
`catigunes_veri.gpkg` katmanları:

| Katman | Kayıt | Ne |
|---|---|---|
| sinirlar | 2 | Çiğli ilçesi (131,98 km²) + Atatürk OSB (6,63 km²) |
| osb_binalari_osm | 1.428 | OSB bina ayak izleri (OSM) — **birincil** |
| cigli_binalari_osm | 22.432 | Çiğli bina ayak izleri (OSM) |
| **osb_catilari** | 1.447 | **analize girecek OSB çatıları**: 1.345 OSM + 102 yalnız Microsoft'ta olan (`ayak_izi_kaynagi`, `dogrulama`); tank, sayvan, sera, < 30 m² çıkarıldı; `sektor_notu` dolu = sanayi dışı bina |
| **kamu_catilari** | 62 | **analize girecek kamu çatıları**: her satır bir bina, `kurum_ad` hangi okul/hastane; `eslesme` nasıl bulundu; `gorsel_kontrol` görüntüde sorun |
| kamu_okul_hastane | 64 | **kapsamdaki** devlet okul + hastane kayıtları (kampüs ve bina poligonları + birkaç nokta); `tur`, `gerekce` (neden kamu sayıldı) |
| kamu_kontrol_meb | 13 | mülkiyeti OSM'den çıkmayan okul kayıtları — MEB listesiyle bakılacak, şimdilik **kapsam dışı** |
| osb_binalari_ms / cigli_binalari_ms | 1.384 / 17.256 | Microsoft ayak izleri — çapraz kontrol |
| iaosb_firmalar | 775 | OSB firmaları: NACE + adres (geometrisiz tablo) |

### 02_tablolar
- `cati_listesi.xlsx` — **çatı listesi**: OSB_catilari, Kamu_catilari, Kamu_kurum_ozeti, Elenenler (neden), Ayak_izi_yok
- `goruntu_kalite.xlsx` — her uydu karosu: çatı kaplaması, gerekli/kenar/gereksiz, netlik, karanlık oranı, çekim bloğu; `goruntu_ornek/` her sınıftan örnek
- `gorsel_kontrol.csv` — kamu çatılarının görsel kontrol kararları (bina_yok → listeden çıkar; goruntu_kotu / agac_alti / sekil_uyumsuz → işaret). **Claude işaretledi, bir kişi teyit etmeli**; dosyayı düzeltip `scripts/cati_listesi.py`'yi yeniden çalıştırın
- `osm_eksik_ms_binalari.geojson` — OSB'de Microsoft'ta olup OSM'de olmayan 532 bina (102'si aday çatı oldu)
- `ham_ozellikler.xlsx` — kamu ve OSB kayıtlarının analizde kullanılan OSM etiketleri (7 sütun). Diğer etiketler (ödeme, telefon, marka…) yalnız `…_etiket_sozlugu` sayfasında listelenir; tam hali `03_ham/osm/*.json`
- `bina_verileri.xlsx` — sadeleştirilmiş: konum, taban alanı, tür, kat; kamu okul+hastane; firmalar; PVGIS özet/aylık/TMY örneği
- `kamu_secim_kontrol.xlsx` — 208 ham kamu kaydının her biri için karar (kapsamda / kontrol / özel diye çıkarıldı / okul-hastane değil) + gerekçe
- `ornek_kayitlar.json` — kayıtların dict yapısına örnek

### 03_ham (dokunulmamış kaynak dosyalar)

| Klasör | İçerik |
|---|---|
| `sinir/` | sınırlar + Overpass ham cevabı |
| `osm/` | `overpass_bina_ham_*.json` (ham dict: type, id, bounds, geometry, **tags**) + `binalar_*.geojson` |
| `ms/` | Microsoft ayak izleri (bölgeye kırpılmış) |
| `pvgis/` | iki bölge için: `tmy` (tipik yıl, saatlik), `ufuk` (ufuk profili), `aylik_isinim` (2005–23), `pv_*` (yıllık üretim: 10° güney / optimum / doğu-batı), **`saatlik_egim10_guney`** (1 kWp, 2020–23, 35.064 saat) |
| `goruntu/` | Esri uydu karoları z19 (piksel 0,23 m, **gerçek çözünürlük 0,34–0,5 m** → yukarı örneklenmiş). Pakette yalnız çatı içeren + çatı kenarındaki karolar (OSB 1.630, kamu 190); yol/boş arsa/tampon karoları (919) çıkarıldı, yerelde duruyor. Dosya adı `19_x_y.jpg` = XYZ (Web Mercator) karo no; tam liste `_karo_listesi.json` |
| `iaosb/` | firma listesi `iaosb_firmalar.csv`, elektrik dağıtımı sayfası, GES başvuru şartları PDF |
| `tarife/` | EPDK tarife tablosu (4 Nisan 2026) |
| `dogrulama/` | İzmir BB'nin lisanssız GES'leri + 26 tesis doğrulama tablosu (kWh/kWp) |
| `envanter.json` | her veri setinin kaynağı, lisansı, indirme tarihi |

### 05_cati_kesitleri
- `osb/`, `kamu/` — her çatı için `<id>.jpg` (çatı + 15 m çevre) + `<id>.jgw` (world file, EPSG:3857 → QGIS'te konumlu açılır)
- `indeks.csv` — satır başına bir kesit: `kutu_px` (SAM kutu istemi, [x0,y0,x1,y1]), `poligon_px` (hizalanmış ayak izi), `yer_m_px` (metre/piksel; alan = piksel × yer_m_px²), `blok_kayma_*`, `ince_*`, `hizalama_kazanci`, `cekim_tarihi`, `uydu`, `gercek_cozunurluk_m`
- `kayma_bloklari.csv` — blok başına ölçülen kayma; `kontrol_ornek.jpg` — sarı: blok kayması, mor: ince ayar sonrası

### 04_kamu_secimi
`kamu_okul_hastane_cigli.geojson` (kapsam) + `kamu_belirsiz_kontrol.geojson` (MEB ile bakılacak). Her kayıtta ham OSM etiketleri `etiketler` alanında.

## Bilmeniz gerekenler (model kurarken)
- **Bina türü OSM'de zayıf:** OSB'de %64, Çiğli'de %91 binada `building=yes` (tür girilmemiş). OSB'de her bina sanayi kabul edilir, sektör firma listesinden (NACE) gelir; kamu türü `kamu_okul_hastane` katmanından.
- **Kampüs ≠ çatı — çözüldü.** 64 kamu kaydı = 30 kampüs (bahçe) sınırı + 32 bina + 2 nokta; 64 kurum DEĞİL. `kamu_catilari` kampüslerin içindeki binaları bulur, aynı binayı bir kez sayar → **2 hastane (Çiğli EAH, İKÇÜ Diş Hekimliği Hastanesi) + 36 okul, 62 çatı, ~65.800 m² taban** (görsel kontrolle 3 çatı çıktı; Şehit Uğur Yıldız Ortaokulu'nun binası görüntüde yok → `Ayak_izi_yok` sayfasında, MEB'e sorulacak). Evka 6 İlkokulu kampüsünde OSM binası yok → Microsoft ayak izi kullanıldı (`ayak_izi_kaynagi=Microsoft`). Adsız kampüs way/93219910 = Cahide Ahmet Dalyanoğlu Ortaokulu + Turan Çakın İÖO'nun **ortak bahçesi** (3 çatı, `kurum_ad` 'ortak kampus: …').
- **OSB'ye Microsoft'tan 102 çatı eklendi:** OSB sınırında Microsoft'ta olup OSM'de hiç olmayan 532 bina vardı; ≥ 100 m² ve en kısa kenarı ≥ 8 m olan 102'si (64.300 m², OSB çatı alanının ~%3'ü) aday çatı. En büyükleri görüntüde gerçek fabrika çatısı; ince şeritler (duvar, sundurma) alınmadı. `dogrulama` sütunu: görüntüden teyit edin.
- **OSB'de çatı olmayanlar çıkarıldı:** 52 depolama tankı, 2 sayvan, 1 sera, 28 yapı < 30 m². 13 binada sanayi dışı işlev var (anaokulu, poliklinik, itfaiye, banka, cami, kafe, SGK) → tüketimleri ayrı ele alınmalı.
- **Ayak izi doğruluğu (Microsoft ile karşılaştırma, `ms_iou` / `ms_durum`):** OSB çatılarının %99,3'ü (alanca) Microsoft'ta da var; MS'te olmayan 93 çatı küçük (medyan 74 m²). Medyan IoU düşük (OSB 0,21) ama sebep hata değil: **MS bitişik binaları birleştiriyor** (eşleşen MS poligonu medyanda OSM binasının 2,8 katı). Boyutu benzer 445 çiftte IoU medyanı 0,67.
- **⚠️ Ayak izleri görüntüye 1–4 m kayık — `05_cati_kesitleri`'nde düzeltildi.** Kayma görüntü bloğuna göre değişiyor (Esri görüntüsünden ölçüldü, `05_cati_kesitleri/kayma_bloklari.csv`): OSM, Ocak 2026 bloğunda doğu +1,4 / kuzey −2,3 m; Ekim 2025 bloğunda doğu +2,8 / kuzey +0,5 m; Microsoft ayak izleri de Esri'ye göre ~3–4 m kayık (Bing görüntüsüyle çizilmişler). Üstüne her çatıya ±3 m ince ayar (çok katlı okullarda eğik bakış kayması). **Kesitlerdeki `kutu_px` / `poligon_px` hizalanmış koordinatlardır; GeoPackage'daki ayak izleri ham, hizasızdır.**
- **Ayak izi ≠ bugünkü bina:** OSM ve Microsoft görüntüden eski olabilir. Kamu kontrolünde 3 poligonun yerinde bina yok (Şehit Uğur Yıldız Ortaokulu — okulun tek binası; Selim Diniz'de yıkıntı; ortak bahçede saha) → çıkarıldı. OSB'de aynı kontrol yapılmadı (1.447 çatı) — SAM maskesi boş/çok küçük çıkan çatılar bu tür kayıtlardır, öyle işaretleyin.
- **Yalnız devlet kurumları.** Özel okul/hastaneler çıkarıldı; ASM, poliklinik ve üniversite binaları "okul/hastane" sayılmadı. Neyin neden çıktığı `kamu_secim_kontrol.xlsx`'te.
- **PVGIS kontrol:** OSB 10° güney 1.477, optimum 1.580 kWh/kWp; Çiğli 1.514 / 1.624. İzmir BB GES medyanı 1.453 ile tutarlı.
- **Azimut tuzağı:** PVGIS'te 0 = güney; pvlib'de 0 = kuzey (güney = 180).
- **İAOSB elektriği kendisi dağıtıyor** (faturalama + uzaktan sayaç okuma, GES başvurusu da İAOSB'ye). Tüketim verisi talebi İAOSB'ye yapılacak.
- Firma listesinde şahıs firması adları var → raporda/arayüzde isim yerine sektör (NACE) kullanın.
- Lisans/atıf: OSM ve Microsoft ODbL; Esri görüntüsü ticari olmayan kullanım + atıf; PVGIS (JRC) atıf.

- **Uydu görüntüsü:** çoğu alan **14 Ocak 2026** (Legion-3, 0,34 m); OSB'nin güneyi (~600 karo) **12 Ekim 2025** (WorldView-2, 0,5 m — daha bulanık, netlik medyanı %20 düşük). Bozuk, boş ya da tekrar eden karo **yok**; 6 kesitte kenarda karo eksik (`eksik_karo`). Kış görüntüsü → uzun gölge: kuzey tarafı karanlık çatılar ve ağaç altı okullar (Balatçık, Münevver Öğretmen) segmentasyonda zor. Çekim bilgisi yalnız 34 örnek noktada (`_cekim_bilgisi.json`) → blok sınırına yakın çatılarda tarih yaklaşık.
- **Mevcut GES'ler:** OSM'de OSB'de yalnız 1 çatı GES'i (Tariş, 0,7 MW) işaretli — gerçekte çok daha fazlası var. Dolu çatılar görüntüden ayıklanmalı. Ham: `03_ham/osm/overpass_gunes_mevcut_ham.json`.

## Henüz elimizde olmayanlar
- Bina bazında elektrik tüketimi (İAOSB, İBB, İl MEM/Sağlık'tan yazıyla istenecek)
- EPİAŞ saatlik tüketim profil katsayıları (Şeffaflık Platformu üyeliği gerekiyor)
- MEB ve İl Sağlık resmî listeleri — 13 kontrol kaydını kapatmak ve OSM'de eksik devlet okulu/hastanesi var mı görmek için
- Lisanssız Elektrik Üretim Yönetmeliği PDF'i

## Eksiksiz geldi mi?
`MANIFEST.csv` paketteki her dosyanın adını, boyutunu ve sha256 özetini listeler. Zip'i açarken hata çıkmadıysa ve klasördeki dosya sayısı MANIFEST'teki satır sayısı + 1 ise (MANIFEST'in kendisi) paket tamdır: 4.897 dosya.
