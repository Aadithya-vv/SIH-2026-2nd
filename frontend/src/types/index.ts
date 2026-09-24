export interface Provenance {
  source_type: string;
  source_name: string;
  effective_date: string;
  notes: string;
}
export interface Port {
  name: string;
  country: string;
  maximum_draft: number;
  maximum_loa: number;
  maximum_beam: number;
  reference_waiting_days: number;
  provenance: Provenance;
}
export interface Shipment {
  cargo_type: string;
  cargo_quantity_tonnes: number;
  origin_country: string;
  origin_port: string;
  destination_country: string;
  destination_port: string;
  required_arrival_date: string;
}
export interface Check {
  constraint: string;
  location: string;
  status: string;
  required: number;
  available: number;
  margin: number;
  unit: string;
  explanation: string;
}
export interface Option {
  vessel: {
    name: string;
    typical_draft: number;
    typical_loa: number;
    typical_beam: number;
    usable_cargo_capacity: number;
  };
  feasibility: { status: string; voyage_count: number; checks: Check[] };
  voyage: {
    distance_nm: number;
    sea_days: number;
    return_sea_days: number;
    loading_days: number;
    unloading_days: number;
    port_days: number;
    expected_delay_days: number;
    estimated_total_days: number;
    estimated_arrival: string;
    arrival_feasible: boolean;
  };
  cost: {
    currency: string;
    ocean_freight: number;
    bunker_component: number;
    port_cost: number;
    expected_demurrage: number;
    lighterage_if_applicable: number;
    storage_if_applicable: number;
    total_logistics_cost: number;
    cost_per_tonne: number;
  };
}
export interface Analysis {
  analysis_date: string;
  data_mode: string;
  shipment: Shipment;
  options: Option[];
  recommendation: {
    recommended_vessel: string | null;
    decision: string;
    human_explanation: string[];
    confidence_status: string;
  };
  provenance: Record<string, Provenance>;
  assumptions: Record<string, string | number>;
}
