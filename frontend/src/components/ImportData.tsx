import { useState } from "react";
import type { FormEvent } from "react";
import { request } from "../api/client";
import type { Category, ImportResult } from "../types/market";
interface Form {
  category: Category;
  source_name: string;
  series_name: string;
  csv_text: string;
  date_column: string;
  value_column: string;
  available_at_column: string;
  unit_column: string;
  unit: string;
  currency: string;
  frequency_days: number;
  route: string;
  vessel_class: string;
  commodity: string;
  benchmark: string;
  origin_region: string;
  fuel_type: string;
  port: string;
}
const initial: Form = {
  category: "FREIGHT",
  source_name: "",
  series_name: "",
  csv_text: "",
  date_column: "date",
  value_column: "value",
  available_at_column: "",
  unit_column: "",
  unit: "index_points",
  currency: "",
  frequency_days: 1,
  route: "",
  vessel_class: "PANAMAX",
  commodity: "COKING_COAL",
  benchmark: "",
  origin_region: "",
  fuel_type: "VLSFO",
  port: "",
};
export function ImportData({ onImported }: { onImported: () => void }) {
  const [form, setForm] = useState(initial);
  const [preview, setPreview] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  function update<K extends keyof Form>(key: K, value: Form[K]) {
    setForm((old) => ({ ...old, [key]: value }));
    setPreview(null);
    setError("");
  }
  function payload() {
    return {
      ...form,
      currency: form.currency || null,
      available_at_column: form.available_at_column || null,
      unit_column: form.unit_column || null,
      route: form.route || null,
      vessel_class:
        form.category === "FREIGHT" ? form.vessel_class || null : null,
      commodity: form.category === "COMMODITY" ? form.commodity : null,
      benchmark: form.category === "COMMODITY" ? form.benchmark : null,
      origin_region: form.origin_region || null,
      fuel_type: form.category === "BUNKER" ? form.fuel_type : null,
      port: ["PORT", "BUNKER"].includes(form.category) ? form.port : null,
    };
  }
  async function validate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setPreview(null);
    try {
      setPreview(
        await request<ImportResult>("/api/data/import/csv", payload()),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import validation failed");
    } finally {
      setBusy(false);
    }
  }
  async function commit() {
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      const result = await request<ImportResult>("/api/data/import/csv", {
        ...payload(),
        commit: true,
        preview_hash: preview.preview_hash,
      });
      setPreview(result);
      onImported();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ingestion failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <div className="section-heading">
        <h2>Import historical data</h2>
        <span>CSV / VALIDATE BEFORE INGESTION</span>
      </div>
      <p className="muted">
        Supply data you have permission to use. All imported values retain
        USER_IMPORT provenance. Dates must be ISO format; timezone-free dates
        mean UTC. Maximum 10,000 rows / 2 MB.
      </p>
      <form onSubmit={validate}>
        <fieldset disabled={busy}>
          <div className="market-fields">
            <label>
              Data category
              <select
                value={form.category}
                onChange={(e) => {
                  const category = e.target.value as Category;
                  setForm({
                    ...form,
                    category,
                    unit:
                      category === "FREIGHT"
                        ? "index_points"
                        : category === "PORT"
                          ? "day"
                          : "tonne",
                    currency: ["COMMODITY", "BUNKER"].includes(category)
                      ? "USD"
                      : "",
                  });
                  setPreview(null);
                }}
              >
                {["FREIGHT", "COMMODITY", "BUNKER", "PORT"].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label>
              Source name
              <input
                required
                value={form.source_name}
                onChange={(e) => update("source_name", e.target.value)}
                placeholder="Internal Historical Charter Records"
              />
            </label>
            <label>
              Series name
              <input
                required
                value={form.series_name}
                onChange={(e) => update("series_name", e.target.value)}
              />
            </label>
            <label>
              CSV file
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  setPreview(null);
                  if (!file) return;
                  if (file.size > 2000000) {
                    update("csv_text", "");
                    setError("File exceeds 2 MB.");
                    return;
                  }
                  try {
                    update("csv_text", await file.text());
                  } catch {
                    setError("Could not read the selected file.");
                  }
                }}
              />
            </label>
            <label>
              Date column
              <input
                required
                value={form.date_column}
                onChange={(e) => update("date_column", e.target.value)}
              />
            </label>
            <label>
              Value column
              <input
                required
                value={form.value_column}
                onChange={(e) => update("value_column", e.target.value)}
              />
            </label>
            <label>
              Publication column (optional)
              <input
                value={form.available_at_column}
                onChange={(e) => update("available_at_column", e.target.value)}
                placeholder="known_at"
              />
            </label>
            <label>
              Unit column (optional)
              <input
                value={form.unit_column}
                onChange={(e) => update("unit_column", e.target.value)}
              />
            </label>
            <label>
              Original unit
              <select
                value={form.unit}
                onChange={(e) => update("unit", e.target.value)}
              >
                {[
                  "index_points",
                  "tonne",
                  "t",
                  "metric_ton",
                  "kg",
                  "day",
                  "hours",
                  "hour",
                ].map((u) => (
                  <option key={u}>{u}</option>
                ))}
              </select>
            </label>
            <label>
              Currency (blank for index/days)
              <input
                maxLength={3}
                value={form.currency}
                onChange={(e) =>
                  update("currency", e.target.value.toUpperCase())
                }
                placeholder="USD"
              />
            </label>
            <label>
              Expected interval / days
              <input
                type="number"
                min={1}
                max={366}
                required
                value={form.frequency_days}
                onChange={(e) =>
                  update("frequency_days", Number(e.target.value))
                }
              />
            </label>
            {form.category === "FREIGHT" && (
              <>
                <label>
                  Vessel class
                  <select
                    value={form.vessel_class}
                    onChange={(e) => update("vessel_class", e.target.value)}
                  >
                    <option value="">Not specified</option>
                    {["HANDYSIZE", "SUPRAMAX", "PANAMAX", "CAPESIZE"].map(
                      (v) => (
                        <option key={v}>{v}</option>
                      ),
                    )}
                  </select>
                </label>
                <label>
                  Route (optional)
                  <input
                    value={form.route}
                    onChange={(e) => update("route", e.target.value)}
                    placeholder="Newcastle -> Paradip"
                  />
                </label>
              </>
            )}
            {form.category === "COMMODITY" && (
              <>
                <label>
                  Commodity
                  <select
                    value={form.commodity}
                    onChange={(e) => update("commodity", e.target.value)}
                  >
                    {["COKING_COAL", "THERMAL_COAL", "IRON_ORE"].map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Benchmark
                  <input
                    required
                    value={form.benchmark}
                    onChange={(e) => update("benchmark", e.target.value)}
                  />
                </label>
                <label>
                  Origin region
                  <input
                    value={form.origin_region}
                    onChange={(e) => update("origin_region", e.target.value)}
                  />
                </label>
              </>
            )}
            {["BUNKER", "PORT"].includes(form.category) && (
              <label>
                Port / hub
                <input
                  required
                  value={form.port}
                  onChange={(e) => update("port", e.target.value)}
                  placeholder={
                    form.category === "BUNKER" ? "Singapore" : "Paradip"
                  }
                />
              </label>
            )}
            {form.category === "BUNKER" && (
              <label>
                Fuel type
                <select
                  value={form.fuel_type}
                  onChange={(e) => update("fuel_type", e.target.value)}
                >
                  <option>VLSFO</option>
                  <option>MGO</option>
                </select>
              </label>
            )}
          </div>
          <p className="muted">
            Without a publication column, observations become available at
            ingestion time and cannot populate earlier feature rows. Supplied
            publication times remain unverified user assertions.
          </p>
          <label>
            CSV contents
            <textarea
              required
              rows={5}
              value={form.csv_text}
              onChange={(e) => update("csv_text", e.target.value)}
              placeholder={
                "date,value,known_at\n2026-08-01,1500,2026-08-01T18:00:00Z"
              }
            />
          </label>
          <button className="primary" type="submit">
            {busy ? "Processing..." : "Validate CSV"}
          </button>
        </fieldset>
      </form>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {preview && (
        <div className="import-preview">
          <h3>{preview.committed ? "Import saved" : "Validation preview"}</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Received</th>
                  <th>Accepted</th>
                  <th>Rejected</th>
                  <th>Missing</th>
                  <th>Duplicates</th>
                  <th>Date range</th>
                  <th>Unit / source</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{preview.quality.rows_received}</td>
                  <td>{preview.quality.rows_accepted}</td>
                  <td>{preview.quality.rows_rejected}</td>
                  <td>{preview.quality.missing_values}</td>
                  <td>{preview.quality.duplicates}</td>
                  <td>
                    {preview.quality.start?.slice(0, 10) ?? "-"} /{" "}
                    {preview.quality.end?.slice(0, 10) ?? "-"}
                  </td>
                  <td>
                    {preview.currency} / {preview.unit}
                    <small>{preview.source_label}</small>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="warning">
            {preview.quality.warnings.join(" / ") || "No validation warnings"}
          </p>
          <p className="muted">
            Rejected raw rows are saved for audit. Duplicate observations are
            retained and flagged, then excluded from analytics. Availability
            rule: {preview.normalization.availability}.
          </p>
          {preview.rows.some((r) => r.issues.length > 0) && (
            <details>
              <summary>Row issues (first 50 flagged rows)</summary>
              <table>
                <thead>
                  <tr>
                    <th>CSV row</th>
                    <th>Outcome</th>
                    <th>Issues</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows
                    .filter((r) => r.issues.length)
                    .slice(0, 50)
                    .map((r) => (
                      <tr key={r.row_number}>
                        <td>{r.row_number}</td>
                        <td>{r.accepted ? "Retained" : "Quarantined"}</td>
                        <td>{r.issues.join(", ")}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </details>
          )}
          {!preview.committed && (
            <button
              className="primary"
              disabled={busy || preview.quality.rows_accepted === 0}
              onClick={commit}
            >
              Ingest validated rows
            </button>
          )}
          {preview.committed && (
            <p role="status">
              {preview.already_ingested
                ? "Already ingested; no duplicate import created."
                : "Historical data saved with source and provenance."}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
