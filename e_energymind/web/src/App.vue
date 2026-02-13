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
            <select v-model.number="sp.runtime.sites_count" @change="saveConfig">
              <option :value="1">1 utenza</option>
              <option :value="2">2 utenze</option>
              <option :value="3">3 utenze</option>
            </select>
            <div class="help">Imposta quante utenze elettriche gestire (1-3).</div>
          </div>
          <div v-if="sp" class="field">
            <label>Polling UI (ms)</label>
            <input type="number" min="500" step="500" v-model.number="sp.runtime.ui_poll_ms" @change="saveConfig"/>
            <div class="help">Intervallo aggiornamento UI.</div>
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
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'

const tab = ref('user')
const sp = ref(null)
const ent = ref(null)
const status = ref(null)
const lastUpdate = ref(null)
const pollMs = ref(3000)
const actions = ref([])
let pollTimer = null
const editingCount = ref(0)
const dirtyEnt = ref({})

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

function onFocus(){
  editingCount.value += 1
  stopPolling()
}
function onBlur(){
  editingCount.value = Math.max(0, editingCount.value - 1)
  if (editingCount.value === 0) startPolling()
}

async function loadConfig(){
  const r = await fetch('/api/config')
  sp.value = await r.json()
  if (sp.value?.runtime?.ui_poll_ms) {
    pollMs.value = Number(sp.value.runtime.ui_poll_ms) || 3000
  }
}
async function saveConfig(){
  await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(sp.value)})
  await loadConfig()
}
async function loadEntities(){
  if (editingCount.value > 0) return
  const r = await fetch('/api/entities')
  const data = await r.json()
  ent.value = data
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
async function refresh(){
  if (tab.value === 'admin' || editingCount.value > 0) return
  const s = await fetch('/api/status')
  status.value = await s.json()
  const a = await fetch('/api/actions')
  actions.value = (await a.json()).items || []
  await loadEntities()
  lastUpdate.value = new Date()
}
async function loadAll(){
  await loadConfig()
  await loadEntities()
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
async function saveAll(){
  await saveConfig()
  await saveEntities()
}

onMounted(async()=>{
  await loadAll()
  startPolling()
})
onBeforeUnmount(()=>{ stopPolling() })
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
