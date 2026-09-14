BEGIN;
CREATE TABLE IF NOT EXISTS auth_mfa (
 username text PRIMARY KEY CHECK(username ~ '^[a-z0-9_.-]{3,40}$'),
 status text NOT NULL CHECK(status IN ('pending','active')),
 secret_encrypted text NOT NULL CHECK(secret_encrypted ~ '^[0-9a-f]+:[0-9a-f]+:[0-9a-f]+$'),
 enrollment_expires_at timestamptz,
 recovery_hashes jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_typeof(recovery_hashes)='array'),
 last_counter bigint CHECK(last_counter IS NULL OR last_counter >= 0),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 confirmed_at timestamptz,
 CHECK((status='pending' AND enrollment_expires_at IS NOT NULL AND confirmed_at IS NULL) OR (status='active' AND enrollment_expires_at IS NULL AND confirmed_at IS NOT NULL))
);
REVOKE ALL ON auth_mfa FROM PUBLIC;
GRANT SELECT,INSERT,UPDATE ON auth_mfa TO mgsfinance;
COMMIT;
