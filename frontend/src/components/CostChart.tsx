import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { Option } from "../types";
export function CostChart({ option }: { option: Option }) {
  const c = option.cost;
  const data = [
    { name: "Charter", usd: c.ocean_freight },
    { name: "Bunker", usd: c.bunker_component },
    { name: "Port", usd: c.port_cost },
    { name: "Demurrage", usd: c.expected_demurrage },
    { name: "Lighterage", usd: c.lighterage_if_applicable },
    { name: "Storage", usd: c.storage_if_applicable },
  ];
  return (
    <section>
      <div className="section-heading">
        <h2>Cost breakdown</h2>
        <span>DERIVED / USD / {option.vessel.name}</span>
      </div>
      <div className="cost-layout">
        <div
          className="chart"
          role="img"
          aria-label="Cost component bar chart; exact values in the adjacent table"
        >
          <ResponsiveContainer width="100%" height={230}>
            <BarChart
              data={data}
              layout="vertical"
              margin={{ left: 0, right: 25, top: 8, bottom: 0 }}
            >
              <CartesianGrid stroke="#2b343c" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fill: "#8e9ba5", fontSize: 11 }}
                tickFormatter={(v) => `${Number(v) / 1000}k`}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={88}
                tick={{ fill: "#bac4cc", fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "#20282f",
                  border: "1px solid #42515d",
                  color: "#fff",
                }}
                formatter={(v) => [
                  `USD ${Number(v).toLocaleString()}`,
                  "Estimate",
                ]}
              />
              <Bar dataKey="usd" fill="#80aaab" barSize={13} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <table className="cost-table">
          <tbody>
            {data.map((d) => (
              <tr key={d.name}>
                <th>{d.name}</th>
                <td>
                  {d.usd.toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </td>
              </tr>
            ))}
            <tr className="total">
              <th>Total USD</th>
              <td>
                {c.total_logistics_cost.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="muted">
        Charter excludes excess waiting charged as demurrage. Lighterage and
        storage are assumed zero; cargo purchase price is excluded.
      </p>
    </section>
  );
}
