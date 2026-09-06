CREATE TABLE IF NOT EXISTS imports (
 id text PRIMARY KEY, source_sha256 text NOT NULL UNIQUE, period date NOT NULL,
 manifest jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS source_cells (
 import_id text NOT NULL REFERENCES imports(id), id text NOT NULL,
 book text NOT NULL, sheet text NOT NULL, cell text NOT NULL, row_no integer NOT NULL,
 kind text NOT NULL, formula text, input jsonb, expected jsonb NOT NULL,
 formatted text NOT NULL, description text NOT NULL, data jsonb NOT NULL,
 PRIMARY KEY (import_id,id)
);
CREATE INDEX IF NOT EXISTS source_lookup ON source_cells(import_id,book,sheet,row_no);
CREATE TABLE IF NOT EXISTS scenarios (
 id text PRIMARY KEY, import_id text NOT NULL REFERENCES imports(id), name text NOT NULL,
 state text NOT NULL CHECK(state IN ('baseline','draft','locked')),
 revision integer NOT NULL DEFAULT 0, overrides jsonb NOT NULL DEFAULT '{}',
 additions jsonb NOT NULL DEFAULT '[]', result jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS entity_versions (
 scenario_id text NOT NULL REFERENCES scenarios(id), entity_id text NOT NULL,
 version integer NOT NULL, kind text NOT NULL CHECK(kind IN ('site','country','partner','manager')),
 name text NOT NULL, valid_from date NOT NULL, valid_until date,
 attributes jsonb NOT NULL, PRIMARY KEY(scenario_id,entity_id,version),
 CHECK(valid_until IS NULL OR valid_until>=valid_from)
);
CREATE TABLE IF NOT EXISTS audit_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, scenario_id text REFERENCES scenarios(id),
 actor text NOT NULL, action text NOT NULL, before_data jsonb, after_data jsonb,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS acceptance_runs (
 id text PRIMARY KEY, scenario_id text NOT NULL REFERENCES scenarios(id),
 status text NOT NULL, summary jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
