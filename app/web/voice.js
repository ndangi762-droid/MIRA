(() => {
  /* MIRA reactive particle field — full dashboard background */
  const particleStyle = document.createElement('style');
  particleStyle.textContent = `
    html,body{background:#030507!important}
    #mira-particles{position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none;background:#030507}
    .app{position:relative;z-index:1;background:transparent!important}
    .sidebar,.center,.rightbar{background:transparent!important}
    .sidebar{backdrop-filter:blur(2px)}
    .center{background:radial-gradient(circle at 50% 35%,rgba(30,35,42,.10),transparent 42%)!important}
    .mira-voice-bar{z-index:30!important}
  `;
  document.head.appendChild(particleStyle);

  const canvas = document.createElement('canvas');
  canvas.id = 'mira-particles';
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d');
  const mouse = {x:-9999,y:-9999,active:false};
  let W=0,H=0,dpr=1,particles=[];
  const COUNT=window.innerWidth<800?95:180;
  const GOLD='245,200,75';

  function resize(){
    dpr=Math.min(window.devicePixelRatio||1,2);
    W=window.innerWidth; H=window.innerHeight;
    canvas.width=Math.floor(W*dpr); canvas.height=Math.floor(H*dpr);
    canvas.style.width=W+'px'; canvas.style.height=H+'px';
    ctx.setTransform(dpr,0,0,dpr,0,0);
    if(!particles.length) init();
  }
  function init(){
    particles=Array.from({length:COUNT},()=>({
      x:Math.random()*W,y:Math.random()*H,
      vx:(Math.random()-.5)*.22,vy:(Math.random()-.5)*.22,
      r:Math.random()*1.35+.35,
      a:Math.random()*.45+.18,
      gold:Math.random()<.18,
      seed:Math.random()*Math.PI*2
    }));
  }
  function pointer(x,y){mouse.x=x;mouse.y=y;mouse.active=true}
  window.addEventListener('pointermove',e=>pointer(e.clientX,e.clientY),{passive:true});
  window.addEventListener('pointerleave',()=>mouse.active=false);
  window.addEventListener('blur',()=>mouse.active=false);
  window.addEventListener('resize',resize,{passive:true});

  function draw(t){
    ctx.clearRect(0,0,W,H);
    for(const p of particles){
      /* Strong, immediate mouse repulsion — particles jump away from cursor */
      if(mouse.active){
        const dx=p.x-mouse.x,dy=p.y-mouse.y;
        const dist=Math.hypot(dx,dy);
        const radius=145;
        if(dist<radius && dist>.1){
          const force=Math.pow(1-dist/radius,2)*2.7;
          p.vx+=(dx/dist)*force;
          p.vy+=(dy/dist)*force;
        }
      }
      const speed=Math.hypot(p.vx,p.vy);
      if(speed>.9){p.vx*=.91;p.vy*=.91}
      p.vx+=(Math.sin(t*.00035+p.seed)*.002);
      p.vy+=(Math.cos(t*.00031+p.seed)*.002);
      p.vx*=.997;p.vy*=.997;
      p.x+=p.vx;p.y+=p.vy;
      if(p.x<-5)p.x=W+5;if(p.x>W+5)p.x=-5;
      if(p.y<-5)p.y=H+5;if(p.y>H+5)p.y=-5;

      const pulse=.72+.28*Math.sin(t*.0012+p.seed);
      ctx.beginPath();ctx.arc(p.x,p.y,p.r*pulse,0,Math.PI*2);
      ctx.fillStyle=p.gold?`rgba(${GOLD},${p.a})`:`rgba(220,228,238,${p.a*.72})`;
      ctx.fill();
    }
    /* Connect nearby particles with very subtle lines */
    for(let i=0;i<particles.length;i++){
      const a=particles[i];
      for(let j=i+1;j<particles.length;j++){
        const b=particles[j],dx=a.x-b.x,dy=a.y-b.y,d=dx*dx+dy*dy;
        if(d<6500){
          const alpha=.055*(1-d/6500);
          ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
          ctx.strokeStyle=`rgba(190,198,210,${alpha})`;ctx.lineWidth=.45;ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }
  resize();
  requestAnimationFrame(draw);

  const KEY = 'mira_voice_enabled';
  let enabled = localStorage.getItem(KEY) === 'true';
  let audio = null;
  let timer = null;
  let lastSpoken = '';
  let provider = 'browser';

  const style = document.createElement('style');
  style.textContent = `
    .mira-voice-bar{position:fixed;right:20px;bottom:92px;z-index:20;display:flex;gap:7px;align-items:center;background:#11151ddd;border:1px solid #303644;border-radius:14px;padding:6px;backdrop-filter:blur(16px);box-shadow:0 12px 40px #0008}
    .mira-voice-btn{border:0;border-radius:10px;padding:8px 11px;background:#1b202b;color:#f5f7fb;cursor:pointer;font:12px Inter,system-ui,sans-serif}
    .mira-voice-btn.on{background:#f4c542;color:#111;font-weight:800}
    .mira-voice-btn.stop{display:none}
  `;
  document.head.appendChild(style);

  const bar = document.createElement('div');
  bar.className = 'mira-voice-bar';
  bar.innerHTML = '<button class="mira-voice-btn toggle"></button><button class="mira-voice-btn stop">■ Stop</button>';
  document.body.appendChild(bar);
  const toggle = bar.querySelector('.toggle');
  const stop = bar.querySelector('.stop');

  function render() {
    toggle.textContent = enabled ? '🔊 Voice ON' : '🔇 Voice OFF';
    toggle.classList.toggle('on', enabled);
    stop.style.display = audio ? 'block' : 'none';
  }

  async function status() {
    try {
      const r = await fetch('/api/voice/status');
      const d = await r.json();
      provider = d.provider || 'browser';
      toggle.title = provider === 'edge-tts'
        ? `Free neural Hindi female voice • ${d.voice || 'Swara'}`
        : provider === 'piper'
          ? `Free local Hindi female voice • ${d.voice || 'Priyamvada'}`
          : 'Voice unavailable';
    } catch (_) {}
  }

  function browserSpeak(text) {
    if (!('speechSynthesis' in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = /[\u0900-\u097F]/.test(text) ? 'hi-IN' : 'en-IN';
    u.rate = 0.96;
    u.pitch = 1.02;
    u.onstart = render;
    u.onend = render;
    speechSynthesis.speak(u);
  }

  async function serverSpeak(text) {
    if (audio) { audio.pause(); audio = null; }
    const r = await fetch('/api/voice/speak', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    if (!r.ok) throw new Error('Server voice unavailable');
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    audio = new Audio(url);
    audio.onended = () => { URL.revokeObjectURL(url); audio = null; render(); };
    audio.onerror = () => { URL.revokeObjectURL(url); audio = null; render(); };
    render();
    await audio.play();
  }

  async function speak(text) {
    if (!enabled || !text || text === lastSpoken) return;
    lastSpoken = text;
    try {
      if (provider === 'edge-tts' || provider === 'piper' || provider === 'elevenlabs') await serverSpeak(text);
      else browserSpeak(text);
    } catch (_) { browserSpeak(text); }
  }

  toggle.onclick = () => {
    enabled = !enabled;
    localStorage.setItem(KEY, String(enabled));
    if (!enabled) {
      if (audio) { audio.pause(); audio = null; }
      if ('speechSynthesis' in window) speechSynthesis.cancel();
    }
    render();
  };

  stop.onclick = () => {
    if (audio) { audio.pause(); audio.currentTime = 0; audio = null; }
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    render();
  };

  const chat = document.getElementById('chat');
  const model = document.getElementById('model');
  if (chat) {
    const observer = new MutationObserver(() => {
      clearTimeout(timer);
      if (!enabled) return;
      timer = setTimeout(() => {
        if (model && /generating|listening/i.test(model.textContent || '')) return;
        const bubbles = chat.querySelectorAll('.assistant .bubble');
        const last = bubbles[bubbles.length - 1];
        if (last && last.textContent.trim()) speak(last.textContent.trim());
      }, 850);
    });
    observer.observe(chat, {subtree: true, childList: true, characterData: true});
  }

  status();
  render();
})();
