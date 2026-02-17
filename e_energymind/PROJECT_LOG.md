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
- Admin: rimosso selettore dispositivo (restano nome/ID manuali).
- Versione add-on aggiornata a 1.2.4.
- Auto-map: ampliati pattern per `battery_soc` e `today_import_kwh`.
- Versione add-on aggiornata a 1.2.5.
- Admin: elenco entità parte vuoto e mostra solo entità importate (toggle “Mostra tutte”).
- Versione add-on aggiornata a 1.2.6.
- Admin: pulsante “Reset entità” (API `/api/entities/reset`).
- Versione add-on aggiornata a 1.2.7.
- UI: mostrato nome dispositivo per ogni utenza in User/Admin.
- Versione add-on aggiornata a 1.2.8.
- User: mostra solo KPI mappati + lista “Entità mappate” per utenza.
- Versione add-on aggiornata a 1.2.9.
- Auto-map: risposta include `matched` e `skipped_existing`.
- Admin: toggle “Sovrascrivi mappature esistenti” + aggiornamento nome dispositivo su import.
- Versione add-on aggiornata a 1.3.0.
- Auto-map: priorità a `pv_power_total` e pattern aggiuntivi per FV totale.
- Versione add-on aggiornata a 1.3.1.
- UI User: etichette KPI/entità prese da HA `friendly_name` (fallback ai label interni).
- Versione add-on aggiornata a 1.3.2.
- UI Admin: etichette sensori prese da HA `friendly_name` (fallback ai label interni).
- Versione add-on aggiornata a 1.3.3.
- Admin: flag ON/OFF accanto alle entità + input verde quando stato ON.
- Versione add-on aggiornata a 1.3.4.
- Admin: flag ON/OFF ora indica entità mappata e presente in HA (non stato on/off).
- Versione add-on aggiornata a 1.3.5.
- Admin: flag manuale con checkbox (on=colora input, off=spento).
- Versione add-on aggiornata a 1.3.6.
- Admin: flag manuali persistenti in config (`runtime.ui_flags`).
- Versione add-on aggiornata a 1.3.7.
- UI: ripristino flags da localStorage se config vuoto + salvataggio locale continuo.
- Versione add-on aggiornata a 1.3.8.
- User: evidenziazione anche in “Entità mappate” + KPI PV Totale.
- Versione add-on aggiornata a 1.3.9.
- Backend: endpoint `/api/device_entities?device_id=...` per elenco entità dispositivo.
- Versione add-on aggiornata a 1.4.0.
- Backend: `/api/device_entities` ora accetta `device_name` e include device list + sample device_id.
- Versione add-on aggiornata a 1.4.1.
- Backend: endpoint `/api/ha_debug` per verificare accesso ai registry HA.
- Versione add-on aggiornata a 1.4.2.
- Backend: priorità al token HA da options (ha_token) rispetto al supervisor token.
- Versione add-on aggiornata a 1.4.3.
- Debug: `/api/ha_debug` ora mostra stato `options.json` e presenza token.
- Versione add-on aggiornata a 1.4.4.
- Backend: accesso ai registry HA via WebSocket (non REST).
- Versione add-on aggiornata a 1.4.5.
- Admin: salvato elenco completo entità dispositivo e mostrato in UI.
- Versione add-on aggiornata a 1.4.6.
- Backend: `/api/device_entities` ora restituisce solo entità del device (debug opzionale).
- Versione add-on aggiornata a 1.4.7.
- Auto-map: aggiorna config e mostra totale entità importate.
- Versione add-on aggiornata a 1.4.8.
- Admin: pulsante “Sincronizza elenco completo” (API `/api/all_entities_sync`).
- Versione add-on aggiornata a 1.4.9.
- Backend: lista completa entità salvata anche in file dedicato `/data/energymind_all_entities.json` per evitare overwrite.
- UI Admin: lettura elenco completo via `/api/entities_all` (non dipende più dalla config).
- Versione add-on aggiornata a 1.5.0.
- UI Admin: contatore entit� e lista scrollabile per mostrare tutte le entit�.
- Versione add-on aggiornata a 1.5.1.
- Admin: tutte le entit� ora nello stesso elenco con flag ON/OFF per ogni riga.
- Versione add-on aggiornata a 1.5.3.
- User: rimosso elenco mappate, ora mostra solo entit� con flag ON in Admin.
- Versione add-on aggiornata a 1.5.4.
- Admin: elenco completo nello stesso stile (label + flag + input con dot).
- User: per entit� flaggate mostra valore/state (non entity_id).
- Versione add-on aggiornata a 1.5.5.
- Admin: flag Storico per ogni entit� (persistente) e DB size in header.
- Backend: storico su DB ogni 30s per entit� con flag Storico, endpoint /api/history + /api/db_info.
- User: click su entit� con flag Storico apre popup grafico 24h.
- Versione add-on aggiornata a 1.6.0.
- DB: storico su tabella unica history, scrittura solo su cambio valore (niente duplicati).
- Versione add-on aggiornata a 1.6.2.
- User: nel popup storico aggiunti esempi XY (3 punti: inizio/mezzo/fine).
- Versione add-on aggiornata a 1.6.3.
- Admin: rimosso header �Entit� dispositivo (tutte)� e stile unificato con l�elenco sopra.
- Versione add-on aggiornata a 1.6.4.
- Admin: rimosso flag Storico (grafico ora su click per tutte le entit� selezionate).
- Versione add-on aggiornata a 1.6.5.
- Grafico storico: aggiunta scala assi X/Y con tick e griglia.
- Versione add-on aggiornata a 1.6.6.
- DB: backfill entity_id per storico usando la colonna key (dati di stamattina visibili).
- Versione add-on aggiornata a 1.6.7.
- Storico: fallback query usa anche key legacy se entity_id mancante (dati di stamattina visibili).
- Versione add-on aggiornata a 1.6.8.
- Report giornaliero automatico (23:59) per entrambe le utenze con MD+JSON in /data/reports.
- Tag cause automatici per carica parziale.
- Versione add-on aggiornata a 1.7.0.
- Report: copia automatica in /share/reports oltre che /data/reports.
- Versione add-on aggiornata a 1.7.1.
- Fix crash: indentation in _num_or_none. Version 1.7.2.
- Report: salvataggio solo in /share/reports (niente doppioni).
- Versione add-on aggiornata a 1.7.3.
- Report: endpoint manuale /api/reports/generate per generazione immediata.
- Versione add-on aggiornata a 1.7.4.
- Admin: aggiunto pulsante 'Genera report ora'.
- Versione add-on aggiornata a 1.7.5.
- Admin: pulsante report spostato in cima alla sezione Configurazione.
- Versione add-on aggiornata a 1.7.6.
- Fix polling: resume automatico in User quando si cambia tab (evita refresh manuale).
- Versione add-on aggiornata a 1.7.7.
- Report: map share:rw in add-on config + log generation action. Version 1.7.8.
- Report: soglie pi� permissive per carica parziale + timezone Europe/Rome.
- Versione add-on aggiornata a 1.7.9.
- User: aggiunta sezione Intelligenza globale e per-utenza con cause, suggerimenti e previsione +60s.
- Backend: endpoint /api/insights con logica realtime.
- Versione add-on aggiornata a 1.8.0.
- UI: aggiunte tab 'Automation setting' e 'Automazioni interface' con pagine placeholder.
- Versione add-on aggiornata a 1.8.1.
## 2026-02-15
- Aggiunti campi dedicati per vista istantanea automazioni (flow) e gestione entita extra datalog in Automation setting.
- Vista Automazioni interface aggiornata per mostrare i valori configurati.
- Logging storico include entita extra definite dall'utente.
- Versione 1.8.2.
## 2026-02-15
- Aggiunto hook pre-push per obbligare aggiornamento WORKLOG.md e PROJECT_LOG.md prima del push.
## 2026-02-15
- Fix hook pre-push: usa /bin/sh per compatibilita durante il push.
## 2026-02-15
- UI Automation setting: etichetta utenza include nome device.
## 2026-02-15
- Fix refresh Automazioni interface (polling stati flow via /api/entity_states).
## 2026-02-15
- Bump versione 1.8.3 per aggiornamento add-on.
## 2026-02-15
- UI Automation setting/interface: carica/scarica batteria oggi.
## 2026-02-15
- UI: Datalogging extra ora in Admin (rimosso da Automation setting).
## 2026-02-15
- Bump versione 1.8.5 per aggiornamento add-on.
## 2026-02-15
- UI: tensione e frequenza nella vista automazioni.
- Bump versione 1.8.6.
## 2026-02-15
- UI: flag per entita extra + sezioni utenza collassabili (Admin/Automation setting).
## 2026-02-15
- UI: titolo utenza include nome reale in tutte le pagine.
## 2026-02-15
- Admin: collapse per utenza separato (niente collapse globale).
## 2026-02-15
- Bump versione 1.8.9.
## 2026-02-15
- UI: Consumo casa oggi in setting e interface.
## 2026-02-15
- UI User: label entita extra usa friendly_name.
## 2026-02-15
- Bump versione 1.9.0.
## 2026-02-15
- UI: nuova pagina View-Card (flow animato).
## 2026-02-15
- Fix: v-else/v-else-if chain in App.vue (tab view_card).
## 2026-02-15
- Bump versione 1.9.2.
## 2026-02-15\n- View-Card: aggiornata grafica con icone, colori e layout stile riferimento.\n- Flow entities estese per Solar SAS / Pannelli portoni / FV totale / Consumo totale / SOC target.\n
## 2026-02-15\n- View-Card: linee rese ortogonali per layout pulito.\n
## 2026-02-15\n- View-Card: tracciati linee allineati allo schema di riferimento.\n
## 2026-02-15\n- View-Card: sostituito SVG con layout HTML+SVG (dash flow) in stile reference.\n
## 2026-02-15\n- Admin: verifica logging DB per entit� mappate.\n
## 2026-02-15\n- Report BMS: SOC/Temp letti da raw se value null.\n
## 2026-02-15\n- Report BMS: auto-detect segno rete e conteggio campioni per utenza.\n
## 2026-02-15\n- Insights: carica parziale rilevata anche se segno rete invertito.\n
## 2026-02-15\n- Config: segno rete configurabile (export positivo/import negativo).\n
## 2026-02-15\n- User: comparazione Intelligenza utenze affiancata sotto Intelligenza globale.\n
## 2026-02-15\n- Insights: aggiunti dettagli numerici per carica parziale.\n
## 2026-02-15\n- Report/log: dettagli numerici carica parziale inclusi.\n
## 2026-02-15\n- Insights: soglie basate su export>300W per >=10s con PV>Load.\n
## 2026-02-15\n- Learning: regole apprese dallo storico esposte in UI.\n
## 2026-02-15\n- Fix crash: indentazione report.\n- Learning: finestra 48h, update ogni 2h.\n
## 2026-02-15\n- Report: nomi reali utenze inclusi.\n
## 2026-02-15\n- Report: stampa tutti gli eventi senza limite.\n
## 2026-02-15\n- Report: prefisso e-energymind nei file.\n
## 2026-02-15\n- Report: nearest window 300s per SOC/Temp/Mode/Export.\n
## 2026-02-15\n- Fix: indentazione report (soc/temp) corretta.\n
## 2026-02-15\n- Admin: campi mappatura sempre visibili (SOC incluso).\n
## 2026-02-15\n- Report: relazione tecnica giornaliera dettagliata per utenza.\n

## 2026-02-15
- Previsioni Solar e-EnergyMind: endpoint /api/forecast, calcoli auto da storico e tabella User + parametri Admin.


## 2026-02-15
- Forecast: profilo orario (PV/Load/Surplus) derivato da storico e scalato su previsioni.


## 2026-02-15
- Forecast: lettura sensori orari PV (attributi watts) per profilo orario e calibrazione.


## 2026-02-15
- Admin: filtro ricerca per entit� nelle utenze (mappate e complete).


## 2026-02-15
- UI: tasto Aggiorna in alto nella top bar.


## 2026-02-15
- Forecast: media oraria load corretta con integrazione tempo (time-weighted).
## Aggiornamenti 2026-02-16
- Forecast: profilo load orario non viene pi� scalato automaticamente (solo se l�utente imposta un consumo giornaliero).
- Versione add-on aggiornata a 2.1.15.
## Aggiornamenti 2026-02-16
- Profilo orario: surplus negativo ora clampato a 0 (solo output).
- Versione add-on aggiornata a 2.1.16.
## Aggiornamenti 2026-02-16
- Forecast: ignorato load_daily quando punta a today_load_kwh (parziale) per evitare profilo load sottostimato.
- Versione add-on aggiornata a 2.1.17.
## Aggiornamenti 2026-02-16
- UI forecast: colonne allargate e header con wrapping per evitare sovrapposizioni.
- Versione add-on aggiornata a 2.1.18.
## Aggiornamenti 2026-02-16
- UI forecast: layout a card per utenza per evitare sovrapposizioni.
- Versione add-on aggiornata a 2.1.19.
## Aggiornamenti 2026-02-16
- Forecast: simulazione batteria oraria (SOC, export/import, fine carica) + nuovi campi UI.
- Versione add-on aggiornata a 2.1.20.
## Aggiornamenti 2026-02-16
- Forecast: aggiunta potenza extra disponibile (instant) per utenza + colonne orarie.
- Versione add-on aggiornata a 2.1.21.
## Aggiornamenti 2026-02-16
- Report: rimossi grafici SVG dai report giornalieri.
- Versione add-on aggiornata a 2.1.23.
## Aggiornamenti 2026-02-16
- UI forecast: profili orari collassabili per utenza (oggi/domani).
- Versione add-on aggiornata a 2.1.24.
## Aggiornamenti 2026-02-16
- UI: spiegazione testuale delle regole apprese (legenda).
- Versione add-on aggiornata a 2.1.25.
## Aggiornamenti 2026-02-16
- UI: Regole apprese con campioni usati per ogni utenza.
- Versione add-on aggiornata a 2.1.26.
## Aggiornamenti 2026-02-16
- UI: campioni usati per regole apprese con etichetta per utenza.
- Versione add-on aggiornata a 2.1.28.
## Aggiornamenti 2026-02-16
- Automation: extra ora disponibile mostrato in settings e interface.
- Versione add-on aggiornata a 2.1.29.
## Aggiornamenti 2026-02-16
- Automation: aggiunta stima extra kWh oggi/domani in settings e interface.
- Versione add-on aggiornata a 2.1.30.

## Aggiornamenti 2026-02-16
- Forecast: target SOC dinamico per utenza e extra "safe" per ora/oggi basato su target.
- UI: extra ora/oggi usa safe quando disponibile; target SOC mostrato nella card previsioni.
- Versione add-on aggiornata a 2.1.31.
## Aggiornamenti 2026-02-16
- UI: BMS max stimato mostrato in Automation setting, Automazioni interface e parametri forecast.
- Versione add-on aggiornata a 2.1.32.
## Aggiornamenti 2026-02-16
- UI: etichette chiare (stima/sim) nella card previsioni.
- Versione add-on aggiornata a 2.1.33.
## Aggiornamenti 2026-02-16
- UI: BMS max reale separato da usato/configurato.
- Versione add-on aggiornata a 2.1.34.
## Aggiornamenti 2026-02-16
- Forecast: BMS max reale calcolato sempre da storico, anche con valori configurati.
- Versione add-on aggiornata a 2.1.35.
## Aggiornamenti 2026-02-16
- Forecast: log pv_adjust (forecast vs reale) per utenza, una volta al giorno.
- Versione add-on aggiornata a 2.1.36.
## Aggiornamenti 2026-02-16
- Forecast: indicatore allineamento reale vs forecast (percentuale e kWh) in UI.
- Versione add-on aggiornata a 2.1.37.
## Aggiornamenti 2026-02-16
- Forecast: allineamento PV intraday (reale vs forecast parziale) in UI.
- Versione add-on aggiornata a 2.1.38.
## Aggiornamenti 2026-02-17
- Forecast: fallback allineamento reale vs forecast usando valori odierni quando lo storico manca.
- Versione add-on aggiornata a 2.1.39.
## Aggiornamenti 2026-02-17
- Admin: mostrato nome addon + nome originale HA per ogni entità mappata (debug rinomina).
- Versione add-on aggiornata a 2.1.40.
## Aggiornamenti 2026-02-17
- Forecast: allineamento reale usa produzione reale (kWh) anche se il sensore “today” è in W.
- Versione add-on aggiornata a 2.1.41.
## Aggiornamenti 2026-02-17
- UI: aggiunto pulsante legenda nelle previsioni con popup descrittivo dei campi.
- Versione add-on aggiornata a 2.1.42.
## Aggiornamenti 2026-02-17
- View-Card: configurazione numero card, titolo e path in Automation setting.
- View-Card: rendering card tramite iframe su view Lovelace configurate.
- Versione add-on aggiornata a 2.1.43.
## Aggiornamenti 2026-02-17
- Ingress: assets con path relativo (Vite base './') per evitare 404 su /assets.
- Versione add-on aggiornata a 2.1.44.
## Aggiornamenti 2026-02-17
- Ingress: API frontend relative al path corrente (evita 401 su /api in HA).
- Versione add-on aggiornata a 2.1.45.
## Aggiornamenti 2026-02-17
- Fix: errore sintassi chiamate API (Ingress) in App.vue.
- Versione add-on aggiornata a 2.1.46.
## Aggiornamenti 2026-02-17
- View-Card: HA base URL per iframe quando si usa la porta 8100.
- Versione add-on aggiornata a 2.1.47.
## Aggiornamenti 2026-02-17
- View-Card: path relativo risolto su origin corrente (Ingress) se manca HA base URL.
- Versione add-on aggiornata a 2.1.48.
## Aggiornamenti 2026-02-17
- View-Card: iframe 100vh e wrapper senza overflow per ridurre lo scroll esterno.
- Versione add-on aggiornata a 2.1.49.
## Aggiornamenti 2026-02-17
- View-Card: aggiunto reverse proxy `/ha` per aprire Lovelace in iframe da porta 8100 (fix blocco X-Frame/CSP).
- View-Card: default `ha_base_url` a `/ha` e fallback automatico su porta 8100.
- Versione add-on aggiornata a 2.1.50.
## Aggiornamenti 2026-02-17
- Proxy `/ha`: fix streaming response (evita ERR_INCOMPLETE_CHUNKED_ENCODING).
- Versione add-on aggiornata a 2.1.51.
## Aggiornamenti 2026-02-17
- Proxy `/ha`: disabilitata compressione upstream per evitare ERR_CONTENT_DECODING_FAILED.
- Versione add-on aggiornata a 2.1.52.
## Aggiornamenti 2026-02-17
- Proxy `/ha`: rewrite HTML per prefissare risorse con `/ha` (fix 404 static/frontend_latest).
- Versione add-on aggiornata a 2.1.53.
## Aggiornamenti 2026-02-17
- Proxy `/ha`: proxy diretto anche per `/static`, `/frontend_latest`, `/hacsfiles`, `/dwains_dashboard`, `/local`, `/media`.
- Versione add-on aggiornata a 2.1.54.
## Aggiornamenti 2026-02-17
- Proxy `/ha`: base URL ora forza `http://homeassistant:8123` se manca `ha_url` (serve per static/frontend).
- Versione add-on aggiornata a 2.1.55.
