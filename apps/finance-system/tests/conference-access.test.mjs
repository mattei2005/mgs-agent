import test from 'node:test';
import assert from 'node:assert/strict';
import {installMonthlyReview} from '../monthly-review-routes.mjs';
test('only exact Rodolfo and Geizian can consult conference; technical APIs remain Rodolfo-only',async()=>{
 const routes=[];await installMonthlyReview({get:(paths,...handlers)=>{for(const path of Array.isArray(paths)?paths:[paths])routes.push({path,guard:handlers[0]});}},{production:true});
 assert.equal(routes.length,8);
 const shared=new Set(['/review.html','/review.js','/review.css','/api/monthly-conference']);
 for(const route of routes){
  for(const auth of [undefined,{role:'owner'},{username:'another-owner',role:'owner'},{username:'other-partner',role:'partner'},{username:'geizian',role:'owner'},{username:'geizian',role:'manager'},{username:'Geizian',role:'partner'},{username:'nicolas',role:'manager'},{username:'rodolfo',role:'manager'},{username:'Rodolfo',role:'owner'}]){
   let status=null,next=false;route.guard({auth},{status(n){status=n;return this;},json(){}},()=>next=true);assert.equal(next,false,route.path+' must deny '+JSON.stringify(auth));assert.equal(status,403);
  }
  let allowed=false;route.guard({auth:{username:'rodolfo',role:'owner'}},{status(){throw Error('Rodolfo denied');}},()=>allowed=true);assert.equal(allowed,true);
  let status=null,geizian=false;route.guard({auth:{username:'geizian',role:'partner'}},{status(n){status=n;return this;},json(){}},()=>geizian=true);assert.equal(geizian,shared.has(route.path),route.path);if(!geizian)assert.equal(status,403);
 }
});
