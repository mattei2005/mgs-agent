import {createHash} from 'node:crypto';
import {periodInfo} from './periods.mjs';
const fail=(message,status=400)=>{throw Object.assign(Error(message),{status});};
const iso=v=>v instanceof Date?v.toISOString():v;
// Fingerprint is a concurrency version, not authorization. Scope and role are checked separately.
export function ledgerVersion(row){return createHash('sha256').update(JSON.stringify(['id','counterparty','period','effective_date','kind','amount_cents','direction','description','actor','created_at','voided_at','voided_by'].map(k=>k==='effective_date'?String(iso(row[k])).slice(0,10):['amount_cents','direction'].includes(k)?Number(row[k]):iso(row[k])??null))).digest('hex');}
export function validateLedgerChange(row,b,action,currentDate){
 if(!row||row.voided_at)fail('Lançamento excluído ou indisponível; atualize a lista',409);
 periodInfo(row.period);if(row.period<'2026-08')fail('Histórico fechado: alteração indisponível',409);
 if(b.period!==row.period||b.counterparty!==row.counterparty)fail('Beneficiário ou competência incompatível',409);
 if(b.version!==ledgerVersion(row))fail('Lançamento alterado; atualize a lista antes de continuar',409);
 if(b.confirmed!==true)fail('Confirme a alteração deste lançamento');
 const allowed=['period','counterparty','version','confirmed',...(action==='edit'?['kind','direction','amount','date','description']:[])];
 if(!['edit','delete'].includes(action)||Object.keys(b).some(k=>!allowed.includes(k)))fail('Campos da alteração inválidos');
 if(action==='delete')return {};
 if(!['adjustment','payment'].includes(b.kind)||![1,-1].includes(b.direction)||b.kind==='payment'&&b.direction!==-1)fail('Natureza do lançamento inválida');
 if(typeof b.amount!=='string'||!/^\d{1,10}(?:\.\d{1,2})?$/.test(b.amount))fail('Valor positivo, com no máximo 2 casas');
 const [whole,decimal='']=b.amount.split('.'),amount=BigInt(whole)*100n+BigInt(decimal.padEnd(2,'0'));
 if(amount<=0n||amount>100000000000n)fail('Valor fora do limite');
 if(typeof b.date!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(b.date)||!Number.isFinite(Date.parse(b.date))||new Date(b.date).toISOString().slice(0,10)!==b.date||b.date>currentDate)fail('Informe uma data real, não futura');
 if(typeof b.description!=='string'||!b.description.trim()||b.description.length>300||/[\x00-\x1f\x7f]/.test(b.description))fail('Descrição inválida');
 return {kind:b.kind,direction:b.direction,amount_cents:Number(amount),effective_date:b.date,description:b.description.trim()};
}
