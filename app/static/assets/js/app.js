/* Disuasión básica: bloquea clic derecho y atajos de inspección. NO reemplaza la seguridad real, que vive en el servidor. */
document.addEventListener('contextmenu',evento=>evento.preventDefault());
document.addEventListener('keydown',evento=>{const tecla=evento.key.toLowerCase();
 const atajoInspeccion=evento.key==='F12'||(evento.ctrlKey&&evento.shiftKey&&['i','j','c','k'].includes(tecla))||(evento.ctrlKey&&['u','s'].includes(tecla))||(evento.metaKey&&evento.altKey&&['i','j','c','u'].includes(tecla));
 if(atajoInspeccion)evento.preventDefault()});

const seleccionar=selector=>document.querySelector(selector),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const formatoMoneda=n=>new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN'}).format(n||0);
const TALLAS={XS:'Extra chica',S:'Chica',M:'Mediana',L:'Grande'},CATS={superior:'Superiores',inferior:'Inferiores',exterior:'Exteriores'},GEN={mujer:'Mujer',hombre:'Hombre',unisex:'Unisex'};
const selGen=(id,v='mujer')=>`<select id="${id}">${Object.entries(GEN).map(([k,n])=>`<option value="${k}" ${k==v?'selected':''}>${n}</option>`).join('')}</select>`;
const obtenerToken=()=>sessionStorage.getItem('t');
const cerrarSesionLocal=()=>{sessionStorage.removeItem('t');sessionStorage.removeItem('rol');sessionStorage.removeItem('nombre')};
const esAdministrador=()=>sessionStorage.getItem('rol')==='Administrador';
async function api(ruta,opciones={}){opciones.headers={...(opciones.headers||{})};if(obtenerToken())opciones.headers.Authorization='Bearer '+obtenerToken();
 const respuesta=await fetch('/api'+ruta,opciones);let datos={};try{datos=await respuesta.json()}catch{}
 if(respuesta.status===401&&!ruta.startsWith('/auth')){cerrarSesionLocal();location.hash='login'}
 if(!respuesta.ok)throw Error(typeof datos.detail==='string'?datos.detail:'Datos inválidos');return datos}
const barraDePaleta=g=>`<div class="barraDePaleta">${g.palette.map(c=>`<i style="flex:${c.pct};background:${c.hex}" title="${esc(c.nombre)} ${c.pct}%"></i>`).join('')}</div>`;
const vistaTallas=g=>`<div class="sizes">${Object.keys(TALLAS).map(t=>`<div class="sz ${g.sizes[t]?'':'zero'}" title="${TALLAS[t]}">${t}<b>${g.sizes[t]}</b></div>`).join('')}</div>`;
const etiquetaVeredicto=v=>`<span class="badge v-${v}">${v}</span>`;

/* ---------------- Acceso: iniciar sesión, crear cuenta y recuperar contraseña ---------------- */
const FORMULARIOS=['form-login','form-registro','form-olvide'];
function mostrarFormulario(id){FORMULARIOS.forEach(f=>seleccionar('#'+f).hidden=f!==id);document.querySelectorAll('.err').forEach(e=>{e.textContent='';e.className='err'})}
const enviarJson=(ruta,datos)=>api(ruta,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(datos)});
function mostrarMensaje(idElemento,texto,esExito){const elemento=seleccionar(idElemento);elemento.className=esExito?'err ok':'err';elemento.textContent=texto}
const alternarVisibilidad=(idCampo,idBoton)=>{const campo=seleccionar(idCampo),boton=seleccionar(idBoton);campo.type=campo.type=='password'?'text':'password';boton.textContent=campo.type=='password'?'Ver':'Ocultar'};
seleccionar('#ver-clave').onclick=()=>alternarVisibilidad('#login-clave','#ver-clave');
seleccionar('#ver-clave-registro').onclick=()=>alternarVisibilidad('#registro-clave','#ver-clave-registro');
seleccionar('#ir-registro').onclick=()=>mostrarFormulario('form-registro');
seleccionar('#ir-olvide').onclick=()=>{mostrarFormulario('form-olvide');seleccionar('#olvide-correo').value=seleccionar('#login-correo').value};
document.querySelectorAll('[data-volver]').forEach(boton=>boton.onclick=()=>{mostrarFormulario('form-login');seleccionar('#olvide-paso1').hidden=false;seleccionar('#olvide-paso2').hidden=true});

seleccionar('#form-login').onsubmit=async evento=>{evento.preventDefault();mostrarMensaje('#error-login','',false);
 try{const sesion=await enviarJson('/auth/login',{email:seleccionar('#login-correo').value,password:seleccionar('#login-clave').value});
  sessionStorage.setItem('t',sesion.token);sessionStorage.setItem('rol',sesion.role);sessionStorage.setItem('nombre',sesion.name);
  seleccionar('#login-clave').value='';location.hash=sesion.role==='Administrador'?'admin/dashboard':'tienda';mostrarPantalla()}
 catch(error){mostrarMensaje('#error-login',error.message,false)}};

seleccionar('#form-registro').onsubmit=async evento=>{evento.preventDefault();mostrarMensaje('#error-registro','',false);
 if(seleccionar('#registro-clave').value!==seleccionar('#registro-clave2').value)return mostrarMensaje('#error-registro','Las contraseñas no coinciden',false);
 try{const respuesta=await enviarJson('/auth/register',{name:seleccionar('#registro-nombre').value,email:seleccionar('#registro-correo').value,password:seleccionar('#registro-clave').value});
  seleccionar('#login-correo').value=seleccionar('#registro-correo').value;seleccionar('#form-registro').reset();
  mostrarFormulario('form-login');mostrarMensaje('#error-login',respuesta.message,true)}
 catch(error){mostrarMensaje('#error-registro',error.message,false)}};

seleccionar('#form-olvide').onsubmit=async evento=>{evento.preventDefault();mostrarMensaje('#error-olvide','',false);const correo=seleccionar('#olvide-correo').value;
 try{if(!seleccionar('#olvide-paso1').hidden){const respuesta=await enviarJson('/auth/forgot',{email:correo});
   seleccionar('#olvide-paso1').hidden=true;seleccionar('#olvide-paso2').hidden=false;seleccionar('#olvide-subtitulo').textContent='Ingresa el código y tu nueva contraseña.';
   mostrarMensaje('#error-olvide',respuesta.demo_code?`Modo demostración: tu código es ${respuesta.demo_code}`:(respuesta.channel=='correo'?'Si la cuenta existe, te enviamos el código por correo.':'Si la cuenta existe, el código aparece en la consola del servidor.'),true)}
  else{const respuesta=await enviarJson('/auth/reset',{email:correo,code:seleccionar('#olvide-codigo').value,new_password:seleccionar('#olvide-nueva').value});
   seleccionar('#login-correo').value=correo;seleccionar('#form-olvide').reset();seleccionar('#olvide-paso1').hidden=false;seleccionar('#olvide-paso2').hidden=true;
   mostrarFormulario('form-login');mostrarMensaje('#error-login',respuesta.message,true)}}
 catch(error){mostrarMensaje('#error-olvide',error.message,false)}};

/* ---------------- Router y menú ---------------- */
const MENU_CLIENTE={tienda:'Tienda',outfits:'Outfits',probador:'Probador con cámara',misoutfits:'Mis outfits'},
 MENU_ADMIN={dashboard:'Resumen',inventario:'Inventario',alta:'Alta de prenda',clientes:'Clientes',bd:'Base de datos'};
let detenerCamara=null;
async function mostrarPantalla(){detenerCamara&&detenerCamara();detenerCamara=null;
 const [seccion,argumento]=(location.hash.slice(1)||'login').split('/'),esRutaAdmin=seccion=='admin';
 if(!obtenerToken()){seleccionar('#shell').hidden=true;seleccionar('#login').hidden=false;if(seccion!='login')location.hash='login';return}
 if(seccion=='login'){location.hash=esAdministrador()?'admin/dashboard':'tienda';return}
 if(esRutaAdmin&&!esAdministrador()){location.hash='tienda';return}
 seleccionar('#login').hidden=true;seleccionar('#shell').hidden=false;
 const claveActiva=esRutaAdmin?(MENU_ADMIN[argumento]?argumento:'dashboard'):(MENU_CLIENTE[seccion]?seccion:'tienda'),menu=esRutaAdmin?MENU_ADMIN:MENU_CLIENTE;
 const enlaceFinal=esRutaAdmin?'<a href="#tienda">Ver tienda</a>':(esAdministrador()?'<a href="#admin/dashboard">Volver a administración</a>':'');
 seleccionar('#nav').innerHTML=`<span class="brand">Atelier</span><small>${esRutaAdmin?'Modo administrador':'Hola, '+esc(sessionStorage.getItem('nombre'))}</small>`
  +Object.entries(menu).map(([ruta,nombre])=>`<a href="#${esRutaAdmin?'admin/':''}${ruta}" class="${ruta==claveActiva?'on':''}">${nombre}</a>`).join('')
  +enlaceFinal+'<a class="end" href="#" data-accion="salir">Cerrar sesión</a>';
 try{await ({tienda,outfits,probador,misoutfits:misOutfits,dashboard,inventario,alta,clientes,bd})[claveActiva](argumento)}catch(error){seleccionar('#main').innerHTML=`<p class="err">${esc(error.message)}</p>`}}
seleccionar('#nav').addEventListener('click',evento=>{if(evento.target.dataset.accion==='salir'){evento.preventDefault();salir()}});
async function salir(){await api('/auth/logout',{method:'POST'}).catch(()=>{});cerrarSesionLocal();location.hash='login';mostrarPantalla()}
addEventListener('hashchange',mostrarPantalla);

/* ---------------- Vista cliente ---------------- */
let categoriaActiva='todas',q='',generoActivo='todos';
async function tienda(){const l=await api(`/tienda/prendas?q=${encodeURIComponent(q)}&categoria=${categoriaActiva}&genero=${generoActivo}`);
 seleccionar('#main').innerHTML=`<div class="row"><input id="q" style="max-width:300px" placeholder="Buscar prenda" value="${esc(q)}">
 ${['todas',...Object.keys(CATS)].map(c=>`<button class="chip ${c==categoriaActiva?'on':''}" data-c="${c}">${CATS[c]||'Todas'}</button>`).join('')}<span style="width:1px;background:var(--line);align-self:stretch"></span>${['todos','mujer','hombre'].map(x=>`<button class="chip ${x==generoActivo?'on':''}" data-g="${x}">${x=='todos'?'Todos':GEN[x]}</button>`).join('')}</div>
 <div class="grid">${l.map(g=>`<div class="card"><img class="thumb" src="${g.image}" alt="${esc(g.name)}" loading="lazy">${barraDePaleta(g)}<b>${esc(g.name)}</b><br><span class="price">${formatoMoneda(g.price)}</span> <span class="tag">${CATS[g.category]}</span> <span class="tag">${GEN[g.gender]}</span>
 ${vistaTallas(g)}<small>${g.stock?g.stock+' disponibles':'<b style="color:var(--bad)">Agotado</b>'}</small><div class="row" style="margin:.6rem 0 0"><a class="btn sm" href="#outfits/${g.id}">Outfits</a><a class="btn sm ghost" href="#probador/${g.id}">Probar</a></div></div>`).join('')||'<p>Sin resultados.</p>'}</div>`;
 document.querySelectorAll('[data-c]').forEach(b=>b.onclick=()=>{categoriaActiva=b.dataset.c;tienda()});document.querySelectorAll('[data-g]').forEach(b=>b.onclick=()=>{generoActivo=b.dataset.g;tienda()});
 let t;seleccionar('#q').oninput=e=>{q=e.target.value;clearTimeout(t);t=setTimeout(()=>tienda().then(()=>{const i=seleccionar('#q');i.focus();i.setSelectionRange(q.length,q.length)}),300)}}
let pedirNuevasSugerencias=false;
async function outfits(id){const all=await api('/tienda/prendas');if(!all.length){seleccionar('#main').innerHTML='<p>Aún no hay prendas.</p>';return}
 const base=all.find(g=>g.id==id)||all[0],r=await api(`/tienda/prendas/${base.id}/outfits?refresh=${pedirNuevasSugerencias}`);pedirNuevasSugerencias=false;
 seleccionar('#main').innerHTML=`<div class="two"><div class="card"><h3>Prenda base</h3><img class="thumb" style="max-width:260px;margin:.6rem auto" src="${base.image}" alt="">${barraDePaleta(base)}<b>${esc(base.name)}</b>
 <p style="color:var(--mut);margin:.3rem 0">Colores: ${base.palette.map(c=>esc(c.nombre)).join(', ')}${base.pattern?' · estampada':''}</p>
 <div class="row">${all.map(g=>`<a href="#outfits/${g.id}"><img class="mini ${g.id==base.id?'sel':''}" src="${g.image}" alt="${esc(g.name)}" title="${esc(g.name)}"></a>`).join('')}</div></div>
 <div class="card"><div class="row"><h3 style="margin:0">Combina con…</h3><button class="btn sm" id="nuevas">Generar nuevas</button></div>
 ${r.map(x=>`<div class="row"><img class="mini" src="${x.garment.image}" alt=""><div style="flex:1"><b>${esc(x.garment.name)}</b> <span class="tag">${CATS[x.garment.category]}</span><br><small>${x.type} · ${formatoMoneda(x.garment.price)} · ${x.garment.stock} uds.</small></div><div style="text-align:right">${etiquetaVeredicto(x.verdict)}<br><b>${x.affinity}%</b><br><button class="btn sm ghost" data-guardar="${x.garment.id}">Guardar</button></div></div>`).join('')||'<p>Sin sugerencias con stock para esta prenda.</p>'}
 <a class="btn acc sm" href="#probador/${base.id}">Probar en cámara</a></div></div>`;
 document.querySelectorAll('[data-guardar]').forEach(boton=>boton.onclick=()=>{const sugerida=r.find(x=>x.garment.id==boton.dataset.guardar).garment;
  abrirDialogoGuardar({[base.category]:base.id,[sugerida.category]:sugerida.id},null,`${base.name} + ${sugerida.name}`.slice(0,80))});
 seleccionar('#nuevas').onclick=()=>{pedirNuevasSugerencias=true;mostrarPantalla()}}


/* ---------------- Mis outfits ---------------- */
const NOMBRE_PRENDA={superior:'Superior',inferior:'Inferior',exterior:'Exterior'};
function abrirDialogoGuardar(prendasPorCategoria,ajustesPorCategoria,nombreSugerido){
 const items=Object.fromEntries(Object.entries(prendasPorCategoria).filter(([,id])=>id)),dialogo=seleccionar('#dlg');
 dialogo.innerHTML=`<form method="dialog" id="form-guardar"><h3>Guardar outfit</h3><label for="nombre-outfit">Nombre del outfit</label><input id="nombre-outfit" maxlength="80" value="${esc(nombreSugerido)}" required>
  <p class="err" id="error-guardar" role="alert"></p><div class="row"><button class="btn acc" value="ok">Guardar</button><button class="btn ghost" value="x" formnovalidate>Cancelar</button></div></form>`;
 dialogo.showModal();
 seleccionar('#form-guardar').onsubmit=async evento=>{if(evento.submitter.value!='ok')return;evento.preventDefault();
  try{await enviarJson('/mis-outfits',{name:seleccionar('#nombre-outfit').value,items,adjustments:ajustesPorCategoria});
   dialogo.innerHTML='<h3>¡Outfit guardado!</h3><p>Lo encuentras en «Mis outfits», aunque cierres sesión.</p><div class="row"><a class="btn acc" href="#misoutfits">Ver mis outfits</a><button class="btn ghost" id="cerrar-dialogo">Seguir</button></div>';
   seleccionar('#cerrar-dialogo').onclick=()=>dialogo.close();dialogo.querySelector('a').onclick=()=>dialogo.close()}
  catch(error){seleccionar('#error-guardar').textContent=error.message}}}

async function misOutfits(){const lista=await api('/mis-outfits');
 seleccionar('#main').innerHTML=`<div class="top"><h2 style="margin:0">Mis outfits</h2><span class="tag">${lista.length} guardados</span></div>
 <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr))">${lista.map(outfit=>`<div class="card"><div class="row" style="justify-content:space-between;margin-bottom:.4rem"><b>${esc(outfit.name)}</b>${etiquetaVeredicto(outfit.verdict)}</div>
  <div class="row">${Object.entries(outfit.items).map(([categoria,prenda])=>prenda?`<div style="text-align:center;width:84px"><img class="mini" style="width:84px;height:84px;cursor:default" src="${prenda.image}" alt=""><small>${esc(prenda.name)}</small></div>`:`<small>${NOMBRE_PRENDA[categoria]||categoria}: prenda ya no disponible</small>`).join('')}</div>
  <small style="color:var(--mut)">${outfit.score}/100 · ${fecha(outfit.created)}</small>
  <div class="row" style="margin:.6rem 0 0"><a class="btn sm acc" href="#probador/o${outfit.id}">Probar en cámara</a><button class="btn sm danger" data-borrar="${outfit.id}">Eliminar</button></div></div>`).join('')||'<p>Aún no guardas outfits. Combina prendas en «Probador con cámara» u «Outfits» y pulsa «Guardar».</p>'}</div>`;
 document.querySelectorAll('[data-borrar]').forEach(boton=>boton.onclick=async()=>{if(confirm('¿Eliminar este outfit?')){await api('/mis-outfits/'+boton.dataset.borrar,{method:'DELETE'});mostrarPantalla()}})}

/* ---------------- Probador con cámara (prendas articuladas) ---------------- */
const suavizar=t=>{t=Math.max(0,Math.min(1,t));return t*t*(3-2*t)};
let generoProbador='mujer';
async function probador(id){const all=(await api('/tienda/prendas')).filter(g=>g.image),sel={},ajustes=Object.fromEntries(Object.keys(CATS).map(c=>[c,{s:1,y:0}]));
 const ini=all.find(g=>g.id==id);if(ini){sel[ini.category]=ini.id;if(ini.gender!='unisex')generoProbador=ini.gender}
 if(String(id).startsWith('o')){/* outfit guardado: carga sus prendas y sus ajustes */
  const guardado=(await api('/mis-outfits')).find(o=>'o'+o.id==id);
  if(guardado){for(const c in guardado.items){const prenda=guardado.items[c];if(prenda){sel[c]=prenda.id;if(prenda.gender!='unisex')generoProbador=prenda.gender}}
   for(const c of Object.keys(CATS)){const a=guardado.adjustments[c];if(a)ajustes[c]={s:a.s,y:a.y}}}}
 seleccionar('#main').innerHTML=`<div class="two pb"><div><div class="stage" id="stage"><canvas id="lienzo"></canvas><video id="videoCamara" playsinline muted></video><div id="msg" style="position:absolute;padding:1rem;text-align:center">Pulsa «Activar cámara» y párate a 2 metros para que se vea tu cuerpo completo.</div></div>
 <div class="row" style="margin-top:.8rem"><button class="btn acc" id="go">Activar cámara</button><span id="est" style="color:var(--mut)"></span></div>
 <div class="card" id="ajustes"><b>Ajustar prenda por prenda</b><p class="nota">Cada prenda tiene su propio tamaño y altura.</p>${Object.keys(CATS).map(c=>`<div class="ajuste-prenda"><b>${NOMBRE_PRENDA[c]}</b><div class="two" style="gap:1rem"><div><label style="margin-top:.2rem">Tamaño: <b id="vs-${c}">100%</b></label><input type="range" data-campo="s" data-c="${c}" min="70" max="160" step="5" value="100"></div>
 <div><label style="margin-top:.2rem">Subir / bajar: <b id="vy-${c}">0</b></label><input type="range" data-campo="y" data-c="${c}" min="-20" max="20" value="0"></div></div></div>`).join('')}</div></div>
 <div><div class="card verdict" id="ver"></div><div class="row" style="margin:.8rem 0 0" id="gs">${['mujer','hombre'].map(x=>`<button class="chip" data-g="${x}">Ropa de ${GEN[x].toLowerCase()}</button>`).join('')}</div><div id="picks"></div></div></div>`;
 const compat=g=>g.gender==generoProbador||g.gender=='unisex';
 const evaluarOutfit=async()=>{const ids=Object.values(sel).filter(Boolean);if(ids.length<2){seleccionar('#ver').innerHTML='<div style="color:var(--mut)">Elige al menos 2 prendas para calificar tu outfit</div>';return}
  const r=await api('/tienda/evaluar?ids='+ids.join(','));seleccionar('#ver').innerHTML=`<div class="big">${r.verdict}</div>${etiquetaVeredicto(r.verdict)}<div class="bar"><i style="width:${r.score}%"></i></div><b>${r.score}/100</b>${r.tips.map(t=>`<p style="margin:.4rem 0;color:var(--mut)">${esc(t)}</p>`).join('')}<button class="btn acc sm" id="guardar-outfit" style="margin-top:.6rem">Guardar outfit</button>`;
  seleccionar('#guardar-outfit').onclick=()=>abrirDialogoGuardar(sel,ajustes,'Mi outfit')};
 const pintarSelectores=()=>{document.querySelectorAll('#gs .chip').forEach(c=>c.classList.toggle('on',c.dataset.g==generoProbador));
  seleccionar('#picks').innerHTML=Object.keys(CATS).map(c=>`<div class="card" style="margin-top:.8rem"><b>${CATS[c]}</b><div class="pick">${all.filter(g=>g.category==c&&compat(g)).map(g=>`<img class="mini ${sel[c]==g.id?'sel':''}" data-c="${c}" data-id="${g.id}" src="${g.image}" alt="${esc(g.name)}" title="${esc(g.name)} · ${formatoMoneda(g.price)}">`).join('')||'<small>Sin prendas</small>'}</div></div>`).join('')};
 seleccionar('#gs').onclick=e=>{const b=e.target.closest('[data-g]');if(!b)return;generoProbador=b.dataset.g;for(const c in sel){const g=all.find(x=>x.id==sel[c]);if(g&&!compat(g))sel[c]=null}pintarSelectores();evaluarOutfit()};
 seleccionar('#picks').onclick=e=>{const b=e.target.closest('[data-id]');if(!b)return;const c=b.dataset.c,v=+b.dataset.id;sel[c]=sel[c]==v?null:v;pintarSelectores();evaluarOutfit()};
 const sincronizarControles=()=>{for(const c of Object.keys(CATS)){const tamano=Math.round(ajustes[c].s*100),altura=Math.round(ajustes[c].y*100);
   document.querySelector(`[data-campo="s"][data-c="${c}"]`).value=tamano;document.querySelector(`[data-campo="y"][data-c="${c}"]`).value=altura;
   seleccionar('#vs-'+c).textContent=tamano+'%';seleccionar('#vy-'+c).textContent=altura}};
 seleccionar('#ajustes').oninput=e=>{const campo=e.target.dataset.campo;if(!campo)return;const c=e.target.dataset.c;ajustes[c][campo]=e.target.value/100;
  seleccionar(`#v${campo}-${c}`).textContent=campo=='s'?e.target.value+'%':e.target.value};
 sincronizarControles();
 pintarSelectores();evaluarOutfit();
 /* texturas reducidas para dibujar rápido */
 const im={};all.forEach(g=>{const i=new Image();i.onload=()=>{const k=Math.min(1,420/Math.max(i.naturalWidth,i.naturalHeight)),c=document.createElement('canvas');c.width=Math.round(i.naturalWidth*k);c.height=Math.round(i.naturalHeight*k);c.getContext('2d').drawImage(i,0,0,c.width,c.height);im[g.id]=c};i.src=g.image});
 const lienzo=seleccionar('#lienzo'),contexto=lienzo.getContext('2d'),videoCamara=seleccionar('#videoCamara');let flujoCamara,camaraActiva=false,detectorPose=null,L=null,idAnimacion;
 detenerCamara=()=>{camaraActiva=false;cancelAnimationFrame(idAnimacion);flujoCamara&&flujoCamara.getTracks().forEach(t=>t.stop())};
 seleccionar('#go').onclick=async()=>{try{flujoCamara=await navigator.mediaDevices.getUserMedia({video:{width:960,height:720,facingMode:'user'}});videoCamara.srcObject=flujoCamara;await videoCamara.play();seleccionar('#msg').hidden=true;camaraActiva=true;seleccionar('#go').hidden=true;
   lienzo.width=videoCamara.videoWidth||960;lienzo.height=videoCamara.videoHeight||720;seleccionar('#est').textContent='Cargando detector de cuerpo…';
   try{const m=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs');
    const fs=await m.FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm');
    detectorPose=await m.PoseLandmarker.createFromOptions(fs,{baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task'},runningMode:'VIDEO',numPoses:1});
    seleccionar('#est').textContent='Silueta activa: mueve los brazos, la prenda te sigue'}catch(e){detectorPose=null;seleccionar('#est').textContent='Sin internet para el detector: alinea tu cuerpo con la guía punteada'}
   loop()}catch(e){seleccionar('#msg').hidden=false;seleccionar('#msg').textContent='No se pudo abrir la cámara: permite el acceso en tu navegador (requiere HTTPS o localhost).'}};

 /* ---- esqueleto: dos lados (A = izquierda de la pantalla, B = derecha) ---- */
 const P=(lm,i)=>({x:(1-lm[i].x)*lienzo.width,y:lm[i].y*lienzo.height,v:lm[i].visibility??1});
 const LADO={izq:['sh','el','wr','hp','kn','an'],ix:[11,13,15,23,25,27],dx:[12,14,16,24,26,28]};
 function esqueleto(){const W=lienzo.width,H=lienzo.height;let A,B,guia=0;
  if(detectorPose){const d=detectorPose.detectForVideo(videoCamara,performance.now()).landmarks[0];
   if(d&&d[11].visibility>.5&&d[12].visibility>.5){const f=ix=>Object.fromEntries(LADO.izq.map((k,n)=>[k,P(d,ix[n])]));A=f(LADO.ix);B=f(LADO.dx)}}
  else{guia=1;A={sh:{x:W*.38,y:H*.27},hp:{x:W*.43,y:H*.58}};B={sh:{x:W*.62,y:H*.27},hp:{x:W*.57,y:H*.58}}}
  if(!A)return L;
  if(A.sh.x>B.sh.x)[A,B]=[B,A];
  const anchoHombros=Math.hypot(B.sh.x-A.sh.x,B.sh.y-A.sh.y),ejeX={x:(B.sh.x-A.sh.x)/anchoHombros,y:(B.sh.y-A.sh.y)/anchoHombros},ejeY={x:-ejeX.y,y:ejeX.x};
  const ok=(p,min=.5)=>p&&(p.v===undefined||p.v>=min),puntoMedio=(a,b)=>({x:(a.x+b.x)/2,y:(a.y+b.y)/2});
  const desplazarPunto=(p,v,k)=>({x:p.x+v.x*k,y:p.y+v.y*k,v:1});
  if(!ok(A.hp)||!ok(B.hp)||A.hp.y<A.sh.y){A.hp=desplazarPunto(A.sh,ejeY,anchoHombros*1.5);B.hp=desplazarPunto(B.sh,ejeY,anchoHombros*1.5);A.hp.x+=ejeX.x*anchoHombros*.15;B.hp.x-=ejeX.x*anchoHombros*.15}
  const torso=Math.hypot(puntoMedio(A.hp,B.hp).x-puntoMedio(A.sh,B.sh).x,puntoMedio(A.hp,B.hp).y-puntoMedio(A.sh,B.sh).y);
  for(const S of [A,B]){
   if(!ok(S.el)||!ok(S.wr)){S.el=desplazarPunto(S.sh,ejeY,anchoHombros*.75);S.wr=desplazarPunto(S.el,ejeY,anchoHombros*.65)}
   if(!ok(S.kn)||!ok(S.an,.4)||S.an.y>H*1.3){S.kn=desplazarPunto(S.hp,ejeY,torso*.85);S.an=desplazarPunto(S.kn,ejeY,torso*.85)}}
  const r={A,B,anchoHombros,ejeX,ejeY,torso,guia,M:puntoMedio(A.sh,B.sh),anchoCaderas:Math.hypot(B.hp.x-A.hp.x,B.hp.y-A.hp.y)};
  if(L&&!guia)for(const s of 'AB')for(const k in r[s]){const o=L[s][k],n=r[s][k];n.x=o.x*.55+n.x*.45;n.y=o.y*.55+n.y*.45}
  return L=r}

 /* ---- malla articulada: cada vértice sigue brazo/pierna según su posición ---- */
 const anguloEntre=(p,q)=>Math.atan2(q.y-p.y,q.x-p.x),rotarPunto=(x,y,a)=>[x*Math.cos(a)-y*Math.sin(a),x*Math.sin(a)+y*Math.cos(a)];
 const limitarAngulo=a=>Math.max(-2.6,Math.min(2.6,a));
 /* gira (X,Y) en el sistema del cuerpo alrededor de `piv`, dos tramos: hueso 1 y hueso 2 (codo/rodilla) */
 function cadena(X,Y,piv,len1,t1,t2,mezcla){let [dx,dy]=rotarPunto(X-piv[0],Y-piv[1],t1);const p1=[piv[0]+dx,piv[1]+dy];
  if(!mezcla)return p1;const [codoX,codoY]=rotarPunto(0,len1,t1),E=[piv[0]+codoX,piv[1]+codoY];[dx,dy]=rotarPunto(p1[0]-E[0],p1[1]-E[1],t2-t1);
  return[p1[0]+(E[0]+dx-p1[0])*mezcla,p1[1]+(E[1]+dy-p1[1])*mezcla]}
 function dibujaMalla(g,cuerpo,Wg,Hg,Y0,deforma){const t=im[g];if(!t)return;const N=12,V=[],{M,ejeX,ejeY}=cuerpo;
  for(let j=0;j<=N;j++)for(let k=0;k<=N;k++){let X=(k/N-.5)*Wg,Y=Y0+j/N*Hg;[X,Y]=deforma(X,Y);V.push([M.x+X*ejeX.x+Y*ejeY.x,M.y+X*ejeX.y+Y*ejeY.y])}
  contexto.globalAlpha=.95;
  for(let j=0;j<N;j++)for(let k=0;k<N;k++){const a=j*(N+1)+k,b=a+1,c=a+N+1,d=c+1,S=(kk,jj)=>[kk/N*t.width,jj/N*t.height];
   dibujarTriangulo(t,S(k,j),S(k+1,j),S(k,j+1),V[a],V[b],V[c]);dibujarTriangulo(t,S(k+1,j),S(k+1,j+1),S(k,j+1),V[b],V[d],V[c])}
  contexto.globalAlpha=1}
 function dibujarTriangulo(t,s0,s1,s2,d0,d1,d2){const den=(s1[0]-s0[0])*(s2[1]-s0[1])-(s2[0]-s0[0])*(s1[1]-s0[1]);if(Math.abs(den)<1e-6)return;
  const cx=(d0[0]+d1[0]+d2[0])/3,cy=(d0[1]+d1[1]+d2[1])/3,gr=p=>{const a=p[0]-cx,b=p[1]-cy,l=Math.hypot(a,b)||1;return[p[0]+a/l*.8,p[1]+b/l*.8]},a=gr(d0),b=gr(d1),c=gr(d2);
  contexto.save();contexto.beginPath();contexto.moveTo(a[0],a[1]);contexto.lineTo(b[0],b[1]);contexto.lineTo(c[0],c[1]);contexto.closePath();contexto.clip();
  const m11=((d1[0]-d0[0])*(s2[1]-s0[1])-(d2[0]-d0[0])*(s1[1]-s0[1]))/den,m21=((d2[0]-d0[0])*(s1[0]-s0[0])-(d1[0]-d0[0])*(s2[0]-s0[0]))/den,
   m12=((d1[1]-d0[1])*(s2[1]-s0[1])-(d2[1]-d0[1])*(s1[1]-s0[1]))/den,m22=((d2[1]-d0[1])*(s1[0]-s0[0])-(d1[1]-d0[1])*(s2[0]-s0[0]))/den;
  contexto.transform(m11,m12,m21,m22,d0[0]-m11*s0[0]-m21*s0[1],d0[1]-m12*s0[0]-m22*s0[1]);contexto.drawImage(t,0,0);contexto.restore()}

 /* superior / exterior: las mangas giran con hombro y codo */
 function ponSuperior(g,cuerpo,kw,kh,ajuste){const t=im[g];if(!t)return;const {anchoHombros,torso,ejeY,A,B}=cuerpo,asp=t.height/t.width,Ht=torso*kh*ajuste.s;
  const Wg=anchoHombros*kw*ajuste.s,Hg=Math.min(Math.max(Wg*asp,Ht*.8),Ht*1.25),Y0=-torso*.14+torso*ajuste.y,ua=anchoHombros*.75,th=Math.atan2(ejeY.y,ejeY.x);
  const ang_=S=>[limitarAngulo(anguloEntre(S.sh,S.el)-th),limitarAngulo(anguloEntre(S.el,S.wr)-th)];const ang0=ang_(A),ang1=ang_(B);
  dibujaMalla(g,cuerpo,Wg,Hg,Y0,(X,Y)=>{for(const [s,[a1,a2]] of [[-1,ang0],[1,ang1]]){
    const w=suavizar((s*X-.42*anchoHombros)/(.28*anchoHombros))*suavizar((Y+.04*anchoHombros)/(.2*anchoHombros));if(w<=0)continue;
    const piv=[s*anchoHombros/2,0],q=cadena(X,Y,piv,ua,a1,a2,suavizar((Y-ua*.85)/(ua*.3)));return[X+(q[0]-X)*w,Y+(q[1]-Y)*w]}return[X,Y]})}
 /* inferior: las piernas giran con cadera y rodilla */
 function ponInferior(g,cuerpo,ajuste){const t=im[g];if(!t)return;const {torso,anchoCaderas,ejeY,A,B,anchoHombros}=cuerpo,asp=t.height/t.width,th=Math.atan2(ejeY.y,ejeY.x),thigh=torso*.85;
  const Hg=(thigh*2)*1.12*ajuste.s,Wt=Math.max(anchoCaderas,anchoHombros*.7)*2.6,Wg=Math.min(Math.max(Hg/asp,Wt*.8),Wt*1.3)*ajuste.s,Y0=torso*.9+torso*ajuste.y;
  const ang_=S=>[limitarAngulo(anguloEntre(S.hp,S.kn)-th),limitarAngulo(anguloEntre(S.kn,S.an)-th)];const ang0=ang_(A),ang1=ang_(B),hx=Math.max(anchoCaderas,anchoHombros*.6)/2;
  dibujaMalla(g,cuerpo,Wg,Hg,Y0,(X,Y)=>{for(const [s,[a1,a2]] of [[-1,ang0],[1,ang1]]){
    const w=suavizar((s*X+.05*hx)/(.5*hx))*suavizar((Y-torso+.05*torso)/(thigh*.3));if(w<=0)continue;
    const piv=[s*hx,torso],q=cadena(X,Y,piv,thigh,a1,a2,suavizar((Y-torso-thigh*.9)/(thigh*.3)));return[X+(q[0]-X)*w,Y+(q[1]-Y)*w]}return[X,Y]})}

 function loop(){if(!camaraActiva)return;contexto.save();contexto.scale(-1,1);contexto.drawImage(videoCamara,-lienzo.width,0,lienzo.width,lienzo.height);contexto.restore();
  const cuerpo=esqueleto();if(cuerpo){
   if(cuerpo.guia){const{A,B}=cuerpo;contexto.strokeStyle='#ffffffaa';contexto.setLineDash([8,8]);contexto.lineWidth=2;contexto.beginPath();contexto.ellipse(cuerpo.M.x,cuerpo.M.y-cuerpo.anchoHombros*.9,cuerpo.anchoHombros*.45,cuerpo.anchoHombros*.55,0,0,7);
    contexto.moveTo(A.sh.x,A.sh.y);contexto.lineTo(A.hp.x,A.hp.y);contexto.lineTo(A.an.x,A.an.y);contexto.moveTo(B.sh.x,B.sh.y);contexto.lineTo(B.hp.x,B.hp.y);contexto.lineTo(B.an.x,B.an.y);contexto.moveTo(A.sh.x,A.sh.y);contexto.lineTo(B.sh.x,B.sh.y);contexto.stroke();contexto.setLineDash([])}
   if(sel.inferior)ponInferior(sel.inferior,cuerpo,ajustes.inferior);
   if(sel.superior)ponSuperior(sel.superior,cuerpo,2.3,1.5,ajustes.superior);
   if(sel.exterior)ponSuperior(sel.exterior,cuerpo,2.7,1.95,ajustes.exterior)}
  idAnimacion=requestAnimationFrame(loop)}}

/* ---------------- Vista administrador ---------------- */
async function dashboard(){const d=await api('/admin/dashboard');const C={'Cálido':'#d9622b','Frío':'#2f7fd0','Neutro':'#9aa39e'};
 seleccionar('#main').innerHTML=`<div class="grid">${[['Prendas',d.total],['Unidades en stock',d.units],['Valor del inventario',formatoMoneda(d.value)],['Agotadas',d.out_of_stock.length]].map(([l,v])=>`<div class="card stat">${l}<b>${v}</b></div>`).join('')}</div><br>
 <div class="two"><div class="card"><h3>Por categoría</h3>${Object.entries(d.categories).map(([k,v])=>`<p style="margin:.4rem 0">${CATS[k]}: <b>${v}</b></p>`).join('')}<h3 style="margin-top:1rem">Por familia de color</h3>${Object.entries(d.families).map(([k,v])=>`<span class="sw" style="width:14px;height:14px;background:${C[k]}"></span>${k}: ${v} &nbsp;`).join('')}</div>
 <div class="card"><h3>Colores dominantes (solo prendas, sin fondo)</h3>${d.dominant.map(h=>`<span class="sw" style="background:${h}" title="${h}"></span>`).join('')}<h3 style="margin-top:1rem">Por reabastecer</h3>${d.out_of_stock.map(g=>`<p style="margin:.3rem 0">${esc(g.name)} <small>(${esc(g.sku)})</small></p>`).join('')||'<p>Todo con existencias.</p>'}</div></div>`}
let busquedaInventario='';
let filasInventario=[];
async function inventario(){const l=filasInventario=await api('/admin/prendas?q='+encodeURIComponent(busquedaInventario));
 seleccionar('#main').innerHTML=`<div class="top"><input id="busquedaInventario" placeholder="Buscar por nombre o SKU" value="${esc(busquedaInventario)}"><a class="btn acc" href="#admin/alta">+ Alta de prenda</a><span>${l.length} prendas</span></div>
 <div class="scroll"><table class="rt"><thead><tr><th></th><th>SKU</th><th>Nombre</th><th>Categoría</th><th>Género</th><th>Precio</th>${Object.keys(TALLAS).map(t=>`<th>${t}</th>`).join('')}<th>Total</th><th></th></tr></thead><tbody>
 ${l.map((g,i)=>`<tr><td class="im"><img class="mini sq" src="${g.image}" alt=""></td><td data-label="SKU">${esc(g.sku)}</td><td data-label="Nombre">${esc(g.name)}</td><td data-label="Categoría">${CATS[g.category]}</td><td data-label="Género">${GEN[g.gender]}</td><td data-label="Precio">${formatoMoneda(g.price)}</td>${Object.keys(TALLAS).map(t=>`<td data-label="Talla ${t}">${g.sizes[t]}</td>`).join('')}<td data-label="Total"><b>${g.stock}</b></td>
 <td style="white-space:nowrap;justify-content:flex-end"><button class="btn sm ghost" data-editar="${i}">Editar</button> <button class="btn sm danger" data-baja="${g.id}">Baja</button></td></tr>`).join('')}</tbody></table></div>`;
 document.querySelectorAll('[data-editar]').forEach(b=>b.onclick=()=>editar(filasInventario[+b.dataset.editar]));document.querySelectorAll('[data-baja]').forEach(b=>b.onclick=()=>baja(+b.dataset.baja));
 let t;seleccionar('#busquedaInventario').oninput=e=>{busquedaInventario=e.target.value;clearTimeout(t);t=setTimeout(()=>inventario().then(()=>{const i=seleccionar('#busquedaInventario');i.focus();i.setSelectionRange(busquedaInventario.length,busquedaInventario.length)}),300)}}
function editar(g){const d=seleccionar('#dlg');d.innerHTML=`<form method="dialog" id="fe"><h3>Editar ${esc(g.sku)}</h3><label>Nombre</label><input id="en" value="${esc(g.name)}" required><label>Categoría</label><select id="ec">${Object.entries(CATS).map(([k,v])=>`<option value="${k}" ${k==g.category?'selected':''}>${v}</option>`).join('')}</select>
 <label>Género</label>${selGen('eg',g.gender)}<label>Precio (MXN)</label><input id="ep" type="number" min="0" step="0.01" value="${g.price}"><label>Existencias por talla</label><div class="sizes">${Object.keys(TALLAS).map(t=>`<div style="flex:1">${t}<input type="number" min="0" id="es-${t}" value="${g.sizes[t]}"></div>`).join('')}</div>
 <p class="err" id="ee"></p><div class="row"><button class="btn" value="ok">Guardar</button><button class="btn ghost" value="x" formnovalidate>Cancelar</button></div></form>`;d.showModal();
 seleccionar('#fe').onsubmit=async e=>{if(e.submitter.value!='ok')return;e.preventDefault();const s={};Object.keys(TALLAS).forEach(t=>s[t]=+seleccionar('#es-'+t).value);
  try{await api('/admin/prendas/'+g.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:seleccionar('#en').value,category:seleccionar('#ec').value,gender:seleccionar('#eg').value,price:+seleccionar('#ep').value,sizes:s})});d.close();mostrarPantalla()}catch(x){seleccionar('#ee').textContent=x.message}}}
async function baja(id){if(confirm('¿Dar de baja esta prenda? Se elimina del inventario.')){await api('/admin/prendas/'+id,{method:'DELETE'});mostrarPantalla()}}
async function alta(){seleccionar('#main').innerHTML=`<div class="two"><div class="card"><div class="drop" id="dz" tabindex="0">Arrastra una foto aquí o haz clic<br><small>JPG o PNG, hasta 10 MB. Se detecta la prenda y se ignora el fondo.</small></div><input type="file" id="f" accept="image/jpeg,image/png" hidden><p id="fn"></p>
 <label>Nombre</label><input id="n"><label>SKU</label><input id="s"><div class="two" style="gap:.6rem"><div><label>Categoría</label><select id="c">${Object.entries(CATS).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></div><div><label>Precio (MXN)</label><input id="pr" type="number" min="0" step="0.01" value="0"></div></div>
 <label>Género</label>${selGen('g')}<label>Existencias por talla</label><div class="sizes">${Object.entries(TALLAS).map(([t,n])=>`<div style="flex:1" title="${n}">${t}<input type="number" min="0" value="0" id="a-${t}"></div>`).join('')}</div>
 <p class="err" id="e"></p><button class="btn acc" id="go">Registrar prenda</button></div><div class="card"><h3>Resultado del análisis</h3><div id="res"><p>Sin resultados todavía.</p></div></div></div>`;
 const f=seleccionar('#f'),dz=seleccionar('#dz');dz.onclick=()=>f.click();dz.ondragover=e=>e.preventDefault();dz.ondrop=e=>{e.preventDefault();f.files=e.dataTransfer.files;f.onchange()};f.onchange=()=>seleccionar('#fn').textContent=f.files[0]?.name||'';
 seleccionar('#go').onclick=async()=>{const x=f.files[0];seleccionar('#e').textContent='';if(!x||!['image/jpeg','image/png'].includes(x.type)||x.size>10485760)return seleccionar('#e').textContent='Elige un JPG o PNG de hasta 10 MB.';if(!seleccionar('#n').value||!seleccionar('#s').value)return seleccionar('#e').textContent='Escribe nombre y SKU.';
  const s={};Object.keys(TALLAS).forEach(t=>s[t]=+seleccionar('#a-'+t).value);const fd=new FormData();fd.append('file',x);fd.append('name',seleccionar('#n').value);fd.append('sku',seleccionar('#s').value);fd.append('category',seleccionar('#c').value);fd.append('gender',seleccionar('#g').value);fd.append('price',seleccionar('#pr').value);fd.append('sizes',JSON.stringify(s));
  seleccionar('#go').disabled=true;try{const g=await api('/admin/prendas',{method:'POST',body:fd});seleccionar('#res').innerHTML=`<img class="thumb" style="max-width:220px" src="${g.image}" alt="">${g.palette.map(c=>`<p><span class="sw" style="background:${c.hex}"></span><b>${esc(c.nombre)}</b> ${c.hex} · ${c.pct}%</p>`).join('')}<p><span class="tag">${g.family}</span>${g.pattern?' <span class="tag">Estampada</span>':''} Prenda registrada.</p>`}catch(e){seleccionar('#e').textContent=e.message}seleccionar('#go').disabled=false}}

async function clientes(){const lista=await api('/admin/clientes');
 seleccionar('#main').innerHTML=`<div class="top"><h2 style="margin:0">Clientes registrados</h2><span class="tag">${lista.length} cuentas</span></div>
 <div class="scroll"><table class="rt"><thead><tr><th>#</th><th>Nombre</th><th>Correo</th><th>Fecha de registro</th></tr></thead><tbody>
 ${lista.map((cliente,posicion)=>`<tr><td data-label="#">${posicion+1}</td><td data-label="Nombre">${esc(cliente.name)}</td><td data-label="Correo">${esc(cliente.email)}</td><td data-label="Registro">${fecha(cliente.created)}</td></tr>`).join('')||'<tr><td colspan="4">Aún no hay clientes registrados.</td></tr>'}</tbody></table></div>`}
let filasBd=[],ordenBd={k:'id',d:1},busquedaBd='';
const BD_COLS=[['id','ID'],['sku','SKU'],['nombre','Nombre'],['categoria','Categoría'],['genero','Género'],['precio','Precio'],['tallas','Tallas'],['existencias','Stock'],['colores','Colores'],['fecha_registro','Registro']];
const ESQUEMA=[['id','INTEGER · llave'],['sku','TEXT · único'],['nombre','TEXT'],['categoria','TEXT'],['genero','TEXT · mujer/hombre/unisex'],['precio','REAL'],['tallas','JSON {XS,S,M,L}'],['existencias','INTEGER'],['ruta_imagen','TEXT'],['ruta_recorte','TEXT'],['paleta','JSON'],['familia','TEXT'],['estampado','BOOLEAN'],['fecha_registro','DATETIME']];
const fecha=i=>new Date(i+'Z').toLocaleString('es-MX',{dateStyle:'short',timeStyle:'short'});
async function bd(){const d=await api('/admin/bd');filasBd=d.rows;
 seleccionar('#main').innerHTML=`<div class="card" style="margin-bottom:1rem"><div class="top" style="margin:0"><b>Tabla «${d.table}»</b><span class="tag">${d.rows.length} registros</span><span class="tag">SQLite · data/inventario.db</span></div>
 <details style="margin-top:.6rem"><summary style="cursor:pointer;color:var(--acc)">Ver estructura de la tabla (${ESQUEMA.length} columnas)</summary><div class="cols" style="margin-top:.6rem">${ESQUEMA.map(([c,t])=>`<span class="tag"><b>${c}</b> · ${t}</span>`).join('')}</div></details></div>
 <div class="top"><input id="bq" placeholder="Buscar en la tabla" value="${esc(busquedaBd)}"><button class="btn ghost" id="csv">Exportar CSV</button></div>
 <div class="scroll"><table class="rt"><thead><tr><th></th>${BD_COLS.map(([k,n])=>`<th ${['tallas','colores'].includes(k)?'':`class="s" data-k="${k}"`}>${n}<span id="f-${k}"></span></th>`).join('')}</tr></thead><tbody id="bdt"></tbody></table></div>`;
 seleccionar('#bq').oninput=e=>{busquedaBd=e.target.value;pintarBd()};
 document.querySelectorAll('th.s').forEach(h=>h.onclick=()=>{const k=h.dataset.k;ordenBd={k,d:ordenBd.k==k?-ordenBd.d:1};pintarBd()});
 seleccionar('#csv').onclick=()=>{const q=v=>'"'+String(v??'').replace(/"/g,'""')+'"',h=['id','sku','nombre','categoria','genero','precio','XS','S','M','L','existencias','familia','estampado','colores','fecha_registro'];
  const csv='\ufeff'+[h.join(','),...filasBd.map(r=>[r.id,r.sku,r.nombre,r.categoria,r.genero,r.precio,r.tallas.XS,r.tallas.S,r.tallas.M,r.tallas.L,r.existencias,r.familia,r.estampado,r.colores.join(' | '),r.fecha_registro].map(q).join(','))].join('\n');
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.download='prendas.csv';a.click()};
 pintarBd()}
function pintarBd(){const t=busquedaBd.toLowerCase(),{k,d}=ordenBd;
 const f=filasBd.filter(r=>!t||[r.sku,r.nombre,r.categoria,r.familia].join(' ').toLowerCase().includes(t)).sort((a,b)=>(a[k]>b[k]?1:a[k]<b[k]?-1:0)*d);
 BD_COLS.forEach(([c])=>{const e=seleccionar('#f-'+c);if(e)e.textContent=c==k?(d>0?' ▲':' ▼'):''});
 seleccionar('#bdt').innerHTML=f.map(r=>`<tr><td class="im"><img class="mini sq" src="${r.recorte}" alt=""></td><td data-label="ID">${r.id}</td><td data-label="SKU">${esc(r.sku)}</td><td data-label="Nombre">${esc(r.nombre)}</td><td data-label="Categoría">${esc(r.categoria)}</td><td data-label="Género">${esc(r.genero)}</td><td data-label="Precio">${formatoMoneda(r.precio)}</td>
  <td data-label="Tallas"><div class="tl">${Object.entries(r.tallas).map(([t,n])=>`<i class="${n?'':'z'}">${t} ${n}</i>`).join('')}</div></td><td data-label="Stock"><b>${r.existencias}</b></td>
  <td data-label="Colores"><div class="cs">${r.colores.map(c=>`<i style="background:${(c.match(/#[0-9a-f]{6}/i)||['#ccc'])[0]}" title="${esc(c)}"></i>`).join('')}</div></td><td data-label="Registro">${fecha(r.fecha_registro)}</td></tr>`).join('')||'<tr><td>Sin resultados</td></tr>'}
mostrarPantalla();
mostrarPantalla();
