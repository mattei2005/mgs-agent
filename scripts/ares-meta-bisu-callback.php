<?php
/**
 * MGS Meta Facebook Login for Business callback.
 *
 * Receives a short-lived authorization code, validates a one-time state,
 * persists the code outside the webroot, and never renders credentials.
 * App secrets and access tokens are intentionally not stored on this host.
 */
declare(strict_types=1);

const MGS_OAUTH_STATE_ROOT = '/home/runcloud/webapps/vizioid/mgs-meta-oauth/.state';
const MGS_OAUTH_MAX_CODE_LEN = 4096;
const MGS_OAUTH_MAX_STATE_LEN = 128;

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('Referrer-Policy: no-referrer');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('X-Robots-Tag: noindex, nofollow, noarchive');
header("Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'");
header('Content-Type: text/html; charset=UTF-8');

function finish(int $status, string $title, string $message): never
{
    http_response_code($status);
    $safeTitle = htmlspecialchars($title, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    $safeMessage = htmlspecialchars($message, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    echo '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">';
    echo '<meta name="viewport" content="width=device-width,initial-scale=1">';
    echo '<title>' . $safeTitle . '</title><style>';
    echo 'body{font-family:system-ui,-apple-system,sans-serif;background:#f5f7fb;color:#172033;margin:0;padding:32px}';
    echo 'main{max-width:620px;margin:10vh auto;background:#fff;border:1px solid #dfe4ec;border-radius:14px;padding:28px}';
    echo 'h1{font-size:1.35rem;margin:0 0 12px}p{line-height:1.55;margin:0}';
    echo '</style></head><body><main><h1>' . $safeTitle . '</h1><p>' . $safeMessage . '</p></main></body></html>';
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
    header('Allow: GET');
    finish(405, 'Método não permitido', 'Use somente o fluxo de autorização iniciado pela MGS.');
}

$state = isset($_GET['state']) && is_string($_GET['state']) ? $_GET['state'] : '';
$code = isset($_GET['code']) && is_string($_GET['code']) ? $_GET['code'] : '';
$error = isset($_GET['error']) && is_string($_GET['error']) ? $_GET['error'] : '';

if ($error !== '') {
    finish(400, 'Autorização não concluída', 'A Meta não concedeu a autorização. Você pode fechar esta janela e avisar o Ares.');
}

if ($state === '' || $code === '') {
    finish(400, 'Fluxo inválido', 'Inicie a autorização pelo link único fornecido pela MGS.');
}

if (
    strlen($state) > MGS_OAUTH_MAX_STATE_LEN ||
    !preg_match('/^[A-Za-z0-9_-]{43,128}$/D', $state) ||
    strlen($code) > MGS_OAUTH_MAX_CODE_LEN ||
    preg_match('/[\x00-\x1F\x7F]/', $code)
) {
    finish(400, 'Fluxo inválido', 'Os dados recebidos não passaram na validação de segurança.');
}

$stateHash = hash('sha256', $state);
$pendingDir = MGS_OAUTH_STATE_ROOT . '/pending';
$completedDir = MGS_OAUTH_STATE_ROOT . '/completed';
$pendingPath = $pendingDir . '/' . $stateHash . '.json';
$completedPath = $completedDir . '/' . $stateHash . '.json';

if (!is_file($pendingPath)) {
    finish(403, 'Autorização recusada', 'Este link não é válido, já foi utilizado ou expirou.');
}

$handle = @fopen($pendingPath, 'c+');
if ($handle === false || !flock($handle, LOCK_EX)) {
    if (is_resource($handle)) {
        fclose($handle);
    }
    finish(503, 'Tente novamente', 'Não foi possível validar o fluxo neste momento.');
}

rewind($handle);
$raw = stream_get_contents($handle);
$pending = is_string($raw) ? json_decode($raw, true) : null;
$now = time();

if (
    !is_array($pending) ||
    ($pending['state_sha256'] ?? '') !== $stateHash ||
    !is_int($pending['expires_at'] ?? null) ||
    $pending['expires_at'] < $now ||
    ($pending['consumed'] ?? false) === true ||
    is_file($completedPath)
) {
    flock($handle, LOCK_UN);
    fclose($handle);
    finish(403, 'Autorização recusada', 'Este link não é válido, já foi utilizado ou expirou.');
}

$record = [
    'schema_version' => 1,
    'state_sha256' => $stateHash,
    'manager_code' => (string)($pending['manager_code'] ?? 'unknown'),
    'request_id' => (string)($pending['request_id'] ?? 'unknown'),
    'received_at' => gmdate('c'),
    'authorization_code' => $code,
];

$tmp = tempnam($completedDir, '.oauth-');
if ($tmp === false) {
    flock($handle, LOCK_UN);
    fclose($handle);
    finish(503, 'Tente novamente', 'Não foi possível concluir o recebimento com segurança.');
}

$encoded = json_encode($record, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
if (file_put_contents($tmp, $encoded . "\n", LOCK_EX) === false || !chmod($tmp, 0600) || !rename($tmp, $completedPath)) {
    @unlink($tmp);
    flock($handle, LOCK_UN);
    fclose($handle);
    finish(503, 'Tente novamente', 'Não foi possível concluir o recebimento com segurança.');
}

$pending['consumed'] = true;
$pending['consumed_at'] = gmdate('c');
rewind($handle);
ftruncate($handle, 0);
fwrite($handle, json_encode($pending, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . "\n");
fflush($handle);
flock($handle, LOCK_UN);
fclose($handle);
@chmod($pendingPath, 0600);

finish(200, 'Autorização recebida', 'Concluído. Nenhum token foi exibido. Você pode fechar esta janela e avisar o Ares.');
