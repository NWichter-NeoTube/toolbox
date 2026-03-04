-- Create databases for services that need their own DB.
-- Runs automatically on first PostgreSQL start.

-- Grafana
CREATE DATABASE grafana;

-- Sentry
CREATE DATABASE sentry;

-- Unleash
CREATE DATABASE unleash;

-- PostHog
CREATE DATABASE posthog;

-- Infisical
CREATE DATABASE infisical;

-- Grant the default user full access to all databases
DO $$
DECLARE
    db TEXT;
BEGIN
    FOR db IN SELECT unnest(ARRAY['grafana','sentry','unleash','posthog','infisical'])
    LOOP
        EXECUTE format('GRANT ALL PRIVILEGES ON DATABASE %I TO toolbox', db);
    END LOOP;
END $$;
