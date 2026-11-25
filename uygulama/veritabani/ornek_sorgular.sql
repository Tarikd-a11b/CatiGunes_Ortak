-- =====================================================================
-- CatiGunes veritabani: ornek sorgular (ekip sunumu)
-- pgAdmin > catigunes_web > Query Tool. Bir sorguyu secip F5 ile calistir.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. VERITABANINDA NE VAR?
-- ---------------------------------------------------------------------

-- 1.1 Tablolar ve satir sayilari
SELECT 'bolge' AS tablo, count(*) AS satir FROM bolge
UNION ALL SELECT 'tarama',        count(*) FROM tarama
UNION ALL SELECT 'cati',          count(*) FROM cati
UNION ALL SELECT 'cati_sonuc',    count(*) FROM cati_sonuc
UNION ALL SELECT 'cati_aciklama', count(*) FROM cati_aciklama;

-- 1.2 Yuklenen veri (tarama)
SELECT * FROM tarama;

-- 1.3 Bolgeler: 1 kWp yillik uretim ve sinir alani
SELECT bolge_kod, ad, ozgul_uretim_kwh_kwp,
       round((ST_Area(sinir::geography) / 1e6)::numeric, 2) AS alan_km2
FROM bolge;


-- ---------------------------------------------------------------------
-- 2. CATILAR: KIMLIK VE TUR
-- ---------------------------------------------------------------------

-- 2.1 Grup ve ture gore cati sayisi
SELECT grup, tur, bolge_kod, count(*) AS cati
FROM cati GROUP BY grup, tur, bolge_kod ORDER BY grup, tur;

-- 2.2 Kamu binalari kuruma gore
SELECT kurum_ad, tur, count(*) AS cati
FROM cati WHERE grup = 'kamu'
GROUP BY kurum_ad, tur ORDER BY cati DESC;


-- ---------------------------------------------------------------------
-- 3. TEK BIR CATI (haritada tiklaninca gelen bilgi)
-- ---------------------------------------------------------------------

-- 3.1 Sanayide birinci cati
SELECT cati_id, tur, grup, panel_durumu, geometri_kaynagi, supheli,
       cati_alan_m2, uygun_alan_m2, kwp, kwh_yil, kwh_alt, kwh_ust,
       yatirim_tl, npv_tl, geri_odeme_yil,
       npv_p10, npv_p50, npv_p90, p_npv_poz,
       sira_npv, sira_grup
FROM v_cati WHERE cati_id = 47;

-- 3.2 Ayni cati icin GeoJSON (haritaya giden geometri)
SELECT cati_id, ST_AsGeoJSON(geom, 6) AS geojson FROM v_cati WHERE cati_id = 47;


-- ---------------------------------------------------------------------
-- 4. OZETLER (raporun Tablo 7, 12 ve 14'u)
-- ---------------------------------------------------------------------

-- 4.1 Bolge x tur toplamlari
SELECT * FROM v_ozet ORDER BY bolge_kod, tur;

-- 4.2 Genel toplam (rapor: 177,7 MWp, 263,1 GWh, NPV 4.167 milyon TL)
SELECT count(*)                         AS cati,
       round(sum(cati_alan_m2))         AS cati_alan_m2,
       round(sum(uygun_alan_m2))        AS uygun_alan_m2,
       round(sum(kwp) / 1000, 1)        AS mwp,
       round(sum(kwh_yil) / 1e6, 1)     AS gwh_yil,
       round(sum(yatirim_tl) / 1e6)     AS yatirim_milyon_tl,
       round(sum(npv_tl) / 1e6)         AS npv_milyon_tl
FROM v_cati;

-- 4.3 Mevcut panel durumu (rapor Tablo 12)
SELECT panel_durumu, count(*) AS cati,
       round(sum(cati_alan_m2)) AS cati_alan_m2,
       round(sum(uygun_alan_m2)) AS uygun_alan_m2
FROM v_cati GROUP BY panel_durumu ORDER BY panel_durumu;

-- 4.4 Geometri kaynagi
SELECT geometri_kaynagi, count(*) AS cati,
       count(*) FILTER (WHERE supheli) AS supheli
FROM v_cati GROUP BY geometri_kaynagi;


-- ---------------------------------------------------------------------
-- 5. ONCELIK LISTELERI
-- ---------------------------------------------------------------------

-- 5.1 Sanayi ilk 10
SELECT sira_grup, cati_id, round(uygun_alan_m2) AS alan_m2, kwp,
       round(npv_tl / 1e6, 1) AS npv_milyon_tl, geri_odeme_yil,
       round(p_npv_poz * 100) AS karli_senaryo_yuzde
FROM v_cati WHERE grup = 'sanayi'
ORDER BY sira_grup LIMIT 10;

-- 5.2 Kamu ilk 10
SELECT sira_grup, cati_id, kurum_ad, tur, kwp,
       round(npv_tl / 1e6, 1) AS npv_milyon_tl, geri_odeme_yil
FROM v_cati WHERE grup = 'kamu'
ORDER BY sira_grup LIMIT 10;

-- 5.3 Kurulan her kWp basina en cok getiri saglayan 10 cati
--     (kamu tarifesi yuksek oldugu icin kamu binalari one cikar)
SELECT sira_npv_kwp, cati_id, tur, kurum_ad, kwp, npv_tl_kwp
FROM v_cati WHERE sira_npv_kwp IS NOT NULL
ORDER BY sira_npv_kwp LIMIT 10;


-- ---------------------------------------------------------------------
-- 6. BELIRSIZLIK
-- ---------------------------------------------------------------------

-- 6.1 Her kosulda oncelikli sanayi catilari (senaryolarin %95'inden fazlasinda ilk 50'de)
SELECT cati_id, sira_grup, round(grup_ilk_orani * 100) AS ilk50_yuzde,
       round(npv_p10 / 1e6, 1) AS kotu_milyon, round(npv_tl / 1e6, 1) AS temel_milyon,
       round(npv_p90 / 1e6, 1) AS iyi_milyon
FROM v_cati WHERE grup = 'sanayi' AND grup_ilk_orani >= 0.95
ORDER BY sira_grup;

-- 6.2 Senaryolarin %10'undan fazlasinda zarar eden catilar
SELECT tur, count(*) AS cati
FROM v_cati WHERE p_npv_poz < 0.9
GROUP BY tur ORDER BY cati DESC;


-- ---------------------------------------------------------------------
-- 7. BUTCE SENARYOSU
-- ---------------------------------------------------------------------

-- 7.1 500 milyon TL butceyle NPV sirasina gore kac cati yapilabilir?
--     Siradan sapmadan, butce asilana kadar sayar. (YONTEM.md'deki 13 cati,
--     butceye sigmayan catiyi atlayip sonrakilerle devam eden farkli bir hesaptir.)
SELECT count(*) AS cati, round(sum(kwp) / 1000, 1) AS mwp,
       round(max(kumulatif) / 1e6) AS yatirim_milyon_tl,
       round(sum(npv_tl) / 1e6) AS npv_milyon_tl
FROM (
  SELECT *, sum(yatirim_tl) OVER (ORDER BY sira_npv) AS kumulatif
  FROM v_cati WHERE sira_npv IS NOT NULL
) x
WHERE kumulatif <= 500e6;


-- ---------------------------------------------------------------------
-- 8. MEKANSAL SORGULAR (PostGIS)
-- ---------------------------------------------------------------------

-- 8.1 Ataturk OSB sinir poligonu icindeki potansiyel
--     Catilar bolge koduna gore degil, konumlarina gore secilir (ST_Intersects).
--     Toplam, v_ozet'teki OSB satirlariyla (sanayi + sanayi_disi) ayni cikmalidir.
SELECT c.tur,
       count(*)                       AS cati,
       round(sum(c.uygun_alan_m2))    AS uygun_alan_m2,
       round(sum(c.kwp) / 1000, 2)    AS mwp,
       round(sum(c.kwh_yil) / 1e6, 2) AS gwh_yil,
       round(sum(c.npv_tl) / 1e6, 1)  AS npv_milyon_tl
FROM v_cati c
JOIN bolge b ON b.bolge_kod = 'ataturk_osb'
WHERE ST_Intersects(c.geom, b.sinir)
GROUP BY c.tur
ORDER BY cati DESC;

-- 8.2 Veritabaninda hesaplanan alan ile veri hattindaki alanin karsilastirmasi
SELECT count(*) AS cati,
       round(avg(abs(ST_Area(geom::geography)::numeric - cati_alan_m2) / cati_alan_m2) * 100, 2) AS ort_fark_yuzde
FROM cati_sonuc;


-- ---------------------------------------------------------------------
-- 9. VERI KURALLARI (veritabani hatali kaydi reddeder)
-- ---------------------------------------------------------------------

-- 9.1 Tamamen panelli bir catiya NPV girmeye calis -> HATA verir (beklenen)
-- UPDATE cati_sonuc SET npv_tl = 1000 WHERE cati_id = 13;

-- 9.2 OSB'ye kamu turunde bina eklemeye calis -> HATA verir (beklenen)
-- INSERT INTO cati (cati_id, osm, bolge_kod, tur) VALUES (99999, 'deneme', 'ataturk_osb', 'okul');
