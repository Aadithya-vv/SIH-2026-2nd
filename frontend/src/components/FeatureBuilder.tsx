import { useState } from "react";
import { request } from "../api/client";
import type { CatalogEntry, FeatureOutput } from "../types/market";
export function FeatureBuilder({ catalog }: { catalog: CatalogEntry[] }) {
  const [target, setTarget] = useState("");
  const [ids, setIds] = useState<string[]>([]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [cutoff, setCutoff] = useState(new Date().toISOString().slice(0, 16));
  const [gap, setGap] = useState(3);
  const [result, setResult] = useState<FeatureOutput | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function build() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(
        await request<FeatureOutput>("/api/features/build", {
          series_ids: [...new Set([target, ...ids])],
          target_series_id: target,
          start,
          end,
          cutoff_time: cutoff + ":00Z",
          max_fill_days: gap,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Build failed");
    } finally {
      setBusy(false);
    }
  }
  function download() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "feature-dataset.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section>
      <div className="section-heading">
        <h2>Feature dataset builder</h2>
        <span>POINT-IN-TIME / NO FORECASTING</span>
      </div>
      <p className="muted">
        Daily UTC alignment using only observations known at each row time.
        Targets are never filled across days. Predictors use bounded past-only
        filling. Export includes per-cell source times and transformations.
      </p>
      <div className="market-fields">
        <label>
          Freight target
          <select
            value={target}
            onChange={(e) => {
              setTarget(e.target.value);
              setResult(null);
              const item = catalog.find(
                (c) => c.series.series_id === e.target.value,
              );
              setStart(item?.start?.slice(0, 10) ?? "");
              setEnd(item?.end?.slice(0, 10) ?? "");
            }}
          >
            <option value="">Select a target</option>
            {catalog
              .filter((c) => c.series.category === "FREIGHT")
              .map((c) => (
                <option key={c.series.series_id} value={c.series.series_id}>
                  {c.series.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Start date
          <input
            type="date"
            value={start}
            onChange={(e) => {
              setStart(e.target.value);
              setResult(null);
            }}
          />
        </label>
        <label>
          End date
          <input
            type="date"
            value={end}
            onChange={(e) => {
              setEnd(e.target.value);
              setResult(null);
            }}
          />
        </label>
        <label>
          Cutoff time / UTC
          <input
            type="datetime-local"
            value={cutoff}
            onChange={(e) => {
              setCutoff(e.target.value);
              setResult(null);
            }}
          />
        </label>
        <label>
          Maximum predictor fill / days
          <input
            type="number"
            min={0}
            max={30}
            value={gap}
            onChange={(e) => {
              setGap(Number(e.target.value));
              setResult(null);
            }}
          />
        </label>
      </div>
      <details>
        <summary>Select predictors ({ids.length})</summary>
        <div className="predictor-list">
          {catalog
            .filter((c) => c.series.series_id !== target)
            .map((c) => (
              <label key={c.series.series_id}>
                <input
                  type="checkbox"
                  checked={ids.includes(c.series.series_id)}
                  onChange={(e) => {
                    setIds(
                      e.target.checked
                        ? [...ids, c.series.series_id]
                        : ids.filter((id) => id !== c.series.series_id),
                    );
                    setResult(null);
                  }}
                />
                {c.series.name}
              </label>
            ))}
        </div>
      </details>
      <button
        className="primary"
        disabled={busy || !target || !start || !end}
        onClick={build}
      >
        {busy ? "Building..." : "Build feature dataset"}
      </button>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {result && (
        <div>
          <p role="status">
            {result.rows.length} aligned rows / {result.suitability}
          </p>
          <p className="muted">
            Missing cells:{" "}
            {Object.values(result.missing_by_series).reduce((a, b) => a + b, 0)}
            . Filled predictor cells:{" "}
            {Object.values(result.filled_by_series).reduce((a, b) => a + b, 0)}.
            Inspect the export before using this dataset for modelling.
          </p>
          <button className="text-button" onClick={download}>
            Download dataset + lineage (JSON)
          </button>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Freight target</th>
                  <th>Predictor values (first 7 rows)</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.slice(0, 7).map((row) => (
                  <tr key={row.date}>
                    <td>{row.date}</td>
                    <td>{row.freight_target ?? "MISSING"}</td>
                    <td>
                      {Object.entries(row.values).map(([key, v]) => (
                        <small key={key}>
                          {key}: {v ?? "MISSING"}
                        </small>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
