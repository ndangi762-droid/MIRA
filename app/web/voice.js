(() => {
  const KEY = 'mira_voice_enabled';
  let enabled = localStorage.getItem(KEY) === 'true';
  let audio = null;
  let timer = null;
  let lastSpoken = '';
  let provider = 'browser';

  /* MIRA visual core: visible slow particle circle, no solid ring or text. */
  const visualStyle = document.createElement('style');
  visualStyle.textContent = `
    .core{background:transparent!important;box-shadow:none!important;filter:none!important;overflow:visible!important}
    .core:before,.core:after,.core-text{display:none!important;content:none!important}
    .mira-particle-field{position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}
    .mira-core-field{position:absolute;left:50%;top:50%;width:300px;height:300px;transform:translate(-50%,-50%);pointer-events:none;overflow:visible;z-index:4}
    .mira-core-dot{position:absolute;width:4px;height:4px;border-radius:50%;background:#f5c84b;box-shadow:0 0 8px #f5c84b99,0 0 20px #f5c84b55;will-change:transform;transform:translate3d(-50%,-50%,0)}
    .mira-core-dot.white{background:#fff4c5;box-shadow:0 0 7px #fff7d6,0 0 17px #f5c84b66}
    .mira-core-dot.dim{width:2.5px;height:2.5px;opacity:.62}
    @media(max-width:720px){.mira-core-field{width:240px;height:240px}.mira-core-dot{width:3.5px;height:3.5px}}
  `;
  document.head.appendChild(visualStyle);

  const canvas = document.createElement('canvas');
  canvas.className = 'mira-particle-field';
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d', {alpha:true});
  const mouse = {x:-9999,y:-9999,active:false};
  let particles = [];
  let coreParticles = [];
  let coreField = null;

  function resizeParticles(){
    const dpr=Math.min(window.devicePixelRatio||1,2);
    canvas.width=innerWidth*dpr; canvas.height=innerHeight*dpr;
    canvas.style.width=innerWidth+'px'; canvas.style.height=innerHeight+'px';
    ctx.setTransform(dpr,0,0,dpr,0,0);
    const count=Math.min(115,Math.max(55,Math.floor(innerWidth*innerHeight/19000)));
    if(particles.length!==count){
      particles=Array.from({length:count},()=>({
        x:Math.random()*innerWidth,y:Math.random()*innerHeight,
        vx:(Math.random()-.5)*.045,vy:(Math.random()-.5)*.045,
        r:1.7+Math.random()*2.1,a:.16+Math.random()*.28,
        gold:Math.random()<.25,seed:Math.random()*Math.PI*2
      }));
    }
  }

  function circularTargets(count){
    const out=[];
    for(let i=0;i<count;i++){
      const angle=(i/count)*Math.PI*2 + (Math.random()-.5)*.025;
      const radius=38 + Math.random()*9;
      out.push({x:50+Math.cos(angle)*radius,y:50+Math.sin(angle)*radius});
    }
    return out;
  }

  function ensureCore(){
    const core=document.querySelector('.core');
    if(!core) return null;
    if(!coreField){
      coreField=document.createElement('div');
      coreField.className='mira-core-field';
      core.appendChild(coreField);
      const targets=circularTargets(150);
      coreParticles=targets.map((target,i)=>{
        const el=document.createElement('i');
        el.className='mira-core-dot'+(i%7===0?' white':'')+(i%5===0?' dim':'');
        coreField.appendChild(el);
        return {el,tx:target.x,ty:target.y,x:target.x,y:target.y,vx:0,vy:0,phase:Math.random()*Math.PI*2,seed:Math.random()*Math.PI*2};
      });
    }
    return core;
  }

  function animateParticles(t){
    const w=innerWidth,h=innerHeight;
    ctx.clearRect(0,0,w,h);

    // Slow background drift.
    for(const p of particles){
      p.x+=p.vx+Math.sin(t*.00012+p.seed)*.012;
      p.y+=p.vy+Math.cos(t*.00010+p.seed)*.012;
      if(p.x<-10)p.x=w+10;if(p.x>w+10)p.x=-10;
      if(p.y<-10)p.y=h+10;if(p.y>h+10)p.y=-10;
      if(mouse.active){
        const dx=p.x-mouse.x,dy=p.y-mouse.y,d=Math.hypot(dx,dy)||1,radius=150;
        if(d<radius){const f=(1-d/radius)*.7;p.x+=dx/d*f;p.y+=dy/d*f;}
      }
      ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle=p.gold?`rgba(245,200,75,${p.a})`:`rgba(205,215,230,${p.a*.48})`;
      ctx.fill();
    }

    const core=ensureCore();
    if(core&&coreField){
      const rect=coreField.getBoundingClientRect();
      const cx=rect.width/2,cy=rect.height/2;
      for(const p of coreParticles){
        // All particles flow slowly together while maintaining the circular silhouette.
        const baseAngle=Math.atan2(p.ty-50,p.tx-50)+t*.00011;
        const baseRadius=Math.hypot(p.tx-50,p.ty-50)/100*rect.width;
        const targetX=cx+Math.cos(baseAngle)*baseRadius+Math.sin(t*.00035+p.phase)*2.2;
        const targetY=cy+Math.sin(baseAngle)*baseRadius+Math.cos(t*.00031+p.seed)*2.2;
        p.vx+=(targetX-p.x)*.028;p.vy+=(targetY-p.y)*.028;

        const px=rect.left+p.x,py=rect.top+p.y;
        if(mouse.active){
          const dx=px-mouse.x,dy=py-mouse.y,d=Math.hypot(dx,dy)||1,radius=145;
          if(d<radius){
            const f=Math.pow(1-d/radius,1.6)*4.8;
            p.vx+=(dx/d)*f;p.vy+=(dy/d)*f;
          }
        }
        p.vx*=.91;p.vy*=.91;p.x+=p.vx;p.y+=p.vy;
        p.el.style.transform=`translate3d(${p.x}px,${p.y}px,0)`;
      }
    }
    requestAnimationFrame(animateParticles);
  }

  addEventListener('pointermove',e=>{mouse.x=e.clientX;mouse.y=e.clientY;mouse.active=true},{passive:true});
  addEventListener('pointerleave',()=>{mouse.active=false});
  addEventListener('resize',resizeParticles);
  resizeParticles();
  requestAnimationFrame(animateParticles);

  /* Voice controls. */
  const style=document.createElement('style');
  style.textContent=`
    .mira-voice-bar{position:fixed;right:20px;bottom:92px;z-index:20;display:flex;gap:7px;align-items:center;background:#11151ddd;border:1px solid #303644;border-radius:14px;padding:6px;backdrop-filter:blur(16px);box-shadow:0 12px 40px #0008}
    .mira-voice-btn{border:0;border-radius:10px;padding:8px 11px;background:#1b202b;color:#f5f7fb;cursor:pointer;font:12px Inter,system-ui,sans-serif}
    .mira-voice-btn.on{background:#f4c542;color:#111;font-weight:800}.mira-voice-btn.stop{display:none}
  `;
  document.head.appendChild(style);
  const bar=document.createElement('div');bar.className='mira-voice-bar';
  bar.innerHTML='<button class="mira-voice-btn toggle"></button><button class="mira-voice-btn stop">■ Stop</button>';
  document.body.appendChild(bar);
  const toggle=bar.querySelector('.toggle'),stop=bar.querySelector('.stop');
  function render(){toggle.textContent=enabled?'🔊 Voice ON':'🔇 Voice OFF';toggle.classList.toggle('on',enabled);stop.style.display=audio?'block':'none';}
  async function status(){try{const r=await fetch('/api/voice/status');const d=await r.json();provider=d.provider||'browser';toggle.title=provider==='edge-tts'?`Free neural Hindi female voice • ${d.voice||'Swara'}`:provider==='piper'?`Free local Hindi female voice • ${d.voice||'Priyamvada'}`:'Voice unavailable';}catch(_){} }
  function browserSpeak(text){if(!('speechSynthesis'in window))return;speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.lang=/[\u0900-\u097F]/.test(text)?'hi-IN':'en-IN';u.rate=.96;u.pitch=1.02;u.onstart=render;u.onend=render;speechSynthesis.speak(u);}
  async function serverSpeak(text){if(audio){audio.pause();audio=null;}const r=await fetch('/api/voice/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});if(!r.ok)throw new Error('Server voice unavailable');const blob=await r.blob(),url=URL.createObjectURL(blob);audio=new Audio(url);audio.onended=()=>{URL.revokeObjectURL(url);audio=null;render()};audio.onerror=()=>{URL.revokeObjectURL(url);audio=null;render()};render();await audio.play();}
  async function speak(text){if(!enabled||!text||text===lastSpoken)return;lastSpoken=text;try{if(provider==='edge-tts'||provider==='piper'||provider==='elevenlabs')await serverSpeak(text);else browserSpeak(text);}catch(_){browserSpeak(text);}}
  toggle.onclick=()=>{enabled=!enabled;localStorage.setItem(KEY,String(enabled));if(!enabled){if(audio){audio.pause();audio=null;}if('speechSynthesis'in window)speechSynthesis.cancel();}render();};
  stop.onclick=()=>{if(audio){audio.pause();audio.currentTime=0;audio=null;}if('speechSynthesis'in window)speechSynthesis.cancel();render();};
  const chat=document.getElementById('chat'),model=document.getElementById('model');
  if(chat){const observer=new MutationObserver(()=>{clearTimeout(timer);if(!enabled)return;timer=setTimeout(()=>{if(model&&/generating|listening/i.test(model.textContent||''))return;const bubbles=chat.querySelectorAll('.assistant .bubble');const last=bubbles[bubbles.length-1];if(last&&last.textContent.trim())speak(last.textContent.trim());},850);});observer.observe(chat,{subtree:true,childList:true,characterData:true});}
  status();render();
})();