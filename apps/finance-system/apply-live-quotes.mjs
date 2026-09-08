import {openDatabase} from './storage.mjs';
import {refreshQuotes} from './workspace.mjs';
const db=await openDatabase();
try{console.log(JSON.stringify(await refreshQuotes(db,{period:process.argv[2]||null,actor:process.argv[3]||'Zeus / cotação automática'})));}finally{await db.close();}
