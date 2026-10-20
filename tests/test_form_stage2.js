const {JSDOM}=require("jsdom");const fs=require("fs");
const d="../frontend/";
let html=fs.readFileSync(d+"index.html","utf8").replace(/<script src="[^"]+"><\/script>/g,"");
const dom=new JSDOM(html,{runScripts:"outside-only"});
const w=dom.window;w.eval(fs.readFileSync(d+"config.js","utf8"));w.eval(fs.readFileSync(d+"app.js","utf8"));
const $=id=>w.document.getElementById(id);
w.HTMLElement.prototype.scrollIntoView=function(){};
let pass=0,fail=0;const t=(n,c)=>{c?pass++:fail++;console.log((c?"PASS ":"FAIL ")+n)};
const submit=()=>$("form").dispatchEvent(new w.Event("submit",{cancelable:true,bubbles:true}));
// empty
submit();t("empty form blocked",$("results").hidden&&$("percentile-err").textContent!=="");
// invalid percentile
$("percentile").value="101";submit();t("101 rejected",$("percentile-err").textContent!=="");
$("percentile").value="92.45678912";submit();t("8 decimals rejected",$("percentile-err").textContent!=="");
// fill valid
$("percentile").value="92.4567891";$("candidateType").value=w.APP_CONFIG.candidateTypes[0];$("category").value="Open";
const b=$("branches").querySelectorAll("select");b[0].value=w.APP_CONFIG.branches[0];b[1].value=w.APP_CONFIG.branches[0];
$("maxFee").value="1,50,000";
const ds=$("districts").querySelectorAll("select");ds[0].value="Pune";
submit();t("duplicate branch rejected",$("branches-err").textContent!=="");
b[1].value=w.APP_CONFIG.branches[2];submit();
t("valid form accepted",!$("results").hidden);
const p=JSON.parse($("payload").textContent);console.log(p);
t("fee parsed",p.maxAnnualFeeINR===150000);t("2 branches",p.branches.length===2);t("balanced default",p.priorities[0]==="balanced");
// any district
$("anyDistrict").checked=true;$("anyDistrict").dispatchEvent(new w.Event("change"));ds[0].value="";submit();
t("any district",JSON.parse($("payload").textContent).districts[0]==="ANY");
// priority exclusivity
const pb=w.document.querySelector("input[name=priorities]");pb.checked=true;pb.dispatchEvent(new w.Event("change"));
t("balanced unticked when priority chosen",!$("balanced").checked);
console.log(pass+" passed, "+fail+" failed");
