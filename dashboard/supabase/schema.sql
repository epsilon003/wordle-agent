-- Run this once in the Supabase SQL editor for your project.

create table if not exists wordle_runs (
  id uuid primary key default gen_random_uuid(),
  puzzle_date date not null unique,
  word text,                          -- the solved word, if solved
  guesses jsonb not null default '[]'::jsonb, -- [{ "guess": "salet", "pattern": [0,0,0,1,1] }, ...]
  num_attempts int not null,
  solved boolean not null,
  duration_seconds numeric,
  created_at timestamptz not null default now()
);

create index if not exists wordle_runs_puzzle_date_idx on wordle_runs (puzzle_date desc);

-- Row Level Security: lock the table down. The Cloudflare Pages Function
-- talks to Supabase using the SERVICE ROLE key (set as a Pages
-- environment variable, never shipped to the browser), which bypasses RLS
-- entirely - so no public policies are needed or created here.
alter table wordle_runs enable row level security;
