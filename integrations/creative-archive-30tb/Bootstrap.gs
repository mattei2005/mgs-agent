function mgsArquivoTeste(e) {
  if (ScriptApp.getScriptId() !== '1NxZ0ZTgZk4f3pzzX3fQQ-Y2wKpunjYbAaxbO8HN1fe9R5gXbEYVLpbUF') {
    throw new Error('PROJETO_INCORRETO');
  }
  var codigo = DriveApp.getFileById('1eZAvS7WhnzMglzRY3NWWnEguBdS5mrPS').getBlob().getDataAsString('UTF-8');
  var hash = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, codigo, Utilities.Charset.UTF_8)
    .map(function(b) { return ('0' + ((b + 256) % 256).toString(16)).slice(-2); }).join('');
  if (hash !== '7c31864eba74f25e0717c174490134f61ecd20d51c119177647393aae693fe81') {
    throw new Error('CODIGO_DIVERGENTE_NAO_EXECUTADO');
  }
  var config = {"account":"mgsdigitalcorp@gmail.com","sourceDriveId":"0AEwt4Ye690ocUk9PVA","sourceRootId":"1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa","archiveRootId":"1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J","controlFolderId":"1d3w4Xc1EjrmueciM_vCMgva6qJiqpFJR","requestsFolderId":"1yjIOwDLmhAaLNmDdt701WpoFNzNeDXGk","receiptsFolderId":"1gmXrQ-nszxNCwqSytsbX5AEnhm1rvXUL","effectiveAfter":"2026-10-20T14:23:41.417372+00:00","canaryJobId":"526d7a2a007c1fed4b2a9147f92d62b4","deleteSource":false};
  config.executionTriggerUid = e && e.triggerUid ? String(e.triggerUid) : null;
  config.workerSha256 = hash;
  return new Function('Drive', 'DriveApp', 'LockService', 'PropertiesService', 'Utilities', 'console', 'cfg',
    codigo + '\nreturn mgsArchiveWorkerTick(cfg);')
    (Drive, DriveApp, LockService, PropertiesService, Utilities, console, config);
}

function mgsArquivoAtivar() {
  var resultado = mgsArquivoTeste();
  if (resultado.status !== 'ok' || resultado.canaryAcknowledged !== true) {
    throw new Error('AGUARDANDO_CONFERENCIA_DA_CONTA_DE_SERVICO');
  }
  var existentes = ScriptApp.getProjectTriggers().filter(function(t) {
    return t.getHandlerFunction() === 'mgsArquivoTeste';
  });
  if (existentes.length > 1) throw new Error('AGENDAMENTO_DUPLICADO');
  if (!existentes.length) {
    ScriptApp.newTrigger('mgsArquivoTeste').timeBased().everyMinutes(5).create();
  }
  console.log(JSON.stringify({status:'agendamento_ativo', intervaloMinutos:5, exclusaoAtiva:false}));
}
