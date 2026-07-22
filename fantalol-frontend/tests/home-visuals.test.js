const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const stylesheet = fs.readFileSync(path.join(__dirname, '../css/style.css'), 'utf8');

test('hero portraits use smaller filled cards and player-specific crops', () => {
  assert.match(stylesheet, /\.hero-player-image\{[^}]*object-fit:cover/);
  assert.match(stylesheet, /\.card-main\{width:280px;height:410px/);
  assert.match(stylesheet, /\.card-back\{width:210px;height:300px/);
  assert.match(stylesheet, /\.card-main \.hero-player-image\{[^}]*object-position:center top/);
  assert.match(stylesheet, /\.card-back \.hero-player-image\{[^}]*object-position:center top/);
  assert.doesNotMatch(stylesheet, /filter:\s*(?:contrast|sharpen)/);
});

test('rules dialog is centered and preserves bottom depth', () => {
  assert.match(stylesheet, /\.rules-dialog\{[^}]*margin:auto/);
  assert.match(stylesheet, /\.rules-dialog::after\{[^}]*linear-gradient/);
  assert.match(stylesheet, /\.rules-dialog::after\{[^}]*pointer-events:none/);
  assert.match(stylesheet, /\.rules-content\{[^}]*padding:0 18px 48px 0/);
});
