(()=>{const i=document.getElementById('qi');if(!i)return;
const v=document.getElementById('qv'),t=document.getElementById('tot'),fee=+i.dataset.fee,max=+i.dataset.max,
 dn=document.querySelector('[data-q="-1"]'),up=document.querySelector('[data-q="1"]');
function set(n){n=Math.max(1,Math.min(max,n||1));i.value=v.value=n;t.value=(fee*n).toLocaleString('ko-KR');dn.disabled=n<=1;up.disabled=n>=max;}
[dn,up].forEach(b=>b.onclick=()=>set(+i.value+ +b.dataset.q));set(+i.value);
const ph=document.querySelector('input[name=phone]');
ph.addEventListener('input',()=>{const d=ph.value.replace(/\D/g,'').slice(0,11);
 ph.value=d.length<4?d:d.length<8?d.slice(0,3)+'-'+d.slice(3):d.slice(0,3)+'-'+d.slice(3,d.length-4)+'-'+d.slice(-4);});})();
