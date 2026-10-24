
/* Šveicariškas laikrodis: serveris naujesnis → automatiškai perkrauna (be Ctrl+F5) */
(function(){
  var PAGE_BUILD='1792856271-1792856362';
  window.PAGE_BUILD=PAGE_BUILD;
  try{
    if(navigator.serviceWorker){
      navigator.serviceWorker.getRegistrations().then(function(rs){
        rs.forEach(function(r){ try{ r.unregister(); }catch(e){} });
      });
    }
  }catch(e){}
  function check(){
    fetch('/api/build',{cache:'no-store'}).then(function(r){ return r.json(); }).then(function(d){
      if(!d || !d.id || d.id===PAGE_BUILD) return;
      var u=new URL(location.href);
      u.searchParams.set('_v', d.id);
      location.replace(u.toString());
    }).catch(function(){});
  }
  check();
  setInterval(check, 45000);
})();
