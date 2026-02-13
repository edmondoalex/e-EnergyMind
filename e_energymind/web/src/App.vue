<template>
  <div class="wrap">
    <header class="top">
      <div class="brand">e-EnergyMind</div>
      <div class="top-actions">
        <button class="action-btn" @click="saveAll">Salva tutto</button>
        <button class="action-btn" @click="exportConfig">Esporta config</button>
        <label class="action-btn upload">
          Importa config
          <input type="file" accept="application/json" @change="importConfig"/>
        </label>
      </div>
      <nav class="tabs">
        <button :class="{active: tab==='user'}" @click="tab='user'">User</button>
        <button :class="{active: tab==='admin'}" @click="tab='admin'">Admin</button>
      </nav>
    </header>

    <main class="main">
      <section v-if="tab==='user'" class="card">
        <h2>Stato (v0.2)</h2>
        <div class="statusline">
          <span class="muted">v{{ status?.version || '-' }}</span>
          <span v-if="status?.runtime_mode === 'live'" class="muted">modo: live operativo</span>
          <span v-else class="muted">mode: {{ status?.runtime_mode || '-' }}</span>
          <span class="badge" :class="status?.ha_connected ? 'ok' : 'off'">
            {{ status?.ha_connected ? 'Online' : 'Offline' }}
          </span>
          <span class="muted">HA</span>
          <span class="muted">Ultimo aggiornamento: {{ lastUpdate ? lastUpdate.toLocaleTimeString() : '-' }}</span>
        </div>
        <p v-if="status?.runtime_mode !== 'live'" class="muted">Dry-run: nessun comando agli attuatori. Serve per validare la logica.</p>

        <div v-if="d" class="grid">
          <div class="kpi" :class="historyEnabled('t_acs_alto') ? 'clickable' : ''" @click="openHistory('t_acs_alto','T_ACS')">
            <div class="k"><i v-if="mdiClass(ent?.t_acs?.attributes?.icon)" :class="mdiClass(ent?.t_acs?.attributes?.icon)"></i> T_ACS</div>
            <div class="v">{{ fmtTemp(d.inputs.t_acs) }}</div>
          </div>
          <div class="kpi" :class="historyEnabled('t_puffer_alto') ? 'clickable' : ''" @click="openHistory('t_puffer_alto','T_Puffer')">
            <div class="k"><i v-if="mdiClass(ent?.t_puffer?.attributes?.icon)" :class="mdiClass(ent?.t_puffer?.attributes?.icon)"></i> T_Puffer</div>
            <div class="v">{{ fmtTemp(d.inputs.t_puffer) }}</div>
          </div>
          <div class="kpi" :class="historyEnabled('t_volano_alto') ? 'clickable' : ''" @click="openHistory('t_volano_alto','T_Volano')">
            <div class="k"><i v-if="mdiClass(ent?.t_volano?.attributes?.icon)" :class="mdiClass(ent?.t_volano?.attributes?.icon)"></i> T_Volano</div>
            <div class="v">{{ fmtTemp(d.inputs.t_volano) }}</div>
          </div>
          <div class="kpi" :class="historyEnabled('t_solare_mandata') ? 'clickable' : ''" @click="openHistory('t_solare_mandata','T_Solare mandata')">
            <div class="k"><i v-if="mdiClass(ent?.t_solare_mandata?.attributes?.icon)" :class="mdiClass(ent?.t_solare_mandata?.attributes?.icon)"></i> T_Solare mandata</div>
            <div class="v">{{ fmtTemp(d.inputs.t_solare_mandata) }}</div>
          </div>
          <div class="kpi" :class="historyEnabled('t_esterna') ? 'clickable' : ''" @click="openHistory('t_esterna','T esterna')">
            <div class="k"><i v-if="mdiClass(ent?.t_esterna?.attributes?.icon)" :class="mdiClass(ent?.t_esterna?.attributes?.icon)"></i> T esterna</div>
            <div class="v">{{ fmtTemp(d.inputs.t_esterna) }}</div>
          </div>
          <div class="kpi" :class="historyEnabled('t_mandata_miscelata') ? 'clickable' : ''" @click="openHistory('t_mandata_miscelata','T mandata miscelata')">
            <div class="k"><i v-if="mdiClass(ent?.t_mandata_miscelata?.attributes?.icon)" :class="mdiClass(ent?.t_mandata_miscelata?.attributes?.icon)"></i> T mandata</div>
            <div class="v">{{ fmtTemp(d.inputs.t_mandata_miscelata) }}</div>
          </div>
          <div class="kpi" :class="historyEnabled('t_ritorno_miscelato') ? 'clickable' : ''" @click="openHistory('t_ritorno_miscelato','T ritorno miscelato')">
            <div class="k"><i v-if="mdiClass(ent?.t_ritorno_miscelato?.attributes?.icon)" :class="mdiClass(ent?.t_ritorno_miscelato?.attributes?.icon)"></i> T ritorno</div>
            <div class="v">{{ fmtTemp(d.inputs.t_ritorno_miscelato) }}</div>
          </div>
          <div class="kpi">
            <div class="k"><i v-if="mdiClass(ent?.grid_export_w?.attributes?.icon)" :class="mdiClass(ent?.grid_export_w?.attributes?.icon)"></i> Export rete</div>
            <div class="v">{{ fmtW(d.inputs.grid_export_w) }}</div>
          </div>
        </div>
        <div v-if="d" class="row3">
          <div class="kpi kpi-center" :class="historyEnabled('t_acs_alto') ? 'clickable' : ''" @click="openHistory('t_acs_alto','ACS Alto')">
            <div class="k">ACS Alto</div>
            <div class="v">{{ fmtTemp(d.inputs.t_acs_alto) }}</div>
          </div>
          <div class="kpi kpi-center" :class="historyEnabled('t_acs_medio') ? 'clickable' : ''" @click="openHistory('t_acs_medio','ACS Medio')">
            <div class="k">ACS Medio</div>
            <div class="v">{{ fmtTemp(d.inputs.t_acs_medio) }}</div>
          </div>
          <div class="kpi kpi-center" :class="historyEnabled('t_acs_basso') ? 'clickable' : ''" @click="openHistory('t_acs_basso','ACS Basso')">
            <div class="k">ACS Basso</div>
            <div class="v">{{ fmtTemp(d.inputs.t_acs_basso) }}</div>
          </div>
        </div>

        <div v-if="d" class="card inner module-panel" :class="modulePanelClass('gas_emergenza')">
          <div class="row"><strong>Grafico rapido (ultimi ~2-3 min)</strong></div>
          <div class="chart-grid">
            <div class="chart">
              <div class="chart-title">Temperature</div>
              <svg viewBox="0 0 300 90" role="img" aria-label="Grafico temperature">
                <polyline :points="sparkPoints(history.t_acs_alto)" class="spark acs"/>
                <polyline :points="sparkPoints(history.t_puffer_alto)" class="spark puffer"/>
                <polyline :points="sparkPoints(history.t_volano_alto)" class="spark volano"/>
              </svg>
              <div class="axis-note">Y: {{ tempStats.label }}</div>
              <div class="axis-note">X: ultimi ~2–3 min</div>
              <div class="legend small">
                <span class="legend-item"><span class="legend-dot acs"></span> ACS</span>
                <span class="legend-item"><span class="legend-dot puffer"></span> Puffer</span>
                <span class="legend-item"><span class="legend-dot volano"></span> Volano</span>
              </div>
            </div>
            <div class="chart">
              <div class="chart-title">Export (W)</div>
              <svg viewBox="0 0 300 90" role="img" aria-label="Grafico export rete">
                <polyline :points="sparkPoints(history.export_w)" class="spark export"/>
              </svg>
              <div class="axis-note">Y: {{ exportStats.label }}</div>
              <div class="axis-note">X: ultimi ~2–3 min</div>
              <div class="legend small">
                <span class="legend-item"><span class="legend-dot export"></span> Export rete</span>
              </div>
            </div>
          </div>
        </div>

        <div class="card inner">
          <div class="row"><strong>Moduli (User)</strong></div>
          <div class="row3">
            <button class="ghost toggle" :class="moduleClass('resistenze_volano')" @click="toggleModule('resistenze_volano')">
              Resistenze Volano: {{ modules.resistenze_volano ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('volano_to_acs')" @click="toggleModule('volano_to_acs')">
              Volano → ACS: {{ modules.volano_to_acs ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('volano_to_puffer')" @click="toggleModule('volano_to_puffer')">
              Volano → Puffer: {{ modules.volano_to_puffer ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('puffer_to_acs')" @click="toggleModule('puffer_to_acs')">
              Puffer → ACS: {{ modules.puffer_to_acs ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('impianto')" @click="toggleModule('impianto')">
              Impianto Riscaldamento: {{ modules.impianto ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('gas_emergenza')" @click="toggleModule('gas_emergenza')">
              Caldaia Gas Emergenza Riscaldamento: {{ modules.gas_emergenza ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('caldaia_legna')" @click="toggleModule('caldaia_legna')">
              Caldaia Legna: {{ modules.caldaia_legna ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('solare')" @click="toggleModule('solare')">
              Solare: {{ modules.solare ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('miscelatrice')" @click="toggleModule('miscelatrice')">
              Miscelatrice: {{ modules.miscelatrice ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('curva_climatica')" @click="toggleModule('curva_climatica')">
              Curva climatica: {{ modules.curva_climatica ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('pdc')" @click="toggleModule('pdc')">
              PDC: {{ modules.pdc ? 'ON' : 'OFF' }}
            </button>
          </div>
        </div>


        <div v-if="d" class="card inner module-panel" :class="modulePanelClass('miscelatrice')">
          <div class="row"><strong>Destinazione surplus:</strong> {{ d.computed.dest }}</div>
          <div class="muted">{{ d.computed.dest_reason }}</div>
          <hr />
          <div class="row"><strong>Source -> ACS:</strong> {{ d.computed.source_to_acs }}</div>
          <div class="muted">{{ d.computed.source_reason }}</div>
          <hr />
          <div class="row"><strong>Carica riserva:</strong> {{ d.computed.charge_buffer }} (step {{ d.computed.resistance_step }}/3)</div>
          <div class="muted">{{ d.computed.charge_reason }}</div>
          <div v-if="moduleReasonsList.length">
            <hr />
            <div class="row"><strong>Moduli</strong></div>
            <div class="module-reasons">
              <div v-for="item in moduleReasonsList" :key="item.key" class="module-row" :class="{'mod-on': item.enabled, 'mod-active': item.enabled && item.active}">
                <div class="module-head">
                  <div class="module-label">{{ item.label }}</div>
                  <div class="module-badges">
                    <span class="badge-mini" :class="item.enabled ? 'on' : 'off'">
                      {{ item.enabled ? 'MOD ON' : 'MOD OFF' }}
                    </span>
                    <span class="badge-mini" :class="item.active ? 'active' : 'idle'">
                      {{ item.active ? 'ATTIVO' : 'INATTIVO' }}
                    </span>
                  </div>
                </div>
                <div class="muted">{{ item.reason }}</div>
                <div v-if="item.key === 'impianto'" class="module-extra">
                  <div class="muted">
                    Selettore: {{ d?.computed?.impianto?.selector || '-' }} | Sorgente: {{ d?.computed?.impianto?.source || '-' }} | Richiesta: {{ d?.computed?.impianto?.richiesta ? 'ON' : 'OFF' }} | Miscelatrice: {{ d?.computed?.impianto?.miscelatrice ? 'ON' : 'OFF' }}
                  </div>
                  <div class="muted">
                    PDC/Volano ready: {{ d?.computed?.impianto?.pdc_ready ? 'SI' : 'NO' }} | Puffer ready: {{ d?.computed?.impianto?.puffer_ready ? 'SI' : 'NO' }}
                  </div>
                  <div class="muted">
                    Volano OK: {{ d?.computed?.impianto?.volano_temp_ok ? 'SI' : 'NO' }} (T={{ fmtTemp(d?.inputs?.t_volano) }} / min {{ fmtNum(sp?.impianto?.volano_min_c) }}°C)
                    | Puffer OK: {{ d?.computed?.impianto?.puffer_temp_ok ? 'SI' : 'NO' }} (T={{ fmtTemp(d?.inputs?.t_puffer) }} / min {{ fmtNum(sp?.impianto?.puffer_min_c) }}°C)
                  </div>
                  <div v-if="d?.computed?.impianto?.blocked_cold" class="muted">
                    Blocco freddo attivo: sorgenti sotto soglia minima.
                  </div>
                  <div v-else class="muted">
                    Blocco freddo: OFF.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="act" class="card inner module-panel" :class="modulePanelClass('resistenze_volano')">
          <div class="row"><strong>Resistenze volano</strong></div>
          <div class="row3">
            <div class="kpi kpi-center clickable" :class="stateClass(act?.r22_resistenza_1_volano_pdc?.state)" @click="userToggle(act?.r22_resistenza_1_volano_pdc, 'resistenze_volano')">
              <div class="k">
                <i v-if="mdiClass(act?.r22_resistenza_1_volano_pdc?.attributes?.icon)" :class="[mdiClass(act?.r22_resistenza_1_volano_pdc?.attributes?.icon), stateClass(act?.r22_resistenza_1_volano_pdc?.state)]"></i>
                R22 Resistenza 1 Volano PDC
              </div>
            </div>
            <div class="kpi kpi-center clickable" :class="stateClass(act?.r23_resistenza_2_volano_pdc?.state)" @click="userToggle(act?.r23_resistenza_2_volano_pdc, 'resistenze_volano')">
              <div class="k">
                <i v-if="mdiClass(act?.r23_resistenza_2_volano_pdc?.attributes?.icon)" :class="[mdiClass(act?.r23_resistenza_2_volano_pdc?.attributes?.icon), stateClass(act?.r23_resistenza_2_volano_pdc?.state)]"></i>
                R23 Resistenza 2 Volano PDC
              </div>
            </div>
            <div class="kpi kpi-center clickable" :class="stateClass(act?.r24_resistenza_3_volano_pdc?.state)" @click="userToggle(act?.r24_resistenza_3_volano_pdc, 'resistenze_volano')">
              <div class="k">
                <i v-if="mdiClass(act?.r24_resistenza_3_volano_pdc?.attributes?.icon)" :class="[mdiClass(act?.r24_resistenza_3_volano_pdc?.attributes?.icon), stateClass(act?.r24_resistenza_3_volano_pdc?.state)]"></i>
                R24 Resistenza 3 Volano PDC
              </div>
            </div>
            <div class="kpi kpi-center clickable" :class="stateClass(act?.generale_resistenze_volano_pdc?.state)" @click="userToggle(act?.generale_resistenze_volano_pdc, 'resistenze_volano')">
              <div class="k">
                <i :class="[mdiClass(act?.generale_resistenze_volano_pdc?.attributes?.icon) || 'mdi mdi-power', stateClass(act?.generale_resistenze_volano_pdc?.state)]"></i>
                R0 Generale Resistenze Volano PDC
              </div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">
                <i v-if="mdiClass(ent?.resistenze_volano_power?.attributes?.icon)" :class="mdiClass(ent?.resistenze_volano_power?.attributes?.icon)"></i>
                Potenza Resistenze
              </div>
              <div class="v">{{ fmtEntity(ent?.resistenze_volano_power) }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">
                <i v-if="mdiClass(ent?.resistenze_volano_energy?.attributes?.icon)" :class="mdiClass(ent?.resistenze_volano_energy?.attributes?.icon)"></i>
                Energia Resistenze
              </div>
              <div class="v">{{ fmtEntity(ent?.resistenze_volano_energy) }}</div>
            </div>
          </div>
          <div class="row2">
            <div class="kpi kpi-center" :class="historyEnabled('t_volano_alto') ? 'clickable' : ''" @click="openHistory('t_volano_alto','T Volano Alto')">
              <div class="k">T Volano Alto</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_volano_alto) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_volano_basso') ? 'clickable' : ''" @click="openHistory('t_volano_basso','T Volano Basso')">
              <div class="k">T Volano Basso</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_volano_basso) }}</div>
            </div>
          </div>
        </div>

        <div v-if="act" class="card inner module-panel" :class="modulePanelClass('volano_to_acs')">
          <div class="row"><strong>Volano → ACS</strong></div>
          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('t_volano') ? 'clickable' : ''" @click="openHistory('t_volano','T_Volano')">
              <div class="k">
                <i v-if="mdiClass(ent?.t_volano?.attributes?.icon)" :class="mdiClass(ent?.t_volano?.attributes?.icon)"></i>
                T_Volano
              </div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_volano) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_acs') ? 'clickable' : ''" @click="openHistory('t_acs','T_ACS')">
              <div class="k">
                <i v-if="mdiClass(ent?.t_acs?.attributes?.icon)" :class="mdiClass(ent?.t_acs?.attributes?.icon)"></i>
                T_ACS
              </div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_acs) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('delta_volano_acs') ? 'clickable' : ''" @click="openHistory('delta_volano_acs','Delta Volano-ACS')">
              <div class="k">Delta (Volano - ACS)</div>
              <div class="v">{{ fmtDelta(d?.inputs?.t_volano, d?.inputs?.t_acs) }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center clickable" :class="stateClass(act?.r6_valve_pdc_to_integrazione_acs?.state)" @click="userToggle(act?.r6_valve_pdc_to_integrazione_acs, 'volano_to_acs')">
              <div class="k">
                <i v-if="mdiClass(act?.r6_valve_pdc_to_integrazione_acs?.attributes?.icon)" :class="[mdiClass(act?.r6_valve_pdc_to_integrazione_acs?.attributes?.icon), stateClass(act?.r6_valve_pdc_to_integrazione_acs?.state)]"></i>
                Valvola PDC → ACS
              </div>
            </div>
            <div class="kpi kpi-center clickable" :class="stateClass(act?.r13_pump_pdc_to_acs_puffer?.state)" @click="userToggle(act?.r13_pump_pdc_to_acs_puffer, 'volano_to_acs')">
              <div class="k">
                <i v-if="mdiClass(act?.r13_pump_pdc_to_acs_puffer?.attributes?.icon)" :class="[mdiClass(act?.r13_pump_pdc_to_acs_puffer?.attributes?.icon), stateClass(act?.r13_pump_pdc_to_acs_puffer?.state)]"></i>
                R13 Pompa PDC → ACS/Puffer
              </div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Stato logica</div>
              <div class="v">{{ d?.computed?.flags?.volano_to_acs ? 'ATTIVO' : 'STOP' }}</div>
            </div>
          </div>
          <div class="row2">
            <div class="kpi kpi-center" :class="historyEnabled('t_volano_alto') ? 'clickable' : ''" @click="openHistory('t_volano_alto','T Volano Alto')">
              <div class="k">T Volano Alto</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_volano_alto) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_volano_basso') ? 'clickable' : ''" @click="openHistory('t_volano_basso','T Volano Basso')">
              <div class="k">T Volano Basso</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_volano_basso) }}</div>
            </div>
          </div>
        </div>

        <div v-if="act" class="card inner module-panel" :class="modulePanelClass('volano_to_puffer')">
          <div class="row"><strong>Volano → Puffer</strong></div>
          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('t_volano') ? 'clickable' : ''" @click="openHistory('t_volano','T_Volano')">
              <div class="k">
                <i v-if="mdiClass(ent?.t_volano?.attributes?.icon)" :class="mdiClass(ent?.t_volano?.attributes?.icon)"></i>
                T_Volano
              </div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_volano) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_puffer') ? 'clickable' : ''" @click="openHistory('t_puffer','T_Puffer')">
              <div class="k">
                <i v-if="mdiClass(ent?.t_puffer?.attributes?.icon)" :class="mdiClass(ent?.t_puffer?.attributes?.icon)"></i>
                T_Puffer
              </div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_puffer) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('delta_volano_puffer') ? 'clickable' : ''" @click="openHistory('delta_volano_puffer','Delta Volano-Puffer')">
              <div class="k">Delta (Volano - Puffer)</div>
              <div class="v">{{ fmtDelta(d?.inputs?.t_volano, d?.inputs?.t_puffer) }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center clickable" :class="stateClass(act?.r7_valve_pdc_to_integrazione_puffer?.state)" @click="userToggle(act?.r7_valve_pdc_to_integrazione_puffer, 'volano_to_puffer')">
              <div class="k">
                <i v-if="mdiClass(act?.r7_valve_pdc_to_integrazione_puffer?.attributes?.icon)" :class="[mdiClass(act?.r7_valve_pdc_to_integrazione_puffer?.attributes?.icon), stateClass(act?.r7_valve_pdc_to_integrazione_puffer?.state)]"></i>
                R7 Valvola PDC → Puffer
              </div>
            </div>
            <div class="kpi kpi-center clickable" :class="stateClass(act?.r13_pump_pdc_to_acs_puffer?.state)" @click="userToggle(act?.r13_pump_pdc_to_acs_puffer, 'volano_to_puffer')">
              <div class="k">
                <i v-if="mdiClass(act?.r13_pump_pdc_to_acs_puffer?.attributes?.icon)" :class="[mdiClass(act?.r13_pump_pdc_to_acs_puffer?.attributes?.icon), stateClass(act?.r13_pump_pdc_to_acs_puffer?.state)]"></i>
                R13 Pompa PDC → ACS/Puffer
              </div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Stato logica</div>
              <div class="v">{{ d?.computed?.flags?.volano_to_puffer ? 'ATTIVO' : 'STOP' }}</div>
            </div>
          </div>
        </div>

        <div v-if="act" class="card inner module-panel" :class="modulePanelClass('solare')">
          <div class="row"><strong>Solare</strong></div>
          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('t_solare_mandata') ? 'clickable' : ''" @click="openHistory('t_solare_mandata','T_Solare mandata')">
              <div class="k">
                <i v-if="mdiClass(ent?.t_solare_mandata?.attributes?.icon)" :class="mdiClass(ent?.t_solare_mandata?.attributes?.icon)"></i>
                T_Solare mandata
              </div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_solare_mandata) }}</div>
            </div>
            <div class="kpi kpi-center" :class="solarModeClass">
              <div class="k">Modalità</div>
              <div class="v">{{ sp?.solare?.mode || 'auto' }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Cutback</div>
              <div class="v">{{ d?.computed?.safety?.acs_max_hit ? 'ACS_MAX' : (d?.inputs?.t_solare_mandata >= (sp?.solare?.max_c || 90) ? 'SOL_MAX' : 'OK') }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="stateClass(act?.r8_valve_solare_notte_low_temp?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r8_valve_solare_notte_low_temp?.attributes?.icon)" :class="[mdiClass(act?.r8_valve_solare_notte_low_temp?.attributes?.icon), stateClass(act?.r8_valve_solare_notte_low_temp?.state)]"></i>
                R8 Solare Notte/Low
              </div>
            </div>
            <div class="kpi kpi-center" :class="stateClass(act?.r9_valve_solare_normal_funz?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r9_valve_solare_normal_funz?.attributes?.icon)" :class="[mdiClass(act?.r9_valve_solare_normal_funz?.attributes?.icon), stateClass(act?.r9_valve_solare_normal_funz?.state)]"></i>
                R9 Solare Normal
              </div>
            </div>
            <div class="kpi kpi-center" :class="stateClass(act?.r10_valve_solare_precedenza_acs?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r10_valve_solare_precedenza_acs?.attributes?.icon)" :class="[mdiClass(act?.r10_valve_solare_precedenza_acs?.attributes?.icon), stateClass(act?.r10_valve_solare_precedenza_acs?.state)]"></i>
                R10 Precedenza ACS
              </div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center clickable" :class="stateClass(act?.r18_valve_ritorno_solare_basso?.state)" @click="userToggleManual(act?.r18_valve_ritorno_solare_basso)">
              <div class="k">
                <i v-if="mdiClass(act?.r18_valve_ritorno_solare_basso?.attributes?.icon)" :class="[mdiClass(act?.r18_valve_ritorno_solare_basso?.attributes?.icon), stateClass(act?.r18_valve_ritorno_solare_basso?.state)]"></i>
                R18 Ritorno Solare Basso
              </div>
            </div>
            <div class="kpi kpi-center clickable" :class="stateClass(act?.r19_valve_ritorno_solare_alto?.state)" @click="userToggleManual(act?.r19_valve_ritorno_solare_alto)">
              <div class="k">
                <i v-if="mdiClass(act?.r19_valve_ritorno_solare_alto?.attributes?.icon)" :class="[mdiClass(act?.r19_valve_ritorno_solare_alto?.attributes?.icon), stateClass(act?.r19_valve_ritorno_solare_alto?.state)]"></i>
                R19 Ritorno Solare Alto
              </div>
            </div>
          </div>
        </div>

        <div v-if="d" class="card inner module-panel" :class="modulePanelClass('miscelatrice')">
          <div class="row"><strong>Collettore solare</strong></div>
          <div class="row3">
            <div class="kpi kpi-center">
              <div class="k">Codice di stato</div>
              <div class="v">{{ fmtText(d?.inputs?.collettore_status_code) }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Stato</div>
              <div class="v">{{ fmtText(d?.inputs?.collettore_status) }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Data e ora</div>
              <div class="v">{{ fmtText(d?.inputs?.collettore_datetime) }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('collettore_energy_day_kwh') ? 'clickable' : ''" @click="openHistory('collettore_energy_day_kwh','Energia solare (giorno)')">
              <div class="k">Energia solare (giorno)</div>
              <div class="v">{{ fmtNum(d?.inputs?.collettore_energy_day_kwh) }} kWh</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('collettore_energy_total_kwh') ? 'clickable' : ''" @click="openHistory('collettore_energy_total_kwh','Energia solare (totale)')">
              <div class="k">Energia solare (totale)</div>
              <div class="v">{{ fmtNum(d?.inputs?.collettore_energy_total_kwh) }} kWh</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('collettore_flow_lmin') ? 'clickable' : ''" @click="openHistory('collettore_flow_lmin','Portata solare')">
              <div class="k">Portata (L/min)</div>
              <div class="v">{{ fmtNum(d?.inputs?.collettore_flow_lmin) }} L/min</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('collettore_pwm_pct') ? 'clickable' : ''" @click="openHistory('collettore_pwm_pct','PWM Pompa solare')">
              <div class="k">PWM Pompa</div>
              <div class="v">{{ fmtNum(d?.inputs?.collettore_pwm_pct) }}%</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Stato 2</div>
              <div class="v">{{ fmtText(d?.inputs?.collettore_status2) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('collettore_temp_esterna') ? 'clickable' : ''" @click="openHistory('collettore_temp_esterna','Temperatura esterna solare')">
              <div class="k">Temperatura esterna</div>
              <div class="v">{{ fmtTemp(d?.inputs?.collettore_temp_esterna) }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('collettore_tsa1') ? 'clickable' : ''" @click="openHistory('collettore_tsa1','Collettore TSA1')">
              <div class="k">Collettore (TSA1)</div>
              <div class="v">{{ fmtTemp(d?.inputs?.collettore_tsa1) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('collettore_tse') ? 'clickable' : ''" @click="openHistory('collettore_tse','Ritorno solare TSE')">
              <div class="k">Ritorno solare (TSE)</div>
              <div class="v">{{ fmtTemp(d?.inputs?.collettore_tse) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('collettore_tsv') ? 'clickable' : ''" @click="openHistory('collettore_tsv','Mandata solare TSV')">
              <div class="k">Mandata solare (TSV)</div>
              <div class="v">{{ fmtTemp(d?.inputs?.collettore_tsv) }}</div>
            </div>
          </div>
          <div class="row2">
            <div class="kpi kpi-center" :class="historyEnabled('collettore_twu') ? 'clickable' : ''" @click="openHistory('collettore_twu','Serbatoio superiore TWU')">
              <div class="k">Serbatoio superiore metà (TWU)</div>
              <div class="v">{{ fmtTemp(d?.inputs?.collettore_twu) }}</div>
            </div>
          </div>
        </div>

        <div v-if="act" class="card inner module-panel" :class="modulePanelClass('puffer_to_acs')">
          <div class="row"><strong>Puffer → ACS</strong></div>

          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('t_puffer') ? 'clickable' : ''" @click="openHistory('t_puffer','T_Puffer')">
              <div class="k">
                <i v-if="mdiClass(ent?.t_puffer?.attributes?.icon)" :class="mdiClass(ent?.t_puffer?.attributes?.icon)"></i>
                T_Puffer
              </div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_puffer) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_acs') ? 'clickable' : ''" @click="openHistory('t_acs','T_ACS')">
              <div class="k">
                <i v-if="mdiClass(ent?.t_acs?.attributes?.icon)" :class="mdiClass(ent?.t_acs?.attributes?.icon)"></i>
                T_ACS
              </div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_acs) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('delta_puffer_acs') ? 'clickable' : ''" @click="openHistory('delta_puffer_acs','Delta Puffer-ACS')">
              <div class="k">Delta (Puffer - ACS)</div>
              <div class="v">{{ fmtDelta(d?.inputs?.t_puffer, d?.inputs?.t_acs) }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center clickable" :class="stateClass(act?.r14_pump_puffer_to_acs?.state)" @click="userToggle(act?.r14_pump_puffer_to_acs, 'puffer_to_acs')">
              <div class="k">
                <i v-if="mdiClass(act?.r14_pump_puffer_to_acs?.attributes?.icon)" :class="[mdiClass(act?.r14_pump_puffer_to_acs?.attributes?.icon), stateClass(act?.r14_pump_puffer_to_acs?.state)]"></i>
                R14 Pompa Puffer → ACS
              </div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Stato logica</div>
              <div class="v">{{ d?.computed?.flags?.puffer_to_acs ? 'ATTIVO' : 'STOP' }}</div>
            </div>
          </div>
        </div>

        <div v-if="act" class="card inner module-panel" :class="modulePanelClass('impianto')">
          <div class="row"><strong>Impianto riscaldamento (interno)</strong></div>
          <div class="row3">
            <div class="kpi kpi-center">
              <div class="k">Sorgente</div>
              <select v-model="sp.impianto.source_mode">
                <option value="AUTO">AUTO</option>
                <option value="PDC">PDC/Volano</option>
                <option value="PUFFER">PUFFER</option>
              </select>
            </div>
            <label class="kpi kpi-center checkbox">
              <input type="checkbox" v-model="sp.impianto.pdc_ready"/>
              <span>PDC/Volano ready</span>
            </label>
            <label class="kpi kpi-center checkbox">
              <input type="checkbox" v-model="sp.impianto.puffer_ready"/>
              <span>Puffer ready</span>
            </label>
            <div class="kpi kpi-center">
              <div class="k">Stagione</div>
              <select v-model="sp.impianto.season_mode">
                <option value="winter">Inverno</option>
                <option value="summer">Estate</option>
              </select>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Richiesta calore</div>
              <div class="v">{{ d?.computed?.impianto?.richiesta ? 'ON' : 'OFF' }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Consenso miscelatrice</div>
              <div class="v">{{ d?.computed?.impianto?.miscelatrice ? 'ON' : 'OFF' }}</div>
            </div>
          </div>
          <div class="help">I checkbox sono manuali nel solo add-on. Richiesta calore e consenso miscelatrice sono in sola lettura.</div>
          <div v-if="d?.computed?.module_reasons?.impianto" class="muted">
            Motivo: {{ d.computed.module_reasons.impianto }}
          </div>
          <div v-if="d?.computed?.impianto?.blocked_cold" class="warn">
            Sorgenti troppo fredde: impianto bloccato.
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="stateClass(act?.r12_pump_mandata_piani?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r12_pump_mandata_piani?.attributes?.icon)" :class="[mdiClass(act?.r12_pump_mandata_piani?.attributes?.icon), stateClass(act?.r12_pump_mandata_piani?.state)]"></i>
                R12 Pompa mandata piani
              </div>
            </div>
            <div class="kpi kpi-center" :class="stateClass(act?.r11_pump_mandata_laboratorio?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r11_pump_mandata_laboratorio?.attributes?.icon)" :class="[mdiClass(act?.r11_pump_mandata_laboratorio?.attributes?.icon), stateClass(act?.r11_pump_mandata_laboratorio?.state)]"></i>
                R11 Pompa mandata laboratorio
              </div>
            </div>
            <div class="kpi kpi-center" :class="stateClass(act?.r4_valve_impianto_da_puffer?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r4_valve_impianto_da_puffer?.attributes?.icon)" :class="[mdiClass(act?.r4_valve_impianto_da_puffer?.attributes?.icon), stateClass(act?.r4_valve_impianto_da_puffer?.state)]"></i>
                R4 Valvola impianto da Puffer
              </div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="stateClass(act?.r5_valve_impianto_da_pdc?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r5_valve_impianto_da_pdc?.attributes?.icon)" :class="[mdiClass(act?.r5_valve_impianto_da_pdc?.attributes?.icon), stateClass(act?.r5_valve_impianto_da_pdc?.state)]"></i>
                R5 Valvola impianto da PDC/Volano
              </div>
            </div>
            <div class="kpi kpi-center" :class="stateClass(act?.r2_valve_comparto_mandata_imp_pt?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r2_valve_comparto_mandata_imp_pt?.attributes?.icon)" :class="[mdiClass(act?.r2_valve_comparto_mandata_imp_pt?.attributes?.icon), stateClass(act?.r2_valve_comparto_mandata_imp_pt?.state)]"></i>
                R2 Valvola comparto PT
              </div>
            </div>
            <div class="kpi kpi-center" :class="stateClass(act?.r3_valve_comparto_mandata_imp_m1p?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r3_valve_comparto_mandata_imp_m1p?.attributes?.icon)" :class="[mdiClass(act?.r3_valve_comparto_mandata_imp_m1p?.attributes?.icon), stateClass(act?.r3_valve_comparto_mandata_imp_m1p?.state)]"></i>
                R3 Valvola comparto M+1P
              </div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="stateClass(act?.r1_valve_comparto_laboratorio?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r1_valve_comparto_laboratorio?.attributes?.icon)" :class="[mdiClass(act?.r1_valve_comparto_laboratorio?.attributes?.icon), stateClass(act?.r1_valve_comparto_laboratorio?.state)]"></i>
                R1 Valvola laboratorio
              </div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('t_puffer_alto') ? 'clickable' : ''" @click="openHistory('t_puffer_alto','T Puffer Alto')">
              <div class="k">T Puffer Alto</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_puffer_alto) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_puffer_medio') ? 'clickable' : ''" @click="openHistory('t_puffer_medio','T Puffer Medio')">
              <div class="k">T Puffer Medio</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_puffer_medio) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_puffer_basso') ? 'clickable' : ''" @click="openHistory('t_puffer_basso','T Puffer Basso')">
              <div class="k">T Puffer Basso</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_puffer_basso) }}</div>
            </div>
          </div>
          <div class="row2">
            <div class="kpi kpi-center" :class="historyEnabled('t_volano_alto') ? 'clickable' : ''" @click="openHistory('t_volano_alto','T Volano Alto')">
              <div class="k">T Volano Alto</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_volano_alto) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_volano_basso') ? 'clickable' : ''" @click="openHistory('t_volano_basso','T Volano Basso')">
              <div class="k">T Volano Basso</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_volano_basso) }}</div>
            </div>
          </div>
          <div class="zones-card">
            <div class="row"><strong>Zone attive</strong></div>
            <div class="zones-grid">
              <div v-for="z in zones" :key="z.entity_id" class="zone-chip" :class="z.active ? 'zone-on' : 'zone-off'" @click="openZone(z)">
                <div class="zone-title">{{ z.group }} | {{ z.entity_id }}</div>
                <div class="zone-sub">{{ z.state || '-' }} | {{ z.hvac_action || '-' }}</div>
                <div class="zone-sub">T: {{ fmtNum(z.temperature) }}°C | SP: {{ fmtNum(z.setpoint) }}°C</div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="d" class="card inner">
          <div class="row"><strong>Caldaia Gas Emergenza Riscaldamento</strong></div>
          <div class="row3">
            <div class="kpi kpi-center">
              <div class="k">Modulo</div>
              <div class="v">{{ modules.gas_emergenza ? 'ON' : 'OFF' }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Necessaria</div>
              <div class="v">{{ d?.computed?.gas_emergenza?.need ? 'SI' : 'NO' }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Domanda</div>
              <div class="v">{{ d?.computed?.gas_emergenza?.demand ? 'ON' : 'OFF' }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center">
              <div class="k">Volano OK</div>
              <div class="v">{{ d?.computed?.gas_emergenza?.vol_ok ? 'SI' : 'NO' }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Puffer OK</div>
              <div class="v">{{ d?.computed?.gas_emergenza?.puf_ok ? 'SI' : 'NO' }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Motivo</div>
              <div class="v">{{ d?.computed?.module_reasons?.gas_emergenza || '-' }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="stateClass(act?.gas_boiler_power?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.gas_boiler_power?.attributes?.icon)" :class="[mdiClass(act?.gas_boiler_power?.attributes?.icon), stateClass(act?.gas_boiler_power?.state)]"></i>
                220V Caldaia Gas
              </div>
            </div>
            <div class="kpi kpi-center" :class="stateClass(act?.gas_boiler_ta?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.gas_boiler_ta?.attributes?.icon)" :class="[mdiClass(act?.gas_boiler_ta?.attributes?.icon), stateClass(act?.gas_boiler_ta?.state)]"></i>
                TA Caldaia Gas Emergenza Riscaldamento
              </div>
            </div>
          </div>
        </div>

        <div v-if="d" class="card inner module-panel" :class="modulePanelClass('caldaia_legna')">
          <div class="row"><strong>Caldaia Legna</strong></div>
          <div class="row3">
            <div class="kpi kpi-center">
              <div class="k">Modulo</div>
              <div class="v">{{ modules.caldaia_legna ? 'ON' : 'OFF' }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_mandata_caldaia_legna') ? 'clickable' : ''" @click="openHistory('t_mandata_caldaia_legna','T mandata legna')">
              <div class="k">T mandata</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_mandata_caldaia_legna) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_puffer_alto') ? 'clickable' : ''" @click="openHistory('t_puffer_alto','T Puffer Alto')">
              <div class="k">T Puffer Alto</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_puffer_alto) }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('t_ritorno_caldaia_legna') ? 'clickable' : ''" @click="openHistory('t_ritorno_caldaia_legna','T ritorno legna')">
              <div class="k">T ritorno</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_ritorno_caldaia_legna) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_caldaia_legna') ? 'clickable' : ''" @click="openHistory('t_caldaia_legna','T caldaia legna')">
              <div class="k">T caldaia</div>
              <div class="v">{{ fmtTemp(d?.inputs?.t_caldaia_legna) }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Motivo</div>
              <div class="v">{{ d?.computed?.caldaia_legna?.reason || d?.computed?.module_reasons?.caldaia_legna || '-' }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center">
              <div class="k">Min alim</div>
              <div class="v">{{ fmtNum(d?.computed?.caldaia_legna?.min_alim) }}&deg;C</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Isteresi alim</div>
              <div class="v">{{ fmtNum(d?.computed?.caldaia_legna?.min_alim_hyst) }}&deg;C</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">SP Puffer Alto</div>
              <div class="v">{{ fmtNum(d?.computed?.caldaia_legna?.sp_puffer_alto) }}&deg;C</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Isteresi TA</div>
              <div class="v">{{ fmtNum(d?.computed?.caldaia_legna?.puffer_hyst) }}&deg;C</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Forced-off</div>
              <div class="v">
                {{ sp?.caldaia_legna?.forced_off ? 'SI' : 'NO' }}
                <button class="ghost" @click="resetLegnaForcedOff">Reset</button>
              </div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center" :class="stateClass(act?.r30_alimentazione_caldaia_legna?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r30_alimentazione_caldaia_legna?.attributes?.icon)" :class="[mdiClass(act?.r30_alimentazione_caldaia_legna?.attributes?.icon), stateClass(act?.r30_alimentazione_caldaia_legna?.state)]"></i>
                R30 Alimentazione Caldaia Legna
              </div>
              <div class="v">{{ act?.r30_alimentazione_caldaia_legna?.state || '-' }}</div>
            </div>
            <div class="kpi kpi-center" :class="stateClass(act?.r20_ta_caldaia_legna?.state)">
              <div class="k">
                <i v-if="mdiClass(act?.r20_ta_caldaia_legna?.attributes?.icon)" :class="[mdiClass(act?.r20_ta_caldaia_legna?.attributes?.icon), stateClass(act?.r20_ta_caldaia_legna?.state)]"></i>
                R20 TA Caldaia Legna
              </div>
              <div class="v">{{ act?.r20_ta_caldaia_legna?.state || '-' }}</div>
            </div>
          </div>
        </div>

        <div v-if="d" class="card inner">
          <div class="row"><strong>Miscelatrice</strong></div>
          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('t_mandata_miscelata') ? 'clickable' : ''" @click="openHistory('t_mandata_miscelata','T mandata miscelata')">
              <div class="k">T mandata</div>
              <div class="v">{{ fmtNum(d?.inputs?.t_mandata_miscelata) }}&deg;C</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('t_ritorno_miscelato') ? 'clickable' : ''" @click="openHistory('t_ritorno_miscelato','T ritorno miscelato')">
              <div class="k">T ritorno</div>
              <div class="v">{{ fmtNum(d?.inputs?.t_ritorno_miscelato) }}&deg;C</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('miscelatrice_setpoint') ? 'clickable' : ''" @click="openHistory('miscelatrice_setpoint','SP miscelatrice')">
              <div class="k">SP mandata</div>
              <div class="v">{{ fmtNum(d?.computed?.miscelatrice?.setpoint) }}&deg;C</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center">
              <div class="k">Delta</div>
              <div class="v">{{ fmtDelta(d?.computed?.miscelatrice?.setpoint, d?.inputs?.t_mandata_miscelata) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('delta_mandata_ritorno') ? 'clickable' : ''" @click="openHistory('delta_mandata_ritorno','Delta Mandata/Ritorno')">
              <div class="k">Δ Mandata/Ritorno</div>
              <div class="v">{{ fmtDelta(d?.inputs?.t_mandata_miscelata, d?.inputs?.t_ritorno_miscelato) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('kp_eff') ? 'clickable' : ''" @click="openHistory('kp_eff','Kp eff')">
              <div class="k">Kp eff</div>
              <div class="v">{{ (d?.computed?.miscelatrice?.kp_eff ?? 0).toFixed(2) }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Stato</div>
              <div class="v">{{ d?.computed?.miscelatrice?.action || 'STOP' }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Motivo</div>
              <div class="v">{{ d?.computed?.miscelatrice?.reason || '-' }}</div>
            </div>
          </div>
        </div>

        <div v-if="d && sp?.curva_climatica" class="card inner module-panel" :class="modulePanelClass('curva_climatica')">
          <div class="row"><strong>Curva climatica mandata</strong></div>
          <div class="row3">
            <div class="kpi kpi-center" :class="historyEnabled('t_esterna') ? 'clickable' : ''" @click="openHistory('t_esterna','T esterna')">
              <div class="k">T esterna</div>
              <div class="v">{{ fmtTemp(d?.computed?.curva_climatica?.t_ext) }}</div>
            </div>
            <div class="kpi kpi-center" :class="historyEnabled('curva_setpoint') ? 'clickable' : ''" @click="openHistory('curva_setpoint','Setpoint curva')">
              <div class="k">Setpoint curva</div>
              <div class="v">{{ fmtNum(d?.computed?.curva_climatica?.setpoint) }}&deg;C</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Offset</div>
              <div class="v">{{ fmtNum(sp?.curva_climatica?.offset) }}&deg;C</div>
            </div>
          </div>
          <div class="curve-chart">
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Curva climatica">
              <polyline :points="curvePoints" class="curve-line"/>
              <line v-if="curveExtX !== null" :x1="curveExtX" y1="0" :x2="curveExtX" y2="100" class="curve-marker"/>
              <circle v-if="curveExtX !== null && curveExtY !== null" :cx="curveExtX" :cy="curveExtY" r="2.6" class="curve-dot"/>
              <text v-for="(y, i) in curveYTicks" :key="`y-${i}`" x="2" :y="4 + (i * 24)" class="curve-axis">
                {{ y.toFixed(1) }}°C
              </text>
            </svg>
            <div class="curve-x-axis">
              <div v-for="(x, i) in curveXTicks" :key="`x-${i}`" class="curve-x-label">{{ x.toFixed(1) }}°C</div>
            </div>
          </div>
          <div class="row2">
            <div class="mini-field">
              <div class="mini-head">
                <span class="mini-label">Inclinazione</span>
                <span class="mini-value">{{ fmtNum(sp?.curva_climatica?.slope) }}</span>
              </div>
              <input type="range" min="-1" max="1" step="0.05" v-model.number="sp.curva_climatica.slope" @input="saveCurveDebounced"/>
            </div>
            <div class="mini-field">
              <div class="mini-head">
                <span class="mini-label">Offset (C)</span>
                <span class="mini-value">{{ fmtNum(sp?.curva_climatica?.offset) }}</span>
              </div>
              <input type="range" min="-10" max="10" step="0.5" v-model.number="sp.curva_climatica.offset" @input="saveCurveDebounced"/>
            </div>
          </div>
          <div class="actions">
            <button class="ghost" @click="save">Salva curva</button>
          </div>
        </div>

        <div v-if="d" class="card inner">
          <div class="row"><strong>Schema impianto (live)</strong></div>
          <div class="muted">Flussi evidenziati in tempo reale.</div>
          <div class="diagram diagram-photo" :style="{ backgroundImage: `url(${schemaImg})` }">
            <svg class="diagram-overlay" viewBox="0 0 1347 864" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Schema impianto e-EnergyMind">
              <defs>
                <radialGradient id="dotGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stop-color="#7ff6e6" stop-opacity="1"/>
                  <stop offset="100%" stop-color="#7ff6e6" stop-opacity="0"/>
                </radialGradient>
              </defs>

              <!-- Dots animati sui punti chiave (senza nuove linee sopra i componenti) -->
              <circle cx="1045" cy="205" r="10" class="pulse" :class="flowSolarToPuffer ? 'pulse-on' : ''"/>
              <circle cx="1180" cy="260" r="10" class="pulse" :class="flowSolarToAcs ? 'pulse-on' : ''"/>
              <circle cx="955" cy="360" r="10" class="pulse" :class="flowPufferToAcs ? 'pulse-on' : ''"/>
              <circle cx="835" cy="360" r="10" class="pulse" :class="flowPufferToImpianto ? 'pulse-on' : ''"/>
              <circle cx="380" cy="250" r="10" class="pulse" :class="flowPufferToLab ? 'pulse-on' : ''"/>
              <circle cx="850" cy="520" r="10" class="pulse" :class="flowVolanoToPuffer ? 'pulse-on' : ''"/>
              <circle cx="980" cy="520" r="10" class="pulse" :class="flowCaldaiaToPuffer ? 'pulse-on' : ''"/>
              <circle cx="900" cy="600" r="10" class="pulse" :class="flowVolanoToAcs ? 'pulse-on' : ''"/>
              <circle cx="300" cy="620" r="10" class="pulse" :class="flowPdcToVolano ? 'pulse-on' : ''"/>
              <circle cx="260" cy="470" r="10" class="pulse" :class="flowPdcToVolano ? 'pulse-on' : ''"/>
              <circle cx="250" cy="140" r="10" class="pulse" :class="flowVolanoToImpianto ? 'pulse-on' : ''"/>

              <!-- Linea animata: Volano -> ACS -->
              <path d="M420 650 H820 V520 H1140" class="tube" :class="flowVolanoToAcs ? 'tube-on' : ''"/>
            </svg>
          </div>
          <div class="legend">
            <span class="legend-item"><span class="legend-dot on"></span> Flusso attivo</span>
            <span class="legend-item"><span class="legend-dot"></span> Flusso inattivo</span>
          </div>
        </div>

        <div class="actions">
          <button @click="refresh">Aggiorna</button>
        </div>

        <div class="card inner">
          <div class="row"><strong>Ultime azioni</strong></div>
          <div v-if="actions.length === 0" class="muted">Nessuna azione registrata.</div>
          <div v-else>
            <div v-for="(line, idx) in actions.slice().reverse()" :key="`a-${idx}`" class="muted">{{ line }}</div>
          </div>
        </div>
      </section>

      <section v-else class="card">
        <h2>Admin (v0.2)</h2>
        <p class="muted">Setpoint interni e mapping e-manager.</p>
        <div class="statusline">
          <span class="muted">v{{ status?.version || '-' }}</span>
          <span class="muted">mode: {{ status?.runtime_mode || '-' }}</span>
          <span class="badge" :class="status?.ha_connected ? 'ok' : 'off'">
            {{ status?.ha_connected ? 'Online' : 'Offline' }}
          </span>
          <span class="muted">HA</span>
          <span class="muted">Ultimo aggiornamento: {{ lastUpdate ? lastUpdate.toLocaleTimeString() : '-' }}</span>
        </div>

        <div class="form">
          <h3 class="section">Configurazione</h3>
        </div>

        <div v-if="sp" class="form setpoint-grid">
          <h3 class="section">Setpoint</h3>
          <div class="set-section">
            <div class="section-title">Runtime</div>
            <div class="field">
              <label>Runtime mode</label>
              <select v-model="sp.runtime.mode" @change="confirmMode">
                <option value="dry-run">dry-run</option>
                <option value="live">live</option>
              </select>
              <div class="help">dry-run = nessun comando agli attuatori. live = comandi reali su HA.</div>
            </div>
            <div class="field">
              <label>Polling UI (ms)</label>
              <input type="number" min="500" step="500" v-model.number="sp.runtime.ui_poll_ms"/>
              <div class="help">Intervallo aggiornamento UI. Non influisce sulla logica interna.</div>
            </div>
          </div>

          <div class="set-section">
            <div class="section-title">ACS</div>
            <div class="field"><label>ACS setpoint (C)</label><input type="number" step="0.5" v-model.number="sp.acs.setpoint_c"/><div class="help">Target acqua sanitaria. Sotto questo valore il sistema cerca una sorgente.</div></div>
            <div class="field"><label>ACS MAX (C)</label><input type="number" step="0.5" v-model.number="sp.acs.max_c"/><div class="help">Sicurezza: sopra questo valore blocca il riscaldamento ACS.</div></div>
          </div>

          <div class="set-section">
            <div class="section-title">Volano</div>
            <div class="field"><label>Volano margine (C)</label><input type="number" step="0.5" v-model.number="sp.volano.margin_c"/><div class="help">Margine usato per decisioni volano (buffer).</div></div>
            <div class="field"><label>Volano MAX (C)</label><input type="number" step="0.5" v-model.number="sp.volano.max_c"/><div class="help">Sicurezza: sopra questo valore non carica volano.</div></div>
            <div class="field"><label>Volano min → ACS (°C)</label><input type="number" step="0.5" v-model.number="sp.volano.min_to_acs_c"/><div class="help">Minimo volano per poter scaldare ACS.</div></div>
            <div class="field"><label>Volano isteresi → ACS (°C)</label><input type="number" step="0.5" v-model.number="sp.volano.hyst_to_acs_c"/><div class="help">Isteresi per evitare ON/OFF continui su ACS.</div></div>
            <div class="field"><label>Δ Start Volano → ACS (C)</label><input type="number" step="0.5" v-model.number="sp.volano.delta_to_acs_start_c"/><div class="help">Differenza T_VOL - T_ACS per avviare.</div></div>
            <div class="field"><label>Δ Hold Volano → ACS (C)</label><input type="number" step="0.5" v-model.number="sp.volano.delta_to_acs_hold_c"/><div class="help">Differenza per mantenere attivo il flusso.</div></div>
            <div class="field"><label>Δ Start Volano → Puffer (C)</label><input type="number" step="0.5" v-model.number="sp.volano.delta_to_puffer_start_c"/><div class="help">Differenza T_VOL - T_PUF per avviare.</div></div>
            <div class="field"><label>Δ Hold Volano → Puffer (C)</label><input type="number" step="0.5" v-model.number="sp.volano.delta_to_puffer_hold_c"/><div class="help">Differenza per mantenere attivo il flusso.</div></div>
            <div class="field"><label>Volano min → Puffer (°C)</label><input type="number" step="0.5" v-model.number="sp.volano.min_to_puffer_c"/><div class="help">Minimo volano per poter caricare puffer.</div></div>
            <div class="field"><label>Volano isteresi → Puffer (°C)</label><input type="number" step="0.5" v-model.number="sp.volano.hyst_to_puffer_c"/><div class="help">Isteresi minimo volano per evitare ON/OFF.</div></div>
            <div class="field">
              <label>Sequenza Volano → ACS (valvola + pompa)</label>
              <div class="row2">
                <div class="mini-field">
                  <span class="mini-label">Start (s)</span>
                  <input type="number" step="1" v-model.number="sp.timers.volano_to_acs_start_s"/>
                </div>
                <div class="mini-field">
                  <span class="mini-label">Stop (s)</span>
                  <input type="number" step="1" v-model.number="sp.timers.volano_to_acs_stop_s"/>
                </div>
              </div>
              <div class="help">Prima apre la valvola, poi parte la pompa. In stop: valvola OFF, pompa OFF con ritardo.</div>
            </div>
            <div class="field">
              <label>Sequenza Volano → Puffer (valvola + pompa)</label>
              <div class="row2">
                <div class="mini-field">
                  <span class="mini-label">Start (s)</span>
                  <input type="number" step="1" v-model.number="sp.timers.volano_to_puffer_start_s"/>
                </div>
                <div class="mini-field">
                  <span class="mini-label">Stop (s)</span>
                  <input type="number" step="1" v-model.number="sp.timers.volano_to_puffer_stop_s"/>
                </div>
              </div>
              <div class="help">Valvola ON → ritardo → pompa ON. In stop: valvola OFF → ritardo → pompa OFF.</div>
            </div>
          </div>

          <div class="set-section">
            <div class="section-title">Puffer</div>
            <div class="field"><label>Puffer setpoint (C)</label><input type="number" step="0.5" v-model.number="sp.puffer.setpoint_c"/><div class="help">Target puffer quando ACS e ok.</div></div>
            <div class="field"><label>Puffer min → ACS (°C)</label><input type="number" step="0.5" v-model.number="sp.puffer.min_to_acs_c"/><div class="help">Minimo puffer per poter scaldare ACS.</div></div>
            <div class="field"><label>Puffer isteresi → ACS (°C)</label><input type="number" step="0.5" v-model.number="sp.puffer.hyst_to_acs_c"/><div class="help">Isteresi per evitare ON/OFF continui su ACS.</div></div>
            <div class="field"><label>Δ Start Puffer → ACS (C)</label><input type="number" step="0.5" v-model.number="sp.puffer.delta_to_acs_start_c"/><div class="help">Differenza T_PUF - T_ACS per avviare.</div></div>
            <div class="field"><label>Δ Hold Puffer → ACS (C)</label><input type="number" step="0.5" v-model.number="sp.puffer.delta_to_acs_hold_c"/><div class="help">Differenza per mantenere attivo il flusso.</div></div>
          </div>

          <div class="set-section">
            <div class="section-title">Miscelatrice</div>
            <div class="field"><label>SP mandata (C)</label><input type="number" step="0.5" v-model.number="sp.miscelatrice.setpoint_c"/><div class="help">Setpoint mandata per la miscelatrice.</div></div>
            <div class="field"><label>Isteresi (C)</label><input type="number" step="0.1" v-model.number="sp.miscelatrice.hyst_c"/><div class="help">Banda di tolleranza intorno al setpoint.</div></div>
            <div class="field"><label>Kp base (sec/°C)</label><input type="number" step="0.1" v-model.number="sp.miscelatrice.kp"/><div class="help">Quanto dura l'impulso per ogni grado di errore.</div></div>
            <div class="field"><label>Impulso min (s)</label><input type="number" step="0.1" v-model.number="sp.miscelatrice.min_imp_s"/><div class="help">Durata minima impulso alza/abbassa.</div></div>
            <div class="field"><label>Impulso max (s)</label><input type="number" step="0.1" v-model.number="sp.miscelatrice.max_imp_s"/><div class="help">Durata massima impulso alza/abbassa.</div></div>
            <div class="field"><label>Pausa dopo impulso (s)</label><input type="number" step="0.1" v-model.number="sp.miscelatrice.pause_s"/><div class="help">Attesa tra un impulso e il successivo.</div></div>
            <div class="field"><label>ΔT ref (°C)</label><input type="number" step="0.5" v-model.number="sp.miscelatrice.dt_ref_c"/><div class="help">Delta mandata/ritorno di riferimento per Kp eff.</div></div>
            <div class="field"><label>ΔT fattore min</label><input type="number" step="0.1" v-model.number="sp.miscelatrice.dt_min_factor"/><div class="help">Limite minimo del fattore Kp eff.</div></div>
            <div class="field"><label>ΔT fattore max</label><input type="number" step="0.1" v-model.number="sp.miscelatrice.dt_max_factor"/><div class="help">Limite massimo del fattore Kp eff.</div></div>
            <div class="field"><label>Forza impulso (s)</label><input type="number" step="0.1" v-model.number="sp.miscelatrice.force_impulse_s"/><div class="help">Impulso extra per evitare stallo.</div></div>
          </div>

          <div class="set-section">
            <div class="section-title">Curva climatica</div>
            <div class="field"><label>Punti X (T esterna)</label><input type="text" v-model="curveXText" @blur="applyCurveText" @focus="onFocus"/><div class="help">Lista temperature esterne, separate da virgola.</div></div>
            <div class="field"><label>Punti Y (Mandata)</label><input type="text" v-model="curveYText" @blur="applyCurveText" @focus="onFocus"/><div class="help">Lista mandata corrispondente, stessa lunghezza di X.</div></div>
            <div class="field"><label>Inclinazione</label><input type="number" step="0.05" v-model.number="sp.curva_climatica.slope"/><div class="help">Regola la pendenza della curva (0 = base).</div></div>
            <div class="field"><label>Offset (C)</label><input type="number" step="0.5" v-model.number="sp.curva_climatica.offset"/><div class="help">Sposta tutta la curva su/giu.</div></div>
            <div class="field"><label>Min mandata (C)</label><input type="number" step="0.5" v-model.number="sp.curva_climatica.min_c"/><div class="help">Limite minimo mandata.</div></div>
            <div class="field"><label>Max mandata (C)</label><input type="number" step="0.5" v-model.number="sp.curva_climatica.max_c"/><div class="help">Limite massimo mandata.</div></div>
          </div>

          <div class="set-section">
            <div class="section-title">Resistenze</div>
            <div class="field"><label>Soglia OFF resistenze (W)</label><input type="number" step="1" v-model.number="sp.resistance.off_threshold_w"/><div class="help">Sotto o uguale a questa soglia, le resistenze scendono a 0.</div></div>
            <div class="field"><label>Off-delay resistenze (s)</label><input type="number" step="1" v-model.number="sp.resistance.off_delay_s"/><div class="help">Ritardo prima di spegnere le resistenze.</div></div>
            <div class="field"><label>Delay salita step (s)</label><input type="number" step="1" v-model.number="sp.resistance.step_up_delay_s"/><div class="help">Ritardo tra step 1→2 e 2→3.</div></div>
            <div class="field">
              <label>Soglie export (W) [1/2/3]</label>
              <div class="row3">
                <input type="number" v-model.number="sp.resistance.thresholds_w[0]"/>
                <input type="number" v-model.number="sp.resistance.thresholds_w[1]"/>
                <input type="number" v-model.number="sp.resistance.thresholds_w[2]"/>
              </div>
              <div class="help">Soglie potenza FV per step 1/2/3 resistenze.</div>
            </div>
          </div>

          <div class="set-section">
            <div class="section-title">Impianto (Zone)</div>
            <div class="field">
              <label>Zone PT</label>
              <div class="list">
                <div v-for="(z, i) in sp.impianto.zones_pt" :key="`pt-${i}`" class="list-row">
                  <input type="text" v-model="sp.impianto.zones_pt[i]" placeholder="climate.pt_1"/>
                  <button class="ghost" @click="removeZone('zones_pt', i)">Rimuovi</button>
                </div>
            <div class="help">Elenco termostati PT (climate.*).</div>
                <button class="ghost" @click="addZone('zones_pt')">+ Aggiungi</button>
              </div>
            </div>
            <div class="field">
              <label>Zone 1P</label>
              <div class="list">
                <div v-for="(z, i) in sp.impianto.zones_p1" :key="`p1-${i}`" class="list-row">
                  <input type="text" v-model="sp.impianto.zones_p1[i]" placeholder="climate.p1_1"/>
                  <button class="ghost" @click="removeZone('zones_p1', i)">Rimuovi</button>
                </div>
            <div class="help">Elenco termostati 1P.</div>
                <button class="ghost" @click="addZone('zones_p1')">+ Aggiungi</button>
              </div>
            </div>
            <div class="field">
              <label>Zone Mansarda</label>
              <div class="list">
                <div v-for="(z, i) in sp.impianto.zones_mans" :key="`mans-${i}`" class="list-row">
                  <input type="text" v-model="sp.impianto.zones_mans[i]" placeholder="climate.jolly"/>
                  <button class="ghost" @click="removeZone('zones_mans', i)">Rimuovi</button>
                </div>
            <div class="help">Elenco termostati mansarda (usano valvola R3).</div>
                <button class="ghost" @click="addZone('zones_mans')">+ Aggiungi</button>
              </div>
            </div>
            <div class="field">
              <label>Zone Lab</label>
              <div class="list">
                <div v-for="(z, i) in sp.impianto.zones_lab" :key="`lab-${i}`" class="list-row">
                  <input type="text" v-model="sp.impianto.zones_lab[i]" placeholder="climate.lab"/>
                  <button class="ghost" @click="removeZone('zones_lab', i)">Rimuovi</button>
                </div>
            <div class="help">Elenco termostati laboratorio.</div>
                <button class="ghost" @click="addZone('zones_lab')">+ Aggiungi</button>
              </div>
            </div>
            <div class="field"><label>Zona Scala (singolo)</label><input type="text" v-model="sp.impianto.zone_scala" placeholder="climate.scala"/></div>
            <div class="help">Termostato scala, se presente.</div>
            <div class="field">
              <label>Cooling bloccato</label>
              <div class="list">
                <div v-for="(z, i) in sp.impianto.cooling_blocked" :key="`cool-${i}`" class="list-row">
                  <input type="text" v-model="sp.impianto.cooling_blocked[i]" placeholder="climate.radiatori_1"/>
                  <button class="ghost" @click="removeZone('cooling_blocked', i)">Rimuovi</button>
                </div>
            <div class="help">Termostati che non devono attivare raffrescamento.</div>
                <button class="ghost" @click="addZone('cooling_blocked')">+ Aggiungi</button>
              </div>
            </div>
            <div class="field"><label>Volano min (°C)</label><input type="number" step="0.5" v-model.number="sp.impianto.volano_min_c"/><div class="help">Minimo volano per abilitare impianto riscaldamento.</div></div>
            <div class="field"><label>Volano isteresi (°C)</label><input type="number" step="0.5" v-model.number="sp.impianto.volano_hyst_c"/><div class="help">Isteresi volano per impianto.</div></div>
            <div class="field"><label>Puffer min (°C)</label><input type="number" step="0.5" v-model.number="sp.impianto.puffer_min_c"/><div class="help">Minimo puffer per abilitare impianto riscaldamento.</div></div>
            <div class="field"><label>Puffer isteresi (°C)</label><input type="number" step="0.5" v-model.number="sp.impianto.puffer_hyst_c"/><div class="help">Isteresi puffer per impianto.</div></div>
            <div class="field"><label>Ritardo avvio pompa (s)</label><input type="number" step="1" v-model.number="sp.impianto.pump_start_delay_s"/><div class="help">Ritardo avvio pompa impianto.</div></div>
            <div class="field"><label>Ritardo stop pompa (s)</label><input type="number" step="1" v-model.number="sp.impianto.pump_stop_delay_s"/><div class="help">Ritardo stop pompa impianto.</div></div>
            <div class="field"><label>Stagione</label>
              <select v-model="sp.impianto.season_mode">
                <option value="winter">Inverno</option>
                <option value="summer">Estate</option>
              </select>
              <div class="help">In estate blocca riscaldamento.</div>
            </div>
            <div class="help">Mansarda e 1P condividono la stessa valvola (R3).</div>
          </div>

          <div class="set-section">
            <div class="section-title">Caldaia Gas Emergenza Riscaldamento</div>
            <div class="field">
              <label>Zone gas emergenza</label>
              <div class="list">
                <div v-for="(z, i) in sp.gas_emergenza.zones" :key="`gas-${i}`" class="list-row">
                  <input type="text" v-model="sp.gas_emergenza.zones[i]" placeholder="climate.pt_1"/>
                  <button class="ghost" @click="removeGasZone(i)">Rimuovi</button>
                </div>
                <div class="help">Termostati da attivare in emergenza gas.</div>
                <button class="ghost" @click="addGasZone">+ Aggiungi</button>
              </div>
            </div>
            <div class="field"><label>Volano min gas (°C)</label><input type="number" step="0.5" v-model.number="sp.gas_emergenza.volano_min_c"/><div class="help">Soglia dedicata: sopra questo valore il gas si spegne.</div></div>
            <div class="field"><label>Volano isteresi gas (°C)</label><input type="number" step="0.5" v-model.number="sp.gas_emergenza.volano_hyst_c"/><div class="help">Isteresi volano per evitare ON/OFF gas.</div></div>
            <div class="field"><label>Puffer min gas (°C)</label><input type="number" step="0.5" v-model.number="sp.gas_emergenza.puffer_min_c"/><div class="help">Soglia dedicata: sopra questo valore il gas si spegne.</div></div>
            <div class="field"><label>Puffer isteresi gas (°C)</label><input type="number" step="0.5" v-model.number="sp.gas_emergenza.puffer_hyst_c"/><div class="help">Isteresi puffer per evitare ON/OFF gas.</div></div>
          </div>

          <div class="set-section">
            <div class="section-title">Caldaia Legna</div>
            <div class="field">
              <label>Temp min alimentazione (Â°C)</label>
              <input type="number" step="0.5" v-model.number="sp.caldaia_legna.temp_min_alim_c"/>
              <div class="help">Sotto questa soglia, dopo il timer, l'alimentazione si disattiva.</div>
            </div>
            <div class="field">
              <label>Isteresi alimentazione (Â°C)</label>
              <input type="number" step="0.5" v-model.number="sp.caldaia_legna.temp_min_alim_hyst_c"/>
              <div class="help">Evita ON/OFF rapido vicino alla soglia.</div>
            </div>
            <div class="field">
              <label>Timer controllo (min)</label>
              <input type="number" step="1" v-model.number="caldaiaLegnaStartupMin"/>
              <div class="help">Tempo di avvio prima del controllo temperatura.</div>
            </div>
            <div class="field">
              <label>SP Puffer alto (Â°C)</label>
              <input type="number" step="0.5" v-model.number="sp.caldaia_legna.puffer_alto_sp_c"/>
              <div class="help">Sopra questa temperatura, TA caldaia legna OFF.</div>
            </div>
            <div class="field">
              <label>Isteresi TA Puffer (Â°C)</label>
              <input type="number" step="0.5" v-model.number="sp.caldaia_legna.puffer_alto_hyst_c"/>
              <div class="help">Isteresi per evitare ON/OFF TA vicino al setpoint.</div>
            </div>
          </div>

          <div class="set-section">
            <div class="section-title">Solare</div>
            <div class="field">
              <label>Modalità</label>
              <select v-model="sp.solare.mode">
                <option value="auto">auto (sun.sun)</option>
                <option value="night">notte fissa</option>
              </select>
            </div>
            <div class="field">
              <label>FV entity (W) per giorno/notte</label>
              <input type="text" v-model="sp.solare.pv_entity" placeholder="sensor.zcs_easas_1_activepower_pv_ext"/>
              <div class="help">Sensore FV usato per decidere giorno/notte.</div>
            </div>
            <div class="field"><label>Soglia giorno FV (W)</label><input type="number" step="10" v-model.number="sp.solare.pv_day_w"/><div class="help">Se FV > soglia allora giorno.</div></div>
            <div class="field"><label>Soglia notte FV (W)</label><input type="number" step="10" v-model.number="sp.solare.pv_night_w"/><div class="help">Se FV &lt; soglia allora notte.</div></div>
            <div class="field"><label>Debounce FV (s)</label><input type="number" step="10" v-model.number="sp.solare.pv_debounce_s"/><div class="help">Tempo minimo per cambiare stato giorno/notte.</div></div>
            <div class="field"><label>Δ Start Solare → ACS (C)</label><input type="number" step="0.5" v-model.number="sp.solare.delta_on_c"/></div>
            <div class="field"><label>Δ Hold Solare → ACS (C)</label><input type="number" step="0.5" v-model.number="sp.solare.delta_hold_c"/></div>
            <div class="field"><label>Solare MAX (C)</label><input type="number" step="0.5" v-model.number="sp.solare.max_c"/><div class="help">Sicurezza: sopra questo valore stop solare.</div></div>
            <div class="help">In NOTTE: R8 ON e R9 OFF. R18/R19 restano manuali con interblocco.</div>
          </div>

        </div>

        <div class="form">
          <h3 class="section">Moduli (Admin)</h3>
          <div class="row3">
            <button class="ghost toggle" :class="moduleClass('resistenze_volano')" @click="toggleModule('resistenze_volano')">
              Resistenze Volano: {{ modules.resistenze_volano ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('volano_to_acs')" @click="toggleModule('volano_to_acs')">
              Volano → ACS: {{ modules.volano_to_acs ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('volano_to_puffer')" @click="toggleModule('volano_to_puffer')">
              Volano → Puffer: {{ modules.volano_to_puffer ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('puffer_to_acs')" @click="toggleModule('puffer_to_acs')">
              Puffer → ACS: {{ modules.puffer_to_acs ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('impianto')" @click="toggleModule('impianto')">
              Impianto Riscaldamento: {{ modules.impianto ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('gas_emergenza')" @click="toggleModule('gas_emergenza')">
              Caldaia Gas Emergenza Riscaldamento: {{ modules.gas_emergenza ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('caldaia_legna')" @click="toggleModule('caldaia_legna')">
              Caldaia Legna: {{ modules.caldaia_legna ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('solare')" @click="toggleModule('solare')">
              Solare: {{ modules.solare ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('miscelatrice')" @click="toggleModule('miscelatrice')">
              Miscelatrice: {{ modules.miscelatrice ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('curva_climatica')" @click="toggleModule('curva_climatica')">
              Curva climatica: {{ modules.curva_climatica ? 'ON' : 'OFF' }}
            </button>
            <button class="ghost toggle" :class="moduleClass('pdc')" @click="toggleModule('pdc')">
              PDC: {{ modules.pdc ? 'ON' : 'OFF' }}
            </button>
          </div>
        </div>

        <details class="form" open>
          <summary class="section">Sensori da e-manager</summary>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_acs_alto?.attributes?.icon)" :class="mdiClass(ent?.t_acs_alto?.attributes?.icon)"></i>
              T_ACS Alto (ACS)
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_acs_alto?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_acs_alto?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_acs_alto.entity_id"
                       placeholder="sensor.acs_alto"
                       @input="dirtyEnt.t_acs_alto = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_acs_alto"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_acs_medio?.attributes?.icon)" :class="mdiClass(ent?.t_acs_medio?.attributes?.icon)"></i>
              T_ACS Medio (ACS)
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_acs_medio?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_acs_medio?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_acs_medio.entity_id"
                       placeholder="sensor.acs_medio"
                       @input="dirtyEnt.t_acs_medio = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_acs_medio"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_acs_basso?.attributes?.icon)" :class="mdiClass(ent?.t_acs_basso?.attributes?.icon)"></i>
              T_ACS Basso (ACS)
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_acs_basso?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_acs_basso?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_acs_basso.entity_id"
                       placeholder="sensor.acs_basso"
                       @input="dirtyEnt.t_acs_basso = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_acs_basso"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_puffer_alto?.attributes?.icon)" :class="mdiClass(ent?.t_puffer_alto?.attributes?.icon)"></i>
              T_Puffer Alto
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_puffer_alto?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_puffer_alto?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_puffer_alto.entity_id"
                       placeholder="sensor.puffer_alto"
                       @input="dirtyEnt.t_puffer_alto = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_puffer_alto"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_puffer_medio?.attributes?.icon)" :class="mdiClass(ent?.t_puffer_medio?.attributes?.icon)"></i>
              T_Puffer Medio
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_puffer_medio?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_puffer_medio?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_puffer_medio.entity_id"
                       placeholder="sensor.puffer_medio"
                       @input="dirtyEnt.t_puffer_medio = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_puffer_medio"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_puffer_basso?.attributes?.icon)" :class="mdiClass(ent?.t_puffer_basso?.attributes?.icon)"></i>
              T_Puffer Basso
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_puffer_basso?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_puffer_basso?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_puffer_basso.entity_id"
                       placeholder="sensor.puffer_basso"
                       @input="dirtyEnt.t_puffer_basso = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_puffer_basso"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_volano_alto?.attributes?.icon)" :class="mdiClass(ent?.t_volano_alto?.attributes?.icon)"></i>
              T_Volano Alto
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_volano_alto?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_volano_alto?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_volano_alto.entity_id"
                       placeholder="sensor.volano_alto"
                       @input="dirtyEnt.t_volano_alto = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_volano_alto"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_volano_basso?.attributes?.icon)" :class="mdiClass(ent?.t_volano_basso?.attributes?.icon)"></i>
              T_Volano Basso
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_volano_basso?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_volano_basso?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_volano_basso.entity_id"
                       placeholder="sensor.volano_basso"
                       @input="dirtyEnt.t_volano_basso = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_volano_basso"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_mandata_caldaia_legna?.attributes?.icon)" :class="mdiClass(ent?.t_mandata_caldaia_legna?.attributes?.icon)"></i>
              T Mandata Caldaia Legna
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_mandata_caldaia_legna?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_mandata_caldaia_legna?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_mandata_caldaia_legna.entity_id"
                       placeholder="sensor.esp32_s3_ct_temp_mandata_caldaia_legna"
                       @input="dirtyEnt.t_mandata_caldaia_legna = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_mandata_caldaia_legna"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_ritorno_caldaia_legna?.attributes?.icon)" :class="mdiClass(ent?.t_ritorno_caldaia_legna?.attributes?.icon)"></i>
              T Ritorno Caldaia Legna
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_ritorno_caldaia_legna?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_ritorno_caldaia_legna?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_ritorno_caldaia_legna.entity_id"
                       placeholder="sensor.esp32_s3_ct_temp_ritorno_caldaia_legna"
                       @input="dirtyEnt.t_ritorno_caldaia_legna = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_ritorno_caldaia_legna"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_caldaia_legna?.attributes?.icon)" :class="mdiClass(ent?.t_caldaia_legna?.attributes?.icon)"></i>
              T Caldaia Legna
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_caldaia_legna?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_caldaia_legna?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_caldaia_legna.entity_id"
                       placeholder="sensor.esp32_s3_ct_temp_caldaia_legna"
                       @input="dirtyEnt.t_caldaia_legna = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_caldaia_legna"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_solare_mandata?.attributes?.icon)" :class="mdiClass(ent?.t_solare_mandata?.attributes?.icon)"></i>
              T_Solare mandata
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_solare_mandata?.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
                <input type="text"
                       :class="isFilled(ent?.t_solare_mandata?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_solare_mandata.entity_id"
                       placeholder="sensor.solar_mandata"
                       @input="dirtyEnt.t_solare_mandata = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_solare_mandata"/> Storico</label></div>
            </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.t_esterna?.attributes?.icon)" :class="mdiClass(ent?.t_esterna?.attributes?.icon)"></i>
              T esterna
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_esterna?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.t_esterna?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_esterna.entity_id"
                       placeholder="sensor.temp_esterna"
                       @input="dirtyEnt.t_esterna = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_esterna"/> Storico</label></div>
            </div>
          </div>
          </div>
          <div class="subsection">Collettore solare</div>
          <div class="field">
            <label>Codice di stato</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_status_code?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_status_code?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_status_code.entity_id"
                       placeholder="sensor.solar_status_code"
                       @input="dirtyEnt.collettore_status_code = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
          </div>
          <div class="field">
            <label>Stato</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_status?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_status?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_status.entity_id"
                       placeholder="sensor.solar_status"
                       @input="dirtyEnt.collettore_status = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
          </div>
          <div class="field">
            <label>Data e Ora</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_datetime?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_datetime?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_datetime.entity_id"
                       placeholder="sensor.solar_datetime"
                       @input="dirtyEnt.collettore_datetime = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
          </div>
          <div class="field">
            <label>Energia solare (giorno)</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_energy_day_kwh?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_energy_day_kwh?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_energy_day_kwh.entity_id"
                       placeholder="sensor.solar_energy_day"
                       @input="dirtyEnt.collettore_energy_day_kwh = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
            <div class="history-inline"><label><input type="checkbox" v-model="sp.history.collettore_energy_day_kwh"/> Storico</label></div>
          </div>
          <div class="field">
            <label>Energia solare (totale)</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_energy_total_kwh?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_energy_total_kwh?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_energy_total_kwh.entity_id"
                       placeholder="sensor.solar_energy_total"
                       @input="dirtyEnt.collettore_energy_total_kwh = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
            <div class="history-inline"><label><input type="checkbox" v-model="sp.history.collettore_energy_total_kwh"/> Storico</label></div>
          </div>
          <div class="field">
            <label>Portata (L/min)</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_flow_lmin?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_flow_lmin?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_flow_lmin.entity_id"
                       placeholder="sensor.solar_flow_lmin"
                       @input="dirtyEnt.collettore_flow_lmin = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
            <div class="history-inline"><label><input type="checkbox" v-model="sp.history.collettore_flow_lmin"/> Storico</label></div>
          </div>
          <div class="field">
            <label>PWM Pompa</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_pwm_pct?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_pwm_pct?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_pwm_pct.entity_id"
                       placeholder="sensor.solar_pwm"
                       @input="dirtyEnt.collettore_pwm_pct = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
            <div class="history-inline"><label><input type="checkbox" v-model="sp.history.collettore_pwm_pct"/> Storico</label></div>
          </div>
          <div class="field">
            <label>Stato 2</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_status2?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_status2?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_status2.entity_id"
                       placeholder="sensor.solar_status_2"
                       @input="dirtyEnt.collettore_status2 = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
          </div>
          <div class="field">
            <label>Temperatura esterna (solare)</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_temp_esterna?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_temp_esterna?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_temp_esterna.entity_id"
                       placeholder="sensor.solar_temp_esterna"
                       @input="dirtyEnt.collettore_temp_esterna = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
            <div class="history-inline"><label><input type="checkbox" v-model="sp.history.collettore_temp_esterna"/> Storico</label></div>
          </div>
          <div class="field">
            <label>Collettore (TSA1)</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_tsa1?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_tsa1?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_tsa1.entity_id"
                       placeholder="sensor.solar_tsa1"
                       @input="dirtyEnt.collettore_tsa1 = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
            <div class="history-inline"><label><input type="checkbox" v-model="sp.history.collettore_tsa1"/> Storico</label></div>
          </div>
          <div class="field">
            <label>Ritorno solare (TSE)</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_tse?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_tse?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_tse.entity_id"
                       placeholder="sensor.solar_tse"
                       @input="dirtyEnt.collettore_tse = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
            <div class="history-inline"><label><input type="checkbox" v-model="sp.history.collettore_tse"/> Storico</label></div>
          </div>
          <div class="field">
            <label>Mandata solare (TSV)</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_tsv?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_tsv?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_tsv.entity_id"
                       placeholder="sensor.solar_tsv"
                       @input="dirtyEnt.collettore_tsv = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
            <div class="history-inline"><label><input type="checkbox" v-model="sp.history.collettore_tsv"/> Storico</label></div>
          </div>
          <div class="field">
            <label>Serbatoio superiore metà (TWU)</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.collettore_twu?.entity_id) ? 'logic-ok' : 'logic-no'">?</span>
                <input type="text"
                       :class="isFilled(ent?.collettore_twu?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.collettore_twu.entity_id"
                       placeholder="sensor.solar_twu"
                       @input="dirtyEnt.collettore_twu = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
            <div class="history-inline"><label><input type="checkbox" v-model="sp.history.collettore_twu"/> Storico</label></div>
          </div>
          <div class="field">
            <label>
              <i v-if="mdiClass(ent?.grid_export_w?.attributes?.icon)" :class="mdiClass(ent?.grid_export_w?.attributes?.icon)"></i>
              Export rete (W)
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.grid_export_w?.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
                <input type="text"
                       :class="isFilled(ent?.grid_export_w?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.grid_export_w.entity_id"
                       placeholder="sensor.grid_export_w"
                       @input="dirtyEnt.grid_export_w = true"
                       @focus="onFocus" @blur="onBlur"/>
            </div>
          </div>

          <div class="subsection">Miscelatrice</div>
          <div class="field">
            <label>T mandata miscelata</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_mandata_miscelata?.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
                <input type="text"
                       :class="isFilled(ent?.t_mandata_miscelata?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_mandata_miscelata.entity_id"
                       placeholder="sensor.mandata_miscelata"
                       @input="dirtyEnt.t_mandata_miscelata = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_mandata_miscelata"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>T ritorno miscelato</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.t_ritorno_miscelato?.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
                <input type="text"
                       :class="isFilled(ent?.t_ritorno_miscelato?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.t_ritorno_miscelato.entity_id"
                       placeholder="sensor.ritorno_miscelato"
                       @input="dirtyEnt.t_ritorno_miscelato = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.t_ritorno_miscelato"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>Setpoint miscelatrice</label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(ent?.miscelatrice_setpoint?.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
                <input type="text"
                       :class="isFilled(ent?.miscelatrice_setpoint?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.miscelatrice_setpoint.entity_id"
                       placeholder="input_number.set_point_valvola_miscelatrice"
                       @input="dirtyEnt.miscelatrice_setpoint = true"
                       @focus="onFocus" @blur="onBlur"/>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.miscelatrice_setpoint"/> Storico</label></div>
            </div>
          </div>
          <div class="subsection">Storici calcolati</div>
          <div class="field">
            <label>Delta Puffer - ACS</label>
            <div class="input-row">
              <span class="logic-dot">?</span>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.delta_puffer_acs" @change="saveHistoryDebounced"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>Delta Volano - ACS</label>
            <div class="input-row">
              <span class="logic-dot">?</span>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.delta_volano_acs" @change="saveHistoryDebounced"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>Delta Volano - Puffer</label>
            <div class="input-row">
              <span class="logic-dot">?</span>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.delta_volano_puffer" @change="saveHistoryDebounced"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>Delta Mandata/Ritorno</label>
            <div class="input-row">
              <span class="logic-dot">?</span>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.delta_mandata_ritorno" @change="saveHistoryDebounced"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>Kp eff</label>
            <div class="input-row">
              <span class="logic-dot">?</span>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.kp_eff" @change="saveHistoryDebounced"/> Storico</label></div>
            </div>
          </div>
          <div class="field">
            <label>Setpoint curva climatica</label>
            <div class="input-row">
              <span class="logic-dot">?</span>
              <div class="history-inline"><label><input type="checkbox" v-model="sp.history.curva_setpoint" @change="saveHistoryDebounced"/> Storico</label></div>
            </div>
          </div>

            <div class="field">
              <label>
                <i v-if="mdiClass(ent?.resistenze_volano_power?.attributes?.icon)" :class="mdiClass(ent?.resistenze_volano_power?.attributes?.icon)"></i>
                Potenza Resistenze Volano (W)
              </label>
              <div class="input-row">
                <span class="logic-dot" :class="isFilled(ent?.resistenze_volano_power?.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
                <input type="text"
                       :class="isFilled(ent?.resistenze_volano_power?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.resistenze_volano_power.entity_id"
                       placeholder="sensor.resistenze_volano_power"
                       @input="dirtyEnt.resistenze_volano_power = true"
                       @focus="onFocus" @blur="onBlur"/>
              </div>
            </div>
            <div class="field">
              <label>
                <i v-if="mdiClass(ent?.resistenze_volano_energy?.attributes?.icon)" :class="mdiClass(ent?.resistenze_volano_energy?.attributes?.icon)"></i>
                Energia Resistenze Volano
              </label>
              <div class="input-row">
                <span class="logic-dot" :class="isFilled(ent?.resistenze_volano_energy?.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
                <input type="text"
                       :class="isFilled(ent?.resistenze_volano_energy?.entity_id) ? 'input-ok' : ''"
                       v-model="ent.resistenze_volano_energy.entity_id"
                       placeholder="sensor.resistenze_volano_energy"
                       @input="dirtyEnt.resistenze_volano_energy = true"
                       @focus="onFocus" @blur="onBlur"/>
              </div>
            </div>
          <div class="actions">
            <button class="ghost" @click="saveEntities">Salva sensori</button>
          </div>
        </details>

        <details class="form" open>
          <summary class="section">Attuatori da e-manager</summary>
          <div class="field">
            <label>Filtro</label>
            <input type="text" v-model="filterAct" placeholder="Cerca R22, PDC, solare..." @focus="onFocus" @blur="onBlur"/>
          </div>
          <div v-for="item in filteredActuators" :key="item.key" class="field">
            <label>
              {{ item.label }}
            </label>
            <div class="input-row">
              <span class="logic-dot" :class="isFilled(act?.[item.key]?.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
              <input type="text"
                     :class="[isFilled(act?.[item.key]?.entity_id) ? 'input-ok' : '', act?.[item.key]?.state === 'on' ? 'input-on' : '']"
                     v-model="act[item.key].entity_id"
                     :placeholder="`switch.${item.key}`"
                     @input="dirtyAct[item.key] = true"
                     @focus="onFocus" @blur="onBlur"/>
            </div>
          </div>
          <div class="actions">
            <button class="ghost" @click="saveActuators">Salva attuatori</button>
          </div>
        </details>

        <div class="actions">
          <button class="ghost" @click="loadAll">Ricarica</button>
        </div>
      </section>
      <div v-if="historyModal.open" class="modal-backdrop" @click.self="closeHistory">
        <div class="modal">
          <div class="modal-head">
            <div class="modal-title">Storico 24h — {{ historyModal.title }}</div>
            <button class="ghost" @click="closeHistory">Chiudi</button>
          </div>
          <div class="modal-body">
            <svg viewBox="0 0 600 220" class="history-chart" role="img" aria-label="Grafico storico">
              <line :x1="historyModal.padL" :y1="historyModal.padT" :x2="historyModal.padL" :y2="historyModal.h - historyModal.padB" class="axis"/>
              <line :x1="historyModal.padL" :y1="historyModal.h - historyModal.padB" :x2="historyModal.w - historyModal.padR" :y2="historyModal.h - historyModal.padB" class="axis"/>
              <g v-for="t in historyModal.yTicks" :key="t.label">
                <line :x1="historyModal.padL - 4" :y1="t.y" :x2="historyModal.padL" :y2="t.y" class="axis"/>
                <text :x="historyModal.padL - 8" :y="t.y + 4" class="axis-label" text-anchor="end">{{ t.label }}</text>
              </g>
              <g v-for="t in historyModal.xTicks" :key="t.label">
                <line :x1="t.x" :y1="historyModal.h - historyModal.padB" :x2="t.x" :y2="historyModal.h - historyModal.padB + 4" class="axis"/>
                <text :x="t.x" :y="historyModal.h - historyModal.padB + 16" class="axis-label" text-anchor="middle">{{ t.label }}</text>
              </g>
              <polyline :points="historyModal.points" class="spark acs"/>
            </svg>
            <div class="legend small">
              <span class="legend-item"><span class="legend-dot acs"></span>{{ historyModal.title }}</span>
              <span class="legend-item muted">Y: °C ({{ historyModal.minY }}–{{ historyModal.maxY }})</span>
              <span class="legend-item muted">X: {{ historyModal.rangeLabel }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="zoneModal.open" class="modal-backdrop" @click.self="closeZone">
        <div class="modal thermo-modal">
          <div class="modal-head">
            <div class="modal-title">{{ zoneModal.title }}</div>
            <button class="ghost" @click="closeZone">Chiudi</button>
          </div>
          <div class="thermo-body">
            <div class="thermo-ring" :style="thermoStyle">
              <div class="thermo-center">
                <div class="thermo-state">{{ hvacLabel(zoneModal.hvac_action) }}</div>
                <div class="thermo-value">{{ fmtNum(zoneModal.setpoint) }}&deg;C</div>
                <div class="thermo-sub">T attuale {{ fmtNum(zoneModal.temperature) }}&deg;C</div>
              </div>
            </div>
            <div class="thermo-controls">
              <button class="thermo-btn" @click="changeZoneSetpoint(-0.5)">−</button>
              <button class="thermo-btn" @click="changeZoneSetpoint(0.5)">+</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import schemaImg from './assets/centrale-termica.png'
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
const tab = ref('user')
const d = ref(null)
const sp = ref(null)
const ent = ref(null)
const act = ref(null)
const status = ref(null)
  let pollTimer = null
  let ws = null
const lastUpdate = ref(null)
const pollMs = ref(3000)
const actions = ref([])
const zones = ref([])
let historySaveTimer = null
let historyReady = false
const history = ref({
  t_acs: [],
  t_acs_alto: [],
  t_acs_medio: [],
  t_acs_basso: [],
  t_puffer: [],
  t_volano: [],
  t_volano_alto: [],
  t_volano_basso: [],
  t_esterna: [],
  collettore_energy_day_kwh: [],
  collettore_energy_total_kwh: [],
  collettore_flow_lmin: [],
  collettore_pwm_pct: [],
  collettore_temp_esterna: [],
  collettore_tsa1: [],
  collettore_tse: [],
  collettore_tsv: [],
  collettore_twu: [],
  curva_setpoint: [],
  t_puffer_alto: [],
  t_puffer_medio: [],
  t_puffer_basso: [],
  t_mandata_miscelata: [],
  t_ritorno_miscelato: [],
  miscelatrice_setpoint: [],
  delta_puffer_acs: [],
  delta_volano_acs: [],
  delta_volano_puffer: [],
  delta_mandata_ritorno: [],
  kp_eff: [],
  export_w: []
})
const curveXText = ref('')
const curveYText = ref('')
let curveSaveTimer = null
const zoneModal = ref({ open: false, entity_id: '', title: '', temperature: 0, setpoint: 0, hvac_action: '' })
const historyModal = ref({ open: false, title: '', points: '', minY: '-', maxY: '-', rangeLabel: '', xTicks: [], yTicks: [], w: 600, h: 220, padL: 40, padR: 10, padT: 10, padB: 20 })
const maxPoints = 60
  const filterAct = ref('')
  const editingCount = ref(0)
  const dirtyEnt = ref({})
  const dirtyAct = ref({})
let focusInHandler = null
let focusOutHandler = null
const modules = ref({
  resistenze_volano: true,
  volano_to_acs: false,
  volano_to_puffer: false,
  puffer_to_acs: false,
  impianto: false,
  solare: false,
  miscelatrice: false,
  curva_climatica: true,
  pdc: false,
  gas_emergenza: false,
  caldaia_legna: false
})
const solareModeInit = ref(false)
const caldaiaLegnaStartupMin = computed({
  get: () => {
    const s = Number(sp.value?.caldaia_legna?.startup_check_s || 0)
    if (!Number.isFinite(s)) return 0
    return Math.round(s / 60)
  },
  set: (v) => {
    if (!sp.value?.caldaia_legna) return
    const n = Number(v)
    sp.value.caldaia_legna.startup_check_s = Number.isFinite(n) ? Math.max(0, Math.round(n * 60)) : 0
  }
})

const actuatorDefs = [
  { key: 'r1_valve_comparto_laboratorio', label: 'R1 Valvola Comparto Laboratorio (riscaldamento)', impl: false },
  { key: 'r2_valve_comparto_mandata_imp_pt', label: 'R2 Valvola Comparto Mandata Imp PT (riscaldamento)', impl: false },
  { key: 'r3_valve_comparto_mandata_imp_m1p', label: 'R3 Valvola Comparto Mandata Imp M+1P (riscaldamento)', impl: false },
  { key: 'r4_valve_impianto_da_puffer', label: 'R4 Valvola Impianto da Puffer', impl: false },
  { key: 'r5_valve_impianto_da_pdc', label: 'R5 Valvola Impianto da PDC', impl: false },
  { key: 'r6_valve_pdc_to_integrazione_acs', label: 'R6 Valvola PDC -> Integrazione ACS', impl: true },
  { key: 'r7_valve_pdc_to_integrazione_puffer', label: 'R7 Valvola PDC -> Integrazione Puffer', impl: true },
  { key: 'r8_valve_solare_notte_low_temp', label: 'R8 Valvola Solare Notte/Low Temp', impl: true },
  { key: 'r9_valve_solare_normal_funz', label: 'R9 Valvola Solare Normal Funz', impl: true },
  { key: 'r10_valve_solare_precedenza_acs', label: 'R10 Valvola Solare Precedenza ACS', impl: true },
  { key: 'r11_pump_mandata_laboratorio', label: 'R11 Pompa Mandata Laboratorio', impl: false },
  { key: 'r12_pump_mandata_piani', label: 'R12 Pompa Mandata Piani', impl: false },
  { key: 'r13_pump_pdc_to_acs_puffer', label: 'R13 Pompa PDC -> ACS/Puffer', impl: true },
  { key: 'r14_pump_puffer_to_acs', label: 'R14 Pompa Puffer -> ACS', impl: true },
  { key: 'r15_pump_caldaia_legna', label: 'R15 Pompa Caldaia Legna -> Puffer', impl: false },
  { key: 'r16_cmd_miscelatrice_alza', label: 'R16 CMD Miscelatrice ALZA', impl: false },
  { key: 'r17_cmd_miscelatrice_abbassa', label: 'R17 CMD Miscelatrice ABBASSA', impl: false },
  { key: 'r18_valve_ritorno_solare_basso', label: 'R18 Valvola Ritorno Solare Basso', impl: true },
  { key: 'r19_valve_ritorno_solare_alto', label: 'R19 Valvola Ritorno Solare Alto', impl: true },
  { key: 'r20_ta_caldaia_legna', label: 'R20 TA Caldaia Legna', impl: false },
  { key: 'r21_libero', label: 'R21 Libero', impl: false },
  { key: 'r22_resistenza_1_volano_pdc', label: 'R22 Resistenza 1 Volano PDC', impl: true },
  { key: 'r23_resistenza_2_volano_pdc', label: 'R23 Resistenza 2 Volano PDC', impl: true },
  { key: 'r24_resistenza_3_volano_pdc', label: 'R24 Resistenza 3 Volano PDC', impl: true },
  { key: 'generale_resistenze_volano_pdc', label: 'R0 Generale Resistenze Volano PDC', impl: true },
  { key: 'r25_comparto_generale_pdc', label: 'R25 Comparto Generale PDC', impl: false },
  { key: 'r26_comparto_pdc1_avvio', label: 'R26 Comparto PDC 1 Avvio', impl: false },
  { key: 'r27_comparto_pdc2_avvio', label: 'R27 Comparto PDC 2 Avvio', impl: false },
  { key: 'r28_scarico_antigelo_mandata_pdc', label: 'R28 Scarico Antigelo Mandata PDC', impl: false },
  { key: 'r29_scarico_antigelo_ritorno_pdc', label: 'R29 Scarico Antigelo Ritorno PDC', impl: false },
  { key: 'r30_alimentazione_caldaia_legna', label: 'R30 Alimentazione Caldaia Legna', impl: false },
  { key: 'gas_boiler_power', label: '220V Caldaia Gas Emergenza Riscaldamento', impl: true },
  { key: 'gas_boiler_ta', label: 'TA Caldaia Gas Emergenza Riscaldamento', impl: true }
]

const isFilled = (v) => (typeof v === 'string' ? v.trim().length > 0 : false)
const filteredActuators = computed(() => {
  const q = filterAct.value.trim().toLowerCase()
  if (!q) return actuatorDefs
  return actuatorDefs.filter(a => (a.label.toLowerCase().includes(q) || a.key.toLowerCase().includes(q)))
})

const fmtTemp = (v) => (Number.isFinite(v) ? `${v.toFixed(1)}°C` : 'n/d')
const fmtDelta = (a, b) => {
  const da = Number(a)
  const db = Number(b)
  if (!Number.isFinite(da) || !Number.isFinite(db)) return 'n/d'
  return `${(da - db).toFixed(1)}C`
}
const fmtW = (v) => (Number.isFinite(v) ? `${Math.round(v)} W` : 'n/d')
const fmtNum = (v) => (Number.isFinite(Number(v)) ? Number(v).toFixed(1) : '-')
const fmtText = (v) => (v === null || v === undefined || v === '' ? '-' : String(v))
const fmtEntity = (e) => {
  if (!e) return 'n/d'
  const raw = e.state
  const unit = e.attributes?.unit_of_measurement || ''
  if (raw === null || raw === undefined) return 'n/d'
  const num = Number(raw)
  if (Number.isFinite(num)) return `${num} ${unit}`.trim()
  return `${raw} ${unit}`.trim()
}
function statsLabel(values, unit){
  if (!values || values.length === 0) return 'n/d'
  const min = Math.min(...values)
  const max = Math.max(...values)
  if (!Number.isFinite(min) || !Number.isFinite(max)) return 'n/d'
  return `${min.toFixed(1)}–${max.toFixed(1)} ${unit}`.trim()
}
const tempStats = computed(() => {
  const vals = []
  vals.push(...(history.value.t_acs_alto || []))
  vals.push(...(history.value.t_puffer_alto || []))
  vals.push(...(history.value.t_volano_alto || []))
  return { label: statsLabel(vals, '°C') }
})
const exportStats = computed(() => {
  const vals = history.value.export_w || []
  if (!vals.length) return { label: 'n/d' }
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  if (!Number.isFinite(min) || !Number.isFinite(max)) return { label: 'n/d' }
  return { label: `${Math.round(min)}–${Math.round(max)} W` }
})
function addZone(key){
  if (!sp.value?.impianto) return
  if (!Array.isArray(sp.value.impianto[key])) sp.value.impianto[key] = []
  sp.value.impianto[key].push('')
}
function removeZone(key, idx){
  if (!sp.value?.impianto) return
  if (!Array.isArray(sp.value.impianto[key])) return
  sp.value.impianto[key].splice(idx, 1)
}
function addGasZone(){
  if (!sp.value?.gas_emergenza) return
  if (!Array.isArray(sp.value.gas_emergenza.zones)) sp.value.gas_emergenza.zones = []
  sp.value.gas_emergenza.zones.push('')
}
function removeGasZone(idx){
  if (!sp.value?.gas_emergenza) return
  if (!Array.isArray(sp.value.gas_emergenza.zones)) return
  sp.value.gas_emergenza.zones.splice(idx, 1)
}
const historyEnabled = (key) => !!sp.value?.history?.[key]
async function openHistory(key, title){
  if (!historyEnabled(key)) return
  const entId = ent.value?.[key]?.entity_id
  let points = []
  if (entId) {
    const r = await fetch(`/api/history?entity_id=${encodeURIComponent(entId)}&hours=24`)
    if (!r.ok) return
    const data = await r.json()
    const items = Array.isArray(data?.items) ? data.items.flat() : []
    for (const st of items){
      const v = Number(st.state)
      if (!Number.isFinite(v)) continue
      const ts = new Date(st.last_changed || st.last_updated || st.last_reported || Date.now()).getTime()
      points.push([ts, v])
    }
    const current = Number(ent.value?.[key]?.state)
    if (Number.isFinite(current)) {
      const now = Date.now()
      const lastTs = points.length ? points[points.length - 1][0] : 0
      if (now - lastTs > 15000) {
        points.push([now, current])
      }
    }
  } else {
    const arr = history.value?.[key] || []
    if (!arr.length) return
    const stepMs = Math.max(1000, Number(pollMs.value || 3000))
    const now = Date.now()
    points = arr.map((v, i) => [now - (arr.length - 1 - i) * stepMs, v])
  }
  if (points.length === 0) return
  const step = Math.max(1, Math.floor(points.length / 200))
  const reduced = points.filter((_, i) => i % step === 0)
  const xs = reduced.map(p => p[0])
  const ys = reduced.map(p => p[1])
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const spanX = Math.max(1, maxX - minX)
  const spanY = Math.max(0.1, maxY - minY)
  const w = 600
  const h = 220
  const padL = 40
  const padR = 10
  const padT = 10
  const padB = 20
  const innerW = w - padL - padR
  const innerH = h - padT - padB
  const pts = reduced.map(([x,y]) => {
    const px = padL + ((x - minX) / spanX) * innerW
    const py = h - padB - ((y - minY) / spanY) * innerH
    return `${px.toFixed(1)},${py.toFixed(1)}`
  }).join(' ')
  const fmtTime = (ts) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const xTicks = [0, 0.25, 0.5, 0.75, 1].map(t => ({
    x: padL + t * innerW,
    label: fmtTime(minX + t * spanX)
  }))
  const yTicks = [0, 0.5, 1].map(t => ({
    y: h - padB - t * innerH,
    label: (minY + t * spanY).toFixed(1)
  }))
  const rangeLabel = entId
    ? `${new Date(minX).toLocaleDateString()} ${fmtTime(minX)} -> ${fmtTime(maxX)}`
    : `ultimo ~${Math.round((maxX - minX) / 60000)} min`
  historyModal.value = { open: true, title, points: pts, minY: minY.toFixed(1), maxY: maxY.toFixed(1), rangeLabel, xTicks, yTicks, w, h, padL, padR, padT, padB }
}
function closeHistory(){
  historyModal.value.open = false
}
function openZone(z){
  if (!z?.entity_id) return
  zoneModal.value = {
    open: true,
    entity_id: z.entity_id,
    title: `${z.group} — ${z.entity_id}`,
    temperature: Number(z.temperature) || 0,
    setpoint: Number(z.setpoint) || 0,
    hvac_action: z.hvac_action || z.state || ''
  }
}
function closeZone(){
  zoneModal.value.open = false
}
const thermoStyle = computed(() => {
  const sp = Number(zoneModal.value.setpoint) || 0
  const min = 10
  const max = 30
  const pct = Math.max(0, Math.min(1, (sp - min) / (max - min)))
  const deg = Math.round(300 * pct)
  return { background: `conic-gradient(#ff8a3c ${deg}deg, rgba(255,255,255,0.08) ${deg}deg)` }
})
const hvacLabel = (s) => {
  const v = String(s || '').toLowerCase()
  if (v.includes('heat')) return 'In riscaldamento'
  if (v.includes('cool')) return 'In raffrescamento'
  if (v.includes('off')) return 'Spento'
  return v ? v : '—'
}
const changeZoneSetpoint = async (delta) => {
  if (!zoneModal.value.entity_id) return
  const next = Math.round((Number(zoneModal.value.setpoint) + delta) * 10) / 10
  zoneModal.value.setpoint = next
  await fetch('/api/climate_setpoint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entity_id: zoneModal.value.entity_id, temperature: next })
  })
}
const flowSolarToAcs = computed(() => d.value?.computed?.source_to_acs === 'SOLAR')
const flowVolanoToAcs = computed(() => d.value?.computed?.source_to_acs === 'VOLANO')
const flowPufferToAcs = computed(() => d.value?.computed?.source_to_acs === 'PUFFER')
const flowVolanoToPuffer = computed(() => d.value?.computed?.flags?.volano_to_puffer)
const flowPufferToVolano = computed(() => false)
const flowSolarToPuffer = computed(() => false)
const flowPufferToImpianto = computed(() => false)
const flowVolanoToImpianto = computed(() => false)
const flowPufferToLab = computed(() => false)
const flowMiscelatrice = computed(() => false)
const flowCaldaiaToPuffer = computed(() => false)
const moduleReasonsList = computed(() => {
  const mr = d.value?.computed?.module_reasons || {}
  const flags = d.value?.computed?.flags || {}
  const step = Number(d.value?.computed?.resistance_step || 0)
  const mixActive = String(d.value?.computed?.miscelatrice?.action || 'STOP').toUpperCase() !== 'STOP'
  const labels = [
    { key: 'solare', label: 'Solare', active: !!flags.solare_to_acs },
    { key: 'volano_to_acs', label: 'Volano -> ACS', active: !!flags.volano_to_acs },
    { key: 'volano_to_puffer', label: 'Volano -> Puffer', active: !!flags.volano_to_puffer },
    { key: 'puffer_to_acs', label: 'Puffer -> ACS', active: !!flags.puffer_to_acs },
    { key: 'miscelatrice', label: 'Miscelatrice', active: mixActive },
    { key: 'curva_climatica', label: 'Curva climatica', active: !!d.value?.computed?.curva_climatica?.setpoint },
    {
      key: 'impianto',
      label: 'Impianto Riscaldamento',
      active: !!(
        d.value?.computed?.impianto?.richiesta &&
        d.value?.computed?.impianto?.source &&
        d.value?.computed?.impianto?.source !== 'OFF' &&
        !d.value?.computed?.gas_emergenza?.enabled
      )
    },
    {
      key: 'caldaia_legna',
      label: 'Caldaia Legna',
      active: !!(d.value?.computed?.caldaia_legna?.power || d.value?.computed?.caldaia_legna?.ta)
    },
    { key: 'gas_emergenza', label: 'Caldaia Gas Emergenza Riscaldamento', active: !!d.value?.computed?.gas_emergenza?.need },
    { key: 'resistenze_volano', label: 'Resistenze Volano', active: step > 0 }
  ]
  return labels
    .filter(item => mr[item.key])
    .map(item => ({
      ...item,
      enabled: modules.value?.[item.key] !== false,
      reason: mr[item.key]
    }))
})
const moduleActiveMap = computed(() => {
  const flags = d.value?.computed?.flags || {}
  const step = Number(d.value?.computed?.resistance_step || 0)
  const mixActive = !!d.value?.computed?.impianto?.miscelatrice
  const impActive = !!(
    d.value?.computed?.impianto?.richiesta &&
    d.value?.computed?.impianto?.source &&
    d.value?.computed?.impianto?.source !== 'OFF' &&
    !d.value?.computed?.gas_emergenza?.enabled
  )
  return {
    solare: !!flags.solare_to_acs,
    volano_to_acs: !!flags.volano_to_acs,
    volano_to_puffer: !!flags.volano_to_puffer,
    puffer_to_acs: !!flags.puffer_to_acs,
    miscelatrice: mixActive,
    curva_climatica: !!d.value?.computed?.curva_climatica?.setpoint,
    impianto: impActive,
    caldaia_legna: !!(d.value?.computed?.caldaia_legna?.power || d.value?.computed?.caldaia_legna?.ta),
    gas_emergenza: !!d.value?.computed?.gas_emergenza?.need,
    resistenze_volano: step > 0,
    pdc: !!d.value?.computed?.pdc?.active
  }
})
const moduleClass = (key) => {
  const enabled = !!modules.value?.[key]
  return {
    on: enabled,
    off: !enabled,
    active: enabled && !!moduleActiveMap.value?.[key]
  }
}
const modulePanelClass = (key) => {
  const enabled = !!modules.value?.[key]
  return {
    'mod-on': enabled,
    'mod-active': enabled && !!moduleActiveMap.value?.[key]
  }
}

const solarModeClass = computed(() => {
  const mode = sp.value?.solare?.mode || 'auto'
  return mode === 'night' ? 'mode-night' : 'mode-day'
})
const flowChargeVolano = computed(() => (d.value?.computed?.resistance_step || 0) > 0)
const flowPdcToVolano = computed(() => false)
const curvePoints = computed(() => {
  const xs = (sp.value?.curva_climatica?.x || []).map(Number).filter(v => !Number.isNaN(v))
  const ys = (sp.value?.curva_climatica?.y || []).map(Number).filter(v => !Number.isNaN(v))
  if (!xs.length || xs.length !== ys.length) return ''
  const slope = Number(sp.value?.curva_climatica?.slope || 0)
  const offset = Number(sp.value?.curva_climatica?.offset || 0)
  const minC = Number(sp.value?.curva_climatica?.min_c || -999)
  const maxC = Number(sp.value?.curva_climatica?.max_c || 999)
  const yAvg = ys.reduce((a, b) => a + b, 0) / ys.length
  const adj = ys.map((y) => {
    const mod = yAvg + (1 + slope) * (y - yAvg) + offset
    return Math.max(minC, Math.min(maxC, mod))
  })
  const xMin = Math.min(...xs)
  const xMax = Math.max(...xs)
  const yMin = Math.min(...adj)
  const yMax = Math.max(...adj)
  const spanX = xMax - xMin || 1
  const spanY = yMax - yMin || 1
  return xs.map((x, i) => {
    const nx = 100 - (((x - xMin) / spanX) * 100)
    const ny = 100 - ((adj[i] - yMin) / spanY) * 100
    return `${nx.toFixed(2)},${ny.toFixed(2)}`
  }).join(' ')
})
const curveExtX = computed(() => {
  const xs = (sp.value?.curva_climatica?.x || []).map(Number).filter(v => !Number.isNaN(v))
  if (!xs.length) return null
  const xMin = Math.min(...xs)
  const xMax = Math.max(...xs)
  const spanX = xMax - xMin || 1
  const ext = d.value?.computed?.curva_climatica?.t_ext
  if (ext === null || ext === undefined) return null
  return 100 - (((Number(ext) - xMin) / spanX) * 100)
})
const curveExtY = computed(() => {
  const ys = (sp.value?.curva_climatica?.y || []).map(Number).filter(v => !Number.isNaN(v))
  if (!ys.length) return null
  const yMin = Math.min(...ys)
  const yMax = Math.max(...ys)
  const spanY = yMax - yMin || 1
  const spv = d.value?.computed?.curva_climatica?.setpoint
  if (spv === null || spv === undefined) return null
  return 100 - ((Number(spv) - yMin) / spanY) * 100
})
const curveBounds = computed(() => {
  const xs = (sp.value?.curva_climatica?.x || []).map(Number).filter(v => !Number.isNaN(v))
  const ys = (sp.value?.curva_climatica?.y || []).map(Number).filter(v => !Number.isNaN(v))
  if (!xs.length || !ys.length) return { xMin: null, xMax: null, yMin: null, yMax: null }
  const slope = Number(sp.value?.curva_climatica?.slope || 0)
  const offset = Number(sp.value?.curva_climatica?.offset || 0)
  const minC = Number(sp.value?.curva_climatica?.min_c || -999)
  const maxC = Number(sp.value?.curva_climatica?.max_c || 999)
  const yAvg = ys.reduce((a, b) => a + b, 0) / ys.length
  const adj = ys.map((y) => {
    const mod = yAvg + (1 + slope) * (y - yAvg) + offset
    return Math.max(minC, Math.min(maxC, mod))
  })
  return {
    xMin: Math.min(...xs),
    xMax: Math.max(...xs),
    yMin: Math.min(...adj),
    yMax: Math.max(...adj)
  }
})
const curveXTicks = computed(() => {
  const xs = (sp.value?.curva_climatica?.x || []).map(Number).filter(v => !Number.isNaN(v))
  return xs.slice().sort((a, b) => b - a)
})
const curveYTicks = computed(() => {
  const { yMin, yMax } = curveBounds.value
  if (yMin === null || yMax === null) return []
  const span = yMax - yMin || 1
  const steps = 4
  return Array.from({ length: steps + 1 }, (_, i) => yMax - (span * i / steps))
})

  function mergeEntities(next){
    if (!ent.value) { ent.value = next; return }
    for (const key of Object.keys(next || {})) {
      const prev = ent.value[key] || { entity_id: null }
      const keepId = (dirtyEnt.value?.[key] || editingCount.value > 0) ? prev.entity_id : next[key]?.entity_id
      ent.value[key] = { ...next[key], entity_id: keepId }
    }
  }
  function mergeActuators(next){
    if (!act.value) { act.value = next; return }
    for (const key of Object.keys(next || {})) {
      const prev = act.value[key] || { entity_id: null }
      const keepId = (dirtyAct.value?.[key] || editingCount.value > 0) ? prev.entity_id : next[key]?.entity_id
      act.value[key] = { ...next[key], entity_id: keepId }
    }
  }
async function refresh(){
  if (tab.value === 'admin' || editingCount.value > 0) return
  const r = await fetch('/api/decision'); d.value = await r.json()
  zones.value = d.value?.zones || []
  updateHistoryFromDecision(d.value)
  const s = await fetch('/api/status'); status.value = await s.json()
  const a = await fetch('/api/actions'); actions.value = (await a.json()).items || []
  await loadActuators()
  await load()
  lastUpdate.value = new Date()
}
async function loadModules(){
  const r = await fetch('/api/modules'); modules.value = await r.json()
}
async function load(){
  historyReady = false
  const r = await fetch('/api/setpoints'); sp.value = await r.json()
  if (!sp.value?.timers) {
    sp.value.timers = {
      volano_to_acs_start_s: 5,
      volano_to_acs_stop_s: 2,
      volano_to_puffer_start_s: 5,
      volano_to_puffer_stop_s: 2
    }
  }
  if (!sp.value?.history) sp.value.history = {}
  const histDefaults = {
    t_acs: false, t_acs_alto: false, t_acs_medio: false, t_acs_basso: false, t_puffer: false, t_volano: false,
    t_volano_alto: false, t_volano_basso: false,
    t_solare_mandata: false, t_esterna: false,
    t_puffer_alto: false, t_puffer_medio: false, t_puffer_basso: false,
    collettore_energy_day_kwh: false, collettore_energy_total_kwh: false, collettore_flow_lmin: false, collettore_pwm_pct: false,
    collettore_temp_esterna: false, collettore_tsa1: false, collettore_tse: false, collettore_tsv: false, collettore_twu: false,
    t_mandata_miscelata: false, t_ritorno_miscelato: false, miscelatrice_setpoint: false,
    delta_puffer_acs: false, delta_volano_acs: false, delta_volano_puffer: false, delta_mandata_ritorno: false, kp_eff: false,
    curva_setpoint: false
  }
  for (const [k, v] of Object.entries(histDefaults)) {
    if (typeof sp.value.history[k] === 'undefined') sp.value.history[k] = v
  }
  if (!sp.value?.solare) {
    sp.value.solare = { mode: 'auto', delta_on_c: 5, delta_hold_c: 2.5, max_c: 90, pv_entity: '', pv_day_w: 1000, pv_night_w: 300, pv_debounce_s: 300 }
  }
  if (!sp.value?.volano) {
    sp.value.volano = { margin_c: 3, max_c: 60, max_hyst_c: 2, min_to_acs_c: 50, hyst_to_acs_c: 5, delta_to_acs_start_c: 5, delta_to_acs_hold_c: 2.5, delta_to_puffer_start_c: 5, delta_to_puffer_hold_c: 2.5, min_to_puffer_c: 55, hyst_to_puffer_c: 2 }
  } else {
    if (typeof sp.value.volano.min_to_puffer_c === 'undefined') sp.value.volano.min_to_puffer_c = 55
    if (typeof sp.value.volano.hyst_to_puffer_c === 'undefined') sp.value.volano.hyst_to_puffer_c = 2
  }
  if (!sp.value?.miscelatrice) {
    sp.value.miscelatrice = { setpoint_c: 45, hyst_c: 0.5, kp: 2, min_imp_s: 1, max_imp_s: 8, pause_s: 5, dt_ref_c: 10, dt_min_factor: 0.6, dt_max_factor: 1.4, min_temp_c: 20, max_temp_c: 80, force_impulse_s: 3 }
  }
  if (!sp.value?.curva_climatica) {
    sp.value.curva_climatica = { x: [-15,-11.25,-7.5,-3.75,0,3.75,7.5,11.25,15], y: [60,57.6,55,52.6,50,47.6,45,42.6,40], slope: 0, offset: 0, min_c: 40, max_c: 60 }
  }
  if (!sp.value?.gas_emergenza) {
    sp.value.gas_emergenza = { zones: [], volano_min_c: 35, volano_hyst_c: 2, puffer_min_c: 35, puffer_hyst_c: 2 }
  }
  if (!sp.value?.impianto) {
  sp.value.impianto = { source_mode: 'AUTO', pdc_ready: false, volano_ready: false, puffer_ready: true, richiesta_heat: false, volano_min_c: 35, volano_hyst_c: 2, puffer_min_c: 35, puffer_hyst_c: 2, zones_pt: [], zones_p1: [], zones_mans: [], zones_lab: [], zone_scala: '', cooling_blocked: [], pump_start_delay_s: 9, pump_stop_delay_s: 0, season_mode: 'winter' }
  }
  curveXText.value = (sp.value.curva_climatica?.x || []).join(', ')
  curveYText.value = (sp.value.curva_climatica?.y || []).join(', ')
  // normalize lists (allow CSV from older configs)
  const normalizeList = (v) => {
    if (Array.isArray(v)) return v.filter(x => String(x).trim().length > 0)
    if (typeof v === 'string') return v.split(',').map(s => s.trim()).filter(Boolean)
    return []
  }
  sp.value.impianto.zones_pt = normalizeList(sp.value.impianto.zones_pt)
  sp.value.impianto.zones_p1 = normalizeList(sp.value.impianto.zones_p1)
  sp.value.impianto.zones_mans = normalizeList(sp.value.impianto.zones_mans)
  sp.value.impianto.zones_lab = normalizeList(sp.value.impianto.zones_lab)
  sp.value.impianto.cooling_blocked = normalizeList(sp.value.impianto.cooling_blocked)
  sp.value.gas_emergenza.zones = normalizeList(sp.value.gas_emergenza.zones)
  if (sp.value?.runtime?.ui_poll_ms) {
    pollMs.value = Number(sp.value.runtime.ui_poll_ms) || 3000
  }
  historyReady = true
}
function parseCurveText(text, fallback){
  if (!text || typeof text !== 'string') return fallback
  const out = text.split(',').map(s => parseFloat(s.trim())).filter(v => !Number.isNaN(v))
  return out.length ? out : fallback
}
function applyCurveText(){
  if (!sp.value?.curva_climatica) return
  const fallbackX = sp.value.curva_climatica.x || []
  const fallbackY = sp.value.curva_climatica.y || []
  sp.value.curva_climatica.x = parseCurveText(curveXText.value, fallbackX)
  sp.value.curva_climatica.y = parseCurveText(curveYText.value, fallbackY)
}
function saveCurveDebounced(){
  if (curveSaveTimer) clearTimeout(curveSaveTimer)
  curveSaveTimer = setTimeout(() => { save() }, 300)
}
function saveHistoryDebounced(){
  if (!historyReady) return
  if (historySaveTimer) clearTimeout(historySaveTimer)
  historySaveTimer = setTimeout(() => { save() }, 300)
}
async function loadActuators(){
  if (editingCount.value > 0) return
  const r = await fetch('/api/actuators'); act.value = await r.json()
}
async function save(){
  applyCurveText()
  await fetch('/api/setpoints',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(sp.value)})
  await refresh()
  if (sp.value?.runtime?.ui_poll_ms) {
    pollMs.value = Number(sp.value.runtime.ui_poll_ms) || 3000
    startPolling()
  }
}
async function resetLegnaForcedOff(){
  if (!sp.value?.caldaia_legna) return
  sp.value.caldaia_legna.forced_off = false
  await save()
}
async function saveAll(){
  await save()
  await saveEntities()
  await saveActuators()
}
async function toggleModule(key){
  const pin = sp.value?.security?.user_pin || ''
  let provided = ''
  if (pin) {
    provided = window.prompt('PIN') || ''
  }
  const next = { ...modules.value, [key]: !modules.value[key] }
  const res = await fetch('/api/modules',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ modules: next, pin: provided })
  })
  if (!res.ok) return
  await loadModules()
}
async function confirmMode(){
  if (!sp.value?.runtime?.mode) return
  if (sp.value.runtime.mode === 'live') {
    const ok = window.confirm('Passare a LIVE? Questo abilita comandi reali agli attuatori.')
    if (!ok) sp.value.runtime.mode = 'dry-run'
  }
  await save()
}
async function loadEntities(){
  if (editingCount.value > 0) return
  const r = await fetch('/api/entities')
  const data = await r.json()
  const out = {}
  for (const key of Object.keys(data || {})) {
    const val = data[key]
    if (typeof val === 'string' || val === null) {
      out[key] = { entity_id: val || null, state: null, attributes: {}, icon: null }
    } else {
      out[key] = val
    }
  }
  ent.value = out
}
  async function saveEntities(){
    const payload = {}
    for (const key of Object.keys(ent.value || {})) {
      payload[key] = ent.value?.[key]?.entity_id || null
    }
    await fetch('/api/entities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({entities: payload})})
    dirtyEnt.value = {}
    await refresh()
  }
  async function saveActuators(){
    const payload = {}
    for (const item of actuatorDefs) {
      payload[item.key] = act.value?.[item.key]?.entity_id || null
    }
    await fetch('/api/actuators',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({actuators: payload})})
    dirtyAct.value = {}
    await loadActuators()
  }
async function exportConfig(){
  const r = await fetch('/api/config')
  const data = await r.json()
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'thermomind_config.json'
  a.click()
  URL.revokeObjectURL(url)
}
async function importConfig(ev){
  const file = ev.target.files?.[0]
  if (!file) return
  const text = await file.text()
  let data = null
  try { data = JSON.parse(text) } catch { return }
  await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
  await loadAll()
}
async function doAct(entity_id, action, opts = {}){
  if (!entity_id) return
  await fetch('/api/actuate',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({entity_id, action, manual: !!opts.manual})
  })
  await loadActuators()
}

function userToggle(entityObj, moduleKey){
  if (!entityObj?.entity_id) return
  if (status.value?.runtime_mode !== 'live') return
  if (moduleKey && !modules.value?.[moduleKey]) return
  const action = entityObj.state === 'on' ? 'off' : 'on'
  doAct(entityObj.entity_id, action)
}

function userToggleManual(entityObj){
  if (!entityObj?.entity_id) return
  const action = entityObj.state === 'on' ? 'off' : 'on'
  const ok = window.confirm(`Manuale solare: ${action.toUpperCase()} ${entityObj.entity_id}. Confermi?`)
  if (!ok) return
  doAct(entityObj.entity_id, action, { manual: true })
}
function stateLabel(state){
  if (state === 'on') return 'ON'
  if (state === 'off') return 'OFF'
  return state || '-'
}
function toggleAct(key){
  const ent = act.value?.[key]
  if (!ent?.entity_id) return
  const action = ent.state === 'on' ? 'off' : 'on'
  const label = actuatorDefs.find(a => a.key === key)?.label || ent.entity_id
  const ok = window.confirm(`Comando manuale su ${label} (${action.toUpperCase()}). Confermi?`)
  if (!ok) return
  doAct(ent.entity_id, action, { manual: true })
}
function mdiClass(icon){
  if (!icon || typeof icon !== 'string') return ''
  if (icon.startsWith('mdi:')) {
    const name = icon.slice(4)
    return `mdi mdi-${name}`
  }
  return ''
}
function stateClass(state){
  if (state === 'on') return 'state-on'
  if (state === 'off') return 'state-off'
  return 'state-unknown'
}
function connectWS(){
  if (ws) ws.close()
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws`)
  ws.onmessage = (ev) => {
    let payload = null
    try { payload = JSON.parse(ev.data) } catch { return }
    if (!payload) return
    d.value = payload.decision || d.value
    if (payload.decision) updateHistoryFromDecision(payload.decision)
    status.value = payload.status || status.value
    actions.value = payload.actions || actions.value
    modules.value = payload.modules || modules.value
    mergeEntities(payload.entities || {})
    mergeActuators(payload.actuators || {})
    lastUpdate.value = new Date()
  }
  ws.onclose = () => {
    setTimeout(connectWS, 2000)
  }
}

function pushHistory(arr, value){
  const v = Number(value)
  if (!Number.isFinite(v)) return
  arr.push(v)
  if (arr.length > maxPoints) arr.splice(0, arr.length - maxPoints)
}
function updateHistoryFromDecision(decision){
  if (!decision?.inputs) return
  pushHistory(history.value.t_acs, decision.inputs.t_acs)
  pushHistory(history.value.t_acs_alto, decision.inputs.t_acs_alto)
  pushHistory(history.value.t_acs_medio, decision.inputs.t_acs_medio)
  pushHistory(history.value.t_acs_basso, decision.inputs.t_acs_basso)
  pushHistory(history.value.t_puffer, decision.inputs.t_puffer)
  pushHistory(history.value.t_volano, decision.inputs.t_volano)
  pushHistory(history.value.t_volano_alto, decision.inputs.t_volano_alto)
  pushHistory(history.value.t_volano_basso, decision.inputs.t_volano_basso)
  pushHistory(history.value.t_esterna, decision.inputs.t_esterna)
  pushHistory(history.value.collettore_energy_day_kwh, decision.inputs.collettore_energy_day_kwh)
  pushHistory(history.value.collettore_energy_total_kwh, decision.inputs.collettore_energy_total_kwh)
  pushHistory(history.value.collettore_flow_lmin, decision.inputs.collettore_flow_lmin)
  pushHistory(history.value.collettore_pwm_pct, decision.inputs.collettore_pwm_pct)
  pushHistory(history.value.collettore_temp_esterna, decision.inputs.collettore_temp_esterna)
  pushHistory(history.value.collettore_tsa1, decision.inputs.collettore_tsa1)
  pushHistory(history.value.collettore_tse, decision.inputs.collettore_tse)
  pushHistory(history.value.collettore_tsv, decision.inputs.collettore_tsv)
  pushHistory(history.value.collettore_twu, decision.inputs.collettore_twu)
  pushHistory(history.value.t_puffer_alto, decision.inputs.t_puffer_alto)
  pushHistory(history.value.t_puffer_medio, decision.inputs.t_puffer_medio)
  pushHistory(history.value.t_puffer_basso, decision.inputs.t_puffer_basso)
  pushHistory(history.value.t_mandata_miscelata, decision.inputs.t_mandata_miscelata)
  pushHistory(history.value.t_ritorno_miscelato, decision.inputs.t_ritorno_miscelato)
  pushHistory(history.value.curva_setpoint, decision.computed?.curva_climatica?.setpoint)
  pushHistory(history.value.miscelatrice_setpoint, decision.computed?.miscelatrice?.setpoint)
  pushHistory(history.value.delta_puffer_acs, (decision.inputs.t_puffer - decision.inputs.t_acs))
  pushHistory(history.value.delta_volano_acs, (decision.inputs.t_volano - decision.inputs.t_acs))
  pushHistory(history.value.delta_volano_puffer, (decision.inputs.t_volano - decision.inputs.t_puffer))
  pushHistory(history.value.delta_mandata_ritorno, (decision.inputs.t_mandata_miscelata - decision.inputs.t_ritorno_miscelato))
  pushHistory(history.value.kp_eff, decision.computed?.miscelatrice?.kp_eff)
  pushHistory(history.value.export_w, decision.inputs.grid_export_w)
}
function sparkPoints(values){
  const w = 300
  const h = 90
  const pad = 6
  if (!values || values.length < 2) return ''
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  return values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (w - pad * 2)
    const y = h - pad - ((v - min) / span) * (h - pad * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}
async function loadAll(){
  await load()
  await loadEntities()
  await loadActuators()
  await loadModules()
  await refresh()
}
function startPolling(){
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async()=>{
    await refresh()
  }, Math.max(500, pollMs.value))
}
function stopPolling(){
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
}
function onFocus(){
  editingCount.value += 1
  stopPolling()
}
function onBlur(){
  editingCount.value = Math.max(0, editingCount.value - 1)
  if (editingCount.value === 0) startPolling()
}
onMounted(async()=>{ 
  await loadAll(); 
  startPolling();
  connectWS();
  solareModeInit.value = true
  focusInHandler = (e) => {
    const tag = e.target?.tagName
    if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') onFocus()
  }
  focusOutHandler = (e) => {
    const tag = e.target?.tagName
    if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') onBlur()
  }
  window.addEventListener('focusin', focusInHandler)
  window.addEventListener('focusout', focusOutHandler)
})
onBeforeUnmount(()=>{ 
  stopPolling();
  if (ws) ws.close()
  if (focusInHandler) window.removeEventListener('focusin', focusInHandler)
  if (focusOutHandler) window.removeEventListener('focusout', focusOutHandler)
})
watch(tab, (val) => {
  if (val === 'admin') {
    stopPolling()
  } else {
    startPolling()
  }
})

watch(
  () => sp.value?.history,
  () => { saveHistoryDebounced() },
  { deep: true }
)

watch(
  () => sp.value?.solare?.mode,
  async (val, old) => {
    if (!solareModeInit.value) return
    if (val === undefined || val === old) return
    await save()
  }
)
</script>

<style>
:root{--bg:#070a0f;--card:#0b101a;--muted:#9fb0c7;--text:#e8f1ff;--accent:#57e3d6;--accent-2:#7aa7ff;--border:rgba(255,255,255,.08)}
*{box-sizing:border-box} body{margin:0;font-family:"Space Grotesk","IBM Plex Sans","Trebuchet MS",sans-serif;background:radial-gradient(1200px 500px at 20% -10%, rgba(122,167,255,.08), transparent),radial-gradient(900px 500px at 80% 0%, rgba(87,227,214,.06), transparent),var(--bg);color:var(--text)}
.wrap{min-height:100vh;display:flex;flex-direction:column}
.top{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid var(--border);position:sticky;top:0;background:rgba(10,15,22,.85);backdrop-filter:blur(14px)}
.brand{font-weight:800;letter-spacing:.3px}
.tabs button{background:transparent;color:var(--text);border:1px solid var(--border);padding:8px 12px;border-radius:12px;margin-left:8px;cursor:pointer}
.tabs button.active{border-color:var(--accent);color:var(--accent)}
.main{padding:18px;max-width:1100px;margin:0 auto;width:100%}
.card{background:linear-gradient(180deg, rgba(11,16,26,.98), rgba(9,14,22,.98));border:1px solid var(--border);border-radius:20px;padding:18px;box-shadow:0 18px 40px rgba(0,0,0,.38)}
.card.inner{margin-top:14px}
.muted{color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}
@media(min-width:760px){.grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
.kpi{border:1px solid var(--border);border-radius:14px;padding:10px;background:rgba(10,15,22,.6)}
.kpi.kpi-center{display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;min-height:72px}
.kpi.kpi-center .k{display:flex;align-items:center;gap:6px;justify-content:center}
.checkbox{gap:8px}
.checkbox input{accent-color:#57e3d6}
.kpi.clickable{cursor:pointer;transition:transform .15s ease, box-shadow .15s ease}
.kpi.clickable:hover{transform:translateY(-1px);box-shadow:0 6px 18px rgba(0,0,0,.25)}
.mode-night{border-color:rgba(59,130,246,.6);background:rgba(59,130,246,.12);box-shadow:0 0 0 1px rgba(59,130,246,.2) inset, 0 0 18px rgba(59,130,246,.25)}
.mode-day{border-color:rgba(250,204,21,.6);background:rgba(250,204,21,.10);box-shadow:0 0 0 1px rgba(250,204,21,.2) inset, 0 0 18px rgba(250,204,21,.25)}
.k{font-size:12px;color:var(--muted)} .v{font-size:18px;font-weight:700;margin-top:2px}
.actions{margin-top:14px;display:flex;gap:10px;flex-wrap:wrap}
button{background:linear-gradient(135deg, var(--accent), #6cf1c9);border:none;color:#062524;padding:10px 12px;border-radius:14px;font-weight:700;cursor:pointer}
button.ghost{background:transparent;border:1px solid var(--border);color:var(--text)}
hr{border:0;border-top:1px solid var(--border);margin:12px 0}
.form{display:grid;gap:10px;margin-top:10px}
.section{margin:6px 0 2px 0;font-size:14px;color:var(--text)}
.field label{display:block;font-size:12px;color:var(--muted);margin-bottom:6px}
.help{font-size:11px;color:var(--muted);margin-top:6px;line-height:1.3}
.field select{width:100%;padding:10px;border-radius:12px;border:1px solid var(--border);background:#0e1522;color:var(--text)}
.field input{width:100%;padding:10px;border-radius:12px;border:1px solid var(--border);background:#0e1522;color:var(--text)}
.upload{display:inline-flex;align-items:center;gap:8px}
.upload input{display:none}
details.form{border:1px solid var(--border);border-radius:14px;padding:10px;background:rgba(0,0,0,.08)}
details.form summary{cursor:pointer;list-style:none}
.top-actions{display:flex;gap:8px;align-items:center}
.action-btn{background:linear-gradient(135deg, var(--accent), #6cf1c9);border:none;color:#062524;padding:10px 12px;border-radius:14px;font-weight:700;cursor:pointer}
.action-btn.upload{display:inline-flex;align-items:center;gap:6px}
@media(max-width:640px){
  .top{flex-wrap:wrap;gap:10px;padding:12px 14px}
  .brand{flex:1 1 100%;font-size:18px}
  .top-actions{flex:1 1 100%;flex-wrap:wrap}
  .top-actions .action-btn{flex:1 1 46%;min-width:140px;text-align:center}
  .tabs{margin-left:auto}
  .tabs button{padding:6px 10px}
}
.setpoint-grid{column-count:1;column-gap:12px}
.setpoint-grid .section{column-span:all}
.setpoint-grid .set-section{display:inline-block;width:100%;margin:0 0 10px;break-inside:avoid}
@media(min-width:900px){.setpoint-grid{column-count:2}}
.set-section{border:1px solid var(--border);border-radius:14px;padding:10px;background:rgba(12,18,30,.55)}
.setpoint-grid .set-section:nth-of-type(odd){background:rgba(14,20,34,.6)}
.setpoint-grid .set-section:nth-of-type(even){background:rgba(10,16,26,.65)}
.set-section .section-title{font-size:14px;letter-spacing:.7px;text-transform:uppercase;color:#c8d7ee;margin-bottom:6px;font-weight:700}
.set-section .field label{margin-bottom:4px}
.set-section .field input,.set-section .field select{padding:8px;border-radius:10px}
.set-section .help{margin-top:4px}
.subsection{margin-top:10px;font-size:12px;letter-spacing:.4px;text-transform:uppercase;color:var(--muted)}
.zone-chip{cursor:pointer}
.thermo-modal{max-width:520px}
.thermo-body{display:flex;flex-direction:column;align-items:center;gap:18px;padding:8px 0 16px}
.thermo-ring{width:260px;height:260px;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:inset 0 0 0 10px rgba(255,255,255,.04),0 20px 60px rgba(0,0,0,.35)}
.thermo-center{width:180px;height:180px;border-radius:50%;background:radial-gradient(circle at 30% 30%, rgba(255,255,255,.08), rgba(0,0,0,.2));display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
.thermo-state{color:#ffb15e;font-weight:600;letter-spacing:.4px}
.thermo-value{font-size:44px;font-weight:700;margin:6px 0}
.thermo-sub{color:var(--muted);font-size:12px}
.thermo-controls{display:flex;gap:12px}
.thermo-btn{width:44px;height:44px;border-radius:50%;border:1px solid var(--border);background:rgba(255,255,255,.06);color:var(--text);font-size:22px}
.warn{margin-top:8px;color:#ffb15e;background:rgba(255,177,94,.08);border:1px solid rgba(255,177,94,.25);padding:8px 10px;border-radius:10px;font-size:12px}
.row3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.row3 input::placeholder{color:rgba(159,176,199,.6)}
.row2{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.mini-field{display:flex;flex-direction:column;gap:6px}
.mini-head{display:flex;align-items:center;justify-content:space-between}
.mini-value{font-size:11px;color:#c8d7ee}
.mini-label{font-size:11px;color:var(--muted)}
.chart-grid{display:grid;gap:12px}
@media(min-width:900px){.chart-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
.chart{border:1px solid var(--border);border-radius:14px;padding:10px;background:rgba(10,15,22,.6)}
.chart-title{font-size:12px;color:var(--muted);margin-bottom:6px}
.axis-note{font-size:10px;color:var(--muted);margin-top:4px}
.curve-chart{border:1px solid var(--border);border-radius:14px;padding:8px;background:rgba(10,15,22,.6);margin:8px 0}
.curve-line{fill:none;stroke:#57e3d6;stroke-width:1.5}
.curve-marker{stroke:#7aa7ff;stroke-width:0.8;opacity:0.8}
.curve-dot{fill:#7aa7ff}
.curve-axis{fill:#9fb0c7;font-size:5px}
.curve-x-axis{display:grid;grid-template-columns:repeat(9,minmax(0,1fr));gap:2px;margin-top:6px}
.curve-x-label{font-size:9px;color:#9fb0c7;text-align:center}
.spark{fill:none;stroke-width:2}
.spark.acs{stroke:#57e3d6}
.spark.puffer{stroke:#7aa7ff}
.spark.volano{stroke:#f59e0b}
.spark.export{stroke:#ef4444}
.legend.small{margin-top:6px;gap:10px}
.legend-dot.acs{background:#57e3d6}
.legend-dot.puffer{background:#7aa7ff}
.legend-dot.volano{background:#f59e0b}
.legend-dot.export{background:#ef4444}
.statusline{display:flex;align-items:center;gap:8px;margin:8px 0 12px 0;flex-wrap:wrap}
.badge{font-size:12px;padding:4px 8px;border-radius:999px;border:1px solid var(--border)}
.badge.ok{color:#0b1f1c;background:var(--accent)}
.badge.off{color:#f5f7fa;background:#3b3f46}
.presence{display:inline-block;margin-right:6px}
.presence-ok{color:#22c55e}
.presence-no{color:#ef4444}
.input-ok{border:2px solid #22c55e; box-shadow:0 0 0 2px rgba(34,197,94,0.15)}
.input-row{display:flex;align-items:center;gap:8px}
.history-inline{display:flex;align-items:center;gap:6px;margin-left:10px;font-size:11px;color:var(--muted)}
.logic-dot{display:inline-block}
.logic-ok{color:#22c55e}
.logic-no{color:#ef4444}
.toggle{justify-content:flex-start;gap:8px}
.toggle.on{border-color:rgba(34,197,94,.45);background:linear-gradient(135deg, rgba(34,197,94,.22), rgba(34,197,94,.08));box-shadow:0 0 0 1px rgba(34,197,94,.08) inset}
.toggle.active{border-color:rgba(239,68,68,.55);background:linear-gradient(135deg, rgba(239,68,68,.28), rgba(239,68,68,.12));box-shadow:0 0 0 1px rgba(239,68,68,.12) inset}
.toggle.off{border-color:var(--border);background:transparent}
.mdi-fallback{font-size:14px;opacity:0.8}
.state-on{color:#ef4444}
.state-off{color:#94a3b8}
.state-unknown{color:#f59e0b}
.kpi.state-on{border-color:rgba(239,68,68,.45);background:rgba(239,68,68,.08)}
.kpi.state-off{border-color:var(--border)}
.input-on{background:rgba(239,68,68,.12) !important}
.dot-toggle{border:0;background:transparent;cursor:pointer;padding:0 2px}
.diagram{margin-top:10px;border:1px solid var(--border);border-radius:16px;padding:16px;background:
  radial-gradient(900px 320px at 70% 10%, rgba(87,227,214,.08), transparent),
  radial-gradient(800px 300px at 20% 90%, rgba(122,167,255,.08), transparent),
  repeating-linear-gradient(135deg, rgba(255,255,255,.01), rgba(255,255,255,.01) 12px, transparent 12px, transparent 24px),
  linear-gradient(180deg, rgba(6,10,16,.85), rgba(6,10,16,.55));
  box-shadow: inset 0 0 50px rgba(0,0,0,.55)}
.diagram-photo{
  padding:0;
  aspect-ratio:1347/864;
  min-height:360px;
  background-position:center center;
  background-repeat:no-repeat;
  background-size:contain;
  position:relative;
}
.diagram-overlay{
  width:100%;
  height:100%;
  display:block;
  position:absolute;
  inset:0;
  pointer-events:none;
}
.pulse{
  fill:url(#dotGlow);
  opacity:0;
}
.pulse-on{
  opacity:1;
  animation:pulse 1.6s ease-in-out infinite;
}
.tube{
  fill:none;
  stroke:rgba(87,227,214,.3);
  stroke-width:7;
  stroke-linecap:round;
}
.tube-on{
  stroke:url(#flowGrad);
  stroke-dasharray:18 10;
  animation:tubeFlow 1.4s linear infinite;
  filter:drop-shadow(0 0 6px rgba(87,227,214,.6));
}
@keyframes pulse{
  0%{r:6;opacity:.4}
  50%{r:12;opacity:1}
  100%{r:6;opacity:.4}
}
@keyframes tubeFlow{
  0%{stroke-dashoffset:0}
  100%{stroke-dashoffset:-56}
}
.diagram svg{width:100%;height:auto}
.node{fill:url(#nodeGrad);stroke:rgba(255,255,255,.08);filter:drop-shadow(0 6px 18px rgba(0,0,0,.35))}
.node-active{stroke:rgba(87,227,214,.75);filter:drop-shadow(0 0 12px rgba(87,227,214,.55))}
.node-label{fill:#e6edf3;font-size:13px;font-weight:700}
.node-sub{fill:#9aa4b2;font-size:11px}
.flow-line{stroke:#2b3447;stroke-width:5.5;fill:none;stroke-linecap:round}
.flow-line.dashed{stroke-dasharray:10 8;opacity:.6}
.flow-on{stroke:url(#flowGrad);filter:drop-shadow(0 0 6px rgba(87,227,214,.45));animation:flow 1.6s linear infinite}
.dot{fill:#2b3447}
.dot-on{fill:#57e3d6;filter:drop-shadow(0 0 6px rgba(87,227,214,.55))}
.legend{display:flex;gap:14px;margin-top:8px;flex-wrap:wrap}
.legend-item{display:flex;align-items:center;gap:6px;color:var(--muted);font-size:12px}
.legend-dot{width:10px;height:10px;border-radius:999px;background:#2b3447}
.legend-dot.on{background:#4fd1c5}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:50}
.modal{background:linear-gradient(180deg, rgba(11,16,26,.98), rgba(9,14,22,.98));border:1px solid var(--border);border-radius:16px;max-width:760px;width:90%;padding:14px;box-shadow:0 20px 50px rgba(0,0,0,.5)}
.modal-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.modal-title{font-weight:700}
.axis{stroke:#2b3447;stroke-width:1}
.axis-label{fill:#9fb0c7;font-size:10px}
.history-chart{width:100%;height:auto}
.zones-card{margin-top:10px}
.zones-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
@media(min-width:900px){.zones-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
.zone-chip{border:1px solid var(--border);border-radius:12px;padding:8px;background:rgba(10,15,22,.5)}
.zone-on{border-color:rgba(245,158,11,.6);box-shadow:0 0 0 1px rgba(245,158,11,.3) inset;background:rgba(245,158,11,.08)}
.zone-off{opacity:.75}
.zone-title{font-size:12px;font-weight:700}
.zone-sub{font-size:11px;color:var(--muted)}
.list{display:flex;flex-direction:column;gap:6px}
.list-row{display:flex;gap:8px;align-items:center}
.list-row input{flex:1}
.module-reasons{display:grid;gap:8px;margin-top:6px}
.module-extra{margin-top:6px;display:grid;gap:4px}
.module-row{border:1px solid var(--border);border-radius:12px;padding:8px 10px;background:rgba(10,15,22,.45)}
.module-row.mod-on{background:linear-gradient(135deg, rgba(34,197,94,.08), rgba(34,197,94,.03))}
.module-row.mod-active{background:linear-gradient(135deg, rgba(239,68,68,.10), rgba(239,68,68,.04))}
.module-head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.module-label{font-size:12px;font-weight:700;letter-spacing:.3px}
.module-badges{display:flex;gap:6px;align-items:center}
.module-panel.mod-on{background:linear-gradient(135deg, rgba(34,197,94,.08), rgba(34,197,94,.03))}
.module-panel.mod-active{background:linear-gradient(135deg, rgba(239,68,68,.10), rgba(239,68,68,.04))}
.badge-mini{font-size:10px;border:1px solid var(--border);padding:2px 6px;border-radius:999px;color:var(--muted)}
.badge-mini.on{background:rgba(87,227,214,.12);border-color:rgba(87,227,214,.4);color:#c6fff6}
.badge-mini.off{background:rgba(148,163,184,.08)}
.badge-mini.active{background:rgba(239,68,68,.16);border-color:rgba(239,68,68,.4);color:#ffd4d4}
.badge-mini.idle{background:rgba(148,163,184,.08)}
@keyframes flow{0%{stroke-dashoffset:0}100%{stroke-dashoffset:-36}}
</style>
