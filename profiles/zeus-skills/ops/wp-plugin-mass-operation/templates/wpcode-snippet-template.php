<?php
/**
 * Zeus Deploy Snippet — Template Canônico
 *
 * USO: Este arquivo é um TEMPLATE. Nunca copiar manualmente para produção.
 * O placeholder ${B64_PAYLOAD} deve ser substituído pelo output exato de:
 *
 *   b64=$(base64 -w 0 /root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php)
 *   echo "$b64" | base64 -d | md5sum   # deve bater com 069270de4c07a9d15838ff45df65f539
 *
 * Só usar após validação MD5 reversa. Ver PITFALL FATAL #1 na skill.
 *
 * Após confirmar deploy via MD5 SFTP → REMOVER este snippet imediatamente (Passo 6).
 */

add_action( 'admin_init', function () {

    // ── Caminhos ──────────────────────────────────────────────────────────────
    $mu_dir  = WP_CONTENT_DIR . '/mu-plugins';
    $target  = $mu_dir . '/yoast-rest-meta.php';
    $hide    = $mu_dir . '/hide-from-home.php';

    // ── Payload (b64 gerado por: base64 -w 0 yoast-rest-meta.php) ─────────────
    // NUNCA editar esta string manualmente após substituição do placeholder.
    $b64 = '${B64_PAYLOAD}';

    // ── Garantir que mu-plugins/ existe ───────────────────────────────────────
    if ( ! is_dir( $mu_dir ) ) {
        wp_mkdir_p( $mu_dir );
    }

    // ── Escrever arquivo canônico em disco ────────────────────────────────────
    $content = base64_decode( $b64 );
    file_put_contents( $target, $content );

    // ── Remover hide-from-home.php se ainda presente ──────────────────────────
    $hide_deleted = false;
    if ( file_exists( $hide ) ) {
        unlink( $hide );
        $hide_deleted = ! file_exists( $hide );
    }

    // ── Registrar evidência de deploy no banco ────────────────────────────────
    update_option( 'zeus_deploy_v4_status', array(
        'md5'          => md5_file( $target ),
        'hide_deleted' => $hide_deleted,
        'ts'           => time(),
    ) );

} );
