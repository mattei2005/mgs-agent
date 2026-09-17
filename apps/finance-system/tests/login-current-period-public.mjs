import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';

const base='https://dash.mgsdigitalcorp.com';
const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);
const credential=JSON.parse(Buffer.concat(chunks).toString());
let browser;
try{
 browser=await chromium.launch({headless:true,executablePath:chromium.executablePath(),args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:900},locale:'pt-BR',timezoneId:'America/New_York'}),page=await context.newPage(),errors=[];
 page.on('pageerror',error=>errors.push(error.message));page.setDefaultTimeout(30000);
 await page.goto(base+'/login');
 await page.evaluate(()=>sessionStorage.setItem('financePeriod','2026-08'));
 await page.locator('#username').fill(credential.username);
 await page.locator('#password').fill(credential.password);
 await page.locator('#submitButton').click();
 if(await page.locator('#mfaPanel').isVisible()){
  await page.locator('#otp').fill(credential.otp);
  await page.locator('#submitButton').click();
 }
 await page.waitForURL(url=>url.pathname==='/'&&url.searchParams.get('period')===credential.expected_period);
 await page.waitForSelector('.cards');
 assert.equal(await page.locator('#period').inputValue(),credential.expected_period);
 assert.equal(await page.evaluate(()=>sessionStorage.getItem('financePeriod')),credential.expected_period);
 assert.equal(await page.locator('#title').innerText(),'Dashboard');
 assert.equal(errors.length,0);
 await page.locator('#logout').click();await page.waitForURL('**/login');
 console.log(JSON.stringify({pass:true,period:credential.expected_period,home:'Dashboard',stale_period_replaced:true,js_errors:0,logout:true}));
}catch(error){console.log(JSON.stringify({pass:false,error_type:error.name,message:String(error.message).slice(0,300)}));process.exitCode=1;}finally{await browser?.close();}
