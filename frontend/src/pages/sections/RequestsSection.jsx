// Full request list with server-side filters and client-side search.
import { useMemo, useState } from "react";
import { ChevronDown, Plus, Search } from "lucide-react";
import Badge from "../../components/Badge";
import { categoryName, fullName, timeAgo } from "../../lib/format";

export default function RequestsSection({
  requests,
  categories,
  filters,
  onFiltersChange,
  onOpenRequest,
  onNewRequest,
}) {
  const [search, setSearch] = useState("");

  // Text search happens locally; the dropdowns re-query the API.
  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return requests;
    return requests.filter((request) =>
      `${request.title} ${categoryName(request.category)} ${request.location}`
        .toLowerCase()
        .includes(needle)
    );
  }, [requests, search]);

  function setFilter(field) {
    return (event) => onFiltersChange({ ...filters, [field]: event.target.value });
  }

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="signal-label">Service pipeline</div>
          <h1 className="mt-2 font-serif text-4xl text-teal">Requests</h1>
        </div>
        <button
          onClick={onNewRequest}
          className="inline-flex items-center gap-2 rounded-xl bg-deep px-4 py-3 text-sm font-semibold text-white hover:bg-teal"
        >
          <Plus className="h-4 w-4" /> Log a request
        </button>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <div className="relative min-w-[240px] flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search title, category or location"
            className="h-10 w-full rounded-xl border border-line bg-card pl-10 pr-3 text-sm outline-none focus:border-accent"
          />
        </div>

        <FilterSelect label="All statuses" value={filters.status} onChange={setFilter("status")}
          options={[
            ["PENDING", "Pending"],
            ["ASSIGNED", "Assigned"],
            ["IN_PROGRESS", "In progress"],
            ["RESOLVED", "Resolved"],
            ["CANCELLED", "Cancelled"],
          ]}
        />
        <FilterSelect label="All priorities" value={filters.priority} onChange={setFilter("priority")}
          options={[
            ["LOW", "Low"],
            ["MEDIUM", "Medium"],
            ["HIGH", "High"],
            ["CRITICAL", "Critical"],
          ]}
        />
        <FilterSelect label="All categories" value={filters.category} onChange={setFilter("category")}
          options={categories.map((category) => [String(category.id), category.name])}
        />
      </div>

      <div className="mt-5 overflow-hidden rounded-2xl border border-line bg-card">
        {visible.map((request) => (
          <button
            key={request.id}
            onClick={() => onOpenRequest(request)}
            className="flex w-full flex-wrap items-center gap-3 border-b border-line/60 p-4 text-left last:border-0 hover:bg-white sm:gap-4"
          >
            <div className="min-w-[200px] flex-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-semibold tracking-[0.12em] text-[#9a7950]">
                  {request.reference}
                </span>
                <Badge value={request.priority} />
              </div>
              <div className="mt-1 truncate text-sm font-semibold">{request.title}</div>
              <div className="mt-0.5 truncate text-xs text-muted">
                {categoryName(request.category)} · {request.location}
              </div>
            </div>
            <div className="hidden w-32 text-xs text-muted md:block">
              {request.source === "SYSTEM" ? "Sensor report" : fullName(request.created_by)}
            </div>
            <div className="hidden w-24 text-xs text-muted lg:block">{timeAgo(request.created_at)}</div>
            <Badge value={request.status} />
            <ChevronDown className="h-4 w-4 -rotate-90 text-muted" />
          </button>
        ))}
        {visible.length === 0 && (
          <p className="p-6 text-sm text-muted">No requests match the current filters.</p>
        )}
      </div>
    </section>
  );
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={onChange}
      className="h-10 rounded-xl border border-line bg-card px-3 text-sm text-[#587078] outline-none focus:border-accent"
    >
      <option value="">{label}</option>
      {options.map(([key, text]) => (
        <option key={key} value={key}>
          {text}
        </option>
      ))}
    </select>
  );
}
