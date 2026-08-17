import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar,
} from "recharts";
import type { WordleRun } from "./types";

export function GuessesOverTime({ runs }: { runs: WordleRun[] }) {
  const data = [...runs]
    .sort((a, b) => a.puzzle_date.localeCompare(b.puzzle_date))
    .map((r) => ({
      date: r.puzzle_date.slice(5), // MM-DD
      guesses: r.solved ? r.num_attempts : null,
    }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data}>
        <CartesianGrid stroke="#22252d" strokeDasharray="3 3" />
        <XAxis dataKey="date" stroke="#8b8f96" fontSize={11} />
        <YAxis stroke="#8b8f96" fontSize={11} domain={[1, 6]} allowDecimals={false} />
        <Tooltip contentStyle={{ background: "#171a21", border: "1px solid #262a33" }} />
        <Line type="monotone" dataKey="guesses" stroke="#4ade80" strokeWidth={2} dot={{ r: 3 }} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function GuessDistribution({ runs }: { runs: WordleRun[] }) {
  const counts = [1, 2, 3, 4, 5, 6].map((n) => ({
    attempts: `${n}`,
    count: runs.filter((r) => r.solved && r.num_attempts === n).length,
  }));
  const failed = runs.filter((r) => !r.solved).length;
  const data = [...counts, { attempts: "X", count: failed }];

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <CartesianGrid stroke="#22252d" strokeDasharray="3 3" />
        <XAxis dataKey="attempts" stroke="#8b8f96" fontSize={12} />
        <YAxis stroke="#8b8f96" fontSize={11} allowDecimals={false} />
        <Tooltip contentStyle={{ background: "#171a21", border: "1px solid #262a33" }} />
        <Bar dataKey="count" fill="#4ade80" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
