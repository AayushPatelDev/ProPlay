import { useState } from "react";
import { api } from "../api/client";
import { formatPct } from "../lib/format";

const PLOTS = [
  { file: "actual_vs_predicted.png", label: "Actual vs predicted" },
  { file: "residuals.png", label: "Residuals" },
  { file: "coefficients.png", label: "Feature effects" },
];

export default function DiagnosticsPlots({ metrics }) {
  const [tab, setTab] = useState(PLOTS[0].file);
  if (!metrics) return null;

  const maxEffect = Math.max(...metrics.coefficients.map((c) => Math.abs(c.effect_pct)), 1);

  return (
    <section className="card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="card-title">Model diagnostics</h3>
          <p className="card-subtitle">matplotlib + seaborn plots from the last training run</p>
        </div>
        <div className="flex flex-wrap gap-1.5" role="tablist">
          {PLOTS.map((plot) => (
            <button
              key={plot.file}
              role="tab"
              aria-selected={tab === plot.file}
              onClick={() => setTab(plot.file)}
              className={`chip ${tab === plot.file ? "chip-on" : "chip-off"}`}
            >
              {plot.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="overflow-hidden rounded-2xl ring-1 ring-canvas-soft">
          <img
            src={api.plotUrl(tab, metrics.trained_at)}
            alt={PLOTS.find((p) => p.file === tab).label}
            className="mx-auto max-h-[460px] w-auto"
          />
        </div>

        <div className="card-sage">
          <p className="card-title">What drives value</p>
          <p className="card-subtitle">% change in value per +1 std · positions vs Goalkeeper</p>
          <ul className="mt-4 space-y-3">
            {[...metrics.coefficients]
              .sort((a, b) => Math.abs(b.effect_pct) - Math.abs(a.effect_pct))
              .map((c) => {
                const positive = c.effect_pct >= 0;
                return (
                  <li key={c.feature}>
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{c.feature.replace("position_", "").replaceAll("_", " ")}</span>
                      <span className={`tabular font-bold ${positive ? "text-positive-deep" : "text-negative-deep"}`}>
                        {formatPct(c.effect_pct)}
                      </span>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-canvas">
                      <div
                        className={`h-full rounded-full ${positive ? "bg-ink" : "bg-negative"}`}
                        style={{ width: `${(Math.abs(c.effect_pct) / maxEffect) * 100}%` }}
                      />
                    </div>
                  </li>
                );
              })}
          </ul>
        </div>
      </div>
    </section>
  );
}
