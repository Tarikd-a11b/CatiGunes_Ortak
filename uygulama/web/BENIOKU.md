# Çatı GES haritası (web)

`catigunes_web` veritabanını okuyan REST API (FastAPI) ve harita sayfası (Leaflet).

## Çalıştırma

1. Docker Desktop'ı aç.
2. `baslat.bat` dosyasına çift tıkla.
3. Tarayıcıda http://localhost:8000 adresini aç.

`baslat.bat` veritabanı container'ını (`catigunes_db`) da başlatır. Kapatmak için açılan pencerede Ctrl+C.

## İlk kurulum (başka bilgisayarda)

```
py -m venv .venv
.venv\Scripts\python -m pip install fastapi "uvicorn[standard]" "psycopg[binary]"
```

Aynı klasöre `.env` dosyası koy:

```
DATABASE_URL=postgresql://postgres:<şifre>@localhost:5432/catigunes_web
```

`.env` şifre içerir, repoya konmaz.

## Klasörler

| Yol | İçerik |
|---|---|
| `api/main.py` | REST API |
| `static/` | Harita sayfası (`index.html`, `app.js`, `style.css`) |

## API

| Uç nokta | Döndürdüğü |
|---|---|
| `GET /api/catilar?grup=sanayi\|kamu\|diger` | Haritadaki çatılar (GeoJSON) |
| `GET /api/catilar/{cati_id}` | Tek çatının tüm bilgileri, varsa LLM açıklaması |
| `GET /api/siralama?olcut=npv\|uretim\|npv_kwp&grup=sanayi\|kamu&limit=10` | Öncelik listesi |
| `GET /api/ozet` | Bölge ve tür toplamları |
| `GET /api/analiz` | Analiz panosu için potansiyeli olan 1.021 çatının özet satırları (geometrisiz) |
| `GET /api/bolgeler` | Bölge sınırları (GeoJSON) |
| `POST /api/sohbet` | Asistan: soruyu Gemini'ye iletir; Gemini gerekirse salt okunur kullanıcıyla SQL çalıştırır |

API belgesi sunucu açıkken http://localhost:8000/docs adresinde.

## Asistan (chatbot)

Sayfadaki **Asistan** bölümü. Kullanıcı sorusunu yazar ya da hazır sorulardan birini seçer. Sunucu soruyu Gemini'ye (`GEMINI_API_KEY`, model `gemini-3.8-flash`) iletir. Gemini veriye ulaşmak için `sql_calistir` aracını çağırır; bu SQL `sorgu_okur` adlı salt okunur kullanıcıyla çalışır (hiçbir tablo değiştirilemez, 5 sn, en fazla 500 satır). Cevaptaki çatılar bölümün kendi haritasında ve ana haritada vurgulanır.

`.env` içinde `GEMINI_API_KEY` ve `SORGU_DATABASE_URL` satırları olmalıdır. Sunucu yalnız bu bilgisayardan erişilecek şekilde çalışır; site internete açılacaksa anahtar ve kota kontrolü yeniden düşünülmelidir.
