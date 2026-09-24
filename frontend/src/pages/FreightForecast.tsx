import { useEffect, useState } from "react";
import {
  Area,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts";
import { request } from "../api/client";
import type { CatalogEntry } from "../types/market";
import type { FreightForecast as Result, Backtest } from "../types/forecast";
type ChartPoint = {
  time: number;
  actual?: number;
  median?: number;
  p50?: number;
  band?: number[];
};
const fmt = (v: number | undefined) =>
  v === undefined
    ? "Unavailable"
    : v.toLocaleString(undefined, { maximumFractionDigits: 2 });
const percent = (v: number) => `${(100 * v).toFixed(1)}%`;
export function FreightForecast() {
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [series, setSeries] = useState("");
  const [asOf, setAsOf] = useState("");
  const [contexts, setContexts] = useState<string[]>([]);
  const [horizon, setHorizon] = useState(7);
  const [result, setResult] = useState<Result | null>(null);
  const [backtest, setBacktest] = useState<Backtest | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [view, setView] = useState("Forecast");
  useEffect(() => {
    let active = true;
    request<CatalogEntry[]>("/api/data/catalog")
      .then((data) => {
        if (active) {
          setCatalog(data);
          const target =
            data.find((c) => c.series.series_id === "demo_panamax_index") ??
            data.find((c) => c.series.category === "FREIGHT");
          if (target) {
            setSeries(target.series.series_id);
            setAsOf(target.end?.slice(0, 10) ?? "");
          }
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!series) return;
    let active = true;
    setResult(null);
    setBacktest(null);
    setMessage("Loading saved forecast...");
    request<Result>("/api/forecast/freight/" + series)
      .then((data) => {
        if (active) {
          setResult(data);
          setMessage("");
        }
      })
      .catch(() => {
        if (active)
          setMessage(
            "Forecast unavailable. Train and evaluate this series to create a forecast. At least 250 complete daily feature rows are required.",
          );
      });
    return () => {
      active = false;
    };
  }, [series]);
  async function train() {
    setBusy(true);
    setError("");
    setMessage(
      "Training baselines and candidates, calibrating intervals and scoring chronological holdouts...",
    );
    setResult(null);
    setBacktest(null);
    try {
      const r = await request<Result>("/api/forecast/train", {
        series_id: series,
        as_of_time: asOf + "T23:59:59Z",
        horizons: [1, 3, 7, 14],
        context_series_ids: contexts,
      });
      setResult(r);
      setMessage("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Training failed");
      setMessage(
        "No forecast created. Review data freshness and publication coverage.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function loadBacktest() {
    if (!result) return;
    setError("");
    try {
      setBacktest(
        await request<Backtest>("/api/forecast/backtest", {
          model_id: result.model_id,
        }),
      );
      setView("Backtest");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Backtest unavailable");
    }
  }
  const target = catalog.find((c) => c.series.series_id === series);
  const selectedPoint = result?.forecast_points.find(
    (p) => p.horizon === horizon,
  );
  const selectedMetric = result?.leaderboard.find(
    (r) => r.horizon === horizon && r.selected,
  );
  const historical =
    result?.as_of_time.slice(0, 10) !== new Date().toISOString().slice(0, 10);
  const points: ChartPoint[] =
    result?.history.map((p) => ({
      time: Date.parse(p.date + "T23:59:59Z"),
      actual: p.actual,
      median: undefined as number | undefined,
      band: undefined as number[] | undefined,
    })) ?? [];
  if (result && points.length) {
    points[points.length - 1].median = result.current_rate;
    points[points.length - 1].band = [result.current_rate, result.current_rate];
    for (const p of result.forecast_points)
      points.push({
        time: Date.parse(p.date + "T23:59:59Z"),
        actual: undefined,
        median: p.p50,
        band: [p.p10, p.p90],
      });
  }
  const backtestPoints: ChartPoint[] =
    backtest?.records
      .filter(
        (r) =>
          r.stage === "test" &&
          r.horizon === horizon &&
          r.model === result?.selected_models[String(horizon)],
      )
      .map((r) => ({
        ...r,
        time: Date.parse(r.target_date + "T23:59:59Z"),
        band:
          r.p10 !== undefined && r.p90 !== undefined
            ? [r.p10, r.p90]
            : undefined,
      })) ?? [];
  return (
    <>
      <section>
        <div className="section-heading">
          <h2>Forecast configuration</h2>
          <span>1 / 3 / 7 / 14 CALENDAR DAYS</span>
        </div>
        <fieldset disabled={busy}>
          <div className="market-fields">
            <label>
              Forecast series
              <select
                value={series}
                onChange={(e) => {
                  setSeries(e.target.value);
                  setContexts([]);
                  setAsOf(
                    catalog
                      .find((c) => c.series.series_id === e.target.value)
                      ?.end?.slice(0, 10) ?? "",
                  );
                }}
              >
                {catalog
                  .filter((c) => c.series.category === "FREIGHT")
                  .map((c) => (
                    <option value={c.series.series_id} key={c.series.series_id}>
                      {c.series.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Training as-of date / UTC end of day
              <input
                type="date"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
                max={new Date().toISOString().slice(0, 10)}
              />
            </label>
            <label>
              Inspect horizon
              <select
                value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
              >
                {[1, 3, 7, 14].map((h) => (
                  <option value={h} key={h}>
                    {h} days
                  </option>
                ))}
              </select>
            </label>
            <label>
              Data source
              <input
                readOnly
                value={target?.series.provenance.source_type ?? "UNAVAILABLE"}
              />
            </label>
          </div>
          <details>
            <summary>
              Optional market context ({contexts.length} selected)
            </summary>
            <div className="predictor-list">
              {catalog
                .filter((c) => c.series.series_id !== series)
                .map((c) => (
                  <label key={c.series.series_id}>
                    <input
                      type="checkbox"
                      checked={contexts.includes(c.series.series_id)}
                      onChange={(e) =>
                        setContexts(
                          e.target.checked
                            ? [...contexts, c.series.series_id]
                            : contexts.filter(
                                (id) => id !== c.series.series_id,
                              ),
                        )
                      }
                    />
                    {c.series.name}
                  </label>
                ))}
            </div>
          </details>
          <button
            className="primary"
            disabled={!series || !asOf || contexts.length > 8}
            onClick={train}
          >
            {busy ? "Training and evaluating..." : "Train & evaluate"}
          </button>
        </fieldset>
        <p className="muted">
          New training uses the configuration above; a displayed saved forecast
          retains its own as-of date and features. No random splits. Up to eight
          rolling origins per stage and horizon. Training may take a minute.
        </p>
      </section>
      {message && (
        <p role="status" className="muted">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {result && (
        <>
          <div className="forecast-notice">
            <strong>{result.evaluation_label}</strong>
            <span>
              {historical
                ? "Historical as-of experiment, not a forecast from today."
                : "Forecast from today."}{" "}
              As of {result.as_of_time}. {result.target.currency ?? ""}{" "}
              {result.target.unit}. Model {result.model_version}.
            </span>
          </div>
          <div className="market-tabs">
            <button
              className={view === "Forecast" ? "active" : ""}
              onClick={() => setView("Forecast")}
            >
              Forecast
            </button>
            <button
              className={view === "Backtest" ? "active" : ""}
              onClick={loadBacktest}
            >
              Out-of-sample backtest
            </button>
          </div>
          <section>
            <div className="section-heading">
              <h2>
                {view === "Forecast"
                  ? "Historical observations and forecast range"
                  : "Out-of-sample backtest / final test"}
              </h2>
              <span>
                {view === "Forecast"
                  ? "P10 / P50 / P90"
                  : `${horizon}-DAY / ${result.selected_models[String(horizon)]}`}
              </span>
            </div>
            <div className="forecast-chart">
              <ResponsiveContainer width="100%" height={340}>
                <ComposedChart
                  data={view === "Forecast" ? points : backtestPoints}
                  margin={{ top: 20, right: 30, left: 15, bottom: 10 }}
                >
                  <CartesianGrid stroke="#2b343c" vertical={false} />
                  <XAxis
                    dataKey="time"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    scale="time"
                    tickFormatter={(v) =>
                      new Date(v).toISOString().slice(0, 10)
                    }
                    tick={{ fill: "#8e9ba5", fontSize: 10 }}
                    minTickGap={65}
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fill: "#8e9ba5", fontSize: 10 }}
                  />
                  <Tooltip
                    labelFormatter={(v) =>
                      new Date(Number(v)).toISOString().slice(0, 10)
                    }
                    contentStyle={{
                      background: "#20282f",
                      border: "1px solid #42515d",
                      color: "#fff",
                    }}
                  />
                  <Legend />
                  <Area
                    type="linear"
                    dataKey="band"
                    name="P10-P90 range"
                    stroke="none"
                    fill="#84abaa"
                    fillOpacity={0.2}
                    isAnimationActive={false}
                  />
                  <Line
                    dataKey="actual"
                    name="Historical actual"
                    stroke="#c2cbd2"
                    dot={false}
                    strokeWidth={1.5}
                    isAnimationActive={false}
                  />
                  <Line
                    dataKey={view === "Forecast" ? "median" : "p50"}
                    name="P50 forecast"
                    stroke="#92c7c0"
                    strokeDasharray="5 3"
                    dot={{ r: 2 }}
                    isAnimationActive={false}
                  />
                  {view === "Forecast" && (
                    <ReferenceLine
                      x={Date.parse(result.as_of_time)}
                      stroke="#c7ac79"
                      label={{
                        value: historical ? "HISTORICAL AS OF" : "TODAY",
                        fill: "#c7ac79",
                        fontSize: 10,
                      }}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <p className="muted">
              Solid line: observations. Dashed line and shaded range: model
              output. Only selected horizons/origins are estimated; connecting
              segments guide the eye. P10-P90 has nominal 80% coverage, not a
              guarantee.
            </p>
          </section>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Current at origin</th>
                  <th>P50 / day {horizon}</th>
                  <th>P10-P90 / day {horizon}</th>
                  <th>Market regime</th>
                  <th>Uncertainty status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{fmt(result.current_rate)}</td>
                  <td>{fmt(selectedPoint?.p50)}</td>
                  <td>
                    {fmt(selectedPoint?.p10)} - {fmt(selectedPoint?.p90)}
                  </td>
                  <td>{result.market_regime}</td>
                  <td>{result.uncertainty_status}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <section>
            <div className="section-heading">
              <h2>Forecast by horizon</h2>
              <span>
                {result.target.currency ?? ""} {result.target.unit}
              </span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Horizon / date</th>
                  <th>Selected model</th>
                  <th>P10</th>
                  <th>P50</th>
                  <th>P90</th>
                  <th>Corrections</th>
                </tr>
              </thead>
              <tbody>
                {result.forecast_points.map((p) => (
                  <tr key={p.horizon}>
                    <th>
                      {p.horizon} days<small>{p.date}</small>
                    </th>
                    <td>{p.model_name}</td>
                    <td>{fmt(p.p10)}</td>
                    <td>{fmt(p.p50)}</td>
                    <td>{fmt(p.p90)}</td>
                    <td>
                      {p.quantile_crossing
                        ? "Crossing sorted"
                        : p.nonnegative_correction
                          ? "Clipped at zero"
                          : "None"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <div className="two-columns">
            <section>
              <div className="section-heading">
                <h2>What informs the forecast?</h2>
              </div>
              {result.explanation.map((text) => (
                <p className="muted" key={text}>
                  {text}
                </p>
              ))}
              {result.feature_importance?.[String(horizon)] && (
                <details>
                  <summary>
                    Tree-model feature associations (not causal)
                  </summary>
                  <p className="muted">
                    {result.feature_importance[String(horizon)].note}
                  </p>
                  {result.feature_importance[String(horizon)].features
                    .slice(0, 8)
                    .map((f) => (
                      <p className="muted" key={f.feature}>
                        {f.feature}: {f.importance.toFixed(4)}
                      </p>
                    ))}
                </details>
              )}
              {result.drivers.context.map((c) => (
                <p key={c.series_id} className="muted">
                  {c.series_id}:{" "}
                  {c.available
                    ? `current ${fmt(c.value ?? undefined)}; 7-day change ${fmt(c.change_7 ?? undefined)}`
                    : "Unavailable; no observed value fabricated."}
                </p>
              ))}
            </section>
            <section>
              <div className="section-heading">
                <h2>Reliability and limitations</h2>
              </div>
              {result.warnings.map((w) => (
                <p className="warning" key={w}>
                  {w}
                </p>
              ))}
              <p className="muted">{result.uncertainty_method}</p>
              <p className="muted">
                Feature associations are not causal explanations. Charter timing
                is coming in Batch 4.
              </p>
            </section>
          </div>
          <section>
            <div className="section-heading">
              <h2>Model performance</h2>
              <span>
                {result.evaluation_label} / {horizon} DAYS
              </span>
            </div>
            <p className="muted">{result.selection_reason}</p>
            <p className="muted">
              Final test: {result.periods.test.start} to{" "}
              {result.periods.test.end}. Selected model: {selectedMetric?.model}
              . Expected P10-P90 coverage: 80%; observed test coverage:{" "}
              {selectedMetric
                ? percent(selectedMetric.test.coverage)
                : "Unavailable"}{" "}
              over {selectedMetric?.test.count} origins.
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Validation MAE</th>
                    <th>Test MAE</th>
                    <th>Test RMSE</th>
                    <th>Test pinball</th>
                    <th>Direction</th>
                    <th>Coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {result.leaderboard
                    .filter((r) => r.horizon === horizon)
                    .map((r) => (
                      <tr
                        key={r.model}
                        className={r.selected ? "recommended" : ""}
                      >
                        <th>
                          {r.model}
                          {r.selected && <small>SELECTED ON VALIDATION</small>}
                        </th>
                        <td>{fmt(r.validation.mae)}</td>
                        <td>{fmt(r.test.mae)}</td>
                        <td>{fmt(r.test.rmse)}</td>
                        <td>{fmt(r.test.mean_pinball)}</td>
                        <td>{percent(r.test.directional_accuracy)}</td>
                        <td>{percent(r.test.coverage)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
            <p className="muted">
              Direction uses rise/fall/unchanged relative to each origin. Test
              scores are descriptive holdout results and do not alter model
              selection. Small overlapping samples do not establish real-world
              accuracy.
            </p>
          </section>
          <details className="provenance">
            <summary>
              Model metadata, features and chronological periods
            </summary>
            <p className="muted">
              Model ID: {result.model_id}. Dataset: {result.dataset_id}. Trained
              through: {result.training_cutoff}.{" "}
              {result.dataset_summary.usable_rows} usable rows from{" "}
              {result.dataset_summary.start} to {result.dataset_summary.end}.
            </p>
            <table>
              <thead>
                <tr>
                  <th>Period</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Feature rows</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.periods).map(([key, p]) => (
                  <tr key={key}>
                    <th>{key}</th>
                    <td>{p.start}</td>
                    <td>{p.end}</td>
                    <td>{p.feature_rows}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted">Features: {result.features.join(", ")}</p>
            {result.limitations.map((l) => (
              <p className="muted" key={l}>
                {l}
              </p>
            ))}
          </details>
        </>
      )}
    </>
  );
}
