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
