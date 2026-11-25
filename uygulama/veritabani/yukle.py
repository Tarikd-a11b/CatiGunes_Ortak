"""model_verisi klasorunu verilen tarama kodu altinda veritabanina yukleyen SQL'i uretir.

Kullanim:
    python yukle.py <model_verisi klasoru> <tarama_kodu> ["aciklama"] [--yenile] > yukleme.sql
    docker exec -i catigunes_db psql -U postgres -d catigunes_web -v ON_ERROR_STOP=1 < yukleme.sql

Ornek:
    python yukle.py ../../model_verisi 2026-11_ara_rapor "WV02 2025-10-12 + LG03 2026-01-14; ara rapor verisi" > yukleme.sql

Davranis:
- Yeni tarama kodu: kayitlar eklenir, onceki taramalara dokunulmaz.
- Ayni kod tekrar verilirse yukleme durur. --yenile verilirse o taramanin
  sonuclari (ve LLM aciklamalari) silinip yeniden yuklenir.
- cati (kimlik) satirlari silinmez; yeni catilar eklenir, tur ve kurum adi guncellenir.
- Bolge sinirlari ve 1 kWp uretim degerleri her yuklemede klasordeki hale getirilir.
Kaynak dosyalara dokunmaz. Okunan dosyalar:
    catilar.gpkg (sinirlar, cati_son, uygun_alan), master_veriseti.csv,
    ekonomi/cati_npv.csv, ekonomi/mc_cati.csv, uretim/yillik_ozet.csv
"""
import csv
import os
import re
import sqlite3
import struct
import sys

argv = [a for a in sys.argv[1:] if a != "--yenile"]
YENILE = "--yenile" in sys.argv
if len(argv) < 2:
    sys.exit(__doc__)
KLASOR, TARAMA = argv[0], argv[1]
ACIKLAMA = argv[2] if len(argv) > 2 else None
if not re.fullmatch(r"[A-Za-z0-9_.\-]+", TARAMA):
    sys.exit("tarama kodu yalniz harf, rakam, _ . - icerebilir")
out = open(sys.stdout.fileno(), "w", encoding="utf-8", newline="\n", closefd=False)


def oku(yol):
    with open(os.path.join(KLASOR, yol), encoding="utf-8-sig", newline="") as f:
        return {int(r["cati_id"]) if "cati_id" in r else i: r for i, r in enumerate(csv.DictReader(f))}


def wkb_hex(blob):
    """GeoPackage geometri blob'undan WKB (hex) cikarir."""
    if blob[:2] != b"GP":
        raise ValueError("GeoPackage geometrisi degil")
    zarf = (blob[3] >> 1) & 0b111
    return blob[8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[zarf]:].hex()


def q(v):
    """Python degerini SQL literaline cevirir. Bos metin NULL olur."""
    if v is None or v == "" or str(v).lower() == "nan":
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def sayi(v, tam=False):
    if v is None or v == "" or str(v).lower() == "nan":
        return "NULL"
    x = float(v)
    return str(int(round(x))) if tam else repr(x)


def bool_(v):
    return {"true": "true", "false": "false"}[str(v).strip().lower()]


def geom(hexstr):
    return f"ST_Multi(ST_GeomFromWKB(decode('{hexstr}', 'hex'), 4326))" if hexstr else "NULL"


# --- girdiler ---------------------------------------------------------
gp = sqlite3.connect(os.path.join(KLASOR, "catilar.gpkg"))
sinir = {e: wkb_hex(g) for e, g in gp.execute("SELECT etiket, geom FROM sinirlar")}
cati_son = {i: wkb_hex(g) for i, g in gp.execute("SELECT cati_id, geom FROM cati_son")}
uygun = {i: wkb_hex(g) for i, g in gp.execute("SELECT cati_id, geom FROM uygun_alan")}
son_bilgi = {i: (k, a, p, u) for i, k, a, p, u in gp.execute(
    "SELECT cati_id, geometri_kaynagi, cati_alan_m2, panel_durumu, uygun_alan_m2 FROM cati_son")}

master = oku("master_veriseti.csv")
npv = oku("ekonomi/cati_npv.csv")
mc = oku("ekonomi/mc_cati.csv")
yillik = {(r["bolge"], r["senaryo"]): r["E_y_kWh_per_kWp"] for r in oku("uretim/yillik_ozet.csv").values()}

idler = sorted(master)
for ad, d in [("cati_son", cati_son), ("cati_npv.csv", npv)]:
    if set(d) != set(idler):
        sys.exit(f"{ad} ile master_veriseti.csv cati_id kumeleri farkli")
eksik_mc = [i for i in idler if npv[i]["panel_durumu"] != "tam_dolu" and i not in mc]
if eksik_mc:
    sys.exit(f"mc_cati.csv'de olmayan potansiyelli cati: {eksik_mc[:10]}")

# --- SQL --------------------------------------------------------------
w = out.write
w("\\set ON_ERROR_STOP on\nBEGIN;\n\n")

w("-- bolgeler\n")
for kod, ad, etiket, pvgis in [("ataturk_osb", "Atatürk OSB", "ataturk_osb", "ataturk_osb"),
                               ("cigli_kamu", "Çiğli kamu binaları", "cigli", "cigli")]:
    w(f"INSERT INTO bolge VALUES ({q(kod)}, {q(ad)}, {yillik[(pvgis, 'egim10_guney')]}, {geom(sinir.get(etiket))})\n"
      "  ON CONFLICT (bolge_kod) DO UPDATE SET ad = EXCLUDED.ad,\n"
      "  ozgul_uretim_kwh_kwp = EXCLUDED.ozgul_uretim_kwh_kwp, sinir = EXCLUDED.sinir;\n")

w("\n-- tarama\n")
if YENILE:
    w(f"DELETE FROM cati_sonuc WHERE tarama_id = (SELECT tarama_id FROM tarama WHERE kod = {q(TARAMA)});\n"
      f"UPDATE tarama SET aciklama = coalesce({q(ACIKLAMA)}, aciklama), yuklenme = now() WHERE kod = {q(TARAMA)};\n"
      f"INSERT INTO tarama (kod, aciklama) VALUES ({q(TARAMA)}, {q(ACIKLAMA)}) ON CONFLICT (kod) DO NOTHING;\n")
else:
    w(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM tarama WHERE kod = {q(TARAMA)}) THEN\n"
      f"  RAISE EXCEPTION 'tarama {TARAMA} zaten yuklu; yeniden yuklemek icin --yenile kullanin'; END IF; END $$;\n"
      f"INSERT INTO tarama (kod, aciklama) VALUES ({q(TARAMA)}, {q(ACIKLAMA)});\n")

w("\n-- catilar (kimlik)\n")
for i in idler:
    m = master[i]
    w(f"INSERT INTO cati (cati_id, osm, bolge_kod, tur, kurum_ad) VALUES "
      f"({i}, {q(m['osm'])}, {q(m['bolge'])}, {q(m['tur'])}, {q(m['kurum_ad'])})\n"
      f"  ON CONFLICT (cati_id) DO UPDATE SET tur = EXCLUDED.tur, kurum_ad = EXCLUDED.kurum_ad;\n")

w("\n-- sonuclar\n")
kolonlar = ("cati_id, tarama_id, geom, geom_uygun, geometri_kaynagi, supheli, panel_durumu, "
            "cati_alan_m2, uygun_alan_m2, kwp, kwh_yil, kwh_alt, kwh_ust, tarife_kr_kwh, "
            "yatirim_tl, npv_tl, geri_odeme_yil, npv_p10, npv_p50, npv_p90, p_npv_poz, "
            "ilk100_orani, grup_ilk_orani")
for i in idler:
    m, n, r = master[i], npv[i], mc.get(i, {})
    kaynak, cati_alan, panel, uygun_alan = son_bilgi[i]
    grup_ilk = r.get("ilk50_sanayi") or r.get("ilk20_kamu")
    degerler = [
        str(i), f"(SELECT tarama_id FROM tarama WHERE kod = {q(TARAMA)})",
        geom(cati_son[i]), geom(uygun.get(i)),
        q(kaynak), bool_(m["supheli"]), q(panel),
        sayi(cati_alan), sayi(uygun_alan),
        sayi(n["kwp_merkez"]), sayi(n["kwh_merkez"], True), sayi(n["kwh_alt"], True), sayi(n["kwh_ust"], True),
        sayi(n["tarife_kr_kWh"]), sayi(n["yatirim_TL"], True), sayi(n["npv_TL"], True), sayi(n["geri_odeme_yil"], True),
        sayi(r.get("npv_p10"), True), sayi(r.get("npv_p50"), True), sayi(r.get("npv_p90"), True),
        sayi(r.get("p_npv_poz")), sayi(r.get("ilk100_hepsi")), sayi(grup_ilk),
    ]
    w(f"INSERT INTO cati_sonuc ({kolonlar}) VALUES ({', '.join(degerler)});\n")

w("\nCOMMIT;\n")
print(f"{len(idler)} cati, tarama {TARAMA}", file=sys.stderr)
