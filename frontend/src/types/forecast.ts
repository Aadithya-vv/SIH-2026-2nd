import type { MarketSeries } from "./market";
export interface ForecastMetrics {
  count: number;
  mae: number;
  rmse: number;
  pinball: Record<string, number>;
  mean_pinball: number;
  directional_accuracy: number;
  coverage: number;
  nominal_coverage: number;
  mean_interval_width: number;
  crossings: number;
}
export interface ForecastPoint {
  horizon: number;
  date: string;
  model_name: string;
  p10: number;
  p50: number;
  p90: number;
  quantile_crossing: boolean;
  nonnegative_correction: boolean;
  calibration_residual_count: number;
}
export interface LeaderboardRow {
  model: string;
  horizon: number;
  validation: ForecastMetrics;
  test: ForecastMetrics;
  selected: boolean;
}
export interface FreightForecast {
  model_id: string;
  model_version: string;
  library_version: string;
  as_of_time: string;
  forecast_generated_at: string;
  training_cutoff: string;
  target: MarketSeries;
  dataset_id: string;
  dataset_summary: {
    start: string;
    end: string;
    raw_observations: number;
    usable_rows: number;
    dropped_target_rows: number;
  };
  features: string[];
  feature_importance?: Record<
    string,
    {
      model: string;
      fit_origin: string;
      note: string;
      features: { feature: string; importance: number }[];
    }
  >;
  evaluation_label: string;
  periods: Record<string, { start: string; end: string; feature_rows: number }>;
  leaderboard: LeaderboardRow[];
  selected_models: Record<string, string>;
  selection_reason: string;
  forecast_points: ForecastPoint[];
  current_rate: number;
  history: { date: string; actual: number }[];
  market_regime: string;
  uncertainty_status: string;
  explanation: string[];
  warnings: string[];
  uncertainty_method: string;
  limitations: string[];
  is_historical_as_of?: boolean;
  drivers: {
    momentum_7: number;
    fractional_volatility_30: number;
    context: {
      series_id: string;
      value: number | null;
      change_7: number | null;
      available: boolean;
    }[];
  };
}
export interface Backtest {
  evaluation_label: string;
  records: {
    stage: string;
    horizon: number;
    model: string;
    origin_date?: string;
    target_date: string;
    actual: number;
    p10?: number;
    p50?: number;
    p90?: number;
  }[];
}
