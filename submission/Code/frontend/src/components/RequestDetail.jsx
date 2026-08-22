// Slide-in panel showing one request, its full history timeline and the
// actions available to the current user (assign / status / comment / cancel).
import { useEffect, useState } from "react";
import { Check, X } from "lucide-react";
import { api } from "../api/csrms";
import { useAuth } from "../context/AuthContext";
import Badge from "./Badge";
import { categoryName, fullName, timeAgo } from "../lib/format";

const NEXT_STATUSES = {
  PENDING: ["ASSIGNED"],
  ASSIGNED: ["IN_PROGRESS", "PENDING"],
  IN_PROGRESS: ["RESOLVED"],
  RESOLVED: [],
  CANCELLED: [],
};

export default function RequestDetail({ requestId, onClose, onChanged }) {
  const { user } = useAuth();
  const [detail, setDetail] = useState(null);
  const [history, setHistory] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isStaffUser = user.role === "STAFF" || user.role === "ADMIN";
  const isOwner = detail?.created_by?.id === user.id;

  useEffect(() => {
    let active = true;
    setError("");

    api
      .requestDetail(requestId)
      .then((data) => active && setDetail(data))
      .catch((reason) => active && setError(reason.message));

    api
      .history(requestId)
      .then((data) => active && setHistory(data))
      .catch(() => {});

    // Staff pick a colleague from the assignable-accounts directory.
    if (isStaffUser) {
      api
        .staffDirectory()
        .then((users) => {
          if (!active) return;
          setStaffList(users);
        })
        .catch(() => {});
    }

    return () => {
      active = false;
    };
  }, [requestId]);

  async function run(action) {
    setBusy(true);
    setError("");
    try {
      await action();
      const [fresh, timeline] = await Promise.all([api.requestDetail(requestId), api.history(requestId)]);
      setDetail(fresh);
      setHistory(timeline);
      onChanged?.();
    } catch (reason) {
      setError(reason.message || "That did not work.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-deep/40 backdrop-blur-sm" onClick={onClose}>
      <aside
        className="h-full w-full max-w-xl overflow-y-auto bg-card p-6 shadow-2xl sm:p-8"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9a7950]">
            Request detail
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-muted hover:bg-line/60">
            <X className="h-5 w-5" />
          </button>
        </div>

        {!detail && !error && <p className="mt-10 text-sm text-muted">Loading…</p>}
        {error && (
          <div className="mt-8 rounded-xl bg-[#fce7df] px-4 py-3 text-xs text-[#a5452d]">{error}</div>
        )}

        {detail && (
          <>
            <div className="mt-6">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-semibold tracking-[0.12em] text-[#9a7950]">
                  {detail.reference}
                </span>
                <Badge value={detail.priority} />
                <Badge value={detail.status} />
              </div>
              <h2 className="mt-3 font-serif text-3xl leading-tight text-teal">{detail.title}</h2>
              <p className="mt-2 text-sm text-muted">
                {categoryName(detail.category)} · {detail.location} · logged by{" "}
                {detail.source === "SYSTEM" ? "the telemetry service" : fullName(detail.created_by)} ·{" "}
                {timeAgo(detail.created_at)}
              </p>
              <p className="mt-4 rounded-2xl bg-paper p-4 text-sm leading-6">{detail.description}</p>
            </div>

            {/* Staff controls */}
            {isStaffUser && detail.status !== "CANCELLED" && detail.status !== "RESOLVED" && (
              <section className="mt-7 rounded-2xl border border-line bg-white p-4">
                <div className="signal-label">Service desk actions</div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {(NEXT_STATUSES[detail.status] || []).map((next) => (
                    <button
                      key={next}
                      disabled={busy}
                      onClick={() => run(() => api.setStatus(detail.id, next))}
                      className="rounded-xl bg-deep px-3 py-2 text-xs font-semibold text-white hover:bg-teal disabled:opacity-50"
                    >
                      Mark {next === "IN_PROGRESS" ? "in progress" : next.toLowerCase()}
                    </button>
                  ))}
                  {detail.status === "ASSIGNED" && (
                    <button
                      disabled={busy}
                      onClick={() => run(() => api.setStatus(detail.id, "PENDING"))}
                      className="rounded-xl border border-line px-3 py-2 text-xs font-semibold text-muted"
                    >
                      Back to pending
                    </button>
                  )}
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <select
                    defaultValue=""
                    disabled={busy}
                    onChange={(event) => {
                      const target = Number(event.target.value);
                      if (target) run(() => api.assign(detail.id, target));
                    }}
                    className="h-10 flex-1 rounded-xl border border-line bg-card px-3 text-sm outline-none focus:border-accent"
                  >
                    <option value="">
                      {detail.assigned_to ? `Reassign (now ${fullName(detail.assigned_to)})` : "Assign to…"}
                    </option>
                    {staffList.map((member) => (
                      <option key={member.id} value={member.id}>
                        {fullName(member)} ({member.role})
                      </option>
                    ))}
                  </select>
                </div>
              </section>
            )}

            {/* Owner cancel */}
            {isOwner && !isStaffUser && !["RESOLVED", "CANCELLED"].includes(detail.status) && (
              <button
                disabled={busy}
                onClick={() => run(() => api.cancelRequest(detail.id))}
                className="mt-5 w-full rounded-xl border border-[#e9c9bb] bg-[#fce7df] px-4 py-3 text-sm font-semibold text-[#a5452d] disabled:opacity-50"
              >
                Cancel this request
              </button>
            )}

            {/* Comment box */}
            <form
              className="mt-5"
              onSubmit={(event) => {
                event.preventDefault();
                if (!comment.trim()) return;
                run(async () => {
                  await api.addComment(detail.id, comment.trim());
                  setComment("");
                });
              }}
            >
              <textarea
                rows={2}
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                placeholder="Add a note to the timeline…"
                className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm outline-none focus:border-accent"
              />
              <button
                disabled={busy || !comment.trim()}
                className="mt-2 rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-deep disabled:opacity-50"
              >
                Post note
              </button>
            </form>

            {/* Timeline */}
            <section className="mt-8">
              <div className="signal-label">Workflow history</div>
              <ol className="mt-4 space-y-4">
                {history.map((entry) => (
                  <li key={entry.id} className="flex gap-3">
                    <span
                      className={`mt-1 grid h-6 w-6 shrink-0 place-items-center rounded-full ${
                        entry.entry_type === "COMMENT"
                          ? "bg-[#e7effc] text-[#315b96]"
                          : "bg-[#e3f0e5] text-[#39704c]"
                      }`}
                    >
                      <Check className="h-3.5 w-3.5" />
                    </span>
                    <div>
                      <div className="text-sm font-semibold text-teal">{describeEntry(entry)}</div>
                      <div className="text-xs text-muted">
                        {entry.changed_by ? `by ${fullName(entry.changed_by)} · ` : ""}
                        {new Date(entry.created_at).toLocaleString()}
                      </div>
                      {entry.comment && <p className="mt-1 text-sm">{entry.comment}</p>}
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          </>
        )}
      </aside>
    </div>
  );
}

function describeEntry(entry) {
  switch (entry.entry_type) {
    case "CREATED":
      return "Request created";
    case "STATUS":
      return `Status: ${entry.from_status || "—"} → ${entry.to_status}`;
    case "ASSIGN":
      return "Assigned to a staff member";
    case "COMMENT":
      return "Note added";
    default:
      return entry.entry_type;
  }
}
