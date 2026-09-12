import { POSITIONS, POSITION_SHORT, formatNumber } from "../lib/format";

function Slider({ label, name, value, original, min, max, step = 1, format = (v) => v, onChange }) {
  const changed = value !== original;
  const fill = `${((value - min) / (max - min)) * 100}%`;
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between text-sm">
        <label htmlFor={`whatif-${name}`} className="font-semibold">
          {label}
        </label>
        <span className="tabular">
          {changed && <span className="mr-2 text-xs text-mute line-through">{format(original)}</span>}
          <span className={`rounded-full px-2 py-0.5 font-bold ${changed ? "bg-primary" : ""}`}>{format(value)}</span>
        </span>
      </div>
      <input
        id={`whatif-${name}`}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        style={{ "--fill": fill }}
        onChange={(e) => onChange({ [name]: Number(e.target.value) })}
        className="range"
      />
    </div>
  );
}

export default function WhatIfPanel({ player, inputs, dirty, onChange, onReset }) {
  const s = player.stats;
  return (
    <section className="card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="card-title">What-if simulator</h3>
          <p className="card-subtitle">Change the stats to see how the valuation moves.</p>
        </div>
        <button onClick={onReset} disabled={!dirty} className="btn btn-secondary btn-sm">
          Reset
        </button>
      </div>

      <div className="mt-6 space-y-5">
        <Slider label="Goals" name="goals" value={inputs.goals} original={s.goals} min={0} max={Math.max(40, s.goals)} onChange={onChange} />
        <Slider label="Assists" name="assists" value={inputs.assists} original={s.assists} min={0} max={Math.max(25, s.assists)} onChange={onChange} />
        <Slider label="Minutes" name="minutes" value={inputs.minutes} original={s.minutes} min={0} max={3420} step={10} format={formatNumber} onChange={onChange} />
        <Slider label="Age" name="age" value={inputs.age} original={s.age} min={16} max={40} onChange={onChange} />

        <div>
          <p className="mb-2 text-sm font-semibold">Position</p>
          <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Position">
            {POSITIONS.map((position) => {
              const selected = inputs.position === position;
              return (
                <button
                  key={position}
                  role="radio"
                  aria-checked={selected}
                  onClick={() => onChange({ position })}
                  className={`chip flex-1 ${selected ? "chip-on" : "chip-off"}`}
                >
                  {POSITION_SHORT[position]}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
