/* Minimal native DOM/MVC doubles: no network, no installed dependencies. */
const assert=require('assert'),fs=require('fs');
const api=require('../netspout/appserver/static/discovery.js');
const data=JSON.parse(fs.readFileSync('netspout/appserver/static/discovery_catalog.json'));
assert(api.filter(data.entries,'BGP',{}).some(r=>r.kind==='scenario'));
assert(api.filter(data.entries,'F5',{}).some(r=>r.kind==='sourcetype'));
assert.strictEqual(api.filter(data.entries,'',{kind:['dashboard']}).length,4);
assert(api.filter(data.entries,'',{industries:['Telecommunications']}).length>=10);
assert(api.filter(data.entries,'',{vendors:['PulseForge'],readiness:['Executable custom simulation']}).length>=25);
assert.strictEqual(api.page(data.entries,0).length,40);
assert.notStrictEqual(api.page(data.entries,0)[0].id,api.page(data.entries,1)[0].id);
assert.throws(()=>api.scope('idx | delete','x'));
assert.throws(()=>api.scope('idx_network_ops','arbitrary-user-id'));
assert.strictEqual(api.assess({fields:['observed_records'],rows:[[0]]},['f']),'MISSING_DATA');
assert.strictEqual(api.assess({fields:['observed_records','present_f'],rows:[[2,1]]},['f']),'MISSING_FIELDS');
assert.strictEqual(api.assess({fields:['observed_records','present_f'],rows:[[2,2]]},['f']),'FIELDS_PRESENT');
assert.strictEqual(api.assess(null,['f']),'INCONCLUSIVE');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.value='';this._text='';}
 set textContent(s){this._text=String(s);this.children=[];}
 get textContent(){return this._text;}
 appendChild(e){this.children.push(e);}
 querySelectorAll(){return [];}
}
const ids={};['pf-discovery','pf-discovery-status','pf-results','pf-detail','pf-search','pf-prev','pf-next','pf-clear','pf-filters'].forEach(id=>ids[id]=new Element('div'));
const walk=e=>[e,...e.children.flatMap(walk)];
let calls=[],searches=[],outcome='complete';
class Search {
 constructor(options){this.options=options;this.handlers={};searches.push(this);}
 on(e,fn){this.handlers[e]=fn;}
 startSearch(){
  if(outcome==='error'){this.handlers['search:error']({});return;}
  this.handlers['search:done']({content:{isDone:outcome==='complete'}});
 }
 data(){return {on:(e,f)=>f(),data:()=>({fields:['observed_records'],rows:[[0]]})};}
 cancel(){this.cancelled=true;}
}
const win={document:{getElementById:id=>ids[id],createElement:tag=>new Element(tag)},location:{pathname:'/en-US/app/netspout/pulseforge_discovery'},
 setTimeout:()=>1,clearTimeout:()=>{},fetch:(url,options)=>{calls.push({url,options});return Promise.resolve({ok:true,json:()=>Promise.resolve(options?{destinations:[{name:'Dummy saved receiver',protocol:'syslog',enabled:true,signals:['logs']}]}:data)});}};
(async()=>{
 api.mount(win,Search);
 for(let i=0;i<8;i++)await Promise.resolve();
 assert.strictEqual(calls.length,2);
 assert(calls[0].url.startsWith('/en-US/static/app/netspout/'));
 assert.strictEqual(JSON.parse(calls[1].options.body).action,'list_destinations');
 assert(ids['pf-results'].children.length<=40);
 ids['pf-search'].value='network_08_firewall_policy';ids['pf-search'].oninput();
 const button=ids['pf-results'].children.find(b=>b.textContent.includes('scenario'));
 assert(button);button.onclick();
 assert(walk(ids['pf-detail']).some(e=>e.textContent.includes('Dummy saved receiver')));
 const dash=walk(ids['pf-detail']).find(e=>e.tag==='button'&&e.textContent.includes('Security incident'));
 assert(dash);dash.onclick();
 const open=walk(ids['pf-detail']).find(e=>e.textContent==='Open Splunk dashboard');
 assert.strictEqual(open.href,'/en-US/app/netspout/pulseforge_security');
 const inputs=walk(ids['pf-detail']).filter(e=>e.tag==='input');
 inputs[1].value='00112233-4455-6677-8899-aabbccddeeff';
 const check=walk(ids['pf-detail']).find(e=>e.textContent.startsWith('Check local data'));
 check.onclick();
 assert(searches[0].options.search.includes('netspout_run_id="00112233-4455-6677-8899-aabbccddeeff"'));
 assert.strictEqual(searches[0].options.earliest_time,'-24h');
 assert(walk(ids['pf-detail']).some(e=>e.textContent.startsWith('MISSING_DATA')));
 outcome='incomplete';check.onclick();
 assert(walk(ids['pf-detail']).some(e=>e.textContent.startsWith('INCONCLUSIVE')));
 outcome='error';check.onclick();
 assert(walk(ids['pf-detail']).some(e=>e.textContent.startsWith('ERROR')));
 assert(!fs.readFileSync('netspout/appserver/static/discovery.js','utf8').includes('innerHTML'));
 console.log('browser assertions passed');
})().catch(e=>{console.error(e);process.exit(1);});
