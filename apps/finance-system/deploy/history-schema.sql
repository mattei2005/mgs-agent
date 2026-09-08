BEGIN;
CREATE TABLE IF NOT EXISTS finance_history (
 period text NOT NULL CHECK(period ~ '^2026-0[1-7]$'),
 book text NOT NULL CHECK(book IN ('principal','nicolas','joe','kelly','isliago','george')),
 source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[a-f0-9]{64}$'),
 payload jsonb NOT NULL CHECK(payload->>'mode'='closed-history' AND (payload->>'read_only')::boolean AND payload->>'period'=period AND payload->>'book'=book),
 imported_at timestamptz NOT NULL DEFAULT now(),
 authority text NOT NULL CHECK(authority='1546884731436671056'),
 PRIMARY KEY(period,book)
);
CREATE OR REPLACE FUNCTION finance_history_immutable() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'Closed history is immutable; supersession requires a separate approved migration'; END;$$;
CREATE OR REPLACE TRIGGER finance_history_immutable BEFORE UPDATE OR DELETE ON finance_history FOR EACH ROW EXECUTE FUNCTION finance_history_immutable();
REVOKE ALL ON finance_history FROM PUBLIC;
GRANT SELECT ON finance_history TO mgsfinance;
COMMIT;
