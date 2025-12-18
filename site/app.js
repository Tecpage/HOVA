const views=[
  {id:'start',title:'Start',file:null,badge:'Home'},
  {id:'nova',title:'nova.yaml',file:'./nova.yaml',badge:'SSOT'},
  {id:'changelog',title:'CHANGELOG.md',file:'./CHANGELOG.md',badge:'Trace'}
];
const nav=document.querySelector('#nav'), title=document.querySelector('#viewTitle'), body=document.querySelector('#viewBody'), search=document.querySelector('#search');

function setActive(id){document.querySelectorAll('.it').forEach(a=>a.classList.remove('active')); const el=document.querySelector(`.it[data-id="${id}"]`); if(el) el.classList.add('active');}

async function loadView(id){
  const v=views.find(x=>x.id===id)||views[0];
  setActive(v.id); title.textContent=v.title;
  if(!v.file){
    body.textContent=[
      'HOVA Viewer (Chrome Installable App)',
      '',
      '• ChatGPT-ähnliches Layout (Sidebar + Content)',
      '• Holiday-Inn-Grün als Akzent',
      '• Fingerprint Watermark',
      '',
      'Tipp: In Chrome -> "Installieren" (PWA)'
    ].join('\n');
    return;
  }
  const r=await fetch(v.file,{cache:'no-store'});
  body.textContent=await r.text();
}

function renderNav(filter=''){
  nav.innerHTML='';
  const f=filter.trim().toLowerCase();
  views.filter(v=>!f||v.title.toLowerCase().includes(f)).forEach(v=>{
    const a=document.createElement('a');
    a.href='#'+v.id; a.className='it'; a.dataset.id=v.id;
    a.innerHTML=`<span>${v.title}</span><span class="badge">${v.badge}</span>`;
    a.addEventListener('click',(e)=>{e.preventDefault();location.hash=v.id;});
    nav.appendChild(a);
  });
}
search.addEventListener('input',()=>renderNav(search.value));
window.addEventListener('hashchange',()=>loadView((location.hash||'#start').replace('#','')));
renderNav(); loadView((location.hash||'#start').replace('#',''));

if('serviceWorker' in navigator){navigator.serviceWorker.register('./sw.js').catch(()=>{});}
