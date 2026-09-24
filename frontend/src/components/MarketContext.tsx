import { useEffect, useState } from "react";
import { request } from "../api/client";
import type { Shipment } from "../types";
import type { Snapshot } from "../types/market";
export function MarketContext({
  shipment,
  vesselClass,
}: {
  shipment: Shipment;
  vesselClass: string;
}) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState("");
  const { origin_port, origin_country, destination_port, cargo_type } =
    shipment;
  useEffect(() => {
    let active = true;
    setSnapshot(null);
    setError("");
    const query = new URLSearchParams({
      origin: origin_port,
      origin_region: origin_country,
      destination: destination_port,
      vessel_class: vesselClass,
      cargo_type,
    });
    request<Snapshot>("/api/market/snapshot?" + query)
      .then((data) => {
        if (active) setSnapshot(data);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [origin_port, origin_country, destination_port, cargo_type, vesselClass]);
  return (
    <section>
      <div className="section-heading">
        <h2>Market context</h2>
        <span>HISTORICAL / SOURCE-LABELLED</span>
      </div>
      <p className="muted">
        Context only. Voyage costs retain the Batch 1 reference assumptions.
        Singapore is a representative fuel hub; commodity benchmarks are
        proxies.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!snapshot && !error && <p role="status">Loading market context...</p>}
      {snapshot && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Category / series</th>
                <th>Latest known value</th>
                <th>Source / provenance</th>
                <th>Observation / freshness</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(snapshot.context).map(([key, item]) => (
                <tr key={key}>
                  <th>
                    {key}
                    <small>{item.series_name ?? "UNAVAILABLE"}</small>
                  </th>
                  <td>
                    {item.available
                      ? `${item.value?.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${item.currency ?? ""} / ${item.unit}`
                      : "Unavailable"}
                  </td>
                  <td>
                    {item.provenance?.source_type ?? "SOURCE NOT CONNECTED"}
                    <small>{item.source?.name ?? item.reason}</small>
                  </td>
                  <td>
                    {item.timestamp?.slice(0, 10) ?? "-"}
                    <small
                      className={
                        item.freshness?.status === "STALE" ? "warning" : ""
                      }
                    >
                      {item.freshness
                        ? `${item.freshness.status} / ${item.freshness.age_days} days old`
                        : "No matching observation"}
                    </small>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
