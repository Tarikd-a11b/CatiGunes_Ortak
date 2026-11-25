"""CatiGunes REST API.

Veritabanindaki v_cati, v_ozet ve bolge'yi okur, web haritasina JSON/GeoJSON verir.
Ayni sunucu static/ klasorundeki harita sayfasini da / adresinden sunar.

Calistirma (web klasorunde):
    .venv\\Scripts\\python -m uvicorn api.main:app --port 8000
Baglanti adresi .env dosyasindaki DATABASE_URL'den okunur.
"""
import json
import os
import time
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

KOK = Path(__file__).resolve().parent.parent


def baglanti_adresi(ad="DATABASE_URL", zorunlu=True):
    if os.environ.get(ad):
        return os.environ[ad]
    env = KOK / ".env"
    for satir in env.read_text(encoding="utf-8").splitlines():
        if satir.startswith(ad + "="):
            return satir.split("=", 1)[1].strip()
    if zorunlu:
        raise RuntimeError(f".env dosyasinda {ad} yok")
    return None


DB = baglanti_adresi()
SORGU_DB = baglanti_adresi("SORGU_DATABASE_URL", zorunlu=False)  # salt okunur kullanici
app = FastAPI(title="CatiGunes API", version="1.0")


def json_sorgu(sql, params=()):
    """Sorgu tek bir JSON degeri dondurur; oldugu gibi istemciye gonderilir. Satir yoksa None."""
    with psycopg.connect(DB) as conn:
        satir = conn.execute(sql, params).fetchone()
    return satir[0] if satir else None


def json_cevap(metin):
    return Response(content=metin, media_type="application/json")


GRUPLAR = {"sanayi", "kamu", "diger"}


@app.get("/api/bolgeler")
def bolgeler():
    """Bolge sinirlari (GeoJSON)."""
    return json_cevap(json_sorgu("""
        SELECT json_build_object('type', 'FeatureCollection', 'features', coalesce(json_agg(json_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(ST_SimplifyPreserveTopology(sinir, 0.00005), 6)::json,
            'properties', json_build_object('bolge_kod', bolge_kod, 'ad', ad)
        )), '[]'))::text
        FROM bolge"""))


@app.get("/api/catilar", summary="Haritadaki catilar (GeoJSON)")
def catilar(grup: str | None = Query(None, description="sanayi, kamu veya diger")):
    """Haritada cizilecek catilar (GeoJSON) ve renklendirme icin ozet alanlar."""
    if grup and grup not in GRUPLAR:
        raise HTTPException(400, "grup sanayi, kamu veya diger olmali")
    return json_cevap(json_sorgu("""
        SELECT json_build_object('type', 'FeatureCollection', 'features', coalesce(json_agg(json_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(geom, 6)::json,
            'properties', json_build_object(
                'cati_id', cati_id, 'tur', tur, 'grup', grup, 'kurum_ad', kurum_ad,
                'panel_durumu', panel_durumu, 'kwp', kwp, 'npv_tl', npv_tl,
                'sira_npv', sira_npv, 'sira_grup', sira_grup)
        ) ORDER BY cati_id), '[]'))::text
        FROM v_cati
        WHERE %(grup)s::text IS NULL OR grup = %(grup)s""", {"grup": grup}))


@app.get("/api/catilar/{cati_id}")
def cati(cati_id: int):
    """Tek catinin tum bilgileri (geometri haric) ve varsa LLM aciklamasi."""
    metin = json_sorgu("""
        SELECT (to_jsonb(v) - 'geom' - 'geom_uygun' - 'konum'
                || jsonb_build_object(
                     'lon', ST_X(v.konum), 'lat', ST_Y(v.konum),
                     'grup_cati_sayisi', (SELECT count(*) FROM v_cati x
                                          WHERE x.grup = v.grup AND x.sira_grup IS NOT NULL),
                     'aciklama', (SELECT jsonb_build_object('ozet', a.ozet, 'sira_nedeni', a.sira_nedeni,
                                         'belirsizlik', a.belirsizlik, 'veri_guvenilirligi', a.veri_guvenilirligi)
                                  FROM cati_aciklama a
                                  WHERE a.cati_id = v.cati_id AND a.tarama_id = v.tarama_id
                                    AND a.sayilar_tutarli)))::text
        FROM v_cati v WHERE v.cati_id = %s""", (cati_id,))
    if metin is None:
        raise HTTPException(404, "cati bulunamadi")
    return json_cevap(metin)


SIRA_OLCUT = {"npv": "sira_npv", "uretim": "sira_uretim", "npv_kwp": "sira_npv_kwp"}


@app.get("/api/siralama")
def siralama(olcut: str = "npv", grup: str | None = None, limit: int = Query(10, ge=1, le=200)):
    """Oncelik listesi. grup verilirse grup ici sira (sira_grup) kullanilir."""
    if olcut not in SIRA_OLCUT:
        raise HTTPException(400, "olcut npv, uretim veya npv_kwp olmali")
    if grup and grup not in {"sanayi", "kamu"}:
        raise HTTPException(400, "grup sanayi veya kamu olmali")
    sira = "sira_grup" if grup and olcut == "npv" else SIRA_OLCUT[olcut]
    return json_cevap(json_sorgu(f"""
        SELECT coalesce(json_agg(r ORDER BY r.sira), '[]')::text FROM (
            SELECT {sira} AS sira, cati_id, tur, grup, kurum_ad, kwp, kwh_yil, npv_tl, geri_odeme_yil,
                   npv_p10, npv_p90, p_npv_poz, ilk100_orani, grup_ilk_orani,
                   ST_X(konum) AS lon, ST_Y(konum) AS lat
            FROM v_cati
            WHERE {sira} IS NOT NULL AND (%(grup)s::text IS NULL OR grup = %(grup)s)
            ORDER BY {sira} LIMIT %(limit)s) r""", {"grup": grup, "limit": limit}))


@app.get("/api/analiz")
def analiz():
    """Analiz panosu icin potansiyeli olan tum catilarin ozet satirlari (geometrisiz)."""
    return json_cevap(json_sorgu("""
        SELECT coalesce(json_agg(r ORDER BY r.sira_npv), '[]')::text FROM (
            SELECT cati_id, tur, grup, kurum_ad, kwp, kwh_yil, yatirim_tl, npv_tl, geri_odeme_yil,
                   npv_p10, npv_p90, p_npv_poz, ilk100_orani, grup_ilk_orani, sira_npv, sira_grup
            FROM v_cati
            WHERE sira_npv IS NOT NULL) r"""))


@app.get("/api/ozet")
def ozet():
    """Bolge x tur toplamlari ve genel toplam."""
    return json_cevap(json_sorgu("""
        SELECT json_build_object(
            'satirlar', (SELECT json_agg(o ORDER BY o.bolge_kod, o.tur) FROM v_ozet o),
            'toplam', (SELECT json_build_object(
                'cati', count(*),
                'potansiyelli_cati', count(*) FILTER (WHERE panel_durumu <> 'tam_dolu'),
                'mevcut_ges_cati', count(*) FILTER (WHERE panel_durumu <> 'panel_yok'),
                'mwp', round(sum(kwp) / 1000, 1),
                'gwh_yil', round(sum(kwh_yil) / 1e6, 1),
                'yatirim_tl', sum(yatirim_tl),
                'npv_tl', sum(npv_tl),
                'tarama', max(tarama))
              FROM v_cati))::text"""))


SORGU_SATIR_SINIRI = 500


def hucre(v):
    """Sorgu sonucundaki degeri JSON'a uygun hale getirir."""
    if v is None or isinstance(v, (bool, int, float, str)):
        if isinstance(v, str) and len(v) > 200:   # geometri gibi uzun metinler
            return v[:200] + "…"
        return v
    if isinstance(v, Decimal):
        return float(v)
    return str(v)[:200]


def sql_calistir(sql):
    """SQL'i salt okunur kullaniciyla calistirir (degisiklik yapamaz, 5 sn, en fazla 500 satir).

    Basarida {kolonlar, satirlar, kesildi, cati_idler}, hatada {hata} dondurur.
    """
    sql = sql.strip().rstrip(";").strip()
    try:
        with psycopg.connect(SORGU_DB) as conn:
            conn.read_only = True
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '5s'")
                cur.execute(sql)
                if cur.description is None:
                    return {"hata": "Sorgu sonuc donduren bir SELECT olmali"}
                kolonlar = [d.name for d in cur.description]
                satirlar = cur.fetchmany(SORGU_SATIR_SINIRI + 1)
    except psycopg.Error as e:
        return {"hata": (e.diag.message_primary if e.diag and e.diag.message_primary else str(e)).strip()}
    kesildi = len(satirlar) > SORGU_SATIR_SINIRI
    satirlar = [[hucre(v) for v in s] for s in satirlar[:SORGU_SATIR_SINIRI]]
    cati_idler = []
    if "cati_id" in kolonlar:
        i = kolonlar.index("cati_id")
        cati_idler = list(dict.fromkeys(s[i] for s in satirlar if isinstance(s[i], int)))  # sirayi koru
    return {"kolonlar": kolonlar, "satirlar": satirlar, "kesildi": kesildi, "cati_idler": cati_idler}


# ---- asistan (chatbot) -----------------------------------------------
GEMINI_KEY = baglanti_adresi("GEMINI_API_KEY", zorunlu=False)
GEMINI_MODEL = "gemini-3.8-flash"
MODELE_SATIR = 60  # modele gonderilen en fazla satir (token tasarrufu)

ASISTAN_SISTEM = """Sen ÇatıGüneş karar destek sisteminin asistanısın. Kullanıcı, İzmir Atatürk OSB ve Çiğli kamu
binalarındaki çatıların güneş enerjisi (GES) potansiyeli ve yatırım önceliği hakkında soru soruyor. Cevapları
yalnızca PostgreSQL veritabanındaki verilere dayandırırsın; veriye ulaşmak için `sql_calistir` aracını kullanırsın.

VERİTABANI (salt okunur; yalnızca SELECT)
v_cati: her çatının güncel hali, bir satır = bir çatı.
  cati_id (int), tur ('sanayi','sanayi_disi','okul','hastane','universite'), grup ('sanayi','kamu','diger'),
  bolge_kod ('ataturk_osb','cigli_kamu'), kurum_ad (yalnız kamu binalarında; sanayi çatılarında NULL, firma adı yok),
  panel_durumu ('panel_yok','kismi_panel_dusuldu','tam_dolu'), geometri_kaynagi ('sam','insan','ayak_izi'),
  supheli (bool), cati_alan_m2, uygun_alan_m2 (panel konabilir alan), kwp (kurulabilir güç),
  kwh_yil, kwh_alt, kwh_ust (yıllık üretim ve aralığı), tarife_kr_kwh (elektrik fiyatı, kuruş),
  yatirim_tl, npv_tl (net bugünkü değer), npv_tl_kwp, geri_odeme_yil,
  npv_p10, npv_p50, npv_p90 (10.000 senaryoluk Monte Carlo; p10–p90 senaryoların %80'inin aralığı),
  p_npv_poz (kârlı senaryo payı, 0–1), ilk100_orani (genel ilk 100'de kalma payı),
  grup_ilk_orani (sanayi: ilk 50, kamu: ilk 20'de kalma payı),
  sira_npv (genel NPV sırası), sira_uretim, sira_npv_kwp, sira_grup (sanayi/kamu içi sıra).
  Tamamen panelli (tam_dolu) çatılarda kwp=0, ekonomi alanları ve sıralar NULL.
v_ozet: bolge_kod, tur, cati, potansiyelli_cati, mevcut_ges_cati, cati_alan_m2, uygun_alan_m2, mwp, gwh_yil,
  yatirim_milyon_tl, npv_milyon_tl.
bolge: bolge_kod, ad, ozgul_uretim_kwh_kwp, sinir (PostGIS geometri).
cati_aciklama: cati_id, tarama_id, ozet, sira_nedeni, belirsizlik, veri_guvenilirligi, sayilar_tutarli
  (yapay zekâ yorumları; şimdilik yalnızca birkaç çatıda var).
PostGIS kullanılabilir (v_cati.geom, bolge.sinir; mesafe için ::geography).

KURALLAR
1. Sayısal bir cevap vermeden önce mutlaka sql_calistir ile veriyi sorgula. Sayı uydurma, tahmin yürütme.
2. Çatıları listeleyen sorgularda SELECT'e her zaman cati_id koy; bu çatılar haritada gösterilir.
   Liste sorgularına makul bir LIMIT koy (en fazla 50). Toplam/ortalama sorularında cati_id gerekmez.
3. Bütçe sorularında çatıları sira_npv sırasıyla ekleyip yatırımın birikimli toplamı bütçeyi aşmayana kadar
   al (sum(yatirim_tl) OVER (ORDER BY sira_npv)).
4. Cevabı Türkçe, kısa ve sade yaz (en fazla 4–5 cümle ya da kısa bir madde listesi). Sayıları Türkçe biçimde
   yuvarla: 60,1 milyon TL; 852 bin TL; 2,52 MW; 394 kWp; 3,72 milyon kWh; %98. Markdown başlığı kullanma;
   gerekirse kısa madde işareti (-) kullanabilirsin.
5. Çatılardan söz ederken "çatı 47" gibi numarasını yaz; kamu binalarında kurum adını da ver.
6. Veritabanında olmayan bir bilgi sorulursa (firma adları, kurulum maliyeti varsayımları, hava durumu vb.)
   bunun veritabanında olmadığını söyle. Sorulmadıkça eksik bilgilerden (örneğin firma adı olmadığından) söz etme.
   Proje dışı sorulara kibarca proje kapsamında yardımcı olabileceğini söyle.
7. Yatırım tavsiyesi verme; sıralamayı ve sayıları aktar. Tüm çatılarda temel NPV pozitiftir. NPV'nin üretimin
   tamamının binada kullanıldığı varsayımına dayalı bir üst değer olduğunu yalnızca kullanıcı NPV'nin
   güvenilirliğini ya da varsayımları sorarsa söyle; her cevaba ekleme.
8. Cevaptaki her sayı bir sorgu sonucundan gelmeli; sorgu sonucunda olmayan bir oranı ya da ortalamayı kafadan
   hesaplama, gerekirse yeni bir sorgu çalıştır."""

ARACLAR = [{"functionDeclarations": [{
    "name": "sql_calistir",
    "description": "Veritabanında salt okunur bir SELECT sorgusu çalıştırır ve sonuç satırlarını döndürür.",
    "parameters": {"type": "OBJECT", "properties": {"sql": {"type": "STRING", "description": "Çalıştırılacak PostgreSQL SELECT sorgusu"}}, "required": ["sql"]},
}]}]


def gemini_istek(icerik):
    istek = {
        "systemInstruction": {"parts": [{"text": ASISTAN_SISTEM}]},
        "contents": icerik,
        "tools": ARACLAR,
        "generationConfig": {"temperature": 0.2},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    for deneme in range(3):
        req = urllib.request.Request(url, data=json.dumps(istek).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_KEY})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and deneme < 2:
                time.sleep(6 * (deneme + 1))
                continue
            if e.code == 429:
                raise HTTPException(429, "Yapay zekâ servisinin kullanım sınırına ulaşıldı, biraz sonra tekrar deneyin.")
            raise HTTPException(502, f"Yapay zekâ servisi hata verdi ({e.code}).")
        except urllib.error.URLError:
            raise HTTPException(502, "Yapay zekâ servisine ulaşılamadı. İnternet bağlantısını kontrol edin.")


class SohbetMesaji(BaseModel):
    rol: str   # "kullanici" ya da "asistan"
    metin: str


class SohbetIstegi(BaseModel):
    mesajlar: list[SohbetMesaji]


@app.post("/api/sohbet")
def sohbet(istek: SohbetIstegi):
    """Asistan: soruyu Gemini'ye iletir; Gemini gerekirse sql_calistir aracini kullanir.

    SQL, salt okunur kullaniciyla calisir. Donus: {cevap, cati_idler, sorgu_sayisi}.
    """
    if not GEMINI_KEY:
        raise HTTPException(503, "Yapay zekâ anahtarı tanımlı değil (.env: GEMINI_API_KEY)")
    if not SORGU_DB:
        raise HTTPException(503, "Sorgu kullanıcısı tanımlı değil (.env: SORGU_DATABASE_URL)")
    gecmis = istek.mesajlar[-10:]  # son 10 mesaj baglam olarak yeter
    if not gecmis or gecmis[-1].rol != "kullanici" or not gecmis[-1].metin.strip():
        raise HTTPException(400, "Soru boş")
    icerik = [{"role": "user" if m.rol == "kullanici" else "model", "parts": [{"text": m.metin[:2000]}]} for m in gecmis]

    cati_idler, sorgu_sayisi = [], 0
    for _ in range(6):  # en fazla 6 arac turu
        cevap = gemini_istek(icerik)
        aday = (cevap.get("candidates") or [{}])[0]
        parcalar = aday.get("content", {}).get("parts", [])
        cagrilar = [p["functionCall"] for p in parcalar if "functionCall" in p]
        if not cagrilar:
            metin = "".join(p.get("text", "") for p in parcalar if not p.get("thought")).strip()
            return {"cevap": metin or "Bu soruya cevap üretemedim, farklı bir şekilde sorar mısınız?",
                    "cati_idler": cati_idler, "sorgu_sayisi": sorgu_sayisi}
        icerik.append(aday["content"])  # modelin mesaji oldugu gibi geri gider (dusunce imzalari dahil)
        yanitlar = []
        for c in cagrilar:
            sonuc = sql_calistir(c.get("args", {}).get("sql", ""))
            sorgu_sayisi += 1
            if sonuc.get("cati_idler"):
                cati_idler = sonuc["cati_idler"]  # haritada son listelenen catilar gosterilir
            modele = sonuc if "hata" in sonuc else {
                "kolonlar": sonuc["kolonlar"], "satirlar": sonuc["satirlar"][:MODELE_SATIR],
                "toplam_satir": len(sonuc["satirlar"]), "kesildi": sonuc["kesildi"] or len(sonuc["satirlar"]) > MODELE_SATIR,
            }
            yanitlar.append({"functionResponse": {"name": c["name"], "response": modele}})
        icerik.append({"role": "user", "parts": yanitlar})
    return {"cevap": "Soruyu cevaplamak için çok fazla adım gerekti. Soruyu daha dar sorar mısınız?",
            "cati_idler": cati_idler, "sorgu_sayisi": sorgu_sayisi}


@app.middleware("http")
async def onbellek_yok(istek, devam):
    """Sayfa dosyalari tarayicida eski surumuyle kalmasin."""
    cevap = await devam(istek)
    if not istek.url.path.startswith("/api/"):
        cevap.headers["Cache-Control"] = "no-cache"
    return cevap


app.mount("/", StaticFiles(directory=KOK / "static", html=True), name="static")
