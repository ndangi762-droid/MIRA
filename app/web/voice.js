(() => {
  const KEY = 'mira_voice_enabled';
  let enabled = localStorage.getItem(KEY) === 'true';
  let audio = null;
  let timer = null;
  let lastSpoken = '';
  let provider = 'browser';

  /* Premium reactive particle field + MIRA core particles */
  const particleStyle = document.createElement('style');
  particleStyle.textContent = `
    .core-text{display:none!important}
    .core{background:transparent!important;box-shadow:none!important;overflow:visible!important}
    .mira-particle-field{position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}
    .center,.sidebar,.rightbar,.topbar,.composer-wrap{position:relative;z-index:1}
    .welcome{position:relative;z-index:1}
    .mira-core-particles{position:absolute;inset:-35px;border-radius:50%;pointer-events:none;overflow:visible}
    .mira-core-particle{position:absolute;width:5px;height:5px;border-radius:50%;background:#f5c84b;box-shadow:0 0 10px #f5c84b99,0 0 22px #f5c84b44;transform:translate(-50%,-50%);will-change:transform}
    .mira-core-particle.small{width:3px;height:3px;opacity:.7}
    @media(max-width:720px){.mira-core-particle{width:4px;height:4px}.mira-core-particle.small{width:2px;height:2px}}
  `;
  document.head.appendChild(particleStyle);

  const canvas = document.createElement('canvas');
  canvas.className = 'mira-particle-field';
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d', { alpha: true });
  const mouse = { x: -9999, y: -9999, active: false };
  let particles = [];
  let coreParticles = [];
  let raf = 0;

  function resizeParticles() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = innerWidth * dpr;
    canvas.height = innerHeight * dpr;
    canvas.style.width = innerWidth + 'px';
    canvas.style.height = innerHeight + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.min(190, Math.max(90, Math.floor(innerWidth * innerHeight / 10500)));
    if (particles.length !== count) {
      particles = Array.from({length: count}, () => ({
        x: Math.random() * innerWidth,
        y: Math.random() * innerHeight,
        vx: (Math.random() - .5) * .22,
        vy: (Math.random() - .5) * .22,
        r: 1.8 + Math.random() * 2.5,
        a: .22 + Math.random() * .5,
        gold: Math.random() < .16
      }));
    }
  }

  function updateCoreParticles() {
    const core = document.querySelector('.core');
    if (!core) return;
    let layer = core.querySelector('.mira-core-particles');
    if (!layer) {
      layer = document.createElement('div');
      layer.className = 'mira-core-particles';
      core.appendChild(layer);
      coreParticles = Array.from({length: 34}, (_, i) => {
        const angle = Math.random() * Math.PI * 2;
        const radius = 72 + Math.random() * 48;
        const el = document.createElement('i');
        el.className = 'mira-core-particle' + (i % 3 === 0 ? ' small' : '');
        layer.appendChild(el);
        return { el, angle, radius, speed: .00035 + Math.random() * .00055, wobble: Math.random() * 8, phase: Math.random() * 6.28 };
      });
    }
  }

  function animateParticles(t) {
    const w = innerWidth, h = innerHeight;
    ctx.clearRect(0, 0, w, h);

    for (const p of particles) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < -10) p.x = w + 10; if (p.x > w + 10) p.x = -10;
      if (p.y < -10) p.y = h + 10; if (p.y > h + 10) p.y = -10;

      if (mouse.active) {
        const dx = p.x - mouse.x, dy = p.y - mouse.y;
        const dist2 = dx * dx + dy * dy;
        const radius = 145;
        if (dist2 < radius * radius) {
          const dist = Math.sqrt(dist2) || 1;
          const force = (1 - dist / radius) * 1.9;
          p.x += (dx / dist) * force;
          p.y += (dy / dist) * force;
        }
      }

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.gold ? `rgba(245,200,75,${p.a})` : `rgba(180,190,205,${p.a * .55})`;
      ctx.fill();
    }

    // Very subtle particle-to-particle network, only when close.
    for (let i = 0; i < particles.length; i++) {
      const a = particles[i];
      for (let j = i + 1; j < particles.length && j < i + 7; j++) {
        const b = particles[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < 92) {
          ctx.beginPath();
          ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(245,200,75,${(1-d/92)*.055})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    }

    updateCoreParticles();
    for (const p of coreParticles) {
      p.angle += p.speed * 16;
      const baseX = 50 + Math.cos(p.angle) * p.radius;
      const baseY = 50 + Math.sin(p.angle) * p.radius;
      let x = baseX + Math.cos(t * .001 + p.phase) * p.wobble;
      let y = baseY + Math.sin(t * .0012 + p.phase) * p.wobble;
      const rect = document.querySelector('.core')?.getBoundingClientRect();
      if (rect && mouse.active) {
        const px = rect.left + (x / 100) * rect.width;
        const py = rect.top + (y / 100) * rect.height;
        const dx = px - mouse.x, dy = py - mouse.y;
        const d = Math.hypot(dx, dy) || 1;
        if (d < 180) {
          const push = (1 - d / 180) * 28;
          x += (dx / d) * push * 100 / rect.width;
          y += (dy / d) * push * 100 / rect.height;
        }
      }
      p.el.style.left = x + '%';
      p.el.style.top = y + '%';
    }
    raf = requestAnimationFrame(animateParticles);
  }

  addEventListener('pointermove', e => { mouse.x = e.clientX; mouse.y = e.clientY; mouse.active = true; }, {passive:true});
  addEventListener('pointerleave', () => { mouse.active = false; });
  addEventListener('resize', resizeParticles);
  resizeParticles();
  raf = requestAnimationFrame(animateParticles);

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
      toggle.title = provider === 'edge-tts' ? `Free neural Hindi female voice • ${d.voice || 'Swara'}` : provider === 'piper' ? `Free local Hindi female voice • ${d.voice || 'Priyamvada'}` : 'Voice unavailable';
    } catch (_) {}
  }

  function browserSpeak(text) {
    if (!('speechSynthesis' in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = /[\u0900-\u097F]/.test(text) ? 'hi-IN' : 'en-IN';
    u.rate = 0.96; u.pitch = 1.02;
    u.onstart = render; u.onend = render;
    speechSynthesis.speak(u);
  }

  async function serverSpeak(text) {
    if (audio) { audio.pause(); audio = null; }
    const r = await fetch('/api/voice/speak', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text})});
    if (!r.ok) throw new Error('Server voice unavailable');
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    audio = new Audio(url);
    audio.onended = () => { URL.revokeObjectURL(url); audio = null; render(); };
    audio.onerror = () => { URL.revokeObjectURL(url); audio = null; render(); };
    render(); await audio.play();
  }

  async function speak(text) {
    if (!enabled || !text || text === lastSpoken) return;
    lastSpoken = text;
    try { if (provider === 'edge-tts' || provider === 'piper' || provider === 'elevenlabs') await serverSpeak(text); else browserSpeak(text); }
    catch (_) { browserSpeak(text); }
  }

  toggle.onclick = () => {
    enabled = !enabled;
    localStorage.setItem(KEY, String(enabled));
    if (!enabled) { if (audio) { audio.pause(); audio = null; } if ('speechSynthesis' in window) speechSynthesis.cancel(); }
    render();
  };
  stop.onclick = () => { if (audio) { audio.pause(); audio.currentTime = 0; audio = null; } if ('speechSynthesis' in window) speechSynthesis.cancel(); render(); };

  const chat = document.getElementById('chat');
  const model = document.getElementById('model');
  if (chat) {
    const observer = new MutationObserver(() => {
      clearTimeout(timer); if (!enabled) return;
      timer = setTimeout(() => {
        if (model && /generating|listening/i.test(model.textContent || '')) return;
        const bubbles = chat.querySelectorAll('.assistant .bubble');
        const last = bubbles[bubbles.length - 1];
        if (last && last.textContent.trim()) speak(last.textContent.trim());
      }, 850);
    });
    observer.observe(chat, {subtree:true, childList:true, characterData:true});
  }

  status(); render();
})();