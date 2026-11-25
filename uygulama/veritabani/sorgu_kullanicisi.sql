-- Web haritasindaki "Sorgu" paneli icin salt okunur kullanici.
-- Bu kullaniciyla hicbir tablo degistirilemez; her sorgu en fazla 5 saniye surer.
-- Sifre psql degiskeni olarak verilir:
--   docker exec -i catigunes_db psql -U postgres -d catigunes_web -v sifre="'...'" < sorgu_kullanicisi.sql

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sorgu_okur') THEN
    CREATE ROLE sorgu_okur LOGIN;
  END IF;
END $$;
ALTER ROLE sorgu_okur PASSWORD :sifre;

GRANT CONNECT ON DATABASE catigunes_web TO sorgu_okur;
GRANT USAGE ON SCHEMA public TO sorgu_okur;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sorgu_okur;   -- tablolar ve gorunumler
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO sorgu_okur;

ALTER ROLE sorgu_okur IN DATABASE catigunes_web SET default_transaction_read_only = on;
ALTER ROLE sorgu_okur IN DATABASE catigunes_web SET statement_timeout = '5s';
