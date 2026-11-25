"""Her catinin sonuclarini Gemini ile sade Turkce bir aciklamaya cevirir ve cati_aciklama tablosuna yazar.

LLM yeni hesap yapmaz; yalnizca v_cati'deki kaydi okunur metne cevirir. Metindeki her sayi kayittaki
bir degerle karsilastirilir; uyusmayan sayi varsa sayilar_tutarli = false olur ve site metni gostermez.

Kullanim (web klasorundeki sanal ortamla):
    ..\\web\\.venv\\Scripts\\python aciklama_uret.py --deneme          # secili 10 cati, sonucu ekrana ve dosyaya yazar
    ..\\web\\.venv\\Scripts\\python aciklama_uret.py --cati 47 988     # belirli catilar
    ..\\web\\.venv\\Scripts\\python aciklama_uret.py --hepsi           # potansiyeli olan tum catilar

Ayarlar ..\\web\\.env dosyasindan okunur: DATABASE_URL, GEMINI_API_KEY.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import psycopg

KOK = Path(__file__).resolve().parent
MODEL = "gemini-3.8-flash"
DENEME_CATILARI = [47, 1493, 1415, 1432, 1230, 33, 816, 647, 988, 1334]

SISTEM = """Sen ÇatıGüneş karar destek sisteminin açıklama katmanısın. Görevin, İzmir Atatürk OSB ve
Çiğli kamu binalarındaki bir çatının çatı GES (güneş enerjisi santrali) analiz sonuçlarını, teknik
bilgisi olmayan bir karar vericinin anlayacağı sade bir Türkçeyle açıklamaktır.

KURALLAR
1. Yalnızca sana verilen kayıttaki bilgileri kullan. Yeni hesap yapma, tahmin yürütme, kayıtta
   olmayan bir bilgi ekleme.
2. Metinde kullandığın her sayı kayıttaki bir değerin yuvarlanmış hali olmalı. Kayıtta olmayan bir
   sayıyı (fark, oran, toplam gibi) kendin hesaplayıp yazma.
3. Neden-sonuç ilişkisi kurma ve yorum katma. Değerleri yalnızca say: "bu yüksek getiriyi
   sağlıyor", "bu başarıda", "avantaj sağlıyor" gibi ifadeler kullanma.
4. Sayıları sade ve yuvarlanmış yaz:
   - Para: 1 milyon TL ve üstü "60,1 milyon TL" (tek ondalık), 10 bin ile 1 milyon arası
     "852 bin TL", 10 bin TL altı tam sayı ("8.540 TL").
   - Güç: 1.000 kWp ve üstü "2,52 MW", 10 kWp ve üstü tam sayı ("394 kWp"), 10 kWp altı tek
     ondalık ("3,1 kWp").
   - Üretim: 1 milyon kWh ve üstü "3,72 milyon kWh", 10 bin ile 1 milyon arası "582 bin kWh",
     10 bin kWh altı tam sayı ("4.509 kWh").
   - Alan: "24.085 m²". Yüzde: "%98". Fiyat: "334,7 kuruş/kWh".
5. Karar verme ve tavsiye dili kullanma ("yatırım yapılmalı" deme). Sıralamayı sistem belirler;
   sen yalnızca hangi değerlerle bu sırada olduğunu söylersin.
6. Sade, günlük bir Türkçe kullan. Resmî ve bürokratik ekler kullanma: "yer almaktadır" yerine
   "yer alıyor", "öngörülmektedir" yerine "bekleniyor" yaz. Her başlık en fazla 2 kısa cümle.
   Abartılı sıfatlar kullanma.
7. Teknik terimleri ilk geçtiği yerde açıkla: NPV = net bugünkü değer.

BAŞLIKLAR
- ozet: Çatının türü, bulunduğu yer, büyüklüğü, kurulabilir gücü ve yıllık üretimi.
- sira_nedeni: Kendi grubundaki sırası ve bu sırayı belirleyen değerler: yatırım, net bugünkü
  değer, geri ödeme süresi, elektrik fiyatı.
- belirsizlik: 10.000 senaryoluk Monte Carlo testinin sonucu, şu sırayla ve iki cümlede:
  1. cümle: olası NPV aralığı. Bunu "senaryoların %80'inde NPV X ile Y arasında" diye yaz. Alt
     uç eksiyse cümlenin sonuna "kötü senaryolarda küçük bir zarar ihtimali de var" ekle.
  2. cümle: kârlı çıkan senaryo oranı ve üst sırada kalma oranı. Kârlı senaryo oranını
     "senaryoların %N'inde kârlı" diye, aralıktaki %80 ile karışmayacak biçimde ayrı söyle.
     Üst sırada kalma oranı %5'in altındaysa yüzde verme, "senaryoların neredeyse hiçbirinde
     ilk 50'ye (ya da ilk 20'ye / ilk 100'e) girmiyor" de.
  Hesap varsayımlarından (üretimin binada kullanılması vb.) söz etme; bu not sitede ayrıca
  gösteriliyor.
- veri_guvenilirligi: Çatı sınırının nereden geldiği (sam: uydu görüntüsünden otomatik çıkarım;
  insan: elle çizim; ayak_izi: kayıtlı bina sınırı), şüpheli işareti varsa otomatik çıkarımın
  güvenilir bulunmadığı için kullanılmadığı, mevcut panel düşüldüyse bu bilgi.

BİLGİ
- Temel hesapta bütün çatıların NPV'si pozitiftir; düşük sıradaki çatılar da kazandırır, yalnızca
  daha az kazandırır. Zarar ihtimali yalnızca olası aralığın alt ucu eksi olan çatılarda vardır.
- Sanayi çatıları sanayi grubunda, okul/hastane/üniversite kamu grubunda sıralanır; sanayi dışı
  binalar (OSB içindeki okul, klinik vb.) yalnızca genel sırada yer alır."""

SEMA = {
    "type": "OBJECT",
    "properties": {k: {"type": "STRING"} for k in ("ozet", "sira_nedeni", "belirsizlik", "veri_guvenilirligi")},
    "required": ["ozet", "sira_nedeni", "belirsizlik", "veri_guvenilirligi"],
    "propertyOrdering": ["ozet", "sira_nedeni", "belirsizlik", "veri_guvenilirligi"],
}

GRUP_UST = {"sanayi": 50, "kamu": 20}
TUR_AD = {"sanayi": "sanayi çatısı", "sanayi_disi": "OSB içinde sanayi dışı bina", "okul": "okul",
          "hastane": "hastane", "universite": "üniversite binası"}
BOLGE_AD = {"ataturk_osb": "Atatürk OSB", "cigli_kamu": "Çiğli"}
PANEL_AD = {"panel_yok": "çatıda mevcut panel yok", "kismi_panel_dusuldu": "çatının bir kısmında mevcut panel var, o kısım düşüldü"}


def ayar(ad):
    for satir in (KOK.parent / "web" / ".env").read_text(encoding="utf-8").splitlines():
        if satir.startswith(ad + "="):
            return satir.split("=", 1)[1].strip()
    sys.exit(f".env dosyasinda {ad} yok")


def kayitlari_oku(db, idler):
    sql = """
        SELECT v.*, (SELECT count(*) FROM v_cati x WHERE x.grup = v.grup AND x.sira_grup IS NOT NULL) AS grup_sayisi,
               (SELECT count(*) FROM v_cati x WHERE x.sira_npv IS NOT NULL) AS genel_sayisi
        FROM v_cati v
        WHERE v.sira_npv IS NOT NULL {filtre}
        ORDER BY v.sira_npv"""
    with psycopg.connect(db) as c, c.cursor(row_factory=psycopg.rows.dict_row) as cur:
        if idler:
            cur.execute(sql.format(filtre="AND v.cati_id = ANY(%s)"), (idler,))
        else:
            cur.execute(sql.format(filtre=""))
        return cur.fetchall()


def llm_girdisi(k):
    """LLM'e giden kayit: yalnizca aciklamada kullanilacak, anlami acik alanlar."""
    g = {
        "cati_id": k["cati_id"],
        "tur": TUR_AD[k["tur"]],
        "bolge": BOLGE_AD[k["bolge_kod"]],
        "kurum_ad": k["kurum_ad"],
        "cati_alani_m2": round(float(k["cati_alan_m2"])),
        "panel_konabilir_alan_m2": round(float(k["uygun_alan_m2"])),
        "mevcut_panel": PANEL_AD[k["panel_durumu"]],
        "kurulabilir_guc_kwp": float(k["kwp"]),
        "yillik_uretim_kwh": k["kwh_yil"],
        "yillik_uretim_alt_kwh": k["kwh_alt"],
        "yillik_uretim_ust_kwh": k["kwh_ust"],
        "elektrik_fiyati_kurus_kwh": float(k["tarife_kr_kwh"]),
        "yatirim_tl": k["yatirim_tl"],
        "npv_tl": k["npv_tl"],
        "geri_odeme_yil": k["geri_odeme_yil"],
        "npv_olasi_aralik_alt_tl": k["npv_p10"],
        "npv_olasi_aralik_ust_tl": k["npv_p90"],
        "karli_senaryo_yuzde": round(float(k["p_npv_poz"]) * 100),
        "genel_sira": k["sira_npv"],
        "genel_cati_sayisi": k["genel_sayisi"],
        "geometri_kaynagi": k["geometri_kaynagi"],
        "supheli": k["supheli"],
    }
    if k["grup"] in GRUP_UST:
        g["grup"] = k["grup"]
        g["grup_sirasi"] = k["sira_grup"]
        g["grup_cati_sayisi"] = k["grup_sayisi"]
        g[f"grup_ilk_{GRUP_UST[k['grup']]}_kalma_yuzde"] = round(float(k["grup_ilk_orani"]) * 100)
    else:
        g["grup"] = "sanayi dışı (grup sıralaması yok)"
        g["genel_ilk_100_kalma_yuzde"] = round(float(k["ilk100_orani"]) * 100)
    return g


def gemini(anahtar, girdi):
    istek = {
        "systemInstruction": {"parts": [{"text": SISTEM}]},
        "contents": [{"role": "user", "parts": [{"text": "Çatı kaydı:\n" + json.dumps(girdi, ensure_ascii=False, indent=1)}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SEMA, "temperature": 0.2},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    for deneme in range(5):
        req = urllib.request.Request(url, data=json.dumps(istek).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": anahtar})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                cevap = json.load(r)
            return json.loads(cevap["candidates"][0]["content"]["parts"][0]["text"])
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and deneme < 4:  # kota ya da gecici hata: bekleyip tekrar dene
                time.sleep(15 * (deneme + 1))
                continue
            raise RuntimeError(f"Gemini {e.code}: {e.read().decode()[:300]}")


# ---- sayi kontrolu --------------------------------------------------
# eksi isareti yalniz bosluktan sonra gelirse sayilir; "12,3–69,0" gibi araliktaki tire eksi sayilmaz
SAYI = re.compile(r"(?<![\w])([-−]?)(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?")


def metindeki_sayilar(metin):
    """'60,1' -> 60.1, '24.085' -> 24085, '%98' -> 98, '-179.136' -> -179136."""
    out = []
    for isaret, tam, ondalik in SAYI.findall(metin):
        v = float(tam.replace(".", "") + ("." + ondalik if ondalik else ""))
        out.append((-v if isaret else v, len(ondalik)))
    return out


def izinli_degerler(girdi):
    """Kayittaki her sayisal degerin metinde yazilabilecegi bicimler (birim donusumleri dahil)."""
    ham = [v for v in girdi.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    for metin_alani in (girdi.get("kurum_ad") or "",):
        ham += [v for v, _ in metindeki_sayilar(metin_alani)]
    izin = set()
    for v in ham:
        for bolen in (1, 1e3, 1e6, 1e9):
            izin.add(v / bolen)
    # kurala dahil sabitler: senaryo sayisi, %80 aralik, ust sira esikleri
    izin.update([10000, 10, 80, 100, 50, 20, 1])
    return izin


def tutarli_mi(metin, izin):
    sorunlu = []
    for v, basamak in metindeki_sayilar(metin):
        tol = 0.5 * 10 ** (-basamak) + 1e-9  # yazilan basamak kadar yuvarlama payi
        if not any(abs(v - i) <= tol or (i and abs(v - i) / abs(i) < 0.006) for i in izin):
            sorunlu.append(v)
    return sorunlu


def yaz(db, sonuclar):
    with psycopg.connect(db) as c:
        for s in sonuclar:
            c.execute("""
                INSERT INTO cati_aciklama (cati_id, tarama_id, ozet, sira_nedeni, belirsizlik, veri_guvenilirligi, sayilar_tutarli, model)
                VALUES (%(cati_id)s, %(tarama_id)s, %(ozet)s, %(sira_nedeni)s, %(belirsizlik)s, %(veri_guvenilirligi)s, %(tutarli)s, %(model)s)
                ON CONFLICT (cati_id, tarama_id) DO UPDATE SET
                  ozet = EXCLUDED.ozet, sira_nedeni = EXCLUDED.sira_nedeni, belirsizlik = EXCLUDED.belirsizlik,
                  veri_guvenilirligi = EXCLUDED.veri_guvenilirligi, sayilar_tutarli = EXCLUDED.sayilar_tutarli,
                  model = EXCLUDED.model, olusturma = now()""", s)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--deneme", action="store_true")
    g.add_argument("--cati", type=int, nargs="+")
    g.add_argument("--hepsi", action="store_true")
    ap.add_argument("--bekle", type=float, default=4.0, help="istekler arasi saniye (kota icin)")
    a = ap.parse_args()

    db, anahtar = ayar("DATABASE_URL"), ayar("GEMINI_API_KEY")
    idler = DENEME_CATILARI if a.deneme else a.cati
    kayitlar = kayitlari_oku(db, idler)
    print(f"{len(kayitlar)} cati, model {MODEL}", file=sys.stderr)

    sonuclar, rapor = [], []
    for i, k in enumerate(kayitlar, 1):
        girdi = llm_girdisi(k)
        cevap = gemini(anahtar, girdi)
        izin = izinli_degerler(girdi)
        sorunlu = {alan: tutarli_mi(cevap[alan], izin) for alan in SEMA["required"]}
        sorunlu = {k_: v for k_, v in sorunlu.items() if v}
        s = {**cevap, "cati_id": k["cati_id"], "tarama_id": k["tarama_id"], "tutarli": not sorunlu, "model": MODEL}
        sonuclar.append(s)
        rapor.append({"cati_id": k["cati_id"], "girdi": girdi, "cevap": cevap, "uyusmayan_sayilar": sorunlu})
        print(f"[{i}/{len(kayitlar)}] cati {k['cati_id']}: {'tutarli' if not sorunlu else 'UYUSMAYAN ' + str(sorunlu)}", file=sys.stderr)
        if i < len(kayitlar):
            time.sleep(a.bekle)

    yaz(db, sonuclar)
    (KOK / "aciklama_rapor.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"yazildi: {len(sonuclar)} aciklama, {sum(not s['tutarli'] for s in sonuclar)} uyusmayan", file=sys.stderr)


if __name__ == "__main__":
    main()
