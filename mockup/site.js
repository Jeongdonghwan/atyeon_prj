// hero slideshow
const slides=[...document.querySelectorAll('.slide')],dots=[...document.querySelectorAll('#dots i')];let cur=0,timer;
function go(n){slides[cur].classList.remove('on');dots[cur].classList.remove('on');cur=(n+slides.length)%slides.length;slides[cur].classList.add('on');dots[cur].classList.add('on');}
function auto(){clearInterval(timer);timer=setInterval(()=>go(cur+1),5500);}
dots.forEach((d,i)=>d.onclick=()=>{go(i);auto();});auto();

// header state + parallax
const hdr=document.getElementById('hdr'),plx=document.getElementById('plx');
addEventListener('scroll',()=>{
  hdr.classList.toggle('on',scrollY>60);
  const r=plx.getBoundingClientRect();if(r.bottom>0&&r.top<innerHeight)plx.style.transform=`translateY(${(r.top-innerHeight)*-.08}px)`;
},{passive:true});

// reveal on scroll
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}}),{threshold:.15});
document.querySelectorAll('[data-r],.stag,.clip').forEach(el=>io.observe(el));

// infinite loops: duplicate content
['mq','track'].forEach(id=>{const el=document.getElementById(id);el.innerHTML+=el.innerHTML;});

// mobile menu
document.getElementById('burger').onclick=()=>document.body.classList.toggle('menu');
document.querySelectorAll('.mnav a').forEach(a=>a.onclick=()=>document.body.classList.remove('menu'));

// cursor
const c=document.querySelector('.cursor');let cx=0,cy=0,tx=0,ty=0;
addEventListener('mousemove',e=>{tx=e.clientX;ty=e.clientY;});
(function loop(){cx+=(tx-cx)*.18;cy+=(ty-cy)*.18;c.style.left=cx+'px';c.style.top=cy+'px';requestAnimationFrame(loop);})();
document.querySelectorAll('a,button,.work,li').forEach(el=>{el.onmouseenter=()=>c.classList.add('big');el.onmouseleave=()=>c.classList.remove('big');});
