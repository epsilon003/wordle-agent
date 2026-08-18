import { useEffect, useState } from "react";
import { GuessesOverTime, GuessDistribution } from "./Charts";
import type { WordleRun } from "./types";

function computeStreak(runs: WordleRun[]): number {
  const sorted = [...runs].sort((a, b) => b.puzzle_date.localeCompare(a.puzzle_date));
  let streak = 0;
  for (const r of sorted) {
    if (r.solved) streak++;
    else break;
  }
  return streak;
}

// Calendar days since the agent last needed a human to step in. Uses the
// most recent *failed* run as the reference point (a failed run is our
// best proxy for "something needed fixing" - DOM break, timeout, etc.);
// if there's never been a failure, counts from the very first recorded
// run instead, so a brand-new project doesn't show an undefined/infinite
// streak.
function computeDaysSinceLastFailure(runs: WordleRun[]): number {
  if (runs.length === 0) return 0;
  const sorted = [...runs].sort((a, b) => b.puzzle_date.localeCompare(a.puzzle_date));
  const lastFailure = sorted.find((r) => !r.solved);
  const referenceDate = lastFailure ? lastFailure.puzzle_date : sorted[sorted.length - 1].puzzle_date;

  const ref = new Date(referenceDate + "T00:00:00Z");
  const now = new Date();
  const todayUTC = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  return Math.max(0, Math.round((todayUTC.getTime() - ref.getTime()) / 86_400_000));
}

export default function App() {
  const [runs, setRuns] = useState<WordleRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/runs")
      .then((r) => r.json())
      .then((data) => {
        if (data.error) setError(data.error);
        else setRuns(data.runs ?? []);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const total = runs.length;
  const solved = runs.filter((r) => r.solved);
  const winRate = total ? Math.round((solved.length / total) * 100) : 0;
  const avgGuesses = solved.length
    ? (solved.reduce((s, r) => s + r.num_attempts, 0) / solved.length).toFixed(2)
    : "-";
  const streak = computeStreak(runs);
  const daysSinceLastFailure = computeDaysSinceLastFailure(runs);

  return (
    <main>
      <h1>Wordle Agent Dashboard</h1>
      <p className="subtitle">
        {loading ? "Loading..." : error ? `Error loading data: ${error}` : `${total} recorded runs`}
      </p>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{streak}</div>
          <div className="stat-label">Current streak</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{winRate}%</div>
          <div className="stat-label">Win rate</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{avgGuesses}</div>
          <div className="stat-label">Avg. guesses (solved)</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{total}</div>
          <div className="stat-label">Total runs</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{daysSinceLastFailure}</div>
          <div className="stat-label">Days since last failure</div>
        </div>
      </div>

      <div className="card">
        <h2>Guesses over time</h2>
        <GuessesOverTime runs={runs} />
      </div>

      <div className="card">
        <h2>Guess distribution</h2>
        <GuessDistribution runs={runs} />
      </div>

      <div className="card">
        <h2>Recent runs</h2>
        <table>
          <thead>
            <tr>
              <th>Date</th><th>Word</th><th>Attempts</th><th>Result</th><th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {runs.slice(0, 30).map((r) => (
              <tr key={r.id}>
                <td>{r.puzzle_date}</td>
                <td>{r.word ?? "—"}</td>
                <td>{r.num_attempts}</td>
                <td>
                  <span className={`pill ${r.solved ? "pill-solved" : "pill-failed"}`}>
                    {r.solved ? "Solved" : "Failed"}
                  </span>
                </td>
                <td>{r.duration_seconds ? `${r.duration_seconds.toFixed(0)}s` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
