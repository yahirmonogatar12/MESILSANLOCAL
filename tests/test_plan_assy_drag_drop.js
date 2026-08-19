// Check de movePlanInGroups (drag & drop de Control de produccion ASSY).
// Correr:  node tests/test_plan_assy_drag_drop.js
const assert = require('assert');

globalThis.window = globalThis; // el modulo hace window.x = ... al cargarse
const { movePlanInGroups } = require('../app/static/js/plan-assy-groups.js');

const build = () => [
  { plans: [{ lot_no: 'A' }, { lot_no: 'B' }, { lot_no: 'C' }] },
  { plans: [{ lot_no: 'X' }, { lot_no: 'Y' }] },
];
const lots = g => g.map(gr => gr.plans.map(p => p.lot_no).join(''));

// Mover hacia abajo dentro del grupo: A antes de C -> B, A, C
let g = build();
assert.ok(movePlanInGroups(g, 'A', 0, 2));
assert.deepStrictEqual(lots(g), ['BAC', 'XY']);

// Mover hacia arriba dentro del grupo: C al inicio
g = build();
assert.ok(movePlanInGroups(g, 'C', 0, 0));
assert.deepStrictEqual(lots(g), ['CAB', 'XY']);

// Entre grupos, en la posicion exacta (antes de Y)
g = build();
assert.ok(movePlanInGroups(g, 'B', 1, 1));
assert.deepStrictEqual(lots(g), ['AC', 'XBY']);

// insertIndex null = al final del grupo destino
g = build();
assert.ok(movePlanInGroups(g, 'A', 1, null));
assert.deepStrictEqual(lots(g), ['BC', 'XYA']);

// Lote inexistente o grupo inexistente: no toca nada
g = build();
assert.strictEqual(movePlanInGroups(g, 'ZZZ', 0, 0), false);
assert.strictEqual(movePlanInGroups(g, 'A', 9, 0), false);
assert.deepStrictEqual(lots(g), ['ABC', 'XY']);

console.log('OK - movePlanInGroups');
