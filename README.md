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

Anahtar, şifre, öğrenci numarası ve büyük veri dosyaları repoya konmaz.
