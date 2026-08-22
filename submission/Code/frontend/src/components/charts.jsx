// Recharts wrappers for the sensor pages.
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const tooltipStyle = {
  contentStyle: { background: "#102a35", border: "0", borderRadius: 10, fontSize: 12 },
  itemStyle: { color: "#f0c477" },
  labelStyle: { color: "#c5d2d0" },
};

const axisProps = {
  tickLine: false,
  axisLine: false,
  tick: { fill: "#98a19e", fontSize: 10 },
};

export function SensorChart({ title, subtitle, data, color, unit, threshold }) {
  const latest = data.length ? data[data.length - 1].value : null;
  return (
    <div className="rounded-2xl border border-line bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-teal">{title}</div>
          <div className="mt-1 text-xs text-muted">{subtitle}</div>
        </div>
        <span className="rounded-full bg-[#e7f0e8] px-2.5 py-1 text-[10px] font-semibold text-[#39704c]">
          Live
        </span>
      </div>

      <div className="mt-4 h-[190px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 6, left: -24, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#e8e2d9" strokeDasharray="3 3" />
            <ReferenceLine
              y={threshold}
              stroke="#b66c28"
              strokeDasharray="4 4"
              label={{ value: "alert threshold", fill: "#b66c28", fontSize: 9, position: "insideTopRight" }}
            />
            <XAxis dataKey="time" {...axisProps} />
            <YAxis width={34} {...axisProps} />
            <Tooltip {...tooltipStyle} formatter={(value) => [`${value} ${unit}`, title]} />
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2.5}
              fill={color}
              fillOpacity={0.12}
              dot={{ r: 2.5, fill: color, strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 flex items-center justify-between border-t border-line/60 pt-3 text-[10px] uppercase tracking-[0.12em] text-muted">
        <span>Recorded readings</span>
        <span className="font-semibold" style={{ color }}>
          {latest !== null ? `${latest} ${unit}` : "No data yet"}
        </span>
      </div>
    </div>
  );
}

export function FireChart({ data, smokeThreshold, temperatureThreshold }) {
  return (
    <div className="rounded-2xl border border-line bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-teal">Fire &amp; smoke sensor</div>
          <div className="mt-1 text-xs text-muted">Smoke concentration and temperature</div>
        </div>
        <span className="rounded-full bg-[#f8eadb] px-2.5 py-1 text-[10px] font-semibold text-[#a45b29]">
          Watched
        </span>
      </div>

      <div className="mt-4 h-[190px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 6, left: -24, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#e8e2d9" strokeDasharray="3 3" />
            <ReferenceLine y={smokeThreshold} stroke="#b24d36" strokeDasharray="4 4" />
            <ReferenceLine y={temperatureThreshold} stroke="#e6a649" strokeDasharray="4 4" yAxisId="right" />
            <XAxis dataKey="time" {...axisProps} />
            <YAxis width={34} {...axisProps} />
            <YAxis orientation="right" width={30} yAxisId="right" {...axisProps} />
            <Tooltip {...tooltipStyle} />
            <Line
              type="monotone"
              dataKey="smoke"
              name="Smoke"
              stroke="#b24d36"
              strokeWidth={2.5}
              dot={{ r: 2.5, fill: "#b24d36", strokeWidth: 0 }}
            />
            <Line
              type="monotone"
              dataKey="temperature"
              name="Temp °C"
              stroke="#e6a649"
              strokeWidth={2.5}
              yAxisId="right"
              dot={{ r: 2.5, fill: "#e6a649", strokeWidth: 0 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
