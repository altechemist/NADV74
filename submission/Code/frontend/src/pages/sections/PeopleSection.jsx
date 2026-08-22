// Admin-only: manage accounts and service categories.
import { useEffect, useState } from "react";
import { api } from "../../api/csrms";

export default function PeopleSection({ categories, onCategoriesChanged }) {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [newCategory, setNewCategory] = useState("");

  function loadUsers() {
    api
      .users()
      .then(setUsers)
      .catch((reason) => setError(reason.message));
  }

  useEffect(loadUsers, []);

  async function deactivate(user) {
    try {
      await api.deactivateUser(user.id);
      loadUsers();
    } catch (reason) {
      setError(reason.message);
    }
  }

  async function addCategory(event) {
    event.preventDefault();
    if (!newCategory.trim()) return;
    try {
      await api.createCategory(newCategory.trim());
      setNewCategory("");
      onCategoriesChanged?.();
    } catch (reason) {
      setError(reason.message);
    }
  }

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="signal-label">Admin workspace</div>
          <h1 className="mt-2 font-serif text-4xl text-teal">People &amp; categories</h1>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-xl bg-deep px-4 py-3 text-sm font-semibold text-white hover:bg-teal"
        >
          {showForm ? "Close form" : "Add staff account"}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-xl bg-[#fce7df] px-4 py-3 text-xs text-[#a5452d]">{error}</div>
      )}

      {showForm && <StaffForm onDone={() => { setShowForm(false); loadUsers(); }} />}

      <div className="mt-6 overflow-hidden rounded-2xl border border-line bg-card">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line/60 text-[10px] uppercase tracking-[0.14em] text-muted">
              <th className="px-5 py-3">User</th>
              <th className="px-5 py-3">Email</th>
              <th className="px-5 py-3">Role</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b border-line/40 last:border-0">
                <td className="px-5 py-3 font-semibold">{user.username}</td>
                <td className="px-5 py-3 text-muted">{user.email || "—"}</td>
                <td className="px-5 py-3">{user.role}</td>
                <td className="px-5 py-3">
                  <span
                    className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${
                      user.is_active !== false
                        ? "bg-[#e3f0e5] text-[#39704c]"
                        : "bg-[#ece7e0] text-[#8a8175]"
                    }`}
                  >
                    {user.is_active !== false ? "Active" : "Deactivated"}
                  </span>
                </td>
                <td className="px-5 py-3 text-right">
                  {user.is_active !== false && user.role !== "ADMIN" && (
                    <button
                      onClick={() => deactivate(user)}
                      className="text-xs font-semibold text-[#a5452d] hover:underline"
                    >
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-8 rounded-2xl border border-line bg-card p-5">
        <div className="signal-label">Service vocabulary</div>
        <h2 className="mt-2 font-serif text-xl text-teal">Categories</h2>
        <form onSubmit={addCategory} className="mt-3 flex flex-wrap gap-2">
          <input
            value={newCategory}
            onChange={(event) => setNewCategory(event.target.value)}
            placeholder="New category name"
            className="h-10 flex-1 rounded-xl border border-line bg-white px-3 text-sm outline-none focus:border-accent"
          />
          <button className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-deep">
            Add category
          </button>
        </form>
        <div className="mt-4 flex flex-wrap gap-2">
          {categories.map((category) => (
            <span key={category.id} className="rounded-full bg-paper px-3 py-1 text-xs font-semibold text-teal">
              {category.name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function StaffForm({ onDone }) {
  const [form, setForm] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    role: "STAFF",
    password: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(field) {
    return (event) => setForm({ ...form, [field]: event.target.value });
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.createUser(form);
      onDone();
    } catch (reason) {
      // Surface field-level validation from the backend when present.
      const details = reason.details;
      const message =
        details && typeof details === "object"
          ? Object.entries(details)
              .map(([field, problem]) => `${field}: ${Array.isArray(problem) ? problem[0] : problem}`)
              .join(" · ")
          : reason.message;
      setError(message || "Could not create the account.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-6 grid gap-4 rounded-2xl border border-line bg-white p-5 sm:grid-cols-2">
      <Field label="Username">
        <input required value={form.username} onChange={update("username")} className={inputClass} />
      </Field>
      <Field label="Role">
        <select value={form.role} onChange={update("role")} className={inputClass}>
          <option value="STAFF">Staff</option>
          <option value="ADMIN">Admin</option>
        </select>
      </Field>
      <Field label="First name">
        <input value={form.first_name} onChange={update("first_name")} className={inputClass} />
      </Field>
      <Field label="Last name">
        <input value={form.last_name} onChange={update("last_name")} className={inputClass} />
      </Field>
      <Field label="Email">
        <input type="email" value={form.email} onChange={update("email")} className={inputClass} />
      </Field>
      <Field label="Temporary password">
        <input required type="password" value={form.password} onChange={update("password")} className={inputClass} />
      </Field>
      {error && (
        <div className="rounded-xl bg-[#fce7df] px-3 py-2 text-xs text-[#a5452d] sm:col-span-2">{error}</div>
      )}
      <button
        disabled={busy}
        className="rounded-xl bg-deep px-4 py-3 text-sm font-semibold text-white disabled:opacity-60 sm:col-span-2"
      >
        {busy ? "Creating…" : "Create account"}
      </button>
    </form>
  );
}

const inputClass =
  "mt-2 h-11 w-full rounded-xl border border-line bg-card px-3 text-sm outline-none focus:border-accent";

function Field({ label, children }) {
  return (
    <label className="block text-xs font-semibold text-[#52696f]">
      {label}
      {children}
    </label>
  );
}
