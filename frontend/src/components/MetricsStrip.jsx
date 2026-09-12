import { formatEUR } from "../lib/format";

function Metric({ label, value, sub, hint }) {
  return (
    <div className="card p-5" title={hint}>
      <p className="text-sm font-semibold text-body">{label}</p>
      <p className="tabular mt-1 text-3xl font-black tracking-tight">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-body">{sub}</p>}
    </div>
  );
}

export default function MetricsStrip({ metrics }) {
  if (!metrics) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => <div key={i} className="card h-[108px] animate-pulse" />)}
      </div>
    );
  }
  const { test, cv } = metrics;
  return (
    <section aria-label="Model evaluation" className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Metric
        label="R² · test"
        value={test.r2.toFixed(3)}
        sub={`${cv.folds}-fold CV ${cv.r2.toFixed(3)}`}
        hint="Share of variance in market value (EUR) explained on held-out players"
      />
      <Metric
        label="R² · log scale"
        value={test.r2_log.toFixed(3)}
        sub="scale the model fits"
        hint="R² on log(value) — less dominated by a few very expensive players"
      />
      <Metric label="MAE" value={formatEUR(test.mae)} sub="mean absolute error" hint="Average absolute error on held-out players" />
      <Metric
        label="RMSE"
        value={formatEUR(test.rmse)}
        sub={`${metrics.n_test} test of ${metrics.n_rows}`}
        hint="Root mean squared error — penalises large misses"
      />
    </section>
  );
}
