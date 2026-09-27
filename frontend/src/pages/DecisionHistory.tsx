import { useEffect, useState } from 'react';
import { request } from '../api/client';
import type { CharterHistory } from '../types/charter';

export function DecisionHistory({ onOpen }: { onOpen: (id: string) => void }) {
  const [rows,setRows] = useState<CharterHistory[]>([]);
  const [error,setError] = useState('');
  useEffect(()=>{let active=true;request<CharterHistory[]>('/api/charter/history').then(r=>{if(active)setRows(r);}).catch(e=>{if(active)setError(String(e));});return()=>{active=false;};},[]);
  return <section><div className="section-heading"><h2>Saved charter decisions</h2><span>LAST 100 IMMUTABLE ANALYSES</span></div><p className="muted">Open a record to reconstruct the saved shipment, forecast, policy, candidates and explanation. It does not fetch a new forecast.</p>{error && <p role="alert">{error}</p>}<div className="table-wrap"><table><thead><tr>{['Analysis / saved date','Shipment','Vessel','Recommendation','Window','Median saving · USD','Evidence','Review'].map(v=><th key={v}>{v}</th>)}</tr></thead><tbody>{rows.map(r=><tr key={r.analysis_id}><td>{r.analysis_id.slice(0,10)}<small>{r.generated_at.slice(0,10)}</small></td><td>{r.request.shipment.cargo_quantity_tonnes.toLocaleString()} t {r.request.shipment.cargo_type}<small>{r.request.shipment.origin_port} → {r.request.shipment.destination_port}</small></td><td>{r.request.vessel_class}</td><td>{r.recommendation.replaceAll('_',' ')}</td><td>{r.recommended_window_start?`${r.recommended_window_start} – ${r.recommended_window_end}`:'—'}</td><td>{r.median_saving?.toLocaleString(undefined,{maximumFractionDigits:2}) ?? '—'}</td><td>{r.evidence_status}</td><td><button className="text-button" onClick={()=>onOpen(r.analysis_id)}>Open evidence</button></td></tr>)}</tbody></table></div>{!rows.length && !error && <p>No saved charter analyses yet. Run a charter decision to create its audit record.</p>}</section>;
}
