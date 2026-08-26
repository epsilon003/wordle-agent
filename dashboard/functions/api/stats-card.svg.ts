import { createClient } from "@supabase/supabase-js";

interface Env {
  SUPABASE_URL: string;
  SUPABASE_SERVICE_ROLE_KEY: string;
}

type Run = {
  puzzle_date: string;
  solved: boolean;
  num_attempts: number;
};

function computeStreak(runs: Run[]): number {
  const sorted = [...runs].sort((a, b) => b.puzzle_date.localeCompare(a.puzzle_date));
  let streak = 0;
  for (const r of sorted) {
    if (r.solved) streak++;
    else break;
  }
  return streak;
}

// Same definition as the dashboard's card: calendar days since the most
// recent failed run (or since the first recorded run, if there's never
// been a failure).
function computeDaysSinceLastFailure(runs: Run[]): number {
  if (runs.length === 0) return 0;
  const sorted = [...runs].sort((a, b) => b.puzzle_date.localeCompare(a.puzzle_date));
  const lastFailure = sorted.find((r) => !r.solved);
  const referenceDate = lastFailure ? lastFailure.puzzle_date : sorted[sorted.length - 1].puzzle_date;

  const ref = new Date(referenceDate + "T00:00:00Z");
  const now = new Date();
  const todayUTC = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  return Math.max(0, Math.round((todayUTC.getTime() - ref.getTime()) / 86_400_000));
}

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderCard(stats: {
  streak: number;
  winRate: string;
  avgGuesses: string;
  daysAutonomous: number;
  updated: string;
}): string {
  const { streak, winRate, avgGuesses, daysAutonomous, updated } = stats;
  return `<svg width="800" height="150" viewBox="0 0 800 150" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, sans-serif">
  <rect x="0.5" y="0.5" width="799" height="149" rx="10" fill="#0f1115" stroke="#262a33"/>
  <text x="24" y="32" font-size="15" font-weight="700" fill="#e7e9ea">Wordle Agent — Live Stats</text>
  <text x="24" y="49" font-size="11.5" fill="#8b8f96">Autonomous NYT Wordle solver, updated daily</text>
  <g text-anchor="middle">
    <text x="140" y="98" font-size="30" font-weight="700" fill="#4ade80">${streak}</text>
    <text x="140" y="118" font-size="11.5" fill="#8b8f96">Day streak</text>
    <text x="330" y="98" font-size="30" font-weight="700" fill="#4ade80">${escapeXml(winRate)}</text>
    <text x="330" y="118" font-size="11.5" fill="#8b8f96">Win rate</text>
    <text x="520" y="98" font-size="30" font-weight="700" fill="#4ade80">${escapeXml(avgGuesses)}</text>
    <text x="520" y="118" font-size="11.5" fill="#8b8f96">Avg. guesses</text>
    <text x="710" y="98" font-size="30" font-weight="700" fill="#4ade80">${daysAutonomous}</text>
    <text x="710" y="118" font-size="11.5" fill="#8b8f96">Days autonomous</text>
  </g>
  <line x1="24" y1="132" x2="776" y2="132" stroke="#22252d" stroke-width="1"/>
  <text x="776" y="145" font-size="9.5" fill="#5b5f68" text-anchor="end">Updated ${escapeXml(updated)}</text>
</svg>`;
}

function errorCard(message: string): string {
  return `<svg width="800" height="150" viewBox="0 0 800 150" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, sans-serif">
  <rect x="0.5" y="0.5" width="799" height="149" rx="10" fill="#0f1115" stroke="#262a33"/>
  <text x="24" y="32" font-size="15" font-weight="700" fill="#e7e9ea">Wordle Agent — Live Stats</text>
  <text x="24" y="78" font-size="13" fill="#f87171">${escapeXml(message)}</text>
</svg>`;
}

function svgResponse(svg: string): Response {
  return new Response(svg, {
    headers: {
      "Content-Type": "image/svg+xml",
      // Cache at the edge for 30 min - this is embedded as an <img> in a
      // README that gets viewed far more often than the underlying data
      // changes (once/day), so no need to hit Supabase on every view.
      "Cache-Control": "public, max-age=1800, s-maxage=1800",
    },
  });
}

// GET /api/stats-card.svg - dynamically rendered SVG for embedding in the
// project README: <img src="https://<project>.pages.dev/api/stats-card.svg">
export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { env } = context;
  try {
    const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
      auth: { persistSession: false },
    });

    const { data, error } = await supabase
      .from("wordle_runs")
      .select("puzzle_date, solved, num_attempts")
      .order("puzzle_date", { ascending: false })
      .limit(365);

    if (error) return svgResponse(errorCard(`Data error: ${error.message}`));

    const runs: Run[] = data ?? [];
    if (runs.length === 0) return svgResponse(errorCard("No runs recorded yet"));

    const solved = runs.filter((r) => r.solved);
    const winRate = `${Math.round((solved.length / runs.length) * 100)}%`;
    const avgGuesses = solved.length
      ? (solved.reduce((s, r) => s + r.num_attempts, 0) / solved.length).toFixed(2)
      : "-";

    const svg = renderCard({
      streak: computeStreak(runs),
      winRate,
      avgGuesses,
      daysAutonomous: computeDaysSinceLastFailure(runs),
      updated: runs[0].puzzle_date,
    });
    return svgResponse(svg);
  } catch (e: any) {
    return svgResponse(errorCard("Stats temporarily unavailable"));
  }
};
