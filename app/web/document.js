(() => {
  const style = document.createElement('style');
  style.textContent = `
    .doc-panel{position:fixed;inset:0;z-index:80;display:none;place-items:center;background:rgba(1,4,7,.78);backdrop-filter:blur(14px)}
    .doc-panel.show{display:grid}
    .doc-card{width:min(92vw,560px);max-height:78vh;overflow:auto;background:rgba(5,10,15,.96);border:1px solid rgba(25,201,255,.28);border-radius:20px;padding:22px;box-shadow:0 20px 80px rgba(0,0,0,.55),0 0 40px rgba(25,201,255,.08)}
    .doc-title{color:#eaf8ff;font-size:14px;letter-spacing:3px;text-transform:uppercase}.doc-sub{color:#697783;font-size:10px;margin:7px 0 18px}.doc-row{display:flex;gap:9px;align-items:center}.doc-btn{border:1px solid rgba(25,201,255,.22);background:#081119;color:#bfefff;border-radius:10px;padding:9px 12px;font-size:10px}.doc-btn:hover{border-color:rgba(25,201,255,.6);color:#fff}.doc-file{color:#7f8c98;font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}.doc-status{margin-top:13px;color:#19c9ff;font-size:9px;line-height:1.5;white-space:pre-wrap}.doc-close{float:right;border:0;background:transparent;color:#697783;font-size:18px}.doc-close:hover{color:#fff}
  `;
  document.head.appendChild(style);

  const panel = document.createElement('div');
  panel.className = 'doc-panel';
  panel.innerHTML = `<div class="doc-card"><button class="doc-close" aria-label="Close">×</button><div class="doc-title">DOCUMENT INTELLIGENCE</div><div class="doc-sub">Upload a PDF, TXT or Markdown file and ask MIRA about it.</div><div class="doc-row"><button class="doc-btn" id="docChoose">CHOOSE FILE</button><div class="doc-file" id="docFile">No file selected</div><button class="doc-btn" id="docUpload" disabled>UPLOAD</button></div><div class="doc-status" id="docStatus"></div></div>`;
  document.body.appendChild(panel);

  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.pdf,.txt,.md,application/pdf,text/plain,text/markdown';
  input.hidden = true;
  document.body.appendChild(input);

  const choose = panel.querySelector('#docChoose');
  const upload = panel.querySelector('#docUpload');
  const fileLabel = panel.querySelector('#docFile');
  const status = panel.querySelector('#docStatus');
  let selected = null;

  function openPanel(){ panel.classList.add('show'); status.textContent=''; }
  function closePanel(){ panel.classList.remove('show'); }
  choose.onclick = () => input.click();
  panel.querySelector('.doc-close').onclick = closePanel;
  panel.addEventListener('click', e => { if(e.target === panel) closePanel(); });

  input.onchange = () => {
    selected = input.files?.[0] || null;
    fileLabel.textContent = selected ? selected.name : 'No file selected';
    upload.disabled = !selected;
    status.textContent = selected ? `${selected.name} ready.` : '';
  };

  upload.onclick = async () => {
    if(!selected) return;
    upload.disabled = true;
    status.textContent = 'Uploading…';
    const body = new FormData();
    body.append('file', selected);
    try {
      const res = await fetch('/api/files/upload', {method:'POST', body});
      const data = await res.json();
      if(!res.ok) throw new Error(data.detail || 'Upload failed');
      status.textContent = `Uploaded: ${data.file || selected.name}\nAb ab chat mein is document ke baare mein question pooch sakte ho.`;
      const textarea = document.querySelector('textarea');
      if(textarea){ textarea.value = `Maine document upload kiya hai: ${data.file || selected.name}. Is document ko read karke batao ki isme kya important hai.`; textarea.dispatchEvent(new Event('input',{bubbles:true})); textarea.focus(); }
    } catch(err) {
      status.textContent = `Upload failed: ${err.message}`;
    } finally { upload.disabled = false; }
  };

  function addButton(){
    const tools = document.querySelector('.tools');
    if(!tools || tools.querySelector('[data-document-tool]')) return;
    const btn = document.createElement('button');
    btn.className = 'tool'; btn.dataset.documentTool = '1'; btn.textContent = '📎 FILE'; btn.title = 'Upload PDF / TXT / MD'; btn.onclick = openPanel;
    tools.prepend(btn);

    const box = document.querySelector('.box');
    if(box && !document.querySelector('[data-document-mobile]')){
      const mobile = btn.cloneNode(true); mobile.dataset.documentMobile='1'; mobile.onclick=openPanel; mobile.className='round'; mobile.textContent='📎'; mobile.title='Upload document';
      box.insertBefore(mobile, box.firstElementChild);
    }
  }

  addButton();
  new MutationObserver(addButton).observe(document.body,{childList:true,subtree:true});
})();
