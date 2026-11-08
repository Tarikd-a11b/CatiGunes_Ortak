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
| `raporlar/` | Ara rapor ve teklif belgeleri |

Repo yaklaşık 535 MB; ilk `git clone` biraz sürer.

## Repoda olmayanlar
- **SAM ağırlığı** (`sam_vit_b_01ec64.pth`, 358 MB, GitHub sınırını aşıyor). SAM'i yeniden koşacak olan [resmî adresten](https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth) indirip betiğin beklediği `modeller/` klasörüne koyar.
- **`proje/cache/`** ve **`proje/veri/arsiv_kapsam_disi/`** (yeniden indirilebilen ara dosyalar, kapsam dışı arşiv).
- **Anahtarlar:** TomTom gibi servis anahtarlarını herkes kendi bilgisayarında tutar, repoya koymaz.

Anahtar, şifre ve öğrenci numarası repoya konmaz.
