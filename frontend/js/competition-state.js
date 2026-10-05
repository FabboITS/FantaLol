/* Selettore globale di competizione (LEC · LCK · LPL · WORLDS), salvato in localStorage. */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.CompetitionState = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    const STORAGE_KEY = 'fantalol_competition';
    const COMPETITIONS = [
        {code: 'LEC', label: 'LEC', name: 'LoL EMEA Championship', ruleset: 'REGIONAL'},
        {code: 'LCK', label: 'LCK', name: 'LoL Champions Korea', ruleset: 'REGIONAL'},
        {code: 'LPL', label: 'LPL', name: 'LoL Pro League', ruleset: 'REGIONAL'},
        {code: 'WORLDS', label: 'WORLDS', name: 'World Championship', ruleset: 'WORLDS'}
    ];
    const CODES = COMPETITIONS.map(item => item.code);

    function normalize(code) {
        const value = String(code || '').toUpperCase();
        return CODES.includes(value) ? value : 'LEC';
    }

    function read(storage) {
        try {
            return normalize(storage?.getItem(STORAGE_KEY));
        } catch (error) {
            return 'LEC';
        }
    }

    function write(storage, code) {
        const value = normalize(code);
        try {
            storage?.setItem(STORAGE_KEY, value);
        } catch (error) {
            /* storage non disponibile: la scelta vale solo per la pagina corrente */
        }
        return value;
    }

    function isWorlds(code) {
        return normalize(code) === 'WORLDS';
    }

    function find(code) {
        return COMPETITIONS.find(item => item.code === normalize(code));
    }

    function chipsHtml(selected, attribute = 'data-competition') {
        const current = normalize(selected);
        return COMPETITIONS.map(item => `<button type="button" class="competition-chip${item.code === current ? ' active' : ''}" ${attribute}="${item.code}" aria-pressed="${item.code === current}">${item.label}</button>`).join('');
    }

    return {STORAGE_KEY, COMPETITIONS, CODES, normalize, read, write, isWorlds, find, chipsHtml};
});
