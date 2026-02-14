<template>
  <div class="wrap">
    <header class="top">
      <div class="top-inner">
        <div class="top-left">
          <div class="brand">e-EnergyMind</div>
        </div>
        <div class="top-center">
          <div class="top-actions">
            <button class="action-btn" @click="saveAll">Salva tutto</button>
            <button class="action-btn" @click="exportConfig">Esporta config</button>
            <label class="action-btn upload">
              Importa config
              <input type="file" accept="application/json" @change="importConfig"/>
            </label>
          </div>
        </div>
        <div class="top-right">
          <nav class="tabs">
            <button :class="{active: tab==='user'}" @click="tab='user'">User</button>
            <button :class="{active: tab==='admin'}" @click="tab='admin'">Admin</button>
          </nav>
        </div>
      </div>
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
            <div class="field">
              <label>Device name (HA)</label>
              <input type="text"
                     v-model="sp.devices[`s${site}`].name"
                     placeholder="ZCS Privato 1"
                     @change="saveConfig"
                     @focus="onFocus" @blur="onBlur"/>
              <div class="help">Nome dispositivo esatto in Home Assistant (opzionale se usi Device ID).</div>
            </div>
            <div class="field">
              <label>Device ID (HA)</label>
              <input type="text"
                     v-model="sp.devices[`s${site}`].id"
                     placeholder="a1b2c3d4e5f6..."
                     @change="saveConfig"
                     @focus="onFocus" @blur="onBlur"/>
              <div class="help">ID dispositivo (preferito). Lo trovi nella pagina dispositivo in HA.</div>
            </div>
            <div class="actions">
              <button class="ghost" :disabled="!canAutoMap(site)" @click="autoMapSite(site)">Importa entità da dispositivo</button>
              <div class="help" v-if="!canAutoMap(site)">Inserisci Device name o Device ID, oppure seleziona un dispositivo.</div>
            </div>
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

function canAutoMap(site){
  const dev = sp.value?.devices?.[`s${site}`] || {}
  const name = (dev.name || '').trim()
  const id = (dev.id || '').trim()
  return Boolean(name || id)
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
  if (!sp.value.devices) {
    sp.value.devices = { s1: { name: '', id: '' }, s2: { name: '', id: '' }, s3: { name: '', id: '' } }
  } else {
    for (const key of ['s1','s2','s3']) {
      if (!sp.value.devices[key]) sp.value.devices[key] = { name: '', id: '' }
      if (typeof sp.value.devices[key].name !== 'string') sp.value.devices[key].name = ''
      if (typeof sp.value.devices[key].id !== 'string') sp.value.devices[key].id = ''
    }
  }
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
async function autoMapSite(site){
  if (!sp.value?.devices) return
  const dev = sp.value.devices[`s${site}`] || {}
  if (!canAutoMap(site)) {
    window.alert('Inserisci Device name o Device ID, oppure seleziona un dispositivo')
    return
  }
  const payload = { site, device_name: dev.name || '', device_id: dev.id || '', overwrite: false }
  const r = await fetch('/api/auto_map',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
  if (!r.ok) {
    window.alert('Importa entità fallito')
    return
  }
  const data = await r.json()
  await loadEntities()
  await refresh()
  window.alert(`Importate: ${data.mapped || 0} entità`)
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
:root{
  --bg:#0a0f14;
  --bg-2:#0f1620;
  --card:#101823;
  --card-2:#0d141e;
  --line:#1a2433;
  --text:#e6eef8;
  --muted:#9fb0c3;
  --accent:#63e6be;
  --accent-2:#4cc9f0;
  --danger:#ff6b6b;
  --ok:#2dd4bf;
  --off:#6b7280;
  --shadow:0 12px 40px rgba(0,0,0,0.35);
}
*{box-sizing:border-box}
body{
  margin:0;
  background:radial-gradient(1200px 600px at 10% -10%, #172234 0%, var(--bg) 60%);
  color:var(--text);
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}
.wrap{
  min-height:100vh;
  display:flex;
  flex-direction:column;
}
.top, .main{
  width:100%;
  max-width:1200px;
  margin:0 auto;
}
.wrap::before{
  content:"";
  position:fixed;
  inset:0;
  background:radial-gradient(1200px 600px at 10% -10%, #172234 0%, var(--bg) 60%);
  z-index:-1;
}
.top{
  position:sticky;
  top:0;
  z-index:5;
  background:linear-gradient(180deg, rgba(10,15,20,0.98), rgba(10,15,20,0.92));
  border-bottom:1px solid var(--line);
  padding:14px 20px;
  box-shadow:var(--shadow);
}
.top-inner{
  display:grid;
  grid-template-columns: 1fr auto 1fr;
  align-items:center;
  gap:16px;
}
.top-left{
  display:flex;
  flex-direction:column;
  gap:8px;
}
.top-center{
  display:flex;
  justify-content:center;
}
.top-right{
  display:flex;
  align-items:center;
  gap:10px;
  justify-content:flex-end;
  flex-wrap:wrap;
}
.brand{
  font-size:20px;
  font-weight:700;
  letter-spacing:0.3px;
}
.top-actions{
  display:flex;
  gap:10px;
  flex-wrap:wrap;
}
.action-btn{
  background:linear-gradient(135deg, var(--accent), var(--accent-2));
  color:#061015;
  border:none;
  padding:8px 14px;
  border-radius:999px;
  font-weight:600;
  cursor:pointer;
}
.action-btn.upload{
  position:relative;
  overflow:hidden;
}
.action-btn.upload input{
  position:absolute;
  inset:0;
  opacity:0;
  cursor:pointer;
}
.tabs{
  display:flex;
  gap:8px;
}
.tabs button{
  background:var(--card);
  color:var(--muted);
  border:1px solid var(--line);
  padding:6px 12px;
  border-radius:8px;
  cursor:pointer;
}
.tabs button.active{
  color:var(--text);
  border-color:var(--accent);
  box-shadow:0 0 0 2px rgba(99,230,190,0.2) inset;
}
.main{
  padding:18px 20px 40px;
}
.card{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:16px;
  padding:18px;
  box-shadow:var(--shadow);
}
.card.inner{
  margin-top:14px;
  background:var(--card-2);
}
.statusline{
  display:flex;
  gap:10px;
  flex-wrap:wrap;
  align-items:center;
  margin-bottom:10px;
}
.badge{
  padding:4px 10px;
  border-radius:999px;
  font-weight:700;
  font-size:12px;
}
.badge.ok{ background:rgba(45,212,191,0.15); color:var(--ok); border:1px solid rgba(45,212,191,0.4); }
.badge.off{ background:rgba(107,114,128,0.2); color:var(--off); border:1px solid rgba(107,114,128,0.4); }
.muted{ color:var(--muted); }
.grid{
  display:grid;
  grid-template-columns:repeat(4, minmax(140px,1fr));
  gap:10px;
}
.row3{
  display:grid;
  grid-template-columns:repeat(3, minmax(160px,1fr));
  gap:10px;
  margin-top:10px;
}
.kpi{
  background:#0b121a;
  border:1px solid var(--line);
  border-radius:12px;
  padding:10px 12px;
}
.kpi-center{ text-align:center; }
.k{ font-size:12px; color:var(--muted); }
.v{ font-size:18px; font-weight:700; margin-top:6px; }
.actions{
  margin-top:12px;
  display:flex;
  gap:10px;
  flex-wrap:wrap;
}
.actions button{
  background:var(--accent);
  color:#061015;
  border:none;
  padding:8px 14px;
  border-radius:10px;
  cursor:pointer;
  font-weight:600;
}
.actions button:disabled{
  opacity:0.5;
  cursor:not-allowed;
}
.actions .ghost{
  background:transparent;
  color:var(--text);
  border:1px solid var(--line);
}
.form{
  margin-top:14px;
  padding:12px;
  background:#0b121a;
  border:1px solid var(--line);
  border-radius:12px;
}
.section{
  font-size:14px;
  text-transform:uppercase;
  letter-spacing:0.08em;
  color:var(--muted);
}
.field{
  display:flex;
  flex-direction:column;
  gap:6px;
  margin-top:10px;
}
.field input, .field select{
  background:#0c141d;
  border:1px solid var(--line);
  color:var(--text);
  padding:8px 10px;
  border-radius:8px;
}
.help{ font-size:12px; color:var(--muted); }
.set-section{
  padding:10px 0;
  border-top:1px dashed var(--line);
}
.section-title{
  font-weight:700;
  margin-bottom:6px;
}
.input-row{
  display:flex;
  align-items:center;
  gap:8px;
}
.logic-dot{ font-size:16px; }
.logic-ok{ color:var(--ok); }
.logic-no{ color:var(--danger); }
.input-ok{ border-color:var(--ok) !important; box-shadow:0 0 0 2px rgba(45,212,191,0.15); }

@media (max-width: 1100px){
  .grid{ grid-template-columns:repeat(2, minmax(140px,1fr)); }
  .row3{ grid-template-columns:repeat(2, minmax(160px,1fr)); }
}
@media (max-width: 900px){
  .top-inner{ grid-template-columns:1fr; justify-items:start; }
  .top-center{ justify-content:flex-start; }
  .top-right{ justify-content:flex-start; }
}
@media (max-width: 640px){
  .grid{ grid-template-columns:1fr; }
  .row3{ grid-template-columns:1fr; }
  .top{ position:static; }
}
</style>
