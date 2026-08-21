import { useState } from "react";
import { api } from "../api/csrms";
import Modal from "./Modal";

// Form used by students (and staff) to log a new request.
export default function NewRequestModal({ categories, onClose, onCreated }) {
  const [form, setForm] = useState({
    title: "",
    description: "",
    location: "",
    priority: "MEDIUM",
  });
  const [categoryId, setCategoryId] = useState(categories[0]?.id ?? "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function updateForm(field) {
    return (event) => setForm({ ...form, [field]: event.target.value });
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await api.createRequest({
        ...form,
        category_id: Number(categoryId),
      });
      onCreated(created);
    } catch (reason) {
      setError(reason.message || "The request could not be saved.");
      setBusy(false);
    }
  }

  return (
    <Modal kicker="Manual report" title="Log a request" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Title">
          <input
            required
            value={form.title}
            onChange={updateForm("title")}
            placeholder="What needs attention?"
            className={inputClass}
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Category">
            <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)} className={inputClass}>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Priority">
            <select value={form.priority} onChange={updateForm("priority")} className={inputClass}>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </Field>
        </div>

        <Field label="Location">
          <input
            required
            value={form.location}
            onChange={updateForm("location")}
            placeholder="Building and room"
            className={inputClass}
          />
        </Field>

        <Field label="Description">
          <textarea
            required
            rows={4}
            value={form.description}
            onChange={updateForm("description")}
            placeholder="Describe the problem"
            className="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm outline-none focus:border-accent"
          />
        </Field>

        {error && (
          <div className="rounded-xl bg-[#fce7df] px-3 py-2 text-xs text-[#a5452d]">{error}</div>
        )}

        <button
          disabled={busy}
          className="w-full rounded-xl bg-deep px-4 py-3 text-sm font-semibold text-white hover:bg-teal disabled:opacity-60"
        >
          {busy ? "Saving…" : "Submit request"}
        </button>
      </form>
    </Modal>
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
