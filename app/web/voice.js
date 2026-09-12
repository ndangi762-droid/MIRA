(() => {
  const KEY = 'mira_voice_enabled';
  let enabled = localStorage.getItem(KEY) === 'true';
  let audio = null;
  let timer = null;
  let lastSpoken = '';
  let provider = 'browser';

  /* MIRA premium M-particle core: slow, coordinated motion + cursor interaction. */
  const particleStyle = document.createElement('style');
  particleStyle.textContent = `
    .core-text{display:none!important}
    .core{background:transparent!important;box-shadow:none!important;overflow:visible!important}
    .mira-particle-field{position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}
    .center,.sidebar,.rightbar,.topbar,.composer-wrap{position:relative;z-index:1}
    .welcome{position:relative;z-index:1}
  `;
  document.head.appendChild(particleStyle);

  const canvas = document.createElement('canvas');
  canvas.className = 'mira-particle-field';
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d', { alpha: true });
  const mouse = { x: -9999, y: -9999, active: false };
  let stars = [];
  let core = [];

  const M_POINTS = [
    [0.00,1.00],[0.08,0.84],[0.16,0.68],[0.24,0.52],[0.32,0.36],[0.40,0.20],[0.50,0.04],
    [0.60,0.20],[0.68,0.36],[0.76,0.52],[0.84,0.68],[0.92,0.84],[1.00,1.00]
  ];

  function resize() {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = innerWidth * dpr;
    canvas.height = innerHeight * dpr;
    canvas.style.width = innerWidth + 'px';
    canvas.style.height = innerHeight + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (stars.length === 0) {
      stars = Array.from({length: 70}, () => ({
        x: Math.random() * innerWidth,
        y: Math.random() * innerHeight,
        vx: (Math.random() - .5) * .045,
        vy: (Math.random() - .5) * .045,
        r: .7 + Math.random() * 1.5,
        a: .16 + Math.random() * .32,
        gold: Math.random() < .18
      }));
    }
    buildM();
  }

  function sampleLine(a, b, spacing) {
    const dx = b[0] - a[0], dy = b[1] - a[1];
    const len = Math.hypot(dx, dy);
    const n = Math.max(2, Math.floor(len / spacing));
    const out = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      out.push([a[0] + dx * t, a[1] + dy * t]);
    }
    return out;
  }

  function buildM() {
    const cx = innerWidth * .50;
    const cy = innerHeight * .49;
    const width = Math.min(innerWidth * .40, 470);
    const height = Math.min(innerHeight * .56, 390);
    const left = cx - width / 2;
    const top = cy - height / 2;
    const spacing = Math.max(0.035, width / 1200);
    let targets = [];
    for (let i = 0; i < M_POINTS.length - 1; i++) {
      targets = targets.concat(sampleLine(M_POINTS[i], M_POINTS[i + 1], spacing));
    }

    // Dense enough to read as an M, but sparse and premium rather than a solid stroke.
    targets = targets.filter((_, i) => i % 2 === 0);
    core = targets.map((p, i) => ({
      tx: left + p[0] * width,
      ty: top + p[1] * height,
      x: left + p[0] * width + (Math.random() - .5) * 12,
      y: top + p[1] * height + (Math.random() - .5) * 12,
      vx: 0,
      vy: 0,
      phase: Math.random() * Math.PI * 2,
      drift: 2 + Math.random() * 5,
      r: 1.2 + Math.random() * 2.2,
      a: .52 + Math.random() * .40,
      gold: i % 8 === 0 || Math.random() < .12
    }));
  }

  function animate(t) {
    const w = innerWidth, h = innerHeight;
    ctx.clearRect(0, 0, w, h);

    // Very slow background stars.
    for (const s of stars) {
      s.x += s.vx; s.y += s.vy;
      if (s.x < -4) s.x = w + 4; if (s.x > w + 4) s.x = -4;
      if (s.y < -4) s.y = h + 4; if (s.y > h + 4) s.y = -4;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = s.gold ? `rgba(245,200,75,${s.a})` : `rgba(190,205,220,${s.a * .48})`;
      ctx.fill();
    }

    // The M moves as one soft field: tiny synchronized breathing/drift, not a rotation.
    const breathe = Math.sin(t * .00055) * .8;
    for (const p of core) {
      const desiredX = p.tx + Math.sin(t * .00072 + p.phase) * p.drift + breathe;
      const desiredY = p.ty + Math.cos(t * .00061 + p.phase) * p.drift * .72;
      const dx0 = desiredX - p.x, dy0 = desiredY - p.y;
      p.vx += dx0 * .010;
      p.vy += dy0 * .010;
      p.vx *= .90;
      p.vy *= .90;

      // Cursor repulsion. Particles are pushed away, then spring back naturally.
      if (mouse.active) {
        const dx = p.x - mouse.x, dy = p.y - mouse.y;
        const d = Math.hypot(dx, dy) || 1;
        const radius = 155;
        if (d < radius) {
          const force = (1 - d / radius) * 2.9;
          p.vx += (dx / d) * force;
          p.vy += (dy / d) * force;
        }
      }

      p.x += p.vx;
      p.y += p.vy;

      // Subtle halo only; no circle/ring is drawn.
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 3.2, 0, Math.PI * 2);
      ctx.fillStyle = p.gold ? `rgba(245,200,75,${p.a * .045})` : `rgba(205,220,235,${p.a * .025})`;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.gold ? `rgba(245,200,75,${p.a})` : `rgba(225,235,245,${p.a * .72})`;
      ctx.fill();
    }

    requestAnimationFrame(animate);
  }

  addEventListener('pointermove', e => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    mouse.active = true;
  }, {passive:true});
  addEventListener('pointerleave', () => { mouse.active = false; });
  addEventListener('resize', resize);
  resize();
  requestAnimationFrame(animate);

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
