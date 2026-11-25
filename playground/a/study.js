'use strict';
const $ = id => document.getElementById(id);
const samples = {ru:'мама ела ананас · Ева написала', en:'area · sea · an apple a day'};
const controls = [
  ['width','Ширина',100,175,.5,107,'%', 'axes'],
  ['weight','Вес',100,900,1,650,'','axes'],
  ['height','Высота',-16,16,1,0,'ед.','tuning'],
  ['thickness','Толщина',85,115,1,110,'%','tuning']
];
const defaults = {lang:'ru',guide:true,ghost:false,detail:false,phrase:samples.ru};
for (const [key,,,,,value] of controls) defaults[key]=value;
const store = 'sp-v4-a-study';
const query = new URLSearchParams(location.search);
let input = {};
try { input=JSON.parse(localStorage.getItem(store)) || {}; } catch {}
if (query.has('width')) input=Object.fromEntries(query);
let state = {...defaults};
for(const [key,,min,max,step] of controls) {
  const v=Number(input[key]);
  if(Number.isFinite(v) && v>=min && v<=max) state[key]=Math.round(v/step)*step;
}
if (input.lang==='en') state.lang='en';
state.phrase=typeof input.phrase==='string'?input.phrase.slice(0,180):samples[state.lang];
for(const key of ['guide','ghost','detail']) if(key in input) state[key]=input[key]===true || input[key]==='true';
const numeric=new Map();
for(const [key,label,min,max,step,,unit,section] of controls){
  const row=document.createElement('div');
  row.innerHTML='<label></label><input type="range"><div class="value"><input type="number"><span></span></div>';
  const [range,field]=row.querySelectorAll('input');
  for(const el of [range,field]){el.min=min;el.max=max;el.step=step;el.setAttribute('aria-label',label+(el===range?' — ползунок':' — значение'));}
  range.id=key;
  row.querySelector('label').htmlFor=key;
  row.querySelector('label').textContent=label;
  row.querySelector('span').textContent=unit;
  for(const el of [range,field]) el.oninput=()=>{
    if(el.value!=='' && el.validity.valid){state[key]=el.valueAsNumber;render();save();}
  };
  field.onblur=()=>{field.value=state[key];};
  numeric.set(key,[range,field]);$(section).append(row);
}
const texts=[];
for(const [variant,title] of [['before','До'],['after','После']]){
  const card=$('sample').content.firstElementChild.cloneNode(true);card.className=variant;card.querySelector('h2').textContent=title;
  card.querySelector('svg').setAttribute('aria-label',title+' — пара букв');$('specimens').append(card);
  const panel=document.createElement('div');panel.innerHTML='<h3></h3><p></p>';panel.querySelector('h3').textContent=title;
  const p=panel.querySelector('p');p.className=variant+' context';texts.push(p);$('contexts').append(panel);
}
function save(){
  try {localStorage.setItem(store,JSON.stringify(state));} catch {}
  if(location.search) history.replaceState(null,'',location.pathname);
}
function render(){
  const settings='"wght" '+state.weight+', "wdth" '+state.width+', "opsz" 48';
  const root=document.documentElement;
  root.style.setProperty('--before',settings);
  root.style.setProperty('--after',settings+', "ABHT" '+state.height+', "ABWT" '+state.thickness);
  root.classList.toggle('ghost-on',state.ghost);root.classList.toggle('hide-guides',!state.guide);
  for(const [key,els] of numeric) for(const el of els) if(el.valueAsNumber!==state[key])el.value=state[key];
  for(const lang of ['ru','en']) $(lang).setAttribute('aria-pressed',lang===state.lang);
  for(const key of ['guide','ghost','detail']) $(key).checked=state[key];
  $('guide').disabled=state.detail;
  for(const svg of document.querySelectorAll('.pair svg')){
    svg.setAttribute('viewBox',state.detail?'0 0 98 34':'0 0 510 178');
    svg.setAttribute('aria-label',svg.closest('article').querySelector('h2').textContent+
      (state.detail?' — нижний стык чаши и стойки':' — пара букв'));
    for(const t of svg.querySelectorAll('text')){
      const pair=state.lang==='ru'?'ае':'ae';
      t.textContent=state.detail?pair[0]:pair;
      t.setAttribute('text-anchor',state.detail?'end':'start');
      t.setAttribute('x',state.detail?'93':'24');
      t.setAttribute('y',state.detail?'29':'148');
    }
  }
  if($('phrase').value!==state.phrase) $('phrase').value=state.phrase;
  for(const p of texts)p.textContent=state.phrase;
}
for(const lang of ['ru','en']) $(lang).onclick=()=>{
  if(state.phrase===samples[state.lang])state.phrase=samples[lang];
  state.lang=lang;render();save();
};
for(const key of ['guide','ghost','detail'])$(key).onchange=()=>{state[key]=$(key).checked;render();save();};
$('phrase').oninput=()=>{state.phrase=$('phrase').value;render();save();};
$('reset').onclick=()=>{state={...defaults};render();save();$('status').textContent='Восстановлен предложенный вариант.';};
$('copy').onclick=async()=>{
  const url=new URL(location.href);url.search=new URLSearchParams(state);
  try{await navigator.clipboard.writeText(url.href);$('status').textContent='Ссылка на этот вариант скопирована.';}
  catch{history.replaceState(null,'',url);$('status').textContent='Скопируй ссылку из адресной строки.';}
};
$('export').onclick=async()=>{
  const height=state.height,thickness=state.thickness;
  $('export').disabled=true;$('status').textContent='Собираю TTF…';
  try{
    const res=await fetch('/api/a-font',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({height,thickness})});
    if(!res.ok)throw Error();
    const url=URL.createObjectURL(await res.blob());
    const a=document.createElement('a');a.href=url;a.download='SP-v4-A-h'+height+'-t'+thickness+'.ttf';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),2000);$('status').textContent='TTF собран с выбранной перекладиной.';
  }catch{$('status').textContent='Не удалось собрать TTF. Открой страницу через локальный сервер лаборатории.';}
  finally{$('export').disabled=false;}
};
render();
Promise.all(['Before','After'].map(f=>document.fonts.load('40px '+f,'аеae'))).catch(()=>{$('status').textContent='Шрифт не загрузился. Обнови страницу.';});
