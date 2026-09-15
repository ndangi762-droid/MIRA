(() => {
  const PC = '/api/pc2';
  const isPcCommand = (text) => {
    const t = String(text || '').trim().toLowerCase();
    if (!t) return false;
    return /\b(notepad|notes|calculator|calc|paint|chrome|google chrome|explorer|file explorer|task manager|youtube|gmail|github)\b/.test(t) && /\b(open|khol|kholo|chalao|start|launch)\b/.test(t)
      || /^(search|search karo|search for|google par|google me)\s+/.test(t)
      || /^(type|type karo|likho)\s+/.test(t)
      || /\b(copy|paste|select all|save|undo|redo|close window|switch window)\b/.test(t)
      || /^click(?: karo)?\s+\d+\s+\d+$/i.test(t);
  };

  function addBubble(text, kind='assistant') {
    const chat = document.querySelector('.chat');
    if (!chat) return;
    const msg = document.createElement('div'); msg.className = 'msg ' + kind;
    const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = text;
    msg.appendChild(bubble); chat.appendChild(msg); chat.scrollTop = chat.scrollHeight;
  }

  async function runPcCommand(text) {
    addBubble(text, 'user');
    addBubble('Boss, PC command bhej rahi hoon…', 'assistant');
    try {
      const r = await fetch(PC + '/command', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: text, device: 'windows'})
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'PC command rejected');
      const id = data.command_id;
      for (let i = 0; i < 20; i++) {
        await new Promise(resolve => setTimeout(resolve, 500));
        const rr = await fetch(PC + '/result/' + encodeURIComponent(id), {cache:'no-store'});
        if (!rr.ok) continue;
        const result = await rr.json();
        if (result.status === 'done') { addBubble('Done Boss — ' + (result.message || 'PC action complete.')); return true; }
        if (result.status === 'error') { addBubble('Boss, PC action fail hua: ' + (result.message || 'Unknown error.')); return true; }
      }
      addBubble('Boss, command PC agent tak queue ho gaya hai. Agent running hona chahiye.');
    } catch (e) {
      addBubble('Boss, PC control error: ' + (e && e.message ? e.message : 'Unknown error.'));
    }
    return true;
  }

  function clearComposer() {
    const ta = document.querySelector('textarea');
    if (ta) { ta.value = ''; ta.dispatchEvent(new Event('input', {bubbles:true})); }
  }

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || e.shiftKey || e.isComposing) return;
    const ta = e.target && e.target.closest ? e.target.closest('textarea') : null;
    if (!ta || !isPcCommand(ta.value)) return;
    e.preventDefault(); e.stopImmediatePropagation();
    const text = ta.value.trim(); clearComposer(); runPcCommand(text);
  }, true);

  document.addEventListener('click', (e) => {
    const btn = e.target && e.target.closest ? e.target.closest('.send') : null;
    if (!btn) return;
    const ta = document.querySelector('textarea');
    if (!ta || !isPcCommand(ta.value)) return;
    e.preventDefault(); e.stopImmediatePropagation();
    const text = ta.value.trim(); clearComposer(); runPcCommand(text);
  }, true);

  window.MIRA_PC = { run: runPcCommand, isCommand: isPcCommand };
})();
