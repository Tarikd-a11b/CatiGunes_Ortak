# ÇatıGüneş web uygulaması

Veritabanı (PostgreSQL + PostGIS), REST API (FastAPI) ve web sayfası (Leaflet). Sayfa yukarıdan aşağı: proje tanıtımı, çatı haritası ve öncelik listesi, analiz panosu (bütçe senaryosu, yoğunlaşma, sanayi/kamu karşılaştırması, 10.000 senaryo testi), yapay zekâ asistanı ve yöntem.

Veri `model_verisi/` klasöründen (ara rapor verisi, 1.085 çatı) yüklenmiştir.

## Kurulum (bir kez)

Gerekenler: **Docker Desktop** ve **Python 3.11+** (Windows).

1. Docker Desktop'ı açın.
2. `uygulama\kur.bat` dosyasına çift tıklayın.
3. Gemini anahtarı sorulduğunda anahtarı yapıştırın. Anahtar repoda yoktur; ya https://aistudio.google.com/apikey adresinden kendi ücretsiz anahtarınızı alın ya da Dorukhan'dan özelden isteyin. Boş bırakırsanız asistan dışındaki her şey çalışır.

Betik şunları yapar: Docker'da `catigunes_db` container'ını kurar (port 5432), `veritabani/yedek/catigunes_web.sql` dökümünü yükler, asistanın kullandığı salt okunur `sorgu_okur` kullanıcısını oluşturur, `web\.venv` Python ortamını kurar ve `web\.env` dosyasını yazar. `.env` repoya gitmez.

Bilgisayarınızda 5432 portunu kullanan başka bir PostgreSQL varsa önce onu durdurun.

## Çalıştırma

1. Docker Desktop'ı açın.
2. `uygulama\web\baslat.bat` dosyasına çift tıklayın. Açılan pencere kapanmadığı sürece site çalışır.
3. Tarayıcıda http://localhost:8000 adresine gidin.

## Klasörler

| Yol | İçerik |
|---|---|
| `web/api/main.py` | REST API ve asistan (Gemini + salt okunur SQL) |
| `web/static/` | Web sayfası (`index.html`, `app.js`, `style.css`) |
| `veritabani/sema.sql` | Tablolar ve görünümler |
| `veritabani/yukle.py` | `model_verisi/` klasörünü veritabanına yükler (yeni veri gelince) |
| `veritabani/aciklama_uret.py` | Çatılar için yapay zekâ yorumu üretir (Gemini) |
| `veritabani/sorgu_kullanicisi.sql` | Asistanın salt okunur kullanıcısı |
| `veritabani/ornek_sorgular.sql` | pgAdmin için örnek sorgular |
| `veritabani/yedek/catigunes_web.sql` | Kurulumda yüklenen veritabanı dökümü |

API uç noktaları ve alanlar kök dizindeki `API.md` dosyasındadır.

## Yapay zekâ yorumları

Şimdilik yalnız 10 deneme çatısında var (sayfada Asistan'a "Yapay zekâ yorumu olan çatılar hangileri?" diye sorarak görebilirsiniz). Hepsini üretmek için:

```
cd uygulama\veritabani
..\web\.venv\Scripts\python aciklama_uret.py --hepsi
```

Gemini ücretsiz kotasıyla 1.021 çatı yaklaşık 1–1,5 saat sürer. Metindeki her sayı veritabanındaki değerle karşılaştırılır; uyuşmayan yorum sayfada gösterilmez.

## Yeni veri yükleme

`model_verisi/` güncellenirse:

```
cd uygulama\veritabani
..\web\.venv\Scripts\python yukle.py ..\..\model_verisi 2026-12_final "aciklama" > yukleme.sql
docker exec -i catigunes_db psql -U postgres -d catigunes_web -v ON_ERROR_STOP=1 < yukleme.sql
```

Eski tarama silinmez; sayfa en yeni taramayı gösterir.
