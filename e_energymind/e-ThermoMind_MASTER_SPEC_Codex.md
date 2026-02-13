# e‑ThermoMind — Master Spec (per Codex) — v1.0
Ultimo aggiornamento: 2026-02-09 (Europe/Rome)

Questo documento definisce in modo **minuzioso** cosa deve fare l’add-on **e‑ThermoMind** per Home Assistant, fino ad arrivare ad una versione “finita” (MVP+ e poi estensioni).
È scritto per essere dato in pasto a un agente di coding (es. Codex) come guida operativa.

---

## 0) Obiettivi chiave (non negoziabili)

1. **Eliminare i blueprint**: tutta la logica deve vivere nell’add-on. In HA restano solo:
   - **sensori** (temperature, potenza FV, export/import, ecc.)
   - **attuatori** (switch/relay: pompe, valvole, resistenze, comandi PDC quando disponibili)
   - eventuali entità “di sistema” standard (es. `sun.sun`) se utili.

2. **Configurabilità totale** dall’interfaccia dell’add-on:
   - mapping entità (sensori/attuatori) per installazioni diverse
   - setpoint, soglie, isteresi, ritardi, priorità, policy (tutto modificabile)
   - abilitazione/disabilitazione moduli singoli (es. PDC in standby ora).

3. **UI Vue responsive**:
   - pagina **Admin** (config/debug/test)
   - pagina **User** (monitoraggio + in futuro schema animato).

4. **Sicurezza**:
   - termostati max (ACS_MAX, VOLANO_MAX, PUFFER_MAX, SOLARE_MAX ecc.) con isteresi
   - anti “attacca-stacca” (debounce, min on/off, off-delay, ecc.)
   - interlock su valvole/pompe (sequenze e tempi)
   - modalità “dry-run” e “live” selezionabili (live disabilitato di default).

5. **Replicabilità**:
   - niente entity_id hardcoded
   - configurazione esportabile/importabile
   - schema a moduli riutilizzabile su altri impianti simili.

---

## 1) Contesto impianto (model mentale)

### Componenti termici
- **Caldaia a legna** che scalda **Puffer grande ~1200 L**.
- **Solare termico (centralina Systa)**:
  - scalda **ACS (Sanicube)** quando mandata solare > temperatura ACS (+ delta)
  - può anche scaldare il **puffer** (per riscaldamento casa)
  - logiche notte/cutback/ritorni (R18/R19) da portare in addon.
- **ACS (Sanicube)**: accumulo sanitario scaldato da **solare**, **puffer**, **PDC** (via volano) e potenzialmente altre sorgenti.
- **Volano puffer (buffer tecnico per PDC)**:
  - le **PDC** scaldano il volano
  - nel volano ci sono **3 resistenze da 1000 W**
  - dal volano si può scaldare **casa** oppure **puffer** oppure **ACS** (tramite valvole/pompe dedicate)
- **2 PDC** separate (entrambe master). Al momento **non operative** → restano mappabili ma “standby” inizialmente.

### Fotovoltaico
- FV carica batterie e si usa il **surplus (export in rete)** per:
  - accendere resistenze volano a step (1/2/3 kW)
  - e/o (in futuro) attivare PDC
- Logica resistenze:
  - se export > **1100 W** → ON resistenza1
  - se export > **2200 W** → ON resistenza2
  - se export > **3300 W** → ON resistenza3
  - evitare on/off rapidi: **OFF delay 5 secondi**.

### Riscaldamento radiatori
- Curva climatica già esistente (oggi su input_text + blueprint)
- Miscelatrice: 2 relè **ALZA** / **ABBASSA**
- Sensori: **mandata miscelata** e anche **ritorno**
- Parametri regolazione da mantenere (isteresi, Kp, min/max impulso, pausa, stabilizzazione, impulso forzatura…)
- Nome modulo UI: **Heat Radiator**.

---

## 2) Filosofia di controllo (“policy”)

### 2.1 Solare “impulsivo” NON blocca il resto
Il solare su ACS può durare pochi minuti.
Quindi:
- solare attivo ≠ bloccare PDC/resistenze
- possiamo in parallelo caricare il volano (energia di riserva), con **VOLANO_MAX** di sicurezza.

### 2.2 ACS a regime → niente carica “per ACS”
Se **ACS ≥ ACS_SP + isteresi**:
- non accendere resistenze o PDC “per ACS”
- se c’è surplus FV, destinazione diventa **PUFFER** (accumulo), con limiti max.

### 2.3 Trasferimento solo se c’è salto termico
Per trasferire calore dal volano verso ACS/puffer:
- START solo se `T_VOLANO >= T_DEST + Δ_START`
- HOLD solo se `T_VOLANO >= T_DEST + Δ_HOLD`
(Δ configurabili separatamente per ACS e per PUFFER).

---

## 3) Moduli funzionali (scope)

### Modulo A — Core Orchestrator (state machine)
**Scopo:** decide cosa fare, quando, e perché. Espone uno snapshot unico.

Output logico minimo:
- `destinazione_surplus`: OFF | ACS | PUFFER
- `source_to_acs`: OFF | SOLARE | PUFFER | VOLANO | PDC | LEGNA
- `resistance_step`: 0..3
- flags: `need_transfer_volano_to_acs`, `need_transfer_volano_to_puffer`, `need_charge_volano`, ecc.

Modalità:
- **DRY_RUN** (default): calcola e mostra, non comanda.
- **LIVE**: comanda attuatori rispettando safety e interlock.

Decisione destinazione (MVP):
1) Se `ACS >= ACS_MAX` → DEST=OFF (stop/limitazioni)
2) Se `ACS non a regime` → DEST=ACS
3) Se `ACS a regime` e policy “accumulo puffer” true → DEST=PUFFER
4) altrimenti DEST=OFF

> Nota: “accumulo puffer” deve essere configurabile (target giorno/notte in futuro).

---

### Modulo B — ACS (Sanicube)
**Scopo:** gestire richiesta ACS e selezione sorgente verso ACS.

Input:
- `T_ACS`
- `ACS_SP`, `ACS_ON_DELTA`, `ACS_OFF_HYST`
- `ACS_MAX`, `ACS_MAX_HYST`
- `T_SOL`, `T_PUFFER`, `T_VOLANO` (se disponibili)

Regole minime:
- Richiesta ACS se `T_ACS <= ACS_SP - ACS_ON_DELTA`
- Stop se `T_ACS >= ACS_SP + ACS_OFF_HYST` oppure `T_ACS >= ACS_MAX`

Sorgenti verso ACS (ordine configurabile):
- Solare: `T_SOL >= T_ACS + Δ_SOLARE_ON`
- Puffer: `T_PUFFER >= T_ACS + Δ_PUFFER_ON`
- Volano: `T_VOL >= T_ACS + Δ_VOL_ACS_START` (e non oltre VOLANO_MAX)

Attuatori (mappabili):
- puffer→ACS: pompa
- volano→ACS: valvola + pompa con sequenza (valvola→delay→pompa; stop valvola→2s→pompa)

---

### Modulo C — PUFFER (1200L)
**Scopo:** accumulo energia quando ACS ok e c’è surplus.

Input:
- `T_PUFFER_TOP`
- setpoint puffer (inizialmente fisso, poi pianificabile)
- `PUFFER_MAX`, `PUFFER_MAX_HYST`

Regole MVP:
- se DEST=PUFFER → consentire carica volano e poi trasferire volano→puffer se Δ ok
- trasferimento volano→puffer solo con Δ start/hold

---

### Modulo D — VOLANO + RESISTENZE (3×1kW)
**Scopo:** usare export FV per caricare volano con resistenze.

Input:
- `T_VOLANO`
- `EXPORT_W` (immissione rete)
- `VOLANO_MAX`, `VOLANO_MAX_HYST`
- soglie export: [1100, 2200, 3300] (config)
- `off_delay_s = 5` (config)
- opzione `invert_export_sign` (alcuni contatori hanno segno invertito)

Regole:
- se DEST=ACS o DEST=PUFFER
- e `T_VOLANO < VOLANO_MAX`
- calcolare step 0..3
- spegnimento step con **ritardo 5s** (anti oscillazione)

Attuatori:
- `switch.resistenza1`, `switch.resistenza2`, `switch.resistenza3`

Anti-chatter:
- per ogni resistenza mantenere uno stato interno e un timer OFF ritardato

---

### Modulo E — SOLARE (Systa) — porting blueprint
**Scopo:** replicare e migliorare la logica solare esistente (NORMAL/PRECEDENZA/NOTTE, cutback, ritorni).

Requisiti MVP:
- PRECEDENZA quando condizioni e limiti ok
- NOTTE da `sun.sun` + offset e/o “notte diurna” con FV bassa persistente + collettore freddo
- CUTBACK se `T_ACS >= T_ACS_MAX` o `T_SOL >= T_SOL_MAX`
- Interlock hard tra valvole (deadtime)
- Gestione ritorni R18/R19:
  - in NOTTE: R18 ON, R19 OFF
  - in non-notte: seguire helper unico (interno addon)

Attuatori mappabili:
- R8, R9, R10, R18, R19

Importante:
- solare non blocca resistenze/PDC (policy §2.1)

---

### Modulo F — HEAT RADIATOR (miscelatrice)
**Scopo:** controllo miscelatrice e setpoint mandata.

Entità (mappabili):
- `sensor.mandata_miscelata`
- `sensor.ritorno_miscelato` (opzionale)
- `input_number.set_point_valvola_miscelatrice` (iniziale)
- `switch.miscelatrice_alza`
- `switch.miscelatrice_abbassa`

Regole MVP = blueprint:
- deadband ± isteresi
- impulso proporzionale: `dur = clamp(Kp * |SP − T|, min_imp, max_imp)`
- pausa dopo impulso
- antirimbalzo dopo cambio sensore grezzo (stabilizzazione)
- safety alta temperatura: stop
- forzatura: impulso ABBASSA unico su transizione ON

Parametri configurabili:
- isteresi, Kp, min/max impulso, pausa, stabilizzazione
- min_temp, max_temp
- forza_impulso_sec
- modalità abilita/disabilita

---

### Modulo G — PDC (2 unità) — standby
MVP:
- modulo presente ma DISABLED di default
- UI Admin per abilitare e mappare
Futuro:
- alternanza, lockout, consenso FV, integrazione carica volano

---

## 4) Configurazione & persistenza

- Persistenza in `/data` (addon storage) citeturn0search2
- File: `/data/thermomind_config.json`
- Import/Export JSON da Admin

Schema config (minimo):
- `entities`: mapping entity_id
- `modules_enabled`
- `setpoints`/`safety`/`timers`/`policy`
- `runtime`: {mode: "dry-run"|"live"}

---

## 5) Comunicazione con Home Assistant (come deve essere fatto)

- API Core via proxy interno `http://supervisor/core/api/`
- Token da env `SUPERVISOR_TOKEN`
- in `config.yaml` aggiungere `homeassistant_api: true` (v0.2) citeturn0search12
- Stati via WebSocket `/api/websocket` con subscribe `state_changed` citeturn0search1
- UI via Ingress citeturn0search0turn0search4

---

## 6) UI Vue (Admin/User)

### Admin (must)
- toggle DRY_RUN/LIVE con doppia conferma
- mapping entità per modulo + status (ok/unavailable/missing)
- pagina setpoint/safety/timers
- pagina resistenze (soglie, off-delay)
- pagina Heat Radiator (parametri)
- log/debug (ring buffer + export)
- import/export config

### User (must)
- dashboard stato: temperature, destinazione, step resistenze, solar mode, miscelatrice state
- reason strings leggibili

### Schema animato (nice-to-have)
- SVG impianto con flussi animati basati su `/api/snapshot`

---

## 7) Backend API add-on

Endpoint minimi:
- `GET /api/snapshot` (stato totale)
- `GET/POST /api/config`
- `GET /api/logs`
- `POST /api/mode`
- `POST /api/test/actuator` (admin only, allowlist, live)

Loop:
- tick 1–5s + event-driven
- rate limit comandi
- no comandi ripetuti se già nello stato desiderato

---

## 8) Interlock e sequenze (must)

Valvola→Pompa start:
1) valvola ON
2) delay start (config)
3) pompa ON

Stop:
1) valvola OFF
2) delay stop (config, tipico 2s)
3) pompa OFF

Solare interlock hard:
- spegni non-target
- wait off con timeout
- deadtime
- accendi target

---

## 9) Spiegabilità (stato + motivo)

Per ogni modulo mantenere:
- `state`: RUNNING/STOPPED/WAITING/CUTBACK/ERROR
- `reason`: stringa umana

---

## 10) Roadmap versione per versione

- v0.1: skeleton + dry-run (già)
- v0.2: mapping + LIVE resistenze (off-delay 5s, safety volano)
- v0.3: volano→ACS live
- v0.4: volano→puffer live
- v0.5: solar manager completo
- v0.6: heat radiator live
- v0.7+: PDC enable e strategie
- v1.0: tutto stabile + schema animato + import/export + test

---

## 11) Criteri “finito” (v1.0)
- blueprint disabilitabili senza regressioni
- resistenze stabili su export con off-delay
- trasferimenti con Δ start/hold e sequenze
- solare notte/cutback/ritorni con interlock
- miscelatrice con parametri e comportamento uguale o migliore
- UI user con schema animato e reason chiare
- config replicabile (export/import)

---

### Riferimenti tecnici
- Ingress add-on citeturn0search0turn0search4
- API Core via Supervisor + SUPERVISOR_TOKEN citeturn0search12
- WebSocket API citeturn0search1
- Storage `/data` citeturn0search2
