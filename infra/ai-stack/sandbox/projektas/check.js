'use strict';

// Paleidimas: node check.js
// Saugus, greitas "testas", kurį agentas gali paleisti ir sutvarkyti.
const fs = require('node:fs');
const path = require('node:path');

const required = ['README.md', 'check.js', 'receptai.json'];
const missing = required.filter((failas) => !fs.existsSync(path.join(__dirname, failas)));

if (missing.length > 0) {
  console.error(`Trūksta failų: ${missing.join(', ')}`);
  process.exit(1);
}

let duomenys;
try {
  duomenys = JSON.parse(fs.readFileSync(path.join(__dirname, 'receptai.json'), 'utf8'));
} catch (err) {
  console.error(`receptai.json neperskaitomas: ${err.message}`);
  process.exit(1);
}

if (!Array.isArray(duomenys.receptai) || duomenys.receptai.length === 0) {
  console.error('receptai.json: laukas "receptai" turi būti ne tuščias masyvas');
  process.exit(1);
}

console.log(`OK: visi failai vietoje (${duomenys.receptai.length} receptai)`);
