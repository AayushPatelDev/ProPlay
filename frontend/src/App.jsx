import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import { BASE_FEATURES } from "./lib/format";
import { useDebouncedValue } from "./lib/useDebouncedValue";
import Header from "./components/Header";
import StatusBanner from "./components/StatusBanner";
import PlayerSearch from "./components/PlayerSearch";
import PlayerCard from "./components/PlayerCard";
import ValuationHero from "./components/ValuationHero";
import WhatIfPanel from "./components/WhatIfPanel";
import MetricsStrip from "./components/MetricsStrip";
import ValueScatter from "./components/ValueScatter";
import DiagnosticsPlots from "./components/DiagnosticsPlots";

const statsDiffer = (a, b) => BASE_FEATURES.some((key) => a[key] !== b[key]);

export default function App() {
  const [metrics, setMetrics] = useState(null);
  const [points, setPoints] = useState([]);
  const [bootError, setBootError] = useState(null);

  const [player, setPlayer] = useState(null);
  const [inputs, setInputs] = useState(null); // { playerId, ...editable stats }
  const [baseline, setBaseline] = useState(null); // prediction for the player's real stats
  const [scenario, setScenario] = useState(null); // prediction for edited stats
  const [loadingPlayer, setLoadingPlayer] = useState(false);
  const [error, setError] = useState(null);

  const selectPlayer = useCallback(async (id) => {
    setLoadingPlayer(true);
    setError(null);
    try {
      const [detail, prediction] = await Promise.all([api.getPlayer(id), api.predict({ player_id: id })]);
      setPlayer(detail);
      setInputs({ playerId: detail.id, ...detail.stats });
      setBaseline(prediction);
      setScenario(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingPlayer(false);
    }
  }, []);

  useEffect(() => {
    Promise.all([api.metrics(), api.evaluation()])
      .then(([metricsData, evaluation]) => {
        setMetrics(metricsData);
        setPoints(evaluation.points);
        // Open on the most valuable player of the latest season.
        const latest = Math.max(...evaluation.points.map((p) => p.season));
        const top = evaluation.points
          .filter((p) => p.season === latest)
          .reduce((best, p) => (!best || p.actual > best.actual ? p : best), null);
        if (top) selectPlayer(top.player_id);
      })
      .catch((err) => setBootError(err.message));
  }, [selectPlayer]);

  // What-if: re-predict when the edited stats settle.
  const debouncedInputs = useDebouncedValue(inputs, 250);
  useEffect(() => {
    if (!player || !debouncedInputs || debouncedInputs.playerId !== player.id) return;
    if (!statsDiffer(debouncedInputs, player.stats)) {
      setScenario(null);
      return;
    }
    const controller = new AbortController();
    const { playerId, ...stats } = debouncedInputs;
    api
      .predict({ player_id: playerId, ...stats }, controller.signal)
      .then(setScenario)
      .catch((err) => err.name !== "AbortError" && setError(err.message));
    return () => controller.abort();
  }, [debouncedInputs, player]);

  const isDirty = Boolean(player && inputs && statsDiffer(inputs, player.stats));

  return (
    <div className="min-h-screen">
      <Header metrics={metrics} />

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:py-8">
        {bootError && <StatusBanner message={bootError} />}
        {error && !bootError && <StatusBanner message={error} compact onDismiss={() => setError(null)} />}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <div className="space-y-6">
            <PlayerSearch onSelect={selectPlayer} disabled={Boolean(bootError)} />
            <PlayerCard player={player} loading={loadingPlayer} />
            {player && inputs && (
              <WhatIfPanel
                player={player}
                inputs={inputs}
                dirty={isDirty}
                onChange={(patch) => setInputs((prev) => ({ ...prev, ...patch }))}
                onReset={() => setInputs({ playerId: player.id, ...player.stats })}
              />
            )}
          </div>

          <div className="space-y-6">
            <ValuationHero
              player={player}
              baseline={baseline}
              scenario={isDirty ? scenario : null}
              labelSource={metrics?.label_source}
              loading={loadingPlayer}
            />
            <MetricsStrip metrics={metrics} />
            <ValueScatter
              points={points}
              baseline={baseline}
              scenario={isDirty ? scenario : null}
              onSelectPlayer={selectPlayer}
            />
          </div>
        </div>

        <DiagnosticsPlots metrics={metrics} />
      </main>

      <footer className="mt-6 bg-ink text-canvas-soft">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-8 text-sm sm:px-6">
          <p>
            <span className="font-black text-primary">ProPlay</span> · Statistics via API-Football v3
          </p>
          <p className="text-mute">Linear Regression (scikit-learn) on log market value</p>
        </div>
      </footer>
    </div>
  );
}
