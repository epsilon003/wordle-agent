export type WordleRun = {
  id: string;
  puzzle_date: string;
  word: string | null;
  guesses: { guess: string; pattern: number[] }[];
  num_attempts: number;
  solved: boolean;
  duration_seconds: number | null;
  created_at: string;
};
