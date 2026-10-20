function verificarContaMGS() {
  var dados = Drive.About.get({
    fields: 'user(emailAddress),storageQuota'
  });
  var email = (dados.user || {}).emailAddress;
  if (email !== 'mgsdigitalcorp@gmail.com') {
    throw new Error('CONTA_INCORRETA: use mgsdigitalcorp@gmail.com');
  }
  var quota = dados.storageQuota || {};
  var resultado = {
    conta: email,
    limiteBytes: quota.limit || null,
    usadoBytes: quota.usage || null,
    usadoDriveBytes: quota.usageInDrive || null,
    lixeiraDriveBytes: quota.usageInDriveTrash || null
  };
  console.log(JSON.stringify(resultado));
  return resultado;
}
