// Telemetry charts for staff and admins, fed by /telemetry/history/.
import { useEffect, useState } from "react";
import { api } from "../../api/csrms";
import { FireChart, SensorChart } from "../../components/charts";
import { clockTime } from "../../lib/format";

const RANGES = [
  ["live", "Live (12 h)"],
  ["24_hours", "24 hours"],
  ["7_days", "7 days"],
];

// Thresholds mirror the backend settings; they only guide the drawn lines.
const THRESHOLDS = {
  network: 100,
  water: 60,
  smoke: 40,
  temperature: 50,
};

export default function SensorsSection() {
  const [range, setRange] = useState("live");
  const [series, setSeries] = useState({ network: [], water: [], fire: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .telemetryHistory(range)
      .then((payload) => {
        if (!active) return;
        setSeries({
          network: payload.network.map(toPoint((reading) => reading.value)),
          water: payload.water.map(toPoint((reading) => reading.value)),
          fire: payload.fire.map(toFirePoint),
        });
        setError("");
      })
      .catch((reason) => active && setError(reason.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [range]);

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="signal-label">Telemetry service</div>
          <h1 className="mt-2 font-serif text-4xl text-teal">Sensor activity</h1>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Readings posted by the three campus sensors. When a threshold is crossed the backend
            raises a request on its own.
          </p>
        </div>
        <div className="flex rounded-xl border border-line bg-card p-1">
          {RANGES.map(([key, label]) => (
            <button
              key={key}
              onClick={() => setRange(key)}
              className={`rounded-lg px-3 py-2 text-xs font-semibold ${
                range === key ? "bg-deep text-white" : "text-muted"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-xl bg-[#fce7df] px-4 py-3 text-xs text-[#a5452d]">{error}</div>
      )}
      {loading && <p className="mt-4 text-sm text-muted">Loading readings…</p>}

      <div className="mt-6 grid gap-5 xl:grid-cols-2">
        <SensorChart
          title="Network monitor"
          subtitle="Gateway latency in milliseconds"
          data={series.network}
          color="#3d6da5"
          unit="ms"
          threshold={THRESHOLDS.network}
        />
        <SensorChart
          title="Water leak sensor"
          subtitle="Moisture percentage near pipes"
          data={series.water}
          color="#39704c"
          unit="%"
          threshold={THRESHOLDS.water}
        />
        <div className="xl:col-span-2">
          <FireChart
            data={series.fire}
            smokeThreshold={THRESHOLDS.smoke}
            temperatureThreshold={THRESHOLDS.temperature}
          />
        </div>
      </div>
    </section>
  );
}

function toPoint(pick) {
  return (reading) => ({
    time: clockTime(reading.timestamp),
    value: Number(pick(reading)),
  });
}

function toFirePoint(reading) {
  return {
    time: clockTime(reading.timestamp),
    smoke: Number(reading.value),
    temperature: Number(reading.secondary_value ?? 0),
  };
}
