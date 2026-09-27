import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { request } from "./api/client";
import type { Analysis, Option, Port, Shipment } from "./types";
import { CostChart } from "./components/CostChart";
import { MarketIntelligence } from "./pages/MarketIntelligence";
import { MarketContext } from "./components/MarketContext";
import { FreightForecast } from "./pages/FreightForecast";
import { FreightOutlook } from "./components/FreightOutlook";
import { CharterDecision } from "./pages/CharterDecision";
import { DecisionHistory } from "./pages/DecisionHistory";

const modules = [
  "Control center",
  "Voyage optimizer",
  "Port & vessel",
  "Market intelligence",
  "Freight forecast",
  "Charter decision",
  "Scenario lab",
  "Portfolio",
  "Decision history",
];
const initialDate = new Date();
initialDate.setUTCDate(initialDate.getUTCDate() + 60);
const initial: Shipment = {
  cargo_type: "COKING_COAL",
  cargo_quantity_tonnes: 70000,
  origin_country: "Australia",
  origin_port: "Newcastle",
  destination_country: "India",
  destination_port: "Paradip",
  required_arrival_date: initialDate.toISOString().slice(0, 10),
};
const money = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
const number = (n: number) =>
  n.toLocaleString("en-US", { maximumFractionDigits: 1 });
const pretty = (s: string) => s.replaceAll("_", " ").toLowerCase();
function Status({ value }: { value: string }) {
  return <span className={`status ${value.toLowerCase()}`}>{value}</span>;
}

export default function App() {
  const [page, setPage] = useState("Voyage optimizer");
  const [savedCharterId, setSavedCharterId] = useState<string | null>(null);
  const [ports, setPorts] = useState<Port[]>([]);
  const [form, setForm] = useState<Shipment>(initial);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [selected, setSelected] = useState("PANAMAX");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [online, setOnline] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all([request<Port[]>("/api/reference/ports"), request("/health")])
      .then(([p]) => {
        if (active) {
          setPorts(p);
          setOnline(true);
        }
      })
      .catch(() => {
        if (active)
          setError("Backend unavailable. Start the API and reload this page.");
      });
    return () => {
      active = false;
    };
  }, []);
  const best = analysis?.options.find(
    (o) => o.vessel.name === analysis.recommendation.recommended_vessel,
  );
  const chosen =
    analysis?.options.find((o) => o.vessel.name === selected) ??
    analysis?.options[0];
  const dirty =
    analysis &&
    Object.entries(form).some(
      ([key, value]) => analysis.shipment[key as keyof Shipment] !== value,
    );
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setAnalysis(null);
    try {
      const result = await request<Analysis>("/api/shipments/analyze", form);
      setAnalysis(result);
      setSelected(
        result.recommendation.recommended_vessel ??
          result.options[0].vessel.name,
      );
      setOnline(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }
  function setPort(kind: "origin" | "destination", name: string) {
    const p = ports.find((p) => p.name === name);
    if (p)
      setForm({
        ...form,
        [`${kind}_port`]: name,
        [`${kind}_country`]: p.country,
      });
  }
  const inputForm = (
    <form className="shipment-form" onSubmit={submit}>
      <div className="section-heading">
        <h2>Plan a shipment</h2>
        <span>01 / SHIPMENT REQUIREMENT</span>
      </div>
      <div className="fields">
        <label>
          Cargo
          <select
            value={form.cargo_type}
            onChange={(e) => setForm({ ...form, cargo_type: e.target.value })}
          >
            <option value="COKING_COAL">Coking coal</option>
            <option value="THERMAL_COAL">Thermal coal</option>
            <option value="IRON_ORE">Iron ore</option>
          </select>
        </label>
        <label>
          Quantity &middot; tonnes
          <input
            type="number"
            min="1"
            max="1000000"
            step="any"
            required
            value={form.cargo_quantity_tonnes}
            onChange={(e) =>
              setForm({
                ...form,
                cargo_quantity_tonnes: Number(e.target.value),
              })
            }
          />
        </label>
        <label>
          Origin port
          <select
            value={form.origin_port}
            onChange={(e) => setPort("origin", e.target.value)}
          >
            {ports
              .filter((p) => p.country !== "India")
              .map((p) => (
                <option key={p.name}>{p.name}</option>
              ))}
          </select>
        </label>
        <label>
          Destination port
          <select
            value={form.destination_port}
            onChange={(e) => setPort("destination", e.target.value)}
          >
            {ports
              .filter((p) => p.country === "India")
              .map((p) => (
                <option key={p.name}>{p.name}</option>
              ))}
          </select>
        </label>
        <label>
          Required arrival
          <input
            type="date"
            required
            min={new Date().toISOString().slice(0, 10)}
            value={form.required_arrival_date}
            onChange={(e) =>
              setForm({ ...form, required_arrival_date: e.target.value })
            }
          />
        </label>
        <button className="primary" disabled={busy || !ports.length}>
          {busy ? "Analyzing..." : "Analyze voyage"}{" "}
          <span aria-hidden="true">&rarr;</span>
        </button>
      </div>
      <p className="muted">
        USD estimates &middot; Immediate departure &middot; Sequential voyages
        &middot; All reference inputs are demo assumptions
      </p>
    </form>
  );
  const summary = analysis && (
    <section className="strategy">
      <div className="section-heading">
        <h2>Recommended strategy</h2>
        <span>VESSEL + COST OPTIMIZATION</span>
      </div>
      <div className="metrics">
        <div>
          <span>Recommended vessel</span>
          <strong>
            {best ? pretty(best.vessel.name) : "No feasible option"}
          </strong>
          <small>
            {best ? "Lowest eligible total cost" : "Review constraints below"}
          </small>
        </div>
        <div>
          <span>Logistics estimate &middot; USD</span>
          <strong>{best ? money(best.cost.total_logistics_cost) : "-"}</strong>
          <small>
            {best
              ? `USD ${best.cost.cost_per_tonne.toFixed(2)} / tonne`
              : "No recommendation"}
          </small>
        </div>
        <div>
          <span>Delivery duration</span>
          <strong>
            {best ? `${number(best.voyage.estimated_total_days)} days` : "-"}
          </strong>
          <small>
            {best
              ? `Arrival ${best.voyage.estimated_arrival}`
              : "Deadline or port constraints"}
          </small>
        </div>
        <div>
          <span>Charter timing</span>
          <button className="text-button" onClick={() => {setSavedCharterId(null);setPage("Charter decision");}}>Open charter decision →</button>
          <small>Analyze forecast, deadline and downside separately</small>
        </div>
      </div>
      <details open className="why">
        <summary>Why this recommendation?</summary>
        <ul>
          {analysis.recommendation.human_explanation.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </details>
    </section>
  );
  function comparison() {
    return (
      analysis && (
        <section>
          <div className="section-heading">
            <h2>Vessel comparison</h2>
            <span>04 CLASSES EVALUATED</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Vessel class</th>
                  <th>Port / capacity</th>
                  <th>Voyages</th>
                  <th>Total days</th>
                  <th>Arrival / deadline</th>
                  <th>Total USD</th>
                  <th>USD / t</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {analysis.options.map((o) => (
                  <tr
                    key={o.vessel.name}
                    className={
                      o.vessel.name === best?.vessel.name ? "recommended" : ""
                    }
                  >
                    <th>
                      {pretty(o.vessel.name)}
                      {o.vessel.name === best?.vessel.name && (
                        <small className="selected-label">RECOMMENDED</small>
                      )}
                    </th>
                    <td>
                      <Status value={o.feasibility.status} />
                    </td>
                    <td>{o.feasibility.voyage_count}</td>
                    <td>{number(o.voyage.estimated_total_days)}</td>
                    <td>
                      {o.voyage.estimated_arrival}
                      <small
                        className={o.voyage.arrival_feasible ? "pass" : "fail"}
                      >
                        {o.voyage.arrival_feasible
                          ? "Meets deadline"
                          : "Misses deadline"}
                      </small>
                    </td>
                    <td>{money(o.cost.total_logistics_cost)}</td>
                    <td>{o.cost.cost_per_tonne.toFixed(2)}</td>
                    <td>
                      <button
                        className="text-button"
                        onClick={() => {
                          setSelected(o.vessel.name);
                          setPage("Port & vessel");
                        }}
                      >
                        Why? &#8599;
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted">
            Costs for failed options are hypothetical comparisons. They are
            excluded from selection. CONDITIONAL means multiple sequential
            voyages.
          </p>
        </section>
      )
    );
  }
  function checks(o: Option) {
    return (
      <section>
        <div className="section-heading">
          <h2>{pretty(o.vessel.name)} / check results</h2>
          <span>BOTH PORTS + SHIPMENT</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Location</th>
                <th>Constraint</th>
                <th>Required</th>
                <th>Available</th>
                <th>Margin</th>
                <th>Status / reason</th>
              </tr>
            </thead>
            <tbody>
              {o.feasibility.checks.map((c, i) => (
                <tr key={i}>
                  <td>{c.location}</td>
                  <th>{c.constraint}</th>
                  <td>
                    {number(c.required)} {c.unit}
                  </td>
                  <td>
                    {number(c.available)} {c.unit}
                  </td>
                  <td>
                    {c.margin > 0 ? "+" : ""}
                    {number(c.margin)} {c.unit}
                  </td>
                  <td>
                    <Status value={c.status} />
                    <small>{c.explanation}</small>
                  </td>
                </tr>
              ))}
              <tr>
                <td>Final delivery</td>
                <th>ARRIVAL</th>
                <td>{analysis?.shipment.required_arrival_date}</td>
                <td>{o.voyage.estimated_arrival}</td>
                <td>-</td>
                <td>
                  <Status value={o.voyage.arrival_feasible ? "PASS" : "FAIL"} />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    );
  }
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">F/</span> FREIGHT INTELLIGENCE
        </div>
        <div className="top-context">
          OPERATIONS / <b>{page.toUpperCase()}</b>
        </div>
        <div className="top-status">
          <span className="demo-tag">COST MODE: DEMO</span>
          <span className={online ? "pass" : "muted"}>
            API {online ? "connected" : "unavailable"}
          </span>
        </div>
      </header>
      <aside>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {modules.map((m, i) => (
            <button
              key={m}
              onClick={() => {if(m === "Charter decision") setSavedCharterId(null);setPage(m);}}
              className={page === m ? "active" : ""}
            >
              <span className="nav-index">0{i + 1}</span>
              {m}
              {["Scenario lab", "Portfolio"].includes(m) && <span className="planned-dot">&#9675;</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="nav-label">REFERENCE ENVIRONMENT</div>
          <strong>Demo cost assumptions</strong>
          <p>
            Market data carries its own source labels. No live market feeds.
          </p>
          <span>PHASE 04 / CORE PROTOTYPE</span>
        </div>
      </aside>
      <main>
        <div className="page-heading">
          <div>
            <div className="eyebrow">
              MARITIME PROCUREMENT / DECISION SUPPORT
            </div>
            <h1>{page}</h1>
            <p>
              {page === "Voyage optimizer"
                ? "From shipment requirement to an explainable vessel decision."
                : page === "Port & vessel"
                  ? "Inspect the operational constraints behind every vessel option."
                  : page === "Control center"
                    ? "Your current shipment and the decisions that matter."
                    : page === "Market intelligence"
                      ? "Inspect historical data, source provenance and forecast readiness."
                      : page === "Freight forecast"
                        ? "Inspect forecast ranges, historical performance and model provenance."
                        : page === "Charter decision"
                          ? "Compare shipment economics, schedule slack and forecast downside."
                          : page === "Decision history"
                            ? "Reconstruct the evidence behind saved charter decisions."
                            : "Future work outside the core prototype."}
            </p>
          </div>
          <span className="edition">
            {["Charter decision", "Decision history"].includes(page) ? "PHASE 04" : page === "Freight forecast"
              ? "BATCH 03"
              : page === "Market intelligence"
                ? "BATCH 02"
                : "BATCH 01"}
            <br />
            <b>
              {["Charter decision", "Decision history"].includes(page) ? "CHARTER DECISION SUPPORT" : page === "Market intelligence"
                ? "MARKET DATA FOUNDATION"
                : page === "Freight forecast"
                  ? "PROBABILISTIC FORECAST"
                  : "VESSEL & COST ENGINE"}
            </b>
          </span>
        </div>
        <div className="demo-banner">
          <strong>DEMO REFERENCE</strong>
          <span>
            All port limits, route distances and rates are illustrative.
            Estimates are not operational quotations.
          </span>
        </div>
        {error && (
          <div role="alert" className="error">
            {error}
          </div>
        )}
        {busy && (
          <p role="status">
            Evaluating four vessel classes against ports, cost and arrival
            deadline...
          </p>
        )}
        {page === "Voyage optimizer" && (
          <>
            {inputForm}
            {dirty && (
              <p className="warning">
                Inputs changed. Analyze again to update the results below.
              </p>
            )}
            {analysis ? (
              <>
                {summary}
                <MarketContext
                  shipment={analysis.shipment}
                  vesselClass={best?.vessel.name ?? ""}
                />
                <FreightOutlook
                  shipment={analysis.shipment}
                  vesselClass={best?.vessel.name ?? ""}
                  onOpen={() => setPage("Freight forecast")}
                />
                {comparison()}
                {best && (
                  <>
                    <CostChart option={best} />
                    <section>
                      <div className="section-heading">
                        <h2>Voyage timeline</h2>
                        <span>
                          {number(best.voyage.distance_nm)} NM / OUTBOUND LEG
                        </span>
                      </div>
                      <div className="timeline">
                        {[
                          ["Loading", best.voyage.loading_days],
                          ["Sea passage", best.voyage.sea_days],
                          ["Return passages", best.voyage.return_sea_days],
                          ["Expected waiting", best.voyage.expected_delay_days],
                          ["Unloading", best.voyage.unloading_days],
                        ].map(([label, days]) => (
                          <div key={label}>
                            <span>{label}</span>
                            <strong>{number(Number(days))} d</strong>
                          </div>
                        ))}
                      </div>
                      <p className="muted">
                        {analysis.shipment.origin_port} &rarr;{" "}
                        {analysis.shipment.destination_port}. Times aggregate
                        all sequential deliveries; return passages occur between
                        deliveries. No final return leg.
                      </p>
                    </section>
                  </>
                )}
              </>
            ) : (
              <div className="empty">
                <span className="eyebrow">READY TO ANALYZE</span>
                <h2>Define the shipment. See the trade-offs.</h2>
                <p>
                  The engine will compare all four vessel classes, explain port
                  constraints, and calculate every cost component.
                </p>
              </div>
            )}
          </>
        )}
        {page === "Port & vessel" && (
          <>
            {!analysis ? (
              <div className="empty">
                <h2>No shipment analyzed yet</h2>
                <p>
                  Compatibility depends on both ports and the cargo quantity.
                </p>
                <button
                  className="primary"
                  onClick={() => setPage("Voyage optimizer")}
                >
                  Plan a shipment &rarr;
                </button>
              </div>
            ) : (
              <>
                <section>
                  <div className="section-heading">
                    <h2>
                      {analysis.shipment.origin_port} &rarr;{" "}
                      {analysis.shipment.destination_port}
                    </h2>
                    <span>DEMO COMPATIBILITY MATRIX</span>
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Vessel class</th>
                          <th>Draft &middot; m</th>
                          <th>LOA &middot; m</th>
                          <th>Beam &middot; m</th>
                          <th>Capacity &middot; t</th>
                          <th>Compatibility</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analysis.options.map((o) => (
                          <tr
                            key={o.vessel.name}
                            className={
                              selected === o.vessel.name ? "recommended" : ""
                            }
                          >
                            <th>
                              <button
                                className="text-button"
                                onClick={() => setSelected(o.vessel.name)}
                              >
                                {pretty(o.vessel.name)}
                              </button>
                            </th>
                            <td>{o.vessel.typical_draft}</td>
                            <td>{o.vessel.typical_loa}</td>
                            <td>{o.vessel.typical_beam}</td>
                            <td>{number(o.vessel.usable_cargo_capacity)}</td>
                            <td>
                              <Status value={o.feasibility.status} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
                {chosen && checks(chosen)}
              </>
            )}
            <p className="muted">
              Class-level dimensions only. Real clearance requires vessel
              particulars, terminal restrictions, tide windows and official port
              circulars. Reduced-draft loading and lighterage are not modelled.
            </p>
          </>
        )}
        {page === "Control center" && (
          <>
            {analysis ? (
              <>
                <section>
                  <div className="section-heading">
                    <h2>Active demo shipment</h2>
                    <button
                      className="text-button"
                      onClick={() => setPage("Voyage optimizer")}
                    >
                      Edit shipment &#8599;
                    </button>
                  </div>
                  <div className="metrics">
                    <div>
                      <span>Cargo</span>
                      <strong className="smaller">
                        {pretty(analysis.shipment.cargo_type)}
                      </strong>
                      <small>
                        {number(analysis.shipment.cargo_quantity_tonnes)} tonnes
                      </small>
                    </div>
                    <div>
                      <span>Origin</span>
                      <strong className="smaller">
                        {analysis.shipment.origin_port}
                      </strong>
                    </div>
                    <div>
                      <span>Destination</span>
                      <strong className="smaller">
                        {analysis.shipment.destination_port}
                      </strong>
                    </div>
                    <div>
                      <span>Required arrival</span>
                      <strong className="smaller">
                        {analysis.shipment.required_arrival_date}
                      </strong>
                    </div>
                  </div>
                </section>
                {summary}
              </>
            ) : (
              <div className="empty">
                <h2>No active shipment</h2>
                <p>
                  Analyze a shipment to populate the control center with
                  calculated results.
                </p>
                <button
                  className="primary"
                  onClick={() => setPage("Voyage optimizer")}
                >
                  Plan a shipment &rarr;
                </button>
              </div>
            )}
            <MarketContext
              shipment={analysis?.shipment ?? form}
              vesselClass={best?.vessel.name ?? ""}
            />
            <FreightOutlook
              shipment={analysis?.shipment ?? form}
              vesselClass={best?.vessel.name ?? ""}
              onOpen={() => setPage("Freight forecast")}
            />
            <div className="two-columns">
              <section>
                <div className="section-heading">
                  <h2>Port waiting assumptions</h2>
                  <span>DEMO / DAYS</span>
                </div>
                {ports
                  .filter((p) => p.country === "India")
                  .map((p) => (
                    <div className="port-row" key={p.name}>
                      <span>{p.name}</span>
                      <b>{p.reference_waiting_days.toFixed(1)} days</b>
                      <span className="muted">ASSUMED</span>
                    </div>
                  ))}
              </section>
              <section>
                <div className="section-heading">
                  <h2>Market intelligence</h2>
                  <button
                    className="text-button"
                    onClick={() => setPage("Market intelligence")}
                  >
                    Open data workspace &rarr;
                  </button>
                </div>
                <p className="muted">
                  Historical imports and simulated series have separate
                  provenance. Review freshness and quality before modelling.
                </p>
              </section>
            </div>
          </>
        )}
        {page === "Market intelligence" && <MarketIntelligence />}
        {page === "Freight forecast" && <FreightForecast />}
        {page === "Charter decision" && <CharterDecision key={savedCharterId ?? 'new'} ports={ports} savedId={savedCharterId} onForecast={() => setPage("Freight forecast")} />}
        {page === "Decision history" && <DecisionHistory onOpen={id => {setSavedCharterId(id);setPage("Charter decision");}} />}
        {["Scenario lab", "Portfolio"].includes(page) && (
          <div className="empty planned">
            <span className="eyebrow">
              PLANNED MODULE / BATCH{" "}
              {page === "Scenario lab"
                ? "05"
                : page === "Portfolio"
                  ? "06"
                  : "07"}
            </span>
            <h2>
              {page === "Scenario lab"
                ? "Test the impact of disruption."
                : page === "Portfolio"
                  ? "Plan across the procurement year."
                  : "Trace decisions back to their inputs."}
            </h2>
            <p>
              {page === "Scenario lab"
                ? "Fuel, freight, congestion and inventory scenarios will compare against the deterministic baseline."
                : page === "Portfolio"
                  ? "Annual procurement allocation and vessel scheduling are reserved for a later batch."
                  : "Saved decisions, versioned assumptions and exportable reports are planned. Analysis snapshots are saved locally; history browsing is planned."}
            </p>
            <button
              className="text-button"
              onClick={() => setPage("Voyage optimizer")}
            >
              Return to voyage optimizer &rarr;
            </button>
          </div>
        )}
        {analysis && modules.indexOf(page) < 3 && (
          <details className="provenance">
            <summary>
              Assumptions & data provenance &middot; analysis{" "}
              {analysis.analysis_date}
            </summary>
            <div className="two-columns">
              <div>
                <h3>Calculation assumptions</h3>
                {Object.entries(analysis.assumptions).map(([k, v]) => (
                  <p key={k}>
                    <b>{pretty(k)}:</b> {v}
                  </p>
                ))}
              </div>
              <div>
                <h3>Input lineage</h3>
                {Object.entries(analysis.provenance).map(([k, v]) => (
                  <p key={k}>
                    <b>{pretty(k)}</b> &middot; {v.source_type}
                    <br />
                    {v.source_name} &middot; {v.effective_date}
                    <br />
                    <span className="muted">{v.notes}</span>
                  </p>
                ))}
              </div>
            </div>
          </details>
        )}
        <footer>
          <span>FREIGHT INTELLIGENCE / ENGINE v0.4</span>
          <span>DEMO ESTIMATES &middot; NOT VALIDATED FOR CHARTERING</span>
        </footer>
      </main>
    </div>
  );
}
