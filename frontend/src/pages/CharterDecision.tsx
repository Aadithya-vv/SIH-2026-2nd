import { useEffect, useState } from 'react';
import { Area, CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { request } from '../api/client';
import type { Port } from '../types';
import type { FreightForecast } from '../types/forecast';
import type { CharterRequest, CharterDecision as Decision, DemoPreset } from '../types/charter';

const cash = (n: number | null) => n == null ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
const addDays = (s: string, n: number) => new Date(Date.parse(s.slice(0,10)+'T00:00:00Z')+n*86400000).toISOString().slice(0,10);
const pretty = (s: string) => s.replaceAll('_',' ');
const today = new Date().toISOString().slice(0,10);
const initial: CharterRequest = {
  shipment: { cargo_type:'COKING_COAL', cargo_quantity_tonnes:70000, origin_country:'Australia', origin_port:'Newcastle', destination_country:'India', destination_port:'Paradip', required_arrival_date:addDays(today,50) },
  vessel_class:'PANAMAX', analysis_as_of:new Date().toISOString(), forecast_model_id:null,
  risk_profile:'BALANCED', schedule_buffer_days:2, storage_usd_per_tonne_day:null, allow_index_proxy:false,
};

export function CharterDecision({ ports, savedId, onForecast }: { ports: Port[]; savedId: string | null; onForecast: () => void }) {
  const [form,setForm] = useState<CharterRequest>(initial);
  const [models,setModels] = useState<FreightForecast[]>([]);
  const [presets,setPresets] = useState<DemoPreset[]>([]);
  const [result,setResult] = useState<Decision | null>(null);
  const [analyzedInputs,setAnalyzedInputs] = useState('');
  const [auto,setAuto] = useState(false);
  const [busy,setBusy] = useState(false);
  const [preparing,setPreparing] = useState(false);
  const [error,setError] = useState('');
  const [revision,setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    Promise.all([request<FreightForecast[]>('/api/forecast/models'),request<DemoPreset[]>('/api/charter/demos')])
      .then(([m,p]) => { if(active){setModels(m);setPresets(p);} }).catch(e => { if(active)setError(String(e)); });
    if(savedId) request<Decision>(`/api/charter/${savedId}`).then(d => {if(active){setForm(d.request);setResult(d);setAnalyzedInputs(JSON.stringify(d.request));}}).catch(e => {if(active)setError(String(e));});
    return () => {active=false;};
  },[savedId]);
  useEffect(() => {
    if(!auto) return;
    let active = true;
    const timer = setTimeout(() => {
      setBusy(true);setError('');
      request<Decision>('/api/charter/analyze',form).then(d => {if(active){setResult(d);setAnalyzedInputs(JSON.stringify(form));}})
        .catch(e => {if(active){setError(String(e));setResult(null);}}).finally(() => {if(active)setBusy(false);});
    },250);
    return () => {active=false;clearTimeout(timer);};
  },[auto,form,revision]);
  const dirty = !!result && analyzedInputs !== JSON.stringify(form);
  const forecast = result?.forecast_metadata;
  function setPort(kind: 'origin'|'destination',name: string) {
    const port=ports.find(p=>p.name===name);
    if(port)setForm({...form,shipment:{...form.shipment,[`${kind}_port`]:name,[`${kind}_country`]:port.country}});
  }
  async function prepare() {
    setPreparing(true);setError('');
    try { setPresets(await request<DemoPreset[]>('/api/charter/demos/prepare',{}));setModels(await request<FreightForecast[]>('/api/forecast/models')); }
    catch(e){setError(String(e));} finally {setPreparing(false);}
  }
  const chartData = result?.candidate_decisions.map(c=>({date:c.charter_date,day:c.wait_days,median:c.costs.p50.total_logistics_cost,range:[c.costs.p10.total_logistics_cost,c.costs.p90.total_logistics_cost]})) ?? [];
  const originDay = result?.request.analysis_as_of.slice(0,10) ?? today;
  const dayOffset = (d: string) => (Date.parse(d)-Date.parse(originDay))/86400000;
  const unsafe = result?.rejected_region.first_unsafe_date;
  const chartEnd = result?.rejected_region.forecast_end_date ? dayOffset(result.rejected_region.forecast_end_date) : 14;
  return <>
    <section className="charter-presets">
      <div className="section-heading"><h2>Demonstration scenarios</h2><span>SIMULATED / HISTORICAL REPLAY</span></div>
      <p className="muted">Fixed seeded histories are processed by the Phase 3 forecasting engine. Presets change shipment constraints; no recommendation is hardcoded.</p>
      <div className="charter-actions">{presets.map(p=><button key={p.key} disabled={!p.ready || preparing} onClick={()=>{setForm(p.request);setAuto(true);setRevision(n=>n+1);}}>{p.key} · {p.label}</button>)}
        {presets.some(p=>!p.ready) && <button className="primary" onClick={prepare} disabled={preparing}>{preparing?'Preparing demo forecasts…':'Prepare seeded demo forecasts'}</button>}
      </div>
      {preparing && <p role="status">Explicitly training two synthetic histories; this can take two minutes. Charter analysis itself never trains a model.</p>}
    </section>
    <form onSubmit={e=>{e.preventDefault();setAuto(true);setRevision(n=>n+1);}} className="shipment-form">
      <div className="section-heading"><h2>Shipment & procurement preferences</h2><span>USD / CALENDAR DAYS</span></div>
      <div className="fields charter-fields">
        <label>Cargo<select value={form.shipment.cargo_type} onChange={e=>setForm({...form,shipment:{...form.shipment,cargo_type:e.target.value}})}>{['COKING_COAL','THERMAL_COAL','IRON_ORE'].map(v=><option key={v} value={v}>{pretty(v)}</option>)}</select></label>
        <label>Quantity · tonnes<input type="number" required min="1" max="1000000" value={form.shipment.cargo_quantity_tonnes} onChange={e=>setForm({...form,shipment:{...form.shipment,cargo_quantity_tonnes:Number(e.target.value)}})}/></label>
        <label>Origin port<select value={form.shipment.origin_port} onChange={e=>setPort('origin',e.target.value)}>{ports.filter(p=>p.country!=='India').map(p=><option key={p.name}>{p.name}</option>)}</select></label>
        <label>Destination port<select aria-label="Destination port" value={form.shipment.destination_port} onChange={e=>setPort('destination',e.target.value)}>{ports.filter(p=>p.country==='India').map(p=><option key={p.name}>{p.name}</option>)}</select></label>
        <label>Vessel class<select value={form.vessel_class} onChange={e=>setForm({...form,vessel_class:e.target.value})}>{['HANDYSIZE','SUPRAMAX','PANAMAX','CAPESIZE'].map(v=><option key={v}>{v}</option>)}</select></label>
        <label>Required arrival<input type="date" required value={form.shipment.required_arrival_date} onChange={e=>setForm({...form,shipment:{...form.shipment,required_arrival_date:e.target.value}})}/></label>
        <label>Schedule buffer · days<input type="number" min="0" max="30" step="0.1" value={form.schedule_buffer_days} onChange={e=>setForm({...form,schedule_buffer_days:Number(e.target.value)})}/></label>
        <label>Risk profile<select value={form.risk_profile} onChange={e=>setForm({...form,risk_profile:e.target.value as CharterRequest['risk_profile']})}>{['CONSERVATIVE','BALANCED','COST_FOCUSED'].map(v=><option key={v} value={v}>{pretty(v)}</option>)}</select></label>
        <label>Saved forecast<select value={form.forecast_model_id ?? ''} onChange={e=>{const m=models.find(m=>m.model_id===e.target.value);setForm({...form,forecast_model_id:e.target.value||null,...(m?{analysis_as_of:m.as_of_time,shipment:{...form.shipment,required_arrival_date:addDays(m.as_of_time,50)}}:{})});}}>
          <option value="">Resolve matching saved forecast</option>{form.forecast_model_id && !models.some(m=>m.model_id===form.forecast_model_id) && <option value={form.forecast_model_id}>Unavailable forecast</option>}{models.map(m=><option key={m.model_id} value={m.model_id}>{m.target.name} / {m.as_of_time.slice(0,10)} / {m.model_id.slice(0,6)}</option>)}</select></label>
        <label>Analysis as-of · UTC<input aria-label="Analysis as-of UTC" value={form.analysis_as_of} onChange={e=>setForm({...form,analysis_as_of:e.target.value})}/></label>
        <label>Storage · USD/tonne/day<input type="number" min="0" step="0.001" placeholder="Not modelled" value={form.storage_usd_per_tonne_day ?? ''} onChange={e=>setForm({...form,storage_usd_per_tonne_day:e.target.value===''?null:Number(e.target.value)})}/></label>
        <label>Demurrage · USD/day<input type="number" min="0" placeholder="Assumed 0.8 × current hire" value={form.demurrage_usd_per_day ?? ''} onChange={e=>setForm({...form,demurrage_usd_per_day:e.target.value===''?null:Number(e.target.value)})}/></label>
      </div>
      <label className="charter-consent"><input type="checkbox" checked={!!form.allow_index_proxy} onChange={e=>setForm({...form,allow_index_proxy:e.target.checked,index_anchor_hire_usd_per_day:null})}/>Use an assumed index-to-hire ratio anchored to demo vessel hire when the target is an index. This is not a market quotation.</label>
      <button className="primary" disabled={busy || preparing}>{busy?'Calculating…':'Analyze charter timing'}</button>
      <p className="muted">After analysis, deadline, buffer and other edits recalculate automatically. Arrival means final unloading complete. Historical forecasts stay on their original date.</p>
    </form>
    {error && <div role="alert" className="error">{error}</div>}
    {busy && <p role="status">Recalculating candidate dates and cost scenarios…</p>}
    {dirty && <p className="warning">Inputs changed; the displayed result belongs to the previous request until recalculation completes.</p>}
    {result && <div className={dirty?'charter-result stale':'charter-result'}>
      <section><div className="section-heading"><h2>Current market context</h2><span>{originDay===today?'ANALYSIS TODAY':`HISTORICAL AS OF ${originDay}`}</span></div>
        {forecast ? <><div className="metrics"><div><span>Freight basis</span><strong>{forecast.current_rate.toLocaleString(undefined,{maximumFractionDigits:2})}</strong><small>{forecast.target.currency} / {forecast.target.unit} · {forecast.target.provenance.source_type}</small></div><div><span>Market regime</span><strong className="smaller">{pretty(forecast.market_regime)}</strong><small>{pretty(forecast.uncertainty_status)}</small></div><div><span>Forecast direction</span><strong className="smaller">{forecast.forecast_points.at(-1)!.p50<forecast.current_rate?'Median declines':'Median rises / flat'}</strong><small>At longest saved horizon; does not decide timing alone</small></div><div><span>Rate conversion</span><strong className="smaller">{pretty(String(result.rate_conversion.method ?? 'Unavailable'))}</strong><small>No executable charter quote</small></div></div></> : <p>Forecast unavailable. No replacement prediction fabricated.</p>}
        <p className="muted">{result.market_snapshot.congestion_used.map(c=>`${c.port}: ${c.used_days_per_call.toFixed(2)} d/call (${c.observation.provenance?.source_type ?? 'ASSUMED'}; ${c.basis})`).join(' · ')}</p>
      </section>
      <section className="charter-hero" aria-label="Charter recommendation">
        <div className="eyebrow">PROTOTYPE CHARTER TIMING / {result.evidence_status} EVIDENCE</div>
        <h2 data-testid="charter-recommendation">{pretty(result.recommendation)}</h2>
        <p className="charter-window">{result.recommendation==='WAIT'?`Recommended window: ${result.recommended_window_start} – ${result.recommended_window_end}`:result.recommendation==='LOCK_NOW'?`Charter on analysis day: ${originDay}`:'Review shipment constraints and forecast basis.'}</p>
        <div className="metrics"><div><span>Latest safe charter</span><strong className="smaller">{result.latest_safe_charter_date}</strong></div><div><span>Median saving vs now</span><strong>{cash(result.median_saving)}</strong><small>Under stated assumptions</small></div><div><span>P90 downside vs now</span><strong>{cash(result.downside_exposure)}</strong></div><div><span>Slack after buffer</span><strong>{result.schedule_slack?.toFixed(2) ?? '—'} days</strong></div></div>
      </section>
      <section><h2>Why this decision?</h2><ol className="charter-reasons">{result.explanation.map(e=><li key={e}>{e}</li>)}</ol></section>
      <section><div className="section-heading"><h2>Decision timeline</h2><span>{result.voyage_context.voyage_count} SEQUENTIAL VOYAGE(S)</span></div><div className="timeline charter-timeline">{[
        ['Analysis day',originDay],['Safe wait search',result.candidate_decisions.length>1?`${originDay} → ${result.candidate_decisions.at(-1)?.charter_date}`:'No later eligible date'],
        ['Recommended window',result.recommended_window_start?`${result.recommended_window_start} → ${result.recommended_window_end}`:'No future window'],['Latest safe charter',result.latest_safe_charter_date],['Required final delivery',result.request.shipment.required_arrival_date]
      ].map(([label,value])=><div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div><p className="muted">{result.voyage_context.voyage.estimated_total_days.toFixed(2)} delivery days + {result.request.schedule_buffer_days} buffer days → {result.voyage_context.rounded_buffered_duration_days} rounded calendar days.</p></section>
      {chartData.length>0 && <section><div className="section-heading"><h2>Logistics cost vs charter date</h2><span>USD / MEDIAN & P10–P90 SCENARIOS</span></div>
        <div className="charter-chart" data-testid="charter-cost-chart"><ResponsiveContainer width="100%" height={330}><ComposedChart data={chartData} margin={{left:25,right:35,top:25,bottom:20}}><CartesianGrid strokeDasharray="3 3"/><XAxis type="number" dataKey="day" domain={[0,Math.max(1,chartEnd)]} tickFormatter={v=>addDays(originDay,Number(v)).slice(5)}/><YAxis domain={[(min: number)=>Math.floor(min*.998), (max: number)=>Math.ceil(max*1.002)]} tickFormatter={v=>`$${(Number(v)/1000).toFixed(0)}k`}/><Tooltip contentStyle={{background:"#19272d",borderColor:"#45605f",color:"#e1e8ed"}} labelFormatter={v=>`Wait ${v} days`} formatter={v=>Array.isArray(v)?v.map(n=>cash(Number(n))).join(' – '):cash(Number(v))}/>
          {unsafe && dayOffset(unsafe)<=chartEnd && <ReferenceArea x1={dayOffset(unsafe)} x2={chartEnd} fill="#b34f43" fillOpacity={.12} label="Infeasible"/>}
          {result.recommended_window_start && <ReferenceArea x1={dayOffset(result.recommended_window_start)} x2={dayOffset(result.recommended_window_end!)} fill="#286d68" fillOpacity={.15}/>}
          <Area type="linear" dataKey="range" name="P10–P90 cost" stroke="none" fill="#3b8580" fillOpacity={.22} isAnimationActive={false}/><Line type="linear" dataKey="median" name="P50 cost" stroke="#99c5be" strokeWidth={2} dot={false} isAnimationActive={false}/><ReferenceLine x={0} label={{value:"AS OF",position:"insideTopLeft",fill:"#a8babd"}} stroke="#829b9b"/>
          {result.latest_safe_charter_date && dayOffset(result.latest_safe_charter_date)<=chartEnd && <ReferenceLine x={dayOffset(result.latest_safe_charter_date)} stroke="#b34f43" label={{value:"Latest safe",position:"insideTopRight",fill:"#d79b8b"}}/>}
        </ComposedChart></ResponsiveContainer></div><p className="muted">Band shows cost scenarios, not a calibrated cost probability interval. Unsafe dates have no cost estimates. A safe date beyond the forecast horizon is shown in the timeline only.</p>
      </section>}
      <section><div className="section-heading"><h2>Compare charter dates</h2><span>{result.performance.candidate_dates} DATES / {result.performance.cost_scenarios} COST CASES</span></div><div className="table-wrap"><table><thead><tr>{['Charter date','Wait','Arrival / status','Slack · d','P10 · USD','P50 · USD','P90 · USD','Median saving','P90 downside','Max regret','Decision'].map(t=><th key={t}>{t}</th>)}</tr></thead><tbody>{result.candidate_decisions.map(c=><tr key={c.wait_days} className={c.decision_status==='RECOMMENDED'?'recommended':''}><th>{c.charter_date}{c.in_recommended_window && <small>IN WINDOW</small>}</th><td>{c.wait_days} d</td><td>{c.estimated_arrival}<small>{c.arrival_status}</small></td><td>{c.schedule_slack_days.toFixed(2)}</td><td>{cash(c.costs.p10.total_logistics_cost)}</td><td>{cash(c.costs.p50.total_logistics_cost)}</td><td>{cash(c.costs.p90.total_logistics_cost)}</td><td>{cash(c.savings_vs_now.p50)}</td><td>{cash(c.downside_exposure)}</td><td>{cash(c.maximum_scenario_regret)}</td><td>{pretty(c.decision_status)}<small>{c.policy_rejections.map(pretty).join(', ')}</small></td></tr>)}</tbody></table></div>
        {!result.candidate_decisions.length && <p>No eligible cost comparison. {pretty(result.recommendation)}.</p>}
        {!!result.rejected_region.excluded_by_deadline_count && <p className="warning">{result.rejected_region.excluded_by_deadline_count} later dates excluded: {result.rejected_region.reason}</p>}
      </section>
      <details className="provenance"><summary>View forecast basis</summary>{forecast?<><p>{forecast.model_id} · {forecast.model_version} · training cutoff {forecast.training_cutoff} · generated {forecast.forecast_generated_at}</p><p>{forecast.target.provenance.source_type} · {forecast.target.provenance.notes}</p><div className="table-wrap"><table><thead><tr><th>Horizon</th><th>Model</th><th>P10</th><th>P50</th><th>P90</th><th>Validation coverage</th><th>Test MAE / coverage</th></tr></thead><tbody>{forecast.forecast_points.map(p=>{const m=forecast.leaderboard.find(r=>r.horizon===p.horizon && r.selected);return <tr key={p.horizon}><td>{p.horizon} d</td><td>{p.model_name}</td><td>{p.p10.toFixed(2)}</td><td>{p.p50.toFixed(2)}</td><td>{p.p90.toFixed(2)}</td><td>{m?(m.validation.coverage*100).toFixed(1)+'%':'Unavailable'}</td><td>{m?`${m.test.mae.toFixed(2)} / ${(m.test.coverage*100).toFixed(1)}%`:'Unavailable'}</td></tr>;})}</tbody></table></div></>:<p>No saved forecast available.</p>}<button className="text-button" onClick={onForecast}>Open forecast workspace →</button></details>
      <details className="provenance"><summary>Assumptions, cost components & limitations</summary><h3>Deterministic policy · {result.request.risk_profile}</h3><dl className="charter-assumptions">{Object.entries({...result.policy,...result.assumptions,...result.rate_conversion}).map(([k,v])=><div key={k}><dt>{pretty(k)}</dt><dd>{v==null?'NOT MODELLED':String(v)}</dd></div>)}</dl>
        {result.candidate_decisions.filter(c=>c.decision_status==='RECOMMENDED').map(c=><div key={c.wait_days}><h3>Selected median cost components · USD</h3><dl className="charter-assumptions">{Object.entries(c.costs.p50).filter(([,v])=>typeof v==='number').map(([k,v])=><div key={k}><dt>{pretty(k)}</dt><dd>{cash(Number(v))}</dd></div>)}</dl></div>)}
        <ul>{result.limitations.map(l=><li key={l}>{l}</li>)}</ul><p>Analysis {result.analysis_id} · policy charter-v1 · {result.performance.analysis_ms.toFixed(1)} ms · Saved immutable evidence; no forecast retraining.</p>
      </details>
    </div>}
  </>;
}
