-- Authority Rodolfo1546858367635685396; bounded application-user expansion.
BEGIN;
SET LOCAL lock_timeout = '5s';
ALTER TABLE finance_users DROP CONSTRAINT finance_users_manager_key_check;
ALTER TABLE finance_users DROP CONSTRAINT finance_users_check;
ALTER TABLE finance_users ADD CONSTRAINT finance_users_manager_key_check CHECK (manager_key IS NULL OR manager_key IN ('nicolas','joe','isliago','kelly','icaro'));
ALTER TABLE finance_users ADD CONSTRAINT finance_users_check CHECK ((role='manager' AND manager_key IS NOT NULL AND manager_key IN ('nicolas','joe','isliago','kelly','icaro')) OR (role='partner' AND manager_key IS NULL));
COMMIT;
