# e‑ThermoMind — CODEX HANDOFF “All‑in‑One” (logica blueprint → addon)
Data: 2026-02-09 (Europe/Rome)

Scopo: questo documento è pensato per **Codex**. Deve permettere di iniziare a implementare la logica dell’addon **senza** dover rileggere tutta la chat.
Qui trovi:
1) cosa fa l’impianto (modello)
2) quali blueprint esistono e **che logica contengono**
3) come unificarli in **moduli** dentro l’addon
4) quali entità (sensori/switch) servono e come mapparle
5) regole precise (start/stop, soglie, isteresi, sequenze, anti-chatter)
6) roadmap implementativa (v0.2 → v1.0)

> Importante: la logica deve vivere nell’addon. In Home Assistant restano solo: **sensori + switch** (I/O).  
> Tutti i setpoint, timer, stati, “reason” e policy vanno **dentro addon**.

---

## 1) Modello impianto (come funziona davvero)

### Blocchi principali
- **ACS (Sanicube)**: accumulo sanitario. Può essere scaldato da:
  1) **Solare termico** (centralina Systa)
  2) **Puffer grande** (1200 L, caricato da caldaia a legna e anche da solare)
  3) **Volano** (puffer tecnico delle PDC; dal volano posso mandare calore ad ACS)
  4) (futuro) **PDC** (2 unità, per ora non attive)
- **Puffer grande 1200 L**: accumulo termico per casa e anche sorgente per ACS.
- **Volano**: buffer tecnico PDC, contiene **3 resistenze da 1000W**. Dal volano posso:
  - scaldare **casa** (radiatori)
  - scaldare **puffer grande**
  - scaldare **ACS**
- **2 PDC** separate (entrambi master): per ora **standby** nell’addon.
- **Fotovoltaico**: la logica usa **immissione in rete (export W)** per decidere quante resistenze accendere.

### Principi di controllo (policy decisa in chat)
1) **Solare è “impulsivo”**: può caricare ACS 2–3 minuti e poi fermarsi. Quindi:
   - “solare attivo” NON deve bloccare l’uso di PDC/resistenze per caricare riserva (volano/puffer).
2) **ACS a regime**:
   - se ACS è già in temperatura → NON caricare “per ACS” con resistenze/PDC.
   - in quel caso, se c’è surplus FV, la priorità diventa **scaldare puffer** (accumulo per la notte).
3) **Trasferimenti volano→ACS e volano→puffer**:
   - il circuito deve stare **fermo** finché il volano non è abbastanza caldo rispetto al destinatario.
   - regola generale (configurabile):
     - START se `T_VOLANO >= T_DEST + Δ_START`
     - HOLD se `T_VOLANO >= T_DEST + Δ_HOLD`
4) **Resistenze su export**:
   - 1100W → 1 resistenza
   - 2200W → 2 resistenze
   - 3300W → 3 resistenze
   - **OFF delay 5 secondi** per evitare attacca/stacca.
5) Sicurezza:
   - termostati max: almeno **ACS_MAX** e **VOLANO_MAX** (puffer max opzionale) con isteresi.

---

## 2) Blueprint esistenti (da “fondere” dentro addon)

### BP1 — Curva climatica semplice (mandata radiatori)
- Input: temperatura esterna + curva JSON
- Output: scrive un valore su `input_number` (setpoint mandata)
- Nota: per ora l’utente usa `input_number.set_point_valvola_miscelatrice` come setpoint.  
  In futuro la curva e i parametri vanno dentro addon.

### BP2 — Puffer → ACS (precedenza, scambio corretto)
- Scopo: avvia pompa puffer→ACS solo se:
  - ACS sotto setpoint di almeno Δstart
  - e puffer più caldo di ACS di almeno Δ_scambio_start
- Stop se:
  - ACS raggiunge setpoint + ΔOFF
  - oppure il salto termico puffer>ACS scende sotto Δ_scambio_hold
  - oppure timeout
- Scrive stato/motivo (input_text) — in addon questi diventano variabili interne (non helper HA).

### BP3 — Modula setpoint puffer (climate) in base ad ACS + protezione bollitore
- Scopo: se ACS fredda → alza setpoint puffer (priorità sanitaria)
- Se ACS troppo calda (>= limite) → forza puffer al minimo (protezione)
- In addon: questa diventa una **policy** (“quanto tenere caldo il puffer”) parametrica.

### BP4 — Gestione Solare ACS (molto completo)
- Scopo: gestisce valvole solare in 3 modalità:
  - NORMAL
  - PRECEDENZA ACS
  - NOTTE
- Usa:
  - astronomico (sun.sun) + offset
  - “notte diurna” se FV sotto soglia per N minuti e collettore freddo
  - cutback ACS (ACS >= ACS_MAX) e cutback solare (T_SOL >= T_SOL_MAX)
  - interlock hard + deadtime valvole
  - gestione R18/R19 (ritorni) con regole dedicate
- In addon: portare questa logica **quasi 1:1** come modulo “SolarManager” ma senza usare helper HA per stato.

### BP5 — Impianto a piani (valvole + pompa)
- Gestisce valvole di zona e pompa centrale con richiesta calore e polling MQTT.
- In addon: può diventare “ZoneManager” separato.  
  Per la v1.0, l’utente vuole poter disabilitare blueprint e farlo fare all’addon.

### BP6 — Sorgente ACS selector (Solare/Puffer/PDC/GAS…)
- Automatico: SOLARE → PUFFER → OFF (se nessun salto utile)
- Manuale: segue input_select
- In addon: questa logica si fonde nel “ACS Orchestrator” e nel “Core Orchestrator” (non usare input_select HA come cervello).

### BP7 — Miscelatrice 2 relè (ALZA/ABBASSA) proporzionale a passi + forzatura
- Controllo a impulsi con Kp sec/°C, min/max impulso, pausa, antirimbalzo, safety max temp.
- In addon: modulo “HeatRadiatorMixer” che replica la stessa dinamica.

### Blueprint PDC helper ACS (quello iniziale) — Gestione PDC Helper ACS
- Logica: in inverno aiuta ACS se:
  - ACS sotto SP−ΔON
  - puffer non basta (sotto SP−margine)
  - min off rispettato
- Sequenze valvola→pompa (30s) e stop valvola→pompa (2s)
- In addon: parte del futuro “PDCManager”, ma **ora** PDC è standby.

---

## 3) Unificazione in addon: moduli e responsabilità

### 3.1 Core Orchestrator (decisione globale)
Produce sempre uno “snapshot” unico con:
- `dest`: OFF | ACS | PUFFER
- `dest_reason`
- `solar_mode`: NORMAL | PRECEDENZA | NOTTE | CUTBACK
- `solar_reason`
- `resistance_step`: 0..3 + reason
- `transfer_vol_to_acs`: RUN/STOP/WAIT (con reason)
- `transfer_vol_to_puf`: RUN/STOP/WAIT (con reason)
- `mixer_state`: ALZA/ABBASSA/HOLD/SAFETY (con reason)
- `errors/warnings`: entità non mappate, unavailable, safety limit

Decisione `dest` (MVP):
1) se `ACS >= ACS_MAX` → `dest=OFF` (non caricare per ACS; applicare cutback se serve)
2) else se `ACS < ACS_SP + ACS_OK_HYST` → `dest=ACS`
3) else → `dest=PUFFER` (accumulo giorno/notte, con puffer max)
4) se puffer non richiede (policy disattiva o max) → dest=OFF

### 3.2 ACS Manager (scelta sorgente verso ACS)
Regole di scelta sorgente verso ACS (ordine configurabile):
- Solare se `T_SOL >= T_ACS + Δ_SOLARE_ON` e non cutback
- Puffer se `T_PUF >= T_ACS + Δ_PUF_ON`
- Volano se `T_VOL >= T_ACS + Δ_VOL_ACS_START` e volano non oltre max
- altrimenti OFF (ACS resta in attesa)

> Nota: in parallelo, si può caricare volano con resistenze anche se solare è attivo (policy solare “impulsivo”).

### 3.3 Puffer Manager (accumulo)
- Se `dest=PUFFER`:
  - caricare volano (resistenze) se c’è export
  - trasferire volano→puffer solo se Δ ok
- Puffer→ACS resta disponibile (BP2) quando ACS non a regime e puffer ha salto utile (questa è un’altra “via” oltre al volano).

### 3.4 Volano + Resistenze (FV/export)
- Calcolo step desiderato in base a export.
- Applicare off-delay 5s per step down.
- Bloccare tutto se `T_VOL >= VOLANO_MAX` (cutback volano).
- Resistenze devono rispettare mappatura e availability degli switch.

### 3.5 Solar Manager (porting BP4)
- Implementare: normal/precedenza/notte/cutback + ritorni + interlock hard.
- Importante: SolarManager gestisce le sue valvole, ma non deve impedire ad altri moduli di operare (salvo safety).

### 3.6 Heat Radiator (miscelatrice)
- Replicare BP7:
  - se T>=max → safety stop
  - se forzatura ON → impulso ABBASSA unico su transizione
  - else se T < SP−H → impulso ALZA proporzionale
  - else se T > SP+H e T>min_temp → impulso ABBASSA proporzionale
  - else HOLD (tutto OFF)
- Antirimbalzo: se trigger da sensore grezzo e non passati `stabilizzazione_sec` → non agire.

### 3.7 PDC Manager (standby)
- Modulo presente ma `enabled=false` fino a quando l’utente attiva le PDC.

---

## 4) Entità HA (sensori/switch) da mappare nell’Admin

### 4.1 Sensori minimi per MVP energetico
- `T_ACS` (°C)
- `T_VOLANO` (°C)
- `T_PUFFER_TOP` (°C)
- `T_SOL_MANDATA` (°C)
- `GRID_EXPORT_W` (W) — con opzione invertibile segno

### 4.2 Switch minimi per MVP resistenze + trasferimenti
- Resistenze: `SW_RES1`, `SW_RES2`, `SW_RES3`
- Volano→ACS: `SW_VOL_ACS_VALVE`, `SW_VOL_ACS_PUMP`
- Volano→Puffer: `SW_VOL_PUF_VALVE`, `SW_VOL_PUF_PUMP`
- Puffer→ACS: `SW_PUF_ACS_PUMP`

### 4.3 Solare (valvole relè)
- `SW_SOL_NORMAL` (R9)
- `SW_SOL_PRECEDENZA` (R10)
- `SW_SOL_NOTTE` (R8)
- `SW_SOL_R18`, `SW_SOL_R19`

### 4.4 Heat Radiator (miscelatrice)
- `T_MANDATA_MISCELATA`
- `T_RITORNO_MISCELATO` opzionale
- `SW_MIX_ALZA`, `SW_MIX_ABBASSA`
- `SP_MIX` (iniziale: input_number già esistente)

---

## 5) Regole operative precise (da implementare)

### 5.1 Sequenze valvola→pompa
Start: valvola ON → delay_start → pompa ON  
Stop: valvola OFF → delay_stop → pompa OFF

### 5.2 Volano→ACS
START se dest=ACS e `T_VOL >= T_ACS + Δ_START` e safety OK  
HOLD finché `T_VOL >= T_ACS + Δ_HOLD` e safety OK  
STOP se setpoint raggiunto o Δ non ok o safety o unavailable

### 5.3 Volano→Puffer
START se dest=PUFFER e `T_VOL >= T_PUF + Δ_START` e limiti OK

### 5.4 Puffer→ACS (BP2)
Start/stop/timeout come blueprint (vedi sezione 2)

### 5.5 Resistenze su export con OFF delay 5s
Step up immediato; step down con countdown 5s; cutback volano immediato.

### 5.6 Solare (BP4)
Macchina a stati con NIGHT/PRECEDENZA/CUTBACK + interlock + ritorni.

### 5.7 Miscelatrice (BP7)
Replica impulsi proporzionali, forzatura, antirimbalzo, safety.

---

## 6) Roadmap consigliata
1) LIVE resistenze + VOLANO_MAX
2) volano→ACS
3) volano→puffer + puffer→ACS
4) SolarManager
5) Miscelatrice
6) ZoneManager + PDC (quando pronti)

---

FINE
