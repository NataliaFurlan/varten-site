const menu=document.querySelector('.menu'),links=document.getElementById('links');
function closeMenu(){links.classList.remove('open');menu.setAttribute('aria-expanded','false')}
menu.addEventListener('click',()=>{const open=links.classList.toggle('open');menu.setAttribute('aria-expanded',String(open))});links.querySelectorAll('a').forEach(a=>a.addEventListener('click',closeMenu));document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMenu()});
const tabs=[document.getElementById('tab-prof'),document.getElementById('tab-student')];
function activateTab(tab){tabs.forEach(t=>{const active=t===tab;t.setAttribute('aria-selected',String(active));t.tabIndex=active?0:-1;document.getElementById(t.getAttribute('aria-controls')).hidden=!active})}
tabs.forEach((tab,i)=>{tab.addEventListener('click',()=>activateTab(tab));tab.addEventListener('keydown',e=>{let next;if(e.key==='ArrowRight'||e.key==='ArrowLeft')next=tabs[1-i];else if(e.key==='Home')next=tabs[0];else if(e.key==='End')next=tabs[1];if(next){e.preventDefault();activateTab(next);next.focus()}})});
const audiences={pessoal:['USO PESSOAL','Seu histórico começa com você.','O modo pessoal foi pensado para registrar suas próprias atividades, sem depender de academia, consultoria ou coach. Corrida, pedalada, caminhada e musculação fazem parte dessa direção, ainda em preparação para o aplicativo.','Qual atividade você gostaria de registrar primeiro?'],personal:['ATENDIMENTO INDIVIDUAL','Mais contexto entre uma sessão e outra.','O ponto de partida é organizar a prescrição e entender o que cada aluno executou, mesmo quando vocês não treinam juntos.','Como você decide qual aluno precisa de uma revisão de treino hoje?'],academia:['ACADEMIAS E ESTÚDIOS','Continuidade para quem treina com sua equipe.','Queremos entender como a prescrição e o histórico podem apoiar o acompanhamento dentro da academia. A experiência interativa apresenta o ciclo individual de treino, sem gestão de equipe ou de recepção.','Como sua equipe compartilha o contexto de um aluno entre os atendimentos?'],consultoria:['CONSULTORIA E COACHING DE TREINAMENTO','O acompanhamento continua à distância.','O registro de execução e o feedback aproximam o planejado do realizado. Estamos investigando como organizar a revisão dos treinos na rotina de uma consultoria.','O que você precisa perguntar por mensagem antes de revisar uma prescrição?']};
document.querySelectorAll('[data-audience]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-audience]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));const a=audiences[b.dataset.audience];['audience-label','audience-title','audience-body','audience-question'].forEach((id,i)=>document.getElementById(id).textContent=a[i])}));

// Continuous preview motion has an explicit pause and respects reduced motion.
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
const hero=document.querySelector('.hero'),motionToggle=document.getElementById('motionToggle');
let motionPaused=reducedMotion.matches;
function syncMotion(){hero.classList.toggle('motion-paused',motionPaused);motionToggle.setAttribute('aria-pressed',String(motionPaused));motionToggle.textContent=motionPaused?'Ativar animações':'Pausar animações'}
motionToggle.addEventListener('click',()=>{motionPaused=!motionPaused;syncMotion()});syncMotion();
const rail=document.querySelector('.activity-carousel'),track=document.getElementById('activityTrack'),slides=Array.from(track.children),play=document.getElementById('activityPlay'),position=document.getElementById('activityPosition');
let index=0,paused=reducedMotion.matches,hovered=false,focused=false,visible=false,timer;
const labels=['Corrida','Pedalada','Musculação','Caminhada','Seu histórico'];
function updatePlay(){play.textContent=paused?'Ativar carrossel':'Pausar carrossel';play.setAttribute('aria-pressed',String(paused));restartTimer()}
function goTo(next,manual=false){index=(next+slides.length)%slides.length;if(manual){paused=true;updatePlay()}rail.scrollTo({left:slides[index].offsetLeft-slides[0].offsetLeft,behavior:reducedMotion.matches?'instant':'smooth'});position.textContent=(index+1)+' de '+slides.length+' · '+labels[index]}
function restartTimer(){clearInterval(timer);if(!paused&&!hovered&&!focused&&visible&&!document.hidden){timer=setInterval(()=>goTo(index+1),5500)}}
document.getElementById('activityNext').addEventListener('click',()=>goTo(index+1,true));
document.getElementById('activityPrev').addEventListener('click',()=>goTo(index-1,true));
play.addEventListener('click',()=>{paused=!paused;updatePlay()});
rail.addEventListener('mouseenter',()=>{hovered=true;restartTimer()});rail.addEventListener('mouseleave',()=>{hovered=false;restartTimer()});
rail.addEventListener('focusin',()=>{focused=true;restartTimer()});rail.addEventListener('focusout',()=>{focused=false;restartTimer()});
rail.addEventListener('pointerdown',()=>{paused=true;updatePlay()},{passive:true});
rail.addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();goTo(index+(e.key==='ArrowRight'?1:-1),true)}else if(e.key==='Home'||e.key==='End'){e.preventDefault();goTo(e.key==='Home'?0:slides.length-1,true)}});
let scrolling;
rail.addEventListener('scroll',()=>{clearTimeout(scrolling);scrolling=setTimeout(()=>{index=slides.reduce((best,s,i)=>Math.abs(s.offsetLeft-slides[0].offsetLeft-rail.scrollLeft)<Math.abs(slides[best].offsetLeft-slides[0].offsetLeft-rail.scrollLeft)?i:best,0);position.textContent=(index+1)+' de '+slides.length+' · '+labels[index]},150)},{passive:true});
new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;restartTimer()},{threshold:.15}).observe(rail);
document.addEventListener('visibilitychange',restartTimer);
reducedMotion.addEventListener('change',()=>{motionPaused=reducedMotion.matches;paused=reducedMotion.matches;syncMotion();updatePlay()});
updatePlay();
// Trailing space lets the last card align at the start at every screen width.
const railSpacer=document.createElement('div');railSpacer.setAttribute('aria-hidden','true');railSpacer.style.flexShrink='0';track.append(railSpacer);
function sizeRailSpacer(){const gap=parseFloat(getComputedStyle(track).gap)||0;railSpacer.style.flexBasis=Math.max(0,rail.clientWidth-slides[0].getBoundingClientRect().width-gap)+'px'}
new ResizeObserver(sizeRailSpacer).observe(rail);sizeRailSpacer();
let dragStart=null;
rail.addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse'||e.button!==0)return;dragStart={x:e.clientX,left:rail.scrollLeft};rail.setPointerCapture(e.pointerId);rail.classList.add('dragging')});
rail.addEventListener('pointermove',e=>{if(!dragStart)return;e.preventDefault();rail.scrollLeft=dragStart.left-(e.clientX-dragStart.x)});
function endDrag(){dragStart=null;rail.classList.remove('dragging')}
rail.addEventListener('pointerup',endDrag);rail.addEventListener('pointercancel',endDrag);rail.addEventListener('lostpointercapture',endDrag);
