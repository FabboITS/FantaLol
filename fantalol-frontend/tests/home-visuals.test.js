const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const stylesheet = fs.readFileSync(path.join(__dirname, '../css/style.css'), 'utf8');
const favicon = fs.readFileSync(path.join(__dirname, '../favicon.svg'), 'utf8');
const homepage = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');

test('hero portraits use original card sizes and high-resolution player assets', () => {
  assert.match(stylesheet, /\.hero-player-image\{[^}]*object-fit:cover/);
  assert.match(stylesheet, /\.card-main\{width:310px;height:450px/);
  assert.match(stylesheet, /\.card-back\{width:235px;height:330px/);
  assert.match(stylesheet, /\.card-main \.hero-player-image\{[^}]*object-position:center top/);
  assert.match(stylesheet, /\.card-back \.hero-player-image\{[^}]*object-position:center top/);
  assert.match(homepage, /src="\/Player_immage\/other\/Caps_1\.webp"/);
  assert.match(homepage, /src="\/Player_immage\/other\/BB_1\.webp"/);
  assert.match(homepage, /alt="BrokenBlade, top laner"/);
  assert.match(homepage, /<span>TOPLANER<\/span><b>BROKENBLADE<\/b>/);
  assert.doesNotMatch(homepage, /SkewMond|SKEWMOND|<span>JUNGLE<\/span>/);
  assert.doesNotMatch(stylesheet, /filter:\s*(?:contrast|sharpen)/);
});

test('rules dialog is centered and preserves bottom depth', () => {
  assert.match(stylesheet, /\.rules-dialog\{[^}]*margin:auto/);
  assert.match(stylesheet, /\.rules-dialog::after\{[^}]*linear-gradient/);
  assert.match(stylesheet, /\.rules-dialog::after\{[^}]*pointer-events:none/);
  assert.match(stylesheet, /\.rules-content\{[^}]*padding:0 18px 48px 0/);
});

test('favicon letter uses the page brand gradient', () => {
  assert.match(favicon, /<linearGradient[^>]*id="brand-gradient"/);
  assert.match(favicon, /#4f8cff/i);
  assert.match(favicon, /#8b5cf6/i);
  assert.match(favicon, /<path[^>]*fill="url\(#brand-gradient\)"/);
  assert.doesNotMatch(favicon, /#c8ff33/i);
});

test('public rules publish the approved Summer 2026 scoring system', () => {
  assert.match(homepage, /Top[^<]*3,00[^<]*2,00[^<]*-2,00[^<]*1,25/);
  assert.match(homepage, /Jungle[^<]*3,00[^<]*2,25[^<]*-2,00[^<]*0,70/);
  assert.match(homepage, /Mid[^<]*3,00[^<]*2,00[^<]*-2,00[^<]*1,00/);
  assert.match(homepage, /ADC[^<]*3,25[^<]*1,75[^<]*-2,25[^<]*1,10/);
  assert.match(homepage, /Support[^<]*2,15[^<]*2,55[^<]*-1,75/);
  assert.match(homepage, /1 punto ogni 50 di vision score/);
  assert.match(homepage, /CS dei Support non assegnano punti/);
  assert.match(homepage, /CS sono calcolati in modo continuo/);
  assert.match(homepage, /Ogni vittoria assegna 3 punti/);
  assert.doesNotMatch(homepage, /MVP <b>\+3<\/b>|VITTORIA <b>\+1<\/b>/);
});

test('public rules explain cumulative scoring, lineup timing and synchronization', () => {
  assert.match(homepage, /media aritmetica di tutte le partite effettivamente disputate.*Summer Split/);
  assert.match(homepage, /non viene aggiunto uno zero alla sua media cumulativa/);
  assert.match(homepage, /riserve ricevono.*valutazione individuale.*non contribuiscono.*fantasy team/);
  assert.match(homepage, /martedì alle 00:00.*giovedì alle 23:59:59.*Europe\/Rome/);
  assert.match(homepage, /efficace dal venerdì alle 00:00/);
  assert.match(homepage, /più di 5 fantasy team.*formazione è fissa.*non può essere modificata/);
  assert.match(homepage, /sincronizza automaticamente.*ogni 6 ore/);
  assert.match(homepage, /Sincronizza ora.*ritenta.*fonti.*non può creare dati.*incompleti/);
});
