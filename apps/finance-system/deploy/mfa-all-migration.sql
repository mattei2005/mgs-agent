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
CREATE TABLE IF NOT EXISTS auth_trusted_devices (
 id uuid PRIMARY KEY,
 token_hash text UNIQUE NOT NULL CHECK(token_hash ~ '^[a-f0-9]{64}$'),
 username text NOT NULL CHECK(username ~ '^[a-z0-9_.-]{3,40}$'),
 user_agent_hash text NOT NULL CHECK(user_agent_hash ~ '^[a-f0-9]{64}$'),
 created_at timestamptz NOT NULL DEFAULT now(),
 last_used timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL,
 revoked boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS auth_trusted_devices_user_active ON auth_trusted_devices(username,revoked,expires_at);
REVOKE ALL ON auth_trusted_devices FROM PUBLIC;
GRANT SELECT,INSERT,UPDATE ON auth_trusted_devices TO mgsfinance;
COMMIT;
