(() => {
  const KEY = 'mira_voice_enabled';
  let enabled = localStorage.getItem(KEY) === 'true';
  let audio = null;
  let timer = null;
  let lastSpoken = '';
  let provider = 'edge-tts';

  const particleStyle = document.createElement('style');
  particleStyle.textContent = `
    /* FINAL NRJ CORE PALETTE: ZERO YELLOW/GOLD */
    .grid{background-image:linear-gradient(rgba(50,215,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(50,215,255,.035) 1px,transparent 1px)!important}
    .mini-orb{border-color:rgba(50,215,255,.55)!important;color:#b9f5ff!important;box-shadow:0 0 24px rgba(50,215,255,.12),inset 0 0 18px rgba(50,215,255,.06)!important}
    .hud-btn:hover{border-color:rgba(50,215,255,.35)!important}
    .reactor:before{background:radial-gradient(circle,rgba(50,215,255,.10),rgba(63,140,255,.025) 38%,transparent 68%)!important}
    .reactor:after{border-color:rgba(50,215,255,.14)!important;box-shadow:0 0 60px rgba(50,215,255,.05),inset 0 0 45px rgba(50,215,255,.035)!important}
    .ring{border-color:rgba(50,215,255,.22)!important}
    .ring.r1{border-left-color:rgba(50,215,255,.65)!important;border-right-color:transparent!important}
    .ring.r2{border-top-color:rgba(63,140,255,.42)!important;border-bottom-color:transparent!important}
    .ring.r3{border-color:rgba(139,108,255,.22)!important}
    .core-label{color:#b9f5ff!important;text-shadow:0 0 18px rgba(50,215,255,.55)!important}
    .msg.user .bubble{border-color:rgba(50,215,255,.12)!important}
    .msg.assistant .bubble{color:#a9eaff!important;border-color:rgba(50,215,255,.16)!important}
    .box{border-color:rgba(50,215,255,.25)!important;box-shadow:0 0 35px rgba(0,0,0,.55),0 0 30px rgba(50,215,255,.035)!important}
    .box:focus-within{border-color:rgba(50,215,255,.58)!important;box-shadow:0 0 0 1px rgba(50,215,255,.07),0 0 40px rgba(50,215,255,.07)!important}
    .round:hover{border-color:rgba(50,215,255,.4)!important}
    .send{background:linear-gradient(145deg,#78e9ff,#2688e8)!important;color:#041016!important}
    .line{background:linear-gradient(90deg,rgba(50,215,255,.28),transparent)!important}
    .right .line{background:linear-gradient(270deg,rgba(50,215,255,.28),transparent)!important}
    .toast{border-color:rgba(50,215,255,.24)!important}
    .core{background:transparent!important;box-shadow:none!important;filter:none!important;overflow:visible!important;width:430px!important;height:430px!important;margin-bottom:6px!important}
    .core:before,.core:after,.core-text{display:none!important;content:none!important}
    .mira-particle-field{position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}
    .mira-core-canvas{position:absolute;left:50%;top:50%;width:430px;height:430px;transform:translate(-50%,-50%);pointer-events:none;overflow:visible;z-index:2}
    .readout{margin-top:18px!important}.reactor{margin-top:14px!important;transform:translateY(8px)}
    .substate{color:#506472!important}.state{color:#6e9eb5!important}.metric{color:#526773!important}.metric b{color:#8fb9c9!important}.side-info{color:#506472!important}.side-info b{color:#82b8ce!important}.brand small{color:#557487!important}
    .composer{bottom:31px!important}.composer > div:last-child{color:#64818e!important;font-size:8px!important;letter-spacing:3px!important;margin-top:8px!important}
    @media(max-width:720px){.core{width:300px!important;height:300px!important}.mira-core-canvas{width:300px!important;height:300px!important}.reactor{transform:translateY(3px)}.composer{bottom:21px!important}.composer > div:last-child{font-size:7px!important;letter-spacing:2px!important}}
  `;
  document.head.appendChild(particleStyle);

  const canvas = document.createElement('canvas');
  canvas.className = 'mira-particle-field';
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d', { alpha: true });
  const mouse = { x: -9999, y: -9999, px: -9999, py: -9999, vx: 0, vy: 0, active: false };
  let particles = [], coreCanvas = null, coreCtx = null, coreParticles = [];

  function resizeParticles() {
    const dpr=Math.min(window.devicePixelRatio||1,2);canvas.width=innerWidth*dpr;canvas.height=innerHeight*dpr;canvas.style.width=innerWidth+'px';canvas.style.height=innerHeight+'px';ctx.setTransform(dpr,0,0,dpr,0,0);
    const count=Math.min(145,Math.max(70,Math.floor(innerWidth*innerHeight/14500)));
    if(particles.length!==count)particles=Array.from({length:count},()=>({x:Math.random()*innerWidth,y:Math.random()*innerHeight,vx:(Math.random()-.5)*.105,vy:(Math.random()-.5)*.105,r:1.5+Math.random()*1.8,a:.20+Math.random()*.38,seed:Math.random()*Math.PI*2}));
  }
  function ensureCore(){const core=document.querySelector('.core');if(!core)return null;if(!coreCanvas){coreCanvas=document.createElement('canvas');coreCanvas.className='mira-core-canvas';core.appendChild(coreCanvas);coreCtx=coreCanvas.getContext('2d',{alpha:true});const dpr=Math.min(devicePixelRatio||1,2);coreCanvas.width=430*dpr;coreCanvas.height=430*dpr;coreCtx.setTransform(dpr,0,0,dpr,0,0);coreParticles=Array.from({length:420},()=>{const theta=Math.random()*Math.PI*2,phi=Math.acos(2*Math.random()-1),radius=Math.pow(Math.random(),.62)*185;return{theta,phi,radius,x:Math.sin(phi)*Math.cos(theta)*radius,y:Math.cos(phi)*radius*.92,z:Math.sin(phi)*Math.sin(theta)*radius,vx:0,vy:0,vz:0,phase:Math.random()*Math.PI*2,size:.65+Math.random()*1.9,alpha:.38+Math.random()*.55}})}return core}
  function drawCore(t){const core=ensureCore();if(!core||!coreCanvas||!coreCtx)return;const rect=coreCanvas.getBoundingClientRect(),w=rect.width,h=rect.height,dpr=Math.min(devicePixelRatio||1,2);if(coreCanvas.width!==Math.round(w*dpr)||coreCanvas.height!==Math.round(h*dpr)){coreCanvas.width=Math.round(w*dpr);coreCanvas.height=Math.round(h*dpr);coreCtx.setTransform(dpr,0,0,dpr,0,0)}coreCtx.clearRect(0,0,w,h);const cx=w/2,cy=h/2,rotY=t*.00008,rotX=Math.sin(t*.00012)*.055;const glow=coreCtx.createRadialGradient(cx,cy,8,cx,cy,w*.43);glow.addColorStop(0,'rgba(40,215,255,.12)');glow.addColorStop(.28,'rgba(25,150,255,.045)');glow.addColorStop(.62,'rgba(120,70,255,.025)');glow.addColorStop(1,'rgba(0,0,0,0)');coreCtx.fillStyle=glow;coreCtx.fillRect(0,0,w,h);const projected=[];for(const p of coreParticles){const wave=Math.sin(t*.00038+p.phase)*2.1;let x=p.x+Math.cos(p.phase+t*.00015)*wave,y=p.y+Math.sin(p.phase+t*.00013)*wave,z=p.z;const dx=rect.left+cx+x-mouse.x,dy=rect.top+cy+y-mouse.y,d=Math.hypot(dx,dy)||1;if(mouse.active&&d<180){const force=Math.pow(1-d/180,1.55)*9.5;p.vx+=(dx/d)*force*.18;p.vy+=(dy/d)*force*.18;p.vz+=force*.12}p.vx*=.90;p.vy*=.90;p.vz*=.90;p.x+=p.vx;p.y+=p.vy;p.z+=p.vz;p.x+=(Math.sin(p.phase+t*.00018)*185-p.x)*.00055;p.y+=(Math.cos(p.phase+t*.00016)*185-p.y)*.00032;p.z+=(Math.sin(p.phase*1.7+t*.00014)*185-p.z)*.00038;const xx=x*Math.cos(rotY)-z*Math.sin(rotY),zz=x*Math.sin(rotY)+z*Math.cos(rotY),yy=y*Math.cos(rotX)-zz*Math.sin(rotX),z2=y*Math.sin(rotX)+zz*Math.cos(rotX),scale=390/(390-z2);projected.push({x:cx+xx*scale,y:cy+yy*scale,z:z2,s:p.size*scale,a:p.alpha})}projected.sort((a,b)=>a.z-b.z);for(const p of projected){if(p.x<-30||p.x>w+30||p.y<-30||p.y>h+30)continue;const near=Math.max(0,(p.z+185)/370),alpha=p.a*(.42+near*.62);coreCtx.beginPath();coreCtx.arc(p.x,p.y,Math.max(.55,p.s),0,Math.PI*2);coreCtx.fillStyle=`rgba(90,220,255,${alpha})`;coreCtx.shadowBlur=7;coreCtx.shadowColor=`rgba(50,205,255,${alpha*.75})`;coreCtx.fill();coreCtx.shadowBlur=0}coreCtx.globalCompositeOperation='lighter';for(let k=0;k<7;k++){const rr=118+k*17,phase=t*.00018*(k%2?-1:1)+k*1.7;coreCtx.beginPath();for(let j=0;j<=90;j++){const a=phase+j/90*Math.PI*2,wobble=Math.sin(a*3+k)*5,x=cx+Math.cos(a)*(rr+wobble),y=cy+Math.sin(a)*(rr*.55+wobble*.35);j?coreCtx.lineTo(x,y):coreCtx.moveTo(x,y)}coreCtx.strokeStyle=k%3===0?'rgba(40,160,255,.18)':'rgba(120,75,255,.12)';coreCtx.lineWidth=1;coreCtx.stroke()}coreCtx.globalCompositeOperation='source-over'}
  function animateParticles(t){const w=innerWidth,h=innerHeight;ctx.clearRect(0,0,w,h);for(const p of particles){p.x+=p.vx+Math.sin(t*.00015+p.seed)*.018;p.y+=p.vy+Math.cos(t*.00013+p.seed)*.018;if(p.x<-10)p.x=w+10;if(p.x>w+10)p.x=-10;if(p.y<-10)p.y=h+10;if(p.y>h+10)p.y=-10;if(mouse.active){const dx=p.x-mouse.x,dy=p.y-mouse.y,d=Math.hypot(dx,dy)||1,radius=Math.max(w,h)*.42;if(d<radius){const proximity=1-d/radius,force=Math.pow(proximity,1.65)*1.8;p.vx+=(dx/d)*force*.018;p.vy+=(dy/d)*force*.018;p.vx+=mouse.vx*proximity*.035;p.vy+=mouse.vy*proximity*.035}}p.vx*=.994;p.vy*=.994;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fillStyle=`rgba(55,205,255,${p.a})`;ctx.fill()}drawCore(t);mouse.vx*=.82;mouse.vy*=.82;requestAnimationFrame(animateParticles)}
  addEventListener('pointermove',e=>{if(mouse.px>-9000){mouse.vx=Math.max(-28,Math.min(28,e.clientX-mouse.px));mouse.vy=Math.max(-28,Math.min(28,e.clientY-mouse.py))}mouse.px=e.clientX;mouse.py=e.clientY;mouse.x=e.clientX;mouse.y=e.clientY;mouse.active=true},{passive:true});addEventListener('pointerleave',()=>{mouse.active=false;mouse.vx=0;mouse.vy=0;mouse.px=-9999;mouse.py=-9999});addEventListener('resize',resizeParticles);resizeParticles();requestAnimationFrame(animateParticles);

  const style=document.createElement('style');style.textContent=`.mira-voice-bar{position:fixed;right:20px;bottom:92px;z-index:20;display:flex;gap:7px;align-items:center;background:#11151ddd;border:1px solid #303d4a;border-radius:14px;padding:6px;backdrop-filter:blur(16px);box-shadow:0 12px 40px #0008}.mira-voice-btn{border:0;border-radius:10px;padding:8px 11px;background:#18232c;color:#e8f8ff;cursor:pointer;font:12px Inter,system-ui,sans-serif}.mira-voice-btn.on{background:#32cfff;color:#041016;font-weight:800}.mira-voice-btn.stop{display:none}`;document.head.appendChild(style);
  const bar=document.createElement('div');bar.className='mira-voice-bar';bar.innerHTML='<button class="mira-voice-btn toggle"></button><button class="mira-voice-btn stop">■ Stop</button>';document.body.appendChild(bar);const toggle=bar.querySelector('.toggle'),stop=bar.querySelector('.stop');
  function render(){toggle.textContent=enabled?'🔊 Voice ON':'🔇 Voice OFF';toggle.classList.toggle('on',enabled);stop.style.display=audio?'block':'none'}
  async function status(){try{const r=await fetch('/api/voice/status');const d=await r.json();provider=d.provider||'edge-tts';toggle.title=provider==='edge-tts'?`Free neural Hindi female voice • ${d.voice||'Ananya'}`:'Voice unavailable'}catch(_){provider='edge-tts'}}
  function browserSpeak(text){if(!('speechSynthesis'in window))return;speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.lang=/[\u0900-\u097F]/.test(text)?'hi-IN':'en-IN';u.rate=.94;u.pitch=1.02;u.onstart=render;u.onend=render;speechSynthesis.speak(u)}
  async function serverSpeak(text){if(audio){audio.pause();audio=null}const r=await fetch('/api/voice/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});if(!r.ok)throw new Error('Server voice unavailable');const blob=await r.blob(),url=URL.createObjectURL(blob);audio=new Audio(url);audio.onended=()=>{URL.revokeObjectURL(url);audio=null;render()};audio.onerror=()=>{URL.revokeObjectURL(url);audio=null;render()};render();await audio.play()}
  async function speak(text){if(!enabled||!text||text===lastSpoken)return;lastSpoken=text;try{await serverSpeak(text)}catch(_){browserSpeak(text)}}
  toggle.onclick=()=>{enabled=!enabled;localStorage.setItem(KEY,String(enabled));if(!enabled){if(audio){audio.pause();audio=null}if('speechSynthesis'in window)speechSynthesis.cancel()}render()};stop.onclick=()=>{if(audio){audio.pause();audio.currentTime=0;audio=null}if('speechSynthesis'in window)speechSynthesis.cancel();render()};
  const chat=document.getElementById('chat'),model=document.getElementById('model');if(chat){const observer=new MutationObserver(()=>{clearTimeout(timer);if(!enabled)return;timer=setTimeout(()=>{if(model&&/generating|listening/i.test(model.textContent||''))return;const bubbles=chat.querySelectorAll('.assistant .bubble'),last=bubbles[bubbles.length-1];if(last&&last.textContent.trim())speak(last.textContent.trim())},850)});observer.observe(chat,{subtree:true,childList:true,characterData:true})}status();render();
})();