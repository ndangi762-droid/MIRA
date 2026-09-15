const CACHE='mira-shell-v4';
const SHELL=['/','/manifest.json','/voice-mobile.js'];
const PC='http://127.0.0.1:8765/command';
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
function pcCommand(message){
  const m=message.toLowerCase().trim();
  let target=null;
  let action='open_website';
  if(/\b(chrome|google chrome)\b.*(khol|open|chala|start)|^(chrome|google chrome)$/.test(m)){target='chrome';action='open_app'}
  else if(/youtube|you tube/.test(m))target='youtube';
  else if(/gmail/.test(m))target='gmail';
  else if(/google.*(khol|open|search)|google par ja/.test(m))target='google';
  else if(/notepad|notes.*(khol|open)|notepad.*(khol|open)/.test(m)){target='notepad';action='open_app'}
  else if(/calculator|calc|calculate|calculator.*(khol|open)/.test(m)){target='calculator';action='open_app'}
  else if(/paint.*(khol|open)|^paint$/.test(m)){target='paint';action='open_app'}
  else if(/file explorer|explorer.*(khol|open)|files.*(khol|open)/.test(m)){target='explorer';action='open_app'}
  else if(/google.*search|search.*google/.test(m)){return fetch(PC,{method:'POST',headers:{'Content-Type':'text/plain'},body:JSON.stringify({token:'mira-local',action:'search_web',target:m.replace(/.*(?:google.*search|search.*google)/,'').trim()})}).then(r=>r.json()).then(x=>x.message||'Search completed.')}
  if(!target)return null;
  return fetch(PC,{method:'POST',headers:{'Content-Type':'text/plain'},body:JSON.stringify({token:'mira-local',action,target})}).then(r=>r.json()).then(x=>x.message||'Command completed.');
}
function injectVoice(response){
  const type=response.headers.get('content-type')||'';
  if(!type.includes('text/html'))return response;
  return response.text().then(html=>{
    if(html.includes('/voice-mobile.js'))return new Response(html,{status:response.status,statusText:response.statusText,headers:response.headers});
    const marker='</body>';const pos=html.toLowerCase().lastIndexOf(marker);
    const injected=pos>=0?html.slice(0,pos)+'<script src="/voice-mobile.js" defer></script>'+html.slice(pos):html+'<script src="/voice-mobile.js" defer></script>';
    const headers=new Headers(response.headers);headers.delete('content-length');
    return new Response(injected,{status:response.status,statusText:response.statusText,headers});
  });
}
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(url.pathname==='/api/chat/stream'&&event.request.method==='POST'){
    event.respondWith((async()=>{try{const copy=event.request.clone();const data=await copy.json();const text=String(data.message||'');const result=await pcCommand(text);if(result){const reply=result+' Boss.';return new Response(JSON.stringify({delta:reply})+'\n',{headers:{'Content-Type':'application/x-ndjson'}})}}catch(e){}return fetch(event.request)})());return;
  }
  if(url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;
  event.respondWith(fetch(event.request).then(response=>{const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));return injectVoice(response)}).catch(()=>caches.match(event.request).then(cached=>cached||caches.match('/'))));
});
