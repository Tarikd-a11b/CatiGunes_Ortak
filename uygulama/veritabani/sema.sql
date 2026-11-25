-- =====================================================================
-- CatiGunes web veritabani  v4 (2026-11-23)
-- PostgreSQL + PostGIS. Web haritasi ve REST API bu veritabanini okur.
--
-- Tablolar
--   bolge          : Atatürk OSB ve Çiğli kamu (sinir + 1 kWp yillik uretim)
--   tarama         : bir veri yuklemesi (ayni bolge tekrar taranirsa yeni satir)
--   cati           : catinin degismeyen kimligi
--   cati_sonuc     : catinin bir taramadaki geometrisi, uretimi ve ekonomisi
--   cati_aciklama  : LLM'in cati icin yazdigi dort baslikli metin
-- Gorunumler
--   v_cati         : her catinin en guncel taramadaki hali + siralar (API/harita)
--   v_ozet         : bolge x tur toplamlari
--
-- Bilerek tutulmayanlar: SAM kosu ayrintilari, goruntu kesitleri, insan
-- cizimleri, firma listesi (10 Kasim karari: firma adi arayuze alinmaz),
-- saatlik/aylik PVGIS serileri, Monte Carlo senaryolari. Bunlar repoda
-- model_verisi/ altinda kalir; arayuz bunlara ihtiyac duymaz.
--
-- Geometriler WGS84 (EPSG:4326).
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- ---------------------------------------------------------------------
-- BOLGE
-- ---------------------------------------------------------------------
CREATE TABLE bolge (
    bolge_kod             TEXT PRIMARY KEY CHECK (bolge_kod IN ('ataturk_osb', 'cigli_kamu')),
    ad                    TEXT NOT NULL,
    ozgul_uretim_kwh_kwp  NUMERIC(7,2) NOT NULL,      -- PVGIS v5.3, guneye 10 derece, %14 kayip
    sinir                 geometry(MultiPolygon, 4326)
);

-- ---------------------------------------------------------------------
-- TARAMA: her yukleme ayri satir, eski taramalar silinmez
-- ---------------------------------------------------------------------
CREATE TABLE tarama (
    tarama_id  SERIAL PRIMARY KEY,
    kod        TEXT NOT NULL UNIQUE,                  -- ornek: 2026-11_ara_rapor
    aciklama   TEXT,                                  -- goruntu tarihleri, veri surumu
    yuklenme   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- CATI: zamanla degismeyen kimlik
-- ---------------------------------------------------------------------
CREATE TABLE cati (
    cati_id    INTEGER PRIMARY KEY,                   -- veri hattindaki kalici numara
    osm        TEXT NOT NULL UNIQUE,                  -- way/... veya ms_... (Microsoft)
    bolge_kod  TEXT NOT NULL REFERENCES bolge (bolge_kod),
    tur        TEXT NOT NULL CHECK (tur IN ('sanayi', 'sanayi_disi', 'okul', 'hastane', 'universite')),
    kurum_ad   TEXT,                                  -- yalniz kamu binalarinda
    grup       TEXT GENERATED ALWAYS AS (
                   CASE WHEN tur = 'sanayi' THEN 'sanayi'
                        WHEN tur IN ('okul', 'hastane', 'universite') THEN 'kamu'
                        ELSE 'diger' END) STORED,      -- oncelik listeleri sanayi ve kamu icin ayri
    CHECK ((bolge_kod = 'ataturk_osb' AND tur IN ('sanayi', 'sanayi_disi'))
        OR (bolge_kod = 'cigli_kamu'  AND tur IN ('okul', 'hastane', 'universite')))
);
CREATE INDEX cati_bolge_tur_idx ON cati (bolge_kod, tur);

-- ---------------------------------------------------------------------
-- CATI_SONUC: catinin bir taramadaki hali
-- Tamamen panelli (tam_dolu) catilarda potansiyel yoktur: kwp ve kwh 0,
-- ekonomi alanlari NULL. Harita bunlari "mevcut GES" diye gostermeli.
-- ---------------------------------------------------------------------
CREATE TABLE cati_sonuc (
    cati_id           INTEGER NOT NULL REFERENCES cati (cati_id),
    tarama_id         INTEGER NOT NULL REFERENCES tarama (tarama_id) ON DELETE CASCADE,

    -- geometri
    geom              geometry(MultiPolygon, 4326) NOT NULL,   -- son cati geometrisi
    geom_uygun        geometry(MultiPolygon, 4326),            -- panelsiz kisim; tam_dolu ise NULL
    geometri_kaynagi  TEXT NOT NULL CHECK (geometri_kaynagi IN ('sam', 'insan', 'ayak_izi')),
    supheli           BOOLEAN NOT NULL,                        -- SAM maskesi supheli isaretli
    panel_durumu      TEXT NOT NULL CHECK (panel_durumu IN ('panel_yok', 'kismi_panel_dusuldu', 'tam_dolu')),
    cati_alan_m2      NUMERIC(10,1) NOT NULL CHECK (cati_alan_m2 > 0),
    uygun_alan_m2     NUMERIC(10,1) NOT NULL CHECK (uygun_alan_m2 >= 0),

    -- uretim (temel senaryo, alt-ust: kurulum varsayimlarina gore aralik)
    kwp               NUMERIC(9,1)  NOT NULL CHECK (kwp >= 0),
    kwh_yil           INTEGER       NOT NULL CHECK (kwh_yil >= 0),
    kwh_alt           INTEGER       NOT NULL,
    kwh_ust           INTEGER       NOT NULL,

    -- ekonomi (temel senaryo)
    tarife_kr_kwh     NUMERIC(8,2)  NOT NULL,                  -- EPDK, vergi haric
    yatirim_tl        BIGINT,
    npv_tl            BIGINT,
    geri_odeme_yil    SMALLINT,

    -- belirsizlik (Monte Carlo, 10.000 senaryo)
    npv_p10           BIGINT,
    npv_p50           BIGINT,
    npv_p90           BIGINT,
    p_npv_poz         NUMERIC(5,4) CHECK (p_npv_poz BETWEEN 0 AND 1),       -- NPV'nin pozitif ciktigi senaryo payi
    ilk100_orani      NUMERIC(5,4) CHECK (ilk100_orani BETWEEN 0 AND 1),    -- tum catilarda ilk 100'de kalma payi
    grup_ilk_orani    NUMERIC(5,4) CHECK (grup_ilk_orani BETWEEN 0 AND 1),  -- sanayi: ilk 50, kamu: ilk 20

    PRIMARY KEY (cati_id, tarama_id),
    CHECK (kwh_alt <= kwh_yil AND kwh_yil <= kwh_ust),
    CHECK (uygun_alan_m2 <= cati_alan_m2),
    CHECK (panel_durumu <> 'tam_dolu'
           OR (uygun_alan_m2 = 0 AND kwp = 0 AND kwh_yil = 0 AND npv_tl IS NULL AND geom_uygun IS NULL)),
    CHECK (panel_durumu = 'tam_dolu'
           OR (geom_uygun IS NOT NULL AND yatirim_tl IS NOT NULL AND npv_tl IS NOT NULL
               AND geri_odeme_yil IS NOT NULL AND npv_p50 IS NOT NULL)),
    CHECK (npv_p10 IS NULL OR (npv_p10 <= npv_p50 AND npv_p50 <= npv_p90))
);
CREATE INDEX cati_sonuc_tarama_idx ON cati_sonuc (tarama_id);
CREATE INDEX cati_sonuc_geom_gix   ON cati_sonuc USING GIST (geom);

-- ---------------------------------------------------------------------
-- CATI_ACIKLAMA: LLM metni (yeni hesap yapmaz, cati_sonuc'u metne cevirir)
-- Metindeki sayilar kayitla eslesmezse sayilar_tutarli = false olur ve
-- arayuz sabit sablonu gosterir.
-- ---------------------------------------------------------------------
CREATE TABLE cati_aciklama (
    cati_id            INTEGER NOT NULL,
    tarama_id          INTEGER NOT NULL,
    ozet               TEXT NOT NULL,
    sira_nedeni        TEXT NOT NULL,
    belirsizlik        TEXT NOT NULL,
    veri_guvenilirligi TEXT NOT NULL,
    sayilar_tutarli    BOOLEAN NOT NULL,
    model              TEXT NOT NULL,
    olusturma          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (cati_id, tarama_id),
    FOREIGN KEY (cati_id, tarama_id) REFERENCES cati_sonuc (cati_id, tarama_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- GORUNUMLER
-- ---------------------------------------------------------------------

-- Her catinin en guncel hali + siralar. Siralar yalniz potansiyeli olan
-- (tam_dolu olmayan) catilar arasinda, en guncel veriye gore hesaplanir.
CREATE VIEW v_cati AS
WITH guncel AS (
    SELECT DISTINCT ON (s.cati_id) s.*
    FROM cati_sonuc s
    ORDER BY s.cati_id, s.tarama_id DESC
),
siralar AS (
    SELECT g.cati_id,
           row_number() OVER (ORDER BY g.npv_tl DESC, g.cati_id)                          AS sira_npv,
           row_number() OVER (ORDER BY g.kwh_yil DESC, g.cati_id)                         AS sira_uretim,
           row_number() OVER (ORDER BY g.npv_tl::numeric / g.kwp DESC, g.cati_id)         AS sira_npv_kwp,
           CASE WHEN c.grup <> 'diger' THEN
               row_number() OVER (PARTITION BY c.grup ORDER BY g.npv_tl DESC, g.cati_id) END AS sira_grup
    FROM guncel g JOIN cati c USING (cati_id)
    WHERE g.panel_durumu <> 'tam_dolu'
)
SELECT c.cati_id, c.osm, c.bolge_kod, c.tur, c.grup, c.kurum_ad,
       t.kod AS tarama, g.tarama_id,
       g.geometri_kaynagi, g.supheli, g.panel_durumu,
       g.cati_alan_m2, g.uygun_alan_m2,
       g.kwp, g.kwh_yil, g.kwh_alt, g.kwh_ust,
       g.tarife_kr_kwh, g.yatirim_tl, g.npv_tl,
       round(g.npv_tl::numeric / nullif(g.kwp, 0)) AS npv_tl_kwp,
       g.geri_odeme_yil,
       g.npv_p10, g.npv_p50, g.npv_p90, g.p_npv_poz, g.ilk100_orani, g.grup_ilk_orani,
       r.sira_npv, r.sira_uretim, r.sira_npv_kwp, r.sira_grup,
       (a.cati_id IS NOT NULL AND a.sayilar_tutarli) AS aciklama_var,
       ST_PointOnSurface(g.geom) AS konum,
       g.geom, g.geom_uygun
FROM guncel g
JOIN cati c   USING (cati_id)
JOIN tarama t ON t.tarama_id = g.tarama_id
LEFT JOIN siralar r USING (cati_id)
LEFT JOIN cati_aciklama a ON a.cati_id = g.cati_id AND a.tarama_id = g.tarama_id;

-- Bolge x tur toplamlari (en guncel veriye gore)
CREATE VIEW v_ozet AS
SELECT bolge_kod, tur,
       count(*)                                          AS cati,
       count(*) FILTER (WHERE panel_durumu <> 'tam_dolu') AS potansiyelli_cati,
       count(*) FILTER (WHERE panel_durumu <> 'panel_yok') AS mevcut_ges_cati,
       round(sum(cati_alan_m2))                          AS cati_alan_m2,
       round(sum(uygun_alan_m2))                         AS uygun_alan_m2,
       round(sum(kwp) / 1000, 2)                         AS mwp,
       round(sum(kwh_yil) / 1e6, 2)                      AS gwh_yil,
       round(sum(yatirim_tl) / 1e6, 1)                   AS yatirim_milyon_tl,
       round(sum(npv_tl) / 1e6, 1)                       AS npv_milyon_tl
FROM v_cati
GROUP BY bolge_kod, tur;
