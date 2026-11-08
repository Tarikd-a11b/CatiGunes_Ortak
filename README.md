# CatiGunes_Ortak

Ekipteki herkesin Claude'unun projede neler olduğunu bilmesi için ortak notlar.

## Kurulum (bir kez)
1. GitHub davetini kabul et.
2. Git ve Claude Code kurulu olsun, sonra:
   ```
   git clone <repo adresi>
   cd CatiGunes_Ortak
   claude
   ```
3. Klasöre güven sorusunu onayla. Oturum başındaki otomatik `git pull` bundan sonra çalışır.

## Kullanım
- Claude'u bu klasörde başlat. `CLAUDE.md`'yi kendisi okur.
- Kod başka klasördeyse oradan `claude --add-dir ../CatiGunes_Ortak` ile başlat ve Claude'a `DURUM.md` dosyasını okumasını söyle.
- İş bitince: "Yaptığımızı DURUM.md'ye yaz ve pushla."

## Dosyalar
| Dosya | İçerik |
|---|---|
| `CLAUDE.md` | Claude'un çalışma kuralları |
| `DURUM.md` | Kim ne yaptı, sırada ne var |
| `KARARLAR.md` | Kapanmış ekip kararları |
| `API.md` | API ve web harita veri sözleşmesi |

| `proje/` | Kodlar, notebook'lar, ham ve işlenmiş veri, belgeler |
| `model_verisi/` | Son veri seti, üretim, NPV ve Monte Carlo çıktıları |
| `YONTEM.md` | Üretim, NPV ve Monte Carlo yöntemi |
| `raporlar/` | Ara rapor teslim dosyası ve TÜBİTAK önerisi |
| `kaynaklar/` | Makaleler; tezde kullanılan 11 kaynak `Tez_Kullanilan_11_Kaynak/` altında (`Isaretli/` notlu kopyalar) |
| `CALISMA_NOTLARI.md` | Veri kuralları, danışman notları, denenip bırakılanlar, tuzaklar |
| `kamu_binalari/` | Çiğli kamu binalarının ayrı paketi |
| `proje/cizim_paketi/` | LabelMe çizim paketi ve insan çizimleri |
| `proje/belgeler/CatiGunes_Calisma_Rehberi.pdf` | Ekip çalışma rehberi (5 sayfa) |
| `proje/belgeler/tubitak_2209a/` | 2209-A çağrı metni, bilgi notu, form ve araçlar |

Repo yaklaşık 950 MB; ilk `git clone` uzun sürebilir. Makaleler yalnız ekip içi kullanım içindir, repo herkese açılmamalı.

## Colab defterleri
Kayıtlı Colab defterleri `proje/notebooks/colab/` altında, son koşunun çıktılarıyla birlikte.

| Defter | İçerik | Gerekenler |
|---|---|---|
| `sonuc_uretim_npv_harita_2026-11-07.ipynb` | Üretim ve NPV özeti, ilk 20 çatı, uydu haritası (hesap yapmaz, gösterir) | `model_verisi/ekonomi/cati_npv.csv` ve `model_verisi/master_veriseti.csv` dosyalarını Colab'da `/content`'e yükle |
| `sam_birlesik_colab.ipynb` | 1.085 çatının SAM koşusu | GPU ve `proje/scripts/sam_birlesik_paketi.py` ile üretilen paket |
| `ayak_izi_tespit_colab.ipynb` | SAM ile eksik ayak izi denemesi (benimsenmedi) | GPU |
| `tahmin_modeli.ipynb` | Üretim hesabının temel aldığı defter | Kaynağı `YONTEM.md`'de |

Açmak için:
1. [colab.research.google.com](https://colab.research.google.com) adresinde **Dosya > Not defteri aç > GitHub** sekmesine gir.
2. **Özel depoları dahil et** kutusunu işaretleyip GitHub hesabınla izin ver.
3. `Tarikd-a11b/CatiGunes_Ortak` deposunu seç ve defteri aç.

Kaydedilmiş çıktılar açılınca görünür. Yeniden koşmak için defteri **Dosya > Drive'a kopya kaydet** ile kendi Drive'ına al. Colab oturumu kişiseldir: başkasının çalışan koşusu görülemez, `/content` altındaki dosyalar oturum kapanınca silinir.

## Repoda olmayanlar
- **SAM ağırlığı** (`sam_vit_b_01ec64.pth`, 358 MB, GitHub sınırını aşıyor). SAM'i yeniden koşacak olan [resmî adresten](https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth) indirip betiğin beklediği `modeller/` klasörüne koyar.
- **`proje/cache/`** ve **`proje/veri/arsiv_kapsam_disi/`** (yeniden indirilebilen ara dosyalar, kapsam dışı arşiv).
- **Ara rapor çalışma sürümleri** (Karşılaştırma, v2): güncel dosya `raporlar/Bitirme_Ara_Rapor_Teslim.docx`.
- **Anahtarlar:** TomTom gibi servis anahtarlarını herkes kendi bilgisayarında tutar, repoya koymaz.

Anahtar, şifre ve öğrenci numarası repoya konmaz.
