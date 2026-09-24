import type { Provenance } from "./index";
export type Category = "FREIGHT" | "COMMODITY" | "BUNKER" | "PORT";
export interface Source {
  source_id: string;
  name: string;
  category: string;
  provider: string;
  access_type: string;
  update_frequency: string;
  expected_units: string[];
  license_notes: string;
  availability_status: string;
  last_successful_ingestion: string | null;
  notes: string;
}
export interface MarketSeries {
  series_id: string;
  name: string;
  category: string;
  source_id: string;
  unit: string;
  currency: string | null;
  frequency_days: number;
  provenance: Provenance;
}
export interface Quality {
  rows_received: number;
  rows_accepted: number;
  rows_rejected: number;
  missing_values: number;
  duplicates: number;
  missing_periods: number;
  completeness_percent: number;
  start: string | null;
  end: string | null;
  latest_age_days: number | null;
  stale: boolean;
  warnings: string[];
  status: string;
}
export interface CatalogEntry {
  series: MarketSeries;
  source: Source;
  records: number;
  start: string | null;
  end: string | null;
  latest: number | null;
  quality: Quality;
  status: string;
  forecast_suitability: string;
}
export interface MarketObservation {
  timestamp: string;
  available_at: string;
  value: number;
  original_value: number;
  original_unit: string;
  original_currency: string | null;
  quality_flags: string[];
}
export interface History {
  series: MarketSeries;
  observations: MarketObservation[];
}
export interface Trends {
  latest: number | null;
  mean_7: number | null;
  mean_30: number | null;
  change: number | null;
  change_percent: number | null;
  rolling_volatility: number | null;
  minimum: number | null;
  maximum: number | null;
  records: number;
  method: string;
  warnings: string[];
}
export interface ImportResult {
  preview_hash: string;
  series_id: string;
  source_label: string;
  unit: string;
  currency: string | null;
  quality: Quality;
  committed: boolean;
  already_ingested: boolean;
  rows: {
    row_number: number;
    accepted: boolean;
    issues: string[];
    raw: Record<string, string>;
  }[];
  normalization: {
    availability: string;
    original_unit: string;
    canonical_unit: string;
    currency_conversion: string;
  };
}
export interface SnapshotItem {
  series_id?: string;
  available: boolean;
  reason?: string;
  series_name?: string;
  value?: number;
  timestamp?: string;
  available_at?: string;
  unit?: string;
  currency?: string | null;
  source?: Source;
  provenance?: Provenance;
  freshness?: { age_days: number; status: string };
  context_note?: string;
}
export interface Snapshot {
  as_of_time: string;
  context: Record<string, SnapshotItem>;
  cost_integration: string;
}
export interface FeatureOutput {
  rows: {
    date: string;
    freight_target: number | null;
    values: Record<string, number | null>;
    calendar: Record<string, number | null>;
    lineage: Record<string, unknown>;
  }[];
  missing_by_series: Record<string, number>;
  filled_by_series: Record<string, number>;
  suitability: string;
  transformations: Record<string, string | number>;
}
