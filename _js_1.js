
function reportClientError(message, source, line, column, stack){
  try{
    fetch('/api/client_error',{
      method:'POST',headers:{'Content-Type':'application/json'},keepalive:true,
      body:JSON.stringify({message:String(message||'client_error'),source:source||'',line:line||0,column:column||0,stack:stack||''})
    }).catch(function(){});
  }catch(ignore){}
}
window.onerror=function(message,source,line,column,error){
  reportClientError(message,source,line,column,error&&error.stack);
  return false;
};
window.addEventListener('unhandledrejection',function(ev){
  var r=ev&&ev.reason;
  reportClientError('Unhandled rejection: '+(r&&r.message?r.message:String(r||'')),'',0,0,r&&r.stack);
});
// ---------- garsai (Web Audio API, be joku isoriniu failu) ----------
var audioCtx = null;
function ac(){ if(!audioCtx){ audioCtx = new (window.AudioContext||window.webkitAudioContext)(); } return audioCtx; }
function beep(freq, dur, type, vol, delay){
  try{
    var ctx = ac();
    var t0 = ctx.currentTime + (delay||0);
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.type = type||'sine'; osc.frequency.setValueAtTime(freq, t0);
    gain.gain.setValueAtTime(0, t0);
    gain.gain.linearRampToValueAtTime(vol||0.2, t0+0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, t0+dur);
    osc.connect(gain); gain.connect(ctx.destination);
    osc.start(t0); osc.stop(t0+dur+0.05);
  }catch(e){}
}
function tickSound(){ beep(720, 0.09, 'square', 0.12); }
function startSound(){
  beep(440,0.14,'sawtooth',0.22,0); beep(660,0.14,'sawtooth',0.22,0.07);
  beep(880,0.4,'sawtooth',0.3,0.14);
}
function fanfareSound(){
  [523,659,784,1047].forEach(function(f,i){ beep(f,0.5,'triangle',0.22,i*0.13); });
}
function noiseBurst(t0, dur, vol){
  try{
    var ctx = ac();
    var n = Math.max(1, Math.floor(ctx.sampleRate*dur));
    var buf = ctx.createBuffer(1, n, ctx.sampleRate);
    var d = buf.getChannelData(0);
    for(var i=0;i<n;i++){ d[i] = (Math.random()*2-1) * (1 - i/n); }
    var src = ctx.createBufferSource(); src.buffer = buf;
    var filt = ctx.createBiquadFilter(); filt.type='bandpass'; filt.frequency.value=1800; filt.Q.value=0.8;
    var gain = ctx.createGain(); gain.gain.setValueAtTime(vol, t0);
    src.connect(filt); filt.connect(gain); gain.connect(ctx.destination);
    src.start(t0); src.stop(t0+dur);
  }catch(e){}
}
function applauseSound(){
  var ctx = ac(); var t0 = ctx.currentTime;
  for(var i=0;i<55;i++){
    var t = t0 + Math.pow(Math.random(),1.3)*2.2;
    noiseBurst(t, 0.035+Math.random()*0.04, 0.18+Math.random()*0.12);
  }
}
function bidApplauseSound(){
  try{
    var ctx = ac(); var t0 = ctx.currentTime;
    for(var i=0;i<42;i++){
      var t = t0 + Math.pow(Math.random(),1.15)*1.05;
      noiseBurst(t, 0.028+Math.random()*0.04, 0.2+Math.random()*0.14);
    }
    /* žaidybiniai „monetų“ dingai */
    beep(880,0.1,'square',0.11,0);
    beep(1175,0.12,'square',0.1,0.08);
    beep(1397,0.16,'triangle',0.12,0.16);
  }catch(e){}
}
function crowdOoohSound(options){
  options=options||{};
  var duration=options.duration||2.1, volume=options.volume||0.075;
  var ctx = ac(); var t0 = ctx.currentTime;
  [220,277,330,415].forEach(function(f){
    var osc = ctx.createOscillator(); var gain = ctx.createGain();
    osc.type='sawtooth'; osc.frequency.setValueAtTime(f*0.82, t0);
    osc.frequency.linearRampToValueAtTime(f, t0+0.45);
    var filt = ctx.createBiquadFilter(); filt.type='lowpass'; filt.frequency.value=1000;
    gain.gain.setValueAtTime(0,t0);
    gain.gain.linearRampToValueAtTime(volume, t0+0.35);
    gain.gain.linearRampToValueAtTime(volume, t0+duration*0.65);
    gain.gain.exponentialRampToValueAtTime(0.001, t0+duration);
    osc.connect(filt); filt.connect(gain); gain.connect(ctx.destination);
    osc.start(t0); osc.stop(t0+duration+0.1);
  });
}
function celebrationSound(){ crowdOoohSound(); applauseSound(); setTimeout(fanfareSound, 250); }

// ---------- kūjis + žaidimo muzika + LT vedėjas ----------
var voiceOn = localStorage.getItem('host_voice') !== '0';
var musicOn = true; // bliuzas fone visada – mygtuko UI nėra
var deskSongOn = false; /* paspausta daina — radijas tyliai, daina groja */
var deskSongN = 0;
var vilkasStageOn = false; /* įžangos viršelis kol Mindaugas neįjungia Vilko */
function getDeskSongEl(){ return document.getElementById('deskSongPlayer'); }
var deskSongNextBusy=false;
function bindDeskSongEnded(){
  var s=getDeskSongEl();
  if(!s || s._deskNextBound) return;
  s._deskNextBound=true;
  s.addEventListener('ended', function(){
    /* Pasibaigus — KITA daina, ne ta pati. Tik audio master keičia serverį. */
    if(!deskSongOn || !deskSongN) return;
    if(typeof isAudioMaster==='function' && !isAudioMaster()) return;
    if(deskSongNextBusy) return;
    deskSongNextBusy=true;
    fetch('/api/desk_song/next', {method:'POST', cache:'no-store'}).then(function(r){ return r.json(); }).then(function(d){
      deskSongNextBusy=false;
      if(d && d.ok){
        try{ applyDeskSong({desk_song: d.song || null}); }catch(e){}
      }
    }).catch(function(){ deskSongNextBusy=false; });
  });
}
function applyDeskSong(st){
  bindDeskSongEnded();
  var song = st && st.desk_song ? st.desk_song : null;
  var n = song ? (Number(song.n)||0) : 0;
  var url = song && song.url ? String(song.url) : (n ? ('/desk-songs/'+n) : '');
  if(n===deskSongN && !!n===deskSongOn){
    if(deskSongOn){
      var sKeep=getDeskSongEl();
      /* Pasibaigus NEKARTOTI tos pačios — paleisti next */
      if(sKeep && sKeep.ended){
        if(typeof isAudioMaster==='function' && isAudioMaster() && !deskSongNextBusy){
          deskSongNextBusy=true;
          fetch('/api/desk_song/next', {method:'POST', cache:'no-store'}).then(function(r){ return r.json(); }).then(function(d){
            deskSongNextBusy=false;
            if(d && d.ok) applyDeskSong({desk_song: d.song || null});
          }).catch(function(){ deskSongNextBusy=false; });
        }
        return;
      }
      if(sKeep && sKeep.paused && !(typeof stageMusicMuted==='function' && stageMusicMuted())){
        try{ var pk=sKeep.play(); if(pk&&pk.catch) pk.catch(function(){}); }catch(e){}
      }
    }
    return;
  }
  deskSongN=n;
  deskSongOn=n>0;
  var s=getDeskSongEl();
  if(!s) return;
  if(!deskSongOn){
    try{ s.pause(); s.removeAttribute('src'); s.load(); }catch(e){}
    var r=getRadioEl && getRadioEl();
    if(r){ try{ r.muted=false; r.volume=radioVolumeForCurrentState(); }catch(e){} }
    try{ if(typeof keepRadioAlive==='function') keepRadioAlive(); }catch(e){}
    return;
  }
  try{ if(typeof softPauseRadioKeepSrc==='function') softPauseRadioKeepSrc(); }catch(e){}
  var rad=getRadioEl && getRadioEl();
  if(rad){ try{ rad.muted=true; rad.volume=0; }catch(e){} }
  if(typeof stageMusicMuted==='function' && stageMusicMuted()){ try{ s.pause(); }catch(e){} return; }
  try{
    if((s.currentSrc||s.src||'').indexOf(url)<0){ s.src=url; }
    s.loop=false; /* baigėsi → kita daina (ended handler) */
    s.muted=false; s.volume=vilkasStageOn ? DESK_SONG_VOL*0.10 : (announceBusy ? DESK_SONG_VOL*MUSIC_DUCK_RATIO : DESK_SONG_VOL);
    var p=s.play(); if(p&&p.catch) p.catch(function(){});
  }catch(e){}
}
function isVilkasStageOn(){ return !!vilkasStageOn; }
function syncCoverMode(){
  try{ document.body.classList.toggle('cover-mode', !vilkasStageOn); }catch(e){}
  var btn=document.getElementById('btnVilkasStage');
  if(btn){
    btn.classList.toggle('on', !!vilkasStageOn);
    btn.textContent = vilkasStageOn ? '■ Vilkas ON — išjungti' : '▶ Įjungti Vilką';
  }
  var vu=document.getElementById('voiceUnlock');
  if(vu && vilkasStageOn) vu.textContent='🔊 Paspausk — įjungti Vilko 8 balsą';
  else if(vu) vu.textContent='🔊 Paspausk — įjungti garsą';
  try{
    if(!vilkasStageOn){
      if(typeof ensureIntroMedia==='function') ensureIntroMedia();
      else if(typeof startDiscoBeat==='function') startDiscoBeat();
    } else {
      /* F9 Vilkas ON: disco vizualas OFF, radijas tik AUDIO MASTER (1 tabas) */
      try{ if(typeof stopDiscoBeat==='function') stopDiscoBeat(); }catch(e2){}
      try{
        musicOn=true; radioArmed=true; pageAudioOk=true;
        if(isAudioMaster()){
          if(typeof keepRadioAlive==='function') keepRadioAlive();
          else if(typeof startMusic==='function') startMusic(false);
        } else {
          softPauseRadioKeepSrc();
        }
      }catch(e2){}
    }
  }catch(e){}
  try{
    if(!vilkasStageOn && typeof closeQrModal==='function') closeQrModal();
  }catch(e){}
  var vuHide=document.getElementById('voiceUnlock');
  if(vuHide && !vilkasStageOn) vuHide.classList.remove('show');
}
function setVilkasStageFromState(st){
  var next=!!(st && st.vilkas_stage_on);
  if(next===vilkasStageOn){ syncCoverMode(); return; }
  vilkasStageOn=next;
  syncCoverMode();
  setMusicDuck(vilkasStageOn);
  if(vilkasStageOn){
    try{ interruptAllSpeech(); }catch(e){}
    try{ heardWelcome=false; }catch(e){}
    try{ heardLotIntro={}; }catch(e){}
    stopIntroMediaRetry();
    try{ keepVilkasOnStage(); }catch(e){}
    try{
      musicOn=true; radioArmed=true; pageAudioOk=true;
      if(isAudioMaster() && typeof keepRadioAlive==='function') keepRadioAlive();
    }catch(e){}
    try{
      (pendingStageEvents||[]).splice(0).forEach(function(ev){ try{ handleServerEvent(ev); }catch(e2){} });
    }catch(e){}
  }
  if(!vilkasStageOn){
    try{interruptAllSpeech();}catch(e){}
    try{wolfIdle();}catch(e){}
    try{ keepVilkasOnStage(); }catch(e){}
    /* F10 → įžanga: priverstinai muzika + šokėjos (ne tik CSS cover-mode) */
    try{ if(typeof releaseRadioAnalyser==='function') releaseRadioAnalyser(); }catch(eR){}
    try{ if(typeof ensureIntroMedia==='function') ensureIntroMedia(true); }catch(eI){}
    try{ if(typeof keepDancerVideoAlive==='function') keepDancerVideoAlive(); }catch(eD){}
  }
  try{ if(typeof render==='function' && state) render(); }catch(e){}
}
(function(){
  /* Vilkas ON/OFF — TIK klaviatūra PC (F9/F10 globalus daemon). Ne Chrome. */
  var b=document.getElementById('btnVilkasStage');
  if(!b) return;
  b.onclick=function(){
    var want=!vilkasStageOn;
    var pass=prompt(want?'Įvesk admin slaptažodį — įjungti Vilką:':'Įvesk admin slaptažodį — grįžti į viršelį:');
    if(pass==null) return;
    b.disabled=true;
    fetch('/api/admin/vilkas_stage',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pass,on:want})})
      .then(function(r){ if(!r.ok) return r.json().then(function(d){ throw new Error(d.detail||'Nepavyko'); }); return r.json(); })
      .then(function(d){
        vilkasStageOn=!!d.vilkas_stage_on;
        syncCoverMode();
        if(typeof poll==='function') poll();
      })
      .catch(function(e){ alert(e.message||'Nepavyko'); })
      .finally(function(){ b.disabled=false; });
  };
})();
syncCoverMode();
var musicNodes = null;
var lastBidKey = null;
var announceBusy = false;
var announceCurrentJob = null;
var announceQueue = [];
var announceEpoch = 0;
var ltVoice = null;
var AUDIO_MASTER_KEY='vilkas_audio_master_v3';
var AUDIO_KILL_KEY='vilkas_audio_kill_v3';
var audioTabId='tab_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2);
var radioArmed=false;
var pageAudioOk=true;
var radioBus=null;
try{ radioBus=new BroadcastChannel('vilkas_audio_v3'); }catch(e){}
function isCoverMode(){
  try{ return document.body.classList.contains('cover-mode'); }catch(e){ return false; }
}
function readAudioMaster(){
  try{return JSON.parse(localStorage.getItem(AUDIO_MASTER_KEY)||'null');}catch(e){return null;}
}
function isAudioMaster(){
  /* Įžanga — VISADA master. Jokio blokavimo iš kito tabo. */
  if(isCoverMode()) return true;
  var m=readAudioMaster();
  return !!(m && m.id===audioTabId && Date.now()-Number(m.at||0)<7000);
}
function shoutKillOthers(){
  /* Įžangoje NEŽUDYTI kitų — jokių blokavimų */
  if(isCoverMode()) return;
  try{ localStorage.setItem(AUDIO_KILL_KEY, JSON.stringify({id:audioTabId,at:Date.now()})); }catch(e){}
  try{ if(radioBus) radioBus.postMessage({type:'kill',id:audioTabId}); }catch(e){}
}
function otherHoldsMaster(){
  if(isCoverMode()) return false;
  try{
    var m=readAudioMaster();
    return !!(m && m.id && m.id!==audioTabId && (Date.now()-Number(m.at||0))<7000);
  }catch(e){ return false; }
}
function claimAudioMaster(force){
  if(isCoverMode()){
    try{localStorage.setItem(AUDIO_MASTER_KEY,JSON.stringify({id:audioTabId,at:Date.now()}));}catch(e){}
    return true;
  }
  if(!force && otherHoldsMaster()) return false;
  shoutKillOthers();
  try{localStorage.setItem(AUDIO_MASTER_KEY,JSON.stringify({id:audioTabId,at:Date.now()}));}catch(e){}
  return isAudioMaster();
}
function releaseAudioMaster(){
  if(isCoverMode()) return;
  try{
    var m=readAudioMaster();
    if(m && m.id===audioTabId) localStorage.removeItem(AUDIO_MASTER_KEY);
  }catch(e){}
}
function pageAllowsAudio(){
  try{
    if(document.visibilityState==='hidden') return false;
    return !!pageAudioOk;
  }catch(e){ return true; }
}
function softPauseRadioKeepSrc(){
  /* Pauzė BE src wipe — grįžus garsas iškart */
  try{
    var el=document.getElementById('vilkasRadioPlayer');
    if(el && !el.paused) el.pause();
  }catch(e){}
}
/* Mindaugas 2026-10-08: Vilko scenoje (F9) muzika OFF — nemaišo balsui/bajeriams/telefonui/gitarai.
   Tik soft pause + mute, src NEliečiamas; F10 įžangoje radijas grįžta. */
var STAGE_MUSIC_OFF = true;
/* Įžangoje radijas ON; F9 scenoje tyli (STAGE_MUSIC_OFF). MUSIC_OFF_ALL=true = tyli ir įžanga. */
/* Praktika (practice_bots): muzika ON scenoje — Vilkas girdi ir mokosi padainuoti. */
var MUSIC_OFF_ALL = false;
var practiceModeOn = false;
function stageMusicMuted(){
  return !!MUSIC_OFF_ALL;
}
function radioVolumeForCurrentState(){
  if(stageMusicMuted()) return 0;
  if(vilkasStageOn) return radioTargetVol*0.10;
  return announceBusy ? radioDuckVol : radioTargetVol;
}
function muteMusicForStage(){
  softPauseRadioKeepSrc();
  try{
    var el=document.getElementById('vilkasRadioPlayer');
    if(el){ el.muted=true; el.volume=0; }
  }catch(e){}
  try{
    var ds=document.getElementById('deskSongPlayer');
    if(ds && !ds.paused) ds.pause();
  }catch(e){}
}
function hardKillRadio(){
  /* Įžangoje IR Vilko scenoje (F9) DRAUDŽIAMA naikinti srautą — tik soft pause */
  if(isCoverMode() || vilkasStageOn){ softPauseRadioKeepSrc(); radioStarting=false; return; }
  radioStarting=false;
  try{ if(typeof stopEnergyWatch==='function') stopEnergyWatch(); }catch(e){}
  try{ if(typeof stopDiscoBeat==='function') stopDiscoBeat(); }catch(e){}
  releaseRadioAnalyser();
  var el=document.getElementById('vilkasRadioPlayer');
  if(!el) return;
  try{
    el.pause();
    el.onplaying=null;
    el.onerror=null;
    el.removeAttribute('src');
    el.load();
  }catch(e){}
}
function silenceThisTab(){
  /* Įžanga: JOKIO blokavimo / kill iš kitų tabų */
  if(isCoverMode()) return;
  try{interruptAllSpeech();}catch(e){
    try{if(hostAudio){hostAudio.pause();hostAudio=null;}}catch(e2){}
    try{if(phoneRingAudio){phoneRingAudio.pause();phoneRingAudio=null;}}catch(e2){}
    try{if(window.speechSynthesis)speechSynthesis.cancel();}catch(e2){}
  }
  try{hardKillRadio();}catch(e){}
}
function onPageAudioSuspend(){
  pageAudioOk=false;
  if(isCoverMode()){
    softPauseRadioKeepSrc();
    return;
  }
  silenceThisTab();
  releaseAudioMaster();
}
function onPageAudioResume(){
  if(document.visibilityState==='hidden') return;
  pageAudioOk=true;
  try{ if(isCoverMode() && typeof ensureIntroMedia==='function') ensureIntroMedia(); }catch(e){}
  try{
    if(vilkasStageOn && musicOn && isAudioMaster()){
      if(typeof keepRadioAlive==='function') keepRadioAlive();
    }
  }catch(e){}
}
setInterval(function(){
  if(document.visibilityState==='hidden'){
    if(isCoverMode()){ softPauseRadioKeepSrc(); return; }
    if(pageAudioOk) onPageAudioSuspend();
    else { try{hardKillRadio();}catch(e){} }
    return;
  }
  pageAudioOk=true;
  /* Įžanga: visada muzika. Vilkas scenoje: muzika TIK audio-master tab'e (kad balsas nesidubliuotų). */
  if(deskSongOn){
    try{ keepRadioAlive(); }catch(e){}
    return;
  }
  if(musicOn && isCoverMode()){
    claimAudioMaster(true);
    try{ keepRadioAlive(); }catch(e){}
  } else if(musicOn && vilkasStageOn){
    if(isAudioMaster()){
      try{ localStorage.setItem(AUDIO_MASTER_KEY,JSON.stringify({id:audioTabId,at:Date.now()})); }catch(e){}
      try{ keepRadioAlive(); }catch(e){}
    } else {
      try{ softPauseRadioKeepSrc(); }catch(e){}
      announceQueue=[]; announceBusy=false; announceCurrentJob=null;
    }
  } else if(isAudioMaster()){
    try{localStorage.setItem(AUDIO_MASTER_KEY,JSON.stringify({id:audioTabId,at:Date.now()}));}catch(e){}
  } else if(otherHoldsMaster()){
    try{hardKillRadio();}catch(e){}
  }
},700);
window.addEventListener('storage',function(e){
  if(isCoverMode()) return; /* jokių kill/master blokų įžangoje */
  if(e.key===AUDIO_MASTER_KEY && !isAudioMaster()) silenceThisTab();
  if(e.key===AUDIO_KILL_KEY){
    try{
      var k=JSON.parse(e.newValue||'null');
      if(k && k.id && k.id!==audioTabId) silenceThisTab();
    }catch(err){}
  }
});
try{
  if(radioBus) radioBus.onmessage=function(ev){
    if(isCoverMode()) return;
    var d=ev && ev.data;
    if(d && d.type==='kill' && d.id!==audioTabId) silenceThisTab();
  };
}catch(e){}
document.addEventListener('visibilitychange',function(){
  if(document.visibilityState==='hidden') onPageAudioSuspend();
  else onPageAudioResume();
});
window.addEventListener('pagehide',function(){ onPageAudioSuspend(); });
window.addEventListener('freeze',function(){ onPageAudioSuspend(); });

function unlockAudio(ev){
  if(document.visibilityState==='hidden') return;
  try{
    if(ev && ev.target && ev.target.closest && ev.target.closest('[data-radio]')) return;
  }catch(e){}
  pageAudioOk=true;
  radioArmed=true;
  musicOn=true;
  claimAudioMaster(true);
  try{
    var c=ac();
    if(c.state==='suspended') c.resume();
  }catch(e){}
  if(window.speechSynthesis) speechSynthesis.getVoices();
  try{ makeRadioAudibleNow(); }catch(e){}
  var vb=document.getElementById('voiceUnlock');
  if(vb && isCoverMode()) vb.classList.remove('show');
}
document.addEventListener('pointerdown', unlockAudio, {once:false, capture:true});
document.addEventListener('click', unlockAudio, {once:false, capture:true});
document.addEventListener('touchstart', unlockAudio, {once:false, capture:true});
document.addEventListener('keydown', unlockAudio, {once:false, capture:true});
/* scroll / wheel — Chrome neleidžia autoplay, bet kartais padeda AudioContext */
document.addEventListener('wheel', function(){ try{ var c=ac(); if(c.state==='suspended') c.resume(); }catch(e){} }, {passive:true, capture:true});

/* Paštas / tel — be Windows „How do you want to open this?“ (mailto be pašto programos) */
(function(){
  var GMAIL='https://mail.google.com/mail/?view=cm&fs=1&to=mindaugasbusiness@gmail.com&su=Penktadienio%20aukcionas';
  var TEL='tel:+37066331913';
  var PHONE='+37066331913';
  var lastAt=0, lastKey='';
  function isPhoneLike(){
    try{
      if(navigator.userAgentData && navigator.userAgentData.mobile) return true;
    }catch(e){}
    var touch=(navigator.maxTouchPoints||0)>0;
    var narrow=Math.min(screen.width||0,screen.height||0)<=920;
    return touch && narrow;
  }
  function toast(msg){
    var el=document.getElementById('contactToast');
    if(!el){
      el=document.createElement('div');
      el.id='contactToast';
      document.body.appendChild(el);
    }
    el.textContent=msg;
    el.classList.add('show');
    clearTimeout(toast._t);
    toast._t=setTimeout(function(){ el.classList.remove('show'); }, 2800);
  }
  function openContactLink(e){
    try{
      var t=e.target;
      if(!t || !t.closest) return;
      var a=t.closest('#discoMailLink, #discoTelLink, #discoContacts a.disco-contact-a, .aqr-contact a, .contact-line a');
      if(!a) return;
      var href=(a.getAttribute('href')||'').trim();
      var isMail=a.id==='discoMailLink' || /mailto:|mail\.google\.com/i.test(href) || /@/.test(a.textContent||'');
      var isTel=a.id==='discoTelLink' || /^tel:/i.test(href) || a.hasAttribute('data-phone');
      if(!isMail && !isTel) return;
      var key=isTel?'tel':'mail';
      var now=Date.now();
      if(key===lastKey && (now-lastAt)<900){ e.preventDefault(); e.stopPropagation(); return; }
      lastAt=now; lastKey=key;
      e.preventDefault();
      e.stopPropagation();
      if(isMail){
        /* HTTPS Gmail rašymas — veikia Chrome/Edge be pašto programos */
        window.open(GMAIL, '_blank', 'noopener');
        return;
      }
      if(isPhoneLike()){
        window.location.href=TEL;
        return;
      }
      /* PC: tel: kelia Windows dialogo — kopijuojam numerį */
      var num=a.getAttribute('data-phone')||PHONE;
      if(navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(num).then(function(){
          toast('Numeris nukopijuotas: '+num+' — skambinkite arba įklijuokite į Phone Link');
        }).catch(function(){ toast('Tel.: '+num); });
      }else{
        toast('Tel.: '+num);
      }
    }catch(err){}
  }
  document.addEventListener('click', openContactLink, true);
})();

function pickLtVoice(){
  if(!window.speechSynthesis) return null;
  var voices = speechSynthesis.getVoices()||[];
  return voices.find(function(v){return /^lt/i.test(v.lang);})
    || voices.find(function(v){return /lithuan|lietuvi/i.test(v.name);})
    || voices.find(function(v){return /Google.*(lt|Lith)/i.test(v.name);})
    || null;
}
if(window.speechSynthesis){
  speechSynthesis.onvoiceschanged = function(){ ltVoice = pickLtVoice(); };
  ltVoice = pickLtVoice();
}

function hammerSound(){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    var osc=ctx.createOscillator(), g=ctx.createGain();
    osc.type='sine';
    osc.frequency.setValueAtTime(140,t0);
    osc.frequency.exponentialRampToValueAtTime(45,t0+0.22);
    g.gain.setValueAtTime(0.001,t0);
    g.gain.linearRampToValueAtTime(0.55,t0+0.015);
    g.gain.exponentialRampToValueAtTime(0.001,t0+0.35);
    osc.connect(g); g.connect(ctx.destination);
    osc.start(t0); osc.stop(t0+0.4);
    noiseBurst(t0, 0.08, 0.35);
    noiseBurst(t0+0.02, 0.05, 0.2);
  }catch(e){}
}
var gongAudio = null;
var gongTimer = null;
function gongSoundSynth(){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    var out=ctx.createGain(); out.gain.value=0.62; out.connect(ctx.destination);
    [[78,1.15,6.2],[98,1,5.5],[146,.75,4.8],[196,.55,4.2],[247,.42,3.5],[311,.32,2.8],[392,.22,2.1],[523,.16,1.5]].forEach(function(p){
      var o=ctx.createOscillator(), g=ctx.createGain();
      o.type='sine';
      o.frequency.setValueAtTime(p[0]*1.04, t0);
      o.frequency.exponentialRampToValueAtTime(p[0], t0+0.35);
      var lfo=ctx.createOscillator(), lg=ctx.createGain(); lfo.frequency.value=2.6+Math.random()*1.8; lg.gain.value=p[0]*0.005;
      lfo.connect(lg); lg.connect(o.frequency); lfo.start(t0); lfo.stop(t0+p[2]);
      g.gain.setValueAtTime(0.0001,t0);
      g.gain.exponentialRampToValueAtTime(p[1],t0+0.018);
      g.gain.exponentialRampToValueAtTime(0.0001,t0+p[2]);
      o.connect(g); g.connect(out); o.start(t0); o.stop(t0+p[2]+0.1);
    });
    noiseBurst(t0, 0.14, 0.55);
    noiseBurst(t0+0.03, 0.08, 0.28);
  }catch(e){}
}
function gongSound(){
  /* ElevenLabs brass/auction gong — pirkimas / vilko gongo smūgis */
  try{
    if(gongAudio){ try{ gongAudio.pause(); }catch(e0){} gongAudio=null; }
    var a=new Audio('/photos/vilkas_gong.mp3?v=1');
    a.volume=0.92;
    gongAudio=a;
    var p=a.play();
    if(p&&p.catch){ p.catch(function(){ gongSoundSynth(); }); }
    return;
  }catch(e){ gongSoundSynth(); }
}
function hitGong(){
  try{ hammerStrike(); }catch(e){}
  clearTimeout(gongTimer);
  gongTimer=setTimeout(function(){ gongTimer=null; try{ gongSound(); }catch(e2){} }, 55);
}
/* Tikroviškas telefonas: MP3 skambutis + vibracija */
var phoneRingAudio = null;
function phoneRingSynth(rings){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    rings = rings || 2;
    for(var r=0;r<rings;r++){
      var start=t0 + r*1.15;
      [440,480].forEach(function(freq){
        var o=ctx.createOscillator(), g=ctx.createGain();
        o.type='sine'; o.frequency.value=freq;
        g.gain.setValueAtTime(0.0001, start);
        g.gain.linearRampToValueAtTime(0.28, start+0.03);
        g.gain.setValueAtTime(0.28, start+0.55);
        g.gain.exponentialRampToValueAtTime(0.0001, start+0.72);
        o.connect(g); g.connect(ctx.destination);
        o.start(start); o.stop(start+0.8);
      });
      /* vibracijos „buzz“ */
      var n=ctx.createBufferSource(), nb=ctx.createBuffer(1, Math.floor(ctx.sampleRate*0.7), ctx.sampleRate);
      var ch=nb.getChannelData(0);
      for(var i=0;i<ch.length;i++) ch[i]=(Math.random()*2-1)*0.4;
      n.buffer=nb;
      var ng=ctx.createGain(), filt=ctx.createBiquadFilter();
      filt.type='bandpass'; filt.frequency.value=180; filt.Q.value=4;
      ng.gain.setValueAtTime(0.0001, start);
      ng.gain.linearRampToValueAtTime(0.35, start+0.05);
      ng.gain.exponentialRampToValueAtTime(0.0001, start+0.7);
      n.connect(filt); filt.connect(ng); ng.connect(ctx.destination);
      n.start(start); n.stop(start+0.75);
    }
  }catch(e){}
}
function phoneVibratePulse(){
  try{
    if(navigator.vibrate){
      /* skambutis: vibr-vibr — pauzė — vibr-vibr */
      navigator.vibrate([220,80,220,400,220,80,220]);
    }
  }catch(e){}
  try{
    var pop=document.getElementById('wolfPop');
    if(pop){
      pop.classList.add('phone-ring');
      setTimeout(function(){ pop.classList.remove('phone-ring'); }, 2600);
    }
  }catch(e2){}
}
function phoneRingSound(){
  if(!pageAllowsAudio() || !isAudioMaster()) return;
  phoneVibratePulse();
  try{
    if(phoneRingAudio){ try{ phoneRingAudio.pause(); }catch(e0){} phoneRingAudio=null; }
    var a=new Audio('/photos/vilkas_phone_ring.mp3?v=1');
    a.volume=0.95;
    phoneRingAudio=a;
    var p=a.play();
    if(p&&p.catch){ p.catch(function(){ if(pageAllowsAudio()) phoneRingSynth(2); }); }
    return;
  }catch(e){ phoneRingSynth(2); }
}
var phoneTradeTimer = null;
var phoneSpeechTimer = null;
var phoneCallActive = false, phoneCallSince = 0;
var phoneSessionActive = false;
var phoneBidHold = []; /* [{name,amount,at}] — kas kėlė kol Vilkas telefone */
function setPhoneCallActive(v){ phoneCallActive=!!v; phoneCallSince=v?Date.now():0; }
function isPhoneBusy(){
  if(phoneSessionActive || phoneCallActive || phoneAway) return true;
  if(phoneSpeechTimer || phoneAwayTimer) return true;
  if(announceBusy && announceCurrentJob && (announceCurrentJob.tag==='phone'||announceCurrentJob.tag==='phone_catchup')) return true;
  try{ if(announceQueueHasTag('phone')||announceQueueHasTag('phone_catchup')) return true; }catch(e){}
  return false;
}
var phoneAway=false, phoneAwayTimer=null;
function beginPhoneSession(){
  phoneSessionActive=true;
  phoneBidHold=[];
  setPhoneCallActive(true);
}
function phoneExcuseLine(){
  return pickNR('phoneExcuse',[
    'Atsiprašau, žmonės — aš trumpai einu pakalbėti.',
    'Atsiprašau, žmonės! Telefonas — trumpam nuklysiu pakalbėti.',
    'Žmonės, atsiprašau — skambutis, einu trumpai pakalbėti.'
  ]);
}
function phoneBossReturnLine(){
  return pickNR('phoneBossReturn',[
    'Viršininkas skambino, sako… O o — kas yra, ko neperka žmonės?',
    'Viršininkas skambino! Sako — o o, kas yra, ko neperka žmonės?',
    'Buvo viršininkas. Sako: o o, kas čia — ko žmonės neperka?',
    'Viršininkas skambino, klausia… O o kas yra, ko neperka žmonės?'
  ]);
}
function hideVilkasPhoneAway(){
  /* F11: Vilkas dingsta į dūmus net scenoje (phoneAway) — keepVilkasOnStage neliečia. */
  phoneAway=true;
  try{ clearTimeout(wolfHideTimer); }catch(e){}
  try{ setBubble('', ''); }catch(e){}
  try{ stopGestures(); }catch(e){}
  try{
    var pop=document.getElementById('wolfPop');
    if(pop){
      pop.classList.remove('talking','lean','coffee','side','idle','alive','show','has-video');
      pop.classList.add('hide');
    }
  }catch(e){}
  /* Priverstiniai dūmai — enterSmokeBreak kitaip gali return dėl announceBusy. */
  try{
    wolfInSmoke=true;
    var field=document.getElementById('smokeField');
    if(field) field.classList.add('on');
    puffSmoke(5);
  }catch(e){}
}
function showVilkasAfterPhone(){
  phoneAway=false;
  try{ clearSmoke(); }catch(e){}
  try{ wolfPopShow('glasses'); }catch(e){}
}
function phoneCatchupLine(names){
  var list='';
  try{
    var uniq=[];
    for(var i=0;i<(names||[]).length;i++){
      var n=String(names[i]||'').trim().split(/\s+/)[0];
      if(!n) continue;
      var low=n.toLowerCase();
      var seen=false;
      for(var j=0;j<uniq.length;j++){ if(uniq[j].toLowerCase()===low){ seen=true; break; } }
      if(!seen) uniq.push(n);
    }
    if(!uniq.length) return '';
    if(uniq.length===1) list=uniq[0];
    else if(uniq.length===2) list=uniq[0]+' ir '+uniq[1];
    else list=uniq.slice(0,-1).join(', ')+' ir '+uniq[uniq.length-1];
  }catch(e){ return ''; }
  return pickNR('phoneCatchup',[
    'O kol kalbėjau telefonu, pakėlė '+list+'. Šaunuoliai!',
    'Kol buvau telefone — '+list+' pakėlė. Kas dar?',
    'Atsiprašau, telefonas… O tuo metu pakėlė '+list+'! Šaunuoliai, šaunuoliai!',
    'Alio baigta. Kol aš telefone, pakėlė '+list+'. Nestabdom!',
    'Oho — kol telefonavau, '+list+' jau spaudė! Brawo!'
  ]);
}
function endPhoneSessionAndCatchup(){
  setPhoneCallActive(false);
  phoneAway=false;
  try{ clearTimeout(phoneAwayTimer); phoneAwayTimer=null; }catch(e){}
  var held=phoneBidHold.slice();
  phoneBidHold=[];
  var names=[];
  for(var i=0;i<held.length;i++) names.push(held[i].name);
  var catchup=phoneCatchupLine(names);
  function finishPhoneSession(){
    phoneSessionActive=false;
  }
  function afterBoss(){
    if(!catchup){ finishPhoneSession(); return; }
    queueAnnounce(catchup,{
      tag:'phone_catchup', priority:true, pose:'raise', bangs:0, fast:true, fx:'cheer',
      gestures:['raise','thumb','clap'], gestureMs:340,
      bubble:'📞→🔔 Kol telefone…',
      onDone:function(){ try{ finishPhoneSession(); }catch(e){} }
    });
  }
  /* Sesija lieka ON kol baigsis viršininkas (+ catchup) — kitaip bid'ai perkerta balsą. */
  try{ if(typeof claimAudioMaster==='function') claimAudioMaster(true); }catch(eM){}
  queueAnnounce(phoneBossReturnLine(),{
    tag:'phone', priority:true, pose:'glasses', bangs:0, fast:true,
    gestures:['glasses','raise','thumb'], bubble:'📞 Viršininkas…',
    onDone:function(){ try{ afterBoss(); }catch(e){ finishPhoneSession(); } }
  });
}
function holdBidDuringPhone(name, amount){
  /* Gongas+burbulas OK; balsas — NE (tik catchup po skambučio). */
  var nm=String(name||'Dalyvis').trim()||'Dalyvis';
  var am=Number(amount)||0;
  try{ hitGong(); }catch(e){}
  try{ cheerBurst(); }catch(e){}
  try{ setBubble('🔔 '+nm+' → '+Math.round(am)+' €', ''); }catch(e){}
  /* Naujesnis to paties vardo — pakeičia seną */
  var low=nm.toLowerCase();
  for(var i=phoneBidHold.length-1;i>=0;i--){
    if(String(phoneBidHold[i].name||'').toLowerCase()===low) phoneBidHold.splice(i,1);
  }
  phoneBidHold.push({name:nm, amount:am, at:Date.now()});
}
/* Savigyda: skambučio vėliava negali kabėti — kitaip F11 / eilė miršta.
   Sesijos metu (F11) — ilgesnis limitas; catchup po onDone. */
setInterval(function(){
  if(!phoneCallActive || !phoneCallSince) return;
  var age=Date.now()-phoneCallSince;
  var softLimit=phoneSessionActive?90000:8000;
  var hardLimit=phoneSessionActive?120000:20000;
  if(age>hardLimit){
    setPhoneCallActive(false);
    if(phoneSessionActive){ try{ endPhoneSessionAndCatchup(); }catch(e){ phoneSessionActive=false; phoneBidHold=[]; } }
    return;
  }
  if(age>softLimit && !announceBusy && !hostAudio && !phoneSpeechTimer){
    setPhoneCallActive(false);
    if(phoneSessionActive){ try{ endPhoneSessionAndCatchup(); }catch(e){ phoneSessionActive=false; phoneBidHold=[]; } }
  }
}, 1000);
/* Gitaros riffas (WebAudio) turi savo master gain — kad interrupt jį nutildytų, o ne grotų po balsu. */
var riffMaster=null;
function stopGuitarRiff(){
  try{
    if(!riffMaster) return;
    var m=riffMaster; riffMaster=null; var t=m.context.currentTime;
    m.gain.cancelScheduledValues(t); m.gain.setValueAtTime(m.gain.value,t); m.gain.linearRampToValueAtTime(0.0001,t+0.15);
    setTimeout(function(){ try{ m.disconnect(); }catch(e){} },260);
  }catch(e){}
}
function playPhoneCallGag(kind){
  /* Skambutis: tyla komentarams; po Alio — catchup kas pakėlė. */
  if(phoneCallActive || phoneSessionActive || hostAudio || announceBusy || announceQueue.length) return;
  beginPhoneSession();
  try{ phoneRingSound(); }catch(e){}
  clearTimeout(phoneSpeechTimer);
  phoneSpeechTimer=setTimeout(function(){
    phoneSpeechTimer=null;
    try{
      if(phoneRingAudio){ phoneRingAudio.pause(); phoneRingAudio.currentTime=0; phoneRingAudio=null; }
      if(navigator.vibrate) navigator.vibrate(0);
    }catch(e1){}
    try{ if(navigator.vibrate) navigator.vibrate(0); }catch(e1){}
    setPhoneCallActive(false);
    try{ if(typeof claimAudioMaster==='function') claimAudioMaster(true); }catch(eM){}
    var line;
    if(kind==='trade'){
      line=pick([
        'Alio, alio! Aš blogai tave girdžiu — aš judesyje, perk telefonus!',
        'Alio, alio! Blogai girdžiu! Aš judesyje — telefonų prekyba, netrukdyk!',
        'Alio, alio! Aš judesyje, perk telefonus — blogai tave girdžiu, paskui!'
      ]);
    } else {
      line=pick([
        'Alio, alio! Aš darbe — kaip kokiam darbe? Penktadienio aukcione! Prekyba, prekyba užsiėmu — gerai, netrukdyk!',
        'Alio, alio! Gerai, aš perskambinsiu. Netrukdyk!',
        'Alio, alio! Aš darbe, Penktadienio aukcione — prekyba užsiėmu. Gerai, netrukdyk!'
      ]);
    }
    queueAnnounce(line, {
      tag:'phone', pose:'glasses', bangs:0,
      gestures:['glasses','wink','raise'],
      bubble: kind==='trade' ? '📞 Alio! Judesyje…' : '📞 Alio, alio!',
      onDone:function(){ try{ endPhoneSessionAndCatchup(); }catch(e){} }
    });
  }, 2700);
}
function scheduleTradePhoneCall(){
  clearTimeout(phoneTradeTimer);
  /* Retas trečias pokalbis: tik po tikro pakėlimo ir tik pasibaigus balsui. */
  if(Math.random() > 0.28) return;
  phoneTradeTimer=setTimeout(function waitForQuiet(){
    if(hostAudio || phoneCallActive || announceBusy || announceQueue.length){
      phoneTradeTimer=setTimeout(waitForQuiet, 1200);
      return;
    }
    playPhoneCallGag('trade');
  }, 6500);
}
function isFemaleName(name){
  var w=String(name||'').trim().split(/\s+/)[0].toLowerCase();
  if(!w) return false;
  if(/(as|is|ys|us|ius|jus)$/.test(w)) return false;
  return /(a|ė|e|ia|ija)$/.test(w);
}
function vocative(name){
  var w=String(name||'').trim().split(/\s+/)[0];
  if(/ius$/i.test(w)) return w.replace(/ius$/i,'iau');
  if(/as$/i.test(w)) return w.replace(/as$/i,'ai');
  if(/is$/i.test(w)) return w.replace(/is$/i,'i');
  if(/ys$/i.test(w)) return w.replace(/ys$/i,'y');
  if(/us$/i.test(w)) return w.replace(/us$/i,'au');
  if(/ė$/i.test(w)) return w.replace(/ė$/i,'e');
  return w;
}
/* Vienas mėlynas Vilkas; gestų judesiai lieka CSS, be skirtingų personažų suliejimo. */
var WOLF_POSES={raise:'/photos/vilkas_blue_pose.webp',bang:'/photos/vilkas_blue_pose.webp',welcome:'/photos/vilkas_blue_pose.webp',bow:'/photos/vilkas_blue_pose.webp',wink:'/photos/vilkas_blue_pose.webp',thumb:'/photos/vilkas_blue_pose.webp',coffee:'/photos/vilkas_blue_pose.webp',present:'/photos/vilkas_blue_pose.webp',clap:'/photos/vilkas_blue_pose.webp',spill:'/photos/vilkas_blue_pose.webp',glasses:'/photos/vilkas_blue_pose.webp',guitar:'/photos/vilkas_blue_pose.webp',guitar2:'/photos/vilkas_blue_pose.webp'};
var WOLF_POSES_ORIG={raise:'/photos/vilkas_raise.webp',bang:'/photos/vilkas_bang.webp',welcome:'/photos/vilkas_welcome.webp',bow:'/photos/vilkas_bow.webp',wink:'/photos/vilkas_wink.webp',thumb:'/photos/vilkas_thumb.webp',coffee:'/photos/vilkas_coffee.webp',present:'/photos/vilkas_present.webp',clap:'/photos/vilkas_clap.webp',spill:'/photos/vilkas_spill.webp',glasses:'/photos/vilkas_glasses.webp',guitar:'/photos/vilkas_guitar.webp',guitar2:'/photos/vilkas_guitar2.webp'};
try{ var _wvb=String(window.PAGE_BUILD||'1'); Object.keys(WOLF_POSES).forEach(function(k){ WOLF_POSES[k]+='?v='+_wvb; }); }catch(e){}
Object.keys(WOLF_POSES).forEach(function(k){ var i=new Image(); i.src=WOLF_POSES[k]; });
var wolfHideTimer=null;
var currentPose='raise', gestureTimer=null;
function setPose(p){
  var src=WOLF_POSES[p]||WOLF_POSES.raise;
  var a=document.getElementById('hostWolfImg'), b=document.getElementById('wolfPopImg'), g=document.getElementById('wolfPopGhost');
  if(a) a.src=src;
  /* has-video (anim) režime #wolfPopImg matomas TIK tyloje — ten visada p1 (ta pati apranga, užčiaupta burna).
     Pozų still'ai keičiami tik be animacijos (fallback), kad nebūtų smokingo/kostiumo mirgėjimo. */
  try{ var popHV=document.getElementById('wolfPop'); if(popHV && popHV.classList.contains('has-video')){ src=WOLF_POSES.raise; } }catch(e){}
  if(b && currentPose!==p && b.getAttribute('src')!==src){
    if(g){ g.src=b.src; restartClass(g,'fade'); }
    b.classList.remove('swap','swap-up'); void b.offsetWidth;
    b.src=src;
    b.classList.add(p==='raise'||p==='clap'||p==='glasses' ? 'swap-up' : 'swap');
  }
  currentPose=p;
}
function setBubble(title, speech){
  var t=document.getElementById('wolfBubT'), s=document.getElementById('wolfBubS');
  if(t && title!=null) t.textContent=title;
  if(s && speech!=null){
    s.innerHTML='';
    speech.split(/\s+/).filter(Boolean).forEach(function(w, i){
      var sp=document.createElement('span'); sp.textContent=(i?' ':'')+w; s.appendChild(sp);
    });
  }
  var b=document.getElementById('wolfPopBubble');
  if(b){
    var blank=!(t&&t.textContent) && !(s&&s.textContent);
    b.classList.toggle('blank', blank);
    if(!blank && speech!=null && speech) restartClass(b,'pop');
  }
}
function revealWords(frac){
  var s=document.getElementById('wolfBubS'); if(!s) return;
  var sp=s.children, total=0, i;
  for(i=0;i<sp.length;i++) total+=sp[i].textContent.length+1;
  var target=Math.min(1, frac+0.04)*total, acc=0;
  for(i=0;i<sp.length;i++){ acc+=sp[i].textContent.length+1; sp[i].classList.toggle('on', acc-((sp[i].textContent.length+1)*0.4)<=target); }
}
function setNoAudio(on){ var b=document.getElementById('wolfPopBubble'); if(b) b.classList.toggle('noaudio', !!on); }
var CLAP=['welcome','clap','welcome','clap','welcome','clap'];
function clapSound(){
  try{ var t=ac().currentTime; noiseBurst(t, 0.05, 0.55); noiseBurst(t+0.012, 0.03, 0.3); }catch(e){}
}
function startGestures(list, ms){
  stopGestures();
  if(!list || list.length<2) return;
  var i=0;
  var pop=document.getElementById('wolfPop'); if(pop) pop.classList.add('lean');
  if(list[0]==='clap') clapSound();
  gestureTimer=setInterval(function(){
    i=(i+1)%list.length; setPose(list[i]);
    if(list[i]==='clap') clapSound();
  }, Math.max(600, ms || (list.indexOf('clap')>=0 ? 600 : 1000)));
}
function fanfareIntro(){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    for(var i=0;i<34;i++){
      var tt=t0+i*0.065;
      noiseBurst(tt, 0.05, 0.08+0.3*(i/34));
    }
    var boom=ctx.createOscillator(), bg=ctx.createGain();
    boom.type='sine'; boom.frequency.setValueAtTime(90,t0+2.2); boom.frequency.exponentialRampToValueAtTime(40,t0+2.9);
    bg.gain.setValueAtTime(0.0001,t0+2.2); bg.gain.linearRampToValueAtTime(0.6,t0+2.23); bg.gain.exponentialRampToValueAtTime(0.0001,t0+3.1);
    boom.connect(bg); bg.connect(ctx.destination); boom.start(t0+2.2); boom.stop(t0+3.2);
    var notes=[[2.25,.16,[392,494,587]],[2.45,.16,[392,494,587]],[2.65,.16,[392,494,587]],[2.85,1.1,[523,659,784,1047]]];
    notes.forEach(function(n){
      n[2].forEach(function(f){
        var o=ctx.createOscillator(), g=ctx.createGain(), lp=ctx.createBiquadFilter();
        o.type='sawtooth'; o.frequency.value=f; lp.type='lowpass'; lp.frequency.value=2400;
        var s=t0+n[0];
        g.gain.setValueAtTime(0.0001,s); g.gain.linearRampToValueAtTime(0.07,s+0.03); g.gain.setValueAtTime(0.07,s+n[1]*0.7); g.gain.exponentialRampToValueAtTime(0.0001,s+n[1]+0.15);
        o.connect(lp); lp.connect(g); g.connect(ctx.destination); o.start(s); o.stop(s+n[1]+0.2);
      });
    });
    setTimeout(function(){ try{ showCymbal(); }catch(e){} }, 2850);
  }catch(e){}
}
function teapotPourSound(){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    var o=ctx.createOscillator(), g=ctx.createGain();
    o.type='sine'; o.frequency.setValueAtTime(1900,t0); o.frequency.linearRampToValueAtTime(2300,t0+0.9);
    g.gain.setValueAtTime(0.0001,t0); g.gain.linearRampToValueAtTime(0.05,t0+0.3); g.gain.linearRampToValueAtTime(0.0001,t0+0.9);
    o.connect(g); g.connect(ctx.destination); o.start(t0); o.stop(t0+1);
    for(var i=0;i<26;i++){
      var tt=t0+1.0+i*0.07+Math.random()*0.03;
      var b=ctx.createOscillator(), bg=ctx.createGain();
      b.type='sine'; var f=300+Math.random()*500+i*18;
      b.frequency.setValueAtTime(f,tt); b.frequency.exponentialRampToValueAtTime(f*1.8,tt+0.05);
      bg.gain.setValueAtTime(0.0001,tt); bg.gain.linearRampToValueAtTime(0.09,tt+0.01); bg.gain.exponentialRampToValueAtTime(0.0001,tt+0.07);
      b.connect(bg); bg.connect(ctx.destination); b.start(tt); b.stop(tt+0.08);
    }
    setTimeout(coffeeSound, 900);
  }catch(e){}
}
function splashSound(){
  try{ var t=ac().currentTime; noiseBurst(t, 0.35, 0.6); noiseBurst(t+0.1, 0.25, 0.35); beep(300,0.25,'sine',0.15,0); beep(180,0.3,'sine',0.12,0.05); }catch(e){}
}
var coffeeActive=false, coffeeTimer=null;
var coffeeIntermissionLotId=null;
function showTable(on){
  var t=document.getElementById('wolfTable'); if(!t) return;
  if(on){ t.classList.remove('hide'); restartClass(t,'show'); }
  else if(t.classList.contains('show')){ t.classList.remove('show'); restartClass(t,'hide'); }
}
function startCoffee(){
  coffeeActive=true; showTable(true);
  setTimeout(teapotPourSound, 500);
  clearTimeout(coffeeTimer);
  /* Trumpai kava → tada dingsta į dūmus */
  coffeeTimer=setTimeout(function(){ endCoffee(); wolfPopHideSoon(200); }, 6500);
}
function startOpeningCoffee(ms){
  /* Po welcome: Vilkas geria kavą, MUZIKA groja, JOKIŲ komentarų ~2 min. */
  coffeeActive=true; showTable(true);
  try{ setTimeout(teapotPourSound, 400); }catch(e){}
  try{ setPose('coffee'); }catch(e){}
  try{
    var pop=document.getElementById('wolfPop');
    if(pop){ pop.classList.add('show','alive','coffee'); pop.classList.remove('talking','hide'); }
  }catch(e){}
  try{ setBubble('☕ Kavos pertraukėlė…', ''); }catch(e){}
  clearTimeout(coffeeTimer);
  coffeeTimer=setTimeout(function(){
    endCoffee();
    try{ if(vilkasStageOn) wolfPopShow('coffee'); }catch(e){}
  }, Math.max(60000, Number(ms)||120000));
}
function startIntermissionCoffee(lotId){
  coffeeIntermissionLotId=lotId;
  startCoffee();
}
function endCoffee(){
  coffeeActive=false; clearTimeout(coffeeTimer); showTable(false);
  var pop=document.getElementById('wolfPop'); if(pop) pop.classList.remove('coffee');
}
var nrHistory={};
function pickNR(key, arr){
  var h=nrHistory[key]||(nrHistory[key]=[]);
  var keep=Math.min(arr.length-1, Math.max(1, Math.floor(arr.length*0.6)));
  var pool=[]; for(var i=0;i<arr.length;i++){ if(h.indexOf(i)<0) pool.push(i); }
  var idx=pool.length ? pool[Math.floor(Math.random()*pool.length)] : Math.floor(Math.random()*arr.length);
  h.push(idx); while(h.length>keep) h.shift();
  return arr[idx];
}
function stopGestures(){
  clearInterval(gestureTimer); gestureTimer=null;
  var pop=document.getElementById('wolfPop'); if(pop) pop.classList.remove('lean');
}
function fxFloat(cls, txt, x, y, extra){
  var d=document.createElement('div');
  d.className='fx-float '+cls; d.textContent=txt;
  if(x!=null){ d.style.left=x+'px'; d.style.top=y+'px'; }
  if(extra) for(var k in extra) d.style.setProperty(k, extra[k]);
  document.body.appendChild(d);
  setTimeout(function(){ d.remove(); }, 2100);
}
function emojiBurst(list, n){
  var cx=innerWidth/2, cy=innerHeight*0.62;
  n=Math.min(n||8, 9);
  for(var i=0;i<n;i++){
    var ang=Math.random()*Math.PI*2, dist=120+Math.random()*200;
    fxFloat('fx-mini', list[i%list.length], cx-19, cy-19, {'--dx':Math.cos(ang)*dist+'px','--dy':(Math.sin(ang)*dist-120)+'px','--rot':(Math.random()*80-40)+'deg'});
  }
}
function heartBurst(){
  fxFloat('fx-bigheart','❤️');
  setTimeout(function(){ emojiBurst(['💖','💕','❤️','😘','💗'], 16); }, 250);
  try{ [660,880,1320].forEach(function(f,i){ beep(f,0.18,'sine',0.12,i*0.09); }); }catch(e){}
}
function splashBurst(){
  emojiBurst(['☕','💦','💧','😱','💦'], 16);
  splashSound();
}
function shutterSound(){
  if(!pageAllowsAudio() || !isAudioMaster()) return;
  try{
    var ctx=ac(), t0=ctx.currentTime, len=Math.floor(ctx.sampleRate*0.075);
    if(ctx.state==='suspended') ctx.resume().catch(function(e){ console.warn('Camera audio resume failed',e); });
    [0,0.085].forEach(function(offset){
      var buf=ctx.createBuffer(1,len,ctx.sampleRate), d=buf.getChannelData(0);
      for(var i=0;i<len;i++) d[i]=(Math.random()*2-1)*Math.pow(1-i/len,2);
      var src=ctx.createBufferSource(); src.buffer=buf;
      var hp=ctx.createBiquadFilter(); hp.type='highpass'; hp.frequency.value=1800;
      var g=ctx.createGain(); g.gain.value=offset?0.12:0.22;
      src.connect(hp); hp.connect(g); g.connect(ctx.destination); src.start(t0+offset);
      src.stop(t0+offset+0.08);
    });
  }catch(e){ console.warn('Camera shutter audio failed',e); }
}
function entranceCrowdSound(){
  if(!pageAllowsAudio() || !isAudioMaster()) return;
  try{
    crowdOoohSound({duration:6,volume:0.12});
    applauseSound();
    setTimeout(function(){ if(pageAllowsAudio() && isAudioMaster()) applauseSound(); },2500);
  }catch(e){ console.warn('Wolf entrance crowd audio failed',e); }
}
function cameraFlashes(n, entrance){
  var pop=document.getElementById('wolfPop'); if(!pop) return;
  if(!isVilkasStageOn() || phoneAway) return;
  var angles=[-165,-135,-105,-75,-45,-20];
  var reduced=window.matchMedia('(prefers-reduced-motion:reduce)').matches;
  n=n||6;
  if(reduced) n=Math.min(n,3);
  if(entrance) entranceCrowdSound();
  for(var i=0;i<n;i++){ (function(k){
    setTimeout(function(){
      if(!isVilkasStageOn() || phoneAway) return;
      var r=pop.getBoundingClientRect();
      if(!r.width || r.top>innerHeight-20) return;
      var a=angles[Math.floor(Math.random()*angles.length)]*Math.PI/180;
      var cx=r.left+r.width/2, cy=r.top+r.height*0.35, dist=r.width*(0.55+Math.random()*0.4);
      var f=document.createElement('div'); f.className='cam-flash';
      if(entrance) f.style.setProperty('--flash-size','clamp(160px,32vw,440px)');
      f.style.left=(cx+Math.cos(a)*dist)+'px'; f.style.top=(cy+Math.sin(a)*dist)+'px';
      f.style.setProperty('--rot',(Math.random()*160-80)+'deg');
      document.body.appendChild(f); setTimeout(function(){ f.remove(); },reduced?1150:850);
      pop.classList.add('flash-hit'); setTimeout(function(){ pop.classList.remove('flash-hit'); },180);
      shutterSound();
    }, k*(reduced?850:420)+Math.random()*60);
  })(i); }
}
var welcomeWolfLots={}, welcomeWolfFirstLot=false;
function welcomeWolfForLot(lot){
  var id=lot && (lot.lot_id||lot.id);
  if(!id){ console.warn('Wolf entrance requires a lot id'); return false; }
  var key=String(id)+'@'+String(lot.starts_at||'');
  if(welcomeWolfLots[key]) return false;
  welcomeWolfLots[key]=true;
  var number=Number(lot.lot_number);
  var welcome=!welcomeWolfFirstLot || (number>0 && number%10===0);
  welcomeWolfFirstLot=true;
  if(!welcome) return false;
  cameraFlashes(18,true);
  return true;
}
function wolfPhotoMoment(caption, pose){
  var card=document.getElementById('wolfPhoto'), img=document.getElementById('wolfPhotoImg');
  var cap=document.getElementById('wolfPhotoCaption');
  if(!card || !img) return;
  img.src=WOLF_POSES[pose||currentPose]||WOLF_POSES.raise;
  if(cap) cap.textContent=(caption||'Vilkas scenoje')+' · +37066331913';
  card.classList.remove('show'); void card.offsetWidth; card.classList.add('show');
  setTimeout(function(){ card.classList.remove('show'); },8200);
}
function photographedWolf(caption, pose){
  cameraFlashes(3);
  setTimeout(function(){ wolfPhotoMoment(caption, pose); },520);
}
function cheerBurst(){
  emojiBurst(['🔥','👍','💪','🎉','⭐'], 14);
}
var LAUGH_LINES=[
  'Cha cha cha! Ha ha ha! Vilkas juokiasi!',
  'Ha ha ha! Cha cha! Oi, kaip juokinga!',
  'Ho ho ho! Cha-cha-cha! Man linksmiau nei jums!',
  'Ha ha ha ha! Cha cha! Kaina kyla — o aš juokiuosi!',
  'Cha cha cha! Ha! Šitas aukcionas — geriausias cirkas!',
  'Ha ha! Cha cha cha! Vilkas nesulaiko juoko!',
  'Ho-ho! Cha cha! Piniginės dreba — o aš juokiuosi!',
  'Ha ha ha! Cha! Dar vienas euras — ir aš vėl juoksiu!'
];
var SOLD_BAJER=[
  'Cha cha! Šitas lotas — į istoriją!',
  'Na taip — piniginė plonesnė, o šypsena platesnė!',
  'Vilkas ploja kojom! Tokia pergalė retai matoma!',
  'Bajeriukas: kas nespėjo — tas pavydės iki sekmadienio!',
  'Ir vėl — vienas laimingas, visi kiti — su istorija papasakoti!',
  'Ha ha! Kūjis ilsisi, o nugalėtojas — šypsosi!',
  'Kaip sako Vilkas: kas drįso — tas ir turi!',
  'Bajeriukas: telefonas naujose rankose, o aš — su nauju komplimentu!',
  'Cha cha! Net mano akiniai nusišypsojo!',
  'Kas pralošė — ateikit penktadienį; kas laimėjo — saugokit dėžutę!',
  'Vilkas sako: geriau vienas euro spaudimas negu šimtas „gal vėliau“!',
  'Bajeriukas: kaina pakilo greičiau nei mano uodega rytą!',
  'Ha ha ha! Salė ūžia, o aš jau galvoju apie kitą lotą!',
  'Šitas sandoris — kaip kava: stiprus ir be cukraus!',
  'Na taip — laimėtojas šypsosi, o aš plakamiu kūju orą iš džiaugsmo!',
  'Bajeriukas: jei būčiau bankas — duočiau kreditą už tokią drąsą!',
  'Cha cha! Istorija bus pasakojama prie stalo iki Kalėdų!',
  'Vilkas patvirtina: čia ne lošimas — čia charakterio egzaminas. Išlaikyta!'
];
var BID_BAJER=[
  'Bajeriukas: pirštas greitesnis už mintį!',
  'Cha cha — ir vėl kaina šoka!',
  'Vilkas mato: čia jau ne žaidimas, čia sportas!',
  'Piniginė sušuko „ai“, o širdis — „dar!“',
  'Kaip sako mano močiutė: kas kelia — tas ir turi!',
  'Bajeriukas: mygtukas raudonas ne veltui — kaip uoga!',
  'Na taip — ir vėl salė sujudėjo!',
  'Ha ha! Net kėdės girgžda iš susijaudinimo!',
  'Čia jau karšta kaip keptuvėj — tik be aliejaus!',
  'Bajeriukas: vienas euras — mažai, o emocija — didelė!',
  'Vilkas skaičiuoja: drąsa plius euras lygu pergalė!',
  'Hei, kas dar miega — keliatės, čia aukcionas, ne pietų miegas!'
];
var lastSingAt=0, sangFor={}, lastSmokeAt=0, wolfInSmoke=false, smokePuffTimer=null;
function clearSmoke(){
  wolfInSmoke=false;
  clearInterval(smokePuffTimer); smokePuffTimer=null;
  var field=document.getElementById('smokeField');
  if(!field) return;
  field.classList.remove('on');
  var puffs=field.querySelectorAll('.smoke-puff');
  for(var i=0;i<puffs.length;i++) puffs[i].remove();
}
function puffSmoke(n){
  var field=document.getElementById('smokeField');
  if(!field) return;
  n=n==null?(3+Math.floor(Math.random()*3)):n;
  for(var i=0;i<n;i++){
    var p=document.createElement('div');
    p.className='smoke-puff';
    /* Dešinėje apačioje — kur Vilkas dingsta */
    p.style.left='auto';
    p.style.right=(2+Math.random()*28)+'%';
    p.style.bottom=(2+Math.random()*22)+'%';
    p.style.setProperty('--sx',(Math.random()*100-50)+'px');
    p.style.setProperty('--sz',(140+Math.random()*160)+'px');
    p.style.setProperty('--dur',(5.5+Math.random()*3)+'s');
    p.style.animationDelay=(i*0.2+Math.random()*0.25)+'s';
    field.appendChild(p);
    (function(el){ setTimeout(function(){ if(el&&el.parentNode) el.remove(); }, 9500); })(p);
  }
  lastSmokeAt=Date.now();
}
function enterSmokeBreak(){
  if(announceBusy || announceQueue.length || coffeeActive) return;
  wolfInSmoke=true;
  var field=document.getElementById('smokeField');
  if(field) field.classList.add('on');
  puffSmoke(5);
  clearInterval(smokePuffTimer);
  smokePuffTimer=setInterval(function(){
    if(!wolfInSmoke || announceBusy || announceQueue.length) return;
    puffSmoke(2+Math.floor(Math.random()*2));
  }, 3200);
}
function watchAmbienceSmoke(){
  /* Dūmai tik kai Vilkas dingęs — ne maišosi su juo scenoje */
  if(!wolfInSmoke) return;
  if(announceBusy || announceQueue.length) return;
  if(Date.now()-lastSmokeAt<2800) return;
  puffSmoke(2);
}
function wolfLaughSound(){
  try{
    var ctx=ac(), t0=ctx.currentTime+0.04;
    /* Cha-cha-cha tipo juokas — trumpi „ha“ tonai */
    var bursts=[0,0.16,0.32, 0.55,0.70,0.85, 1.15,1.30,1.48, 1.85,2.00];
    bursts.forEach(function(off,i){
      var t=t0+off;
      var o=ctx.createOscillator(), g=ctx.createGain();
      o.type='sawtooth';
      var f=220+(i%3)*40+Math.random()*25;
      o.frequency.setValueAtTime(f,t);
      o.frequency.exponentialRampToValueAtTime(f*0.75,t+0.11);
      g.gain.setValueAtTime(0.0001,t);
      g.gain.exponentialRampToValueAtTime(0.22,t+0.02);
      g.gain.exponentialRampToValueAtTime(0.0001,t+0.12);
      o.connect(g); g.connect(ctx.destination);
      o.start(t); o.stop(t+0.14);
      if(i%3===0) noiseBurst(t, 0.04, 0.15);
    });
  }catch(e){}
}
function laughBurst(){ emojiBurst(['😄','😂','🤣','😆','🐺'], 14); }
function notesBurst(){ emojiBurst(['🎵','🎶','💃','🕺','🎵'], 16); }
function rockBurst(){ emojiBurst(['🎸','🤘','⚡','🔥','🎶'], 18); }
function maybeSing(key, prob){
  // Aukciono vedėjas nepertraukia prekybos dainelėmis ar bajeriukais.
  return false;
}
/* Bajeriukai generuojami tik tada, kai Vilkas juos iš tiesų pasako. */
function coffeeSound(){
  try{
    var ctx=ac(), t0=ctx.currentTime;
    var n=Math.floor(ctx.sampleRate*1.6), buf=ctx.createBuffer(1,n,ctx.sampleRate), d=buf.getChannelData(0);
    for(var i=0;i<n;i++) d[i]=(Math.random()*2-1)*0.6;
    var src=ctx.createBufferSource(); src.buffer=buf;
    var bp=ctx.createBiquadFilter(); bp.type='bandpass'; bp.Q.value=4;
    bp.frequency.setValueAtTime(500,t0); bp.frequency.exponentialRampToValueAtTime(1800,t0+1.5);
    var g=ctx.createGain(); g.gain.setValueAtTime(0.001,t0); g.gain.linearRampToValueAtTime(0.35,t0+0.1); g.gain.setValueAtTime(0.35,t0+1.3); g.gain.linearRampToValueAtTime(0.001,t0+1.6);
    src.connect(bp); bp.connect(g); g.connect(ctx.destination); src.start(t0); src.stop(t0+1.6);
    [2.1,2.35].forEach(function(t){ noiseBurst(t0+t, 0.12, 0.25); });
  }catch(e){}
}
function restartClass(el, cls){ if(!el) return; el.classList.remove(cls); void el.offsetWidth; el.classList.add(cls); }
function wolfPopShow(pose){
  if(typeof isVilkasStageOn==='function' && !isVilkasStageOn()) return;
  clearTimeout(wolfHideTimer);
  clearSmoke(); /* Vilkas grįžta — dūmai dingsta */
  var pop=document.getElementById('wolfPop');
  setPose(pose||'raise');
  if(!pop) return;
  pop.classList.remove('idle','hide');
  pop.classList.add('alive');
  if(!pop.classList.contains('show')){ restartClass(pop,'show'); }
  else { pop.classList.add('show'); }
  pop.classList.add('alive');
  /* Gyvas klipas kaip sokejos — telefonas/bajeriai/TTS lieka per announceQueue */
  try{ keepVilkasVideoAlive(); }catch(e){}
}
function wolfPopTalking(on){
  var pop=document.getElementById('wolfPop');
  if(pop) pop.classList.toggle('talking', !!on);
  /* Baigus kalbą has-video režime po animacija lieka matomas still — grąžinam į p1 (ta pati apranga, užčiaupta burna) */
  if(pop && !on && pop.classList.contains('has-video')){ try{ setPose('raise'); }catch(e){} }
}
function wolfPopHideSoon(ms){
  /* F9 scenoje Vilkas LIEKA — tik burbulas užsidaro. Kitaip telefonas mato lotą be vedėjo. */
  if(typeof isVilkasStageOn==='function' && isVilkasStageOn()){
    clearTimeout(wolfHideTimer);
    wolfHideTimer=setTimeout(function(){
      setBubble('', '');
      var b=document.getElementById('wolfPopBubble');
      if(b) b.classList.remove('open');
      wolfPopTalking(false);
      wolfPopShow(currentPose||'raise');
    }, ms||900);
    return;
  }
  clearTimeout(wolfHideTimer);
  wolfHideTimer=setTimeout(function(){
    if(announceBusy || announceQueue.length || coffeeActive) return;
    var pop=document.getElementById('wolfPop');
    if(!pop) return;
    pop.classList.remove('talking','lean','coffee','side','idle','alive');
    pop.classList.add('show');
    restartClass(pop,'hide');
    setBubble('', '');
    var b=document.getElementById('wolfPopBubble');
    if(b) b.classList.remove('open');
    enterSmokeBreak();
    setTimeout(function(){
      if(announceBusy || announceQueue.length) return;
      if(typeof isVilkasStageOn==='function' && isVilkasStageOn()){ wolfPopShow('raise'); return; }
      pop.classList.remove('show','hide','alive');
    }, 650);
  }, ms||900);
}
function keepVilkasVideoAlive(){
  /* Skaidrus anim WebP (be fono) — F9 scenoje visada matomas + disco judesiai. */
  if(typeof isVilkasStageOn!=='function' || !isVilkasStageOn()) return;
  if(document.visibilityState==='hidden') return;
  try{
    var pop=document.getElementById('wolfPop');
    var vid=document.getElementById('wolfPopVid');
    if(!vid||!pop) return;
    if(!pop.classList.contains('show')) return;
    if(vid.tagName==='VIDEO'){
      vid.muted=true; vid.defaultMuted=true; vid.loop=true; vid.playsInline=true;
      vid.setAttribute('playsinline',''); vid.setAttribute('muted','');
      if(vid.error){ pop.classList.remove('has-video'); return; }
      pop.classList.add('has-video');
      if(vid.paused || vid.ended){
        var p=vid.play();
        if(p&&p.catch) p.catch(function(){ try{ pop.classList.remove('has-video'); }catch(e){} });
      }
      return;
    }
    /* IMG anim WebP — jokio juodo remo; tik vilkas */
    if(!vid.getAttribute('src') && !vid.src){ pop.classList.remove('has-video'); return; }
    if(!vid.complete || vid.naturalWidth===0){ pop.classList.remove('has-video'); return; }
    pop.classList.add('has-video');
  }catch(e){}
}
function keepVilkasOnStage(){
  if(typeof isVilkasStageOn==='function' && isVilkasStageOn()){
    if(phoneAway){
      /* F11 telefono išėjimas — NErodyti Vilko, kol negrįžo */
      try{
        var pop=document.getElementById('wolfPop');
        if(pop){ pop.classList.remove('show','alive','talking'); pop.classList.add('hide'); }
      }catch(e){}
      return;
    }
    try{ wolfPopShow(currentPose||'raise'); }catch(e){}
    try{ keepVilkasVideoAlive(); }catch(e){}
    return;
  }
  try{
    var vid=document.getElementById('wolfPopVid');
    if(vid && vid.tagName==='VIDEO' && !vid.paused) vid.pause();
  }catch(e){}
  var pop=document.getElementById('wolfPop');
  if(pop){
    pop.classList.remove('show','alive','talking','hide','has-video');
  }
}
var IDLE_POSES=['raise','welcome','thumb','present','clap','wink','glasses','raise'];
var idlePoseI=0;
setInterval(keepVilkasOnStage, 900);
setInterval(keepVilkasVideoAlive, 900);
setInterval(function(){
  if(typeof isVilkasStageOn!=='function' || !isVilkasStageOn()) return;
  if(announceBusy || (announceQueue&&announceQueue.length) || phoneCallActive || hostAudio) return;
  idlePoseI=(idlePoseI+1)%IDLE_POSES.length;
  try{
    var popV=document.getElementById('wolfPop');
    /* has-video: tyloje matomas p1 kadras — laikom VIENĄ pozą (be smokingo/kostiumo mirgėjimo), gyvumas per soft-sway */
    if(popV && popV.classList.contains('has-video')) setPose('raise'); else setPose(IDLE_POSES[idlePoseI]);
  }catch(e){}
  try{
    var pop=document.getElementById('wolfPop');
    if(!pop) return;
    pop.classList.remove('lean','strike','surprise');
    if(idlePoseI%3===0) pop.classList.add('lean');
  }catch(e){}
}, 4200);
function hammerStrike(){
  setPose('bang');
  hammerSound();
  restartClass(document.getElementById('wolfPop'),'strike');
  restartClass(document.getElementById('wolfImpact'),'go');
  restartClass(document.getElementById('stageRoot'),'shake');
  restartClass(document.getElementById('hostBar'),'host-flash');
}
function bangHammer(times, onDone, gongLast){
  if(times===0){ if(onDone) setTimeout(onDone, 50); return; }
  times=times||1;
  var i=0;
  (function next(){
    setPose('raise');
    setTimeout(function(){
      hammerStrike();
      /* Plaktuko smūgis, po ~55ms — gongo skambesys */
      if(gongLast && i===times-1) setTimeout(function(){ try{ gongSound(); }catch(e){} }, 55);
      i++;
      if(i<times){ setTimeout(next, 330); }
      else if(onDone){ setTimeout(onDone, gongLast ? 520 : 380); }
    }, 170);
  })();
}
function wolfGesture(kind){
  var w=document.getElementById('hostWolf');
  if(!w) return;
  w.classList.remove('idle','talking','bow','wave');
  void w.offsetWidth;
  if(kind==='talk'){ w.classList.add('talking'); return; }
  if(kind==='bow'){ w.classList.add('bow'); setTimeout(function(){ if(!announceBusy){ w.classList.remove('bow'); w.classList.add('idle'); } }, 1100); return; }
  if(kind==='wave'){ w.classList.add('wave'); setTimeout(function(){ if(!announceBusy){ w.classList.remove('wave'); w.classList.add('idle'); } }, 900); return; }
  w.classList.add('idle');
}
function wolfIdle(){
  var w=document.getElementById('hostWolf');
  if(!w) return;
  w.classList.remove('talking','bow','wave');
  w.classList.add('idle');
}
wolfIdle();
function speechTitle(t){ return String(t||'').replace(/\b\d+\s?(GB|TB)\b/ig,'').replace(/\s{2,}/g,' ').trim(); }
function tonightTitles(){
  var titles=[], seen={};
  function add(t){
    t=speechTitle(t);
    if(!t || seen[t]) return;
    seen[t]=1; titles.push(t);
  }
  if(state && state.lot && state.lot.status==='live') add(state.lot.title);
  ((state && state.queue)||[]).forEach(function(q){ if(titles.length<10) add(q.title); });
  if(!titles.length) ((state && state.queue_titles)||[]).forEach(function(t){ if(titles.length<10) add(t); });
  return titles;
}
function openingLines(){
  var titles=tonightTitles();
  var items;
  if(!titles.length) items='keletas išmaniųjų telefonų ir kitų gerų daiktų';
  else if(titles.length>5) items=titles.slice(0,5).join(', ')+' ir dar keletas įdomių daiktų';
  else if(titles.length>1) items=titles.slice(0,-1).join(', ')+' ir '+titles[titles.length-1];
  else items=titles[0];
  return [
    'Labas vakaras, susirinkusieji! Malonu jus matyti. Sveikinu jus Penktadienio aukcione. Įsitaisykite patogiai.',
    'Taisyklės paprastos. Kiekviena prekė startuoja nuo simbolinės kainos. Vienas paspaudimas — ir kaina kyla vienu euru. Laimi tas, kurio statymas lieka paskutinis, kai nuskamba mano gongas.',
    'Gongas! Lotas uždarytas!',
    'Šį vakarą ant stalo, eilės tvarka: '+items+'. Apačioje galite juos peržiūrėti. Atsipalaiduokite… ir stebėkite!'
  ];
}
var openingDone = (Date.now()-(parseInt(sessionStorage.getItem('vilkas_open'),10)||0)) < 10*60*1000;
if(/[?&]fresh=(?:\d+|play|demo)(?:&|$)/.test(location.search)){ openingDone=false; try{ sessionStorage.removeItem('vilkas_open'); }catch(e){} }
function maybeOpeningSpeech(){
  // DISABLED: server director owns this
  return;
  if(openingDone || !voiceOn) return;
  /* Palaukti kol state ateis — kad Vilkas vardytų tikras prekes iš navigacijos */
  if(!state) return;
  var titles=tonightTitles();
  if(state.auction_locked && !titles.length) return;
  openingDone=true;
  try{ sessionStorage.setItem('vilkas_open', String(Date.now())); }catch(e){}
  var L=openingLines();
  Promise.all([
    Promise.resolve(L[0]),
    Promise.resolve(L[1]),
    Promise.resolve(L[2]),
    vilkasThink('opening_items', {tonight_titles:titles, items:titles.join(', ')}, L[3])
  ]).then(function(lines){
    lines.forEach(prefetchTts);
    queueAnnounce(lines[0], {pose:'welcome', bangs:0, gestures:['welcome','present','raise'], gestureMs:1600, bubble:'Penktadienio aukcionas'});
    queueAnnounce(lines[1], {pose:'present', bangs:0, gestures:['present','welcome','thumb'], gestureMs:1800, bubble:'Taisyklės'});
    queueAnnounce(lines[2], {pose:'bang', bangs:0, gestures:['bang','raise'], gestureMs:900, bubble:'🔔 Gongas!',
      onSpeak:function(){
        setTimeout(function(){ try{ hitGong(); }catch(e){} }, 2400);
      }});
    queueAnnounce(lines[3], {pose:'present', bangs:1, after:'bow', gestures:['present','raise','welcome'], gestureMs:1600, bubble:'Šio vakaro prekės'});
  });
}
function setHostBubble(html){
  var b=document.getElementById('hostBubble');
  if(!b) return;
  b.innerHTML=html;
  b.classList.remove('talk');
  void b.offsetWidth;
  b.classList.add('talk');
}
function eurosWords(n){
  var x=Math.round(Number(n)||0);
  if(x>0 && x<1000){
    var U=['','vieną','du','tris','keturis','penkis','šešis','septynis','aštuonis','devynis'];
    var T=['dešimt','vienuolika','dvylika','trylika','keturiolika','penkiolika','šešiolika','septyniolika','aštuoniolika','devyniolika'];
    var D=['','','dvidešimt','trisdešimt','keturiasdešimt','penkiasdešimt','šešiasdešimt','septyniasdešimt','aštuoniasdešimt','devyniasdešimt'];
    var w=[], h=Math.floor(x/100), r=x%100;
    if(h===1) w.push('šimtą'); else if(h>1) w.push((h===2?'du':U[h])+' šimtus');
    if(r>=10 && r<20) w.push(T[r-10]);
    else { if(r>=20) w.push(D[Math.floor(r/10)]); if(r%10) w.push(U[r%10]); }
    var last=x%10, teen=(r>=10&&r<20);
    return w.join(' ')+' '+(teen||last===0 ? 'eurų' : (last===1 ? 'eurą' : 'eurus'));
  }
  return x+' eurų';
}
function pick(a){ return a[Math.floor(Math.random()*a.length)]; }
function capSentences(s){ return s.replace(/(^|[!?.]\s+)([a-ząčęėįšųūž])/g, function(m,a,b){ return a+b.toUpperCase(); }); }
/* Vilkas smegenys — LLM + šablonai ant GPU kompo (be ElevenLabs) */
function vilkasThink(event, payload, fallbackText){
  var fb=String(fallbackText||'').trim()||'Nestabdom, judam! Kas kitas?';
  return fetch('/api/vilkas/think', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({event:event, payload:payload||{}})
  })
  .then(function(r){ return r.ok ? r.json() : {text:fb}; })
  .then(function(j){ return (j && j.text) ? String(j.text).trim() : fb; })
  .catch(function(){ return fb; });
}
function bidLine(name, amount, isFirst){
  var n=String(name||'').split(' ')[0]||'drauge';
  var priceNow=eurosWords(amount);
  var item='telefono';
  try{
    var t=(state && state.lot && state.lot.title) ? String(state.lot.title) : '';
    if(/iphone|apple/i.test(t)) item='iPhone';
    else if(/samsung|galaxy/i.test(t)) item='Samsung';
    else if(/nokia|lumia/i.test(t)) item='Nokia';
    else if(/motorola|moto/i.test(t)) item='Motorola';
    else if(/telefon/i.test(t)) item='telefono';
  }catch(e){}
  var fem=false;
  try{ fem=!!isFemaleName(name); }catch(eF){}
  var praise=fem ? 'šaunuolė, šaunuolė' : 'šaunuolis, šaunuolis';
  var want=fem ? 'Nori '+item+'?' : 'Nori '+item+'?';
  /* Gyvas Vilko stilius su keliančiu žmogumi — mokykla tobulina bajeriukus. */
  return pickNR('bidSpeechLive',[
    'O '+n+' pakėlė — '+praise+'! '+want+' Viso jau '+priceNow+'. Kas kitas?',
    'Žiūrėkit — '+n+' kelia! '+praise+'! '+want+' Dabar '+priceNow+'. Kas atsakys?',
    'Ooo, '+n+'! '+praise+'! Pakėlė kainą — '+want+' Jau '+priceNow+'. Kas perims?',
    'Štai '+n+' spaudžia! '+praise+'! Gal tikrai nori '+item+'? '+priceNow+'. Kas kitas?',
    'Nu va — '+n+' pakėlė! '+praise+'! '+want+' Kaina '+priceNow+'. Nestabdom!',
    'Brawo, '+n+'! '+praise+'! '+item+' jau '+priceNow+'. Kas drįsta atsakyti?'
  ]);
}
function bidLineRaw(name, amount, isFirst){ return bidLine(name, amount, isFirst); }
function bidPose(name){ return isFemaleName(name) ? pickNR('fpose',['wink','glasses']) : pickNR('mpose',['thumb','raise','clap']); }
var hostAudio = null;
var speakGen = 0; /* kiekviena nauja kalba — senos Async TTS / onended miršta */
function interruptAllSpeech(){
  speakGen++;
  announceEpoch++;
  try{ clearTimeout(visualAnnTimer); visualAnnTimer=null; }catch(eVA){}
  announceBusy=false;
  announceCurrentJob=null;
  announceQueue=[];
  setPhoneCallActive(false);
  phoneSessionActive=false;
  phoneAway=false;
  try{ clearTimeout(phoneAwayTimer); phoneAwayTimer=null; }catch(ePA){}
  phoneBidHold=[];
  try{ stopGuitarRiff(); }catch(e){}
  try{ if(coffeeActive) endCoffee(); }catch(e){}
  try{ if(hostAudio){ killAudio(hostAudio); hostAudio=null; } }catch(e){}
  try{ clearTimeout(gongTimer); gongTimer=null; }catch(e){}
  try{ if(gongAudio){ gongAudio.pause(); gongAudio.currentTime=0; gongAudio=null; } }catch(e){}
  try{ if(phoneRingAudio){ phoneRingAudio.pause(); phoneRingAudio.currentTime=0; phoneRingAudio=null; } }catch(e){}
  try{ clearTimeout(phoneTradeTimer); clearTimeout(phoneSpeechTimer); phoneSpeechTimer=null; }catch(e){}
  try{ if(navigator.vibrate) navigator.vibrate(0); }catch(e){}
  try{ if(window.speechSynthesis) speechSynthesis.cancel(); }catch(e){}
  try{ stopGestures(); }catch(e){}
}
/*
  Statymo pranešimas negali laukti ElevenLabs užklausos: gongas ir frazė
  paleidžiami tą pačią akimirką naršyklėje. Tai ypač svarbu po žmogaus
  paspaudimo, kai garso leidimas jau suteiktas.
*/
var lastBidSpeechAt=0;
function announceJobProtected(job){
  if(!job) return false;
  if(job.tag==='sold' || job.tag==='start') return true;
  if(job.tag==='phone' || job.tag==='phone_catchup') return true;
  if(job.after==='bow' || job.pose==='bow') return true;
  return false;
}
function announceQueueHasProtected(){
  for(var i=0;i<announceQueue.length;i++){
    if(announceJobProtected(announceQueue[i])) return true;
  }
  return false;
}
function announceQueueSoftOnly(){
  if(!announceQueue.length) return true;
  for(var i=0;i<announceQueue.length;i++){
    var j=announceQueue[i];
    if(!j) continue;
    if(announceJobProtected(j)) return false;
    if(j.tag && j.tag!=='nudge' && j.tag!=='joke' && j.tag!=='phone' && j.tag!=='guitar' && j.tag!=='sing') return false;
  }
  return true;
}
function speakBidNow(name, amount){
  /* F11 / telefonas — JOKIŲ komentarų; vardai catchup po skambučio. */
  if(isPhoneBusy()){ holdBidDuringPhone(name, amount); return; }
  var now=Date.now();
  var bubble='🔔 '+name+' → '+Math.round(amount)+' €';
  var fallback=bidLine(name, amount, false);
  /* Gongas + burbulas VISADA iškart — balsas eina per eilę, be chaotiško pertraukimo. */
  try{ hitGong(); }catch(e){}
  try{ cheerBurst(); }catch(e){}
  try{ setBubble(bubble, fallback); }catch(e){}
  if(now-lastBidSpeechAt<9000) return;
  lastBidSpeechAt=now;
  /* Visada su vardu — bajeriukas / pagyrimas keliančiam. */
  var text=fallback || bidLine(name, amount, false);
  var fem=false; try{ fem=!!isFemaleName(name); }catch(eF){}
  var opts={
    tag:'bid', priority:true, pose:'bang', bangs:0, fast:!fem, fx:'cheer',
    gestures:['bang',bidPose(name),'thumb'], gestureMs:350, bubble:bubble
  };
  if(fem) opts.speed=0.88;
  /* Sold/start (arba einanti kalba) — nešluojam eilės; bid į frontą. Soft (nudge/joke/phone) — galima interrupt. */
  if(announceBusy || announceQueueHasProtected() || !announceQueueSoftOnly()){
    queueAnnounce(text, opts);
    return;
  }
  interruptAllSpeech();
  queueAnnounce(text, opts);
}
function readingMs(text){ return Math.max(1800, text.split(/\s+/).length*320); }
function silentRead(text, onDone, already){
  setNoAudio(true);
  setTimeout(function(){ if(onDone) onDone(); }, Math.max(600, readingMs(text)-(already||0)));
}
function speakHostBrowser(text, onDone, already){
  if(!ltVoice) ltVoice=pickLtVoice();
  if(!window.speechSynthesis || !ltVoice){ silentRead(text, onDone, already); return; }
  try{
    speechSynthesis.cancel();
    var u=new SpeechSynthesisUtterance(text);
    u.lang='lt-LT';
    u.rate=1.05;
    u.pitch=1.12;
    u.volume=1;
    u.voice=ltVoice;
    setNoAudio(true);
    u.onend=function(){ if(onDone) onDone(); };
    u.onerror=function(){ if(onDone) onDone(); };
    speechSynthesis.speak(u);
  }catch(e){ if(onDone) onDone(); }
}
function killAudio(a){
  try{
    a.onended=a.onerror=a.onplaying=a.ontimeupdate=null;
    if(a._wolfVoiceSource) a._wolfVoiceSource.disconnect();
    if(a._wolfVoiceGain) a._wolfVoiceGain.disconnect();
    a.pause(); a.removeAttribute('src'); a.load();
  }catch(e){}
}
/* TTS blob cache — NAUJAS_v3_lt (v3lt55). Senų kešų URL nebegalioja. */
var TTS_VER='v8-lt-intonacija-sexy-20261010';
var ttsBlobCache={}, ttsBlobWait={};
/*
  Vienas puslapio atidarymas negali generuoti dešimčių nepanaudojamų
  bajeriukų. TTS kvota naudojama tik frazei, kuri iš tiesų bus pasakyta.
*/
var TTS_PREFETCH_ENABLED = true;
function ttsCacheKey(text, fast, speed){
  var sp=(speed && speed>0)?String(speed):'';
  return TTS_VER+'|'+(fast?'1|':'0|')+sp+'|'+String(text||'');
}
function ttsFetchUrl(text, fast, speed){
  var u='/api/tts?text='+encodeURIComponent(text)+(fast?'&fast=1':'')+'&v='+encodeURIComponent(TTS_VER)+'&_='+Date.now();
  if(speed && speed>0) u+='&speed='+encodeURIComponent(String(speed));
  return u;
}
function prefetchTts(text, fast, speed){
  if(!TTS_PREFETCH_ENABLED) return;
  if(!voiceOn || !text) return;
  var key=ttsCacheKey(text, !!fast, speed);
  if(ttsBlobCache[key] || ttsBlobWait[key]) return;
  ttsBlobWait[key]=true;
  fetch(ttsFetchUrl(text, fast, speed), {cache:'no-store'})
    .then(function(r){ if(!r.ok) throw new Error('tts'); return r.blob(); })
    .then(function(b){ ttsBlobCache[key]=URL.createObjectURL(b); })
    .catch(function(){})
    .then(function(){ delete ttsBlobWait[key]; });
}
function loadTtsUrl(text, fast, speed){
  var key=ttsCacheKey(text, !!fast, speed);
  if(ttsBlobCache[key]) return Promise.resolve(ttsBlobCache[key]);
  if(!TTS_PREFETCH_ENABLED){
    return fetch(ttsFetchUrl(text, fast, speed), {cache:'no-store'})
      .then(function(r){ if(!r.ok) throw new Error('tts'); return r.blob(); })
      .then(function(b){ var u=URL.createObjectURL(b); ttsBlobCache[key]=u; return u; });
  }
  return new Promise(function(resolve, reject){
    var tries=0;
    (function poll(){
      if(ttsBlobCache[key]) return resolve(ttsBlobCache[key]);
      if(!ttsBlobWait[key] && tries===0) prefetchTts(text, fast, speed);
      tries++;
      if(tries>200) return reject(new Error('tts_timeout'));
      setTimeout(poll, 50);
    })();
  }).catch(function(){
    return fetch(ttsFetchUrl(text, fast, speed), {cache:'no-store'})
      .then(function(r){ if(!r.ok) throw new Error('tts'); return r.blob(); })
      .then(function(b){ var u=URL.createObjectURL(b); ttsBlobCache[key]=u; return u; });
  });
}
function speakHost(text, onDone, onStart, opts){
  opts = opts || {};
  var title = opts.bubble != null ? opts.bubble : null;
  var fast = !!opts.fast;
  var speed = (opts.speed && opts.speed>0) ? opts.speed : null;
  var readyUrl = opts.audioUrl || null;
  var myGen = (opts.gen != null) ? opts.gen : speakGen;
  function stillMine(){ return myGen === speakGen; }
  setNoAudio(false);
  var t0=Date.now(), done=false, startedCb=false, raf=null, tries=0;
  function begin(){
    if(!stillMine()) return;
    if(startedCb) return; startedCb=true;
    setBubble(title, text);
    var b=document.getElementById('wolfPopBubble');
    if(b){ b.classList.add('open'); restartClass(b,'pop'); }
    revealWords(0);
    wolfPopTalking(true);
    wolfGesture('talk');
    if(onStart) try{ onStart(); }catch(e){}
  }
  function finish(){
    if(done) return;
    done=true;
    clearTimeout(lateTimer);
    if(raf) cancelAnimationFrame(raf);
    if(a) killAudio(a);
    if(hostAudio===a) hostAudio=null;
    if(!stillMine()) return; /* perėmė naujas balsas — nekviesk onDone */
    revealWords(1);
    wolfIdle();
    wolfPopTalking(false);
    var b=document.getElementById('wolfPopBubble');
    if(b) b.classList.remove('open');
    setMusicDuck(false);
    if(onDone) onDone();
  }
  function fallback(blocked){
    if(done || !stillMine()) return;
    if(tries < 2){
      tries++;
      clearTimeout(lateTimer);
      if(a) killAudio(a);
      readyUrl=null;
      playOnce();
      return;
    }
    clearTimeout(lateTimer);
    if(a) killAudio(a);
    begin();
    silentRead(text, finish, Date.now()-t0);
  }
  var a=null, lateTimer=null;
  if(!voiceOn || !isAudioMaster() || !pageAllowsAudio()){ begin(); silentRead(text, finish); return; }
  if(!stillMine()) return;
  setMusicDuck(true);
  try{ if(hostAudio) killAudio(hostAudio); hostAudio=null; }catch(e){}
  try{ if(window.speechSynthesis) speechSynthesis.cancel(); }catch(e){}
  function bindAndPlay(url){
    if(!stillMine() || done) return;
    a = new Audio(url);
    a.preload = 'auto';
    a.volume = WOLF_VOICE_VOL;
    try{
      var VoiceAudioContext=window.AudioContext||window.webkitAudioContext;
      if(VoiceAudioContext){
        if(!wolfVoiceAudioContext) wolfVoiceAudioContext=new VoiceAudioContext();
        a._wolfVoiceSource=wolfVoiceAudioContext.createMediaElementSource(a);
        a._wolfVoiceGain=wolfVoiceAudioContext.createGain();
        a._wolfVoiceGain.gain.value=WOLF_VOICE_BOOST;
        a._wolfVoiceSource.connect(a._wolfVoiceGain);
        a._wolfVoiceEchoDelay=wolfVoiceAudioContext.createDelay(1);
        a._wolfVoiceEchoDelay.delayTime.value=WOLF_ECHO_DELAY_S;
        a._wolfVoiceEchoGain=wolfVoiceAudioContext.createGain();
        a._wolfVoiceEchoGain.gain.value=WOLF_ECHO_GAIN;
        a._wolfVoiceGain.connect(wolfVoiceAudioContext.destination);
        a._wolfVoiceGain.connect(a._wolfVoiceEchoDelay);
        a._wolfVoiceEchoDelay.connect(a._wolfVoiceEchoGain);
        a._wolfVoiceEchoGain.connect(wolfVoiceAudioContext.destination);
        if(wolfVoiceAudioContext.state==='suspended') wolfVoiceAudioContext.resume();
      } else {
        a.volume=Math.min(1,WOLF_VOICE_VOL*WOLF_VOICE_BOOST);
      }
    }catch(voiceGainError){
      a.volume=Math.min(1,WOLF_VOICE_VOL*WOLF_VOICE_BOOST);
      console.warn('Vilko balso stiprinimas nepavyko:',voiceGainError);
    }
    a.playbackRate = 0.93;
    if('preservesPitch' in a) a.preservesPitch = false;
    else if('webkitPreservesPitch' in a) a.webkitPreservesPitch = false;
    hostAudio = a;
    var started = false;
    lateTimer = setTimeout(function(){ if(!started && stillMine()) fallback(false); }, 12000);
    function startSync(){
      if(!stillMine() || started) return;
      started = true;
      clearTimeout(lateTimer);
      begin();
      (function loop(){
        if(done || !stillMine()) return;
        if(a && a.duration && isFinite(a.duration) && a.duration > 0){
          revealWords(a.currentTime / a.duration);
        }
        raf = requestAnimationFrame(loop);
      })();
    }
    a.onplaying = startSync;
    a.onended = finish;
    a.onerror = function(){ if(stillMine()) fallback(false); };
    var p = a.play();
    if(p && p.catch) p.catch(function(err){ if(stillMine()) fallback(err && err.name === 'NotAllowedError'); });
  }
  function playOnce(){
    if(!stillMine() || done) return;
    if(readyUrl){ bindAndPlay(readyUrl); readyUrl=null; return; }
    loadTtsUrl(text, fast, speed).then(function(url){
      if(!stillMine() || done) return;
      bindAndPlay(url);
    }).catch(function(){ if(stillMine()) fallback(false); });
  }
  playOnce();
}
function announceJobKey(job){
  if(!job) return '';
  return String(job.tag||'')+'|'+String(job.text||'').trim();
}
function runAnnounceQueue(){
  if(!pageAllowsAudio()){
    /* Hidden tab — eilė miršta, be fono TTS / Vilko. */
    announceQueue=[];
    announceBusy=false;
    announceCurrentJob=null;
    return;
  }
  if(!isCoverMode() && !isAudioMaster()){
    announceQueue=[];
    announceBusy=false;
    announceCurrentJob=null;
    return;
  }
  if(announceBusy || !announceQueue.length) return;
  /* Statymo pranešimas / skambučio vėliava — palaukiam. BET jei phoneCallActive
     užstrigo be hostAudio >3s, nenužudom eilės amžiams (F11 tada „neskamba“). */
  if(hostAudio){
    setTimeout(runAnnounceQueue, 180);
    return;
  }
  /* phoneCallActive stabdo KITUS darbus per skambučio skambėjimą.
     phone / phone_catchup — PRIVALO eiti (F11 „Atsiprašau“ / Alio / viršininkas).
     Kitaip: skambutis skamba, o Vilkas tyli amžinai. */
  if(phoneCallActive){
    var peek=announceQueue[0];
    var phoneJob=peek && (peek.tag==='phone' || peek.tag==='phone_catchup');
    if(phoneJob){
      setPhoneCallActive(false);
    } else if(phoneCallSince && Date.now()-phoneCallSince>3000){
      setPhoneCallActive(false);
    } else {
      setTimeout(runAnnounceQueue, 180);
      return;
    }
  }
  var job=announceQueue.shift();
  /* Pasenęs soft darbas (nudge/joke/phone/guitar laukė >25 s) — išmetam, kad Vilkas nekalbėtų apie praeitį. */
  if(job && job.queuedAt && (job.tag==='nudge'||job.tag==='joke'||job.tag==='phone'||job.tag==='guitar'||job.tag==='sing') && Date.now()-job.queuedAt>25000){
    if(job.onDone && job.tag==='phone') try{ job.onDone(); }catch(e){}
    setTimeout(runAnnounceQueue, 0);
    return;
  }
  announceBusy=true;
  announceCurrentJob=job;
  var jobEpoch=announceEpoch;
  if(announceQueue[0]) prefetchTts(announceQueue[0].text, announceQueue[0].fast, announceQueue[0].speed);
  /* 1) Pirma užkraunam balsą — Vilkas dar NĖRA scenoje */
  var prep = (job.playMs || !job.text) ? Promise.resolve(null) : loadTtsUrl(job.text, !!job.fast, job.speed).catch(function(){ return null; });
  prep.then(function(audioUrl){
    if(jobEpoch!==announceEpoch) return;
    if(job.applause){ try{ bidApplauseSound(); }catch(e){} }
    function doSpeak(){
      var popEl=document.getElementById('wolfPop');
      if(popEl){ popEl.classList.remove('coffee','side'); if(job.cls) popEl.classList.add(job.cls); }
      if(job.bangsBefore) setPose(job.pose||'raise');
      else setPose(job.pose||'raise');
      if(job.onSpeak) try{ job.onSpeak(); }catch(e){}
      if(job.fx==='heart') heartBurst(); else if(job.fx==='cheer') cheerBurst(); else if(job.fx==='splash') splashBurst(); else if(job.fx==='notes') notesBurst(); else if(job.fx==='laugh'){ laughBurst(); try{ wolfLaughSound(); }catch(e){} } else if(job.fx==='rock') rockBurst();
      var say = job.playMs ? function(t, cb, onStart){
        setBubble(job.bubble||null, ''); var b=document.getElementById('wolfPopBubble'); if(b) b.classList.add('open'); wolfPopTalking(true); setMusicDuck(true); onStart();
        setTimeout(function(){ wolfPopTalking(false); setMusicDuck(false); if(b) b.classList.remove('open'); cb(); }, job.playMs);
      } : function(t, cb, onStart){
        speakHost(t, cb, onStart, {bubble: job.bubble, fast: job.fast, speed: job.speed, audioUrl: audioUrl, gen: speakGen});
      };
      say(job.text, function(){
        if(jobEpoch!==announceEpoch) return;
        stopGestures();
        if(popEl && !job.keepCls) popEl.classList.remove('coffee','side');
        bangHammer(job.bangs==null?1:job.bangs, function(){
          if(jobEpoch!==announceEpoch) return;
          if(job.after) setPose(job.after);
          announceBusy=false;
          announceCurrentJob=null;
          if(job.onDone) try{ job.onDone(); }catch(e){}
          if(announceQueue.length) setTimeout(runAnnounceQueue, 180);
          else if(job.stay && coffeeActive){ setPose('coffee'); var pe=document.getElementById('wolfPop'); if(pe) pe.classList.add('coffee'); setBubble('', ''); }
          else wolfPopHideSoon(job.after?500:280);
        });
      }, function(){ startGestures(job.gestures, job.gestureMs); });
    }
    function appearThenSpeak(){
      clearSmoke();
      wolfPopShow(job.pose||'raise');
      /* Pop animacija ~0.28s — tada balsas+lentelė+judesiai kartu */
      setTimeout(doSpeak, job.bangsBefore ? 80 : 280);
    }
    if(job.bangsBefore){
      clearSmoke();
      wolfPopShow('raise');
      bangHammer(job.bangsBefore, appearThenSpeak, job.gong);
    } else {
      appearThenSpeak();
    }
  });
}
var visualAnnTimer=null;
function runVisualAnnounce(text, opts){
  /* Telefonas / antras tabas: BE TTS (balsas tik audio-master), bet Vilkas MATOMAS + kalbos poza. */
  if(typeof isVilkasStageOn==='function' && !isVilkasStageOn()) return;
  if(phoneAway) return;
  opts=opts||{};
  try{ wolfPopShow(opts.pose||'present'); }catch(e){}
  try{ clearTimeout(visualAnnTimer); }catch(e){}
  try{
    var pop=document.getElementById('wolfPop');
    if(pop){ pop.classList.remove('hide','coffee','side'); if(opts.cls) pop.classList.add(opts.cls); }
  }catch(e){}
  try{ setPose(opts.pose||'raise'); }catch(e){}
  try{ wolfPopTalking(true); }catch(e){}
  try{ if(opts.gestures) startGestures(opts.gestures, opts.gestureMs); }catch(e){}
  try{
    if(opts.fx==='cheer') cheerBurst();
    else if(opts.fx==='heart') heartBurst();
    else if(opts.fx==='laugh') laughBurst();
    else if(opts.fx==='splash') splashBurst();
    else if(opts.fx==='notes') notesBurst();
    else if(opts.fx==='rock') rockBurst();
  }catch(e){}
  try{ if(opts.onSpeak) opts.onSpeak(); }catch(e){}
  var ms=opts.playMs||Math.min(10000, Math.max(1800, String(text||opts.text||'').length*50));
  visualAnnTimer=setTimeout(function(){
    visualAnnTimer=null;
    try{ wolfPopTalking(false); }catch(e){}
    try{ stopGestures(); }catch(e){}
    try{ if(opts.after) setPose(opts.after); }catch(e){}
    try{ if(opts.onDone) opts.onDone(); }catch(e){}
    try{ wolfPopShow(opts.after||opts.pose||'raise'); }catch(e){}
  }, ms);
}
function queueAnnounce(text, opts){
  if(typeof isVilkasStageOn==='function' && !isVilkasStageOn()) return; /* izanga — Vilkas tyli */
  if(typeof opts!=='object' || opts===null) opts={applause:!!opts};
  opts.text=text;
  try{ wolfPopShow((opts && opts.pose) || 'present'); }catch(e){}
  /* Balsas tik audio-master; VAIZDAS — visiems (telefonas be TTS, su kalbos poza). */
  if(!isCoverMode() && typeof isAudioMaster==='function' && !isAudioMaster()){
    runVisualAnnounce(text, opts);
    return;
  }
  if(!pageAllowsAudio()) return; /* tab hidden */
  opts.queuedAt=Date.now();
  var key=announceJobKey(opts);
  if(key && key!=='|'){
    for(var i=0;i<announceQueue.length;i++){
      if(announceJobKey(announceQueue[i])===key) return;
    }
    if(announceBusy && announceCurrentJob && announceJobKey(announceCurrentJob)===key) return;
  }
  if(opts.priority) announceQueue.unshift(opts);
  else announceQueue.push(opts);
  prefetchTts(text, opts.fast);
  runAnnounceQueue();
}
function maybeAnnounceBid(state){
  // DISABLED: server director owns this
  return;
  if(!state || !state.bids || !state.bids.length) return;
  var b=state.bids[0];
  var key=String(b.at)+'|'+b.name+'|'+b.amount;
  if(lastBidKey===null){ lastBidKey=key; return; } // nepranešti istorinių
  if(key===lastBidKey) return;
  /* Tavo paspaudimas jau paskelbtas iš serverio atsakymo — nekartoti. */
  if(locallyAnnouncedBid &&
     locallyAnnouncedBid.name===b.name &&
     Number(locallyAnnouncedBid.amount)===Number(b.amount)){
    locallyAnnouncedBid=null;
    lastBidKey=key;
    return;
  }
  lastBidKey=key;
  var isFirst = state.bids.length===1;
  silence.bidAt=Date.now(); silence.stage=0;
  /* interruptAllSpeech viduje speakBidNow — senas balsas miršta */
  if(coffeeActive) endCoffee();
  speakBidNow(b.name, b.amount);
  scheduleTradePhoneCall();
}

var silence={lotId:null, bidAt:0, stage:0, nudged:{}};
function cuteName(name){
  var w=String(name||'').trim().split(/\s+/)[0];
  if(!w) return 'gražuole';
  if(/^oksana$/i.test(w)) return 'Oksanka';
  if(/^vanessa$/i.test(w)) return 'Vanessa';
  if(/ita$/i.test(w)) return w.replace(/ita$/i,'yte'); /* Brigita → Brigyte */
  if(/ė$/i.test(w)) return w.replace(/ė$/i,'yte');     /* Giedrė → Giedryte */
  if(/a$/i.test(w)) return w.replace(/a$/i,'ute');     /* Laura → Laurute */
  return vocative(w);
}
/* Naujos damos — kai dvi prisijungia: „Ooo! Dar dvi damos… Paplokime!“ */
var seenJoinNames = {};
var seenJoinEventIds = null;
var pendingDames = [];
var dameBatchTimer = null;
function announceTwoDames(a, b){
  var line='Ooooo! '+a+'! Paplokite — prisijungė! Ooo ir '+cuteName(b)+'!';
  queueAnnounce(line, {
    pose:'clap', bangs:0, applause:true,
    gestures:CLAP.concat(['wink','glasses','wink']), gestureMs:360,
    bubble:'👏 Oooo! '+a+' ir '+b+'!',
    fx:'cheer'
  });
}
function noteNewDame(name){
  var w=String(name||'').trim().split(/\s+/)[0];
  if(!w || !isFemaleName(w)) return false;
  if(seenJoinNames[w]) return false;
  seenJoinNames[w]=true;
  if(pendingDames.indexOf(w)>=0) return false;
  pendingDames.push(w);
  if(pendingDames.length>=2){
    clearTimeout(dameBatchTimer); dameBatchTimer=null;
    var x=pendingDames.shift(), y=pendingDames.shift();
    announceTwoDames(x, y);
    return true;
  }
  clearTimeout(dameBatchTimer);
  dameBatchTimer=setTimeout(function(){
    dameBatchTimer=null;
    if(pendingDames.length===1){
      var one=pendingDames.shift();
      queueAnnounce('Ooo! Dama '+cuteName(one)+' su mumis! Sveikinam — paplokime!', {
        pose:'wink', bangs:0, applause:true,
        gestures:['wink','clap','wink'], bubble:'👏 '+one
      });
    }
  }, 45000);
  return true;
}
function maybeAnnounceNewJoins(st){
  // Prisijungimas keičia tik dalyvių sąrašą; balsinio sveikinimo nėra.
  clearTimeout(dameBatchTimer);
  pendingDames=[];
  return;
}
/* Trumpas profesionalus raginimas vardu — be atsitiktinių asmeninių prielaidų. */
function encourageBidLine(name){
  var n=String(name||'').trim().split(/\s+/)[0]||'drauge';
  var v=vocative(n);
  if(isFemaleName(n)){
    return pick([
      n+', tavo ėjimas — jei patinka, spausk KELTI!',
      v+', dar vienas euras ir tu priekyje!',
      n+', Vilkas mato gerą skonį — judam!',
      'Na ką, '+v+' — ar imam šitą lotą?'
    ]);
  }
  return pick([
    v+', tavo ėjimas — spausk KELTI!',
    n+', dar vienas euras ir tu priekyje!',
    n+', Vilkas laukia tavo ėjimo!',
    'Na ką, '+v+' — ar imam šitą lotą?'
  ]);
}
function pickEncourageTarget(){
  var names=(state && state.participant_names)||[];
  var lead=state && state.lot && state.lot.current_bidder;
  var lead0=lead ? String(lead).split(' ')[0] : '';
  var pool=names.filter(function(n){
    var w=String(n||'').split(' ')[0];
    return w && w!==lead0 && w!=='Mindaugas';
  });
  if(!pool.length) pool=names.filter(Boolean);
  return pool.length ? pick(pool) : null;
}
function otherParticipant(){
  return pickEncourageTarget();
}
var START_LINE='Pradedame! Minutė prasideda — spauskite KELTI mygtuką! Kas pirmas?';
var presented={}, armedLot=null, startFlashUntil=0, lastGreenN=null;
function splitList(s){ return String(s||'').split(/[;\n]+/).map(function(x){return x.trim();}).filter(Boolean); }
var CONDITION_WORDS={nauja:'visiškai nauja', kaip_nauja:'kaip nauja', gera:'geros būklės', naudota:'naudota, bet dar tarnaus'};
function showShowcase(lot){
  return; /* vidurinė prekės kortelė išjungta – viską apibūdina Vilkas */
  var sc=document.getElementById('showcase'); if(!sc) return;
  var img=document.getElementById('showcaseImg');
  if(lot.photo_file){ img.src='/photos/'+lot.photo_file; img.style.display='block'; } else img.style.display='none';
  document.getElementById('showcaseTitle').textContent=lot.title||'';
  var h='', d=0;
  function chip(cls, t){ h+='<span class="chip '+cls+'" style="animation-delay:'+(0.5+d*0.35)+'s">'+esc(t)+'</span>'; d++; }
  splitList(lot.pluses).forEach(function(p){ chip('plus','✅ '+p); });
  splitList(lot.defects).forEach(function(p){ chip('def','⚠️ '+p); });
  splitList(lot.included).forEach(function(p){ chip('inc','📦 '+p); });
  chip('price','Pradinė kaina '+fmt(lot.starting_price||lot.current_price)+' €');
  document.getElementById('showcaseChips').innerHTML=h;
  sc.classList.remove('hide'); restartClass(sc,'show');
}
function hideShowcase(){
  var sc=document.getElementById('showcase'); if(!sc || !sc.classList.contains('show')) return;
  sc.classList.remove('show'); restartClass(sc,'hide');
}
function presentLot(lot){
  presented[lot.id]=true;
  var pl=splitList(lot.pluses), df=splitList(lot.defects), inc=splitList(lot.included);
  var cond=CONDITION_WORDS[String(lot.condition||'').toLowerCase()]||'';
  var intro=pick(['O dabar — dėmesio!','Ponai ir ponios, žiūrėkit, ką turiu!','Tūkstantis perkūnų, koks lotas!','Paruoškit pinigines — ir širdis!'])+
    ' Lotas numeris '+lot.lot_number+' — '+lot.title+'!'+(cond?' Būklė — '+cond+'.':'');
  /* Retas asmeninis prisiminimas — ne prie kiekvieno loto. */
  if(Math.random()<0.28 && /(samsung|galaxy|iphone|nokia|motorola|alcatel|phone)/i.test(String(lot.title||''))){
    intro+=pick([
      ' Ooo, aš tokį turėjau prieš trejus metus!',
      'Ooo, toks telefonas man buvo rankose prieš trejus metus!',
      'Prisiminiau — prieš trejus metus su tokiu telefonu vaikščiojau!'
    ]);
  }
  var details='';
  if(pl.length) details+=' Pliusai: '+pl.slice(0,4).join(', ')+'.';
  if(df.length) details+=' Defektai, sąžiningai: '+df.slice(0,3).join(', ')+'. '+pick([
    'Viskas pasakyta atvirai — sprendimas jūsų.',
    'Maži niuansai, bet kaina tai žino.',
    'Nieko neslepiam — žinot, ką perkat.',
    'Būklė įvertinta sąžiningai, o daiktas dar turi parako.',
    'Svarbiausia — veikia ir laukia naujo šeimininko.'
  ]);
  else details+=' Defektų — nerasta, tikrinau su lupa!';
  if(inc.length) details+=' Pridedu: '+inc.slice(0,3).join(', ')+'.';
  var price=lot.starting_price||lot.current_price;
  var t1=intro+details, t2='Pradinė kaina — '+eurosWords(price)+'! Spauskite KELTI mygtuką — ruoškitės!';
  var brainPayload={
    lot_number:lot.lot_number, title:lot.title, description:lot.description||'',
    condition:cond, pluses:pl.join('; '), defects:df.join('; '), included:inc.join('; '),
    price:price, starting_price:price
  };
  if(coffeeActive) endCoffee();
  var waited=0;
  (function go(){
    if((announceBusy || announceQueue.length) && waited<50000){ waited+=300; return setTimeout(go, 300); }
    if(lot.starts_at*1000-Date.now() < 12000){ armedLot=lot.id; return; }
    Promise.all([Promise.resolve(t1), Promise.resolve(t2)]).then(function(lines){
      prefetchTts(lines[0]); prefetchTts(lines[1]); prefetchTts(START_LINE);
      runPresentation(lot, lines[0], lines[1], price);
    });
  })();
}
function runPresentation(lot, t1, t2, price){
  fanfareIntro();
  wolfPopShow('clap','🥁 Dėmesio! Naujas lotas!');
  setTimeout(function(){ welcomeWolfForLot(lot); }, 1000);
  startGestures(CLAP, 330);
  setTimeout(function(){
    stopGestures();
    queueAnnounce(t1, {tag:'present', pose:'present', cls:'side', keepCls:true, bangs:0, gestures:['present','welcome','present','thumb'],
      bubble:'🎤 Lotas #'+lot.lot_number+': '+lot.title});
    queueAnnounce(t2, {tag:'present', pose:'raise', cls:'side', bangs:1, fx:'cheer', gestures:['raise','welcome','raise'],
       bubble:'💰 Pradinė kaina '+fmt(price)+' €!', onSpeak:function(){ armedLot=lot.id; setTimeout(hideShowcase, 3500); }});
  }, 3300);
}
function maybePresent(lot){
  if(!lot || lot.status!=='live' || !lot.starts_at || presented[lot.id]) return;
  var r=lot.starts_at*1000-Date.now();
  if(r>16000) presentLot(lot);
  else { presented[lot.id]=true; armedLot=lot.id; }
}
function setBtn(cls, label, time){
  var b=els.bidBtn;
  ['armed','go-green','start-pop','hurry'].forEach(function(c){ if(c!==cls && !(cls==='hurry' && c==='hurry')) b.classList.remove(c); });
  if(cls && !b.classList.contains(cls)) b.classList.add(cls);
  if(label!=null){ els.bidLabel.textContent=label; }
}
function tickButton(){
  var lot=state && state.lot;
  if(!els.bidBtn) return;
  if(!lot || lot.status==='ended'){
    els.bidBtn.classList.remove('armed','go-green','start-pop','hurry');
    return;
  }
  if(state && state.auction_locked){
    return;
  }
  var now=Date.now();
  if(lot.starts_at && lot.starts_at*1000>now){
    var r=(lot.starts_at*1000-now)/1000;
    els.bidBtn.disabled=true;
    if(r>9.5){
      lastGreenN=null;
      if(armedLot===lot.id) setBtn('armed','KELTI KAINĄ +1 €');
      else setBtn(null,'🎤 Vilkas pristato…');
    } else {
      var n=Math.max(1,Math.ceil(r));
      if(lastGreenN===null){ armedLot=lot.id; hideShowcase(); }
      if(n!==lastGreenN){ lastGreenN=n; tickSound(); restartClass(els.bidBtn,'go-green'); }
      setBtn('go-green', String(n));
    }
    return;
  }
  if(lastGreenN!==null){
    lastGreenN=null; startFlashUntil=now+1300; startSound();
    announceQueue=announceQueue.filter(function(j){ return j.tag!=='present'; });
    hideShowcase();
  }
  if(now<startFlashUntil){
    setBtn('start-pop','🚀 START!');
    els.bidBtn.disabled=true;
    return;
  }
  var left=lot.ends_at ? Math.max(0, lot.ends_at*1000-now) : 60000;
  els.bidBtn.classList.remove('armed','go-green','start-pop');
  els.bidBtn.classList.toggle('hurry', left<10000);
  if(state && state.auction_locked){ els.bidBtn.disabled=true; return; }
  if(!myPid){
    els.bidBtn.disabled=true;
    els.bidLabel.textContent='Užsiregistruok';
    return;
  }
  if(lot.current_bidder===myNickname){
    els.bidBtn.disabled=true;
    els.bidLabel.textContent='👑 TU LYDERIAUJI';
  } else {
    els.bidBtn.disabled=false;
    els.bidLabel.textContent='KELTI KAINĄ +1 €';
  }
}
function watchSilence(){
  // DISABLED: server director owns this (nudge/phone/joke)
  return;
  var lot=state && state.lot;
  if(!lot || lot.status==='ended' || !lot.ends_at || (lot.starts_at && lot.starts_at*1000>Date.now())) return;
  if(silence.lotId!==lot.id){ silence={lotId:lot.id, bidAt:Date.now(), stage:0, finale:false}; return; }
  if(announceBusy || announceQueue.length || coffeeActive) return;
  var quiet=(Date.now()-silence.bidAt)/1000;
  var remain=(lot.ends_at*1000-Date.now())/1000;
  /* Paskutinės sekundės: nestabdom + vardas */
  if(!silence.finale && remain<=9 && remain>2){
    silence.finale=true;
    var who=pickEncourageTarget();
    var line='Nu kas pakels dar? Nu — nestabdom, nestabdo, judam!';
    if(who) line+=' '+encourageBidLine(who);
    var pose=who && isFemaleName(who) ? 'wink' : 'raise';
    queueAnnounce(line, {pose:pose, bangs:0, gestures:[pose,'welcome','raise'], bubble:'⏰ Nu kas pakels dar?'});
    return;
  }
  /* Viduryje tylos — vienas raginimas vardu (be bajeriukų / kavutės) */
  if(silence.stage===0 && quiet>12 && remain>18){
    silence.stage=1;
    var who2=pickEncourageTarget();
    if(who2){
      var pose2=isFemaleName(who2)?'wink':'thumb';
      queueAnnounce(encourageBidLine(who2), {
        pose:pose2, bangs:0,
        gestures:isFemaleName(who2)?['wink','glasses','wink']:['thumb','raise','thumb'],
        bubble:'👉 '+String(who2).split(' ')[0]
      });
    } else {
      wolfPopHideSoon(80);
    }
    return;
  }
  /* Ilgai niekas neperka — žemaitiškai arba skambutis */
  if(silence.stage===1 && quiet>26 && remain>14){
    silence.stage=2;
    if(Math.random()<0.45){
      playPhoneCallGag();
    } else {
      /* Ilgas lėtas LT tarimas — BE žodžio „tyla“ */
      var zem=pick([
        'Nu kas čia — keliam?',
        'Nu… kas čia? Keliam?',
        'Kas čia — keliam aukščiau?',
        'Nu kas čia — kas kels?',
        'Nu kas čia? Spauskit mygtuką — keliam!'
      ]);
      queueAnnounce(zem, {pose:'raise', bangs:0, gestures:['raise','welcome','raise'], bubble:'❓ Nu kas čia — keliam?', speed:0.7, fast:false});
    }
    return;
  }
  /* Dar tyla — kitas efektas (jei anksčiau nebuvo skambučio) */
  if(silence.stage===2 && quiet>38 && remain>12){
    silence.stage=3;
    if(Math.random()<0.55) playPhoneCallGag();
    else wolfPopHideSoon(80);
    return;
  }
  if(silence.stage===3 && quiet>50){
    silence.stage=4;
    wolfPopHideSoon(80);
  }
}
function doSilenceAct(lot, remain, key){
  wolfPopHideSoon(80);
}
function speakSold(name, price, lotId){
  var n=String(name||'').split(' ')[0]||'drauge';
  var line='Parduota! Plojimai!';
  queueAnnounce(line, {tag:'sold', pose:isFemaleName(name)?'wink':'welcome', bangsBefore:3, gong:true, bangs:0, after:'bow',
    fx:isFemaleName(name)?'heart':'cheer', gestures:CLAP.concat(isFemaleName(name)?['wink','glasses','wink']:['thumb','welcome']), gestureMs:380,
    bubble:'🏆 PARDUOTA! '+(isFemaleName(name)?'Gražuolė ':'Šaunuolis ')+n+'!',
    onSpeak:function(){ try{ celebrationSound(); }catch(e){} try{ photographedWolf('🏆 Parduota!', currentPose); }catch(e){} },
    onDone:function(){
      /* Kava TIK kai nėra kito loto — kitaip Vilkas turi IŠKART pristatyti lot_intro */
      try{
        for(var i=0;i<announceQueue.length;i++){
          if(announceQueue[i] && announceQueue[i].tag==='lot_intro') return;
        }
        if(announceBusy && announceCurrentJob && announceCurrentJob.tag==='lot_intro') return;
      }catch(e){}
      /* Be kito loto kavą paleidžia intermission handler (ne čia dubliuoti) */
    }});
}
function speakLotStart(){
  // DISABLED: server director owns this
  return;
  if(coffeeActive) endCoffee();
  queueAnnounce(START_LINE, {tag:'start', pose:'welcome', bangsBefore:1, gong:true, bangs:0, gestures:CLAP.concat(['raise']), bubble:'🔨 PRADEDAME! Kas pirmas?'});
}

var radioStarting = false;
/* Po Vilko kalbos radijas garsiau; kalbant — duck žemyn */
var MUSIC_DUCK_RATIO = 0.80;
var MUSIC_TARGET_VOL = 0.82;
var MUSIC_DUCK_VOL = MUSIC_TARGET_VOL*MUSIC_DUCK_RATIO;
var DESK_SONG_VOL = 0.86;
var radioTargetVol = MUSIC_TARGET_VOL;
var radioDuckVol = MUSIC_DUCK_VOL;
function syncPracticeMusicLevels(){
  /* Kalbant muzika sumažinama 20% nuo atitinkamo įprasto lygio. */
  radioTargetVol=practiceModeOn?0.88:0.82;
  radioDuckVol=radioTargetVol*MUSIC_DUCK_RATIO;
}
var radioFadeTimer = null;
var WOLF_VOICE_VOL = 0.81;
var WOLF_VOICE_BOOST = 1.75;
var WOLF_ECHO_DELAY_S = 0.26;
var WOLF_ECHO_GAIN = 0.18;
var wolfVoiceAudioContext = null;
var RADIO_STATIONS = [
  /* /radio/club = same-origin proxy — jokių geo/CORS blokų; fallback = tiesioginis upstream */
  {id:'club', name:'Bendruomenės klubas', url:'/radio/club', fallback:'https://streams.ilovemusic.de/iloveradio14.mp3', segment:'ilovepartyhard', fallbackSegment:'ilovepartyhard'},
  {id:'dance', name:'Šokiai', url:'https://stream.powerhitradio.lt/PHR_AAC', fallback:'https://stream.m-1.fm/m1/mp3', segment:'', fallbackSegment:''},
  {id:'m1', name:'M-1', url:'https://stream.m-1.fm/m1/mp3', fallback:'', segment:'', fallbackSegment:''}
];
var radioStationId = 'club';
var radioLabel = 'Bendruomenės klubas';
var radioUrlTry = 0;
var energyWatchTimer = null;
var slowEnergyStreak = 0;
var SLOW_ENERGY_SECONDS = 22;
var radioPeakHistory = [];

function getRadioEl(){
  return document.getElementById('vilkasRadioPlayer');
}
function getRadioStation(id){
  id=id||radioStationId;
  for(var i=0;i<RADIO_STATIONS.length;i++){
    if(RADIO_STATIONS[i].id===id) return RADIO_STATIONS[i];
  }
  return RADIO_STATIONS[0];
}
function radioStreamUrl(){
  var st=getRadioStation(radioStationId);
  return (radioUrlTry===1 && st.fallback) ? st.fallback : st.url;
}
function radioSrcMatches(el, url){
  if(!el || !url) return false;
  var cur=(el.currentSrc||el.src||'').split('?')[0];
  var want=String(url).split('?')[0];
  if(!cur || !want) return false;
  if(cur===want || cur.indexOf(want)>=0 || want.indexOf(cur)>=0) return true;
  /* relative /radio/club vs absolute https://host/radio/club */
  try{
    if(want.charAt(0)==='/' && cur.indexOf(want)>=0) return true;
    if(want.indexOf('/radio/club')>=0 && cur.indexOf('/radio/club')>=0) return true;
  }catch(e){}
  return false;
}
/* Srautas gyvas (gali būti muted — Chrome autoplay) */
function radioHasLiveStream(){
  var el=getRadioEl();
  if(!el) return false;
  var src=el.currentSrc||el.src||'';
  return !!src && !el.paused && !el.ended;
}
/* Žmogus GIRDI */
function radioIsPlaying(){
  var el=getRadioEl();
  if(!el) return false;
  return radioHasLiveStream() && !el.muted && Number(el.volume||0)>0.01;
}
/* Unmute + volume — NENAIKINTI src (teardown = tyla iki bufferio) */
function makeRadioAudibleNow(){
  if(stageMusicMuted()){ muteMusicForStage(); return false; }
  if(deskSongOn) return false;
  var el=getRadioEl();
  if(!el || !musicOn) return false;
  if(document.visibilityState==='hidden') return false;
  if(isCoverMode()){ try{ claimAudioMaster(true); }catch(e){} }
  else if(vilkasStageOn){ if(!isAudioMaster()) return false; }
  else { try{ claimAudioMaster(true); }catch(e){} }
  try{
    el.muted=false;
    el.defaultMuted=false;
    el.removeAttribute('muted');
    el.volume=radioVolumeForCurrentState();
  }catch(e){}
  if(!radioHasLiveStream()){
    try{ startMusic(true); }catch(e){}
    return radioIsPlaying();
  }
  try{
    var p=el.play();
    if(p && p.catch) p.catch(function(){});
  }catch(e){}
  return radioIsPlaying();
}
function forceRadioAudible(){ return makeRadioAudibleNow(); }
/* Palaikyti srautą: jei jau groja (net muted) — NELIESTI src */
function keepRadioAlive(){
  if(stageMusicMuted()){ muteMusicForStage(); return; }
  if(deskSongOn){
    try{ softPauseRadioKeepSrc(); }catch(e){}
    var rr=getRadioEl();
    if(rr){ try{ rr.muted=true; rr.volume=0; }catch(e2){} }
    var s=getDeskSongEl();
    if(s && (s.paused || s.ended)){
      try{ var ps=s.play(); if(ps&&ps.catch) ps.catch(function(){}); }catch(e3){}
    }
    return;
  }
  var el=getRadioEl();
  if(!el || !musicOn) return;
  if(document.visibilityState==='hidden') return;
  if(isCoverMode()){ try{ claimAudioMaster(true); }catch(e){} }
  else if(vilkasStageOn){
    if(!isAudioMaster()) return;
    try{ localStorage.setItem(AUDIO_MASTER_KEY,JSON.stringify({id:audioTabId,at:Date.now()})); }catch(e){}
  } else { try{ claimAudioMaster(true); }catch(e){} }
  var url=radioStreamUrl();
  if(radioHasLiveStream() && radioSrcMatches(el, url)){
    /* jau bufferina/groja — bandyti unmute (be gesto Chrome gali atmesti — OK) */
    try{
      el.muted=false;
      el.defaultMuted=false;
      el.removeAttribute('muted');
      el.volume=radioVolumeForCurrentState();
    }catch(e){}
    try{ var p=el.play(); if(p&&p.catch) p.catch(function(){}); }catch(e){}
    return;
  }
  if(!radioStarting) try{ startMusic(true); }catch(e){}
}
function pauseRadio(){
  hardKillRadio();
}
function resumeRadio(steal){
  if(!musicOn) return;
  if(document.visibilityState==='hidden') return;
  pageAudioOk=true;
  if(!isAudioMaster() && !claimAudioMaster(steal)) return;
  if(!isAudioMaster()) return;
  if(radioIsPlaying() || radioStarting) return;
  startMusic(steal);
}
function stopEnergyWatch(){
  if(energyWatchTimer){ clearInterval(energyWatchTimer); energyWatchTimer=null; }
  slowEnergyStreak=0;
  radioPeakHistory=[];
}
/* Diskotekos fonas įžangoje — zibintai pagal muzikos taktą */
var discoRaf=null, discoPrevBass=0, discoHue=0, discoLastBeat=0;
/* Vienas captureStream visam — ne dubliuoti garsą */
var radioAnalyserCtx=null, radioAnalyserSrc=null, radioAnalyserNode=null;
function releaseRadioAnalyser(){
  try{ if(radioAnalyserSrc) radioAnalyserSrc.disconnect(); }catch(e){}
  radioAnalyserSrc=null; radioAnalyserNode=null;
  try{ if(radioAnalyserCtx && radioAnalyserCtx.state!=='closed') radioAnalyserCtx.close(); }catch(e){}
  radioAnalyserCtx=null;
}
function getRadioAnalyser(){
  /* Įžangoje captureStream + šokėjų mp4 = Chrome stabdo vaizdą. Tik fake beat. */
  try{
    if(document.body.classList.contains('cover-mode') && document.querySelector('.dd-video')){
      return null;
    }
  }catch(e){}
  if(!radioIsPlaying()) return null;
  if(radioAnalyserNode) return radioAnalyserNode;
  var el=getRadioEl();
  if(!el || typeof el.captureStream!=='function') return null;
  try{
    radioAnalyserCtx=new (window.AudioContext||window.webkitAudioContext)();
    radioAnalyserSrc=radioAnalyserCtx.createMediaStreamSource(el.captureStream());
    radioAnalyserNode=radioAnalyserCtx.createAnalyser();
    radioAnalyserNode.fftSize=2048;
    radioAnalyserNode.smoothingTimeConstant=0.72;
    radioAnalyserSrc.connect(radioAnalyserNode);
    if(radioAnalyserCtx.state==='suspended') radioAnalyserCtx.resume();
  }catch(e){ releaseRadioAnalyser(); return null; }
  return radioAnalyserNode;
}
function keepDancerVideoAlive(){
  if(!document.body.classList.contains('cover-mode')) return;
  if(document.visibilityState==='hidden') return;
  try{
    document.querySelectorAll('.dd-video').forEach(function(v){
      try{
        v.muted=true; v.defaultMuted=true; v.loop=true; v.playsInline=true;
        v.setAttribute('playsinline',''); v.setAttribute('muted','');
        var spin=v.closest?v.closest('.dd-spin'):null;
        if(spin && v.dataset.swapBusy!=='1' && spin.style.opacity==='0') spin.style.opacity='1';
        if(v.paused || v.ended){
          var p=v.play();
          if(p&&p.catch) p.catch(function(){});
        }
      }catch(e){}
    });
  }catch(e){}
}
setInterval(keepDancerVideoAlive, 700);
var discoDancers=[], discoBeatBoost=0;
function lerp(a,b,t){ return a+(b-a)*t; }
function initDiscoDancers(){
  if(discoDancers.length) return;
  document.querySelectorAll('.disco-dancer').forEach(function(el,i){
    discoDancers.push({
      spin:el.querySelector('.dd-spin'),
      idx:i,
      seed:i*1.37+0.4,
      sway:0, bob:0, lean:0, skew:0, stretch:1,
      tSway:0, tBob:0, tLean:0, tSkew:0, tStretch:1
    });
  });
}
function updateDiscoDancers(strength,onBeat){
  initDiscoDancers();
  if(!discoDancers.length) return;
  var t=performance.now()/1000;
  var s=Math.max(0.35, Math.min(1.2, strength||0.45));
  if(onBeat) discoBeatBoost=1;
  discoBeatBoost*=0.90;
  var pulse=discoBeatBoost;
  discoDancers.forEach(function(d){
    var p=d.seed;
    /* VOS VOS — rėmelis beveik stovi (Mindaugas: anksčiau nesisiūbavo stipriai). */
    d.tSway = Math.sin(t*(1.4+p*0.15)+p)*1.6*s;
    d.tBob = 0.4 + (0.5+0.5*Math.sin(t*(3.2+p*0.2)+p*2.0))*1.4*s + pulse*1.2;
    d.tLean = Math.sin(t*(1.2+p*0.12)+p*0.8)*0.22*s;
    d.tSkew = 0;
    d.tStretch = 1 + pulse*0.006;
    var ease=0.06;
    d.sway=lerp(d.sway,d.tSway,ease);
    d.bob=lerp(d.bob,d.tBob,ease);
    d.lean=lerp(d.lean,d.tLean,ease);
    d.stretch=lerp(d.stretch,d.tStretch,ease);
    if(d.spin) d.spin.style.transform='translate('+d.sway.toFixed(1)+'px,'+(-d.bob).toFixed(1)+'px) rotate('+d.lean.toFixed(2)+'deg) scale('+d.stretch.toFixed(3)+')';
  });
  try{
    document.querySelectorAll('.dd-video').forEach(function(v){
      if(v.paused){ var pr=v.play(); if(pr&&pr.catch) pr.catch(function(){}); }
    });
  }catch(e){}
}
function resetDiscoDancers(){
  discoDancers=[]; discoBeatBoost=0;
}
function setDiscoVisible(on){
  var f=document.getElementById('discoField');
  if(!f) return;
  var show=!!on && document.body.classList.contains('cover-mode') && document.visibilityState!=='hidden';
  f.classList.toggle('on', show);
  f.setAttribute('aria-hidden', show?'false':'true');
  if(!show) f.classList.remove('beat');
}
function stopDiscoBeat(){
  if(discoRaf){ try{ cancelAnimationFrame(discoRaf); }catch(e){} discoRaf=null; }
  try{ if(typeof dancerTimer!=='undefined'&&dancerTimer){ clearTimeout(dancerTimer); dancerTimer=null; } }catch(e){}
  setDiscoVisible(false);
  discoPrevBass=0;
  resetDiscoDancers();
}
function startDiscoBeat(){
  if(discoRaf) return; /* jau veikia — neperkrauti */
  if(!document.body.classList.contains('cover-mode')) return;
  setDiscoVisible(true);
  var spots=document.querySelectorAll('#discoField .disco-spot');
  var beams=document.querySelectorAll('#discoField .disco-beam');
  var field=document.getElementById('discoField');
  var fakePhase=0;
  function pulseBeat(strength){
    var now=performance.now();
    if(now-discoLastBeat<140) return;
    discoLastBeat=now;
    if(!field) return;
    field.classList.remove('beat');
    void field.offsetWidth;
    field.classList.add('beat');
    discoHue=(discoHue+37+(strength*40))%360;
    /* klubo spalva — seka video foną (auto hue), default mėlyna */
    var DH=(typeof window.__DH==='number')?window.__DH:212;
    var cols=[
      'hsla('+DH+',100%,60%,.68)',
      'hsla('+((DH+340)%360)+',100%,55%,.62)',
      'hsla('+((DH+20)%360)+',100%,64%,.62)',
      'hsla('+((DH+350)%360)+',100%,72%,.55)',
      'hsla('+((DH+40)%360)+',100%,66%,.58)'
    ];
    for(var i=0;i<spots.length;i++) spots[i].style.background=cols[i%cols.length];
    for(var b=0;b<beams.length;b++){
      beams[b].style.opacity=String(0.2+strength*0.55);
      beams[b].style.transform='rotate('+((-18+b*14)+strength*8)+'deg)';
    }
    try{ updateDiscoDancers(strength,true); }catch(e){}
  }
  function tick(){
    discoRaf=requestAnimationFrame(tick);
    if(!document.body.classList.contains('cover-mode') || document.visibilityState==='hidden'){
      setDiscoVisible(false);
      return;
    }
    setDiscoVisible(true);
    var bass=0, strength=0.35, radioLive=radioIsPlaying();
    var analyser=radioLive ? getRadioAnalyser() : null;
    if(analyser && radioLive){
      try{
        if(radioAnalyserCtx && radioAnalyserCtx.state==='suspended') radioAnalyserCtx.resume();
        var freq=new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(freq);
        var n=Math.min(24, freq.length), sum=0;
        for(var i=0;i<n;i++) sum+=freq[i];
        bass=sum/(n*255);
        strength=Math.min(1, bass*1.8);
        if(bass>0.12 && bass>discoPrevBass*1.12) pulseBeat(strength);
        discoPrevBass=bass*0.82+discoPrevBass*0.18;
      }catch(e){}
    } else {
      /* fallback — ~120 BPM pulsas jei analyser neprieinamas */
      fakePhase+=1;
      if(fakePhase%28===0) pulseBeat(0.55);
    }
    /* švelnus nuolatinis judesys */
    for(var s=0;s<spots.length;s++){
      var o=0.35+strength*0.45+(Math.sin(performance.now()/400+s)*0.08);
      spots[s].style.opacity=String(Math.max(0.2, Math.min(0.85, o)));
    }
    try{ updateDiscoDancers(strength,false); }catch(e){}
  }
  discoRaf=requestAnimationFrame(tick);
}
/* Auto lėta→šokiai BE MediaElementSource (jis nutildydavo).
   Naudojam WebAudio Analyser ant atskiro MediaStream, jei browser palaiko captureStream. */
function startEnergyWatch(){
  stopEnergyWatch();
  if(radioStationId!=='club') return;
  energyWatchTimer=setInterval(function(){
    if(document.visibilityState==='hidden' || !isAudioMaster() || !musicOn) return;
    if(radioStationId!=='club' || !radioIsPlaying()){ slowEnergyStreak=0; return; }
    /* Įžangoje be captureStream — vaizdas prioritetas */
    try{ if(document.body.classList.contains('cover-mode') && document.querySelector('.dd-video')) return; }catch(e){}
    var analyser=getRadioAnalyser();
    if(!analyser) return;
    try{
      if(radioAnalyserCtx && radioAnalyserCtx.state==='suspended') radioAnalyserCtx.resume();
      var buf=new Uint8Array(analyser.fftSize);
      analyser.getByteTimeDomainData(buf);
      var sum=0, peak=0;
      for(var i=0;i<buf.length;i++){
        var v=Math.abs((buf[i]-128)/128);
        sum+=v*v;
        if(v>peak) peak=v;
      }
      var rms=Math.sqrt(sum/buf.length);
      radioPeakHistory.push(rms);
      if(radioPeakHistory.length>8) radioPeakHistory.shift();
      var avg=0;
      for(var j=0;j<radioPeakHistory.length;j++) avg+=radioPeakHistory[j];
      avg/=radioPeakHistory.length;
      /* Lėta = žemas RMS ilgiau; tik jei tikrai girdim signalą */
      if(avg>0.002 && avg<0.04){
        slowEnergyStreak++;
        if(slowEnergyStreak>=SLOW_ENERGY_SECONDS){
          slowEnergyStreak=0;
          stopEnergyWatch();
          selectRadioStation('dance', true);
        }
      } else if(avg>=0.04){
        slowEnergyStreak=0;
      }
    }catch(e){}
  },1000);
}
function renderRadioChoices(){
  var el=document.getElementById('radioBadge');
  if(!el){
    el=document.createElement('div');
    el.id='radioBadge';
    el.className='radio-badge';
    document.body.appendChild(el);
  }
  /* Tik Klubas ženklelis — Šokiai auto fone, mygtuko nerodom */
  el.setAttribute('aria-label','Klubinė muzika');
  el.innerHTML='<button class="radio-choice active" type="button" data-radio="club"><span class="rb-top">klubo</span><span class="rb-mid">Bendruomenė</span></button>';
}
function setRadioBadge(){
  renderRadioChoices();
}
function selectRadioStation(id, fromAuto){
  var st=getRadioStation(id);
  if(!st) return;
  if(st.id===radioStationId && (radioIsPlaying() || radioStarting) && !fromAuto) return;
  pageAudioOk=true;
  radioArmed=true;
  musicOn=true;
  radioStationId=st.id;
  radioLabel=st.name;
  radioUrlTry=0;
  claimAudioMaster(true);
  setRadioBadge();
  hardKillRadio();
  startMusic(true);
}
document.addEventListener('click', function(ev){
  var btn=ev.target && ev.target.closest ? ev.target.closest('[data-radio]') : null;
  if(!btn) return;
  ev.preventDefault();
  selectRadioStation(btn.getAttribute('data-radio')||'club', false);
});

function startMusic(steal){
  if(stageMusicMuted()){ muteMusicForStage(); return; }
  if(deskSongOn) return;
  if(!musicOn) return;
  if(document.visibilityState==='hidden') return;
  pageAudioOk=true;
  var cover=isCoverMode();
  if(cover){ try{ claimAudioMaster(true); }catch(e){} }
  else if(!isAudioMaster() && !claimAudioMaster(!!steal)) return;
  if(radioStarting) return;
  var el=getRadioEl();
  if(!el) return;
  var st=getRadioStation(radioStationId);
  var url=(radioUrlTry===1 && st.fallback) ? st.fallback : st.url;
  /* JAU gyvas srautas tuo pačiu URL — NENAIKINTI (teardown = tyla). Tik unmute. */
  if(radioHasLiveStream() && radioSrcMatches(el, url)){
    radioArmed=true;
    radioLabel=st.name;
    try{ setRadioBadge(); }catch(e){}
    try{
      el.muted=false;
      el.defaultMuted=false;
      el.removeAttribute('muted');
      el.volume=(radioVolumeForCurrentState());
    }catch(e){}
    try{ var p0=el.play(); if(p0&&p0.catch) p0.catch(function(){}); }catch(e){}
    if(st.id==='club'){ try{ startEnergyWatch(); }catch(e){} }
    try{ startDiscoBeat(); }catch(e){}
    return;
  }
  radioArmed=true;
  radioStarting=true;
  shoutKillOthers();
  stopEnergyWatch();
  releaseRadioAnalyser();
  /* NENAIKINTI src jei jau tas pats URL — tik play */
  var needReload=!radioSrcMatches(el, url);
  if(needReload){
    try{
      el.pause();
      el.onplaying=null;
      el.onerror=null;
      el.removeAttribute('crossorigin');
      el.removeAttribute('src');
      el.load();
    }catch(e){}
    el.src=url;
  }
  el.volume=(radioVolumeForCurrentState());
  el.onplaying=function(){
    radioStarting=false;
    radioLabel=st.name;
    setRadioBadge();
    try{
      el.muted=false;
      el.defaultMuted=false;
      el.removeAttribute('muted');
      el.volume=(radioVolumeForCurrentState());
    }catch(e){}
    if(st.id==='club') startEnergyWatch();
    else stopEnergyWatch();
    try{ startDiscoBeat(); }catch(e){}
  };
  el.onerror=function(){
    if(radioUrlTry===0 && st.fallback){
      radioUrlTry=1;
      radioStarting=false;
      setTimeout(function(){ if(musicOn) startMusic(true); }, 200);
      return;
    }
    radioStarting=false;
    stopEnergyWatch();
    try{ stopDiscoBeat(); }catch(e){}
    if(st.id==='club'){
      radioStationId='dance';
      radioLabel='Šokiai';
      radioUrlTry=0;
      setRadioBadge();
      setTimeout(function(){ if(musicOn) startMusic(true); }, 250);
    }
  };
  function afterPlayOk(){
    radioStarting=false;
    try{
      el.muted=false;
      el.defaultMuted=false;
      el.removeAttribute('muted');
      el.volume=(radioVolumeForCurrentState());
    }catch(e){}
  }
  function playMutedFallback(){
    /* Chrome leidžia muted autoplay — srautas bufferina; gestas = garsas iškart */
    try{
      el.muted=true;
      var pm=el.play();
      if(pm && pm.then){
        pm.then(function(){ radioStarting=false; }).catch(function(){ radioStarting=false; });
      } else { radioStarting=false; }
    }catch(e){ radioStarting=false; }
  }
  try{
    el.muted=false;
    el.defaultMuted=false;
    el.removeAttribute('muted');
    var p=el.play();
    if(p && p.then){
      p.then(afterPlayOk).catch(function(){
        playMutedFallback();
      });
    } else {
      radioStarting=false;
    }
  }catch(e){
    playMutedFallback();
  }
}

function stopMusic(){
  hardKillRadio();
}

function setMusicDuck(ducking){
  var shouldDuck = !!ducking || !!vilkasStageOn;
  try{
    var ds=getDeskSongEl();
    if(ds && deskSongOn){ ds.volume = vilkasStageOn ? DESK_SONG_VOL*0.10 : (shouldDuck ? DESK_SONG_VOL*MUSIC_DUCK_RATIO : DESK_SONG_VOL); }
  }catch(e){}
  var el=getRadioEl();
  if(!el) return;
  var target = (!musicOn || deskSongOn || stageMusicMuted()) ? 0 : (vilkasStageOn ? radioTargetVol*0.10 : (shouldDuck ? radioDuckVol : radioTargetVol));
  if(radioFadeTimer) clearInterval(radioFadeTimer);
  radioFadeTimer = setInterval(function(){
    var r=getRadioEl();
    if(!r){ clearInterval(radioFadeTimer); return; }
    var cur = r.volume;
    var step = 0.018;
    if(Math.abs(cur - target) <= step){
      r.volume = target;
      clearInterval(radioFadeTimer);
    } else if(cur < target){
      r.volume = Math.min(target, cur + step);
    } else {
      r.volume = Math.max(target, cur - step);
    }
  }, 40);
}

function syncMusicBtn(){
  musicOn = true;
}
/* ---- šokėjų rotacija kas 5–10 min + fono auto-prisitaikymas pagal video ---- */
var dancerDeck=[], dancerDeckPos=0, dancerCurrentUrl='', dancerTimer=null, dancerProbed=false;
window.__DH=212;
function discoSetHue(h){
  h=((Math.round(h)%360)+360)%360; window.__DH=h;
  var f=document.getElementById('discoField'); if(!f) return;
  try{
    f.style.setProperty('--dh',h);
    f.style.setProperty('--dhA',(h+340)%360);
    f.style.setProperty('--dhB',(h+20)%360);
  }catch(e){}
}
function discoSampleHue(video){
  try{
    var c=document.createElement('canvas'); c.width=48; c.height=27;
    var x=c.getContext('2d',{willReadFrequently:true});
    x.drawImage(video,0,0,48,27);
    var d=x.getImageData(0,0,48,27).data, sh=0, ss=0;
    for(var i=0;i<d.length;i+=4){
      var r=d[i]/255,g=d[i+1]/255,b=d[i+2]/255;
      var mx=Math.max(r,g,b),mn=Math.min(r,g,b),df=mx-mn;
      if(mx<0.16||df<0.12) continue;
      var h=0;
      if(df){ if(mx===r) h=((g-b)/df)%6; else if(mx===g) h=(b-r)/df+2; else h=(r-g)/df+4; h*=60; if(h<0)h+=360; }
      var w=df*mx; sh+=h*w; ss+=w;
    }
    if(ss>0.5) discoSetHue(sh/ss);
  }catch(e){}
}
var DANCER_WHITELIST=["/photos/dance_club_1.mp4","/photos/dance_club_2.mp4","/photos/dance_club_3.mp4","/photos/dance_club_4.mp4","/photos/dance_club_5.mp4","/photos/dance_club_6.mp4","/photos/dance_club_7.mp4","/photos/dance_club_8.mp4","/photos/dance_club_9.mp4","/photos/dance_club_10.mp4","/photos/dance_club_11.mp4","/photos/dance_club_12.mp4","/photos/dance_club_14.mp4","/photos/dance_club_15.mp4","/photos/dance_club_17.mp4","/photos/dance_club_18.mp4","/photos/dance_club_19.mp4","/photos/dance_club_20.mp4","/photos/dance_club_21.mp4","/photos/dance_club_22.mp4","/photos/dance_club_23.mp4","/photos/dance_club_24.mp4","/photos/dance_club_25.mp4","/photos/dance_club_26.mp4","/photos/dance_club_27.mp4","/photos/dance_club_28.mp4","/photos/dance_club_29.mp4","/photos/dance_club_30.mp4","/photos/dance_club_31.mp4","/photos/dance_club_32.mp4","/photos/dance_club_33.mp4","/photos/dance_club_34.mp4","/photos/dance_club_35.mp4","/photos/dance_club_36.mp4","/photos/dance_club_37.mp4","/photos/dance_club_38.mp4","/photos/dance_club_39.mp4","/photos/dance_club_40.mp4","/photos/dance_club_41.mp4","/photos/dance_club_42.mp4","/photos/dance_club_43.mp4"];
function dancerShuffle(arr){
  for(var i=arr.length-1;i>0;i--){
    var j=Math.floor(Math.random()*(i+1));
    var tmp=arr[i]; arr[i]=arr[j]; arr[j]=tmp;
  }
  return arr;
}
function dancerCacheBust(url){
  /* STABILUS kešas vieno deploy viduje — Date.now LAUŽĖ kešą ir vėlavo kiekvienas swap.
     PAGE_BUILD keičiasi tik per deploy, todėl video kraunasi iš kešo akimirksniu. */
  var q=String(url||'').indexOf('?');
  var base=(q>=0?String(url).slice(0,q):String(url));
  var ver='1';
  try{ ver=String(window.PAGE_BUILD||document.querySelector('meta[name="build"]')?.content||'1').slice(0,24); }catch(e){}
  return base+'?v='+encodeURIComponent(ver);
}
var dancerPreloadEl=null, dancerPreloadUrl='';
function dancerPreloadNext(){
  try{
    if(!document.body.classList.contains('cover-mode')) return;
    var nxt=dancerDeck[dancerDeckPos]||'';
    if(!nxt||nxt===dancerCurrentUrl||nxt===dancerPreloadUrl) return;
    if(!dancerPreloadEl){
      dancerPreloadEl=document.createElement('video');
      dancerPreloadEl.muted=true; dancerPreloadEl.loop=true;
      dancerPreloadEl.playsInline=true; dancerPreloadEl.preload='auto';
      dancerPreloadEl.setAttribute('playsinline',''); dancerPreloadEl.setAttribute('muted','');
      dancerPreloadEl.style.display='none';
      try{document.body.appendChild(dancerPreloadEl);}catch(e){}
    }
    dancerPreloadUrl=nxt;
    dancerPreloadEl.src=dancerCacheBust(nxt);
    try{ dancerPreloadEl.load(); }catch(e){}
  }catch(e){}
}
setInterval(function(){ try{ dancerPreloadNext(); }catch(e){} }, 8000);
function dancerSaveState(){
  try{
    localStorage.setItem('dancer_deck', JSON.stringify(dancerDeck||[]));
    localStorage.setItem('dancer_pos', String(dancerDeckPos||0));
  }catch(e){}
}
function dancerLoadState(){
  try{
    var raw=localStorage.getItem('dancer_deck')||'';
    var pos=parseInt(localStorage.getItem('dancer_pos')||'0',10)||0;
    if(!raw) return false;
    var arr=JSON.parse(raw);
    if(!arr||!arr.length) return false;
    /* palikti tik whitelist video — apsauga nuo senų/pašalintų URL */
    var ok=[];
    for(var i=0;i<arr.length;i++){ if(DANCER_WHITELIST.indexOf(arr[i])>=0) ok.push(arr[i]); }
    if(!ok.length) return false;
    /* jei deck trumpas (sena versija) — pratęsti trūkstamais be dublio */
    if(ok.length<DANCER_WHITELIST.length){
      var rest=[];
      for(var k=0;k<DANCER_WHITELIST.length;k++){ if(ok.indexOf(DANCER_WHITELIST[k])<0) rest.push(DANCER_WHITELIST[k]); }
      ok=ok.concat(dancerShuffle(rest));
    }
    if(pos<0) pos=0; if(pos>ok.length) pos=ok.length;
    dancerDeck=ok; dancerDeckPos=pos;
    return true;
  }catch(e){ return false; }
}
function dancerUpdateCount(){
  try{
    var el=document.getElementById('dancerCount'); if(!el) return;
    var total=(typeof DANCER_WHITELIST!=='undefined'&&DANCER_WHITELIST.length)?DANCER_WHITELIST.length:15;
    var n=dancerDeckPos||0; if(n<1) n=1; if(n>total) n=total;
    el.textContent=n+'/'+total;
  }catch(e){}
}
function dancerRefillDeck(excludeBase){
  dancerDeck=dancerShuffle(DANCER_WHITELIST.slice());
  dancerDeckPos=0;
  if(excludeBase&&dancerDeck.length>1&&dancerDeck[0]===excludeBase){
    for(var i=1;i<dancerDeck.length;i++){
      if(dancerDeck[i]!==excludeBase){
        var t=dancerDeck[0]; dancerDeck[0]=dancerDeck[i]; dancerDeck[i]=t;
        break;
      }
    }
  }
  dancerSaveState();
}
function dancerTakeNext(excludeBase){
  if(!dancerDeck.length||dancerDeckPos>=dancerDeck.length) dancerRefillDeck(excludeBase||'');
  if(excludeBase&&dancerDeck.length>1&&dancerDeck[dancerDeckPos]===excludeBase){
    dancerDeckPos++;
    if(dancerDeckPos>=dancerDeck.length) dancerRefillDeck(excludeBase);
  }
  return dancerDeck[dancerDeckPos]||'';
}
function dancerCommitNext(){ dancerDeckPos++; dancerSaveState(); dancerUpdateCount(); }
/* Serveris nusprendžia šokėją — VISI ekranai tą pačią (PC = telefonas). */
var dancerServerSeenAt=0;
function dancerBase(u){ return String(u||'').split('?')[0]; }
function applyServerDancer(st){
  try{
    var d=st&&st.dancer?st.dancer:null;
    if(!d||!d.url) return;
    if(!document.body.classList.contains('cover-mode')) return;
    dancerServerSeenAt=Date.now();
    var base=String(d.url);
    if(dancerBase(dancerCurrentUrl)===dancerBase(base)){
      try{
        var el=document.getElementById('dancerCount');
        if(el&&d.n) el.textContent=d.n+'/'+(d.total||DANCER_WHITELIST.length);
      }catch(e){}
      return;
    }
    if(dancerApplyNow(base)){
      try{
        var idx=(typeof d.idx==='number')?d.idx:-1;
        if(idx<0){ for(var i=0;i<DANCER_WHITELIST.length;i++){ if(DANCER_WHITELIST[i]===base){ idx=i; break; } } }
        if(idx>=0){
          var order=[];
          for(var k=1;k<=DANCER_WHITELIST.length;k++){ order.push(DANCER_WHITELIST[(idx+k)%DANCER_WHITELIST.length]); }
          dancerDeck=order; dancerDeckPos=0; dancerSaveState();
        }
        var el2=document.getElementById('dancerCount');
        if(el2&&d.n) el2.textContent=d.n+'/'+(d.total||DANCER_WHITELIST.length);
        dancerPreloadUrl='';
        setTimeout(function(){ dancerPreloadNext(); },800);
      }catch(e){}
    }
  }catch(e){}
}
window.addEventListener('keydown',function(e){
  try{ if(e&&e.key==='F5'){ navigator.sendBeacon('/api/dancer/next'); } }catch(_){}
});
function dancerApplyNow(baseUrl,retry){
  if(!baseUrl) return false;
  var v=document.querySelector('.dd-video'); if(!v) return false;
  var target=dancerCacheBust(baseUrl);
  try{ v.src=target; v.load(); var p=v.play(); if(p&&p.catch)p.catch(function(){}); }catch(e){
    if(!retry) return dancerApplyNow(baseUrl,true);
    return false;
  }
  dancerCurrentUrl=baseUrl;
  try{ localStorage.setItem('dancer_last', baseUrl); }catch(e){}
  try{ dancerUpdateCount(); }catch(e){}
  setTimeout(function(){ try{ discoSampleHue(v); }catch(e){} },1200);
  return true;
}
function dancerEnsurePlaying(){
  if(dancerCurrentUrl) return;
  fetch('/api/dancer',{cache:'no-store'}).then(function(r){return r.json();}).then(function(d){
    applyServerDancer({dancer:d&&d.dancer});
    if(!dancerCurrentUrl){
      var next=dancerTakeNext('');
      if(next&&dancerApplyNow(next)) dancerCommitNext();
    }
  }).catch(function(){
    if(dancerCurrentUrl) return;
    var next=dancerTakeNext('');
    if(next&&dancerApplyNow(next)) dancerCommitNext();
  });
}
function dancerOnPoolReady(){
  /* Transliacija VIENA: šokėją parenka serveris (/photos dance_club).
     PC ir telefonas seka tą patį URL — ne localStorage deck. */
  dancerEnsurePlaying();
}
function dancerProbePool(){
  if(dancerProbed) return;
  dancerProbed=true;
  dancerOnPoolReady();
  /* NEBE-probe'inam visų 15 iš karto — tai ir vėlino startą (15x lygiagretus fetch).
     Užtenka preload next; whitelist jau patikrintas serveryje. */
  try{ setTimeout(function(){ dancerPreloadNext(); }, 2500); }catch(e){}
}
function dancerSchedule(){
  if(dancerTimer){ try{clearTimeout(dancerTimer);}catch(e){} dancerTimer=null; }
  dancerTimer=setTimeout(dancerSwap,(2+Math.random()*1)*60000);
}
function dancerSwap(){
  if(!document.body.classList.contains('cover-mode')||document.visibilityState==='hidden'){ dancerSchedule(); return; }
  var v=document.querySelector('.dd-video'); if(!v){ dancerSchedule(); return; }
  if(v.dataset.swapBusy==='1'){ dancerSchedule(); return; }
  /* NEkeisti lokaliai — visiems viena šokėja iš serverio */
  fetch('/api/dancer',{cache:'no-store'}).then(function(r){return r.json();}).then(function(d){
    applyServerDancer({dancer:d&&d.dancer});
    dancerSchedule();
  }).catch(function(){ dancerSchedule(); });
}
function startDancerRotation(){
  dancerProbePool();
  dancerEnsurePlaying();
  try{ discoSetHue(212); }catch(e){}
  if(dancerTimer) return;
  dancerSchedule();
}
setTimeout(function(){ try{ dancerProbePool(); }catch(e){} },4000);
var introMediaRetry=null;
function ensureIntroMedia(steal){
  if(!document.body.classList.contains('cover-mode')) return;
  try{ releaseRadioAnalyser(); }catch(e){} /* atlaisvinti captureStream — vaizdas nestabdytų */
  try{ if(!discoRaf) startDiscoBeat(); }catch(e){}
  try{ if(typeof startDancerRotation==='function') startDancerRotation(); }catch(e){}
  try{ keepDancerVideoAlive(); }catch(e){}
  if(document.visibilityState==='hidden') return;
  pageAudioOk=true;
  radioArmed=true;
  musicOn=true;
  claimAudioMaster(true);
  try{ setRadioBadge(); }catch(e){}
  try{ keepRadioAlive(); }catch(e){}
  if(radioHasLiveStream() && !discoRaf){
    try{ startDiscoBeat(); }catch(e){}
  }
  if(introMediaRetry) return;
  introMediaRetry=setInterval(function(){
    if(!document.body.classList.contains('cover-mode')){
      clearInterval(introMediaRetry); introMediaRetry=null; return;
    }
    try{ if(typeof startDancerRotation==='function') startDancerRotation(); }catch(e){}
    if(document.visibilityState==='hidden') return;
    pageAudioOk=true;
    claimAudioMaster(true);
    try{ if(!discoRaf) startDiscoBeat(); }catch(e){}
    try{ keepRadioAlive(); }catch(e){}
    if(radioHasLiveStream()){
      try{ if(!discoRaf) startDiscoBeat(); }catch(e){}
    }
  }, 1200);
}
function stopIntroMediaRetry(){
  if(introMediaRetry){ clearInterval(introMediaRetry); introMediaRetry=null; }
}
function syncVoiceBtn(){
  var btn=document.getElementById('btnVoice');
  if(!btn) return;
  btn.textContent = voiceOn ? 'Balsas ON' : 'Balsas OFF';
  btn.classList.toggle('on', voiceOn);
}
var _vb = document.getElementById('btnVoice');
if(_vb) _vb.onclick=function(){
  unlockAudio(); voiceOn=!voiceOn; localStorage.setItem('host_voice', voiceOn?'1':'0'); syncVoiceBtn();
  if(voiceOn) queueAnnounce('Vilkas grįžo! Balsas įjungtas, kūjis paruoštas!');
};
syncMusicBtn(); syncVoiceBtn();
voiceOn = true; // balsas visada ON — mygtuko UI nėra

/* Įžanga: HTML autoplay muted = srautas iškart; kick bando unmute; gestas = garsas. */
(function bootCoverAudioHard(){
  try{ localStorage.removeItem(AUDIO_MASTER_KEY); }catch(e){}
  try{ claimAudioMaster(true); }catch(e){}
  function kick(){
    if(!document.body.classList.contains('cover-mode')) return;
    pageAudioOk=true; radioArmed=true; musicOn=true;
    try{ claimAudioMaster(true); }catch(e){}
    try{ ensureIntroMedia(true); }catch(e){}
    try{ keepRadioAlive(); }catch(e){}
  }
  kick();
  setTimeout(kick, 150);
  setTimeout(kick, 500);
  setTimeout(kick, 1200);
  setTimeout(kick, 2500);
})();

// ---------- konfeti ----------
var confettiCanvas = document.getElementById('confettiCanvas');
var cctx = confettiCanvas.getContext('2d');
var confettiParticles = [];
function resizeConfetti(){ confettiCanvas.width = window.innerWidth; confettiCanvas.height = window.innerHeight; }
window.addEventListener('resize', resizeConfetti); resizeConfetti();
var confettiColors = ['#ff7a33','#ffb347','#e3b23c','#4caf7d','#f3ead9'];
function fireworkBurst(cx, cy, count){
  for(var i=0;i<count;i++){
    var ang = (Math.PI*2)*(i/count) + Math.random()*0.3;
    var speed = 4+Math.random()*7;
    confettiParticles.push({
      x: cx, y: cy, vx: Math.cos(ang)*speed, vy: Math.sin(ang)*speed,
      grav: 0.13, size: 4+Math.random()*5, color: confettiColors[i%confettiColors.length],
      rot: Math.random()*360, vrot: (Math.random()-0.5)*14, life: 0
    });
  }
}
function launchConfetti(){
  confettiParticles = [];
  var w = confettiCanvas.width;
  fireworkBurst(w*0.28, confettiCanvas.height*0.32, 60);
  setTimeout(function(){ fireworkBurst(w*0.72, confettiCanvas.height*0.28, 60); }, 260);
  setTimeout(function(){ fireworkBurst(w*0.5, confettiCanvas.height*0.22, 70); }, 520);
  // ir sviesios krentancios juostelas is virsaus, kaip anksciau, papildomai
  for(var i=0;i<70;i++){
    confettiParticles.push({
      x: Math.random()*w, y: -20-Math.random()*200,
      vx: (Math.random()-0.5)*3, vy: 2+Math.random()*4, grav: 0,
      size: 5+Math.random()*6, color: confettiColors[i%confettiColors.length],
      rot: Math.random()*360, vrot: (Math.random()-0.5)*10, life: 0
    });
  }
  confettiCanvas.classList.add('show');
  var start = Date.now();
  function frame(){
    cctx.clearRect(0,0,confettiCanvas.width,confettiCanvas.height);
    var elapsed = Date.now()-start;
    confettiParticles.forEach(function(p){
      p.x+=p.vx; p.y+=p.vy; p.vy += (p.grav||0); p.rot+=p.vrot; p.life++;
      var alpha = p.grav ? Math.max(0, 1-p.life/70) : 1;
      cctx.save(); cctx.globalAlpha = alpha; cctx.translate(p.x,p.y); cctx.rotate(p.rot*Math.PI/180);
      cctx.fillStyle = p.color; cctx.fillRect(-p.size/2,-p.size/2,p.size,p.size*0.6);
      cctx.restore();
    });
    if(elapsed < 3800){ requestAnimationFrame(frame); }
    else { confettiCanvas.classList.remove('show'); cctx.clearRect(0,0,confettiCanvas.width,confettiCanvas.height); }
  }
  frame();
}

var myName = localStorage.getItem('vardas') || '';
var myNickname = localStorage.getItem('slapyvardis') || '';
var myContact = localStorage.getItem('kontaktas') || '';
var myPhone = localStorage.getItem('telefonas') || '';
var myPayMethod = localStorage.getItem('mokejimo_budas') || '';
var myPid = localStorage.getItem('pid') || '';
(function bootBuyerFlag(){
  try{
    var q=new URLSearchParams(location.search);
    var force = q.get('buyer')==='1' || q.get('as')==='pirkejas' || q.get('fresh')==='play' || q.get('fresh')==='demo';
    var suppliedPid = q.get('pid') || '';
    if(force){
      localStorage.setItem('aukcionas_buyer','1');
      /* Asmeninė testo nuoroda turi jau užregistruoto dalyvio PID. */
      if(suppliedPid){
        myPid=suppliedPid;
        localStorage.setItem('pid',myPid);
      } else {
        localStorage.removeItem('pid');
        myPid = '';
      }
      if(!localStorage.getItem('vardas') || localStorage.getItem('vardas')==='Mindaugas') localStorage.setItem('vardas','Mindaugas');
      if(!localStorage.getItem('slapyvardis')) localStorage.setItem('slapyvardis','Mindaugas');
      if(!localStorage.getItem('kontaktas')) localStorage.setItem('kontaktas','mindaugasbusiness@gmail.com');
      if(!localStorage.getItem('telefonas')) localStorage.setItem('telefonas','+37066331913');
      if(!localStorage.getItem('mokejimo_budas')) localStorage.setItem('mokejimo_budas','paypal');
      myName = localStorage.getItem('vardas') || 'Mindaugas';
      myNickname = localStorage.getItem('slapyvardis') || 'Mindaugas';
      myContact = localStorage.getItem('kontaktas') || 'mindaugasbusiness@gmail.com';
      myPhone = localStorage.getItem('telefonas') || '+37066331913';
      myPayMethod = localStorage.getItem('mokejimo_budas') || 'paypal';
    }
  }catch(e){}
})();
var els = {};
['lotTag','viewerCount','artWrap','artEmpty','itemBody','itemTitle','itemMeta','descText','priceNum','bidderLine','joinForm','joinFormTitle','nameInput','nicknameInput','contactInput','phoneInput','joinBtn','regNote','regClosedNote','bidBtn','bidLabel','timerNum','timerCircle','hint','soldBanner','soldName','soldPrice','payBox','payTotal','payWait','payPrivate','payPrivLabel','payPrivMail','payPrivHint','feedList','pastBox','pastList','countdownOverlay','countdownNum','celebrateOverlay','celebrateName','celebratePrice','celebrateClose','lockBanner'].forEach(function(id){els[id]=document.getElementById(id);});
if(els.nameInput && myName) els.nameInput.value = myName;
if(els.nicknameInput && myNickname) els.nicknameInput.value = myNickname;
if(els.contactInput && myContact) els.contactInput.value = myContact;
if(els.phoneInput && myPhone) els.phoneInput.value = myPhone;
(function restorePayRadio(){
  if(!myPayMethod) return;
  var r=document.querySelector('input[name="payMethod"][value="'+myPayMethod+'"]');
  if(r) r.checked=true;
})();
function selectedPayMethod(){
  var r=document.querySelector('input[name="payMethod"]:checked');
  return r ? r.value : '';
}
function syncRegPanel(){
  var done = document.getElementById('ppDone');
  var doneMsg = document.getElementById('ppDoneMsg');
  var panel = document.getElementById('participantsPanel');
  if(myPid){
    if(panel) panel.classList.add('registered');
    if(panel) panel.classList.remove('reg-collapsed');
    if(els.joinForm) els.joinForm.style.display='none';
    if(done) done.style.display='flex';
    if(doneMsg) doneMsg.textContent='Tu jau užsiregistravęs kaip '+(myNickname||'Mindaugas')+'. Kaina kelti — kai bus gyvas lotas.';
  } else {
    if(panel) panel.classList.remove('registered');
    if(panel && window.innerWidth<=640 && !panel.dataset.regOpened) panel.classList.add('reg-collapsed');
    if(els.joinForm) els.joinForm.style.display='flex';
    if(els.joinFormTitle) els.joinFormTitle.textContent='1. Registracija';
    if(done) done.style.display='none';
  }
}
syncRegPanel();
(function(){
  var btn=document.getElementById('ppChangeReg');
  if(!btn) return;
  btn.onclick=function(){
    myPid=''; myName=''; myNickname=''; myContact=''; myPhone=''; myPayMethod='';
    try{
      localStorage.removeItem('pid');
      localStorage.removeItem('name');
      localStorage.removeItem('nickname');
      localStorage.removeItem('contact');
      localStorage.removeItem('telefonas');
      localStorage.removeItem('pay_method');
    }catch(e){}
    if(els.nameInput) els.nameInput.value='';
    if(els.nicknameInput) els.nicknameInput.value='';
    if(els.contactInput) els.contactInput.value='';
    if(els.phoneInput) els.phoneInput.value='';
    syncRegPanel();
  };
})();
if(els.joinFormTitle) els.joinFormTitle.onclick=function(){
  var panel=document.getElementById('participantsPanel');
  if(!panel || myPid) return;
  panel.dataset.regOpened='1';
  panel.classList.toggle('reg-collapsed');
};
function registerBuyer(done){
  if(state && state.public_registration_open===false){ if(done) done(false); return; }
  var name = (myName||'Mindaugas').slice(0,80);
  var nickname = (myNickname||'Mindaugas').slice(0,24);
  var contact = (myContact||'mindaugasbusiness@gmail.com').slice(0,60);
  var phone = (myPhone||'+37066331913').slice(0,32);
  var pay_method = (myPayMethod||'paypal');
  fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,nickname:nickname,contact:contact,phone:phone,pay_method:pay_method})})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(d && d.pid){
        myPid=d.pid; myName=name; myNickname=nickname; myContact=contact; myPhone=phone; myPayMethod=pay_method;
        try{
          localStorage.setItem('pid', myPid);
          localStorage.setItem('vardas', myName);
          localStorage.setItem('slapyvardis', myNickname);
          localStorage.setItem('kontaktas', myContact);
          localStorage.setItem('telefonas', myPhone);
          localStorage.setItem('mokejimo_budas', myPayMethod);
          localStorage.setItem('aukcionas_buyer','1');
        }catch(e){}
        syncRegPanel();
      }
      if(done) done(!!(d && d.pid));
    })
    .catch(function(){ if(done) done(false); });
}
function ensureBuyerSession(done){
  var want=false;
  try{ want = localStorage.getItem('aukcionas_buyer')==='1'; }catch(e){}
  /* Nuorodoje esantis PID jau yra užregistruotas dalyvis: jo neperrašome. */
  if(myPid){ syncRegPanel(); if(done) done(); return; }
  if(!want){ if(done) done(); return; }
  /* Jei PID nėra, sukurkime naują pirkėjo sesiją. */
  myPid = '';
  try{ localStorage.removeItem('pid'); }catch(e){}
  registerBuyer(function(){ if(done) done(); });
}
function fmt(n){return (n||0).toLocaleString('lt-LT',{minimumFractionDigits:2,maximumFractionDigits:2});}
function stepFor(p){return 1;}
function timeStr(ms){var s=Math.max(0,Math.ceil(ms/1000)),m=Math.floor(s/60),r=s%60;return m+':'+(r<10?'0':'')+r;}
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function applyAuctionLock(locked, msg){
  document.body.classList.toggle('auction-locked', !!locked);
  if(els.lockBanner){
    if(locked){
      els.lockBanner.classList.add('show');
      if(msg) els.lockBanner.innerHTML = '<b>Aukcionas ruošiamas</b> — '+esc(msg);
    } else {
      els.lockBanner.classList.remove('show');
    }
  }
  if(els.joinBtn) els.joinBtn.disabled = false;
  if(locked){
    if(els.bidBtn){
      els.bidBtn.disabled = true;
      els.bidLabel.textContent = 'KELTI KAINĄ +1 €';
    }
    if(els.payBox) els.payBox.classList.remove('show');
    if(els.soldBanner) els.soldBanner.classList.remove('show');
    if(els.celebrateOverlay) els.celebrateOverlay.classList.remove('show');
  }
}
function applyPublicRegistration(open, msg){
  var on = open !== false;
  document.body.classList.toggle('reg-closed', !on);
  var hideIds=['nameInput','nicknameInput','contactInput','phoneInput','joinBtn','payMethodOpts'];
  hideIds.forEach(function(id){ var el=els[id]||document.getElementById(id); if(el) el.style.display = on ? '' : 'none'; });
  if(els.joinFormTitle) els.joinFormTitle.textContent = on ? '1. Registracija' : 'Registracija uždaryta';
  if(els.regNote) els.regNote.style.display = on ? '' : 'none';
  if(els.regClosedNote){
    els.regClosedNote.style.display = on ? 'none' : 'block';
    if(!on) els.regClosedNote.textContent = msg || 'Registracija uždaryta — Vilkas mokosi su imitaciniais pirkėjais.';
  }
  if(els.joinBtn) els.joinBtn.disabled = !on;
}

els.joinBtn.onclick=function(){
  if(state && state.public_registration_open===false){
    applyPublicRegistration(false, state.public_reg_closed_msg||'');
    if(els.regClosedNote) els.regClosedNote.textContent = state.public_reg_closed_msg || 'Registracija uždaryta.';
    return;
  }
  unlockAudio();
  if(musicOn) resumeRadio();
  var name=els.nameInput.value.trim(), nickname=els.nicknameInput.value.trim(), contact=els.contactInput.value.trim();
  var phone=(els.phoneInput?els.phoneInput.value:'').trim();
  var pay_method=selectedPayMethod();
  if(!name){els.regNote.textContent='Įvesk vardą ir pavardę.';return;}
  if(!(contact.indexOf('@')>1 && contact.indexOf('.',contact.indexOf('@'))>contact.indexOf('@'))){
    els.regNote.textContent='Įvesk el. paštą — ten gausi mokėjimo instrukcijas.';return;
  }
  if((phone.replace(/\D/g,'')).length<8){
    els.regNote.textContent='Įvesk telefono numerį (kad galėtume susisiekti).';return;
  }
  if(!pay_method){els.regNote.textContent='Pažymėk, kuo atsiskaitysi: PayPal, Skrill, Neteller arba Paysafe.';return;}
  els.joinBtn.disabled=true;
  els.regNote.textContent='Registruojama…';
  fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,nickname:nickname,contact:contact,phone:phone,pay_method:pay_method})})
    .then(function(r){
      if(!r.ok) return r.json().then(function(d){ throw new Error(d.detail || 'Registracija nepavyko'); });
      return r.json();
    }).then(function(d){
      var isExtraParticipant=!!myPid;
      var publicName=(d && d.public_name) || nickname || name.split(/\s+/)[0] || name;
      if(!isExtraParticipant){
        myName=name; myNickname=publicName; myContact=contact; myPhone=phone; myPayMethod=pay_method; myPid=d.pid;
        localStorage.setItem('vardas',name); localStorage.setItem('slapyvardis',myNickname); localStorage.setItem('kontaktas',contact); localStorage.setItem('telefonas',phone); localStorage.setItem('mokejimo_budas',pay_method); localStorage.setItem('pid',myPid);
      }
      els.regNote.textContent='';
      syncRegPanel();
      // Iš karto — sąrašas + skaičius (optimistiškai, tada poll)
      if(state){
        state.participant_count = (state.participant_count||0)+1;
        state.participant_names = [publicName].concat((state.participant_names||[]).filter(function(n){ return n!==publicName; }));
        renderParticipants();
      }
      if(isExtraParticipant){
        els.nameInput.value=''; els.nicknameInput.value=''; els.contactInput.value=''; if(els.phoneInput) els.phoneInput.value='';
        document.querySelectorAll('input[name="payMethod"]').forEach(function(x){ x.checked=false; });
        els.regNote.textContent='Dalyvis '+publicName+' užregistruotas ('+pay_method+').';
      }
      els.joinBtn.disabled=false;
      poll();
    }).catch(function(e){
      els.joinBtn.disabled=false;
      els.regNote.textContent = e.message || 'Registracija nepavyko';
    });
};
var state=null;
var lastLotId = null;
var lastStatus = null;
var lastCountdownInt = null;
var locallyAnnouncedBid = null;
els.bidBtn.onclick=function(){
  if(!state || !state.lot) return;
  if(state.auction_locked){
    applyAuctionLock(true, state.auction_lock_msg);
    return;
  }
  var lot=state.lot;
  if(lot.status!=='live') return;
  if(lot.starts_at && lot.starts_at*1000 > Date.now()) return;
  unlockAudio();
  if(musicOn) resumeRadio();
  els.bidBtn.disabled=true;
  function sendBid(retried){
    if(!myPid){
      registerBuyer(function(ok){
        if(!ok){ poll(); return; }
        sendBid(true);
      });
      return;
    }
    fetch('/api/bid',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pid:myPid,nickname:myNickname})})
      .then(function(r){
        if(r.ok) return r.json();
        if((r.status===403) && !retried){
          myPid=''; try{ localStorage.removeItem('pid'); }catch(e){}
          return new Promise(function(resolve,reject){
            registerBuyer(function(ok){
              if(!ok){ reject(new Error('reg')); return; }
              fetch('/api/bid',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pid:myPid,nickname:myNickname})})
                .then(function(r2){ if(!r2.ok) throw new Error('bid'); return r2.json(); })
                .then(resolve).catch(reject);
            });
          });
        }
        throw new Error('bid_'+r.status);
      })
      .then(function(d){
        /*
          Pirmas statymas negali laukti poll(): naujo loto pirmas įrašas
          anksčiau būdavo palaikomas istorija ir nutylimas.
        */
        if(d && d.ok && !d.already){
          locallyAnnouncedBid={name:myNickname, amount:Number(d.current_price)};
        }
        poll();
      })
      .catch(function(){ poll(); });
  }
  sendBid(false);
};
function closeCelebrate(){
  if(els.celebrateOverlay) els.celebrateOverlay.classList.remove('show');
  try{clearTimeout(window._celebrateAutoClose);}catch(e){}
}
els.celebrateClose.onclick=closeCelebrate;
var _celX=document.getElementById('celebrateCloseX');
if(_celX) _celX.onclick=closeCelebrate;

var payBoxUserClosed=false;
var _payBoxClose=document.getElementById('payBoxClose');
if(_payBoxClose) _payBoxClose.onclick=function(){
  payBoxUserClosed=true;
  if(els.payBox) els.payBox.classList.remove('show');
};

(function initPayBadges(){
  var PAY={
    paypal:{name:'PayPal',
      hint:'Po laimėjimo mokėjimo el. paštą gausite į savo registruotą el. paštą. Viešai mokėjimo adresai nerodomi.'},
    skrill:{name:'Skrill',
      hint:'Po laimėjimo Skrill mokėjimo instrukcijas gausite į savo el. paštą. Viešai adresai nerodomi.'},
    neteller:{name:'Neteller',
      hint:'Po laimėjimo Neteller mokėjimo instrukcijas gausite į savo el. paštą. Viešai adresai nerodomi.'},
    paysafe:{name:'Paysafe',
      hint:'Po laimėjimo Paysafe mokėjimo instrukcijas gausite į savo el. paštą. PIN niekada nesiųskite.'}
  };
  var detail=document.getElementById('payStripDetail');
  var nameEl=document.getElementById('psdName');
  var hintEl=document.getElementById('psdHint');
  function closePayStripDetail(){
    if(!detail) return;
    detail.classList.remove('on');
    document.querySelectorAll('.pay-badge').forEach(function(b){ b.style.outline=''; });
  }
  var _psdClose=document.getElementById('payStripDetailClose');
  if(_psdClose) _psdClose.onclick=function(ev){ if(ev){ev.preventDefault();ev.stopPropagation();} closePayStripDetail(); };
  (function(){
    var panel=document.getElementById('aqrPanel');
    var toggle=document.getElementById('aqrToggle');
    var close=document.getElementById('aqrClose');
    function closeRules(){ if(panel) panel.classList.remove('open'); }
    if(toggle) toggle.onclick=function(ev){
      if(ev){ev.preventDefault();ev.stopPropagation();}
      closePayStripDetail();
      if(panel) panel.classList.toggle('open');
    };
    if(close) close.onclick=function(ev){ if(ev){ev.preventDefault();ev.stopPropagation();} closeRules(); };
  })();
  document.querySelectorAll('.pay-badge[data-pay]').forEach(function(btn){
    btn.addEventListener('click', function(){
      var p=PAY[btn.getAttribute('data-pay')];
      if(!p||!detail) return;
      nameEl.textContent=p.name+' — privatūs mokėjimai';
      hintEl.textContent=p.hint;
      detail.classList.add('on');
      document.querySelectorAll('.pay-badge').forEach(function(b){ b.style.outline=''; });
      btn.style.outline='2px solid #39ff6a';
      var radio=document.querySelector('input[name="payMethod"][value="'+btn.getAttribute('data-pay')+'"]');
      if(radio && !myPid) radio.checked=true;
    });
  });
})();

function loadWinnerPayment(){
  if(!els.payPrivate) return;
  if(!myPid){
    if(els.payWait) els.payWait.style.display='block';
    els.payPrivate.classList.remove('show');
    return;
  }
  fetch('/api/my_payment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pid:myPid})})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(d && d.winner && d.pay_email){
        if(els.payWait) els.payWait.style.display='none';
        els.payPrivate.classList.add('show');
        if(els.payPrivLabel) els.payPrivLabel.textContent='Mokėkite per '+d.pay_label+' į:';
        if(els.payPrivMail) els.payPrivMail.textContent=d.pay_email;
        if(els.payPrivHint) els.payPrivHint.textContent=d.pay_hint||'';
      } else {
        if(els.payWait){
          els.payWait.style.display='block';
          els.payWait.textContent=(d && d.message) || 'Mokėjimo el. paštai viešai nerodomi. Laimėtojas gaus instrukcijas į savo el. paštą.';
        }
        els.payPrivate.classList.remove('show');
      }
    }).catch(function(){});
}

function renderParticipants(){
  var n = (state && state.participant_count) || 0;
  var names = (state && state.participant_names) || [];
  var c = document.getElementById('ppCount');
  var list = document.getElementById('ppList');
  if(c) c.textContent = n + (n===1 ? ' dalyvis' : ' dalyvių');
  if(!list) return;
  if(!names.length){
    list.innerHTML = '<div class="pp-empty">Kol kas nieko</div>';
    return;
  }
  var me = myNickname || '';
  list.innerHTML = names.map(function(name){
    var cls = (me && name===me) ? 'pp-name me' : 'pp-name';
    return '<div class="'+cls+'">'+esc(name)+'</div>';
  }).join('');
  // naujausią (pirmą) matyti viršuje
  list.scrollTop = 0;
  syncRegPanel();
}
function render(){
  setVilkasStageFromState(state);
  try{
    var wasPr=practiceModeOn;
    practiceModeOn=!!(state && state.practice_bots);
    syncPracticeMusicLevels();
    if(practiceModeOn && vilkasStageOn){
      try{ musicOn=true; radioArmed=true; pageAudioOk=true; }catch(e0){}
      if(typeof isAudioMaster==='function' && isAudioMaster() && typeof keepRadioAlive==='function') keepRadioAlive();
      else if(typeof makeRadioAudibleNow==='function') makeRadioAudibleNow();
    } else if(wasPr && !practiceModeOn && typeof keepRadioAlive==='function'){
      try{ keepRadioAlive(); }catch(e1){}
    }
  }catch(e){}
  try{ applyDeskSong(state); }catch(e){}
  try{ applyServerDancer(state); }catch(e){}
  var lot=state.lot;
  applyAuctionLock(!!state.auction_locked, state.auction_lock_msg || '');
  applyPublicRegistration(state.public_registration_open!==false, state.public_reg_closed_msg||'');
  renderParticipants();
  if(els.viewerCount) els.viewerCount.textContent=state.participant_count+(state.participant_count===1?' dalyvis':' dalyvių');
  /* Įžangos viršelis: be prekių/scenos iki Vilko ON */
  if(!isVilkasStageOn() || !lot){
    if(els.lotTag)els.lotTag.textContent= isVilkasStageOn() ? 'LOTŲ KOL KAS NĖRA' : 'ĮŽANGA';
    if(els.artEmpty)els.artEmpty.style.display='none';
    els.itemBody.style.display='none';
    els.countdownOverlay.style.display='none';
    var mp=document.getElementById('mainPanel'); if(mp) mp.classList.add('empty-lot');
    var img0=document.getElementById('artPhoto'); if(img0) img0.style.display='none';
    if(els.bidBtn){
      els.bidBtn.disabled=true;
      els.bidLabel.textContent = myPid ? 'KELTI KAINĄ +1 €' : 'REGISTRUOKIS';
    }
    renderPast();
    renderQueueRail();
    return;
  }
  var mp2=document.getElementById('mainPanel'); if(mp2) mp2.classList.remove('empty-lot');
  els.artEmpty.style.display='none'; els.itemBody.style.display='block';
  if(els.lotTag) els.lotTag.textContent='LOTAS #'+String(lot.lot_number).padStart(3,'0')+(lot.status==='ended' ? ' · PARDUOTA' : ' · GYVAI');
  els.itemTitle.textContent=lot.title||'—';
  els.itemMeta.innerHTML='Siuntimas <b>'+fmt(lot.shipping)+' €</b>';
  els.descText.textContent=lot.description||'';
  els.priceNum.innerHTML=fmt(lot.current_price)+'<small>€</small>';
  var img=document.getElementById('artPhoto');
  if(lot.photo_file){ if(!img){img=document.createElement('img');img.id='artPhoto';els.artWrap.insertBefore(img,els.artEmpty);} img.src='/photos/'+lot.photo_file; img.style.display='block';}
  else if(img){img.style.display='none';}

  var celebrating = false;
  if(state.auction_locked){
    els.soldBanner.classList.remove('show');
    els.payBox.classList.remove('show');
    els.celebrateOverlay.classList.remove('show');
    els.bidBtn.disabled=true;
    els.bidLabel.textContent='KELTI KAINĄ +1 €';
    els.bidderLine.innerHTML = 'Žiūrėti galima — pirkimas bus atidarytas, kai viską sutvarkysime.';
  } else if(lot.status==='ended'){
    els.soldBanner.classList.add('show'); els.soldName.textContent=lot.current_bidder||'—'; els.soldPrice.textContent=fmt(lot.current_price)+' €';
    els.bidBtn.disabled=true; els.bidLabel.textContent='Aukcionas baigtas';
    if(lot.current_bidder){
      if(!payBoxUserClosed) els.payBox.classList.add('show');
      else els.payBox.classList.remove('show');
      els.payTotal.textContent = fmt(lot.current_price + (lot.shipping||0)) + ' €';
      loadWinnerPayment();
    } else {
      els.payBox.classList.remove('show');
      if(els.payPrivate) els.payPrivate.classList.remove('show');
    }
    if(lastStatus!=='ended' && lot.current_bidder){
      celebrating = true;
      els.celebrateName.textContent = lot.current_bidder;
      els.celebratePrice.textContent = fmt(lot.current_price)+' €';
      els.celebrateOverlay.classList.add('show');
      launchConfetti();
      clearTimeout(window._celebrateAutoClose);
      window._celebrateAutoClose=setTimeout(function(){
        if(els.celebrateOverlay) els.celebrateOverlay.classList.remove('show');
      }, 4200);
    }
  } else {
    /* Naujas live lotas — nuimti seną PARDUOTA langą, kad neuždengtų +1 € */
    payBoxUserClosed=false;
    if(els.celebrateOverlay) els.celebrateOverlay.classList.remove('show');
    els.soldBanner.classList.remove('show');
    els.payBox.classList.remove('show');
    els.bidderLine.innerHTML = lot.current_bidder ? ('Šiuo metu siūlo <b>'+esc(lot.current_bidder)+'</b>') : 'Dar niekas nesiūlė kainos — būk pirmas.';
    var inCountdown = lot.starts_at && (lot.starts_at*1000 > Date.now());
    if(inCountdown || Date.now()<startFlashUntil){
      els.bidBtn.disabled=true;
    } else if(!myPid){
      els.bidBtn.disabled=true;
      els.bidLabel.textContent='Užsiregistruok';
    } else {
      els.bidBtn.disabled = (lot.current_bidder===myNickname);
      els.bidLabel.textContent = (lot.current_bidder===myNickname) ? '👑 TU LYDERIAUJI' : 'KELTI KAINĄ +1 €';
    }
  }
  lastStatus = lot.status;
  if(lastLotId !== lot.id){ lastBidKey = null; }
  lastLotId = lot.id;

  if(!state.bids.length){els.feedList.innerHTML='<div class="feed-empty">Kol kas tylu.</div>';}
  else{
    var h='';
    state.bids.slice(0,12).forEach(function(b){
      var t=new Date(b.at*1000);
      h+='<div class="feed-row"><span>'+esc(b.name)+'</span><span class="feed-amt">'+fmt(b.amount)+' €</span><span class="feed-time">'+t.getHours()+':'+String(t.getMinutes()).padStart(2,'0')+':'+String(t.getSeconds()).padStart(2,'0')+'</span></div>';
    });
    els.feedList.innerHTML=h;
  }
  renderPast();
  renderQueueRail();
}
function buildTonightItems(){
  var items=[], seen={};
  var lot=state && state.lot;
  if(lot && (lot.status==='live' || (lot.status==='ended' && state.auction_locked))){
    items.push(Object.assign({}, lot, {_live:true}));
    seen[lot.id]=1;
  }
  ((state && state.queue)||[]).forEach(function(q){
    if(!q || seen[q.id]) return;
    items.push(Object.assign({}, q, {_live:false}));
    seen[q.id]=1;
  });
  return items;
}
function qrCardHtml(it, ord){
  var photo = it.photo_file ? '<img src="/photos/'+esc(it.photo_file)+'" alt="">' : '<span class="ph">nėra foto</span>';
  var price = it.starting_price!=null ? it.starting_price : it.current_price;
  var def = (it.defects||'').trim();
  var ordLabel = it._live ? 'Dabar' : ('#'+ord);
  var cls = 'qr-card'+(it._live?' now':'');
  return '<button type="button" class="'+cls+'" data-qr="'+ord+'" data-id="'+(it.id||'')+'">'+
    '<div class="qr-photo">'+photo+'</div>'+
    '<div class="qr-meta">'+
      '<span class="qr-ord">'+ordLabel+'</span>'+
      '<div class="qr-name">'+esc(it.title||'Prekė')+'</div>'+
      '<div class="qr-price">'+fmt(price)+'<small>€ start</small></div>'+
      (def?'<div class="qr-def">'+esc(def)+'</div>':'')+
    '</div></button>';
}
var qrItemsCache=[], qrSig='', qrPaused=false, qrOffset=0, qrRaf=0;
function renderQueueRail(){
  var rail=document.getElementById('queueRail');
  var track=document.getElementById('qrTrack');
  var countEl=document.getElementById('qrCount');
  if(!rail||!track) return;
  if(!isVilkasStageOn()){
    qrItemsCache=[];
    qrSig='cover';
    if(countEl) countEl.textContent='įžanga — prekės pasirodys kai įjungsime Vilką';
    rail.classList.add('qr-empty');
    track.innerHTML='<div style="padding:28px 16px;color:rgba(243,232,211,.4);font-size:13px;">Įžanga. Prekių eilė pasirodys, kai Mindaugas įjungs Vilką.</div>';
    qrOffset=0; track.style.transform='translateX(0)';
    return;
  }
  var items=buildTonightItems();
  qrItemsCache=items;
  var sig=items.map(function(x){return x.id+':'+(x.photo_file||'')+':'+(x.starting_price||'')+':'+(x.defects||'');}).join('|');
  if(countEl){
    countEl.textContent = items.length
      ? (items.length+' prekė'+(items.length===1?'':'s')+' · eilės tvarka')
      : 'kai bus prekių — čia slinks eilė';
  }
  rail.classList.toggle('qr-empty', !items.length);
  if(sig===qrSig) return;
  qrSig=sig;
  if(!items.length){
    track.innerHTML='<div style="padding:28px 16px;color:rgba(243,232,211,.4);font-size:13px;">Kol kas eilėje nieko — kai pridėsime, čia matysi eiliškumą.</div>';
    qrOffset=0; track.style.transform='translateX(0)';
    return;
  }
  var html='';
  items.forEach(function(it,i){ html+=qrCardHtml(it, i+1); });
  // dubliuoti sklandžiam auto-slinkimui
  if(items.length>=3){
    items.forEach(function(it,i){ html+=qrCardHtml(it, i+1); });
  }
  track.innerHTML=html;
  qrOffset=0; track.style.transform='translateX(0)';
  track.querySelectorAll('[data-qr]').forEach(function(btn){
    btn.onclick=function(){
      var ord=parseInt(btn.getAttribute('data-qr'),10);
      openQrModal(qrItemsCache[ord-1], ord);
    };
  });
}
function openQrModal(it, ord){
  if(!it) return;
  var m=document.getElementById('qrModal');
  if(!m) return;
  var img=document.getElementById('qrModalImg');
  if(it.photo_file){ img.src='/photos/'+it.photo_file; img.style.display='block'; }
  else { img.removeAttribute('src'); img.style.display='none'; }
  document.getElementById('qrModalOrd').textContent = it._live ? 'Dabar scenoje' : ('Eilėje #'+ord+' — ateis kai baigsis ankstesnė');
  document.getElementById('qrModalTitle').textContent = it.title||'Prekė';
  var sp = it.starting_price!=null ? it.starting_price : it.current_price;
  document.getElementById('qrModalPrice').textContent = 'Pradinė kaina: '+fmt(sp)+' €'+(it.shipping!=null?' · siuntimas '+fmt(it.shipping)+' €':'');
  function row(id, label, val){
    var el=document.getElementById(id);
    if(!el) return;
    if(val && String(val).trim()){ el.innerHTML='<b>'+label+':</b> '+esc(String(val).trim()); el.style.display='block'; }
    else { el.textContent=''; el.style.display='none'; }
  }
  row('qrModalCond','Būklė', it.condition);
  row('qrModalDef','Defektai', it.defects);
  row('qrModalPlus','Pliusai', it.pluses);
  row('qrModalInc','Komplektacija', it.included);
  row('qrModalDesc','Aprašymas', it.description);
  m.classList.add('open'); m.setAttribute('aria-hidden','false');
  qrPaused=true;
}
function speakQueueItem(it, ord){
  if(!it || !voiceOn) return;
  if(announceBusy || announceQueue.length) return;
  var title=speechTitle(it.title)||'ši prekė';
  var sp=it.starting_price!=null?it.starting_price:it.current_price;
  var def=(it.defects||'').trim();
  var line;
  if(it._live){
    line='Dabar scenoje — '+title+'! Pradinė kaina '+eurosWords(sp)+'.'+(def?' Defektas: '+def+'.':'')+' Kas kelia?';
  } else {
    line='Eilėje numeris '+ord+' — '+title+'. Startas nuo '+eurosWords(sp)+'.'+(def?' Sąžiningai: '+def+'.':'')+' Ateis, kai baigsis ankstesnė!';
  }
  queueAnnounce(capSentences(line), {pose:'present', bangs:0, gestures:['present','thumb','raise'],
    bubble:(it._live?'Dabar: ':'#'+ord+' ')+(it.title||'')});
}
function closeQrModal(){
  var m=document.getElementById('qrModal');
  if(m){ m.classList.remove('open'); m.setAttribute('aria-hidden','true'); }
  qrPaused=false;
}
function qrStep(dir){
  var track=document.getElementById('qrTrack');
  var vp=document.getElementById('qrViewport');
  if(!track||!vp) return;
  var card=track.querySelector('.qr-card');
  var step=(card?card.offsetWidth:111)+8;
  qrPaused=true;
  qrOffset = Math.max(0, qrOffset + dir*step);
  var max = Math.max(0, track.scrollWidth/2 - vp.clientWidth);
  if(qrOffset>max) qrOffset=0;
  track.style.transition='transform .35s ease';
  track.style.transform='translateX(' + (-qrOffset) + 'px)';
  clearTimeout(qrStep._t);
  qrStep._t=setTimeout(function(){ qrPaused=false; track.style.transition='none'; }, 900);
}
function qrAutoTick(){
  var track=document.getElementById('qrTrack');
  var vp=document.getElementById('qrViewport');
  if(track && vp && !qrPaused && qrItemsCache.length>=2){
    qrOffset += 0.28;
    var half = track.scrollWidth/2;
    if(half>0 && qrOffset >= half) qrOffset -= half;
    track.style.transform='translateX(' + (-qrOffset) + 'px)';
  }
  qrRaf=requestAnimationFrame(qrAutoTick);
}
(function initQueueRail(){
  var prev=document.getElementById('qrPrev'), next=document.getElementById('qrNext');
  var vp=document.getElementById('qrViewport'), modal=document.getElementById('qrModal');
  var close=document.getElementById('qrModalClose');
  if(prev) prev.onclick=function(){ qrStep(-1); };
  if(next) next.onclick=function(){ qrStep(1); };
  if(vp){
    vp.addEventListener('mouseenter', function(){ qrPaused=true; });
    vp.addEventListener('mouseleave', function(){ if(!document.getElementById('qrModal').classList.contains('open')) qrPaused=false; });
    vp.addEventListener('touchstart', function(){ qrPaused=true; }, {passive:true});
  }
  if(close) close.onclick=closeQrModal;
  if(modal) modal.addEventListener('click', function(e){ if(e.target===modal) closeQrModal(); });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeQrModal(); });
  qrRaf=requestAnimationFrame(qrAutoTick);
})();
function renderPast(){
  // Ankstesni lotai viešai PASLĖPTI — ataskaita folderiuose sau
  if(els.pastBox) els.pastBox.style.display='none';
}

var announcedCount = null;
function tickCountdownOverlay(){
  var lot = state && state.lot;
  if(!lot || !lot.starts_at || lot.status==='ended'){ els.countdownOverlay.style.display='none'; announcedCount=null; return; }
  var remain = lot.starts_at*1000 - Date.now();
  if(remain<=0){
    if(announcedCount!==null && announcedCount>0){ startSound(); }
    els.countdownOverlay.style.display='none'; announcedCount=null; return;
  }
  els.countdownOverlay.style.display='flex';
  var n = Math.ceil(remain/1000);
  if(n !== announcedCount){
    announcedCount = n;
    if(n<=0){
      els.countdownNum.textContent='START';
      els.countdownNum.classList.add('start');
      startSound();
    } else {
      els.countdownNum.textContent = n;
      els.countdownNum.classList.remove('start');
      els.countdownNum.style.animation='none'; void els.countdownNum.offsetWidth; els.countdownNum.style.animation='';
      if(n<=10) tickSound();
    }
  }
}

function tick(){
  if(els.countdownOverlay) els.countdownOverlay.style.display='none';
  try{ tickButton(); }catch(e){}
  try{ watchAmbienceSmoke(); }catch(e){}
  var lot=state && state.lot;
  var ring=document.querySelector('.timer-ring');
  var inCd = lot && lot.starts_at && lot.starts_at*1000 > Date.now();
  /* Vienas laikrodis: kol Vilkas pristato — tik mygtuke 1:00; žiedas tik kai vyksta pirkimas */
  /* Be F9 lotai SUŠALDYTI — ends_at praeityje neturi sukti poll() kas 200 ms */
  if(!lot || lot.status==='ended' || inCd || (state && state.auction_locked) || !isVilkasStageOn()){
    if(els.timerNum) els.timerNum.textContent = (lot && lot.status==='ended') ? '0:00' : '1:00';
    if(els.timerCircle) els.timerCircle.style.strokeDashoffset=0;
    if(ring) ring.style.opacity = inCd ? '0.35' : '1';
    return;
  }
  if(ring) ring.style.opacity='1';
  if(!lot.ends_at){ if(els.timerNum) els.timerNum.textContent='1:00'; return; }
  var remain=lot.ends_at*1000-Date.now();
  if(remain<=0){els.timerNum.textContent='0:00';pollSoon();return;}
  els.timerNum.textContent=timeStr(remain);
  var frac=remain/60000, C=2*Math.PI*32;
  els.timerCircle.style.strokeDashoffset=C*(1-Math.min(1,frac));
  els.timerCircle.style.stroke=frac<0.2?'#ff4d4d':'#ff7a33';
}
var pollBusy=false, pollLastAt=0;
function poll(){
  pollLastAt=Date.now();
  fetch('/api/state').then(function(r){return r.json();}).then(function(d){state=d;render();})
    .catch(function(){});
}
function pollSoon(){
  if(pollBusy || Date.now()-pollLastAt<1000) return;
  pollBusy=true; pollLastAt=Date.now();
  fetch('/api/state').then(function(r){return r.json();}).then(function(d){state=d;render();})
    .catch(function(){})
    .then(function(){ pollBusy=false; });
}
var serverEventSeen={}, serverEventOrder=[], lastServerEventId=0, eventSocket=null, eventSocketOpen=false;
function rememberServerEvent(id){
  id=Number(id)||0;
  if(!id || serverEventSeen[id]) return false;
  serverEventSeen[id]=1; serverEventOrder.push(id);
  while(serverEventOrder.length>600){ delete serverEventSeen[serverEventOrder.shift()]; }
  lastServerEventId=Math.max(lastServerEventId,id);
  return true;
}
function announceQueueHasTag(tag){
  for(var i=0;i<announceQueue.length;i++){ if(announceQueue[i] && announceQueue[i].tag===tag) return true; }
  return !!(announceBusy && announceCurrentJob && announceCurrentJob.tag===tag);
}
function clearPhoneJobsFromQueue(){
  try{
    announceQueue=(announceQueue||[]).filter(function(j){ return !(j && j.tag==='phone'); });
  }catch(e){}
}
function serverPhone(text, manual){
  /* F11 PRIVALOMA eiga:
     1) STOP visi kelimai/pokalbiai
     2) skambutis skamba
     3) „Atsiprašau žmonės, einu pakalbėti“
     4) Vilkas IŠNYKSTA ~1 min
     5) grįžta: „Viršininkas skambino… ko neperka žmonės?“
     6) jei kas kėlė — catchup vardai */
  text=String(text||'').trim();
  if(!manual){
    if(phoneCallActive || phoneSessionActive || announceQueueHasTag('phone')) return;
    if(!text) text=phoneExcuseLine();
    beginPhoneSession();
    queueAnnounce('',{tag:'phone',pose:'glasses',bangs:0,playMs:2200,bubble:'📞 Skambutis',
      gestures:['glasses'],onSpeak:function(){ setPhoneCallActive(true); if(isAudioMaster()) phoneRingSound(); },
      onDone:function(){ try{if(phoneRingAudio){phoneRingAudio.pause();phoneRingAudio=null;}}catch(e){} }});
    queueAnnounce(text,{tag:'phone',pose:'glasses',bangs:0,gestures:['glasses','wink','raise'],bubble:'📞 Alio…',
      onDone:function(){ try{ endPhoneSessionAndCatchup(); }catch(e){} }});
    return;
  }
  /* F11 manual — VISADA pertraukiam bid/nudge/joke (net lot_intro soft); sold paliekam protected per interrupt. */
  try{ interruptAllSpeech(); }catch(e){}
  beginPhoneSession();
  try{ if(isAudioMaster()) phoneRingSound(); }catch(e2){}
  try{ wolfPopShow('glasses'); }catch(e3){}
  try{ setBubble('📞 Skambutis', ''); }catch(e4){}
  clearTimeout(phoneSpeechTimer);
  phoneSpeechTimer=setTimeout(function(){
    phoneSpeechTimer=null;
    try{ if(phoneRingAudio){ phoneRingAudio.pause(); phoneRingAudio.currentTime=0; phoneRingAudio=null; } }catch(e5){}
    try{ if(navigator.vibrate) navigator.vibrate(0); }catch(e6){}
    /* Atlaisvinam eilę — phoneCallActive kitaip ryja „Atsiprašau“ (skamba, bet nekalba). */
    setPhoneCallActive(false);
    try{ if(typeof claimAudioMaster==='function') claimAudioMaster(true); }catch(eM){}
    clearPhoneJobsFromQueue();
    var excuse=phoneExcuseLine();
    queueAnnounce(excuse,{tag:'phone',priority:true,pose:'glasses',bangs:0,gestures:['glasses','wink'],bubble:'📞 Atsiprašau…',
      onDone:function(){
        queueAnnounce(text,{tag:'phone',priority:true,pose:'glasses',bangs:0,gestures:['glasses','raise'],bubble:'📞 Alio…',
          onDone:function(){
            try{ hideVilkasPhoneAway(); }catch(eH){}
            try{ clearTimeout(phoneAwayTimer); }catch(eT){}
            phoneAwayTimer=setTimeout(function(){
              phoneAwayTimer=null;
              try{ showVilkasAfterPhone(); }catch(eS){}
              try{ endPhoneSessionAndCatchup(); }catch(eE){}
            }, 60000);
          }});
      }});
  }, 2200);
}

var heardWelcome=false; var heardLotIntro={};
var pendingStageEvents=[];
function handleServerEvent(ev){
  if(!ev) return;
  if(!isVilkasStageOn()){
    if(ev.event_type==='lot_intro' || ev.event_type==='welcome' || ev.event_type==='start'){
      pendingStageEvents.push(ev);
    }
    return;
  }
  if(!rememberServerEvent(ev.event_id)) return;
  var now=Date.now(), age=now-(Number(ev.created_at)||0)*1000;
  var p=ev.payload||{}, lot=state&&state.lot;
  var phoneManual=!!(ev.event_type==='phone' && p.manual);
  var maxAge={bid:15000,nudge:18000,phone:18000,joke:22000,guitar:22000,start:18000,sold:45000,intermission:45000,welcome:25000,lot_intro:40000};
  if(phoneManual) maxAge.phone=60000;
  if(ev.expires_at && Number(ev.expires_at)*1000<=now) return;
  if(maxAge[ev.event_type] && age>maxAge[ev.event_type]) return;
  /* Kito loto intro/start NEGALI dingti malonės metu (state dar senas ended).
     phone (ypač F11 manual) — NEMESTI dėl lot_id neatitikimo. */
  if(p.lot_id && lot && Number(p.lot_id)!==Number(lot.id)){
    if(ev.event_type!=='lot_intro' && ev.event_type!=='start' && ev.event_type!=='welcome' && ev.event_type!=='phone') return;
  }
  var text=String(p.text||'').trim();
  /* Perduoda mokyklos parinktą intonaciją į kalbą. */
  var femBid=false;
  try{ femBid=(ev.event_type==='bid') && !!isFemaleName(p.name||''); }catch(eF){}
  var itoId=String(p.intonacija_id||'');
  var itoSexy=femBid || p.female_name===true || String(p.intonacija||'')==='seksuali' || itoId==='int-sexy';
  var itoSpeed=(p.speed && Number(p.speed)>0)?Number(p.speed):(itoSexy?0.93:0);
  /* Skambučio metu — jokių soft komentarų (nudge/joke/gitara/dainavimas). */
  if(isPhoneBusy() && (ev.event_type==='nudge'||ev.event_type==='joke'||ev.event_type==='guitar'||ev.event_type==='sing'||ev.event_type==='lot_intro'||ev.event_type==='welcome'||ev.event_type==='start')) return;
  if(ev.event_type==='bid'){
    if(coffeeActive) endCoffee();
    if(isPhoneBusy()){
      holdBidDuringPhone(p.name||'Dalyvis', Number(p.amount)||0);
      return;
    }
    /* Serverio tekstas (mokykla bid frazės) — jei yra; kitaip gyvas bidLine */
    if(text && text.length>8){
      try{ hitGong(); }catch(eG){}
      try{ cheerBurst(); }catch(eC){}
      var bubbleB='🔔 '+(p.name||'Dalyvis')+' → '+Math.round(Number(p.amount)||0)+' €';
      try{ setBubble(bubbleB, text); }catch(eB){}
      var nowB=Date.now();
      if(nowB-lastBidSpeechAt>=9000){
        lastBidSpeechAt=nowB;
        var optsB={tag:'bid', priority:true, pose:'bang', bangs:0, fast:!itoSexy, fx:'cheer',
          gestures:['bang',bidPose(p.name||''),'thumb'], gestureMs:350, bubble:bubbleB};
        if(itoSpeed) optsB.speed=itoSpeed;
        if(announceBusy || announceQueueHasProtected() || !announceQueueSoftOnly()) queueAnnounce(text, optsB);
        else { interruptAllSpeech(); queueAnnounce(text, optsB); }
      }
    } else {
      speakBidNow(p.name||'Dalyvis',Number(p.amount)||0);
    }
  } else if(ev.event_type==='sold'){
    interruptAllSpeech();
    if(p.winner) speakSold(p.winner,Number(p.price)||0,p.lot_id);
    else if(text) queueAnnounce(text,{tag:'sold',pose:'bow',bangsBefore:1,gong:true,bangs:0,after:'bow',bubble:'Lotas baigtas'});
  } else if(ev.event_type==='phone'){
    if(text) serverPhone(text, phoneManual);
  } else if(ev.event_type==='joke'){
    if(text) queueAnnounce(text,{tag:'joke',pose:'wink',bangs:0,fx:'laugh',gestures:['wink','glasses','raise'],bubble:'😄 Vilko bajeriukas'});
  } else if(ev.event_type==='guitar'){
    return; /* Ignoruojami ir seni gitaros įvykiai iš eilės / DB. */
  } else if(ev.event_type==='sing'){
    /* Trumpas dainavimas su muzika — duck švelnus, bitas lieka */
    if(text){
      try{ if(practiceModeOn && typeof makeRadioAudibleNow==='function') makeRadioAudibleNow(); }catch(eS){}
      queueAnnounce(text,{tag:'sing',pose:'raise',bangs:0,fx:'notes',gestures:['raise','welcome','clap'],bubble:'🎤 Vilkas dainuoja'+(p.daina?(': '+p.daina):''),
        onSpeak:function(){ try{ if(typeof makeRadioAudibleNow==='function') makeRadioAudibleNow(); }catch(e2){} }});
    }
  } else if(ev.event_type==='intermission'){
    if(p.skip_coffee){
      if(text) queueAnnounce(text,{tag:'intermission',pose:'present',bangs:0,gestures:['present','raise'],bubble:'➡️ Kitas lotas'});
      return;
    }
    if(text) queueAnnounce(text,{tag:'intermission',pose:'coffee',bangs:0,gestures:['coffee'],bubble:'☕ Pertrauka',onDone:function(){
      startIntermissionCoffee(p.lot_id);
    }});
    if((Number(p.lot_id)||0)%3===0) queueAnnounce(
      'Jūs man paskambinkite dėl prekių realizavimo. Aš laukiu jūsų skambučio.',
      {tag:'intermission',pose:'glasses',bangs:0,gestures:['glasses','welcome','raise'],bubble:'📞 +37066331913',
       onSpeak:function(){ photographedWolf('Prekių realizavimas', 'glasses'); }}
    );
  } else if(ev.event_type==='start'){
    if(text) queueAnnounce(text,{tag:'start',priority:true,pose:'welcome',bangsBefore:1,gong:true,bangs:0,gestures:CLAP.concat(['raise']),bubble:'🔨 PRADEDAME!'});
  } else if(ev.event_type==='lot_intro'){
    try{ if(coffeeActive) endCoffee(); }catch(e){}
    try{
      /* Soft intermission/kava — išmesk, kad pristatymas nelauktų */
      announceQueue=announceQueue.filter(function(j){
        return j && j.tag!=='intermission' && j.tag!=='joke' && j.tag!=='phone' && j.tag!=='nudge' && j.tag!=='guitar' && j.tag!=='sing';
      });
      if(announceBusy && announceCurrentJob && (announceCurrentJob.tag==='intermission'||announceCurrentJob.tag==='joke'||announceCurrentJob.tag==='phone'||announceCurrentJob.tag==='nudge'||announceCurrentJob.tag==='guitar'||announceCurrentJob.tag==='sing')){
        interruptAllSpeech();
      }
    }catch(e){}
    var lid=String(p.lot_id||'')+'@'+String(p.starts_at||'');
    if(heardLotIntro[lid]) return;
    heardLotIntro[lid]=1;
    try{ wolfPopShow('present'); }catch(e){}
    setTimeout(function(){ welcomeWolfForLot(p); },1000);
    if(text) queueAnnounce(text,{tag:'lot_intro',priority:true,pose:'present',bangs:1,gestures:['present','welcome','thumb'],bubble:'🎤 Lotas #'+(p.lot_number||'')+': '+(p.title||''),fast:false,speed:1.00});
  } else if(ev.event_type==='welcome'){
    if(heardWelcome) return;
    heardWelcome=true;
    var coffeeMs=Math.max(60000, (Number(p.coffee_s)||120)*1000);
    if(text) queueAnnounce(text,{tag:'welcome',pose:'welcome',bangs:0,gestures:['welcome','present','raise'],bubble:'Penktadienio aukcionas',
      onDone:function(){ try{ startOpeningCoffee(coffeeMs); }catch(e){} }});
  } else if(ev.event_type==='nudge' && text){
    queueAnnounce(text,{tag:'nudge',pose:'raise',bangs:0,gestures:['raise','welcome','thumb'],bubble:'Kas kitas?'});
  }
}
function applySocketMessage(msg){
  if(!msg) return;
  if(msg.kind==='state' && msg.state){ state=msg.state; render(); }
  else if(msg.kind==='event') handleServerEvent(msg.event);
}
function connectEvents(){
  if(eventSocket && (eventSocket.readyState===0 || eventSocket.readyState===1)) return;
  var proto=location.protocol==='https:'?'wss:':'ws:';
  eventSocket=new WebSocket(proto+'//'+location.host+'/ws?last_event_id='+lastServerEventId);
  eventSocket.onopen=function(){ eventSocketOpen=true; };
  eventSocket.onmessage=function(e){ try{ applySocketMessage(JSON.parse(e.data)); }catch(err){ reportClientError(err.message,'websocket',0,0,err.stack); } };
  eventSocket.onclose=function(){ eventSocketOpen=false; setTimeout(connectEvents,1800); };
  eventSocket.onerror=function(){ eventSocketOpen=false; };
}
function pollEventsFallback(){
  if(eventSocketOpen) return;
  fetch('/api/events?last_event_id='+lastServerEventId)
    .then(function(r){return r.json();})
    .then(function(d){(d.events||[]).forEach(handleServerEvent);})
    .catch(function(){});
}

/* === VILKO_MOKYKLA_CLIENT_START (Fable 2026-10-08) === */
var vilkoBrain=null, vilkoLastBidAt=0;
function vilkoParams(){ try{ return (vilkoBrain&&vilkoBrain.judesiai&&vilkoBrain.judesiai.parametrai)||{}; }catch(e){ return {}; } }
function vilkoApplyMotion(p){
  try{
    var r=document.documentElement.style;
    if(p.bob_px!=null) r.setProperty('--wolf-bob-px',p.bob_px+'px');
    if(p.sway_deg!=null) r.setProperty('--wolf-sway-deg',p.sway_deg+'deg');
    if(p.talk_s!=null) r.setProperty('--wolf-talk-s',p.talk_s+'s');
    if(p.walk_ms!=null) r.setProperty('--wolf-walk-ms',Math.round(p.walk_ms)+'ms');
    if(p.raise_px!=null) r.setProperty('--wolf-raise-px',p.raise_px+'px');
    if(p.fade_ms!=null) r.setProperty('--wolf-fade-ms',Math.round(p.fade_ms)+'ms');
    if(p.idle_s!=null) r.setProperty('--wolf-idle-s',p.idle_s+'s');
    if(p.ease) r.setProperty('--wolf-ease',p.ease);
  }catch(e){}
}
function vilkoFetchBrain(){
  fetch('/api/vilkas/brain',{cache:'no-store'}).then(function(r){return r.json();}).then(function(d){
    if(d&&d.ok){ vilkoBrain=d; vilkoApplyMotion(vilkoParams()); }
  }).catch(function(){});
}
function vilkoFeedback(kind,payload){
  try{
    var body=JSON.stringify({kind:kind,payload:payload||{}});
    if(navigator.sendBeacon){ navigator.sendBeacon('/api/vilkas/feedback', new Blob([body],{type:'application/json'})); return; }
    fetch('/api/vilkas/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:body,keepalive:true}).catch(function(){});
  }catch(e){}
}
function vilkoSeq(tag){
  try{
    var arr=vilkoBrain&&vilkoBrain.judesiai&&vilkoBrain.judesiai.sekos&&vilkoBrain.judesiai.sekos[tag];
    if(!arr||!arr.length) return null;
    function beta(a,b){ /* Thompson: paprasta Beta aproksimacija per gamma (Marsaglia) */
      function g(k){ if(k<1){ return g(k+1)*Math.pow(Math.random(),1/k); } var d=k-1/3,c=1/Math.sqrt(9*d); for(;;){ var x,v; do{ x=(Math.random()*2-1)+(Math.random()*2-1)+(Math.random()*2-1); v=1+c*x; }while(v<=0); v=v*v*v; var u=Math.random(); if(u<1-0.0331*x*x*x*x) return d*v; if(Math.log(u)<0.5*x*x+d*(1-v+Math.log(v))) return d*v; } }
      var x=g(a),y=g(b); return x/(x+y);
    }
    var best=null,bv=-1;
    for(var i=0;i<arr.length;i++){ var v=beta(Math.max(0.05,+arr[i].a||1),Math.max(0.05,+arr[i].b||1)); if(v>bv){bv=v;best=arr[i];} }
    return best?{id:best.id,seq:(best.seka||[]).slice()}:null;
  }catch(e){ return null; }
}
/* Jank / pertraukimų matavimas gesto metu (tik audio-master — vienas matuotojas) */
var vilkoJank={on:false,jank:0,last:0,start:0,seqId:null,tag:null,bids:0,raf:null};
function vilkoJankStart(seqId,tag){
  if(typeof isAudioMaster==='function' && !isAudioMaster()) return;
  vilkoJank={on:true,jank:0,last:performance.now(),start:performance.now(),seqId:seqId,tag:tag,bids:0,raf:null};
  function loop(t){ if(!vilkoJank.on) return; var dt=t-vilkoJank.last; vilkoJank.last=t; if(dt>50) vilkoJank.jank+=dt-50; vilkoJank.raf=requestAnimationFrame(loop); }
  vilkoJank.raf=requestAnimationFrame(loop);
}
function vilkoJankStop(interrupted){
  if(!vilkoJank.on) return;
  var j=vilkoJank; vilkoJank.on=false; if(j.raf) cancelAnimationFrame(j.raf);
  var dur=performance.now()-j.start;
  vilkoFeedback('motion',{jank_ms:Math.round(j.jank),dur_ms:Math.round(dur),interrupted:!!interrupted,bid_during:j.bids,tag:j.tag,seq_id:j.seqId});
  if(j.seqId){
    var t0=Date.now();
    setTimeout(function(){ vilkoFeedback('gesture',{seq_id:j.seqId,tag:j.tag,bid_within:(vilkoLastBidAt>=t0-dur)?1:0,interrupted:!!interrupted}); }, 20000);
  }
}
/* Grakštūs judesiai */
function wolfWalkIn(){
  try{
    var pop=document.getElementById('wolfPop'); if(!pop) return;
    pop.classList.remove('walk-in'); void pop.offsetWidth; pop.classList.add('walk-in');
    var ms=+(vilkoParams().walk_ms||900);
    setTimeout(function(){ pop.classList.remove('walk-in'); }, ms+40);
  }catch(e){}
}
function wolfRaiseHand(){
  try{
    var pop=document.getElementById('wolfPop'); if(!pop) return;
    pop.classList.remove('raise-hand'); void pop.offsetWidth; pop.classList.add('raise-hand');
    try{ setPose('raise'); }catch(e){}
    setTimeout(function(){ pop.classList.remove('raise-hand'); }, 760);
  }catch(e){}
}
/* startGestures supranta 'walk' / 'raisehand'; tempas iš smegenų */
(function(){
  var _orig=startGestures;
  startGestures=function(list, ms){
    var l=[];
    (list||[]).forEach(function(g){
      if(g==='walk'){ wolfWalkIn(); return; }
      if(g==='raisehand'){ wolfRaiseHand(); l.push('raise'); return; }
      l.push(g);
    });
    return _orig(l, ms || +(vilkoParams().gesture_ms||0) || undefined);
  };
})();
/* queueAnnounce: išmokta gestų seka pagal tag + matavimas */
(function(){
  var _orig=queueAnnounce;
  queueAnnounce=function(text, opts){
    try{
      if(opts && typeof opts==='object' && opts.tag && !opts._vk){
        var tag=opts.tag==='lot_intro'?'lot_intro':opts.tag;
        var s=vilkoSeq(tag);
        if(s && s.seq.length>=2 && !opts.playMs){
          opts._vk=s.id;
          opts.gestures=s.seq;
          if(!opts.gestureMs) opts.gestureMs=+(vilkoParams().gesture_ms||0)||undefined;
          var oS=opts.onSpeak; opts.onSpeak=function(){ vilkoJankStart(s.id,tag); if(oS) return oS.apply(this,arguments); };
          var oD=opts.onDone; opts.onDone=function(){ vilkoJankStop(false); if(oD) return oD.apply(this,arguments); };
        }
      }
    }catch(e){}
    return _orig(text, opts);
  };
})();
(function(){
  var _oI=interruptAllSpeech;
  interruptAllSpeech=function(){ try{ if(vilkoJank.on) vilkoJankStop(true); }catch(e){} return _oI.apply(this,arguments); };
  var _oB=speakBidNow;
  speakBidNow=function(){ vilkoLastBidAt=Date.now(); try{ if(vilkoJank.on) vilkoJank.bids++; }catch(e){} return _oB.apply(this,arguments); };
})();
/* Soft-sway, kai Vilkas scenoje tyli (grakštus kvėpavimas, ne trypčiojimas) */
setInterval(function(){
  try{
    var pop=document.getElementById('wolfPop'); if(!pop) return;
    var on=(typeof isVilkasStageOn==='function' && isVilkasStageOn()) && pop.classList.contains('show') && !announceBusy && !hostAudio && !phoneCallActive;
    pop.classList.toggle('soft-sway', !!on);
  }catch(e){}
}, 700);
vilkoFetchBrain(); setInterval(vilkoFetchBrain, 300000);
/* === VILKO_MOKYKLA_CLIENT_END === */

ensureBuyerSession(function(){
  poll();
  connectEvents();
  setInterval(poll, 3000);
  setInterval(pollEventsFallback, 2500);
  setInterval(function(){
    fetch('/api/desk_song').then(function(r){return r.json();}).then(function(d){
      try{ applyDeskSong({desk_song: d.song || null}); }catch(e){}
    }).catch(function(){});
  }, 700);
});
setInterval(tick, 200);
