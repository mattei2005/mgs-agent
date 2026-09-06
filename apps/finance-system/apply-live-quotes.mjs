import {openDatabase} from './storage.mjs';
import {refreshQuotes} from './workspace.mjs';
const db=await openDatabase();
try{console.log(JSON.stringify(await refreshQuotes(db)));}finally{await db.close();}
