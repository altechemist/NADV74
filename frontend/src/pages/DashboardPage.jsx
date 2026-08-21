// Authenticated shell: sidebar navigation, header with notifications and the
// section views (Overview, Requests, Sensors, People).
import { useEffect, useState } from "react";
import {
  Activity,
  Bell,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Plus,
  Users,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/csrms";
import { useAuth } from "../context/AuthContext";
import NewRequestModal from "../components/NewRequestModal";
import RequestDetail from "../components/RequestDetail";
import OverviewSection from "./sections/OverviewSection";
import RequestsSection from "./sections/RequestsSection";
import SensorsSection from "./sections/SensorsSection";
import PeopleSection from "./sections/PeopleSection";

const EMPTY_FILTERS = { status: "", priority: "", category: "" };

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [section, setSection] = useState("Overview");
  const [summary, setSummary] = useState(null);
  const [requests, setRequests] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [telemetry, setTelemetry] = useState({ network: [], water: [], fire: [] });
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showNewRequest, setShowNewRequest] = useState(false);
  const [openRequestId, setOpenRequestId] = useState(null);
  const [error, setError] = useState("");

  const isStaffUser = user.role === "STAFF" || user.role === "ADMIN";

  function loadCore() {
    // Dashboard counts and the request list refresh together because every
    // mutation in the detail drawer can affect both.
    api
      .dashboard()
      .then(setSummary)
      .catch((reason) => setError(reason.message));

    const query = new URLSearchParams(
      Object.entries(filters).filter(([, value]) => value !== "")
    ).toString();
    api
      .requests(query)
      .then(setRequests)
      .catch((reason) => setError(reason.message));
  }

  useEffect(() => {
    loadCore();
    api.categories().then(setCategories).catch(() => {});
    api.notifications().then(setNotifications).catch(() => {});
    if (isStaffUser) {
      api.telemetryHistory("live").then(setTelemetry).catch(() => {});
    }
  }, [filters]);

  async function signOut() {
    await logout();
    navigate("/login", { replace: true });
  }

  const unreadCount = notifications.filter((item) => !item.is_read).length;

  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[252px] flex-col bg-deep text-white lg:flex">
        <div className="border-b border-white/10 px-7 py-6">
          <div className="font-serif text-xl tracking-tight">CSRMS</div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-[#b9c8c8]">
            Campus service desk
          </div>
        </div>

        <nav className="space-y-1 px-5 py-6">
          <NavItem icon={LayoutDashboard} label="Overview" active={section === "Overview"} onClick={() => setSection("Overview")} />
          <NavItem icon={ClipboardList} label="Requests" active={section === "Requests"} onClick={() => setSection("Requests")} />
          {isStaffUser && (
            <NavItem icon={Activity} label="Sensors" active={section === "Sensors"} onClick={() => setSection("Sensors")} />
          )}
          {user.role === "ADMIN" && (
            <NavItem icon={Users} label="People" active={section === "People"} onClick={() => setSection("People")} />
          )}
        </nav>

        <div className="mt-auto border-t border-white/10 p-5">
          <div className="flex items-center gap-3 rounded-2xl bg-white/10 p-3">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-accent font-semibold text-deep">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold">{user.first_name || user.username}</div>
              <div className="text-xs text-[#a9b9b8]">{user.role}</div>
            </div>
            <button onClick={signOut} title="Sign out" className="rounded-lg p-2 hover:bg-white/10">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main column */}
      <main className="lg:pl-[252px]">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-line bg-paper/95 px-5 backdrop-blur sm:px-8">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#9a7950]">
              Sol Plaatje University · {user.role} workspace
            </div>
            <div className="font-serif text-xl leading-tight">
              Hello, {user.first_name || user.username}.
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowNewRequest(true)}
              className="hidden items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-deep hover:brightness-105 sm:flex"
            >
              <Plus className="h-4 w-4" /> Log a request
            </button>

            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="grid h-10 w-10 place-items-center rounded-xl border border-line bg-card text-[#45616a] hover:bg-white"
              >
                <Bell className="h-4 w-4" />
                {unreadCount > 0 && (
                  <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-[#d16848]" />
                )}
              </button>

              {showNotifications && (
                <div className="absolute right-0 top-12 z-40 w-80 overflow-hidden rounded-2xl border border-line bg-card shadow-xl">
                  <div className="border-b border-line/60 px-4 py-3 signal-label">Notifications</div>
                  <div className="max-h-80 overflow-y-auto">
                    {notifications.length === 0 && (
                      <p className="px-4 py-4 text-sm text-muted">Nothing yet.</p>
                    )}
                    {notifications.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => {
                          setShowNotifications(false);
                          if (item.request) setOpenRequestId(item.request);
                        }}
                        className={`block w-full border-b border-line/40 px-4 py-3 text-left last:border-0 hover:bg-white ${
                          item.is_read ? "" : "bg-[#fff8ec]"
                        }`}
                      >
                        <div className="text-sm font-semibold">{item.title}</div>
                        <div className="text-xs text-muted">{item.message}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-[1480px] px-5 py-7 sm:px-8 lg:px-12">
          {error && (
            <div className="mb-5 rounded-xl bg-[#fce7df] px-4 py-3 text-xs text-[#a5452d]">
              {error} — is the Django server running?
            </div>
          )}

          {section === "Overview" && (
            <OverviewSection
              user={user}
              summary={summary}
              requests={requests}
              telemetry={telemetry}
              onOpenRequest={(request) => setOpenRequestId(request.id)}
            />
          )}

          {section === "Requests" && (
            <RequestsSection
              requests={requests}
              categories={categories}
              filters={filters}
              onFiltersChange={setFilters}
              onOpenRequest={(request) => setOpenRequestId(request.id)}
              onNewRequest={() => setShowNewRequest(true)}
            />
          )}

          {section === "Sensors" && isStaffUser && <SensorsSection />}

          {section === "People" && user.role === "ADMIN" && (
            <PeopleSection
              categories={categories}
              onCategoriesChanged={() => api.categories().then(setCategories)}
            />
          )}
        </div>
      </main>

      {showNewRequest && (
        <NewRequestModal
          categories={categories}
          onClose={() => setShowNewRequest(false)}
          onCreated={() => {
            setShowNewRequest(false);
            loadCore();
          }}
        />
      )}

      {openRequestId && (
        <RequestDetail
          requestId={openRequestId}
          onClose={() => setOpenRequestId(null)}
          onChanged={loadCore}
        />
      )}
    </div>
  );
}

function NavItem({ icon: Icon, label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${
        active ? "bg-accent font-semibold text-deep" : "text-[#d1dada] hover:bg-white/10"
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}
