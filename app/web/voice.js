(() => {
  const KEY = 'mira_voice_enabled';
  let enabled = localStorage.getItem(KEY) === 'true';
  let audio = null;
  let timer = null;
  let lastSpoken = '';
  let provider = 'browser';

  /* MIRA particle core: keep the existing UI, replace only the old ring with a slow reactive M. */
  const particleStyle = document.createElement('style');
  particleStyle.textContent = `
    .core{background:transparent!important;box-shadow:none!important;filter:none!important;overflow:visible!important}
    .core:before,.core:after,.core-text{display:none!important;content:none!important}
    .mira-particle-field{position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}
    .center,.sidebar,.rightbar,.topbar,.composer-wrap,.welcome{position:relative;z-index:1}
    .mira-core-field{position:absolute;left:50%;top:50%;width:260px;height:230px;transform:translate(-50%,-50%);pointer-events:none;overflow:visible;z-index:2}
    .mira-core-dot{position:absolute;width:4px;height:4px;border-radius:50%;background:#f5c84b;box-shadow:0 0 8px #f5c84b99,0 0 18px #f5c84b44;will-change:transform;transform:translate3d(-50%,-50%,0)}
    .mira-core-dot.dim{width:2.5px;height:2.5px;opacity:.58}
    @media(max-width:720px){.mira-core-field{width:220px;height:195px}.mira-core-dot{width:3.5px;height:3.5px}.mira-core-dot.dim{width:2px;height:2px}}
  `;
  document.head.appendChild(particleStyle);

  const canvas = document.createElement('canvas');
  canvas.className = 'mira-particle-field';
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d', { alpha: true });
  const mouse = { x: -9999, y: -9999, active: false };
  let particles = [];
  let coreParticles = [];
  let coreField = null;

  function resizeParticles() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = innerWidth * dpr;
    canvas.height = innerHeight * dpr;
    canvas.style.width = innerWidth + 'px';
    canvas.style.height = innerHeight + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const count = Math.min(145, Math.max(70, Math.floor(innerWidth * innerHeight / 14500)));
    if (particles.length !== count) {
      particles = Array.from({length: count}, () => ({
        x: Math.random() * innerWidth,
        y: Math.random() * innerHeight,
        vx: (Math.random() - .5) * .105,
        vy: (Math.random() - .5) * .105,
        r: 1.5 + Math.random() * 1.8,
        a: .20 + Math.random() * .38,
        gold: Math.random() < .18,
        seed: Math.random() * Math.PI * 2
      }));
    }
  }

  function mTargets(count) {
    const segments = [
      [20,88,20,16],
      [20,16,50,58],
      [50,58,80,16],
      [80,16,80,88]
    ];
    const targets = [];
    for (let i = 0; i < count; i++) {
      const s = segments[i % segments.length];
      const t = ((i / count) * segments.length + Math.random() * .55) % segments.length;
      const idx = Math.floor(t);
      const f = t - idx;
      const a = segments[idx];
      const b = segments[(idx + 1) % segments.length];
      const x = a[0] + (b[0] - a[0]) * f;
      const y = a[1] + (b[1] - a[1]) * f;
      targets.push({x, y});
    }
    return targets;
  }

  function ensureCore() {
    const core = document.querySelector('.core');
    if (!core) return null;
    if (!coreField) {
      coreField = document.createElement('div');
      coreField.className = 'mira-core-field';
      core.appendChild(coreField);
      const count = 96;
      const targets = mTargets(count);
      coreParticles = targets.map((target, i) => {
        const el = document.createElement('i');
        el.className = 'mira-core-dot' + (i % 4 === 0 ? ' dim' : '');
        coreField.appendChild(el);
        return {
          el,
          tx: target.x,
          ty: target.y,
          x: target.x + (Math.random() - .5) * 2,
          y: target.y + (Math.random() - .5) * 2,
          vx: 0,
          vy: 0,
          drift: Math.random() * Math.PI * 2,
          phase: Math.random() * Math.PI * 2
        };
      });
    }
    return core;
  }

  function animateParticles(t) {
    const w = innerWidth, h = innerHeight;
    ctx.clearRect(0, 0, w, h);

    // Slow ambient background motion.
    for (const p of particles) {
      p.x += p.vx + Math.sin(t * .00015 + p.seed) * .018;
      p.y += p.vy + Math.cos(t * .00013 + p.seed) * .018;
      if (p.x < -10) p.x = w + 10;
      if (p.x > w + 10) p.x = -10;
      if (p.y < -10) p.y = h + 10;
      if (p.y > h + 10) p.y = -10;

      if (mouse.active) {
        const dx = p.x - mouse.x, dy = p.y - mouse.y;
        const d = Math.hypot(dx, dy) || 1;
        const radius = 135;
        if (d < radius) {
          const force = (1 - d / radius) * .95;
          p.x += (dx / d) * force;
          p.y += (dy / d) * force;
        }
      }

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.gold ? `rgba(245,200,75,${p.a})` : `rgba(190,200,215,${p.a * .48})`;
      ctx.fill();
    }

    const core = ensureCore();
    if (core && coreField) {
      const fieldRect = coreField.getBoundingClientRect();
      const spring = .045;
      for (const p of coreParticles) {
        const tx = (p.tx / 100) * fieldRect.width;
        const ty = (p.ty / 100) * fieldRect.height;

        // Soft autonomous flow while preserving the M silhouette.
        const waveX = Math.sin(t * .00045 + p.phase) * 1.8;
        const waveY = Math.cos(t * .00038 + p.drift) * 1.8;
        const targetX = tx + waveX;
        const targetY = ty + waveY;
        p.vx += (targetX - p.x) * spring;
        p.vy += (targetY - p.y) * spring;

        // Cursor interaction: fast push away, then spring smoothly back to M.
        if (mouse.active) {
          const px = fieldRect.left + p.x;
          const py = fieldRect.top + p.y;
          const dx = px - mouse.x, dy = py - mouse.y;
          const d = Math.hypot(dx, dy) || 1;
          const radius = 125;
          if (d < radius) {
            const force = Math.pow(1 - d / radius, 1.7) * 3.8;
            p.vx += (dx / d) * force;
            p.vy += (dy / d) * force;
          }
        }

        p.vx *= .89;
        p.vy *= .89;
        p.x += p.vx;
        p.y += p.vy;
        p.el.style.transform = `translate3d(${p.x}px,${p.y}px,0)`;
      }
    }

    requestAnimationFrame(animateParticles);
  }

  addEventListener('pointermove', e => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    mouse.active = true;
  }, {passive:true});
  addEventListener('pointerleave', () => { mouse.active = false; });
  addEventListener('resize', resizeParticles);
  resizeParticles();
  requestAnimationFrame(animateParticles);

  /* Existing voice controls kept unchanged. */
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
    observer.observe(chat, {subtree:true, childList:true, characterData:true});
  }

  status();
  render();
})();