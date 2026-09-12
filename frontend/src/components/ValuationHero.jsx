import { formatEUR, formatPct } from "../lib/format";

export default function ValuationHero({ player, baseline, scenario, labelSource, loading }) {
  const active = scenario ?? baseline;
  const predicted = active?.predicted_value_eur;
  const actual = baseline?.actual_value_eur;
  const gapPct = actual ? ((baseline.predicted_value_eur - actual) / actual) * 100 : null;
  const scenarioPct = scenario
    ? ((scenario.predicted_value_eur - baseline.predicted_value_eur) / baseline.predicted_value_eur) * 100
    : null;
  const verdict = gapPct == null ? null : Math.abs(gapPct) < 10 ? "Fairly valued" : gapPct > 0 ? "Stats suggest higher" : "Stats suggest lower";

  return (
    <section aria-live="polite" className="card-dark p-6 sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-canvas-soft">Predicted market value</p>
        {scenario && <span className="badge bg-primary text-ink">What-if scenario</span>}
      </div>

      <p className={`tabular mt-2 text-6xl font-black leading-none tracking-tight text-primary sm:text-7xl ${loading ? "opacity-50" : ""}`}>
        {predicted != null ? formatEUR(predicted) : "—"}
      </p>
      <p className="mt-3 text-base text-canvas-soft">
        {player ? (
          <>
            <span className="font-semibold text-canvas">{player.name}</span> · {player.team}
          </>
        ) : (
          "Select a player to value"
        )}
      </p>
      {scenario && (
        <p className="mt-1 text-sm text-mute">
          Baseline {formatEUR(baseline.predicted_value_eur)} →{" "}
          <span className="font-semibold text-primary">{formatPct(scenarioPct, 1)}</span> with edited stats
        </p>
      )}

      <dl className="mt-6 grid grid-cols-2 gap-3">
        <div className="rounded-2xl bg-ink-raised p-4">
          <dt className="text-xs font-semibold text-mute">Label value</dt>
          <dd className="tabular mt-1 text-3xl font-black tracking-tight text-canvas">{formatEUR(actual)}</dd>
        </div>
        <div className="rounded-2xl bg-ink-raised p-4">
          <dt className="text-xs font-semibold text-mute">Model vs label</dt>
          <dd className="tabular mt-1 text-3xl font-black tracking-tight text-canvas">{formatPct(gapPct)}</dd>
          {verdict && (
            <dd className={`badge mt-2 ${Math.abs(gapPct) < 10 ? "bg-canvas-soft text-ink" : gapPct > 0 ? "bg-primary text-ink" : "bg-negative text-canvas"}`}>
              {verdict}
            </dd>
          )}
        </div>
      </dl>

      {labelSource === "synthetic" && (
        <p className="mt-4 rounded-2xl bg-warning px-4 py-3 text-sm text-warning-content">
          <strong>Placeholder values.</strong> API-Football has no valuation data, so labels are synthetic. Add{" "}
          <code className="font-semibold">backend/data/market_values.csv</code> and retrain for real market values.
        </p>
      )}
    </section>
  );
}
