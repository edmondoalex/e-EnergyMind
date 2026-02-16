<template>
  <div class="wrap">
    <header class="top">
      <div class="top-inner">
        <div class="top-left">
          <div class="brand">e-EnergyMind</div>
        </div>
        <div class="top-center">
          <div class="top-actions">
            <button class="action-btn" @click="refresh">Aggiorna</button>
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
            <button :class="{active: tab==='view_card'}" @click="tab='view_card'">View-Card</button>
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
        <div class="card inner" v-if="insights?.learned_rules">
          <div class="row"><strong>Regole apprese</strong></div>
          <div class="muted" v-if="!insights.learned_rules.updated_at">In attesa aggiornamento...</div>
          <div class="entity-list" v-else>
            <div class="entity-row">
              <span class="entity-name">Aggiornate</span>
              <span class="entity-value">{{ new Date(insights.learned_rules.updated_at * 1000).toLocaleString() }}</span>
            </div>
            <div class="entity-row" v-for="site in siteList" :key="`lr-${site}`">
              <span class="entity-name">{{ siteTitle(site) }}</span>
              <span class="entity-value">
                Export> {{ insights.learned_rules[`site${site}`]?.export_threshold_w ?? 'n/d' }}W ·
                Surplus> {{ insights.learned_rules[`site${site}`]?.min_surplus_w ?? 'n/d' }}W ·
                Durata {{ insights.learned_rules[`site${site}`]?.min_duration_s ?? 'n/d' }}s ·
                Carica tipica {{ insights.learned_rules[`site${site}`]?.typical_charge_pct ?? 'n/d' }}%
              </span>
            </div>
          </div>
        </div>
        <div class="card inner" v-if="forecast?.sites?.length">
          <div class="row"><strong>Previsioni Solar e-EnergyMind</strong></div>
          <div class="muted" v-if="!forecast.updated_at">In attesa dati...</div>
          <div class="forecast-table" v-else>
            <div class="forecast-row forecast-head">
              <div>Utenza</div>
              <div>PV Oggi</div>
              <div>PV Domani</div>
              <div>Consumo Oggi</div>
              <div>Consumo Domani</div>
              <div>Surplus Oggi</div>
              <div>Export Oggi</div>
              <div>SOC Fine</div>
              <div>Cap. kWh</div>
              <div>Max C/D W</div>
              <div>Fattore PV</div>
            </div>
            <div class="forecast-row" v-for="row in forecast.sites" :key="`fc-${row.site}`">
              <div>{{ row.name || siteTitle(row.site) }}</div>
              <div>{{ fmtKwh(row.pv_today_kwh) }}</div>
              <div>{{ fmtKwh(row.pv_tomorrow_kwh) }}</div>
              <div>{{ fmtKwh(row.load_today_kwh) }}</div>
              <div>{{ fmtKwh(row.load_tomorrow_kwh) }}</div>
              <div>{{ fmtKwh(row.surplus_today_kwh) }}</div>
              <div>{{ fmtKwh(row.export_today_kwh) }}</div>
              <div>{{ fmtPct(row.end_soc) }}</div>
              <div>{{ fmtNum(row.capacity_kwh) }}</div>
              <div>{{ fmtChargeDischarge(row.max_charge_w, row.max_discharge_w) }}</div>
              <div>{{ fmtFactor(row.factors?.pv_adjust) }}</div>
            </div>
          </div>
          <div class="muted forecast-note">Se un campo è vuoto, viene stimato automaticamente dai dati storici.</div>
        </div>
        <div class="card inner" v-if="forecast?.sites?.length">
          <div class="row"><strong>Profilo Orario (oggi)</strong></div>
          <div class="muted" v-if="!forecast.updated_at">In attesa dati...</div>
          <div v-else class="hourly-wrap">
            <div class="hourly-block" v-for="row in forecast.sites" :key="`hourly-${row.site}`">
              <div class="row"><strong>{{ row.name || siteTitle(row.site) }}</strong></div>
              <div class="hourly-table">
                <div class="hourly-row hourly-head">
                  <div>Ora</div>
                  <div>PV (W)</div>
                  <div>Load (W)</div>
                  <div>Surplus (W)</div>
                </div>
                <div class="hourly-row" v-for="h in row.hourly || []" :key="`h-${row.site}-${h.h}`">
                  <div>{{ String(h.h).padStart(2,'0') }}:00</div>
                  <div>{{ fmtW(h.pv_w) }}</div>
                  <div>{{ fmtW(h.load_w) }}</div>
                  <div>{{ fmtW(h.surplus_w) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="card inner" v-if="forecast?.sites?.length">
          <div class="row"><strong>Profilo Orario (domani)</strong></div>
          <div class="muted" v-if="!forecast.updated_at">In attesa dati...</div>
          <div v-else class="hourly-wrap">
            <div class="hourly-block" v-for="row in forecast.sites" :key="`hourly-tom-${row.site}`">
              <div class="row"><strong>{{ row.name || siteTitle(row.site) }}</strong></div>
              <div class="hourly-table">
                <div class="hourly-row hourly-head">
                  <div>Ora</div>
                  <div>PV (W)</div>
                  <div>Load (W)</div>
                  <div>Surplus (W)</div>
                </div>
                <div class="hourly-row" v-for="h in row.hourly_tomorrow || []" :key="`ht-${row.site}-${h.h}`">
                  <div>{{ String(h.h).padStart(2,'0') }}:00</div>
                  <div>{{ fmtW(h.pv_w) }}</div>
                  <div>{{ fmtW(h.load_w) }}</div>
                  <div>{{ fmtW(h.surplus_w) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="insights-compare" v-if="ent">
          <div v-for="site in siteList" :key="`ins-${site}`" class="card inner">
            <div class="row"><strong>Intelligenza {{ siteTitle(site) }}</strong></div>
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
          <div class="row">
            <strong>{{ siteTitle(site) }}</strong>
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
          <div class="actions">
            <label class="muted">Verifica logging (ore):</label>
            <input type="number" min="1" max="168" v-model.number="loggingHours" style="width:90px" />
            <button class="ghost" @click="runLoggingCheck()">Verifica logging</button>
          </div>
          <div v-if="loggingCheck?.ok" class="muted">
            Mappate: {{ loggingCheck.total_mapped }} · Presenti: {{ loggingCheck.total_present }} · Mancanti: {{ loggingCheck.total_missing }}
          </div>
          <div v-if="loggingCheck?.ok && loggingCheck.total_missing > 0" class="entity-list">
            <div class="entity-row" v-for="item in loggingCheck.missing" :key="`miss-${item.site}-${item.key}`">
              <span class="entity-name">Utenza {{ item.site }} · {{ item.key }}</span>
              <span class="entity-value">{{ item.entity_id }}</span>
            </div>
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
          <div v-if="sp" class="field">
            <label>Segno rete (export positivo)</label>
            <select v-model="sp.runtime.grid_export_positive" @change="saveConfig">
              <option :value="true">Export positivo, Import negativo</option>
              <option :value="false">Export negativo, Import positivo</option>
            </select>
            <div class="help">Imposta la convenzione di segno del sensore rete.</div>
          </div>
        </div>

        <div class="form" v-if="ent">
          <div class="section">Sensori energia (read-only)</div>
          <div class="field">
            <label>Visualizzazione entità</label>
            <div class="actions">
              <button class="ghost" @click="showAll = !showAll">
                {{ showAll ? 'Mostra solo importate' : 'Mostra tutte' }}
              </button>
            </div>
            <div class="help">Di default mostra solo le entità importate. Attiva “Mostra tutte” per aggiungere manualmente.</div>
          </div>
          <details v-for="site in siteList" :key="`site-${site}`" class="set-section" open>
            <summary class="section-title">{{ siteTitle(site) }}</summary>
            <div class="field">
              <label>Filtra entità</label>
              <input type="text" v-model="adminFilter[site]" placeholder="cerca: load, carico, pv..." />
              <div class="help">Filtra per nome, chiave o entity_id.</div>
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
            <div v-if="filteredEntityDefs(site).length === 0" class="muted">Nessuna entità importata. Usa “Importa entità da dispositivo”.</div>
            <div v-for="item in filteredEntityDefs(site)" :key="`s${site}_${item.key}`" class="field">
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
            <div v-for="e in filteredAllEntities(site)" :key="`all-${site}-${e.entity_id}`" class="field field-readonly">
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
          </details>
          <div class="actions">
            <button class="ghost" @click="saveEntities">Salva sensori</button>
            <button class="ghost danger" @click="resetEntities">Reset entità</button>
          </div>
        </div>

        <div class="form" v-if="sp">
          <h3 class="section">Previsioni Solar e-EnergyMind (parametri)</h3>
          <div class="help">Se lasci vuoto, il valore viene stimato automaticamente dai dati storici.</div>
          <details v-for="site in siteList" :key="`forecast-${site}`" class="set-section" open>
            <summary class="section-title">{{ siteTitle(site) }}</summary>
            <div class="field">
              <label>Forecast PV Oggi (kWh)</label>
              <input type="text" v-model="sp.forecast[`s${site}`].pv_forecast_today" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Forecast PV Oggi Orario (W)</label>
              <input type="text" v-model="sp.forecast[`s${site}`].pv_forecast_today_hourly" placeholder="sensor.energy_production_today_4" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Forecast PV Domani (kWh)</label>
              <input type="text" v-model="sp.forecast[`s${site}`].pv_forecast_tomorrow" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Forecast PV Domani Orario (W)</label>
              <input type="text" v-model="sp.forecast[`s${site}`].pv_forecast_tomorrow_hourly" placeholder="sensor.energy_production_tomorrow_4" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Consumo giornaliero (kWh)</label>
              <input type="text" v-model="sp.forecast[`s${site}`].load_daily" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Capacità batteria (kWh)</label>
              <input type="number" step="0.1" v-model.number="sp.forecast[`s${site}`].battery_capacity_kwh" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Max carica (W)</label>
              <input type="number" step="10" v-model.number="sp.forecast[`s${site}`].max_charge_w" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Max scarica (W)</label>
              <input type="number" step="10" v-model.number="sp.forecast[`s${site}`].max_discharge_w" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>SOC minimo (%)</label>
              <input type="number" step="0.1" v-model.number="sp.forecast[`s${site}`].min_soc" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>SOC massimo (%)</label>
              <input type="number" step="0.1" v-model.number="sp.forecast[`s${site}`].max_soc" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Export limit (W)</label>
              <input type="number" step="10" v-model.number="sp.forecast[`s${site}`].export_limit_w" @change="saveConfig"/>
            </div>
          </details>
        </div>

        <div class="form" v-if="sp">
          <h3 class="section">Datalogging extra</h3>
          <div class="help">Aggiungi entità extra da registrare nel database storico.</div>
          <details v-for="site in siteList" :key="`datalog-admin-${site}`" class="set-section" open>
            <summary class="section-title">{{ siteTitle(site) }}</summary>
            <div class="field">
              <label>Nuova entità da datalog</label>
              <div class="input-row">
                <input type="text" v-model="newDatalog[site]" placeholder="sensor.xxx" />
                <button class="ghost" @click="addDatalogEntity(site)">Aggiungi</button>
              </div>
              <div class="help">Inserisci l'`entity_id` completo.</div>
            </div>
            <div class="entity-list" v-if="extraDatalogList(site).length">
              <div class="entity-row" v-for="item in extraDatalogItems(site)" :key="`datalog-admin-${site}-${item.entity_id}`">
                <span class="entity-name">{{ item.entity_id }}</span>
                <span class="state-flag" :class="item.enabled ? 'state-on' : 'state-off'">
                  <input class="flag-checkbox" type="checkbox" :checked="item.enabled"
                         @change="toggleExtraEnabled(site, item.entity_id)"/>
                  <span>{{ item.enabled ? 'ON' : 'OFF' }}</span>
                </span>
                <button class="ghost danger" @click="removeDatalogEntity(site, item.entity_id)">Rimuovi</button>
              </div>
            </div>
            <div class="muted" v-else>Nessuna entità extra.</div>
          </details>
        </div>

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
          <details v-for="site in siteList" :key="`flow-${site}`" class="set-section" open>
            <summary class="section-title">{{ siteTitle(site) }}</summary>
            <div class="field">
              <label>Solar SAS (W)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].pv_a" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Pannelli portoni (W)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].pv_b" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Produzione FV Totale (W)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].pv_total" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>PV Power (W)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].pv" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Consumo totale (W)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].load_total" placeholder="sensor.xxx" @change="saveConfig"/>
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
              <label>SOC Min/Target (%)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].soc_min" placeholder="sensor.xxx" @change="saveConfig"/>
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
              <label>Consumo casa oggi (kWh)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].today_house" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Export oggi (kWh)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].today_export" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Carica batteria oggi (kWh)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].today_charge" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Scarica batteria oggi (kWh)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].today_discharge" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Tensione (V)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].voltage" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
            <div class="field">
              <label>Frequenza (Hz)</label>
              <input type="text" v-model="sp.automation.flow_entities[`s${site}`].frequency" placeholder="sensor.xxx" @change="saveConfig"/>
            </div>
          </details>
        </div>
      </section>

      <section v-else-if="tab==='automation_interface'" class="card">
        <h2>Automazioni interface</h2>
        <p class="muted">Vista istantanea per utenza basata sui campi configurati in “Automation setting”.</p>
        <div v-for="site in siteList" :key="`auto-ui-${site}`" class="card inner">
          <div class="row">
            <strong>{{ siteTitle(site) }}</strong>
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
              <div class="k">Consumo casa oggi</div>
              <div class="v">{{ flowValue(site, 'today_house') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Export oggi</div>
              <div class="v">{{ flowValue(site, 'today_export') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Carica oggi</div>
              <div class="v">{{ flowValue(site, 'today_charge') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Scarica oggi</div>
              <div class="v">{{ flowValue(site, 'today_discharge') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Tensione</div>
              <div class="v">{{ flowValue(site, 'voltage') }}</div>
            </div>
            <div class="flow-card">
              <div class="k">Frequenza</div>
              <div class="v">{{ flowValue(site, 'frequency') }}</div>
            </div>
          </div>
        </div>
      </section>

      <section v-else-if="tab==='view_card'" class="card">
        <h2>View-Card</h2>
        <p class="muted">Vista grafica stile power-flow, animata e responsive.</p>
        <div v-for="site in siteList" :key="`view-${site}`" class="card inner viewcard-wrap">
          <div class="row">
            <strong>{{ siteTitle(site) }}</strong>
          </div>
          <div class="viewcard-panel">
            <div class="viewcard-title">{{ siteTitle(site).toUpperCase() }}</div>

            <div class="viewcard-box yellow viewcard-today">
              <div class="val">{{ flowValue(site,'today_prod') }}</div>
              <div class="lab">Energia solare oggi</div>
            </div>

            <div class="viewcard-box yellow viewcard-solar">
              <div class="val">{{ flowValueOr(site,'pv_total','pv') }}</div>
              <div class="lab">Solare</div>
            </div>

            <div class="viewcard-box yellow viewcard-house">
              <div class="val">{{ flowValue(site,'load') }}</div>
              <div class="lab">Consumo casa</div>
            </div>

            <div class="viewcard-box red viewcard-grid">
              <div class="val">{{ flowValue(site,'grid') }}</div>
              <div class="lab">Rete (import + / export -)</div>
            </div>

            <div class="viewcard-box purple viewcard-batt">
              <div class="val">{{ flowValue(site,'battery') }}</div>
              <div class="lab">Batteria (scarica + / carica -)</div>
            </div>

            <div class="viewcard-box purple viewcard-soc">
              <div class="val">{{ flowValue(site,'soc') }}</div>
              <div class="lab">SoC</div>
            </div>

            <div class="viewcard-box red viewcard-vf">
              <div class="val">{{ flowValue(site,'voltage') }}</div>
              <div class="lab">{{ flowValue(site,'frequency') }}</div>
            </div>

            <div class="viewcard-icon i-solar">
              <svg viewBox="0 0 64 64" fill="none">
                <path d="M10 40h28l-6 14H16l-6-14Z" stroke="currentColor" stroke-width="4" />
                <path d="M46 12l8 8M46 28h12M42 16l6 6" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
                <path d="M38 10l-6 18h10l-6 22" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
              </svg>
              <div>
                <div class="icon-title">FV</div>
                <div class="icon-cap">Produzione</div>
              </div>
            </div>

            <div class="viewcard-icon i-house">
              <svg viewBox="0 0 64 64" fill="none">
                <path d="M10 30 32 12l22 18v22H10V30Z" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
                <path d="M26 52V38h12v14" stroke="currentColor" stroke-width="4" />
              </svg>
              <div>
                <div class="icon-title">Casa</div>
                <div class="icon-cap">Consumo</div>
              </div>
            </div>

            <div class="viewcard-icon i-grid">
              <svg viewBox="0 0 64 64" fill="none">
                <path d="M20 54h24M24 54l8-36 8 36" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M22 30h20M20 40h24" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
              </svg>
              <div>
                <div class="icon-title">Rete</div>
                <div class="icon-cap">Linea</div>
              </div>
            </div>

            <div class="viewcard-icon i-batt">
              <svg viewBox="0 0 64 64" fill="none">
                <rect x="14" y="18" width="36" height="30" rx="4" stroke="currentColor" stroke-width="4"/>
                <path d="M50 28h4v10h-4" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
                <path d="M24 33h16" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
              </svg>
              <div>
                <div class="icon-title">Batteria</div>
                <div class="icon-cap">Accumulo</div>
              </div>
            </div>

            <svg class="viewcard-svg" viewBox="0 0 1200 675" preserveAspectRatio="none">
              <path class="pipe" d="M 260 235 H 520 V 360 H 860" />
              <path class="pipe" d="M 260 535 H 520" />
              <path class="pipe" d="M 520 360 V 535 H 860" />
              <path class="pipe" d="M 520 360 V 235" />

              <path id="flow_solar_house" class="flow yellow" :class="flowClass(site,'pv')" d="M 260 235 H 520 V 360 H 860" />
              <path id="flow_batt" class="flow purple" :class="flowClass(site,'battery')" d="M 260 535 H 520" />
              <path id="flow_grid" class="flow red" :class="flowClass(site,'grid')" d="M 520 360 V 535 H 860" />
            </svg>

            <div class="viewcard-footer">Dati da Home Assistant (sensor.xxx) via WebSocket</div>
          </div>
        </div>
      </section>
      <section v-else class="card">
        <h2>Pagina</h2>
        <p class="muted">Seleziona una tab.</p>
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
const forecast = ref(null)
const loggingCheck = ref(null)
const loggingHours = ref(24)
let pollTimer = null
const editingCount = ref(0)
const dirtyEnt = ref({})
const showAll = ref(true)
const overwriteMap = ref({ 1: false, 2: false, 3: false })
const manualFlags = ref({})
const historyModal = ref({ open: false, title: '', series: [], unit: '', samples: [] })
const allEntitiesState = ref({ 1: [], 2: [], 3: [] })
const newDatalog = ref({ 1: '', 2: '', 3: '' })
const flowStates = ref({})
const extraStates = ref({})
const adminFilter = ref({ 1: '', 2: '', 3: '' })

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
const fmtKwh = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return 'n/d'
  return `${Number(v).toFixed(2)} kWh`
}
const fmtPct = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return 'n/d'
  return `${Number(v).toFixed(1)} %`
}
const fmtNum = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return 'n/d'
  return Number(v).toFixed(2)
}
const fmtChargeDischarge = (c, d) => {
  if ((c === null || c === undefined) && (d === null || d === undefined)) return 'n/d'
  const cText = c === null || c === undefined ? 'n/d' : `${Math.round(Number(c))}`
  const dText = d === null || d === undefined ? 'n/d' : `${Math.round(Number(d))}`
  return `${cText} / ${dText}`
}
const fmtFactor = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return 'n/d'
  return `${Number(v).toFixed(2)}x`
}
const fmtW = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return 'n/d'
  return `${Math.round(Number(v))} W`
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
const siteTitle = (site) => {
  const label = deviceLabel(site)
  return label ? `Utenza ${site} — ${label}` : `Utenza ${site}`
}
const allEntities = (site) => {
  const list = allEntitiesState.value?.[site] || []
  if (list.length > 0) return list
  return sp.value?.all_entities?.[`s${site}`] || []
}
const extraDatalogItems = (site) => {
  const list = sp.value?.automation?.extra_datalog_entities || []
  return list.filter((e) => e.site === site).map((e) => ({
    site: e.site,
    entity_id: e.entity_id,
    enabled: e.enabled !== false
  }))
}
const extraDatalogList = (site) => extraDatalogItems(site).map((e) => e.entity_id)
const addDatalogEntity = async (site) => {
  const raw = String(newDatalog.value?.[site] || '').trim()
  if (!raw) return
  const list = sp.value?.automation?.extra_datalog_entities || []
  const exists = list.some((e) => e.site === site && e.entity_id === raw)
  if (!exists) {
    list.push({ site, entity_id: raw, enabled: true })
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
const toggleExtraEnabled = async (site, entity_id) => {
  const list = sp.value?.automation?.extra_datalog_entities || []
  const next = list.map((e) => {
    if (e.site === site && e.entity_id === entity_id) {
      return { ...e, enabled: !(e.enabled !== false) }
    }
    return e
  })
  sp.value.automation.extra_datalog_entities = next
  await saveConfig()
}
const visibleEntityDefs = (site) => {
  return energyEntityDefs
}
const mappedEntries = (site) => {
  return energyEntityDefs.filter((item) => isMapped(site, item.key))
}
const _filterText = (site) => String(adminFilter.value?.[site] || '').trim().toLowerCase()
const filteredEntityDefs = (site) => {
  const q = _filterText(site)
  if (!q) return visibleEntityDefs(site)
  return visibleEntityDefs(site).filter((item) => {
    const label = String(item.label || '').toLowerCase()
    const key = String(item.key || '').toLowerCase()
    const eid = String(ent.value?.[`s${site}_${item.key}`]?.entity_id || '').toLowerCase()
    return label.includes(q) || key.includes(q) || eid.includes(q)
  })
}
const filteredAllEntities = (site) => {
  const q = _filterText(site)
  const list = allEntities(site)
  if (!q) return list
  return list.filter((e) => {
    const name = String(e.name || e.original_name || '').toLowerCase()
    const eid = String(e.entity_id || '').toLowerCase()
    return name.includes(q) || eid.includes(q)
  })
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
  for (const e of extraDatalogItems(site)) {
    if (!e.enabled) continue
    const payload = extraStates.value?.[e.entity_id]
    const fname = payload?.attributes?.friendly_name
    out.push({
      key: `extra_s${site}_${e.entity_id}`,
      label: (typeof fname === 'string' && fname.trim().length > 0) ? fname : e.entity_id,
      value: payload ? fmtEntityRaw(payload.state, payload.attributes) : 'n/d',
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
  const cached = flowStates.value?.[eid]
  if (cached) {
    return fmtEntityRaw(cached.state, cached.attributes)
  }
  const e = entityById(site, eid)
  if (!e) return 'n/d'
  return fmtEntityRaw(e.state, e.attributes)
}
const flowValueOr = (site, key, fallbackKey) => {
  const v = flowValue(site, key)
  if (v !== 'n/d') return v
  return fallbackKey ? flowValue(site, fallbackKey) : v
}
const flowLabelOr = (site, key, fallbackKey, fallbackLabel) => {
  const lbl = flowLabel(site, key, '')
  if (lbl && lbl !== 'n/d') return lbl
  if (fallbackKey) {
    const fb = flowLabel(site, fallbackKey, '')
    if (fb && fb !== 'n/d') return fb
  }
  return fallbackLabel || 'n/d'
}
const flowNumber = (site, key) => {
  const eid = sp.value?.automation?.flow_entities?.[`s${site}`]?.[key] || ''
  if (!eid) return null
  const cached = flowStates.value?.[eid]
  const src = cached || entityById(site, eid)
  if (!src) return null
  const num = Number(String(src.state).replace(',', '.'))
  return Number.isFinite(num) ? num : null
}
const flowClass = (site, key) => {
  const v = flowNumber(site, key)
  if (!Number.isFinite(v)) return ''
  if (Math.abs(v) < 0.05) return ''
  return v >= 0 ? 'on fwd' : 'on rev'
}
const flowPercent = (site, key, totalKey) => {
  const v = flowNumber(site, key)
  const t = flowNumber(site, totalKey)
  if (!Number.isFinite(v) || !Number.isFinite(t) || t === 0) return '0%'
  return `${Math.round((v / t) * 100)}%`
}
const batteryFillH = (site) => {
  const soc = flowNumber(site, 'soc')
  const pct = Math.max(0, Math.min(100, Number.isFinite(soc) ? soc : 0))
  return (70 * pct) / 100
}
const batteryFillY = (site) => {
  const h = batteryFillH(site)
  return 70 - h + 6
}
const flowLabel = (site, key, fallback) => {
  const eid = sp.value?.automation?.flow_entities?.[`s${site}`]?.[key] || ''
  if (!eid) return fallback
  const cached = flowStates.value?.[eid]
  const fn = cached?.attributes?.friendly_name
  if (typeof fn === 'string' && fn.trim().length > 0) return fn
  return fallback
}
const flowNum = (site, key) => {
  const eid = sp.value?.automation?.flow_entities?.[`s${site}`]?.[key] || ''
  if (!eid) return 0
  const cached = flowStates.value?.[eid]
  const raw = cached?.state
  const n = Number(raw)
  return Number.isFinite(n) ? n : 0
}
const flowDur = (site, key) => {
  const n = Math.abs(flowNum(site, key))
  const min = 1.2
  const max = 6.0
  if (n <= 10) return `${max}s`
  if (n >= 5000) return `${min}s`
  const t = max - (n / 5000) * (max - min)
  return `${t.toFixed(2)}s`
}
const flowActive = (site, key) => {
  const n = Math.abs(flowNum(site, key))
  return n > 10 ? 'active' : ''
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
    for (const k of ['pv','load','battery','grid','soc','battery_v','battery_a','today_prod','today_load','today_house','today_export','today_charge','today_discharge','voltage','frequency']) {
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
      const fc = await fetch('/api/forecast')
      forecast.value = await fc.json()
    } catch {}
    await refreshExtraStates()
  }
  if (tab.value === 'automation_interface') {
    await refreshFlowStates()
  }
  if (tab.value === 'view_card') {
    await refreshFlowStates()
  }
  await loadEntities()
  lastUpdate.value = new Date()
}

async function refreshFlowStates(){
  const ids = []
  for (const site of siteList.value || []) {
    const flow = sp.value?.automation?.flow_entities?.[`s${site}`] || {}
    for (const k of ['pv_a','pv_b','pv_total','pv','load_total','load','battery','grid','soc','soc_min','battery_v','battery_a','today_prod','today_load','today_house','today_export','today_charge','today_discharge','voltage','frequency']) {
      const eid = String(flow[k] || '').trim()
      if (eid) ids.push(eid)
    }
  }
  if (ids.length === 0) return
  const uniq = Array.from(new Set(ids))
  const r = await fetch('/api/entity_states', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entity_ids: uniq })
  })
  if (!r.ok) return
  const data = await r.json()
  flowStates.value = data.items || {}
}

async function refreshExtraStates(){
  const ids = []
  for (const site of siteList.value || []) {
    for (const item of extraDatalogItems(site)) {
      if (item.enabled) ids.push(item.entity_id)
    }
  }
  if (ids.length === 0) return
  const uniq = Array.from(new Set(ids))
  const r = await fetch('/api/entity_states', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entity_ids: uniq })
  })
  if (!r.ok) return
  const data = await r.json()
  extraStates.value = data.items || {}
}

async function generateReport(){
  try {
    const r = await fetch('/api/reports/generate', { method: 'POST' })
    if (!r.ok) return
    reportStatus.value = await r.json()
  } catch {}
}
async function runLoggingCheck(site = null){
  try {
    const qs = new URLSearchParams()
    if (site) qs.set('site', String(site))
    qs.set('hours', String(loggingHours.value || 24))
    const r = await fetch(`/api/logging_check?${qs.toString()}`)
    if (!r.ok) return
    loggingCheck.value = await r.json()
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
.forecast-table{
  margin-top:10px;
  display:flex;
  flex-direction:column;
  gap:6px;
}
.forecast-row{
  display:grid;
  grid-template-columns:
    1.4fr
    minmax(100px,1fr)
    minmax(100px,1fr)
    minmax(120px,1fr)
    minmax(120px,1fr)
    minmax(100px,1fr)
    minmax(100px,1fr)
    minmax(90px,1fr)
    minmax(90px,1fr)
    minmax(120px,1fr)
    minmax(90px,1fr);
  gap:8px;
  padding:8px;
  border:1px solid var(--line);
  border-radius:10px;
  background:#0b121a;
  font-size:12px;
}
.forecast-row > div{
  white-space:nowrap;
}
.forecast-head > div{
  white-space:normal;
  line-height:1.1;
}
.forecast-head{
  font-weight:700;
  color:var(--muted);
  text-transform:uppercase;
  letter-spacing:0.04em;
  background:#0f1620;
}
.forecast-note{
  margin-top:8px;
  font-size:12px;
}
.hourly-wrap{
  display:flex;
  flex-direction:column;
  gap:12px;
  margin-top:8px;
}
.hourly-block{
  background:#0b121a;
  border:1px solid var(--line);
  border-radius:12px;
  padding:10px;
}
.hourly-table{
  margin-top:8px;
  display:flex;
  flex-direction:column;
  gap:4px;
  max-height:320px;
  overflow:auto;
}
.hourly-row{
  display:grid;
  grid-template-columns: 90px repeat(3, minmax(100px, 1fr));
  gap:8px;
  padding:6px 8px;
  border:1px solid var(--line);
  border-radius:8px;
  background:#0f1620;
  font-size:12px;
}
.hourly-head{
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:0.04em;
  color:var(--muted);
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
.insights-compare{
  display:grid;
  grid-template-columns:repeat(2, minmax(260px, 1fr));
  gap:10px;
  margin-top:12px;
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
.set-section > summary.section-title{
  cursor:pointer;
  list-style:none;
}
.set-section > summary.section-title::-webkit-details-marker{
  display:none;
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
.flow-canvas{
  width:100%;
  overflow:hidden;
  padding:10px 0;
}
.flow-svg{
  width:100%;
  height:auto;
  max-height:720px;
  background:linear-gradient(180deg, #0b0f14, #0b121a);
  border:1px solid var(--line);
  border-radius:16px;
}
.viewcard-panel{
  width:min(1200px, 98vw);
  aspect-ratio: 16 / 9;
  background: radial-gradient(1200px 600px at 50% 40%, #161a1f 0%, #0e1012 55%, #0b0d0f 100%);
  border-radius:18px;
  box-shadow:0 30px 80px rgba(0,0,0,.45);
  position:relative;
  overflow:hidden;
  margin:12px auto 0;
}
.viewcard-title{
  position:absolute;
  left:0;
  right:0;
  top:22px;
  text-align:center;
  font-weight:600;
  letter-spacing:.12em;
  color:#8f97a0;
  font-size:28px;
  opacity:.9;
}
.viewcard-box{
  position:absolute;
  background:rgba(20,24,28,.75);
  border:1px solid rgba(255,255,255,.08);
  border-radius:10px;
  padding:10px 12px;
  backdrop-filter: blur(6px);
  min-width:140px;
}
.viewcard-box .val{
  font-size:22px;
  font-weight:700;
  line-height:1.1;
}
.viewcard-box .lab{
  font-size:12px;
  color:#6b737b;
  margin-top:4px;
  letter-spacing:.04em;
  text-transform:uppercase;
}
.viewcard-box.yellow{ border-color:rgba(255,179,0,.35); }
.viewcard-box.yellow .val{ color:#ffb300; }
.viewcard-box.red{ border-color:rgba(255,59,48,.35); }
.viewcard-box.red .val{ color:#ff3b30; }
.viewcard-box.purple{ border-color:rgba(168,85,247,.35); }
.viewcard-box.purple .val{ color:#a855f7; }
.viewcard-today{ left:60px; top:80px; min-width:220px; }
.viewcard-solar{ left:60px; top:140px; }
.viewcard-house{ right:90px; top:210px; }
.viewcard-grid{ right:90px; bottom:110px; }
.viewcard-batt{ left:70px; bottom:120px; }
.viewcard-soc{ left:270px; bottom:145px; min-width:120px; }
.viewcard-vf{ right:360px; top:350px; min-width:160px; }
.viewcard-icon{
  position:absolute;
  display:flex;
  align-items:center;
  gap:10px;
  color:#ffb300;
  opacity:.95;
  user-select:none;
}
.viewcard-icon svg{
  position:static;
  width:44px;
  height:44px;
}
.viewcard-icon .icon-title{
  font-weight:700;
}
.viewcard-icon .icon-cap{
  font-size:12px;
  color:#6b737b;
  margin-top:2px;
}
.viewcard-icon.i-solar{ left:70px; top:250px; }
.viewcard-icon.i-house{ right:160px; top:280px; color:#ffb300; }
.viewcard-icon.i-grid{ right:170px; bottom:170px; color:#ff3b30; }
.viewcard-icon.i-batt{ left:95px; bottom:210px; color:#a855f7; }
.viewcard-svg{
  position:absolute;
  inset:0;
}
.pipe{
  fill:none;
  stroke:#2b3138;
  stroke-width:6;
  stroke-linecap:round;
  opacity:.9;
}
.flow{
  fill:none;
  stroke-width:6;
  stroke-linecap:round;
  stroke-dasharray:14 14;
  filter: drop-shadow(0 0 6px rgba(255,179,0,.25));
  opacity:0;
}
.flow.on{ opacity:1; }
.flow.yellow{ stroke:#ffb300; }
.flow.red{ stroke:#ff3b30; }
.flow.purple{ stroke:#a855f7; }
.flow.fwd{ animation: dash 1.1s linear infinite; }
.flow.rev{ animation: dashrev 1.1s linear infinite; }
@keyframes dash{ to{ stroke-dashoffset:-28 } }
@keyframes dashrev{ to{ stroke-dashoffset:28 } }
.viewcard-footer{
  position:absolute;
  left:18px;
  bottom:14px;
  font-size:12px;
  color:#707780;
  opacity:.75;
}
.flow-line{
  stroke:#3a3f44;
  stroke-width:4;
  fill:none;
  stroke-linecap:round;
}
.flow-line.active{
  stroke:#ffb000;
}
.pv-line.active,.load-line.active{ stroke:#ffb000; }
.grid-line.active{ stroke:#ff5c5c; }
.batt-line.active{ stroke:#ffa94d; }
.flow-dot{
  fill:#ffb000;
  opacity:0.9;
}
.pv-dot{ fill:#ffb000; }
.load-dot{ fill:#ffb000; }
.grid-dot{ fill:#ff5c5c; }
.batt-dot{ fill:#ffa94d; }
.box rect{
  fill:#13181f;
  stroke:#2a2f36;
  stroke-width:2;
}
.box-value{
  fill:#e6eef8;
  font-size:22px;
  font-weight:700;
}
.box-label{
  fill:#9fb0c3;
  font-size:12px;
}
.box-sub{
  fill:#c5d1dd;
  font-size:12px;
}
.vf-box rect{ stroke:#ff6b6b; }
.vf-box .box-value{ fill:#ff6b6b; font-size:18px; }
.stats .stat-title{
  fill:#9fb0c3;
  font-size:12px;
}
.stats .stat-value{
  fill:#ffb000;
  font-size:16px;
  font-weight:700;
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
  .insights-compare{ grid-template-columns:1fr; }
  .forecast-row{ grid-template-columns: 1fr 1fr; row-gap:6px; }
  .hourly-row{ grid-template-columns: 1fr 1fr; row-gap:6px; }
}
@media (max-width: 900px){
  .top-inner{ grid-template-columns:1fr; justify-items:start; }
  .top-center{ justify-content:flex-start; }
  .top-right{ justify-content:flex-start; }
  .flow-svg{ max-height:560px; }
}
@media (max-width: 640px){
  .grid{ grid-template-columns:1fr; }
  .row3{ grid-template-columns:1fr; }
  .flow-grid{ grid-template-columns:1fr; }
  .top{ position:static; }
}
</style>
