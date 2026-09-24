import { useEffect, useState } from "react";
import { request } from "../api/client";
import type { Shipment } from "../types";
import type { Snapshot } from "../types/market";
import type { FreightForecast } from "../types/forecast";
export function FreightOutlook({
  shipment,
  vesselClass,
  onOpen,
}: {
  shipment: Shipment;
  vesselClass: string;
  onOpen: () => void;
}) {
  const [result, setResult] = useState<FreightForecast | null>(null);
  const [message, setMessage] = useState("Loading saved outlook...");
  const { origin_port, destination_port, cargo_type } = shipment;
  useEffect(() => {
    let active = true;
    setResult(null);
    setMessage("Loading saved outlook...");
    const query = new URLSearchParams({
      origin: origin_port,
      destination: destination_port,
      vessel_class: vesselClass,
      cargo_type,
    });
    request<Snapshot>("/api/market/snapshot?" + query)
      .then(async (snapshot) => {
        const freight = snapshot.context.freight;
        if (!freight.available || !freight.series_id)
          throw new Error("No relevant freight market available.");
        return request<FreightForecast>(
          "/api/forecast/freight/" + freight.series_id,
        );
      })
      .then((r) => {
        if (active) {
          setResult(r);
          setMessage("");
        }
      })
      .catch(() => {
        if (active)
          setMessage(
            "Forecast unavailable. Train an eligible freight series in Freight forecast. No replacement forecast is fabricated.",
          );
      });
    return () => {
      active = false;
    };
  }, [origin_port, destination_port, cargo_type, vesselClass]);
  const day7 = result?.forecast_points.find((p) => p.horizon === 7);
  const day14 = result?.forecast_points.find((p) => p.horizon === 14);
  return (
    <section>
      <div className="section-heading">
        <h2>Freight outlook</h2>
        <button className="text-button" onClick={onOpen}>
          Open forecasts &rarr;
        </button>
      </div>
      {message && <p className="muted">{message}</p>}
      {result && (
        <>
          <p className="warning">
            {result.evaluation_label} / As of {result.as_of_time.slice(0, 10)} /{" "}
            {result.is_historical_as_of ? "HISTORICAL ORIGIN, NOT TODAY" : ""}
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Current historical value</th>
                  <th>7-day P50</th>
                  <th>7-day P10-P90</th>
                  <th>14-day P50</th>
                  <th>Uncertainty</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{result.current_rate.toFixed(2)}</td>
                  <td>{day7?.p50.toFixed(2) ?? "Unavailable"}</td>
                  <td>
                    {day7
                      ? `${day7.p10.toFixed(2)} - ${day7.p90.toFixed(2)}`
                      : "Unavailable"}
                  </td>
                  <td>{day14?.p50.toFixed(2) ?? "Unavailable"}</td>
                  <td>{result.uncertainty_status}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="muted">
            {result.target.name} / {result.target.currency ?? ""}{" "}
            {result.target.unit}. Direction:{" "}
            {day7
              ? day7.p50 > result.current_rate
                ? "rise"
                : day7.p50 < result.current_rate
                  ? "fall"
                  : "unchanged"
              : "unavailable"}{" "}
            relative to historical origin. No currency or voyage-cost
            conversion.
          </p>
        </>
      )}
      <p className="muted">
        Charter timing: coming in Batch 4. Forecast direction alone is not a
        charter recommendation.
      </p>
    </section>
  );
}
