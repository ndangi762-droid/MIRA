(()=>{
  let listening=false;
  let recognition=null;
  let recorder=null;
  let chunks=[];
  let finalText='';
  const getInput=()=>document.querySelector('textarea');
  const setListeningUI=(on)=>{
    const input=getInput();
    document.documentElement.dataset.miraListening=on?'1':'0';
    document.querySelectorAll('[onclick="voiceInput()"],#micBtn,.mic-btn').forEach(b=>{
      b.setAttribute('aria-pressed',on?'true':'false');
      if(on)b.classList.add('listening');else b.classList.remove('listening');
    });
    const s=document.getElementById('status');
    if(s)s.textContent=on?'VOICE LISTENING':'SYSTEM ONLINE';
    if(typeof setState==='function')setState(on?'LISTENING':'STANDBY');
    if(on&&input)input.focus();
  };
  const toastSafe=(msg)=>{
    if(typeof toast==='function'){toast(msg);return;}
    let t=document.getElementById('miraVoiceToast');
    if(!t){t=document.createElement('div');t.id='miraVoiceToast';t.style='position:fixed;left:50%;top:80px;transform:translateX(-50%);z-index:99999;padding:9px 14px;border:1px solid rgba(25,201,255,.3);background:#070b10;color:#d7f7ff;border-radius:10px;font:12px system-ui';document.body.appendChild(t)}
    t.textContent=msg;t.style.display='block';clearTimeout(t._timer);t._timer=setTimeout(()=>t.style.display='none',3000);
  };
  const setText=(text)=>{const input=getInput();if(!input)return;input.value=text;input.dispatchEvent(new Event('input',{bubbles:true}));if(typeof resize==='function')resize(input)};
  const sendText=()=>{if(getInput()?.value.trim()&&typeof send==='function')setTimeout(()=>send(),120)};
  const uploadRecording=async(blob)=>{
    const form=new FormData();
    const ext=blob.type.includes('mp4')?'m4a':blob.type.includes('ogg')?'ogg':'webm';
    form.append('file',blob,`mira-voice.${ext}`);
    const r=await fetch('/api/voice/transcribe',{method:'POST',body:form,cache:'no-store'});
    if(!r.ok){let detail='Voice transcription failed';try{const x=await r.json();detail=x.detail||detail}catch(e){}throw new Error(detail)}
    const x=await r.json();
    return String(x.text||'').trim();
  };
  const startRecorder=async()=>{
    if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){toastSafe('Is iPhone browser me audio recording supported nahi hai.');return;}
    let stream;
    try{stream=await navigator.mediaDevices.getUserMedia({audio:true});}
    catch(e){toastSafe('Microphone permission allow karo, phir MIC dabao.');return;}
    const types=['audio/mp4','audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus'];
    const mime=types.find(t=>MediaRecorder.isTypeSupported?.(t))||'';
    chunks=[];
    try{recorder=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);}catch(e){stream.getTracks().forEach(t=>t.stop());toastSafe('Audio recorder start nahi hua.');return;}
    listening=true;setListeningUI(true);toastSafe('Sun raha hoon Boss… boliye.');
    recorder.ondataavailable=e=>{if(e.data&&e.data.size)chunks.push(e.data)};
    recorder.onerror=()=>toastSafe('Audio recording error.');
    recorder.onstop=async()=>{
      stream.getTracks().forEach(t=>t.stop());
      const blob=new Blob(chunks,{type:recorder?.mimeType||mime||'audio/mp4'});
      recorder=null;listening=false;setListeningUI(false);
      if(blob.size<1000){toastSafe('Kuch record nahi hua, dobara try karo.');return;}
      toastSafe('MIRA sun rahi hai…');
      try{const text=await uploadRecording(blob);if(!text){toastSafe('Speech samajh nahi aayi, dobara bolo.');return;}setText(text);sendText();}
      catch(e){toastSafe(e.message||'Voice transcription failed.');}
    };
    recorder.start();
  };
  window.voiceInput=async function(){
    if(listening){try{if(recorder)recorder.stop();else recognition&&recognition.stop()}catch(e){}return;}
    const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR){await startRecorder();return;}
    try{
      if(navigator.mediaDevices?.getUserMedia){const stream=await navigator.mediaDevices.getUserMedia({audio:true});stream.getTracks().forEach(t=>t.stop());}
    }catch(e){toastSafe('Microphone permission allow karo, phir MIC dabao.');return;}
    finalText='';recognition=new SR();recognition.lang='hi-IN';recognition.continuous=false;recognition.interimResults=true;recognition.maxAlternatives=1;
    recognition.onstart=()=>{listening=true;setListeningUI(true);toastSafe('Sun raha hoon Boss…');};
    recognition.onresult=(e)=>{let interim='';for(let i=e.resultIndex;i<e.results.length;i++){const text=e.results[i][0].transcript;if(e.results[i].isFinal)finalText+=text+' ';else interim+=text}setText((finalText+interim).trim())};
    recognition.onerror=async(e)=>{if(e.error==='not-allowed'||e.error==='service-not-allowed'){try{await startRecorder();return}catch(x){}}if(e.error!=='aborted')toastSafe(({ 'audio-capture':'Microphone detect nahi hua.','no-speech':'Kuch sunai nahi diya, dobara try karo.','network':'Voice service ke liye internet chahiye.'}[e.error])||'Voice input stopped.')};
    recognition.onend=()=>{const text=finalText.trim();listening=false;setListeningUI(false);recognition=null;if(text){setText(text);sendText()}};
    try{recognition.start()}catch(e){recognition=null;listening=false;setListeningUI(false);await startRecorder()}
  };

  // Hide the internal AI engine/provider badge from the user-facing HUD.
  const hideEngineBadge=()=>{
    document.querySelectorAll('.metric,.side-info').forEach(el=>{
      const text=(el.textContent||'').replace(/\s+/g,' ').trim().toUpperCase();
      if(text.includes('AI ENGINE')&&text.includes('GEMINI'))el.style.display='none';
    });
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',hideEngineBadge,{once:true});
  else hideEngineBadge();
  new MutationObserver(hideEngineBadge).observe(document.documentElement,{subtree:true,childList:true});
})();
