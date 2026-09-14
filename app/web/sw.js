const CACHE='mira-shell-v2';
const SHELL=['/','/manifest.json'];
const PC='http://127.0.0.1:8765/command';
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
function pcCommand(message){const m=message.toLowerCase();let target=null;if(/youtube|you tube/.test(m))target='youtube';else if(/google/.test(m))target='google';else if(/gmail/.test(m))target='gmail';else if(/notepad|notes/.test(m))target='notepad';else if(/calculator|calc|calculate/.test(m))target='calculator';if(!target)return null;const app=ALLOWED_APP(target);return fetch(PC,{method:'POST',headers:{'Content-Type':'text/plain'},body:JSON.stringify({token:'mira-local',action:app?'open_app':'open_website',target})}).then(r=>r.json()).then(x=>x.message||'Command completed.');}
function ALLOWED_APP(t){return t==='notepad'||t==='calculator'}
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(url.pathname==='/api/chat/stream'&&event.request.method==='POST'){
    event.respondWith((async()=>{try{const copy=event.request.clone();const data=await copy.json();const text=String(data.message||'');const result=await pcCommand(text);if(result){const reply=result+' Boss.';return new Response(JSON.stringify({delta:reply})+'\n',{headers:{'Content-Type':'application/x-ndjson'}})}}catch(e){}return fetch(event.request)})());return;
  }
  if(url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;
  event.respondWith(fetch(event.request).then(response=>{const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));return response}).catch(()=>caches.match(event.request).then(cached=>cached||caches.match('/'))));
});
