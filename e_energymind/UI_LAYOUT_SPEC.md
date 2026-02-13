# e-EnergyMind UI Layout Spec (baseline)

Questo documento descrive la struttura della UI attuale (User/Admin) per la versione energia.

## Struttura globale
- `wrap` (contenitore pagina, flex column)
- `top` (header sticky)
  - `brand`
  - `top-actions`: `Salva tutto`, `Esporta config`, `Importa config` (file input)
  - `tabs`: `User` / `Admin`
- `main` (contenitore centrale)

## Tab User (sezione principale)
Tutto il contenuto User è dentro una `card` principale, con `card inner` per ogni utenza.

1. **Stato**
   - `h2` titolo
   - `statusline` con: versione, runtime_mode, badge HA online/offline, ultimo aggiornamento
   - testo `Dry-run` quando non in `live`

2. **Card Utenza (ripetuta per N utenze)** (`card inner`)
   - `grid` con KPI energia (PV, load, grid, import/export, battery power, SOC, temp)
   - `row3` con KPI energia giornalieri (produzione, consumo, import)
   - `row3` con KPI forecast (export, forecast oggi/domani)

3. **Ultime azioni** (`card inner`)
   - log azioni (se presente)

## Tab Admin (sezione principale)
Tutto il contenuto Admin è dentro una `card` principale.

1. **Stato Admin**
   - riepilogo versione/runtime/HA simile al tab User

2. **Config base**
   - selezione numero utenze (1-3)
   - runtime mode e polling UI

3. **Mapping Entità Energia**
   - elenco campi per ogni utenza
   - indicatori “input-ok”

## Componenti ricorrenti
- `card`, `card inner`, `module-panel`
- `grid`, `row2`, `row3`
- `kpi`, `kpi-center`, `clickable`
- `badge`, `badge-mini`
- `chart-grid`, `chart`, `spark` (sparkline)
- `modal` (history e termostato)
- `diagram` con overlay SVG

## Note di layout
- Layout a card verticali, con molta “densità” di info.
- Interazione principale via toggle e KPI cliccabili.
- Tab Admin concentra configurazione e mapping.
