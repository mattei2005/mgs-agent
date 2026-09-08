CREATE TABLE IF NOT EXISTS finance_users (
 username text PRIMARY KEY CHECK(username ~ '^[a-z0-9_.-]{3,40}$' AND username <> 'rodolfo'),
 display_name text NOT NULL, role text NOT NULL CHECK(role IN ('partner','manager')),
 manager_key text CHECK(manager_key IS NULL OR manager_key='nicolas'),
 enabled boolean NOT NULL DEFAULT false, salt text, password_hash text,
 revision integer NOT NULL DEFAULT 0, created_at timestamptz NOT NULL DEFAULT now(),
 CHECK((role='manager' AND manager_key='nicolas') OR (role='partner' AND manager_key IS NULL)),
 CHECK(NOT enabled OR (salt IS NOT NULL AND password_hash IS NOT NULL))
);
ALTER TABLE finance_users ADD COLUMN IF NOT EXISTS email text NOT NULL DEFAULT '';
ALTER TABLE finance_users ADD COLUMN IF NOT EXISTS phone text NOT NULL DEFAULT '';
ALTER TABLE finance_users ADD COLUMN IF NOT EXISTS discord_id text NOT NULL DEFAULT '';
CREATE TABLE IF NOT EXISTS finance_approvals (
 id uuid PRIMARY KEY, actor text NOT NULL, path text NOT NULL, payload jsonb NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
 created_at timestamptz NOT NULL DEFAULT now(), decided_at timestamptz, decided_by text, reason text,
 notified_at timestamptz, notification_message text
);
CREATE TABLE IF NOT EXISTS finance_ledger (
 id uuid PRIMARY KEY, counterparty text NOT NULL, period text NOT NULL,
 effective_date date NOT NULL, kind text NOT NULL CHECK(kind IN ('adjustment','payment')),
 amount_cents bigint NOT NULL CHECK(amount_cents > 0 AND amount_cents <= 100000000000),
 direction smallint NOT NULL CHECK(direction IN (-1,1)), description text NOT NULL,
 actor text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 voided_at timestamptz, voided_by text,
 CHECK(kind <> 'payment' OR direction=-1)
);
CREATE INDEX IF NOT EXISTS finance_ledger_party_period ON finance_ledger(counterparty,period);
