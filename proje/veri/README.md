# Uygulama fazı veri paketi (2026-10-14)

> **2026-10-16 düzen:** kalıcı yalnız iki hal var — **`veri/ham/`** (ilk indirilen ana veri, elle dokunulmaz) + `veri/elle/` (insan kararları: görsel kontrol) → **son hal `Desktop\CatiGunes_Model_Verisi\`**. Ara klasörler (`veri/islenmis`, `veri/inceleme`) ve eski paketler (v1–v3) kaldırıldı; son hali yeniden kurmak için: `python scripts/kur.py`.

Kapsam: **Atatürk OSB** (pilot, sanayi çatıları) + **Çiğli'deki devlet okulları ve devlet hastaneleri**.
Amaç: bu çatıların güneş paneline **uygunluğunu** analiz etmek.

> **2026-10-15 kapsam daraltma (hoca kararı):** kamu tarafında yalnız **okul + hastane**, **özel kurum yok** ·
> **gölge analizi çıkarıldı** → 3D-GloBFP yükseklikleri gereksiz · **toplumsal ihtiyaç endeksi çıkarıldı**
> (kamu binasında GES zaten kamu yararı) → sosyal veriler gereksiz. Bunlar silinmedi, `veri/arsiv_kapsam_disi/`'e taşındı.
> Kamu seçimi: `python scripts/kamu_okul_hastane.py` → `veri/islenmis/` + karar tablosu `veri/inceleme/kamu_secim_kontrol.xlsx`.
Makine-okunur envanter: `envanter.json`. Yeniden üretme: `python scripts/uygulama_veri_indir.py hepsi`
(+ `scripts/globfp_kirp.py`, `scripts/iaosb_firmalar.py`). Ham veriye elle dokunulmaz; işlenmiş çıktılar `veri/islenmis/`'e.

## İndirilen (veri/ham/)

| Klasör | İçerik | Kaynak / lisans | Ne için |
|---|---|---|---|
| `sinir/` | Çiğli ilçe (rel 1268482, 131,98 km²) + Atatürk OSB (rel 10166289, admin_level 8, 6,63 km²) | OSM, ODbL | çalışma alanı |
| `osm/` | OSM binaları — Çiğli 22.432 (6,07 km² taban), OSB 1.428 (2,25 km²); **tüm etiketler** (height, building:levels, roof:*) | OSM, ODbL | ayak izi (birincil) |
| `kamu/` | Çiğli kamu hizmeti tesisleri, 208 kayıt — **ham**, özel kurumları da içerir | OSM, ODbL | yalnız süzme girdisi; kullanılacak liste `veri/islenmis/kamu_okul_hastane_cigli.geojson` (64 kayıt: 3 hastane + 61 okul) |
| `ms/` | Microsoft ayak izleri (Çiğli 17.256, OSB 1.384) | MS GlobalMLBuildingFootprints, ODbL | çapraz kontrol |
| `pvgis/` | her bölge için TMY, ufuk profili, aylık ışınım 2005–23, yıllık PV (10° güney / optimum / doğu-batı), **saatlik 1 kWp üretim 2020–23** | PVGIS 5.3, SARAH3 | üretim + saatlik öz tüketim |
| `goruntu/` | Esri World Imagery z19 (~0,23 m/piksel): OSB 2.089 karo, okul+hastane çevresi 650 karo | Esri, ticari olmayan + atıf | SAM çatı segmentasyonu |
| `iaosb/` | firma rehberi 775 firma (NACE 501, adres 762), elektrik dağıtımı sayfası, GES başvuru şartları PDF | iaosb.org.tr | sektör → tüketim yoğunluğu; firma↔çatı eşleşmesi |
| `tarife/` | EPDK tarife tablosu 2026-04-04 | EPDK | NPV |
| `dogrulama/` | İBB lisanssız GES listesi + 26 tesis doğrulama tablosu | İBB açık veri | kWh/kWp doğrulama |

PVGIS kontrol: OSB 10° güney 1.477, optimum 1.580 kWh/kWp; Çiğli 1.514 / 1.624 → İBB 26 GES medyanı 1.453 ile tutarlı.
**Azimut tuzağı:** PVGIS 0 = güney, pvlib 0 = kuzey.

## İşlenmiş (veri/islenmis/)

| Dosya | İçerik |
|---|---|
| `kamu_okul_hastane_cigli.geojson` | **kapsamdaki** kamu binaları: Çiğli EAH, İKÇÜ Diş Hekimliği Fak. Hastanesi (+ binası), MEB okul kampüs/bina kayıtları, 2 kamu anaokulu (İBB Yuvamız İzmir, İKÇÜ Çelebi) |
| `kamu_belirsiz_kontrol.geojson` | 13 kayıt: adsız okul poligonu (9) + mülkiyeti belirsiz anaokulu (4) — MEB listesiyle bakılıp ya kapsama ya çıkarılacak |

Çıkarılanlar: 30 özel kurum (7 özel hastane/tıp merkezi, 23 kolej/özel okul kaydı) + okul/hastane olmayan 101 kayıt (ASM, poliklinik, klinik, üniversite binası, ibadethane, PTT…).
Mülkiyet kuralı: işletmeci (MEB/Sağlık Bak./devlet üniversitesi) → meb.k12.tr sitesi → ad (Özel/Kolej = özel; İlkokulu/Ortaokulu/Lisesi = MEB) → adsız bina, kampüsünden miras. Elle kararlar betikte gerekçeli.

## Önemli bulgu: İAOSB kendi elektrik dağıtıcısı
İAOSB kendi şebekesini işletiyor (ATAER TM, 2×140/160 MVA), faturalama yapıyor, 2022'den beri sayaçlar uzaktan okunuyor
ve lisanssız GES başvurularını kendisi alıyor (`iaosb/iaosb_ges_basvuru.pdf`). → OSB tüketim verisi için muhatap **GDZ değil İAOSB Elektrik İşletme Birimi**.

## İndirilemeyen — elle / başvuruyla alınacak

| Veri | Neden indirilemedi | Yol |
|---|---|---|
| EPİAŞ profil katsayıları (saatlik tüketim şekli) | Şeffaflık API'si 401 — ücretsiz üyelik (TGT) gerekiyor | ekipten biri seffaflik.epias.com.tr'ye üye olsun, kullanıcı adı/şifre ile çekeriz |
| Lisanssız Elektrik Üretim Yönetmeliği | mevzuat.gov.tr bot koruması | tarayıcıdan PDF indir → `veri/ham/mevzuat/` |
| MEB resmî okul listesi (Çiğli) | meb.gov.tr JS bot koruması | tarayıcıdan veya İlçe MEM'den; **13 kontrol kaydını ve OSM'de eksik devlet okullarını** bununla kapat |
| İl Sağlık hastane listesi | açık liste bulunamadı | izmir.saglik.gov.tr — Çiğli'de OSM dışında devlet hastanesi kalıp kalmadığını doğrula |
| İAOSB parsel bazlı tüketim + sözleşme gücü (anonim) | kamuya açık değil | **İAOSB Elektrik İşletme Birimi'ne yazı** (hoca imzalı) |
| Kamu binaları yıllık elektrik tüketimi | açık veri yok | ETKB ENVER bildirimleri / İBB / İl MEM-Sağlık — bilgi edinme başvurusu |

## Notlar
- İAOSB firma listesinde şahıs firması adları kişisel veri sayılır → tezde/arayüzde anonim (NACE düzeyinde) kullan.
- Overpass büyük sorguda 504 veriyor; betik karolara bölüp önbellekliyor (`osm/karo/`), karo **asla sessizce atlanmaz**.
