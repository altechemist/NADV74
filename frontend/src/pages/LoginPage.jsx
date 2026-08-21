import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Sign-in and sign-up share one screen; new accounts are always students.
export default function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    username: "",
    password: "",
    email: "",
    first_name: "",
    last_name: "",
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
      if (mode === "login") {
        await login(form.username, form.password);
      } else {
        await register(form);
      }
      navigate("/", { replace: true });
    } catch (reason) {
      setError(reason.message || "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-paper p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="font-serif text-3xl tracking-tight text-deep">CSRMS</div>
          <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-muted">
            Campus service request management
          </div>
        </div>

        <form onSubmit={submit} className="rounded-3xl bg-card p-7 shadow-xl sm:p-9">
          <div className="signal-label">{mode === "login" ? "Welcome back" : "Create your account"}</div>
          <h1 className="mt-2 font-serif text-2xl text-teal">
            {mode === "login" ? "Sign in to the service desk" : "Register as a student"}
          </h1>

          <div className="mt-6 space-y-4">
            <Field label="Username">
              <input
                required
                value={form.username}
                onChange={update("username")}
                autoComplete="username"
                className={inputClass}
              />
            </Field>

            {mode === "register" && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="First name">
                    <input value={form.first_name} onChange={update("first_name")} className={inputClass} />
                  </Field>
                  <Field label="Last name">
                    <input value={form.last_name} onChange={update("last_name")} className={inputClass} />
                  </Field>
                </div>
                <Field label="Email">
                  <input type="email" value={form.email} onChange={update("email")} className={inputClass} />
                </Field>
              </>
            )}

            <Field label="Password">
              <input
                required
                type="password"
                value={form.password}
                onChange={update("password")}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                className={inputClass}
              />
            </Field>
          </div>

          {error && (
            <div className="mt-4 rounded-xl bg-[#fce7df] px-3 py-2 text-xs text-[#a5452d]">{error}</div>
          )}

          <button
            disabled={busy}
            className="mt-6 w-full rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-deep transition hover:brightness-105 disabled:opacity-60"
          >
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>

          <p className="mt-5 text-center text-xs text-muted">
            {mode === "login" ? "New student on campus?" : "Already registered?"}{" "}
            <button
              type="button"
              className="font-semibold text-[#a16312] hover:underline"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError("");
              }}
            >
              {mode === "login" ? "Create an account" : "Sign in instead"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}

const inputClass =
  "mt-2 h-11 w-full rounded-xl border border-line bg-white px-3 text-sm outline-none focus:border-accent";

function Field({ label, children }) {
  return (
    <label className="block text-xs font-semibold text-[#52696f]">
      {label}
      {children}
    </label>
  );
}
