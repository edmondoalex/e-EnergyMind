# e-EnergyMind — Project log (estratto dalla conversazione)
Data export: 2026-02-08 (Europe/Rome)

> Nota: non posso garantire un “verbatim transcript” perfetto al 100% dell’intera chat (limiti tecnici dell’interfaccia),
> ma questo documento contiene una traccia fedele e dettagliata di decisioni, requisiti e specifiche concordate.

## Obiettivo
- Portare la logica dall’insieme di blueprint ad un Add-on HA replicabile.
- UI in **Vue**, responsive: **Admin** (config/debug) + **User** (monitoraggio; in futuro schema animato).
- HA resta I/O (sensori/switch). Setpoint/stati/logica dentro addon.

## Nome Add-on
- **e-EnergyMind**

## 2026-02-13
- UI energia: pulizia totale dei riferimenti termici in User/Admin.
- Admin: selezione numero utenze (1-3) e mapping sensori energia.
- Backend: rimosse logiche termiche, API minimal per status/config/entities.
- Logger: dati ogni 10s su SQLite con retention 90 giorni.
- Auto-mapping entità da device HA (nome o device_id).

## Architettura concordata
- Motore modulare a “state machine”:
  1) ACS Orchestrator
  2) Puffer
  3) Volano + Resistenze (FV/export)
  4) Solare (valvole + ritorni + notte/cutback)
  5) Heat Radiator (miscelatrice mandata/ritorno)
  6) PDC (2 macchine) – per ora DISABLED/standby

## Setpoint e safety
- Setpoint **interni addon**:
  - ACS_SP, PUFFER_SP
  - VOLANO_TARGET = ACS_SP + margine (scelta “2”)
- Sicurezze configurabili:
  - ACS_MAX (+ isteresi)
  - VOLANO_MAX (+ isteresi)
  - (futuro) PUFFER_MAX

## Solare “impulsivo”
- Il solare su ACS può durare pochi minuti: NON deve bloccare carica riserva.
- Possibile: SOLAR→ACS mentre si carica VOLANO (PDC/resistenze) per ripartenza.

## Regola “ACS a regime”
- Se ACS è già a regime: non accendere PDC/resistenze “per ACS”.
- In quel caso, se c’è surplus, la destinazione diventa PUFFER (accumulo giorno/notte).

## Volano → ACS / Puffer (delta termico)
- Trasferimento (valvola + pompa) parte solo se:
  - T_volano >= T_dest + Δ_start
  - continua finché T_volano >= T_dest + Δ_hold

## Resistenze su export rete
- 3×1000W su volano.
- Step in base a export (immissione), con OFF delay 5s per evitare attacca/stacca.
- Condizionate dalla destinazione: ACS (se non a regime) o PUFFER (se ACS a regime).

## PDC
- 2 PDC (entrambe master), richiesto supporto alternanza/fallback.
- Stato attuale: non funzionanti → modulo PDC DISABLED in v1, attivabile da Admin quando pronte.

## Aggiornamenti 2026-02-08
- Fix encoding/charset in `config.yaml`, `web/index.html`, `web/src/App.vue`, `backend/logic.py`.
- UI Admin estesa per mapping entità HA + reload rapido.
- API backend aggiunte: `/api/entities` GET/POST.
- Validazione base payload e normalizzazione config/setpoint.
- Guardie su `thresholds_w` + formatting output decisioni.
- WS HA con reconnect/backoff e logging minimo.

## Aggiornamenti 2026-02-09
- Resistenze volano LIVE con off-delay, runtime mode UI (dry-run/live) e log azioni.
- Mapping completo attuatori R1–R30 + indicatori logica/presenza e icone HA.
- Moduli togglable in User/Admin con PIN opzionale.
- Export/Import configurazione e pulsanti header; setpoint compatti.
- Polling UI controllato (stop in Admin / durante editing).
- Dry-run con log simulati completi (moduli ON/OFF/DISABLED).
- Moduli ON evidenziati in rosso trasparente.
- Comandi manuali rimossi; toggle attuatori via pallino con bordo rosso se ON (User senza pallino).
- Header Admin: pulsanti config uniformati (stesso stile/colore) e duplicazione rimossa.
- Guard HA: se un attuatore viene acceso da HA mentre il modulo è attivo, auto spegnimento dopo 2s (UI esclusa).
- UI: WebSocket per aggiornamenti live su User/Admin con merge che non sovrascrive input in editing.
- Resistenze: switch generale + sensori potenza/energia integrati (UI + logica).
- Runtime mode persistente (salvataggio automatico) + generale resistenze segue step.

## Prossime implementazioni
- Validazione completa via schema (Pydantic) per `config`/`entities`/`setpoints`.
- Persistenza configurazione per `runtime.mode` e future azioni live.
- Motori logici modulari (ACS/Puffer/Volano/Solare/PDC) con state machine separata.
- Ingress UI: sezione stato attuatori + wiring per comandi live (v0.2+).
## UI Mapping Indicators (Do Not Change)
- Dot (green/red): mapped in logic (entity_id present)
- Input border green: entity present
- Input fill red: entity state ON

## Aggiornamenti 2026-02-11
- Modulo **Caldaia Gas Emergenza** con:
  - soglie dedicate Volano/Puffer + isteresi;
  - lista termostati “gas emergenza” gestiti dal modulo;
  - attuatori `220V caldaia gas` e `TA caldaia gas`.
- Logica gas:
  - GAS attivo solo se Volano/Puffer sotto soglia;
  - termostati gas sempre forzati in `heat` quando GAS attivo;
  - TA/220V ON solo se almeno un termostato è in `heating`;
  - **R4/R5 sempre OFF** in gas.
- Valvole in gas:
  - PT/Scala → R2 + R3
  - Laboratorio → R3 + R1 + pompa lab (R11)
  - Mansarda/1P da soli → nessuna valvola (caldaia spinge con pompa interna).
- **Pompa mandata piani (R12)** mai usata in gas.
- **Miscelatrice**:
  - in gas, se PT o Lab in heating → apertura totale (ALZA fisso);
  - fuori gas → logica normale.
- Modalità normale (impianto):
  - se calore disponibile (Puffer/Volano sopra soglia) → termostati in `heat`;
  - se calore assente → termostati in `off` (risparmio testine).
- Fix vari:
  - `/api/setpoints` include `gas_emergenza`;
  - persistenza flag “Storico” per Volano Alto/Basso;
  - log “SAVE …” in Ultime azioni per setpoints/entities/actuators/modules.

## Aggiornamenti 2026-02-14
- Fix static UI: mount StaticFiles su `/` (html=True) per servire index+assets e prevenire errori 500 su `/assets`.
- Rimosse route `FileResponse` dedicate a `/` e `/index.html` (static gestisce tutto).
- Versione add-on aggiornata a 1.1.3.
- Hotfix static: mount `/assets` separato + `FileResponse` per `/` e `/index.html`.
- Versione add-on aggiornata a 1.1.4.
- Hotfix static: fallback mount `/assets` su `/app/static` se `assets/` non esiste.
- Versione add-on aggiornata a 1.1.5.
- Hotfix static: serve `/assets/{path}` via `FileResponse` con fallback su `/app/static`.
- Versione add-on aggiornata a 1.1.6.
- Hotfix static: `FileResponse` con `media_type` corretto (mimetypes) per CSS/JS.
- Versione add-on aggiornata a 1.1.7.
- UI: reintrodotti stili principali in `App.vue` (tema scuro, card, grid, bottoni).
- Versione add-on aggiornata a 1.1.8.
- UI: layout centrato con max-width e header allineato stile e-ThermoMind.
- Versione add-on aggiornata a 1.1.9.
- UI: header con brand a sinistra, azioni centrate, tab a destra (come e-ThermoMind).
- Versione add-on aggiornata a 1.2.0.
- Admin: selezione dispositivo resa opzionale, import entità attivo con device name/ID.
- Versione add-on aggiornata a 1.2.1.
- Backend: aggiunta route `/api/auto_map/` per compatibilità (trailing slash).
- Versione add-on aggiornata a 1.2.2.
- Auto-map: fallback su stati HA con match per `device_name` quando device registry non è disponibile.
- Versione add-on aggiornata a 1.2.3.
