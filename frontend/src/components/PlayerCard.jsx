import { useState } from "react";
import { POSITION_SHORT, formatEUR, formatNumber, formatSeason, initials } from "../lib/format";

function Avatar({ player }) {
  const [broken, setBroken] = useState(false);
  if (player.photo && !broken) {
    return (
      <img
        src={player.photo}
        alt=""
        onError={() => setBroken(true)}
        className="size-16 shrink-0 rounded-2xl bg-canvas-soft object-cover"
      />
    );
  }
  return (
    <div className="grid size-16 shrink-0 place-items-center rounded-2xl bg-primary text-xl font-black text-ink">
      {initials(player.name)}
    </div>
  );
}

function StatTile({ label, value, sub }) {
  return (
    <div className="min-w-0 rounded-2xl bg-canvas-soft px-3 py-3">
      <p className="truncate text-xs font-semibold text-body">{label}</p>
      <p className="tabular mt-0.5 text-2xl font-black tracking-tight">{value}</p>
      {sub && <p className="truncate text-[11px] text-body">{sub}</p>}
    </div>
  );
}

export default function PlayerCard({ player, loading }) {
  if (!player) {
    return (
      <div className="card animate-pulse">
        <div className="flex gap-4">
          <div className="size-16 rounded-2xl bg-canvas-soft" />
          <div className="flex-1 space-y-2 py-1">
            <div className="h-5 w-2/3 rounded-full bg-canvas-soft" />
            <div className="h-4 w-1/3 rounded-full bg-canvas-soft" />
          </div>
        </div>
        <div className="mt-5 grid grid-cols-3 gap-2">
          {Array.from({ length: 6 }, (_, i) => <div key={i} className="h-[74px] rounded-2xl bg-canvas-soft" />)}
        </div>
      </div>
    );
  }

  const { stats, career } = player;
  const per90 = stats.minutes > 0 ? ((stats.goals + stats.assists) / stats.minutes) * 90 : 0;

  return (
    <article className={`card transition-opacity ${loading ? "opacity-60" : ""}`}>
      <div className="flex items-center gap-4">
        <Avatar player={player} />
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-2xl font-black tracking-tight">{player.name}</h2>
          <p className="truncate text-sm text-body">
            {player.team}
            {player.nationality && ` · ${player.nationality}`}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <span className="badge badge-brand">{player.position}</span>
            <span className="badge badge-neutral">{formatSeason(player.season)}</span>
          </div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-2">
        <StatTile label="Goals" value={stats.goals} />
        <StatTile label="Assists" value={stats.assists} />
        <StatTile label="G+A / 90" value={per90.toFixed(2)} />
        <StatTile label="Minutes" value={formatNumber(stats.minutes)} sub={`${player.appearances} apps`} />
        <StatTile label="Age" value={stats.age} />
        <StatTile label="Position" value={POSITION_SHORT[stats.position]} />
      </div>

      <p className="mt-4 text-sm text-body">
        In dataset: <strong className="text-ink">{career.seasons_played}</strong> season(s) ·{" "}
        <strong className="text-ink">{career.career_goals}</strong> G ·{" "}
        <strong className="text-ink">{career.career_assists}</strong> A ·{" "}
        <strong className="text-ink">{formatNumber(career.career_minutes)}</strong> min
      </p>

      {player.history.length > 1 && (
        <div className="mt-4 overflow-x-auto rounded-2xl ring-1 ring-canvas-soft">
          <table className="tabular w-full text-left text-sm">
            <thead className="bg-canvas-soft text-xs text-body">
              <tr>
                <th className="px-3 py-2 font-semibold">Season · club</th>
                <th className="px-3 py-2 text-right font-semibold">Min</th>
                <th className="px-3 py-2 text-right font-semibold">G</th>
                <th className="px-3 py-2 text-right font-semibold">A</th>
                <th className="px-3 py-2 text-right font-semibold">Value</th>
              </tr>
            </thead>
            <tbody>
              {player.history.map((row) => (
                <tr key={row.season} className="border-t border-canvas-soft">
                  <td className="max-w-0 px-3 py-2" title={row.team}>
                    <p className="font-semibold">{formatSeason(row.season)}</p>
                    <p className="truncate text-xs text-body">{row.team}</p>
                  </td>
                  <td className="px-3 py-2 text-right">{formatNumber(row.minutes)}</td>
                  <td className="px-3 py-2 text-right">{row.goals}</td>
                  <td className="px-3 py-2 text-right">{row.assists}</td>
                  <td className="px-3 py-2 text-right font-semibold">{formatEUR(row.market_value_eur)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}
