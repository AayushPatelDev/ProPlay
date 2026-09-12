import { formatSeason } from "../lib/format";

export default function Header({ metrics }) {
  const seasons = metrics?.seasons ?? [];
  return (
    <header className="sticky top-0 z-30 bg-canvas/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-primary text-ink">
            <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
              <path d="M3 17l5-5 4 4 8-9" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M15 7h5v5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="leading-tight">
            <p className="text-xl font-black tracking-tight">ProPlay</p>
            <p className="text-xs text-body">EPL market value predictor</p>
          </div>
        </div>

        {metrics && (
          <div className="flex flex-wrap items-center gap-2">
            <span className={`badge ${metrics.data_source === "mock" ? "badge-warning" : "badge-positive"}`}>
              <span className={`size-1.5 rounded-full ${metrics.data_source === "mock" ? "bg-warning-content" : "bg-positive"}`} />
              {metrics.data_source === "mock" ? "Mock data" : "Live · API-Football"}
            </span>
            <span className={`badge ${metrics.label_source === "synthetic" ? "badge-warning" : "badge-neutral"}`}>
              Labels: {metrics.label_source}
            </span>
            {seasons.length > 0 && (
              <span className="badge badge-neutral">
                {seasons.length === 1
                  ? formatSeason(seasons[0])
                  : `${formatSeason(seasons[0])} – ${formatSeason(seasons[seasons.length - 1])}`}
              </span>
            )}
            <span className="badge badge-neutral">{metrics.n_players} players</span>
          </div>
        )}
      </div>
    </header>
  );
}
