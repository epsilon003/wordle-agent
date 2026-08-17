import { createClient } from "@supabase/supabase-js";

interface Env {
  SUPABASE_URL: string;
  SUPABASE_SERVICE_ROLE_KEY: string;
  INGEST_SECRET: string;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

// POST /api/runs - called once a day by the GitHub Actions runner after it
// plays Wordle. Protected by a shared secret (not real auth, just keeps
// randoms off the internet from writing fake rows into your table).
export const onRequestPost: PagesFunction<Env> = async (context) => {
  const { request, env } = context;

  const secret = request.headers.get("x-ingest-secret");
  if (!secret || secret !== env.INGEST_SECRET) {
    return json({ error: "unauthorized" }, 401);
  }

  let body: any;
  try {
    body = await request.json();
  } catch {
    return json({ error: "invalid JSON body" }, 400);
  }

  const { puzzle_date, word, guesses, num_attempts, solved, duration_seconds } = body ?? {};
  if (!puzzle_date || typeof num_attempts !== "number" || typeof solved !== "boolean") {
    return json({ error: "missing required fields" }, 400);
  }

  const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { persistSession: false },
  });

  const { error } = await supabase
    .from("wordle_runs")
    .upsert(
      {
        puzzle_date,
        word: word ?? null,
        guesses: guesses ?? [],
        num_attempts,
        solved,
        duration_seconds: duration_seconds ?? null,
      },
      { onConflict: "puzzle_date" }
    );

  if (error) return json({ error: error.message }, 500);
  return json({ ok: true });
};

// GET /api/runs - raw run history, most recent first. Used by the
// dashboard frontend, also handy for curl'ing during setup.
export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { env } = context;
  const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { persistSession: false },
  });

  const { data, error } = await supabase
    .from("wordle_runs")
    .select("*")
    .order("puzzle_date", { ascending: false })
    .limit(365);

  if (error) return json({ error: error.message }, 500);
  return json({ runs: data });
};
