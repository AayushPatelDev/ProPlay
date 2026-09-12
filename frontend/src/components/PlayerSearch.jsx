import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api/client";
import { POSITION_SHORT, formatSeason } from "../lib/format";
import { useDebouncedValue } from "../lib/useDebouncedValue";

export default function PlayerSearch({ onSelect, disabled }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState([]);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const listId = useId();
  const debouncedQuery = useDebouncedValue(query, 180);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setLoading(true);
    api
      .searchPlayers(debouncedQuery, 12, controller.signal)
      .then((data) => {
        setResults(data.players);
        setActive(0);
      })
      .catch(() => {})
      .finally(() => !controller.signal.aborted && setLoading(false));
    return () => controller.abort();
  }, [debouncedQuery, open]);

  const choose = (player) => {
    onSelect(player.id);
    setQuery("");
    setOpen(false);
    inputRef.current?.blur();
  };

  const onKeyDown = (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter" && open && results[active]) {
      event.preventDefault();
      choose(results[active]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="card relative">
      <label htmlFor={`${listId}-input`} className="card-title mb-3 block">
        Find a player
      </label>
      <div className="relative">
        <svg className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-ink" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" strokeLinecap="round" />
        </svg>
        <input
          id={`${listId}-input`}
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={open && results[active] ? `${listId}-${results[active].id}` : undefined}
          disabled={disabled}
          value={query}
          placeholder="Search by name, e.g. Saka"
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
          className="input pl-12 pr-11"
        />
        {loading && (
          <span className="absolute right-4 top-1/2 size-4 -translate-y-1/2 animate-spin rounded-full border-2 border-canvas-soft border-t-ink" />
        )}
      </div>

      {open && (
        <ul
          id={listId}
          role="listbox"
          onMouseDown={(e) => e.preventDefault()} // keep focus so the click lands before blur
          className="absolute inset-x-6 z-20 mt-2 max-h-80 overflow-auto rounded-2xl bg-canvas p-2 shadow-[0_12px_32px_-8px_rgba(14,15,12,0.25)] ring-1 ring-ink/10"
        >
          {results.length === 0 && !loading && (
            <li className="px-3 py-3 text-sm text-body">No players match “{query}”.</li>
          )}
          {results.map((player, index) => (
            <li
              key={player.id}
              id={`${listId}-${player.id}`}
              role="option"
              aria-selected={index === active}
              onMouseEnter={() => setActive(index)}
              onClick={() => choose(player)}
              className={`flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 ${index === active ? "bg-canvas-soft" : ""}`}
            >
              {player.photo ? (
                <img src={player.photo} alt="" className="size-9 shrink-0 rounded-full bg-canvas-soft object-cover" />
              ) : (
                <span className="size-9 shrink-0 rounded-full bg-canvas-soft" />
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{player.name}</p>
                <p className="truncate text-xs text-body">
                  {player.team} · {formatSeason(player.season)}
                </p>
              </div>
              <span className="badge badge-neutral shrink-0">{POSITION_SHORT[player.position]}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
