const fs=require("fs"),path=require("path");const DIR=process.env.REAL_DATA_DIR;
const R=require(require("path").join(__dirname,"..","..","frontend","engine.js")),L=require(require("path").join(__dirname,"..","..","frontend","dataloader.js"));
const fetchFn=async(u)=>{const p=path.join(DIR,u.replace(/^data\//,""));if(!fs.existsSync(p))return{ok:false,status:404,arrayBuffer:async()=>new ArrayBuffer(0)};const b=fs.readFileSync(p);return{ok:true,status:200,arrayBuffer:async()=>b.buffer.slice(b.byteOffset,b.byteOffset+b.length)}};
(async()=>{const out={};for(const [k,o] of Object.entries({A:{homeUniversity:"Savitribai Phule Pune University",gender:"Male",category:"OPEN"},B:{homeUniversity:"Mumbai University",gender:"Female",category:"OBC"}})){
const r=await L.recommend(Object.assign({percentile:92,admissionYear:"auto",candidateType:"Maharashtra State candidate",extraEligibility:[],branches:["Computer Engineering"],districts:["ANY"],maxAnnualFeeINR:1000000,feeBasis:"total",priorities:["admission_chance"]},o),{baseUrl:"data/",fetchFn,Recommender:R,engineOptions:{asOfDate:"2026-11-10",maxResults:400}});
out[k]={student:o,res:r.results.map(x=>({cc:x.choiceCode,rounds:x.currentRounds,cur:x.currentCutoff}))};}
fs.writeFileSync(process.env.DUMP_OUT,JSON.stringify(out));})();
