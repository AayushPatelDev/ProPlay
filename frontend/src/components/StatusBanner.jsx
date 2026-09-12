export default function StatusBanner({ message, compact = false, onDismiss }) {
  return (
    <div role="alert" className="card flex items-start justify-between gap-4 border-l-8 border-negative">
      <div className="min-w-0">
        <p className="font-semibold text-negative-deep">{compact ? "Something went wrong" : "Can't reach the model"}</p>
        <p className="mt-1 text-sm text-body">{message}</p>
        {!compact && (
          <pre className="mt-4 overflow-x-auto rounded-2xl bg-ink px-4 py-3 text-xs leading-relaxed text-primary">
{`cd ~/Desktop/ProPlay/backend
source .venv/bin/activate
python -m app.fetch_data   # or --mock
python -m app.train
uvicorn app.main:app --reload --port 8000`}
          </pre>
        )}
      </div>
      {onDismiss && (
        <button onClick={onDismiss} className="btn btn-secondary btn-sm" aria-label="Dismiss">
          Dismiss
        </button>
      )}
    </div>
  );
}
