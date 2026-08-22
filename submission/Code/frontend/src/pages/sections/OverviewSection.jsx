// Landing view: headline stats, the newest requests and a sensor snapshot.
import { ClipboardList, Check, Zap, Activity, CloudRain, Flame, Wifi } from "lucide-react";
import Badge from "../../components/Badge";
import { categoryName, timeAgo } from "../../lib/format";

export default function OverviewSection({ user, summary, requests, telemetry, onOpenRequest }) {
  const isStudent = user.role === "STUDENT";
  const cards = [
    { label: "Open requests", value: (summary?.pending ?? 0) + (summary?.assigned ?? 0), icon: ClipboardList },
    { label: "In progress", value: summary?.in_progress ?? 0, icon: Zap },
    { label: "Resolved", value: summary?.resolved ?? 0, icon: Check },
    {
      label: isStudent ? "My total" : "Live sensors",
      value: isStudent ? requests.length : "3",
      icon: Activity,
    },
  ];

  const latest = latestReadings(telemetry);

  return (
    <>
      <section className="relative overflow-hidden rounded-3xl bg-teal p-8 text-white sm:p-10">
        <div className="max-w-xl">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#f0c477]">
            <span className="h-px w-8 bg-[#f0c477]" />
            {isStudent ? "Your service brief" : "Operational brief"}
          </div>
          <h1 className="mt-4 font-serif text-4xl leading-tight">
            {isStudent ? (
              <>Track your campus requests.</>
            ) : (
              <>
                Keep the campus <span className="text-[#f0c477]">in rhythm.</span>
              </>
            )}
          </h1>
          <p className="mt-4 text-sm leading-6 text-[#c5d2d0]">
            {isStudent
              ? "Log a problem once and follow every step the service desk takes."
              : "Assign, progress and resolve what the campus reports — plus anything the sensors pick up first."}
          </p>
        </div>
        <div className="absolute -bottom-20 right-10 hidden h-52 w-52 rounded-full border border-[#f0c477]/20 lg:block" />
      </section>

      <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-2xl border border-line bg-card p-5">
            <div className="flex items-start justify-between">
              <div className="signal-label">{label}</div>
              <Icon className="h-4 w-4 text-[#a16312]" />
            </div>
            <div className="mt-3 font-serif text-4xl text-teal">{value}</div>
          </div>
        ))}
      </section>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <section>
          <div className="mb-3 flex items-end justify-between">
            <h2 className="font-serif text-2xl text-teal">Latest requests</h2>
          </div>
          <div className="overflow-hidden rounded-2xl border border-line bg-card">
            {requests.slice(0, 5).map((request) => (
              <button
                key={request.id}
                onClick={() => onOpenRequest(request)}
                className="flex w-full items-center gap-4 border-b border-line/60 p-4 text-left last:border-0 hover:bg-white"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-semibold tracking-[0.12em] text-[#9a7950]">
                      {request.reference}
                    </span>
                    <Badge value={request.priority} />
                  </div>
                  <div className="mt-1 truncate text-sm font-semibold">{request.title}</div>
                  <div className="mt-0.5 text-xs text-muted">
                    {categoryName(request.category)} · {timeAgo(request.created_at)}
                  </div>
                </div>
                <Badge value={request.status} />
              </button>
            ))}
            {requests.length === 0 && (
              <p className="p-6 text-sm text-muted">Nothing logged yet — your queue is clear.</p>
            )}
          </div>
        </section>

        {!isStudent && (
          <section>
            <div className="mb-3 flex items-end justify-between">
              <h2 className="font-serif text-2xl text-teal">System signals</h2>
            </div>
            <div className="space-y-3">
              <SensorRow
                icon={Wifi}
                label="Network monitor"
                detail={latest.network ? `Gateway latency ${latest.network} ms` : "Awaiting readings"}
              />
              <SensorRow
                icon={CloudRain}
                label="Water leak sensor"
                detail={latest.water ? `Moisture ${latest.water}%` : "Awaiting readings"}
              />
              <SensorRow
                icon={Flame}
                label="Fire & smoke sensor"
                detail={
                  latest.fire
                    ? `${latest.fire.smoke} smoke · ${latest.fire.temperature} °C`
                    : "Awaiting readings"
                }
              />
            </div>
          </section>
        )}
      </div>
    </>
  );
}

function SensorRow({ icon: Icon, label, detail }) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-line bg-card p-4">
      <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#e7eff5] text-[#3d6da5]">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold">{label}</div>
        <div className="truncate text-xs text-muted">{detail}</div>
      </div>
    </div>
  );
}

function latestReadings(telemetry) {
  const last = (list) => (list.length ? list[list.length - 1] : null);
  const network = last(telemetry.network);
  const water = last(telemetry.water);
  const fire = last(telemetry.fire);
  return {
    network: network ? network.value : null,
    water: water ? water.value : null,
    fire: fire ? { smoke: fire.value, temperature: fire.secondary_value ?? "—" } : null,
  };
}
