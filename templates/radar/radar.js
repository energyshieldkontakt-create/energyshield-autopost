/* Shield Radar – baut eine Slide aus den Daten in #daten (Spec: Automatisierung/shield-radar.md).
   Daten: { seite, logo, post: { slides: [...] } }. Ergebnis: body[data-fertig="ja"],
   body[data-fehler] (leer = alles passt) und window.radarFertig (Promise, liefert die Fehler). */
(() => {
  const SVG = 'http://www.w3.org/2000/svg';
  const RINGE = { lokal: 'Lokal', de: 'Deutschland', welt: 'Welt' };
  const GRENZE = { lokal: .38, de: .69, welt: 1 };                       // Ringlinien (Anteil am Radius)
  const BAND = { lokal: [.19, .30], de: [.47, .60], welt: [.75, .87] };  // wo die Punkte eines Rings liegen
  const BOGEN = [44, 316];   // erlaubte Winkel der Punkte; oben stehen die Ring-Namen
  const fehler = [];

  let fertig;
  window.radarFertig = new Promise(r => { fertig = r; });

  const daten = JSON.parse(document.getElementById('daten').textContent);
  const slides = (daten.post && daten.post.slides) || [];
  const seite = daten.seite;
  const S = slides[seite - 1] || {};
  const istStory = S.vorlage === 'radar-story';
  const coverSlide = slides.find(s => s.vorlage === 'radar-cover') || {};
  const info = istStory ? { ausgabe: S.ausgabe, datum: S.datum } : { ausgabe: coverSlide.ausgabe, datum: coverSlide.datum };
  if (!info.ausgabe) fehler.push(istStory ? 'radar-story braucht "ausgabe"' : 'Erste Slide muss radar-cover mit "ausgabe" sein');

  // Meldungen (nummeriert) und Kurzpunkte des ganzen Karussells: daraus entsteht das Radar
  const meldungen = istStory
    ? (S.meldungen || []).map((m, i) => ({ nr: i + 1, ring: m.ring, titel: m.titel, anriss: m.anriss || m.titel }))
    : slides.filter(s => s.vorlage === 'radar-meldung').map((m, i) => ({ nr: i + 1, ring: m.ring, titel: m.titel, anriss: m.anriss || m.titel, slide: m }));
  const kurzpunkte = istStory ? [] : slides.filter(s => s.vorlage === 'radar-kurz')
    .flatMap(k => k.punkte || []).map(p => ({ ring: p.ring, titel: p.text, klein: true }));
  for (const p of [...meldungen, ...kurzpunkte]) {
    if (!RINGE[p.ring]) fehler.push(`Unbekannter Ring "${p.ring}" (erlaubt: lokal, de, welt)`);
    if (!p.titel) fehler.push('Meldung ohne Titel/Text');
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
  function pflicht(slide, felder) {
    for (const f of felder) if (slide[f] == null || slide[f] === '') fehler.push(`${slide.vorlage}: Feld "${f}" fehlt`);
  }
  const zwei = n => String(n).padStart(2, '0');
  function hash(s) { let h = 2166136261; for (const z of String(s)) { h ^= z.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
  const zufall = s => (hash(s) % 100000) / 100000;
  function prng(seed) {
    let a = seed >>> 0;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const pos = (a, r) => [r * Math.sin(a * Math.PI / 180), -r * Math.cos(a * Math.PI / 180)];   // 0° = oben, im Uhrzeigersinn
  const f1 = n => n.toFixed(1);

  // Ring-Symbol: lokal gefüllt, Deutschland Ring mit Kern, Welt nur Kontur
  function kern(ring, gross) {
    const s = gross ? 1 : .62;
    if (ring === 'lokal') return `<circle r="${7.5 * s}" fill="#2EE6F5"/>`;
    if (ring === 'de') return `<circle r="${6.5 * s}" fill="#03070D" stroke="#2EE6F5" stroke-width="${3 * s}"/><circle r="${2.4 * s}" fill="#2EE6F5"/>`;
    return `<circle r="${6.5 * s}" fill="none" stroke="#2EE6F5" stroke-opacity=".8" stroke-width="${2.4 * s}"/>`;
  }
  function marker(ring) {
    const s = document.createElementNS(SVG, 'svg');
    s.setAttribute('viewBox', '-11 -11 22 22');
    s.innerHTML = kern(ring, true);   // nur feste Werte
    return s;
  }
  function ringTag(ring) {
    const t = el('span', 'tag ' + ring);
    t.appendChild(marker(ring));
    t.appendChild(document.createTextNode(RINGE[ring]));
    return t;
  }
  function quelle(text) {
    if (!text) return null;
    const q = document.createDocumentFragment();
    q.appendChild(document.createTextNode('Quelle: '));
    q.appendChild(el('b', '', text));
    return q;
  }

  /* ---------- Rahmen: Kopfleiste, Fortschritt, Inhalt, Fußleiste ---------- */
  function rahmen(klasse, { marke = 'SHIELD RADAR', links = null, kopf = true, fortschritt = true, fuss = true } = {}) {
    document.body.className = klasse;
    const f = el('div', 'flaeche');
    f.appendChild(el('div', 'punkte'));
    if (kopf) {
      const k = el('header', 'kopf');
      k.appendChild(markenZeile(marke));
      const a = el('div', 'ausgabe');
      a.appendChild(el('span', 'datum', info.datum));
      a.appendChild(el('span', 'strich'));
      a.appendChild(el('span', 'nr', '#' + zwei(info.ausgabe)));
      k.appendChild(a);
      f.appendChild(k);
    }
    if (fortschritt) {
      const p = el('div', 'fortschritt');
      for (let i = 1; i <= slides.length; i++) p.appendChild(el('i', i < seite ? 'war' : i === seite ? 'jetzt' : ''));
      f.appendChild(p);
    }
    const inhalt = el('main', 'inhalt');
    f.appendChild(inhalt);
    if (fuss) {
      const u = el('footer', 'fuss');
      const l = el('span', 'quelle');
      if (typeof links === 'string') setzeText(l, links); else if (links) l.appendChild(links);
      u.appendChild(l);
      u.appendChild(el('span', 'handle', '@energy.shield.rave'));
      f.appendChild(u);
    }
    f.appendChild(el('div', 'grain'));
    f.appendChild(el('div', 'scan'));
    document.body.appendChild(f);
    return inhalt;
  }
  function markenZeile(text) {
    const m = el('div', 'marke');
    if (daten.logo) { const img = el('img'); img.src = daten.logo; m.appendChild(img); }
    m.appendChild(el('span', '', text));
    return m;
  }
  function anrissListe(liste) {
    const ol = el('ol', 'anrisse');
    for (const m of liste) {
      const li = el('li');
      li.appendChild(el('span', 'nrtag', zwei(m.nr)));
      if (RINGE[m.ring]) { const s = marker(m.ring); s.classList.add('punkt'); li.appendChild(s); }
      li.appendChild(el('span', 'anriss', m.anriss));
      ol.appendChild(li);
    }
    return ol;
  }

  /* ---------- Radar ---------- */
  // Winkel aus dem Titel (gleich bei jedem Rendern), pro Ring gleichmäßig über den Bogen verteilt
  function platziere(R) {
    const out = [];
    for (const ring of Object.keys(BAND)) {
      const liste = [...meldungen, ...kurzpunkte].filter(p => p.ring === ring)
        .sort((x, y) => hash(x.titel + ring) - hash(y.titel + ring));
      const n = liste.length;
      if (!n) continue;
      const [a0, a1] = BOGEN, slot = (a1 - a0) / n;
      const versatz = (zufall('v' + info.ausgabe + ring) - .5) * slot * .5;
      liste.forEach((p, i) => {
        let a = a0 + slot * (i + .5) + versatz + (zufall(p.titel + 'w') - .5) * slot * .3;
        a = Math.min(a1 - 3, Math.max(a0 + 3, a));
        const [b0, b1] = BAND[ring];
        out.push({ ...p, a, r: R * (b0 + (b1 - b0) * zufall(p.titel + 'r')) });
      });
    }
    return out;
  }

  // Nummern-Etiketten neben die Punkte setzen, ohne Punkte, Logo, Ring-Namen oder andere Etiketten zu verdecken
  function etiketten(punkte, R, opt) {
    const g = opt.g, LW = 50 * g, LH = 30 * g, LA = 17 * g;
    const kreise = punkte.map(p => { const [x, y] = pos(p.a, p.r); p.x = x; p.y = y; return { x, y, r: (p.klein ? 7 : 18) * g, p }; });
    const schneidet = (a, b) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
    const trifft = (b, k) => { const nx = Math.max(b.x0, Math.min(k.x, b.x1)), ny = Math.max(b.y0, Math.min(k.y, b.y1)); return (nx - k.x) ** 2 + (ny - k.y) ** 2 < k.r ** 2; };
    const logo = R * .12;
    const belegt = [{ x0: -logo, y0: -logo, x1: logo, y1: logo }];
    if (opt.detail) for (const [ring, name] of Object.entries(RINGE)) {
      const rr = R * GRENZE[ring] - 16 * g, w = name.length * 15 * g + 10, h = Math.min(Math.PI * .9, (w / 2) / rr);
      belegt.push({ x0: -rr * Math.sin(h), x1: rr * Math.sin(h), y0: -rr - 14 * g, y1: -rr * Math.cos(h) + 4 });
    }
    for (const p of punkte.filter(p => !p.klein && opt.nummern.has(p.nr)).sort((a, b) => a.nr - b.nr)) {
      const rechts = p.x >= 0;
      const kandidaten = [
        rechts ? [p.x + LA, p.y - LH / 2] : [p.x - LA - LW, p.y - LH / 2],
        rechts ? [p.x - LA - LW, p.y - LH / 2] : [p.x + LA, p.y - LH / 2],
        [p.x - LW / 2, p.y - LA - LH], [p.x - LW / 2, p.y + LA]];
      let wahl = null;
      for (const [x0, y0] of kandidaten) {
        const b = { x0, y0, x1: x0 + LW, y1: y0 + LH };
        // ganz innerhalb des Radarkreises bleiben, damit Gradskala und Gradzahlen frei bleiben
        const draussen = [[b.x0, b.y0], [b.x1, b.y0], [b.x0, b.y1], [b.x1, b.y1]].some(([x, y]) => Math.hypot(x, y) > R - 3);
        if (draussen || belegt.some(o => schneidet(b, o)) || kreise.some(k => k.p !== p && trifft(b, k))) continue;
        wahl = b;
        break;
      }
      if (!wahl) fehler.push(`Radar: Etikett ${zwei(p.nr)} findet keinen freien Platz`);
      else { p.etikett = wahl; belegt.push(wahl); }
    }
    for (let i = 0; i < kreise.length; i++) for (let j = i + 1; j < kreise.length; j++) {
      if (Math.hypot(kreise[i].x - kreise[j].x, kreise[i].y - kreise[j].y) < kreise[i].r + kreise[j].r) fehler.push('Radar: Punkte überlappen');
    }
  }

  function grundSVG(R, opt, kante) {
    const t = [];
    t.push('<defs><radialGradient id="scheibe"><stop offset="0" stop-color="#2EE6F5" stop-opacity=".14"/>'
      + '<stop offset=".42" stop-color="#0B3350" stop-opacity=".55"/><stop offset="1" stop-color="#03070D" stop-opacity=".92"/></radialGradient></defs>');
    t.push(`<circle r="${R}" fill="url(#scheibe)"/>`);
    t.push(`<circle r="${f1(R * GRENZE.lokal)}" fill="#2EE6F5" fill-opacity=".05"/>`);
    const d = f1(R * .7071);
    t.push(`<g stroke="#2EE6F5" stroke-width="1"><line x1="${-R}" x2="${R}" stroke-opacity=".14"/><line y1="${-R}" y2="${R}" stroke-opacity=".14"/>`
      + `<line x1="-${d}" y1="-${d}" x2="${d}" y2="${d}" stroke-opacity=".06"/><line x1="-${d}" y1="${d}" x2="${d}" y2="-${d}" stroke-opacity=".06"/></g>`);
    for (const f of [.535, .845]) t.push(`<circle r="${f1(R * f)}" fill="none" stroke="#2EE6F5" stroke-opacity=".12" stroke-dasharray="2 7"/>`);
    t.push(`<circle r="${f1(R * GRENZE.lokal)}" fill="none" stroke="#2EE6F5" stroke-opacity=".5" stroke-width="1.5"/>`);
    t.push(`<circle r="${f1(R * GRENZE.de)}" fill="none" stroke="#2EE6F5" stroke-opacity=".4" stroke-width="1.5"/>`);
    t.push(`<circle r="${R}" fill="none" stroke="#2EE6F5" stroke-width="${2.5 * opt.g}"/>`);
    if (opt.skala) for (let w = 0; w < 360; w += 5) {
      const lang = (w % 30 === 0 ? 20 : w % 15 === 0 ? 13 : 8) * opt.g;
      const [x1, y1] = pos(w, R + 6 * opt.g), [x2, y2] = pos(w, R + 6 * opt.g + lang);
      t.push(`<line x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}" stroke="#2EE6F5" stroke-opacity="${w % 30 ? .3 : .8}" stroke-width="${w % 30 ? 1.5 : 2}"/>`);
      if (opt.detail && w % 30 === 0) {
        const [x, y] = pos(w, R + 38 * opt.g);
        t.push(`<text x="${f1(x)}" y="${f1(y)}" text-anchor="middle" dominant-baseline="central" font-size="${13 * opt.g}" fill="#8CA3B5" letter-spacing="1">${String(w).padStart(3, '0')}</text>`);
      }
    }
    if (opt.detail) {
      for (const [ring, name] of Object.entries(RINGE)) {
        const r = f1(R * GRENZE[ring] - 16 * opt.g);
        t.push(`<path id="bogen-${ring}" d="M -${r} 0 A ${r} ${r} 0 0 1 ${r} 0" fill="none"/>`);
        t.push(`<text font-size="${14 * opt.g}" letter-spacing="${4 * opt.g}" fill="#2EE6F5" fill-opacity=".8"><textPath href="#bogen-${ring}" startOffset="50%" text-anchor="middle">${name.toUpperCase()}</textPath></text>`);
      }
      // Rauschen wie auf einem echten Schirm, hinter dem Strahl heller
      const z = prng(hash('rauschen' + info.ausgabe));
      for (let i = 0; i < 90; i++) {
        const a = z() * 360, r = R * Math.sqrt(.02 + z() * .96), hinten = ((kante - a) % 360 + 360) % 360;
        const o = (.05 + z() * .16) * (hinten < 90 ? 2.2 - hinten / 75 : 1);
        const [x, y] = pos(a, r);
        t.push(`<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1((.8 + z() * 1.3) * opt.g)}" fill="#8CF0FA" fill-opacity="${o.toFixed(2)}"/>`);
      }
    }
    return t.join('');
  }

  function obenSVG(R, punkte, opt, kante) {
    const t = [];
    const [ex, ey] = pos(kante, R);
    t.push(`<defs><linearGradient id="kante" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="${f1(ex)}" y2="${f1(ey)}">`
      + '<stop offset="0" stop-color="#2EE6F5" stop-opacity=".08"/><stop offset="1" stop-color="#2EE6F5"/></linearGradient></defs>');
    t.push(`<line x1="0" y1="0" x2="${f1(ex)}" y2="${f1(ey)}" stroke="url(#kante)" stroke-width="${2.5 * opt.g}"/>`);
    for (const p of punkte) {
      const hinten = ((kante - p.a) % 360 + 360) % 360;
      const hell = (1 - .5 * hinten / 360) * (opt.hervor && p.nr !== opt.hervor ? .3 : 1);
      t.push(`<g transform="translate(${f1(p.x)} ${f1(p.y)}) scale(${opt.g})" opacity="${hell.toFixed(2)}">`);
      if (!p.klein) t.push('<circle r="18" fill="#2EE6F5" fill-opacity=".14"/><circle r="18" fill="none" stroke="#2EE6F5" stroke-opacity=".45" stroke-width="1.2"/>');
      t.push(kern(p.ring, !p.klein) + '</g>');
    }
    for (const p of punkte.filter(p => p.etikett)) {
      const { x0, y0, x1, y1 } = p.etikett, c = 7 * opt.g;
      t.push(`<polygon points="${f1(x0 + c)},${f1(y0)} ${f1(x1)},${f1(y0)} ${f1(x1)},${f1(y1 - c)} ${f1(x1 - c)},${f1(y1)} ${f1(x0)},${f1(y1)} ${f1(x0)},${f1(y0 + c)}" `
        + `fill="#03070D" fill-opacity=".88" stroke="#2EE6F5" stroke-width="${1.5 * opt.g}"/>`);
      t.push(`<text x="${f1((x0 + x1) / 2)}" y="${f1((y0 + y1) / 2 + 1)}" text-anchor="middle" dominant-baseline="central" font-size="${18 * opt.g}" font-weight="900" fill="#FFFFFF">${zwei(p.nr)}</text>`);
    }
    return t.join('');
  }

  // opt: detail (Gradzahlen, Ring-Namen, Rauschen), skala, g (Größe der Punkte), nummern (Set), hervor (nr), weiter (Grad, um den der Strahl weitergedreht ist)
  function zeichneRadar(box, R, opt) {
    const P = opt.P;
    const D = 2 * (R + P);
    const wrap = el('div', 'radar');
    wrap.style.width = D + 'px';
    wrap.style.height = D + 'px';
    const punkte = platziere(R);
    etiketten(punkte, R, opt);
    const ziel = punkte.find(p => !p.klein && p.nr === (opt.hervor || 1));
    const kante = (((ziel ? ziel.a : 120) + 14 + (opt.weiter || 0)) % 360 + 360) % 360;   // Strahl hat Meldung 1 gerade erfasst
    const vb = `${-(R + P)} ${-(R + P)} ${D} ${D}`;
    const grund = document.createElementNS(SVG, 'svg');
    grund.setAttribute('viewBox', vb);
    grund.innerHTML = grundSVG(R, opt, kante);
    const strahl = el('div', 'strahl');
    Object.assign(strahl.style, {
      left: P + 'px', top: P + 'px', width: 2 * R + 'px', height: 2 * R + 'px',
      background: `conic-gradient(from ${f1(kante - 90)}deg, rgba(46,230,245,0) 0deg, rgba(46,230,245,.05) 45deg, rgba(46,230,245,.36) 90deg, rgba(46,230,245,0) 90.3deg)`,
    });
    const oben = document.createElementNS(SVG, 'svg');
    oben.setAttribute('viewBox', vb);
    oben.classList.add('oben');
    oben.innerHTML = obenSVG(R, punkte, opt, kante);
    if (daten.logo) {
      const s = R * .2, img = document.createElementNS(SVG, 'image');
      img.setAttribute('href', daten.logo);
      for (const [k, v] of Object.entries({ x: -s / 2, y: -s / 2, width: s, height: s, preserveAspectRatio: 'xMidYMid meet', class: 'logo' })) img.setAttribute(k, v);
      oben.appendChild(img);
    }
    wrap.append(grund, strahl, oben);
    box.appendChild(wrap);
  }
  function radius(box, P, max, min) {
    const r = Math.floor(Math.min(box.clientWidth, box.clientHeight) / 2) - P;
    if (r < min) fehler.push('Zu wenig Platz für das Radar');
    return Math.max(min, Math.min(max, r));
  }

  /* ---------- Vorlagen ---------- */
  function cover() {
    if (!meldungen.length) fehler.push('Karussell ohne radar-meldung');
    const inhalt = rahmen('cover', { marke: 'ENERGYSHIELD', links: 'Neue Ausgabe alle zwei Wochen' });
    inhalt.appendChild(el('div', 'cover-titel fit-zeile', 'SHIELD RADAR'));
    inhalt.appendChild(el('p', 'cover-unter', 'Szene-News von nebenan bis weltweit.'));
    const box = el('div', 'radar-box');
    inhalt.appendChild(box);
    inhalt.appendChild(anrissListe(meldungen));
    const opt = { detail: true, skala: true, g: 1, P: 46, nummern: new Set(meldungen.map(m => m.nr)) };
    return () => zeichneRadar(box, radius(box, opt.P, 330, 200), opt);
  }

  function meldung() {
    pflicht(S, ['ring', 'titel', 'text', 'quelle']);   // nur Fakten mit Quelle
    const nr = meldungen.findIndex(m => m.slide === S) + 1;
    const inhalt = rahmen('meldung', { links: quelle(S.quelle) });
    const kopf = el('div', 'm-kopf');
    const meta = el('div', 'm-meta');
    const tags = el('div', 'm-tags');
    tags.appendChild(el('span', 'nrtag', zwei(nr)));
    if (RINGE[S.ring]) tags.appendChild(ringTag(S.ring));
    if (S.kategorie) tags.appendChild(el('span', 'tag leise', S.kategorie));
    meta.appendChild(tags);
    if (S.ort) meta.appendChild(el('div', 'm-ort', S.ort));
    kopf.appendChild(meta);
    const mini = el('div', 'mini');
    kopf.appendChild(mini);
    inhalt.appendChild(kopf);
    const koerper = el('div', 'm-koerper');
    koerper.appendChild(el('h1', 'titel', S.titel));
    koerper.appendChild(el('p', 'text', S.text));
    if (S.wichtig) {
      const w = el('div', 'wichtig');
      w.appendChild(el('div', 'w-label', 'Warum das wichtig ist'));
      w.appendChild(el('p', 'w-text', S.wichtig));
      koerper.appendChild(w);
    }
    inhalt.appendChild(koerper);
    const opt = { detail: false, skala: true, g: .8, P: 30, hervor: nr, nummern: new Set([nr]) };
    return () => zeichneRadar(mini, radius(mini, opt.P, 110, 80), opt);
  }

  function kurz() {
    if (!(S.punkte || []).length) fehler.push('radar-kurz braucht "punkte"');
    for (const p of S.punkte || []) if (!p.quelle) fehler.push('radar-kurz: Kurzmeldung ohne "quelle"');
    const inhalt = rahmen('kurz', { links: 'Alle Quellen stehen auch in der Caption.' });
    inhalt.appendChild(el('h2', 'k-titel', 'Kurz notiert'));
    inhalt.appendChild(el('p', 'k-unter', 'Was sonst noch auf dem Radar war.'));
    const ul = el('ul', 'k-liste');
    for (const p of S.punkte || []) {
      const li = el('li');
      const r = el('div', 'k-ring');
      if (RINGE[p.ring]) r.appendChild(ringTag(p.ring));
      li.appendChild(r);
      const b = el('div');
      b.appendChild(el('p', 'k-text', p.text));
      if (p.quelle) b.appendChild(el('p', 'k-quelle', 'Quelle: ' + p.quelle));
      li.appendChild(b);
      ul.appendChild(li);
    }
    inhalt.appendChild(ul);
  }

  function wissen() {
    pflicht(S, ['begriff', 'text']);
    const inhalt = rahmen('wissen', { links: quelle(S.quelle) });
    const k = el('div', 'w-kopf');
    k.appendChild(el('span', 'tag', 'Szene-Wissen'));
    inhalt.appendChild(k);
    inhalt.appendChild(el('div', 'begriff fit-zeile', S.begriff));
    inhalt.appendChild(el('div', 'skala'));
    if (S.titel) inhalt.appendChild(el('h1', 'titel', S.titel));
    inhalt.appendChild(el('p', 'text', S.text));
  }

  function ende() {
    pflicht(S, ['frage']);
    const inhalt = rahmen('ende', { links: 'Alle Quellen stehen in der Caption.' });
    const box = el('div', 'radar-box');
    inhalt.appendChild(box);
    inhalt.appendChild(el('h1', 'titel', S.frage));
    inhalt.appendChild(el('p', 'e-unter', 'Schreibt es uns in die Kommentare.'));
    const infos = el('div', 'e-infos');
    const zelle = (label, wert, klasse) => { const z = el('div', 'e-zelle'); z.appendChild(el('span', 'e-label', label)); z.appendChild(el('span', 'e-wert ' + (klasse || ''), wert)); infos.appendChild(z); };
    zelle('Tipps für die nächste Ausgabe', 'Per DM an uns');
    if (S.naechste) zelle('Nächste Ausgabe', S.naechste, 'zahl');
    inhalt.appendChild(infos);
    const opt = { detail: false, skala: true, g: .85, P: 30, weiter: 150, nummern: new Set() };
    return () => zeichneRadar(box, radius(box, opt.P, 200, 120), opt);
  }

  function story() {
    if (!meldungen.length) fehler.push('radar-story braucht "meldungen"');
    const inhalt = rahmen('story', { kopf: false, fortschritt: false, fuss: false });
    inhalt.appendChild(markenZeile('ENERGYSHIELD'));
    inhalt.appendChild(el('div', 's-neu', 'Neue Ausgabe'));
    inhalt.appendChild(el('div', 's-titel fit-zeile', 'SHIELD RADAR'));
    const z = el('div', 's-zeile');
    z.appendChild(el('span', 'nr', '#' + zwei(info.ausgabe)));
    z.appendChild(el('span', 'strich'));
    z.appendChild(el('span', 'datum', info.datum));
    inhalt.appendChild(z);
    const box = el('div', 'radar-box');
    inhalt.appendChild(box);
    inhalt.appendChild(anrissListe(meldungen));
    inhalt.appendChild(el('span', 'tag lokal s-cta', 'Jetzt im Feed'));
    const opt = { detail: true, skala: true, g: 1.15, P: 58, nummern: new Set(meldungen.map(m => m.nr)) };
    return () => zeichneRadar(box, radius(box, opt.P, 400, 220), opt);
  }

  /* ---------- Auto-Fit: erst einzeilige Titel, dann Schlagzeilen und Text verkleinern ---------- */
  function passeAn() {
    for (const e of document.querySelectorAll('.fit-zeile')) {
      let g = parseFloat(getComputedStyle(e).fontSize);
      while (e.scrollWidth > e.clientWidth + 1 && g > 24) { g -= 2; e.style.fontSize = g + 'px'; }
    }
    const wurzel = document.documentElement.style;
    const titel = [...document.querySelectorAll('.titel, .k-titel')];
    const inhalt = document.querySelector('.inhalt');
    let hs = 1, ts = 1;
    const setze = () => { wurzel.setProperty('--hs', hs.toFixed(3)); wurzel.setProperty('--ts', ts.toFixed(3)); };
    const zuBreit = () => titel.some(e => e.scrollWidth > e.clientWidth + 1);
    const zuHoch = () => inhalt.scrollHeight > inhalt.clientHeight + 1;
    while (zuBreit() && hs > .5) { hs -= .02; setze(); }
    while (zuHoch() && (hs > .55 || ts > .89)) { hs = Math.max(.55, hs - .03); ts = Math.max(.89, ts - .015); setze(); }
    if (zuBreit()) fehler.push('Ein Wort in der Schlagzeile ist zu lang');
    if (zuHoch()) fehler.push('Zu viel Text für die Slide');
    for (const e of document.querySelectorAll('.fit-zeile')) if (e.scrollWidth > e.clientWidth + 1) fehler.push('Begriff zu lang');
  }

  const BAUER = { 'radar-cover': cover, 'radar-meldung': meldung, 'radar-kurz': kurz, 'radar-wissen': wissen, 'radar-ende': ende, 'radar-story': story };
  async function los() {
    try {
      const bauer = BAUER[S.vorlage];
      if (!bauer) throw new Error(`Unbekannte Vorlage "${S.vorlage}"`);
      const danach = bauer();
      const schnitte = ['800 40px Unbounded', '700 40px Unbounded', '500 30px Montserrat', '600 30px Montserrat', '700 30px Montserrat', '800 30px Montserrat', '700 20px Orbitron', '900 20px Orbitron'];
      await Promise.all(schnitte.map(s => document.fonts.load(s, 'ÄÖÜß#01')));
      await document.fonts.ready;
      passeAn();
      if (danach) danach();
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
