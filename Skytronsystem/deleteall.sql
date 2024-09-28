DO $$ 
DECLARE 
    r RECORD;
    keep_table CONSTANT text := 'skytron_api_user';
BEGIN 
    -- Disable triggers temporarily to avoid foreign key constraint issues
    PERFORM set_config('session_replication_role', 'replica', true);

    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != keep_table) LOOP 
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE;';
    END LOOP;

    -- Re-enable triggers
    PERFORM set_config('session_replication_role', 'origin', true);
END $$;
