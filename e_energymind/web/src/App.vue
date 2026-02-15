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
            <button :class="{active: tab==='automation_settings'}" @click="tab='automation_settings'">Automation setting</button>
            <button :class="{active: tab==='automation_interface'}" @click="tab='automation_interface'">Automazioni interface</button>
          </nav>
        </div>
      </div>
    </header>

    <main class="main">
      <section v-if="tab==='user'" class="card">
        <h2>Stato (energia)</h2>
        <div class="card inner">
          <div class="row"><strong>Intelligenza (globale)</strong></div>
          <div class="muted" v-if="!insights?.global">In attesa dati...</div>
          <div v-else class="entity-list">
            <div class="entity-row row-on">
              <span class="entity-name">Stato</span>
              <span class="entity-value">{{ insights.global.status }}</span>
            </div>
            <div class="entity-row">
              <span class="entity-name">Note</span>
              <span class="entity-value">{{ insights.global.notes }}</span>
            </div>
          </div>
        </div>
        <div class="statusline">
          <span class="muted">v{{ status?.version || '-' }}</span>
          <span class="muted">mode: {{ status?.runtime_mode || '-' }}</span>
          <span class="badge" :class="status?.ha_connected ? 'ok' : 'off'">
            {{ status?.ha_connected ? 'Online' : 'Offline' }}
          </span>
          <span class="muted">HA</span>
          <span class="muted">Ultimo aggiornamento: {{ lastUpdate ? lastUpdate.toLocaleTimeString() : '-' }}</span>
          <span class="muted" v-if="dbInfo?.size_human">DB: {{ dbInfo.size_human }}</span>
        </div>
        <p v-if="status?.runtime_mode !== 'live'" class="muted">Dry-run: nessun comando agli attuatori. Analisi solo lettura.</p>

        <div v-if="ent" v-for="site in siteList" :key="`user-site-${site}`" class="card inner">
          <div class="card inner">
            <div class="row"><strong>Intelligenza Utenza {{ site }}</strong></div>
            <div class="muted" v-if="!siteInsight(site)">In attesa dati...</div>
            <div v-else class="entity-list">
              <div class="entity-row row-on">
                <span class="entity-name">Stato</span>
                <span class="entity-value">{{ siteInsight(site).status }} ({{ siteInsight(site).confidence }})</span>
              </div>
              <div class="entity-row">
                <span class="entity-name">Cause</span>
                <span class="entity-value">{{ (siteInsight(site).reasons || []).join(' · ') }}</span>
              </div>
              <div class="entity-row">
                <span class="entity-name">Suggerimenti</span>
                <span class="entity-value">{{ (siteInsight(site).suggestions || []).join(' · ') }}</span>
              </div>
              <div class="entity-row">
                <span class="entity-name">Previsione +60s</span>
                <span class="entity-value">
                  Batt {{ siteInsight(site).forecast?.t_plus_60s?.battery_power ?? 'n/d' }} W ·
                  Grid {{ siteInsight(site).forecast?.t_plus_60s?.grid_power ?? 'n/d' }} W
                </span>
              </div>
            </div>
          </div>
          <div class="row">
            <strong>Utenza {{ site }}</strong>
            <span class="muted" v-if="deviceLabel(site)"> — {{ deviceLabel(site) }}</span>
          </div>
          <div class="grid">
            <div v-for="item in userKpiDefs.filter(i => isMapped(site, i.key))" :key="`u1-${site}-${item.key}`" class="kpi"
                 :class="isOn(site, item.key) ? 'kpi-on' : ''">
              <div class="k">{{ labelFor(site, item.key, item.label) }}</div>
              <div class="v">{{ fmtEntity(getEnt(site, item.key)) }}</div>
            </div>
          </div>
          <div class="row3">
            <div v-for="item in userDailyDefs.filter(i => isMapped(site, i.key))" :key="`u2-${site}-${item.key}`" class="kpi kpi-center"
                 :class="isOn(site, item.key) ? 'kpi-on' : ''">
              <div class="k">{{ labelFor(site, item.key, item.label) }}</div>
              <div class="v">{{ fmtEntity(getEnt(site, item.key)) }}</div>
            </div>
          </div>
          <div class="row3">
            <div v-for="item in userForecastDefs.filter(i => isMapped(site, i.key))" :key="`u3-${site}-${item.key}`" class="kpi kpi-center"
                 :class="isOn(site, item.key) ? 'kpi-on' : ''">
              <div class="k">{{ labelFor(site, item.key, item.label) }}</div>
              <div class="v">{{ fmtEntity(getEnt(site, item.key)) }}</div>
            </div>
          </div>

          <div class="card inner">
            <div class="row"><strong>Entità selezionate (flag ON)</strong></div>
            <div v-if="selectedEntities(site).length === 0" class="muted">Nessuna entità selezionata.</div>
            <div v-else class="entity-list">
              <div v-for="item in selectedEntities(site)" :key="`sel-${site}-${item.key}`"
                   class="entity-row row-on clickable" @click="openHistory(item, site)">
                <span class="entity-name">{{ item.label }}</span>
                <span class="entity-value">{{ item.value }}</span>
              </div>
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

      <section v-else-if="tab==='admin'" class="card">
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
          <span class="muted" v-if="dbInfo?.size_human">DB: {{ dbInfo.size_human }}</span>
        </div>

        <div class="form">
          <h3 class="section">Configurazione</h3>
          <div class="actions">
            <button class="ghost" @click="generateReport">Genera report ora</button>
          </div>
          <div v-if="reportStatus?.ok" class="muted">Report generato: {{ reportStatus.date }} in {{ reportStatus.dir }}</div>
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
          <div class="field">
            <label>Visualizzazione entità</label>
            <div class="actions">
              <button class="ghost" @click="showAll = !showAll">
                {{ showAll ? 'Mostra solo importate' : 'Mostra tutte' }}
              </button>
            </div>
            <div class="help">Di default mostra solo le entità importate. Attiva “Mostra tutte” per aggiungere manualmente.</div>
          </div>
          <div v-for="site in siteList" :key="`site-${site}`" class="set-section">
            <div class="section-title">
              Utenza {{ site }}
              <span class="muted" v-if="deviceLabel(site)"> — {{ deviceLabel(site) }}</span>
            </div>
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
              <label class="toggle">
                <input type="checkbox" v-model="overwriteMap[site]">
                <span>Sovrascrivi mappature esistenti</span>
              </label>
              <button class="ghost" :disabled="!canAutoMap(site)" @click="autoMapSite(site)">Importa entità da dispositivo</button>
              <button class="ghost" :disabled="!canAutoMap(site)" @click="syncAllEntities(site)">Sincronizza elenco completo</button>
              <div class="help" v-if="!canAutoMap(site)">Inserisci Device name o Device ID, oppure seleziona un dispositivo.</div>
            </div>
            <div v-if="visibleEntityDefs(site).length === 0" class="muted">Nessuna entità importata. Usa “Importa entità da dispositivo”.</div>
            <div v-for="item in visibleEntityDefs(site)" :key="`s${site}_${item.key}`" class="field">
              <label class="label-row">
                <span>{{ labelFor(site, item.key, item.label) }}</span>
                <span class="state-flag" :class="isOn(site, item.key) ? 'state-on' : 'state-off'">
                  <input class="flag-checkbox" type="checkbox" :checked="isOn(site, item.key)"
                         @change="toggleManual(site, item.key)"/>
                  <span>{{ isOn(site, item.key) ? 'ON' : 'OFF' }}</span>
                </span>
              </label>
              <div class="input-row">
                <span class="logic-dot" :class="isFilled(ent?.[`s${site}_${item.key}`]?.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
                <input type="text"
                       :class="[isFilled(ent?.[`s${site}_${item.key}`]?.entity_id) ? 'input-ok' : '', isOn(site, item.key) ? 'input-on' : '']"
                       v-model="ent[`s${site}_${item.key}`].entity_id"
                       :placeholder="item.placeholder || 'sensor.xxx'"
                       @input="dirtyEnt[`s${site}_${item.key}`] = true"
                       @focus="onFocus" @blur="onBlur"/>
              </div>
              <div v-if="item.help" class="help">{{ item.help }}</div>
            </div>
            <div v-for="e in allEntities(site)" :key="`all-${site}-${e.entity_id}`" class="field field-readonly">
              <label class="label-row">
                <span>{{ e.name || e.original_name || e.entity_id }}</span>
                <span class="state-flag" :class="isOnKey(`all_s${site}_${e.entity_id}`) ? 'state-on' : 'state-off'">
                  <input class="flag-checkbox" type="checkbox" :checked="isOnKey(`all_s${site}_${e.entity_id}`)"
                         @change="toggleManualKey(`all_s${site}_${e.entity_id}`)"/>
                  <span>{{ isOnKey(`all_s${site}_${e.entity_id}`) ? 'ON' : 'OFF' }}</span>
                </span>
              </label>
              <div class="input-row">
                <span class="logic-dot" :class="isFilled(e.entity_id) ? 'logic-ok' : 'logic-no'">●</span>
                <input type="text" :class="[isOnKey(`all_s${site}_${e.entity_id}`) ? 'input-on' : '']" :value="e.entity_id" readonly />
              </div>
            </div>
          </div>
          <div class="actions">
            <button class="ghost" @click="saveEntities">Salva sensori</button>
            <button class="ghost danger" @click="resetEntities">Reset entità</button>
          </div>
        </details>

        <div class="actions">
          <button class="ghost" @click="loadAll">Ricarica</button>
        </div>
      </section>

      <section v-else-if="tab==='automation_settings'" class="card">
        <h2>Automation setting</h2>
        <p class="muted">Configurazione automazioni e campi dedicati per la vista istantanea.</p>
        <div class="form" v-if="sp">
          <h3 class="section">Campi dedicati (diagramma istantaneo)</h3>
          <div class="help">Inserisci le entità da usare nella vista “Automazioni interface”.</div>
          <div v-for="site in siteList" :key="`flow-${site}`" class="set-section">
            <div class="section-title">
              Utenza {{ site }}
              <span class="muted" v-if="deviceLabel(site)"> — {{ deviceLabel(site) }}</span>
            </div>
            <div class="field">
              <label>PV Power (W)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].pv" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Consumo casa (W)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].load" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Batteria Power (W)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].battery" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Rete / PCC (W)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].grid" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>SOC Batteria (%)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].soc" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Batteria V</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].battery_v" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Batteria A</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].battery_a" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Produzione oggi (kWh)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].today_prod" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Consumo oggi (kWh)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].today_load" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Export oggi (kWh)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].today_export" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
          </div>
        </div>
        <div class="form" v-if="sp">
          <h3 class="section">Datalogging extra</h3>
          <div class="help">Aggiungi entità extra da registrare nel database storico.</div>
          <div v-for="site in siteList" :key="`datalog-${site}`" class="set-section">
            <div class="section-title">Utenza {{ site }}</div>
            <div class="field">
              <label>Nuova entità da datalog</label>
              <div class="input-row">
                <input type="text" v-model="newDatalog[site]" placeholder="sensor.xxx" />
                <button class="ghost" @click="addDatalogEntity(site)">Aggiungi</button>
              </div>
              <div class="help">Inserisci l'`entity_id` completo.</div>
            </div>
            <div class="entity-list" v-if="extraDatalogList(site).length">
              <div class="entity-row" v-for="eid in extraDatalogList(site)" :key="`datalog-${site}-${eid}`">
                <span class="entity-name">{{ eid }}</span>
                <button class="ghost danger" @click="removeDatalogEntity(site, eid)">Rimuovi</button>
              </div>
            </div>
            <div class="muted" v-else>Nessuna entità extra.</div>
          </div>
        </div>
      </section>

      <section v-else class="card">
        <h2>Automazioni interface</h2>
        <p class="muted">Vista istantanea per utenza basata sui campi configurati in “Automation setting”.</p>
        <div v-for="site in siteList" :key="`auto-ui-${site}`" class="card inner">
          <div class="row">
            <strong>Utenza {{ site }}</strong>
            <span class="muted" v-if="deviceLabel(site)"> — {{ deviceLabel(site) }}</span>
          </div>
          <div class="flow-grid">
            <div class="flow-card">
              <div class="k">PV</div>
              <div class="v">{{ flowValue(site, 'pv') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Consumo</div>
              <div class="v">{{ flowValue(site, 'load') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Batteria</div>
              <div class="v">{{ flowValue(site, 'battery') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Rete</div>
              <div class="v">{{ flowValue(site, 'grid') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">SOC</div>
              <div class="v">{{ flowValue(site, 'soc') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Batteria V</div>
              <div class="v">{{ flowValue(site, 'battery_v') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Batteria A</div>
              <div class="v">{{ flowValue(site, 'battery_a') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Prod. oggi</div>
              <div class="v">{{ flowValue(site, 'today_prod') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Cons. oggi</div>
              <div class="v">{{ flowValue(site, 'today_load') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Export oggi</div>
              <div class="v">{{ flowValue(site, 'today_export') }}</div>
            </div>
          </div>
        </div>
      </section>
    </main>

    <div v-if="historyModal.open" class="modal-backdrop" @click="historyModal.open=false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <strong>{{ historyModal.title }}</strong>
          <button class="ghost" @click="historyModal.open=false">Chiudi</button>
        </div>
        <div v-if="historyModal.series.length === 0" class="muted">Nessun dato storico disponibile.</div>
        <svg v-else class="chart" viewBox="0 0 640 220" preserveAspectRatio="none">
          <g class="axis">
            <line x1="40" y1="10" x2="40" y2="210" />
            <line x1="40" y1="210" x2="630" y2="210" />
            <g v-for="(t, i) in chartMeta(historyModal.series).yTicks" :key="`y-${i}`">
              <line :x1="40" :y1="t.y" :x2="630" :y2="t.y" class="grid"/>
              <text :x="36" :y="t.y + 4" text-anchor="end">{{ t.label }}</text>
            </g>
            <g v-for="(t, i) in chartMeta(historyModal.series).xTicks" :key="`x-${i}`">
              <line :x1="t.x" :y1="210" :x2="t.x" :y2="10" class="grid"/>
              <text :x="t.x" :y="218" text-anchor="middle">{{ t.label }}</text>
            </g>
          </g>
          <path :d="chartMeta(historyModal.series).path" fill="none" stroke="var(--accent)" stroke-width="2" />
        </svg>
        <div v-if="historyModal.series.length > 0" class="muted">
          Range: 24h · punti: {{ historyModal.series.length }} · unità: {{ historyModal.unit || '-' }}
        </div>
        <div v-if="historyModal.samples.length > 0" class="muted">
          Esempi XY:
          <span v-for="(s, i) in historyModal.samples" :key="`s-${i}`" class="sample">
            ({{ s.t }}, {{ s.v }}{{ s.unit ? ' ' + s.unit : '' }})
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'

const tab = ref('user')
const sp = ref(null)
const ent = ref(null)
const status = ref(null)
const dbInfo = ref(null)
const lastUpdate = ref(null)
const pollMs = ref(3000)
const actions = ref([])
const analysis = ref({ ok: false, events: [], missing: [] })
const reportStatus = ref(null)
const insights = ref({ global: null, sites: [] })
let pollTimer = null
const editingCount = ref(0)
const dirtyEnt = ref({})
const showAll = ref(false)
const overwriteMap = ref({ 1: false, 2: false, 3: false })
const manualFlags = ref({})
const historyModal = ref({ open: false, title: '', series: [], unit: '', samples: [] })
const allEntitiesState = ref({ 1: [], 2: [], 3: [] })
const newDatalog = ref({ 1: '', 2: '', 3: '' })

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

const userKpiDefs = [
  { key: 'pv_power', label: 'PV Power' },
  { key: 'pv_power_total', label: 'PV Power Totale' },
  { key: 'load_power', label: 'Carico casa' },
  { key: 'grid_power', label: 'Rete (PCC)' },
  { key: 'grid_import_power', label: 'Import rete' },
  { key: 'grid_export_power', label: 'Export rete' },
  { key: 'battery_power', label: 'Batteria Power' },
  { key: 'battery_soc', label: 'Batteria SOC' },
  { key: 'battery_temp', label: 'Batteria Temp' },
]
const userDailyDefs = [
  { key: 'today_production_kwh', label: 'Produzione oggi' },
  { key: 'today_load_kwh', label: 'Consumo oggi' },
  { key: 'today_import_kwh', label: 'Import oggi' },
  { key: 'today_export_kwh', label: 'Export oggi' },
]
const userForecastDefs = [
  { key: 'forecast_today_kwh', label: 'Forecast oggi' },
  { key: 'forecast_tomorrow_kwh', label: 'Forecast domani' },
]

const siteList = computed(() => {
  const n = Number(sp.value?.runtime?.sites_count || 1)
  const safe = Number.isFinite(n) ? Math.min(3, Math.max(1, Math.round(n))) : 1
  return Array.from({ length: safe }, (_, i) => i + 1)
})

const isFilled = (v) => (typeof v === 'string' ? v.trim().length > 0 : false)
const isMapped = (site, key) => {
  const eid = ent.value?.[`s${site}_${key}`]?.entity_id || ''
  return String(eid).trim().length > 0
}
const fmtEntity = (e) => {
  if (!e) return 'n/d'
  const raw = e.state
  const unit = e.attributes?.unit_of_measurement || ''
  if (raw === null || raw === undefined) return 'n/d'
  const num = Number(raw)
  if (Number.isFinite(num)) return `${num} ${unit}`.trim()
  return `${raw} ${unit}`.trim()
}
const fmtEntityRaw = (st, attrs) => {
  if (st === null || st === undefined) return 'n/d'
  const unit = attrs?.unit_of_measurement || ''
  const num = Number(st)
  if (Number.isFinite(num)) return `${num} ${unit}`.trim()
  return `${st} ${unit}`.trim()
}
const getEnt = (site, key) => {
  if (!ent.value) return null
  return ent.value[`s${site}_${key}`] || null
}
const isOnKey = (k) => {
  const manual = manualFlags.value?.[k]
  if (typeof manual === 'boolean') return manual
  return false
}
const isOn = (site, key) => isOnKey(`s${site}_${key}`)
const toggleManualKey = async (k) => {
  const cur = manualFlags.value?.[k]
  const next = !(cur === true)
  manualFlags.value = { ...manualFlags.value, [k]: next }
  try {
    localStorage.setItem('energymind_manual_flags', JSON.stringify(manualFlags.value))
  } catch {}
  if (sp.value?.runtime) {
    sp.value.runtime.ui_flags = { ...manualFlags.value }
    await saveConfig()
  }
}
const toggleManual = async (site, key) => toggleManualKey(`s${site}_${key}`)
const labelFor = (site, key, fallback) => {
  const e = getEnt(site, key)
  const fn = e?.attributes?.friendly_name
  return (typeof fn === 'string' && fn.trim().length > 0) ? fn : fallback
}
const deviceLabel = (site) => {
  const dev = sp.value?.devices?.[`s${site}`] || {}
  const name = String(dev.name || '').trim()
  const id = String(dev.id || '').trim()
  return name || (id ? `ID ${id}` : '')
}
const allEntities = (site) => {
  const list = allEntitiesState.value?.[site] || []
  if (list.length > 0) return list
  return sp.value?.all_entities?.[`s${site}`] || []
}
const extraDatalogList = (site) => {
  const list = sp.value?.automation?.extra_datalog_entities || []
  return list.filter((e) => e.site === site).map((e) => e.entity_id)
}
const addDatalogEntity = async (site) => {
  const raw = String(newDatalog.value?.[site] || '').trim()
  if (!raw) return
  const list = sp.value?.automation?.extra_datalog_entities || []
  const exists = list.some((e) => e.site === site && e.entity_id === raw)
  if (!exists) {
    list.push({ site, entity_id: raw })
    sp.value.automation.extra_datalog_entities = list
    await saveConfig()
  }
  newDatalog.value = { ...newDatalog.value, [site]: '' }
}
const removeDatalogEntity = async (site, entity_id) => {
  const list = sp.value?.automation?.extra_datalog_entities || []
  sp.value.automation.extra_datalog_entities = list.filter((e) => !(e.site === site && e.entity_id === entity_id))
  await saveConfig()
}
const visibleEntityDefs = (site) => {
  if (showAll.value) return energyEntityDefs
  return energyEntityDefs.filter((item) => {
    const eid = ent.value?.[`s${site}_${item.key}`]?.entity_id || ''
    return String(eid).trim().length > 0
  })
}
const mappedEntries = (site) => {
  return energyEntityDefs.filter((item) => isMapped(site, item.key))
}
const selectedEntities = (site) => {
  const out = []
  for (const item of energyEntityDefs) {
    const key = `s${site}_${item.key}`
    if (isOnKey(key) && isMapped(site, item.key)) {
      const entityId = getEnt(site, item.key)?.entity_id || ''
    out.push({
      key,
      label: labelFor(site, item.key, item.label),
      value: fmtEntity(getEnt(site, item.key)),
      entity_id: entityId,
      history: true,
    })
    }
  }
  for (const e of allEntities(site)) {
    const key = `all_s${site}_${e.entity_id}`
    if (!isOnKey(key)) continue
    out.push({
      key,
      label: e.name || e.original_name || e.entity_id,
      value: fmtEntityRaw(e.state, e.attributes),
      entity_id: e.entity_id,
      history: true,
    })
  }
  return out
}

const entityById = (site, entity_id) => {
  if (!entity_id) return null
  const list = allEntities(site)
  const found = list.find((e) => e.entity_id === entity_id)
  if (found) return found
  for (const item of energyEntityDefs) {
    const e = getEnt(site, item.key)
    if (e?.entity_id === entity_id) {
      return {
        entity_id: e.entity_id,
        name: e.attributes?.friendly_name,
        original_name: e.attributes?.friendly_name,
        state: e.state,
        attributes: e.attributes,
        icon: e.icon,
      }
    }
  }
  return null
}
const flowValue = (site, key) => {
  const eid = sp.value?.automation?.flow_entities?.[`s${site}`]?.[key] || ''
  if (!eid) return 'n/d'
  const e = entityById(site, eid)
  if (!e) return 'n/d'
  return fmtEntityRaw(e.state, e.attributes)
}

async function openHistory(item, site){
  if (!item?.entity_id) return
  const r = await fetch(`/api/history?site=${site}&hours=24&entity_id=${encodeURIComponent(item.entity_id)}`)
  if (!r.ok) return
  const data = await r.json()
  const items = Array.isArray(data.items) ? data.items : []
  const samples = pickSamples(items)
  historyModal.value = {
    open: true,
    title: item.label,
    unit: items.find(i => i.unit)?.unit || '',
    series: items,
    samples
  }
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
  if (!sp.value.automation) {
    sp.value.automation = {
      flow_entities: { s1: {}, s2: {}, s3: {} },
      extra_datalog_entities: []
    }
  }
  if (!sp.value.automation.flow_entities) {
    sp.value.automation.flow_entities = { s1: {}, s2: {}, s3: {} }
  }
  for (const key of ['s1','s2','s3']) {
    if (!sp.value.automation.flow_entities[key]) sp.value.automation.flow_entities[key] = {}
    const flow = sp.value.automation.flow_entities[key]
    for (const k of ['pv','load','battery','grid','soc','battery_v','battery_a','today_prod','today_load','today_export']) {
      if (typeof flow[k] !== 'string') flow[k] = ''
    }
  }
  if (!Array.isArray(sp.value.automation.extra_datalog_entities)) {
    sp.value.automation.extra_datalog_entities = []
  }
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
  if (sp.value?.runtime?.ui_flags && typeof sp.value.runtime.ui_flags === 'object') {
    manualFlags.value = { ...sp.value.runtime.ui_flags }
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
async function loadAllEntities(site){
  try {
    const r = await fetch(`/api/entities_all?site=${site}`)
    if (!r.ok) return
    const data = await r.json()
    const items = Array.isArray(data.items) ? data.items : []
    allEntitiesState.value = { ...allEntitiesState.value, [site]: items }
  } catch {}
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
async function resetEntities(){
  const ok = window.confirm('Resettare tutte le entità? Operazione irreversibile.')
  if (!ok) return
  await fetch('/api/entities/reset',{method:'POST'})
  await loadEntities()
  await refresh()
}
async function autoMapSite(site){
  if (!sp.value?.devices) return
  const dev = sp.value.devices[`s${site}`] || {}
  if (!canAutoMap(site)) {
    window.alert('Inserisci Device name o Device ID, oppure seleziona un dispositivo')
    return
  }
  const payload = { site, device_name: dev.name || '', device_id: dev.id || '', overwrite: !!overwriteMap.value[site] }
  const r = await fetch('/api/auto_map',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
  if (!r.ok) {
    window.alert('Importa entità fallito')
    return
  }
  const data = await r.json()
  if (data.device && sp.value?.devices?.[`s${site}`]) {
    sp.value.devices[`s${site}`].name = data.device
    await saveConfig()
  }
  await loadConfig()
  await loadAllEntities(site)
  await loadEntities()
  await refresh()
  window.alert(`Importate: ${data.mapped || 0} entità (trovate: ${data.matched || 0}, già presenti: ${data.skipped_existing || 0}, totali: ${data.total_entities || 0})`)
}
async function syncAllEntities(site){
  if (!sp.value?.devices) return
  const dev = sp.value.devices[`s${site}`] || {}
  if (!canAutoMap(site)) {
    window.alert('Inserisci Device name o Device ID')
    return
  }
  const payload = { site, device_name: dev.name || '', device_id: dev.id || '' }
  const r = await fetch('/api/all_entities_sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
  if (!r.ok) {
    window.alert('Sync elenco fallito')
    return
  }
  const data = await r.json()
  if (data.device && sp.value?.devices?.[`s${site}`]) {
    sp.value.devices[`s${site}`].name = data.device
    await saveConfig()
  }
  await loadConfig()
  await loadAllEntities(site)
  window.alert(`Elenco completo aggiornato: ${data.total || 0} entità`)
}
async function refresh(){
  if (tab.value === 'admin' || editingCount.value > 0) return
  const s = await fetch('/api/status')
  status.value = await s.json()
  const d = await fetch('/api/db_info')
  dbInfo.value = await d.json()
  const a = await fetch('/api/actions')
  actions.value = (await a.json()).items || []
  if (tab.value === 'user') {
    try {
      const an = await fetch(`/api/analysis?site=1&hours=24`)
      analysis.value = await an.json()
      const ins = await fetch('/api/insights')
      insights.value = await ins.json()
    } catch {}
  }
  await loadEntities()
  lastUpdate.value = new Date()
}

async function generateReport(){
  try {
    const r = await fetch('/api/reports/generate', { method: 'POST' })
    if (!r.ok) return
    reportStatus.value = await r.json()
  } catch {}
}
async function loadAll(){
  await loadConfig()
  await loadEntities()
  for (const site of [1,2,3]) {
    await loadAllEntities(site)
  }
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

function chartPath(series){
  const pts = series
    .map(p => ({ x: Number(p.ts), y: Number(p.value) }))
    .filter(p => Number.isFinite(p.x) && Number.isFinite(p.y))
  if (pts.length === 0) return ''
  const minX = Math.min(...pts.map(p => p.x))
  const maxX = Math.max(...pts.map(p => p.x))
  const minY = Math.min(...pts.map(p => p.y))
  const maxY = Math.max(...pts.map(p => p.y))
  const left = 40, right = 10, top = 10, bottom = 10
  const w = 640 - left - right
  const h = 220 - top - bottom
  const dx = maxX === minX ? 1 : (maxX - minX)
  const dy = maxY === minY ? 1 : (maxY - minY)
  const scaleX = (x) => left + ((x - minX) / dx) * w
  const scaleY = (y) => top + h - ((y - minY) / dy) * h
  let d = `M ${scaleX(pts[0].x)} ${scaleY(pts[0].y)}`
  for (let i = 1; i < pts.length; i++) {
    d += ` L ${scaleX(pts[i].x)} ${scaleY(pts[i].y)}`
  }
  return d
}

function chartMeta(series){
  const pts = series
    .map(p => ({ x: Number(p.ts), y: Number(p.value) }))
    .filter(p => Number.isFinite(p.x) && Number.isFinite(p.y))
  if (pts.length === 0) return { path: '', xTicks: [], yTicks: [] }
  const minX = Math.min(...pts.map(p => p.x))
  const maxX = Math.max(...pts.map(p => p.x))
  const minY = Math.min(...pts.map(p => p.y))
  const maxY = Math.max(...pts.map(p => p.y))
  const left = 40, right = 10, top = 10, bottom = 10
  const w = 640 - left - right
  const h = 220 - top - bottom
  const dx = maxX === minX ? 1 : (maxX - minX)
  const dy = maxY === minY ? 1 : (maxY - minY)
  const scaleX = (x) => left + ((x - minX) / dx) * w
  const scaleY = (y) => top + h - ((y - minY) / dy) * h
  const path = chartPath(series)
  const yTicks = []
  for (let i = 0; i <= 4; i++) {
    const v = minY + (dy * i / 4)
    yTicks.push({ y: scaleY(v), label: v.toFixed(2) })
  }
  const xTicks = []
  for (let i = 0; i <= 4; i++) {
    const v = minX + (dx * i / 4)
    xTicks.push({ x: scaleX(v), label: fmtTs(v) })
  }
  return { path, xTicks, yTicks }
}

function fmtTs(ts){
  const d = new Date(ts * 1000)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

function pickSamples(items){
  if (!Array.isArray(items) || items.length === 0) return []
  if (items.length <= 3) {
    return items.map(i => ({ t: fmtTs(i.ts), v: i.value, unit: i.unit }))
  }
  const mid = items[Math.floor(items.length / 2)]
  const first = items[0]
  const last = items[items.length - 1]
  return [
    { t: fmtTs(first.ts), v: first.value, unit: first.unit },
    { t: fmtTs(mid.ts), v: mid.value, unit: mid.unit },
    { t: fmtTs(last.ts), v: last.value, unit: last.unit },
  ]
}

function siteInsight(site){
  return insights.value?.sites?.find(s => s.site === site)
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
  // One-time recovery: if config has no flags but localStorage has them, restore.
  try {
    const raw = localStorage.getItem('energymind_manual_flags')
    if (raw) {
      const lsFlags = JSON.parse(raw) || {}
      const hasCfgFlags = sp.value?.runtime?.ui_flags && Object.keys(sp.value.runtime.ui_flags).length > 0
      if (!hasCfgFlags && Object.keys(lsFlags).length > 0) {
        manualFlags.value = { ...lsFlags }
        if (sp.value?.runtime) {
          sp.value.runtime.ui_flags = { ...lsFlags }
          await saveConfig()
        }
      }
    }
  } catch {}
  startPolling()
})
watch(tab, (t) => {
  if (t === 'admin') {
    stopPolling()
  } else {
    editingCount.value = 0
    startPolling()
  }
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
.kpi-on{
  background:rgba(45,212,191,0.12);
  border-color:rgba(45,212,191,0.6);
}
.kpi-center{ text-align:center; }
.k{ font-size:12px; color:var(--muted); }
.v{ font-size:18px; font-weight:700; margin-top:6px; }
.entity-list{
  margin-top:8px;
  display:flex;
  flex-direction:column;
  gap:6px;
}
.entity-list-full{
  max-height:520px;
  overflow:auto;
  padding-right:6px;
}
.field-readonly input{
  opacity:0.85;
}
.entity-row{
  display:flex;
  justify-content:space-between;
  gap:12px;
  padding:6px 8px;
  border:1px solid var(--line);
  border-radius:8px;
  background:#0b121a;
}
.row-on{
  background:rgba(45,212,191,0.12);
  border-color:rgba(45,212,191,0.6);
}
.entity-name{ color:var(--muted); }
.entity-value{ font-weight:600; }
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
.actions .danger{
  border-color:rgba(255,107,107,0.6);
  color:var(--danger);
}
.toggle{
  display:flex;
  align-items:center;
  gap:8px;
  color:var(--muted);
  font-size:13px;
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
.input-on{
  background:rgba(45,212,191,0.12) !important;
  border-color:rgba(45,212,191,0.6) !important;
}
.label-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:10px;
}
.state-flag{
  font-size:11px;
  font-weight:700;
  padding:2px 8px;
  border-radius:999px;
  border:1px solid var(--line);
  color:var(--muted);
  display:flex;
  align-items:center;
  gap:6px;
}
.flag-checkbox{
  width:14px;
  height:14px;
  accent-color: #2dd4bf;
}
.state-on{
  border-color:rgba(45,212,191,0.6);
  color:var(--ok);
  background:rgba(45,212,191,0.12);
}
.state-off{
  border-color:rgba(107,114,128,0.4);
  color:var(--off);
}
.entity-row.clickable{
  cursor:pointer;
}
.flow-grid{
  margin-top:10px;
  display:grid;
  grid-template-columns:repeat(5, minmax(140px,1fr));
  gap:10px;
}
.flow-card{
  background:#0b121a;
  border:1px solid var(--line);
  border-radius:12px;
  padding:10px 12px;
}
.modal-backdrop{
  position:fixed;
  inset:0;
  background:rgba(0,0,0,0.6);
  display:flex;
  align-items:center;
  justify-content:center;
  z-index:20;
}
.modal{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:14px;
  padding:14px;
  width:min(900px, 92vw);
  box-shadow:var(--shadow);
}
.modal-header{
  display:flex;
  align-items:center;
  justify-content:space-between;
  margin-bottom:8px;
}
.chart{
  width:100%;
  height:240px;
  background:#0b121a;
  border:1px solid var(--line);
  border-radius:10px;
  margin:8px 0;
}
.axis line{
  stroke:rgba(159,176,195,0.35);
  stroke-width:1;
}
.axis text{
  fill:var(--muted);
  font-size:10px;
}
.axis .grid{
  stroke:rgba(159,176,195,0.12);
}
.sample{
  margin-left:8px;
  display:inline-block;
}

@media (max-width: 1100px){
  .grid{ grid-template-columns:repeat(2, minmax(140px,1fr)); }
  .row3{ grid-template-columns:repeat(2, minmax(160px,1fr)); }
  .flow-grid{ grid-template-columns:repeat(2, minmax(160px,1fr)); }
}
@media (max-width: 900px){
  .top-inner{ grid-template-columns:1fr; justify-items:start; }
  .top-center{ justify-content:flex-start; }
  .top-right{ justify-content:flex-start; }
}
@media (max-width: 640px){
  .grid{ grid-template-columns:1fr; }
  .row3{ grid-template-columns:1fr; }
  .flow-grid{ grid-template-columns:1fr; }
  .top{ position:static; }
}
</style>
