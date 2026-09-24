import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { request } from "../api/client";
import type {
  CatalogEntry,
  History,
  Source,
  Trends,
  MarketObservation,
} from "../types/market";
import { ImportData } from "../components/ImportData";
import { FeatureBuilder } from "../components/FeatureBuilder";
const fmt = (value: number | null | undefined) =>
  value == null
    ? "Unavailable"
    : value.toLocaleString(undefined, { maximumFractionDigits: 3 });
export function MarketIntelligence() {
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [selected, setSelected] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [history, setHistory] = useState<History | null>(null);
  const [trends, setTrends] = useState<Trends | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [tab, setTab] = useState("History");
  useEffect(() => {
    let active = true;
    setError("");
    Promise.all([
      request<CatalogEntry[]>("/api/data/catalog"),
      request<Source[]>("/api/data/sources"),
    ])
      .then(([c, s]) => {
        if (active) {
          setCatalog(c);
          setSources(s);
          setSelected((old) => old || c[0]?.series.series_id || "");
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [revision]);
  useEffect(() => {
    if (!selected) return;
    let active = true;
    setHistory(null);
    setTrends(null);
    setError("");
    const q = new URLSearchParams();
    if (start) q.set("start", start);
    if (end) q.set("end", end);
    Promise.all([
      request<History>(`/api/data/series/${selected}?${q}`),
      request<Trends>(`/api/market/trends?series_id=${selected}&${q}`),
    ])
      .then(([h, t]) => {
        if (active) {
          setHistory(h);
          setTrends(t);
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [selected, start, end, revision]);
  const item = catalog.find((c) => c.series.series_id === selected);
  const q = item?.quality;
  // Keep the latest known revision; break visible gaps instead of interpolating them.
  const revisions = new Map<string, MarketObservation>();
  for (const observation of history?.observations ?? []) {
    if (!observation.quality_flags.includes("DUPLICATE"))
      revisions.set(observation.timestamp, observation);
  }
  const chart: { time: number; value: number | null }[] = [];
  const interval = (item?.series.frequency_days ?? 1) * 86400000;
  for (const observation of revisions.values()) {
    const time = Date.parse(observation.timestamp);
    const previous = chart[chart.length - 1];
    if (previous && time - previous.time > interval * 1.5)
      chart.push({ time: previous.time + interval, value: null });
    chart.push({ time, value: observation.value });
  }
  return (
    <>
      <div className="section-heading">
        <h2>Data status</h2>
        <button
          className="text-button"
          onClick={() => setRevision((r) => r + 1)}
        >
          Refresh catalog
        </button>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Category</th>
              <th>Status</th>
              <th>Latest observation</th>
              <th>Source / range</th>
            </tr>
          </thead>
          <tbody>
            {["FREIGHT", "COMMODITY", "BUNKER", "PORT"].map((category) => {
              const entries = catalog
                .filter((c) => c.series.category === category)
                .sort(
                  (a, b) =>
                    Number(a.status === "DEMO") - Number(b.status === "DEMO") ||
                    (b.end ?? "").localeCompare(a.end ?? ""),
                );
              const entry = entries[0];
              return (
                <tr key={category}>
                  <th>{category}</th>
                  <td>
                    {entry?.status ?? "UNAVAILABLE"}
                    <small>
                      {entry?.series.provenance.source_type ??
                        "SOURCE NOT CONNECTED"}
                    </small>
                  </td>
                  <td>
                    {entry?.end?.slice(0, 10) ?? "-"}
                    <small className="warning">
                      {entry?.quality.stale ? "STALE" : ""}
                    </small>
                  </td>
                  <td>
                    {entry?.source.name ?? "No data available"}
                    <small>
                      {entry?.start?.slice(0, 10)} / {entry?.end?.slice(0, 10)}{" "}
                      / {entries.length} series
                    </small>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="market-tabs">
        {["History", "Data catalog", "Import data", "Feature dataset"].map(
          (t) => (
            <button
              className={t === tab ? "active" : ""}
              key={t}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ),
        )}
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {tab === "History" && (
        <>
          <section>
            <div className="section-heading">
              <h2>Market history</h2>
              <span>
                {item?.series.provenance.source_type ?? "LOADING"} / DESCRIPTIVE
                ONLY
              </span>
            </div>
            <div className="market-filters">
              <label>
                Historical series
                <select
                  value={selected}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  {catalog.map((c) => (
                    <option key={c.series.series_id} value={c.series.series_id}>
                      {c.series.name} / {c.status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                From date
                <input
                  type="date"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                />
              </label>
              <label>
                Through date
                <input
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                />
              </label>
            </div>
            <p className="muted">
              {item?.source.name} / {item?.series.provenance.source_type} /{" "}
              {item?.series.currency ? `${item.series.currency} per ` : ""}
              {item?.series.unit}. No forecast. Duplicate rows excluded; source
              revisions remain visible in history.
            </p>
            <div className="market-chart">
              {chart.length ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart
                    data={chart}
                    margin={{ top: 15, right: 25, left: 20, bottom: 10 }}
                  >
                    <CartesianGrid stroke="#2b343c" vertical={false} />
                    <XAxis
                      dataKey="time"
                      type="number"
                      scale="time"
                      domain={["dataMin", "dataMax"]}
                      tickFormatter={(value) =>
                        new Date(value).toISOString().slice(0, 10)
                      }
                      minTickGap={65}
                      tick={{ fill: "#8e9ba5", fontSize: 10 }}
                    />
                    <YAxis
                      domain={["auto", "auto"]}
                      tick={{ fill: "#8e9ba5", fontSize: 10 }}
                    />
                    <Tooltip
                      labelFormatter={(value) =>
                        new Date(Number(value)).toISOString().slice(0, 10)
                      }
                      contentStyle={{
                        background: "#20282f",
                        border: "1px solid #42515d",
                        color: "#fff",
                      }}
                    />
                    <Line
                      type="linear"
                      dataKey="value"
                      stroke="#99bdb9"
                      strokeWidth={1.5}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="empty">
                  {history
                    ? "No observations in this date range."
                    : "Loading history..."}
                </p>
              )}
            </div>
          </section>
          <div className="two-columns">
            <section>
              <div className="section-heading">
                <h2>Source & provenance</h2>
                <span>{item?.status}</span>
              </div>
              <dl className="data-details">
                <dt>Source</dt>
                <dd>{item?.source.name}</dd>
                <dt>Access</dt>
                <dd>{item?.source.access_type}</dd>
                <dt>Provenance</dt>
                <dd>{item?.series.provenance.source_type}</dd>
                <dt>Latest observation</dt>
                <dd>{item?.end ?? "-"}</dd>
                <dt>Last ingestion</dt>
                <dd>{item?.source.last_successful_ingestion ?? "-"}</dd>
                <dt>Original currency / canonical unit</dt>
                <dd>
                  {item?.series.currency ?? "No currency"} / {item?.series.unit}
                </dd>
                <dt>Selected range records</dt>
                <dd>{history?.observations.length ?? 0}</dd>
                <dt>Forecast suitability</dt>
                <dd>{item?.forecast_suitability}</dd>
              </dl>
              <p className="muted">{item?.source.license_notes}</p>
            </section>
            <section>
              <div className="section-heading">
                <h2>Data quality</h2>
                <span>ENTIRE DATASET</span>
              </div>
              <dl className="data-details">
                <dt>Status</dt>
                <dd>{q?.status}</dd>
                <dt>Completeness</dt>
                <dd>{fmt(q?.completeness_percent)}%</dd>
                <dt>Missing values / periods</dt>
                <dd>
                  {q?.missing_values ?? "-"} / {q?.missing_periods ?? "-"}
                </dd>
                <dt>Duplicates</dt>
                <dd>{q?.duplicates ?? "-"}</dd>
                <dt>Rejected rows</dt>
                <dd>{q?.rows_rejected ?? "-"}</dd>
                <dt>Observation age</dt>
                <dd>{fmt(q?.latest_age_days)} days</dd>
              </dl>
              <p className="warning">
                {q?.warnings.join(" / ") || "No quality warnings"}
              </p>
              <p className="muted">
                Completeness measures non-empty mapped date and value fields.
                Missing periods use the declared calendar-day interval;
                freshness threshold is max(7 days, twice the interval).
              </p>
            </section>
          </div>
          <section>
            <div className="section-heading">
              <h2>Descriptive statistics</h2>
              <span>SELECTED DATE RANGE</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {[
                      "Latest",
                      "7-period mean",
                      "30-period mean",
                      "Change",
                      "Change %",
                      "30-return volatility",
                      "Minimum",
                      "Maximum",
                    ].map((k) => (
                      <th key={k}>{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    {[
                      trends?.latest,
                      trends?.mean_7,
                      trends?.mean_30,
                      trends?.change,
                      trends?.change_percent,
                      trends?.rolling_volatility,
                      trends?.minimum,
                      trends?.maximum,
                    ].map((v, i) => (
                      <td key={i}>{fmt(v)}</td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="muted">
              {trends?.method} Insufficient history returns Unavailable.
              Volatility is a fractional return statistic.
            </p>
          </section>
        </>
      )}
      {tab === "Data catalog" && (
        <>
          <section>
            <div className="section-heading">
              <h2>Available series</h2>
              <span>{catalog.length} SERIES</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Series / category</th>
                    <th>Source / provenance</th>
                    <th>Frequency</th>
                    <th>Start / end</th>
                    <th>Records</th>
                    <th>Quality / status</th>
                  </tr>
                </thead>
                <tbody>
                  {catalog.map((c) => (
                    <tr key={c.series.series_id}>
                      <th>
                        <button
                          className="text-button"
                          onClick={() => {
                            setSelected(c.series.series_id);
                            setStart("");
                            setEnd("");
                            setTab("History");
                          }}
                        >
                          {c.series.name}
                        </button>
                        <small>{c.series.category}</small>
                      </th>
                      <td>
                        {c.source.name}
                        <small>{c.series.provenance.source_type}</small>
                      </td>
                      <td>{c.series.frequency_days} day(s)</td>
                      <td>
                        {c.start?.slice(0, 10)}
                        <small>{c.end?.slice(0, 10)}</small>
                      </td>
                      <td>{c.records}</td>
                      <td>
                        {c.quality.status}
                        <small>
                          {c.status} / {c.forecast_suitability}
                        </small>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section>
            <div className="section-heading">
              <h2>Source registry</h2>
              <span>INCLUDING UNAVAILABLE SOURCES</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Source / provider</th>
                    <th>Access</th>
                    <th>Availability</th>
                    <th>License / notes</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((s) => (
                    <tr key={s.source_id}>
                      <th>
                        {s.name}
                        <small>{s.provider}</small>
                      </th>
                      <td>{s.access_type}</td>
                      <td>{s.availability_status}</td>
                      <td>
                        {s.license_notes}
                        <small>{s.notes}</small>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
      {tab === "Import data" && (
        <ImportData onImported={() => setRevision((r) => r + 1)} />
      )}
      {tab === "Feature dataset" && <FeatureBuilder catalog={catalog} />}
    </>
  );
}
