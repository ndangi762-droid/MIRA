(()=>{
  let listening=false;
  let recognition=null;
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
    if(typeof toast==='function'){toast(msg);return}
    let t=document.getElementById('miraVoiceToast');
    if(!t){t=document.createElement('div');t.id='miraVoiceToast';t.style='position:fixed;left:50%;top:80px;transform:translateX(-50%);z-index:99999;padding:9px 14px;border:1px solid rgba(25,201,255,.3);background:#070b10;color:#d7f7ff;border-radius:10px;font:12px system-ui';document.body.appendChild(t)}
    t.textContent=msg;t.style.display='block';clearTimeout(t._timer);t._timer=setTimeout(()=>t.style.display='none',2600);
  };
  const setText=(text)=>{const input=getInput();if(!input)return;input.value=text;input.dispatchEvent(new Event('input',{bubbles:true}));if(typeof resize==='function')resize(input)};
  window.voiceInput=async function(){
    if(listening){try{recognition&&recognition.stop()}catch(e){}return;}
    const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR){toastSafe('Is device/browser me voice input supported nahi hai. Android Chrome try karo.');return;}
    try{
      if(navigator.mediaDevices?.getUserMedia){
        const stream=await navigator.mediaDevices.getUserMedia({audio:true});
        stream.getTracks().forEach(t=>t.stop());
      }
    }catch(e){
      const name=e?.name||'';
      if(name==='NotAllowedError'||name==='PermissionDeniedError')toastSafe('Microphone permission allow karo, phir mic dabao.');
      else toastSafe('Microphone access nahi mil raha.');
      return;
    }
    finalText='';
    recognition=new SR();
    recognition.lang='hi-IN';
    recognition.continuous=false;
    recognition.interimResults=true;
    recognition.maxAlternatives=1;
    recognition.onstart=()=>{listening=true;setListeningUI(true);toastSafe('Sun raha hoon Boss…');};
    recognition.onresult=(e)=>{
      let interim='';
      for(let i=e.resultIndex;i<e.results.length;i++){
        const text=e.results[i][0].transcript;
        if(e.results[i].isFinal)finalText+=text+' ';else interim+=text;
      }
      setText((finalText+interim).trim());
    };
    recognition.onerror=(e)=>{
      const map={
        'not-allowed':'Microphone permission denied.',
        'service-not-allowed':'Voice service allowed nahi hai.',
        'audio-capture':'Microphone detect nahi hua.',
        'no-speech':'Kuch sunai nahi diya, dobara try karo.',
        'network':'Voice service ke liye internet chahiye.'
      };
      if(e.error!=='aborted')toastSafe(map[e.error]||'Voice input stopped.');
    };
    recognition.onend=()=>{
      const text=finalText.trim()||getInput()?.value.trim()||'';
      listening=false;setListeningUI(false);recognition=null;
      if(finalText.trim()){
        setText(text);
        setTimeout(()=>{if(typeof send==='function')send();},120);
      }
    };
    try{recognition.start();}catch(e){listening=false;setListeningUI(false);toastSafe('Voice start nahi hua, dobara try karo.');}
  };
})();
