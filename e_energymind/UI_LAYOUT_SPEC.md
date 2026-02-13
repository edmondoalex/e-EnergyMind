# e-EnergyMind UI Layout Spec (baseline)

Questo documento descrive la struttura della UI attuale (User/Admin) da usare come layout di riferimento per la ricostruzione grafica.

## Struttura globale
- `wrap` (contenitore pagina, flex column)
- `top` (header sticky)
  - `brand`
  - `top-actions`: `Salva tutto`, `Esporta config`, `Importa config` (file input)
  - `tabs`: `User` / `Admin`
- `main` (contenitore centrale)

## Tab User (sezione principale)
Tutto il contenuto User è dentro una `card` principale, con molte `card inner` successive.

1. **Stato**
   - `h2` titolo
   - `statusline` con: versione, runtime_mode, badge HA online/offline, ultimo aggiornamento
   - testo `Dry-run` quando non in `live`

2. **KPI Grid** (`grid`)
   - 8 KPI principali (temperatura / export) a griglia 2 colonne mobile, 4 colonne desktop
   - `row3` successivo con 3 KPI “ACS Alto/Medio/Basso”
   - KPI cliccabili se history abilitata

3. **Grafici rapidi** (`card inner module-panel`)
   - titolo “Grafico rapido”
   - `chart-grid` con 2 grafici sparkline:
     - Temperature (ACS/Puffer/Volano)
     - Export (W)
   - note assi + legenda

4. **Moduli (User)** (`card inner`)
   - elenco toggle moduli in `row3` (bottoni `ghost toggle`)
   - include: resistenze_volano, volano_to_acs, volano_to_puffer, puffer_to_acs, impianto, gas_emergenza, caldaia_legna, solare, miscelatrice, curva_climatica, pdc

5. **Pannello logica (destinazione surplus)** (`card inner module-panel`)
   - riepilogo `dest`, `source_to_acs`, `charge_buffer`
   - elenco “Module reasons” con stato/attivo e motivazione

6. **Pannelli modulo (User)** (`card inner module-panel`)
   - Pannelli dettagliati per moduli (diverse card):
     - Resistenze volano
     - Volano → ACS
     - Volano → Puffer
     - Puffer → ACS
     - Impianto riscaldamento
     - Gas emergenza
     - Caldaia legna
     - Solare (include modalità/parametri)
     - Miscelatrice
     - Curva climatica
     - PDC
   - Ogni pannello ha KPI, stato attuatori, valori input, delta e/o setpoint

7. **Schema impianto** (`card inner diagram`)
   - immagine di sfondo (foto/diagramma)
   - overlay SVG con nodi, linee, flow animation, dot pulse

8. **Zonizzazione / Termostati**
   - card “Zones” con griglia `zones-grid` di chip/stati
   - modal termostato per modifica setpoint (UI tipo “thermo ring”)

9. **Storico**
   - modal con grafico storico (SVG) per KPI cliccati

## Tab Admin (sezione principale)
Tutto il contenuto Admin è dentro una `card` principale, con molte `card inner` successive.

1. **Stato Admin**
   - riepilogo versione/runtime/HA simile al tab User

2. **Config base**
   - form per `log_level`, `ha_url`, `ha_token`, poll interval
   - `Salva` / `Reset` / `Refresh` (azioni)

3. **Setpoint**
   - `setpoint-grid` a colonne (1 col mobile, 2 col desktop)
   - sezioni con titoli e input numerici, select e help text

4. **Mapping Entità HA**
   - mappa input per sensori/entità
   - indicatori “input-ok”

5. **Mapping Attuatori**
   - elenco attuatori R1…R30 con select entità
   - comandi manuali e stato attuatori

6. **Moduli Admin**
   - toggle abilita/disabilita moduli
   - eventuali configurazioni per modulo (dipende dalla logica)

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
