import type { Shipment, Option } from './index';
import type { FreightForecast } from './forecast';

export interface CharterRequest {
  shipment: Shipment;
  vessel_class: string;
  analysis_as_of: string;
  forecast_model_id: string | null;
  risk_profile: 'CONSERVATIVE' | 'BALANCED' | 'COST_FOCUSED';
  schedule_buffer_days: number;
  storage_usd_per_tonne_day: number | null;
  demurrage_usd_per_day?: number | null;
  loading_days?: number | null;
  unloading_days?: number | null;
  allow_index_proxy?: boolean;
  index_anchor_hire_usd_per_day?: number | null;
  max_downside_fraction?: number | null;
  window_cost_tolerance_fraction?: number;
}
export interface Candidate {
  wait_days: number;
  charter_date: string;
  estimated_arrival: string;
  buffered_arrival: string;
  arrival_status: string;
  schedule_slack_days: number;
  freight_quantiles: Record<string, number>;
  hire_usd_per_day: Record<string, number>;
  forecast_basis: string;
  costs: Record<string, Option['cost']>;
  savings_vs_now: Record<string, number>;
  downside_exposure: number;
  maximum_scenario_regret: number;
  decision_status: string;
  policy_rejections: string[];
  in_recommended_window: boolean;
}
export interface CharterDecision {
  analysis_id: string;
  generated_at: string;
  request: CharterRequest;
  recommendation: string;
  recommended_window_start: string | null;
  recommended_window_end: string | null;
  latest_safe_charter_date: string | null;
  selected_wait_days: number | null;
  evidence_status: string;
  current_charter_cost: number | null;
  recommended_median_cost: number | null;
  median_saving: number | null;
  downside_exposure: number | null;
  schedule_slack: number | null;
  candidate_decisions: Candidate[];
  explanation: string[];
  forecast_metadata: FreightForecast | null;
  voyage_context: { voyage: Option['voyage']; voyage_count: number; feasibility: Option['feasibility']; rounded_buffered_duration_days: number };
  market_snapshot: { congestion_used: { port: string; used_days_per_call: number; basis: string; status: string; observation: { provenance?: { source_type: string } } }[] };
  policy: Record<string, string | number | boolean>;
  assumptions: Record<string, unknown>;
  limitations: string[];
  rate_conversion: Record<string, unknown>;
  evidence_factors: Record<string, unknown>;
  rejected_region: { first_unsafe_date?: string; excluded_by_deadline_count?: number; forecast_end_date?: string; reason?: string };
  performance: { analysis_ms: number; candidate_dates: number; cost_scenarios: number };
}
export interface DemoPreset { key: string; label: string; ready: boolean; request: CharterRequest }
export type CharterHistory = Pick<CharterDecision, 'analysis_id' | 'generated_at' | 'request' | 'recommendation' | 'recommended_window_start' | 'recommended_window_end' | 'median_saving' | 'evidence_status'>;
