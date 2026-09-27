-- Align the NIC schema with dev (reference) for the differences reported by db_compare.py.
-- Run through run_sql.py, which wraps everything in ONE transaction (all or nothing).
-- Behaviour of the application does not change:
--   * Django always supplies these column values itself, so the DB-level DEFAULTs were unused.
--   * ON DELETE CASCADE is performed by Django's ORM (models use on_delete=CASCADE), so the
--     DB-level CASCADE was redundant. Django creates FKs as DEFERRABLE INITIALLY DEFERRED.

-- 1) Drop DB-level defaults that exist only on NIC
ALTER TABLE skytron_api_devicemodeltechnicalonboardingrequest ALTER COLUMN request_datetime DROP DEFAULT;
ALTER TABLE skytron_api_devicemodeltechnicalonboardingrequest ALTER COLUMN status           DROP DEFAULT;
ALTER TABLE skytron_api_dto_rto      ALTER COLUMN expirydate DROP DEFAULT;
ALTER TABLE skytron_api_em_admin     ALTER COLUMN expirydate DROP DEFAULT;
ALTER TABLE skytron_api_em_ex        ALTER COLUMN expirydate DROP DEFAULT;
ALTER TABLE skytron_api_esimprovider ALTER COLUMN expirydate DROP DEFAULT;
ALTER TABLE skytron_api_manufacturer ALTER COLUMN expirydate DROP DEFAULT;
ALTER TABLE skytron_api_retailer     ALTER COLUMN expirydate DROP DEFAULT;
ALTER TABLE skytron_api_stateadmin   ALTER COLUMN expirydate DROP DEFAULT;
ALTER TABLE skytron_api_vehicleowner ALTER COLUMN expirydate DROP DEFAULT;

-- 2) Replace the hand-made ON DELETE CASCADE foreign keys with Django-style ones (same as dev)
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT DISTINCT rel.relname, con.conname
    FROM pg_constraint con
    JOIN pg_class rel     ON rel.oid = con.conrelid
    JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY (con.conkey)
    WHERE con.contype = 'f'
      AND (   (rel.relname = 'skytron_api_devicemodeltechnicalonboardingdemodevice' AND att.attname = 'onboarding_request_id')
           OR (rel.relname = 'skytron_api_devicemodeltechnicalonboardingrequest'    AND att.attname IN ('device_model_id', 'manufacturer_id')))
  LOOP
    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.relname, r.conname);
  END LOOP;
END $$;

ALTER TABLE skytron_api_devicemodeltechnicalonboardingdemodevice
  ADD CONSTRAINT skytron_api_devicemo_onboarding_request_i_2390262e_fk_skytron_a
  FOREIGN KEY (onboarding_request_id) REFERENCES skytron_api_devicemodeltechnicalonboardingrequest (id)
  DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE skytron_api_devicemodeltechnicalonboardingrequest
  ADD CONSTRAINT skytron_api_devicemo_device_model_id_bf0e1360_fk_skytron_a
  FOREIGN KEY (device_model_id) REFERENCES skytron_api_devicemodel (id)
  DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE skytron_api_devicemodeltechnicalonboardingrequest
  ADD CONSTRAINT skytron_api_devicemo_manufacturer_id_04db2656_fk_skytron_a
  FOREIGN KEY (manufacturer_id) REFERENCES skytron_api_manufacturer (id)
  DEFERRABLE INITIALLY DEFERRED;

-- 3) Missing LIKE-search index (Django creates it for indexed CharFields)
CREATE INDEX IF NOT EXISTS skytron_api_devicemodelt_status_f7d6e857_like
  ON skytron_api_devicemodeltechnicalonboardingrequest USING btree (status varchar_pattern_ops);
