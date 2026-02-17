# Worklog — e-EnergyMind

## 2026-02-08
- Normalizzazione config e setpoint con guardie su input e defaults.
- Aggiunte API `/api/entities` GET/POST e validazioni minime payload.
- Reconnect WS Home Assistant con backoff e logging base.
- UI Admin estesa per mapping entità HA.
- Fix encoding in titoli/UI e stringhe logica.
- Aggiornato `PROJECT_LOG.md` con stato e roadmap.
- Aggiunto `build.yaml` per forzare base image `base-python` nel build add-on.
- Avvio server tramite `uvicorn` nel Dockerfile (binding su 0.0.0.0:8099).
- Abilitati `homeassistant_api` e `hassio_api` per ottenere `SUPERVISOR_TOKEN`.
- Lettura fallback del token da `/run/secrets/supervisor_token`.
- Avvio in modalità standalone se il token Supervisor non è disponibile.
- Serviti asset statici Vite da `/assets` per evitare pagina bianca.
- Endpoint debug `/api/assets` per verificare presenza file statici.
- Indicatore Online/Offline HA in UI (User/Admin) con endpoint `/api/status`.
- Supporto token HA da `options.json` con `ha_url`/`ha_token` (fallback se token Supervisor assente).
- Ricerca token Supervisor anche in `s6/container_environment` (compatibilità add-on).
- Mostrata versione add-on in User/Admin via `/api/status`.
- Versione UI ora letta da `config.yaml` (coerente con add-on).
- Polling UI automatico (refresh ogni 3s).
- Polling UI configurabile e timestamp ultimo aggiornamento in UI.
- Logica: isteresi ACS, hold VOLANO->ACS e stato last_* in decision.
- UI: configurazione attuatori + comandi manuali + stato attuatori.
- Logging con timestamp in output add-on.
- Etichette attuatori piu chiare (descrizione funzione).
- Etichetta pompa ACS specificata come PDC -> ACS.
- UI attuatori completa con canali R1-R30 (mapping manuale in Admin).
- Simbolo fisso per attuatori implementati (UI).

## 2026-02-13
- Ripulita UI User/Admin: rimosse tutte le sezioni termiche.
- UI energia: layout con KPI per utenza e mapping sensori read-only.
- Admin: selettore numero utenze (1-3) e runtime base.
- Backend semplificato: rimosse logiche termiche, solo mapping sensori e status.
- Logger: campionamento 10s su SQLite `/data/energymind.db`, retention 90 giorni.
- UI statiche: servite da `/app/static` con route `/`.
- Fix routing: API non più oscurate da statici; assets serviti su `/assets`.
- Auto-mapping: import entità da device HA via nome/ID (Admin).
- Fix auto-mapping: uso endpoint `device_registry/list` e `entity_registry/list`.
- Aggiunto endpoint `/api/devices` per elencare device HA con id e nome.
- Admin: dropdown dispositivi per auto-compilare name/id e import.
- Fix UI styling: route `/assets/{path}` serve i file statici.
- Pallino verde/rosso per gestito/non gestito.
- Fix salvataggio attuatori (salva solo entity_id).
- Indicatore popolato/non popolato per entita e attuatori in Admin.
- Comandi manuali con toggle singolo e stato (icona da HA attributes).
- Toggle colorato per stato e icone MDI reali.
- MDI font locale bundlato via npm (icone HA visibili anche senza CDN).
- Icone toggle colorate per stato e aggiornamento attuatori via polling.
- Selettore runtime mode (dry-run/live) con conferma.
- LIVE resistenze volano con off-delay (R22/R23/R24).
- Log azioni e indicatori runtime mode in UI.
- Icone HA anche per i sensori (Admin + User).
- Admin: etichette e-manager, layout a sezioni, filtro attuatori, export/import config.
- Admin: pulsanti in header + setpoint compatti.
- User: mostra runtime mode e stato resistenze volano (R22/R23/R24).
- Import config anche in header.
- User: nomi completi resistenze + icone colorate per stato.
- Dry-run: log simulato step/export in "Ultime azioni".
- Compatibilita load sensori (stringa -> oggetto UI).
- Blocca refresh mentre si editano i campi (no sparizione input).
- Polling sospeso con focus globale input/select/textarea.
- Polling sospeso in tab Admin (no overwrite mentre si compila).
- Indicatore presenza: pallino rosso fisso + bordo verde se entity presente.
- Rimosso bordo verde; pallino rosso unico a sinistra.
- Indicatori ripristinati: verde = in logica, rosso = non in logica, bordo verde se entity presente.
- Bordo verde input piu evidente (2px + glow).
- Pallino logica spostato accanto all'input entita.
- Pallino logica accanto anche ai sensori.
- Toggle moduli anche in Admin (7 moduli).
- Dry-run: log simulato completo per moduli (stati ON/OFF/DISABLED) + flag volano->puffer.
- Moduli UI: evidenziazione ON con fondo rosso trasparente.
- PROJECT_LOG aggiornato con snapshot 2026-02-09.
- Rimossi comandi manuali, toggle via pallino attuatori + bordo rosso quando ON; user senza pallino.
- Header: pulsanti config uniformati e rimossa duplicazione in sezione Configurazione.
- Guard: se un attuatore ON da HA con modulo attivo, auto-OFF dopo 2s (UI toggle escluso).
- UI User: "Ultime azioni" in ordine inverso (nuove in cima).
- Input attuatori: bordo verde per entita presente + riempimento rosso quando ON.
- Forzato riempimento rosso input ON con !important.
- WebSocket UI: aggiornamento live per User/Admin senza sovrascrivere input in editing.
- Resistenze: aggiunti sensori potenza/energia + switch generale in logica (ON con step).
- Input mapping: blocco overwrite da WS quando campi sono "dirty" finché non salvi.
- WS: applica logica live resistenze durante snapshot (general OFF quando step=0).
- User: aggiunto R0 generale resistenze nella card Resistenze volano.
- User: schema impianto animato con flussi live.
- Resistenze: generale segue step (ON se step>0, OFF se step=0).
- Runtime mode: cambio live/dry-run salvato automaticamente.

## 2026-02-14
- Fix static UI: mount unico su `/` (StaticFiles html=True) per servire `index.html` e `assets` senza 500 su `/assets`.
- Rimossi handler `FileResponse` per `/` e `/index.html` (delegati a StaticFiles).
- Versione add-on aggiornata a 1.1.3.
- Hotfix static: reintrodotto `FileResponse` per `/` + mount `/assets` separato.
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
## 2026-02-09
- UI: restyle completo e schema impianto più pulito e leggibile.
- Backend: attuazione live per Volano→ACS, Volano→Puffer e Puffer→ACS con sequenze valvola→pompa.
- Config: aggiunti timer `valve_to_pump_start_s` e `valve_to_pump_stop_s` con campi UI.
- UI: sequenze separate Volano→ACS e Volano→Puffer con nomi logici.
- Config: timer separati per Volano→ACS e Volano→Puffer (start/stop).
- User: grafico rapido temperature + export.
- Backend: elenco completo entit� salvato anche in /data/energymind_all_entities.json (persistente).
- UI Admin: elenco completo caricato da /api/entities_all anche se la config non lo riporta.
- Versione add-on aggiornata a 1.5.0.
- UI Admin: contatore entit� e lista scrollabile per mostrare tutte le entit�.
- Versione add-on aggiornata a 1.5.1.
- Admin: tutte le entit� ora nello stesso elenco con flag ON/OFF per ogni riga.
- Versione add-on aggiornata a 1.5.3.
- UI: aggiunte tab 'Automation setting' e 'Automazioni interface' con pagine placeholder.
- Versione add-on aggiornata a 1.8.1.
## 2026-02-15
- Automation setting: campi dedicati per vista istantanea (flow) per utenza.
- Automation setting: lista entita extra da datalog per utenza (persistente in config).
- Automation interface: vista istantanea con valori basati sui campi flow.
- Backend: history logging include extra entita da datalog.
- Versione add-on aggiornata a 1.8.2.
## 2026-02-15
- Aggiunta automazione locale pre-push: blocca il push se WORKLOG.md e PROJECT_LOG.md non sono aggiornati.
## 2026-02-15
- Fix hook pre-push: script ora compatibile /bin/sh (niente pwsh).
## 2026-02-15
- Automation setting: mostrato nome reale device accanto a ogni utenza.
## 2026-02-15
- Automazioni interface: refresh dedicato delle entita flow via endpoint batch /api/entity_states.
- Backend: aggiunto endpoint /api/entity_states per recupero stati multipli.
## 2026-02-15
- Versione add-on aggiornata a 1.8.3.
## 2026-02-15
- Automation setting/interface: aggiunti campi carica e scarica batteria oggi.
## 2026-02-15
- Datalogging extra spostato da Automation setting a pagina Admin.
## 2026-02-15
- Versione add-on aggiornata a 1.8.5.
## 2026-02-15
- Automation setting/interface: aggiunti campi tensione e frequenza.
- Versione add-on aggiornata a 1.8.6.
## 2026-02-15
- Datalogging extra: aggiunto flag ON/OFF per mostrare in User e storico al click.
- Admin/Automation setting: sezioni utenza collassabili.
## 2026-02-15
- UI: ovunque �Utenza X� ora mostra anche il nome reale (Utenza X � Nome).
## 2026-02-15
- Admin: rimosso collapse globale; collasso separato per utenza.
## 2026-02-15
- Versione add-on aggiornata a 1.8.9.
## 2026-02-15
- Automation setting/interface: aggiunta voce Consumo casa oggi.
## 2026-02-15
- User: entita extra manuali mostrano il friendly_name (se presente) invece dell'entity_id.
## 2026-02-15
- Versione add-on aggiornata a 1.9.0.
## 2026-02-15
- Aggiunta pagina View-Card con flow grafico animato e responsive.
## 2026-02-15
- Fix build: corretta chain v-if/v-else-if per tab view_card.
## 2026-02-15
- Versione add-on aggiornata a 1.9.2.
## 2026-02-15
- View-Card: layout e icone aggiornati per replica visiva.
- Flow entities: aggiunti Solar SAS, Pannelli portoni, FV totale, Consumo totale, SOC target.
- Automation setting: nuovi campi per View-Card.

## 2026-02-15
- View-Card: linee ridisegnate con percorsi ortogonali.

## 2026-02-15
- View-Card: linee riallineate per layout identico (tratti e angoli).

## 2026-02-15
- View-Card: layout e linee ricostruiti con HTML+SVG e dash animation (stile reference).

## 2026-02-15
- Admin: aggiunta verifica logging DB per entit� mappate (mancanti/presenti).

## 2026-02-15
- Report BMS: SOC/Temp ora derivati anche da raw quando value � null.

## 2026-02-15
- Report BMS: rilevazione automatica inversione segno rete + diagnostica campioni per utenza.

## 2026-02-15
- Insights: rilevazione carica parziale anche con segno rete invertito (export/import).

## 2026-02-15
- Runtime: aggiunta opzione segno rete (export positivo) usata in insights e report.

## 2026-02-15
- User: tabelle Intelligenza utenze spostate sotto Intelligenza globale (comparazione affiancata).

## 2026-02-15
- Insights: dettagli numerici su surplus/carica e potenze in cause/suggerimenti.

## 2026-02-15
- Report: aggiunti dettagli surplus/carica per eventi e log INSIGHT in azioni.

## 2026-02-15
- Insights: regola carica parziale basata solo su PV>Load ed export>300 per >=10s (senza soglie SOC/percentuali).

## 2026-02-15
- Learning: regole apprese da storico (export/surplus/durata) e mostrate in User.

## 2026-02-15
- Fix: corretto indentazione report (crash).
- Learning: finestra 48h, update ogni 2h.

## 2026-02-15
- Report: aggiunti nomi reali utenze in header e sezioni.

## 2026-02-15
- Report: rimossa limitazione 20 eventi (stampa tutti).

## 2026-02-15
- Report: file rinominati con prefisso report_e-energymind_.

## 2026-02-15
- Report: finestra nearest per SOC/Temp/Mode/Export aumentata a 300s.

## 2026-02-15
- Fix: indentazione report (soc/temp) corretta.

## 2026-02-15
- Admin: campi mappatura sempre visibili (incluso Batteria SOC%).

## 2026-02-15
- Report: aggiunta relazione tecnica giornaliera con statistiche per utenza.


## 2026-02-15
- Previsioni Solar e-EnergyMind: aggiunti forecast automatici e parametri in Admin + tabella in User.

## 2026-02-15
- Previsioni: aggiunto profilo orario PV/Load/Surplus con scaling su forecast.

## 2026-02-15
- Forecast: supporto sensori PV orari (today/tomorrow) con calibrazione e profilo orario da attributi.


## 2026-02-15
- Admin: aggiunto filtro per entit� (ricerca) per trovare rapidamente Carico casa e altre voci.

## 2026-02-15
- UI: aggiunto tasto Aggiorna nella barra superiore.

## 2026-02-15
- Forecast: profilo orario load calcolato con media pesata nel tempo (non media semplice campioni).
## 2026-02-16
- Forecast: profilo load orario non viene pi� scalato automaticamente (solo se l�utente imposta un consumo giornaliero).
- Versione add-on aggiornata a 2.1.15.
## 2026-02-16
- Profilo orario: surplus negativo ora clampato a 0 (solo output).
- Versione add-on aggiornata a 2.1.16.
## 2026-02-16
- Forecast: ignorato load_daily quando punta a today_load_kwh (parziale) per evitare profilo load sottostimato.
- Versione add-on aggiornata a 2.1.17.
## 2026-02-16
- UI forecast: colonne allargate e header con wrapping per evitare sovrapposizioni.
- Versione add-on aggiornata a 2.1.18.
## 2026-02-16
- UI forecast: layout a card per utenza per evitare sovrapposizioni.
- Versione add-on aggiornata a 2.1.19.
## 2026-02-16
- Forecast: simulazione batteria oraria (SOC, export/import, fine carica) + nuovi campi UI.
- Versione add-on aggiornata a 2.1.20.
## 2026-02-16
- Forecast: aggiunta potenza extra disponibile (instant) per utenza + colonne orarie.
- Versione add-on aggiornata a 2.1.21.
## 2026-02-16
- Admin: preview valore accanto alle entit� (live state) + refresh dedicato.
- Versione add-on aggiornata a 2.1.22.
## 2026-02-16
- Report: rimossi grafici SVG dai report giornalieri.
- Versione add-on aggiornata a 2.1.23.
## 2026-02-16
- UI forecast: profili orari collassabili per utenza (oggi/domani).
- Versione add-on aggiornata a 2.1.24.
## 2026-02-16
- UI: spiegazione testuale delle regole apprese (legenda).
- Versione add-on aggiornata a 2.1.25.
## 2026-02-16
- UI: Regole apprese con campioni usati per ogni utenza.
- Versione add-on aggiornata a 2.1.26.
## 2026-02-16
- UI forecast: collassabili anche le sezioni profilo orario (oggi/domani).
- Versione add-on aggiornata a 2.1.27.
## 2026-02-16
- UI: campioni usati per regole apprese con etichetta per utenza.
- Versione add-on aggiornata a 2.1.28.
## 2026-02-16
- Automation: extra ora disponibile mostrato in settings e interface.
- Versione add-on aggiornata a 2.1.29.
## 2026-02-16
- Automation: aggiunta stima extra kWh oggi/domani in settings e interface.
- Versione add-on aggiornata a 2.1.30.

## 2026-02-16
- Forecast: aggiunta target SOC dinamico per utenza e extra "safe" basato su target (ora/oggi).
- UI: extra ora/oggi usa safe quando disponibile; target SOC mostrato nella card previsioni.
- Versione add-on aggiornata a 2.1.31.
## 2026-02-16
- UI: visualizzazione BMS max stimato in Automation setting, Automazioni interface e sezione parametri forecast.
- Versione add-on aggiornata a 2.1.32.
## 2026-02-16
- UI: etichette chiare (stima/sim) nei valori della card previsioni per evitare confusione.
- Versione add-on aggiornata a 2.1.33.
## 2026-02-16
- UI: mostrati BMS max reali (storico) separati da valori usati/configurati.
- Versione add-on aggiornata a 2.1.34.
## 2026-02-16
- Forecast: calcolo BMS max reale sempre da storico, anche se configurato manualmente.
- Versione add-on aggiornata a 2.1.35.
## 2026-02-16
- Forecast: log trasparente di pv_adjust con confronto forecast vs reale (per utenza, una volta al giorno).
- Versione add-on aggiornata a 2.1.36.
## 2026-02-16
- Forecast: aggiunto indicatore di allineamento reale vs forecast (percentuale e kWh).
- Versione add-on aggiornata a 2.1.37.
## 2026-02-16
- Forecast: aggiunto allineamento PV intraday (reale vs forecast parziale) con percentuale.
- Versione add-on aggiornata a 2.1.38.
## 2026-02-17
- Forecast: fallback allineamento reale vs forecast usando valori odierni quando lo storico manca (evita n/d).
- Versione add-on aggiornata a 2.1.39.
## 2026-02-17
- Admin: mostrato nome addon + nome originale HA per ogni entità mappata (debug rinomina).
- Versione add-on aggiornata a 2.1.40.
## 2026-02-17
- Forecast: allineamento reale usa produzione reale (kWh) anche se il sensore “today” è in W.
- Versione add-on aggiornata a 2.1.41.
## 2026-02-17
- UI: aggiunto pulsante legenda nelle previsioni con popup descrittivo dei campi.
- Versione add-on aggiornata a 2.1.42.
## 2026-02-17
- View-Card: aggiunta configurazione numero card, titolo e path in Automation setting.
- View-Card: rendering delle card tramite iframe su view Lovelace configurate.
- Versione add-on aggiornata a 2.1.43.
## 2026-02-17
- Ingress: assets caricati con path relativo (Vite base './') per evitare 404 su /assets.
- Versione add-on aggiornata a 2.1.44.
## 2026-02-17
- Ingress: chiamate API frontend ora relative al path corrente (evita 401 su /api in HA).
- Versione add-on aggiornata a 2.1.45.
## 2026-02-17
- Fix: syntax error nelle chiamate API (Ingress) in App.vue.
- Versione add-on aggiornata a 2.1.46.
## 2026-02-17
- View-Card: aggiunto HA base URL per iframe quando si apre da porta 8100.
- Versione add-on aggiornata a 2.1.47.
## 2026-02-17
- View-Card: path relativo ora risolto su origin corrente (Ingress) se manca HA base URL.
- Versione add-on aggiornata a 2.1.48.
## 2026-02-17
- View-Card: iframe esteso a 100vh e wrapper senza overflow per ridurre lo scroll esterno.
- Versione add-on aggiornata a 2.1.49.
## 2026-02-17
- View-Card: aggiunto reverse proxy `/ha` per aprire Lovelace in iframe da porta 8100 (fix blocco X-Frame/CSP).
- View-Card: default `ha_base_url` a `/ha` e fallback automatico su porta 8100.
- Versione add-on aggiornata a 2.1.50.
## 2026-02-17
- Proxy `/ha`: fix streaming response (evita ERR_INCOMPLETE_CHUNKED_ENCODING).
- Versione add-on aggiornata a 2.1.51.
## 2026-02-17
- Proxy `/ha`: disabilitata compressione upstream per evitare ERR_CONTENT_DECODING_FAILED.
- Versione add-on aggiornata a 2.1.52.
## 2026-02-17
- Proxy `/ha`: rewrite HTML per prefissare risorse con `/ha` (fix 404 static/frontend_latest).
- Versione add-on aggiornata a 2.1.53.
## 2026-02-17
- Proxy `/ha`: proxy diretto anche per `/static`, `/frontend_latest`, `/hacsfiles`, `/dwains_dashboard`, `/local`, `/media`.
- Versione add-on aggiornata a 2.1.54.
## 2026-02-17
- Proxy `/ha`: base URL ora forza `http://homeassistant:8123` se manca `ha_url` (serve per static/frontend).
- Versione add-on aggiornata a 2.1.55.
## 2026-02-17
- Proxy `/ha`: aggiunti passthrough per `/auth` e `/api` (login HA).
- Versione add-on aggiornata a 2.1.56.
## 2026-02-17
- Proxy `/ha`: aggiunto WebSocket passthrough `/api/websocket` (fix "Unable to connect").
- Versione add-on aggiornata a 2.1.57.
## 2026-02-17
- Proxy `/ha`: spostati passthrough HA su `/ha/auth` e `/ha/api` per non rompere API addon.
- Proxy `/ha`: WebSocket su `/ha/api/websocket`.
- Versione add-on aggiornata a 2.1.58.
## 2026-02-17
- Proxy `/ha`: aggiunto WebSocket passthrough anche su `/api/websocket` (solo WS) per compatibilit� frontend HA.
- Versione add-on aggiornata a 2.1.59.
## 2026-02-17
- Proxy `/ha`: aggiunto passthrough anche per `/auth/*` root (fix auth token 404).
- Versione add-on aggiornata a 2.1.60.
## 2026-02-17
- Proxy `/ha`: aggiunto passthrough per `/lovelace/*` root (fix redirect a /lovelace/0).
- Versione add-on aggiornata a 2.1.61.
## 2026-02-17
- Proxy `/ha`: iniezione token `ha_token` in header Authorization per richieste e WebSocket (fix Unauthorized).
- Versione add-on aggiornata a 2.1.62.
## 2026-02-17
- Proxy `/ha`: middleware che proxy `/api/*` verso HA solo se referer da `/ha` o `/lovelace`.
- Versione add-on aggiornata a 2.1.63.
## 2026-02-17
- Proxy `/ha`: base HTML ora usa `/` (no prefix) per routing HA; middleware `/api` esteso a dashboard.
- Versione add-on aggiornata a 2.1.64.
## 2026-02-17
- Proxy `/ha`: ripristinato base `/ha/` e rewrite path per routing HA corretto.
- Versione add-on aggiornata a 2.1.65.
