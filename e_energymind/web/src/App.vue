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
        <h2>Stato (energia)</h2>
        <div class="statusline">
          <span class="muted">v{{ status?.version || '-' }}</span>
          <span class="muted">mode: {{ status?.runtime_mode || '-' }}</span>
          <span class="badge" :class="status?.ha_connected ? 'ok' : 'off'">
            {{ status?.ha_connected ? 'Online' : 'Offline' }}
          </span>
          <span class="muted">HA</span>
          <span class="muted">Ultimo aggiornamento: {{ lastUpdate ? lastUpdate.toLocaleTimeString() : '-' }}</span>
        </div>
        <p v-if="status?.runtime_mode !== 'live'" class="muted">Dry-run: nessun comando agli attuatori. Analisi solo lettura.</p>

        <div v-if="ent" v-for="site in siteList" :key="`user-site-${site}`" class="card inner">
          <div class="row"><strong>Utenza {{ site }}</strong></div>
          <div class="grid">
            <div class="kpi">
              <div class="k">PV Power</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'pv_power')) }}</div>
            </div>
            <div class="kpi">
              <div class="k">Carico casa</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'load_power')) }}</div>
            </div>
            <div class="kpi">
              <div class="k">Rete (PCC)</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'grid_power')) }}</div>
            </div>
            <div class="kpi">
              <div class="k">Import rete</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'grid_import_power')) }}</div>
            </div>
            <div class="kpi">
              <div class="k">Export rete</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'grid_export_power')) }}</div>
            </div>
            <div class="kpi">
              <div class="k">Batteria Power</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'battery_power')) }}</div>
            </div>
            <div class="kpi">
              <div class="k">Batteria SOC</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'battery_soc')) }}</div>
            </div>
            <div class="kpi">
              <div class="k">Batteria Temp</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'battery_temp')) }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center">
              <div class="k">Produzione oggi</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'today_production_kwh')) }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Consumo oggi</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'today_load_kwh')) }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Import oggi</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'today_import_kwh')) }}</div>
            </div>
          </div>
          <div class="row3">
            <div class="kpi kpi-center">
              <div class="k">Export oggi</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'today_export_kwh')) }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Forecast oggi</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'forecast_today_kwh')) }}</div>
            </div>
            <div class="kpi kpi-center">
              <div class="k">Forecast domani</div>
              <div class="v">{{ fmtEntity(getEnt(site, 'forecast_tomorrow_kwh')) }}</div>
            </div>
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
        <h2>Admin (energia)</h2>
        <p class="muted">Configurazione e mapping sensori energia (read-only).</p>
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
          <div v-if="sp" class="field">
            <label>Numero utenze</label>
            <select v-model.number="sp.runtime.sites_count" @change="save">
              <option :value="1">1 utenza</option>
              <option :value="2">2 utenze</option>
              <option :value="3">3 utenze</option>
            </select>
            <div class="help">Imposta quante utenze elettriche gestire (1-3).</div>
          </div>
        </div>

        <div v-if="sp" class="form setpoint-grid">
          <h3 class="section">Runtime</h3>
          <div class="set-section">
            <div class="section-title">Modalità</div>
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
              <div class="help">Intervallo aggiornamento UI.</div>
            </div>
          </div>
        </div>

        <details class="form" open v-if="ent">
          <summary class="section">Sensori energia (read-only)</summary>
          <div v-for="site in siteList" :key="`site-${site}`" class="set-section">
            <div class="section-title">Utenza {{ site }}</div>
            <div v-for="item in energyEntityDefs" :key="`s${site}_${item.key}`" class="field">
              <label>{{ item.label }}</label>
              <div class="input-row">
                <span class="logic-dot" :class="isFilled(ent?.[`s${site}_${item.key}`]?.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
                <input type="text"
                       :class="isFilled(ent?.[`s${site}_${item.key}`]?.entity_id) ? 'input-ok' : ''"
                       v-model="ent[`s${site}_${item.key}`].entity_id"
                       :placeholder="item.placeholder || 'sensor.xxx'"
                       @input="dirtyEnt[`s${site}_${item.key}`] = true"
                       @focus="onFocus" @blur="onBlur"/>
              </div>
              <div v-if="item.help" class="help">{{ item.help }}</div>
            </div>
          </div>
          <div class="actions">
            <button class="ghost" @click="saveEntities">Salva sensori</button>
          </div>
        </details>

        <div class="actions">
          <button class="ghost" @click="loadAll">Ricarica</button>
        </div>
      </section>
      <div v-if="historyModal.open" class="modal-backdrop" @click.self="closeHistory">
        <div class="modal">
          <div class="modal-head">
            <div class="modal-title">Storico 24h â€” {{ historyModal.title }}</div>
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
              <span class="legend-item muted">Y: Â°C ({{ historyModal.minY }}â€“{{ historyModal.maxY }})</span>
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
              <button class="thermo-btn" @click="changeZoneSetpoint(-0.5)">âˆ’</button>
              <button class="thermo-btn" @click="changeZoneSetpoint(0.5)">+</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
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

const energyEntityDefs = [
  { key: 'pv_power', label: 'PV Power (W)', placeholder: 'sensor.zcs_pv_power' },
  { key: 'pv_power_aux', label: 'PV Power Aux (W)', placeholder: 'sensor.zcs_pv1_power' },
  { key: 'pv_power_total', label: 'PV Power Totale (W)', placeholder: 'sensor.zcs_pv_total' },
  { key: 'load_power', label: 'Carico casa (W)', placeholder: 'sensor.zcs_activepower_load_sys' },
  { key: 'grid_power', label: 'Rete (PCC) totale (W)', placeholder: 'sensor.zcs_activepower_pcc_total', help: 'Segno da verificare: positivo=import o export.' },
  { key: 'grid_import_power', label: 'Import rete (W)', placeholder: 'sensor.zcs_grid_import' },
  { key: 'grid_export_power', label: 'Export rete (W)', placeholder: 'sensor.zcs_grid_export' },
  { key: 'battery_power', label: 'Batteria Potenza (W)', placeholder: 'sensor.zcs_battery_power', help: 'Segno da verificare: positivo=carica o scarica.' },
  { key: 'battery_voltage', label: 'Batteria Tensione (V)', placeholder: 'sensor.zcs_battery_voltage' },
  { key: 'battery_current', label: 'Batteria Corrente (A)', placeholder: 'sensor.zcs_battery_current' },
  { key: 'battery_soc', label: 'Batteria SOC (%)', placeholder: 'sensor.zcs_battery_soc' },
  { key: 'battery_soh', label: 'Batteria SOH (%)', placeholder: 'sensor.zcs_battery_soh' },
  { key: 'battery_temp', label: 'Batteria Temperatura (C)', placeholder: 'sensor.zcs_battery_temperature' },
  { key: 'storage_control_mode', label: 'Storage Control Mode', placeholder: 'sensor.zcs_storage_control_mode' },
  { key: 'timed_charge_start', label: 'Timed Charge Start', placeholder: 'sensor.zcs_timed_charge_start' },
  { key: 'timed_charge_end', label: 'Timed Charge End', placeholder: 'sensor.zcs_timed_charge_end' },
  { key: 'timed_charge_power', label: 'Timed Charge Power', placeholder: 'sensor.zcs_timed_charge_power' },
  { key: 'timed_discharge_start', label: 'Timed Discharge Start', placeholder: 'sensor.zcs_timed_discharge_start' },
  { key: 'timed_discharge_end', label: 'Timed Discharge End', placeholder: 'sensor.zcs_timed_discharge_end' },
  { key: 'timed_discharge_power', label: 'Timed Discharge Power', placeholder: 'sensor.zcs_timed_discharge_power' },
  { key: 'today_production_kwh', label: 'Today Production (kWh)', placeholder: 'sensor.zcs_today_production' },
  { key: 'today_load_kwh', label: 'Today Load (kWh)', placeholder: 'sensor.zcs_today_load_consumption' },
  { key: 'today_import_kwh', label: 'Today Import (kWh)', placeholder: 'sensor.zcs_today_energy_import' },
  { key: 'today_export_kwh', label: 'Today Export (kWh)', placeholder: 'sensor.zcs_today_energy_export' },
  { key: 'forecast_today_kwh', label: 'Forecast PV Oggi (kWh)', placeholder: 'sensor.pv_forecast_today' },
  { key: 'forecast_tomorrow_kwh', label: 'Forecast PV Domani (kWh)', placeholder: 'sensor.pv_forecast_tomorrow' },
  { key: 'inverter_status', label: 'Inverter Status', placeholder: 'sensor.zcs_inverter_status' },
  { key: 'device_fault', label: 'Device Fault', placeholder: 'sensor.zcs_device_fault' },
  { key: 'grid_frequency', label: 'Grid Frequency (Hz)', placeholder: 'sensor.zcs_grid_frequency' },
  { key: 'ambient_temp_1', label: 'Ambient Temperature 1 (C)', placeholder: 'sensor.zcs_ambient_temperature_1' },
  { key: 'ambient_temp_2', label: 'Ambient Temperature 2 (C)', placeholder: 'sensor.zcs_ambient_temperature_2' },
  { key: 'module_temp_1', label: 'Module Temperature 1 (C)', placeholder: 'sensor.zcs_module_temperature_1' },
  { key: 'module_temp_2', label: 'Module Temperature 2 (C)', placeholder: 'sensor.zcs_module_temperature_2' },
  { key: 'module_temp_3', label: 'Module Temperature 3 (C)', placeholder: 'sensor.zcs_module_temperature_3' },
  { key: 'radiator_temp_1', label: 'Radiator Temperature 1 (C)', placeholder: 'sensor.zcs_radiator_temperature_1' },
  { key: 'radiator_temp_2', label: 'Radiator Temperature 2 (C)', placeholder: 'sensor.zcs_radiator_temperature_2' },
  { key: 'radiator_temp_3', label: 'Radiator Temperature 3 (C)', placeholder: 'sensor.zcs_radiator_temperature_3' },
  { key: 'radiator_temp_4', label: 'Radiator Temperature 4 (C)', placeholder: 'sensor.zcs_radiator_temperature_4' },
  { key: 'radiator_temp_5', label: 'Radiator Temperature 5 (C)', placeholder: 'sensor.zcs_radiator_temperature_5' },
  { key: 'radiator_temp_6', label: 'Radiator Temperature 6 (C)', placeholder: 'sensor.zcs_radiator_temperature_6' },
]

const siteList = computed(() => {
  const n = Number(sp.value?.runtime?.sites_count || 1)
  const safe = Number.isFinite(n) ? Math.min(3, Math.max(1, Math.round(n))) : 1
  return Array.from({ length: safe }, (_, i) => i + 1)
})

const isFilled = (v) => (typeof v === 'string' ? v.trim().length > 0 : false)
const filteredActuators = computed(() => {
  const q = filterAct.value.trim().toLowerCase()
  if (!q) return actuatorDefs
  return actuatorDefs.filter(a => (a.label.toLowerCase().includes(q) || a.key.toLowerCase().includes(q)))
})

const fmtTemp = (v) => (Number.isFinite(v) ? `${v.toFixed(1)}Â°C` : 'n/d')
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
const getEnt = (site, key) => {
  if (!ent.value) return null
  return ent.value[`s${site}_${key}`] || null
}
function statsLabel(values, unit){
  if (!values || values.length === 0) return 'n/d'
  const min = Math.min(...values)
  const max = Math.max(...values)
  if (!Number.isFinite(min) || !Number.isFinite(max)) return 'n/d'
  return `${min.toFixed(1)}â€“${max.toFixed(1)} ${unit}`.trim()
}
const tempStats = computed(() => {
  const vals = []
  vals.push(...(history.value.t_acs_alto || []))
  vals.push(...(history.value.t_puffer_alto || []))
  vals.push(...(history.value.t_volano_alto || []))
  return { label: statsLabel(vals, 'Â°C') }
})
const exportStats = computed(() => {
  const vals = history.value.export_w || []
  if (!vals.length) return { label: 'n/d' }
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  if (!Number.isFinite(min) || !Number.isFinite(max)) return { label: 'n/d' }
  return { label: `${Math.round(min)}â€“${Math.round(max)} W` }
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
    title: `${z.group} â€” ${z.entity_id}`,
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
  return v ? v : 'â€”'
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
  a.download = 'energymind_config.json'
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




