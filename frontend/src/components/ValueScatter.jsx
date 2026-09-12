import { useMemo, useState } from "react";
import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { POSITIONS, POSITION_SHORT, formatEUR, formatSeason } from "../lib/format";

const COLORS = { point: "#163300", lime: "#9fe870", ink: "#0e0f0c", body: "#454745", grid: "#eef0ec", mute: "#868685" };

function logTicks(lo, hi) {
  const ticks = [];
  for (let exp = Math.floor(Math.log10(lo)); exp <= Math.ceil(Math.log10(hi)); exp++) {
    for (const m of [1, 3]) {
      const t = m * 10 ** exp;
      if (t >= lo && t <= hi) ticks.push(t);
    }
  }
  return ticks;
}

function PointTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const errorPct = ((p.predicted - p.actual) / p.actual) * 100;
  return (
    <div className="rounded-2xl bg-ink px-4 py-3 text-xs text-canvas-soft shadow-xl">
      <p className="text-sm font-semibold text-canvas">{p.name}</p>
      {p.team && (
        <p>
          {p.team} · {formatSeason(p.season)} · {POSITION_SHORT[p.position]}
        </p>
      )}
      <div className="tabular mt-2 grid grid-cols-2 gap-x-4 gap-y-0.5">
        <span>Actual</span>
        <span className="text-right font-semibold text-canvas">{formatEUR(p.actual)}</span>
        <span>Predicted</span>
        <span className="text-right font-semibold text-primary">{formatEUR(p.predicted)}</span>
        <span>Error</span>
        <span className="text-right font-semibold text-canvas">
          {errorPct > 0 ? "+" : ""}
          {errorPct.toFixed(0)}%
        </span>
      </div>
      {!p.highlight && <p className="mt-2 text-[10px] text-mute">Click to open player</p>}
    </div>
  );
}

function HighlightDot({ cx, cy }) {
  if (cx == null || cy == null) return null;
  return (
    <g>
      <circle cx={cx} cy={cy} r={15} fill={COLORS.lime} opacity={0.45} />
      <circle cx={cx} cy={cy} r={7.5} fill={COLORS.lime} stroke={COLORS.ink} strokeWidth={2.5} />
    </g>
  );
}

export default function ValueScatter({ points, baseline, scenario, onSelectPlayer }) {
  const [position, setPosition] = useState("All");

  const data = useMemo(
    () => points.filter((p) => p.actual > 0 && p.predicted > 0 && (position === "All" || p.position === position)),
    [points, position],
  );

  const [lo, hi] = useMemo(() => {
    const values = points.flatMap((p) => [p.actual, p.predicted]).filter((v) => v > 0);
    if (!values.length) return [1e5, 1e8];
    return [Math.min(...values) * 0.8, Math.max(...values) * 1.25];
  }, [points]);

  const highlight =
    baseline?.player && baseline.actual_value_eur
      ? [{
          ...baseline.player,
          actual: baseline.actual_value_eur,
          predicted: (scenario ?? baseline).predicted_value_eur,
          highlight: true,
        }]
      : [];

  const axisProps = {
    type: "number",
    scale: "log",
    domain: [lo, hi],
    ticks: logTicks(lo, hi),
    tickFormatter: formatEUR,
    allowDataOverflow: true,
    tick: { fill: COLORS.body, fontSize: 12 },
    tickLine: false,
    axisLine: { stroke: "#e8ebe6" },
  };

  return (
    <section className="card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="card-title">Actual vs predicted</h3>
          <p className="card-subtitle">
            {data.length} player-seasons, out-of-fold. Above the line means over-predicted.
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by position">
          {["All", ...POSITIONS].map((p) => (
            <button
              key={p}
              onClick={() => setPosition(p)}
              aria-pressed={position === p}
              className={`chip ${position === p ? "chip-on" : "chip-off"}`}
            >
              {p === "All" ? "All" : POSITION_SHORT[p]}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 h-[380px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 12, bottom: 24, left: 4 }}>
            <CartesianGrid stroke={COLORS.grid} />
            <XAxis
              {...axisProps}
              dataKey="actual"
              name="Actual"
              label={{ value: "Actual (label) value", position: "insideBottom", offset: -14, fill: COLORS.body, fontSize: 12 }}
            />
            <YAxis
              {...axisProps}
              dataKey="predicted"
              name="Predicted"
              width={58}
              label={{ value: "Predicted", angle: -90, position: "insideLeft", offset: 10, fill: COLORS.body, fontSize: 12 }}
            />
            <ZAxis range={[30, 30]} />
            <ReferenceLine segment={[{ x: lo, y: lo }, { x: hi, y: hi }]} stroke={COLORS.mute} strokeDasharray="6 5" />
            <Tooltip content={<PointTooltip />} cursor={{ strokeDasharray: "3 3", stroke: COLORS.mute }} />
            <Scatter
              data={data}
              fill={COLORS.point}
              fillOpacity={0.28}
              isAnimationActive={false}
              className="cursor-pointer"
              onClick={(entry) => {
                const id = entry?.payload?.player_id ?? entry?.player_id;
                if (id != null) onSelectPlayer(id);
              }}
            />
            <Scatter data={highlight} shape={<HighlightDot />} isAnimationActive={false} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {highlight.length > 0 && (
        <p className="mt-1 flex items-center gap-2 text-sm text-body">
          <span className="inline-block size-3.5 rounded-full border-2 border-ink bg-primary" />
          <span className="font-semibold text-ink">{highlight[0].name}</span>
          {scenario ? "what-if" : "current model"}
        </p>
      )}
    </section>
  );
}
