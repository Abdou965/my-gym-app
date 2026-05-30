const CACHE="ironcore-v2";
const FILES=["./","./index.html","./manifest.json"];

self.addEventListener("install",e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES)));
  self.skipWaiting();
});

self.addEventListener("activate",e=>{
  e.waitUntil(
    caches.keys().then(keys=>
      Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch",e=>{
  const url=e.request.url;
  if(url.includes("wger.de")||url.includes("fonts.googleapis")||url.includes("fonts.gstatic")){
    e.respondWith(fetch(e.request).catch(()=>new Response("",{status:503})));
    return;
  }
  e.respondWith(
    caches.match(e.request).then(r=>r||fetch(e.request).catch(()=>caches.match("./index.html")))
  );
});
