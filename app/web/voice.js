(() => {
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
      if (provider === 'elevenlabs') toggle.title = 'Natural ElevenLabs Hindi voice';
      else toggle.title = 'Browser voice fallback — configure ElevenLabs for natural voice';
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

  async function elevenSpeak(text) {
    if (audio) { audio.pause(); audio = null; }
    const r = await fetch('/api/voice/speak', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    if (!r.ok) throw new Error('ElevenLabs voice unavailable');
    const blob = await r.blob();
    audio = new Audio(URL.createObjectURL(blob));
    audio.onended = () => { audio = null; render(); };
    audio.onerror = () => { audio = null; render(); };
    render();
    await audio.play();
  }

  async function speak(text) {
    if (!enabled || !text || text === lastSpoken) return;
    lastSpoken = text;
    try {
      if (provider === 'elevenlabs') await elevenSpeak(text);
      else browserSpeak(text);
    } catch (_) {
      browserSpeak(text);
    }
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
  if (chat) {
    const observer = new MutationObserver(() => {
      clearTimeout(timer);
      if (!enabled) return;
      timer = setTimeout(() => {
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
