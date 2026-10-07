/* Behind the Shield – baut eine Slide aus den Daten in #daten (Spec: Automatisierung/behind-the-shield.md).
   Daten: { seite, logo, post: { slides: [...] } }. Ergebnis: body[data-fertig="ja"],
   body[data-fehler] (leer = alles passt) und window.btsFertig (Promise, liefert die Fehler). */
(() => {
  const SVG = 'http://www.w3.org/2000/svg';
  // Farben wie AKZENTE in scripts/render.py, Umrisse = Element mit class "s-umriss" in templates/schilde/<name>.svg
  const RESIDENTS = {
    'kruxer': { name: 'KruXer', akzent: '#2EE6F5', handle: '@kruxer.dnb',
      umriss: 'M30,44 L72,20 H368 L410,44 V250 C410,392 318,468 220,510 C122,468 30,392 30,250 Z' },
    'stone d': { name: 'Stone D', akzent: '#FF4FA3', handle: '@stone_d_97',
      umriss: 'M40,64 L118,22 H322 L400,64 L414,262 L336,444 L220,508 L104,444 L26,262 Z' },
    'jhinx': { name: 'Jhinx', akzent: '#9D7BFF', handle: '@jhinx.dnb',
      umriss: 'M64,20 L376,20 L420,64 L420,282 L300,468 L220,510 L140,468 L20,282 L20,64 Z' },
    'ranj': { name: 'Ranj', akzent: '#FF9A3C', handle: '@ranj.dnb',
      umriss: 'M30,70 L70,22 L110,58 L150,14 L190,54 L220,6 L250,54 L290,14 L330,58 L370,22 L410,70 L402,148 L420,180 L398,220 L414,260 L384,330 L340,420 L220,510 L100,420 L56,330 L26,260 L42,220 L20,180 L38,148 Z' },
  };
  const STANDARD_UMRISS = 'M20,44 Q220,4 420,44 V240 C420,382 322,462 220,508 C118,462 20,382 20,240 Z';
  const NACHT = [3, 7, 13];
  const SCHILD = { x: 215, y: 268, b: 650 };   // Cover-Schild: links, oben, Breite in px (Seitenverhältnis 440 : 520)
  const fehler = [];

  let fertig;
  window.btsFertig = new Promise(r => { fertig = r; });

  // Daten lesen passiert in los() innerhalb des Fehlerfangs: kaputte Daten werden gemeldet, statt das Rendern aufzuhalten
  let daten, slides, seite, S, cover, R;
  function liste(wert, name) {
    if (wert == null) return [];
    if (!Array.isArray(wert)) throw new Error(`"${name}" muss eine Liste sein`);
    return wert;
  }
  function vorbereiten() {
    daten = JSON.parse(document.getElementById('daten').textContent);
    slides = liste(daten.post && daten.post.slides, 'slides');
    seite = daten.seite;
    S = slides[seite - 1] || {};
    cover = slides[0] || {};
    if (cover.vorlage !== 'bts-cover') fehler.push('Erste Slide muss bts-cover sein');
    R = RESIDENTS[String(cover.resident || '').trim().toLowerCase()];
    if (!R) {
      fehler.push(`Unbekannter Resident "${cover.resident || ''}" (erlaubt: KruXer, Stone D, Jhinx, Ranj)`);
      R = { name: String(cover.resident || '?'), akzent: '#2EE6F5', handle: '', umriss: STANDARD_UMRISS };
    }
    document.body.style.setProperty('--a', R.akzent);
  }

  /* ---------- Helfer ---------- */
  function el(tag, klasse, text) {
    const e = document.createElement(tag);
    if (klasse) e.className = klasse;
    if (text != null && text !== '') setzeText(e, text);
    return e;
  }
  function setzeText(e, text) {   // immer als Text, nie als HTML; \n wird Zeilenumbruch
    String(text).split('\n').forEach((zeile, i) => {
      if (i) e.appendChild(document.createElement('br'));
      e.appendChild(document.createTextNode(zeile));
    });
  }
  function svg(klasse, viewBox, inhalt) {   // inhalt nur aus festen Werten und Umrissen der Tabelle
    const s = document.createElementNS(SVG, 'svg');
    s.setAttribute('class', klasse);
    s.setAttribute('viewBox', viewBox);
    s.innerHTML = inhalt;
    return s;
  }
  function pflicht(slide, felder) {
    for (const f of felder) if (slide[f] == null || slide[f] === '') fehler.push(`${slide.vorlage}: Feld "${f}" fehlt`);
  }
  function balken(label, text) {
    const b = el('div', 'balken');
    b.appendChild(el('div', 'label', label));
    b.appendChild(el('div', 'b-text', text));
    return b;
  }
  const zwei = n => String(n).padStart(2, '0');
  const klemme = (v, lo, hi) => Math.min(Math.max(v, lo), hi);
  const stile = () => liste(cover.stile, 'stile').map(s => String(s).trim()).filter(Boolean);

  /* ---------- Fotos: laden, Fokus, Zoom ---------- */
  // wartet auf "load" statt auf img.decode(): Laden zählt auch Edge headless mit (virtuelle Zeit), Dekodieren nicht
  async function ladeFoto(name) {
    const img = new Image();
    try {
      await new Promise((ok, nein) => { img.onload = ok; img.onerror = nein; img.src = name; });
      return img;
    } catch (e) {
      fehler.push(`Foto „${name}“ nicht ladbar`);
      return null;
    }
  }
  function fokus(text, standard) {
    const m = String(text || standard).match(/^\s*(-?[\d.]+)%\s+(-?[\d.]+)%\s*$/);
    if (!m) { fehler.push('"fokus" muss so aussehen: "50% 30%"'); return fokus(standard, standard); }
    return [klemme(m[1] / 100, 0, 1), klemme(m[2] / 100, 0, 1)];
  }
  // Füllt die Fläche bw x bh immer ganz; zoomt (höchstens 1,6-fach) so weit, dass das Gesicht (fx, fy) waagerecht mittig
  // und senkrecht auf zielY sitzen kann
  function platziereFoto(nw, nh, bw, bh, fx, fy, zielY) {
    const s = Math.max(bw / nw, bh / nh);
    const wMin = bw / (2 * Math.max(Math.min(fx, 1 - fx), 1e-3));
    const hMin = Math.max(zielY / Math.max(fy, 1e-3), (bh - zielY) / Math.max(1 - fy, 1e-3));
    const zoom = klemme(Math.max(wMin / (nw * s), hMin / (nh * s)), 1, 1.6);
    const w = nw * s * zoom, h = nh * s * zoom;
    return { w, h, x: klemme(bw / 2 - fx * w, bw - w, 0), y: klemme(zielY - fy * h, bh - h, 0) };
  }
  function pruefeFuellung(p, bw, bh) {
    if (p.x > .5 || p.y > .5 || p.x + p.w < bw - .5 || p.y + p.h < bh - .5) fehler.push('Foto füllt die Fläche nicht');
  }
  function setzePosition(e, p) {
    Object.assign(e.style, { width: p.w + 'px', height: p.h + 'px', left: p.x + 'px', top: p.y + 'px' });
  }

  // Duotone in der Resident-Farbe: Nacht → Akzent → Weiß, Mitten gedämpft wie im freigegebenen Muster 1B
  // (Stufen: Nacht, 15 % Akzent, 68 % Akzent, Akzent/Weiß 25/75, Weiß; geprüft mit tests/bts/helligkeit.ps1)
  function duotone(id) {
    const a = R.akzent.match(/\w\w/g).map(h => parseInt(h, 16));
    const ueberNacht = (k, anteil) => NACHT[k] * (1 - anteil) + a[k] * anteil;
    const tab = k => [NACHT[k], ueberNacht(k, .15), ueberNacht(k, .68), a[k] * .25 + 255 * .75, 255].map(v => (v / 255).toFixed(3)).join(' ');
    const s = svg('', '0 0 0 0',
      `<filter id="${id}" color-interpolation-filters="sRGB">` +
      '<feColorMatrix type="matrix" values=".3 .59 .11 0 0  .3 .59 .11 0 0  .3 .59 .11 0 0  0 0 0 1 0"/>' +
      `<feComponentTransfer><feFuncR type="table" tableValues="${tab(0)}"/><feFuncG type="table" tableValues="${tab(1)}"/>` +
      `<feFuncB type="table" tableValues="${tab(2)}"/></feComponentTransfer></filter>`);
    Object.assign(s.style, { position: 'absolute', width: '0', height: '0' });
    document.body.appendChild(s);
  }

  /* ---------- Rahmen: Fläche, Kopfleiste, Fortschritt, Fuß ---------- */
  function rahmen(klasse, { marke = 'BEHIND THE SHIELD', fuss = true, inhalt = true } = {}) {
    const b = document.body;
    b.className = 'bts ' + klasse;
    b.appendChild(el('div', 'flaeche'));
    b.appendChild(el('div', 'punkte'));
    const k = el('header', 'kopf');
    const m = el('div', 'marke');
    if (daten.logo) { const img = el('img'); img.src = daten.logo; m.appendChild(img); }
    m.appendChild(el('span', '', marke));
    k.appendChild(m);
    const f = el('div', 'folge');
    f.appendChild(el('span', 'wer', R.name));
    f.appendChild(el('span', 'strich'));
    f.appendChild(el('span', 'nr', zwei(cover.folge || 0)));
    k.appendChild(f);
    b.appendChild(k);
    const p = el('div', 'fortschritt');
    for (let i = 1; i <= slides.length; i++) p.appendChild(el('i', i < seite ? 'war' : i === seite ? 'jetzt' : ''));
    b.appendChild(p);
    let main = null;
    if (inhalt) { main = el('main', 'inhalt'); b.appendChild(main); }
    if (fuss) {
      const u = el('footer', 'fuss');
      u.appendChild(el('span', 'links', R.handle));
      u.appendChild(el('span', 'rechts', '@energy.shield.rave'));
      b.appendChild(u);
    }
    b.appendChild(el('div', 'grain'));
    b.appendChild(el('div', 'scan'));
    return main;
  }

  /* ---------- Slides ---------- */
  function coverSlide() {
    pflicht(S, ['resident', 'folge', 'bild', 'seit']);
    if (!stile().length) fehler.push('bts-cover: Feld "stile" fehlt');
    rahmen('cover', { marke: 'ENERGYSHIELD', fuss: false, inhalt: false });
    duotone('duo');
    const b = document.body;
    const hud = el('div', 'hud');
    for (const e of ['e1', 'e2', 'e3', 'e4']) hud.appendChild(el('span', 'ecke ' + e));
    b.appendChild(hud);
    const serie = el('div', 'serie');
    serie.appendChild(el('span', '', 'BEHIND THE SHIELD'));
    b.appendChild(serie);
    // außerhalb des Schilds abdunkeln, oben und unten Verlauf, Umriss leuchtet
    const t = `translate(${SCHILD.x} ${SCHILD.y}) scale(${(SCHILD.b / 440).toFixed(4)})`;
    const maske = svg('maske', '0 0 1080 1350',
      `<defs><mask id="mb"><rect width="1080" height="1350" fill="white"/><path transform="${t}" d="${R.umriss}" fill="black"/></mask>` +
      '<linearGradient id="abb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#03070D" stop-opacity=".85"/>' +
      '<stop offset=".22" stop-color="#03070D" stop-opacity="0"/><stop offset=".6" stop-color="#03070D" stop-opacity="0"/>' +
      '<stop offset=".86" stop-color="#03070D" stop-opacity=".92"/><stop offset="1" stop-color="#03070D" stop-opacity="1"/></linearGradient></defs>' +
      '<rect width="1080" height="1350" fill="#03070D" opacity=".62" mask="url(#mb)"/><rect width="1080" height="1350" fill="url(#abb)"/>' +
      `<path class="umriss" transform="${t}" d="${R.umriss}"/>`);
    b.appendChild(maske);
    const name = el('h1', 'name', R.name);
    name.dataset.name = R.name;
    name.dataset.fit = '';
    b.appendChild(name);
    const tags = el('div', 'ctags');
    tags.appendChild(el('span', 'tag voll orb', 'Resident'));
    if (stile().length) tags.appendChild(el('span', 'tag orb', stile().join(' · ')));
    if (S.seit) tags.appendChild(el('span', 'tag leise orb', 'Seit ' + S.seit));
    b.appendChild(tags);
    b.appendChild(el('div', 'hook', 'Wer steht da eigentlich am Pult? Wisch rüber.'));
    if (!S.bild) return null;
    return async () => {
      const img = await ladeFoto(S.bild);
      if (!img) return;
      const [fx, fy] = fokus(S.fokus, '50% 30%');
      const p = platziereFoto(img.naturalWidth, img.naturalHeight, 1080, 1350, fx, fy, 470);
      img.className = 'vollbild';
      img.style.filter = 'url(#duo)';
      setzePosition(img, p);
      b.insertBefore(img, maske);
      pruefeFuellung(p, 1080, 1350);
      // Gesicht muss im oberen Teil des Schilds landen (innerer Rahmen: 10 % Rand seitlich und oben, bis 70 % der Schildhöhe)
      const H = SCHILD.b * 520 / 440, gx = p.x + fx * p.w, gy = p.y + fy * p.h;
      if (gx < SCHILD.x + .1 * SCHILD.b || gx > SCHILD.x + .9 * SCHILD.b || gy < SCHILD.y + .1 * H || gy > SCHILD.y + .7 * H) {
        fehler.push('Gesicht liegt nicht im Schild: "fokus" prüfen oder ein anderes Foto nehmen');
      }
    };
  }

  function steckbrief() {
    pflicht(S, ['rolle']);
    const inhalt = rahmen('steckbrief');
    const kopf = el('div', 's-kopf');
    const links = el('div');
    links.appendChild(el('span', 'tag orb', 'Steckbrief'));
    const titel = el('div', 'titel', 'Das ist');
    titel.appendChild(document.createElement('br'));
    titel.appendChild(el('em', '', R.name + '.'));
    links.appendChild(titel);
    kopf.appendChild(links);
    const mini = svg('mini', '0 0 440 520',
      `<defs><clipPath id="km"><path d="${R.umriss}"/></clipPath></defs><path d="${R.umriss}" fill="#060c14"/>` +
      `<g clip-path="url(#km)"></g><path class="umriss" d="${R.umriss}"/>`);
    kopf.appendChild(mini);
    inhalt.appendChild(kopf);
    const ul = el('ul', 'daten');
    const zeile = (k, v) => {
      const li = el('li');
      li.appendChild(el('span', 'k', k));
      li.appendChild(typeof v === 'string' ? el('span', 'v', v) : v);
      ul.appendChild(li);
    };
    if (S.vorname) zeile('Name', String(S.vorname));
    if (cover.seit) zeile('Am Pult seit', String(cover.seit));
    const tags = el('span', 'v tags');
    for (const s of stile()) tags.appendChild(el('span', 'tag', s));
    zeile('Sound', tags);
    zeile('Bei EnergyShield', String(S.rolle || ''));
    if (R.handle) zeile('Instagram', R.handle);
    inhalt.appendChild(ul);
    if (S.name_herkunft) inhalt.appendChild(balken('Woher kommt der Name?', S.name_herkunft));
    else document.body.classList.add('ohne-herkunft');
    if (!cover.bild) return null;
    return async () => {
      const img = await ladeFoto(cover.bild);
      if (!img) return;
      const [fx, fy] = fokus(cover.fokus, '50% 30%');
      const p = platziereFoto(img.naturalWidth, img.naturalHeight, 440, 520, fx, fy, 520 * .35);
      const bild = document.createElementNS(SVG, 'image');
      const geladen = new Promise(r => { bild.addEventListener('load', r); bild.addEventListener('error', r); });
      bild.setAttribute('href', cover.bild);
      bild.setAttribute('preserveAspectRatio', 'none');
      for (const [k, v] of [['x', p.x], ['y', p.y], ['width', p.w], ['height', p.h]]) bild.setAttribute(k, v.toFixed(1));
      mini.querySelector('g').appendChild(bild);
      await geladen;
    };
  }

  function sound() {
    pflicht(S, ['fuer_neue', 'erklaert']);
    const worte = liste(S.worte, 'worte');
    if (worte.length !== 3) fehler.push('bts-sound: "worte" braucht genau 3 Wörter');
    const inhalt = rahmen('sound');
    inhalt.appendChild(el('span', 'tag orb', 'So klingt ' + R.name));
    const w = el('div', 'worte');
    worte.slice(0, 3).forEach((x, i) => {
      const wort = String(x).trim();   // eigenes Satzzeichen („Laut!“) bleibt, sonst kommt ein Punkt dazu
      const e = el('div', 'wort w' + (i + 1), /[.!?…]$/.test(wort) ? wort : wort + '.');
      e.dataset.fit = '';
      w.appendChild(e);
    });
    inhalt.appendChild(w);
    const eq = el('div', 'eq');
    for (let i = 0; i < 64; i++) {
      const b = el('i');
      b.style.height = (18 + 82 * Math.abs(Math.sin(i * .37) * Math.cos(i * .11))).toFixed(1) + '%';
      eq.appendChild(b);
    }
    inhalt.appendChild(eq);
    inhalt.appendChild(balken('Für alle, die noch nie Drum and Bass gehört haben', S.fuer_neue));
    const k = el('div', 'erklaert');
    k.appendChild(el('div', 'label', 'Kurz erklärt · ' + (stile()[0] || '')));
    k.appendChild(el('p', '', S.erklaert));
    inhalt.appendChild(k);
    return null;
  }

  function anfang() {
    pflicht(S, ['zitat', 'moment']);
    const inhalt = rahmen('anfang');
    inhalt.appendChild(el('span', 'tag orb', 'Wie alles anfing'));
    // Anführungszeichen aus zwei schrägen Balken wie im Logo
    inhalt.appendChild(svg('zeichen', '0 0 124 92', '<path d="M8,92 L36,0 H62 L40,92 Z M62,92 L90,0 H116 L94,92 Z"/>'));
    inhalt.appendChild(el('div', 'zitat', S.zitat));
    inhalt.appendChild(el('div', 'signatur', '— ' + R.name));
    inhalt.appendChild(balken('Bester EnergyShield-Moment', S.moment));
    return null;
  }

  // „Künstler – Titel“: getrennt am ersten Gedanken- oder Bindestrich mit Leerzeichen; ohne Trennung ist alles Titel
  function teileTrack(x) {
    const m = String(x).match(/^(.*?)\s+[–-]\s+(.*)$/);
    return m ? [m[1].trim(), m[2].trim()] : ['', String(x).trim()];
  }
  function tracks() {
    const t = liste(S.tracks, 'tracks');
    if (t.length !== 3) fehler.push('bts-tracks: "tracks" braucht genau 3 Einträge');
    const inhalt = rahmen('tracks');
    inhalt.appendChild(el('span', 'tag orb', 'Playlist'));
    const titel = el('div', 'titel', '3 Tracks, die mich ');
    titel.appendChild(el('em', '', 'ausmachen'));
    inhalt.appendChild(titel);
    const ul = el('ul', 'liste');
    t.slice(0, 3).forEach((x, i) => {
      const [kuenstler, name] = teileTrack(x);
      const li = el('li');
      li.appendChild(el('span', 'pad', 'ABC'[i]));
      const d = el('div', 'track');
      if (kuenstler) d.appendChild(el('div', 'art', kuenstler));
      d.appendChild(el('div', 'tit', name));
      li.appendChild(d);
      ul.appendChild(li);
    });
    inhalt.appendChild(ul);
    const h = el('div', 'hinweis');
    h.appendChild(el('span', 'tag orb', 'Shield Sessions'));
    h.appendChild(el('span', '', 'Meine Mixe in voller Länge, jeden Sonntag um 18 Uhr'));
    inhalt.appendChild(h);
    return null;
  }

  function abseits() {
    if (!S.funfact && !S.abseits) fehler.push('bts-abseits: "funfact" oder "abseits" fehlt');
    const inhalt = rahmen('abseits' + (S.bild ? '' : ' ohne-bild'));
    const streifen = S.bild ? el('div', 'bildstreifen') : null;
    if (streifen) inhalt.appendChild(streifen);
    inhalt.appendChild(el('span', 'tag orb', 'Abseits vom Pult'));
    for (const [feld, label] of [['funfact', 'Was keiner von mir weiß'], ['abseits', 'Wenn ich nicht auflege']]) {
      if (!S[feld]) continue;
      const q = balken(label, S[feld]);
      q.classList.add('qa');
      inhalt.appendChild(q);
    }
    if (!streifen) return null;
    return async () => {   // erst nach dem Auto-Fit: dann steht die Größe des Streifens fest
      const img = await ladeFoto(S.bild);
      if (!img) return;
      const bw = streifen.clientWidth, bh = streifen.clientHeight;
      const [fx, fy] = fokus(S.fokus, '50% 50%');
      const p = platziereFoto(img.naturalWidth, img.naturalHeight, bw, bh, fx, fy, bh * .5);
      setzePosition(img, p);
      streifen.appendChild(img);
      pruefeFuellung(p, bw, bh);
    };
  }

  function bastion() {
    pflicht(S, ['set']);
    const inhalt = rahmen('bastion');
    inhalt.appendChild(el('span', 'tag orb', 'Club-Debut'));
    const titel = el('div', 'titel', 'Am 30.1. live in der ');
    titel.appendChild(el('em', '', 'Bastion'));
    inhalt.appendChild(titel);
    const mitte = el('div', 'mitte');
    mitte.appendChild(balken('Was euch bei meinem Set erwartet', S.set));
    if (S.an_neue) mitte.appendChild(balken('An alle, die zum ersten Mal kommen', S.an_neue));
    inhalt.appendChild(mitte);
    inhalt.appendChild(el('span', 'tag voll orb plaetze', 'Nur 120 Plätze'));
    const g = el('div', 'infos');
    for (const [label, wert, zahl] of [['Samstag', '30.01.', true], ['Wo', 'Club Bastion\nKirchheim'], ['Eintritt', 'Abendkasse\nab 18 Jahren']]) {
      const c = el('div', 'zelle');
      c.appendChild(el('span', 'z-l', label));
      c.appendChild(el('span', 'z-w' + (zahl ? ' zahl' : ''), wert));
      g.appendChild(c);
    }
    inhalt.appendChild(g);
    return null;
  }

  /* ---------- Auto-Fit: erst große Wörter in die Breite, dann Titel und Fließtext in die Höhe ---------- */
  function passeAn() {
    const wurzel = document.documentElement.style;
    let hs = 1, ts = 1;
    const setze = () => { wurzel.setProperty('--hs', hs.toFixed(3)); wurzel.setProperty('--ts', ts.toFixed(3)); };
    const fit = [...document.querySelectorAll('[data-fit], .titel')];
    const inhalt = document.querySelector('.inhalt');
    const zuBreit = () => fit.some(e => e.scrollWidth > e.clientWidth + 1);
    const zuHoch = () => !!inhalt && inhalt.scrollHeight > inhalt.clientHeight + 1;
    while (zuBreit() && hs > .6) { hs -= .02; setze(); }
    while (zuHoch() && (hs > .6 || ts > .7)) { hs = Math.max(.6, hs - .02); ts = Math.max(.7, ts - .02); setze(); }
    if (zuBreit()) fehler.push('Ein Wort ist zu lang für die Slide');
    if (zuHoch()) fehler.push('Zu viel Text für die Slide');
    for (const t of document.querySelectorAll('.track .tit')) {
      if (t.getBoundingClientRect().height > 2.5 * parseFloat(getComputedStyle(t).lineHeight)) { fehler.push('Track-Titel zu lang'); break; }
    }
    const tags = document.querySelector('.ctags');
    if (tags && tags.scrollWidth > tags.clientWidth + 1) fehler.push('Stile zu lang für das Cover');
    if (inhalt) {
      const box = inhalt.getBoundingClientRect();
      for (const e of inhalt.querySelectorAll('*')) {
        if (e.closest('svg')) continue;
        const r = e.getBoundingClientRect();
        if (r.width && (r.right > box.right + 1 || r.left < box.left - 1)) {
          fehler.push(`Text läuft seitlich über den Rand (${e.className || e.tagName})`);
          break;
        }
      }
    }
  }

  const BAUER = { 'bts-cover': coverSlide, 'bts-steckbrief': steckbrief, 'bts-sound': sound, 'bts-anfang': anfang,
                  'bts-tracks': tracks, 'bts-abseits': abseits, 'bts-bastion': bastion };
  async function los() {
    try {
      vorbereiten();
      const bauer = BAUER[S.vorlage];
      if (!bauer) throw new Error(`Unbekannte Vorlage "${S.vorlage}"`);
      const danach = bauer();
      const schnitte = ['800 40px Unbounded', '700 40px Unbounded', '500 30px Montserrat', '600 30px Montserrat', '700 30px Montserrat',
                        '800 30px Montserrat', '700 20px Orbitron', '900 20px Orbitron'];
      await Promise.all(schnitte.map(s => document.fonts.load(s, 'ÄÖÜß01')));
      await document.fonts.ready;
      passeAn();
      if (danach) await danach();
    } catch (e) {
      fehler.push('Skriptfehler: ' + e.message);
    }
    const text = [...new Set(fehler)].join(' | ');
    document.body.dataset.fehler = text;
    document.body.dataset.fertig = 'ja';
    fertig(text);
  }
  los();
})();
