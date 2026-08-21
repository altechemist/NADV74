// Bare-bones modal dialog: dark backdrop, card body, close on backdrop click.
import { X } from "lucide-react";

export default function Modal({ title, kicker, onClose, children, wide = false }) {
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-deep/55 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className={`max-h-[92vh] w-full overflow-y-auto rounded-3xl bg-card p-6 shadow-2xl sm:p-8 ${
          wide ? "max-w-2xl" : "max-w-lg"
        }`}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            {kicker && <div className="signal-label">{kicker}</div>}
            <h2 className="mt-2 font-serif text-3xl text-teal">{title}</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-muted hover:bg-line/60"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}
