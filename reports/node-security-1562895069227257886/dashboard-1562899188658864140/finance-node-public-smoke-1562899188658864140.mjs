import assert from 'node:assert/strict';
import {chromium} from '/root/mgs-agent/apps/finance-system/node_modules/@playwright/test/index.mjs';
const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
const checks=[];
try {
  for (const viewport of [{width:1440,height:1000},{width:390,height:844}]) {
    const context=await browser.newContext({viewport});
    const page=await context.newPage();
    const errors=[];
    page.on('pageerror', error=>errors.push(error.name));
    const response=await page.goto('https://dash.mgsdigitalcorp.com/',{waitUntil:'networkidle',timeout:45000});
    await page.waitForURL('**/login');
    assert.equal(response.status(),200);
    assert.equal(await page.locator('#username').count(),1);
    assert.equal(await page.locator('#password').count(),1);
    assert.ok(await page.locator('button[type=submit]').count()>0);
    assert.equal((await context.request.get('https://dash.mgsdigitalcorp.com/api/scenarios')).status(),401);
    assert.equal(errors.length,0);
    const fits=await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2);
    assert.ok(fits);
    checks.push({viewport,login_rendered:true,api_auth_preserved:true,js_errors:errors.length,no_horizontal_overflow:fits});
    await context.close();
  }
  console.log(JSON.stringify({pass:true,checks,login_attempts:0,financial_posts:0}));
} finally {await browser.close();}
