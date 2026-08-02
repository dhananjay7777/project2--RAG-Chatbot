import type { AskEnvelope, HealthPayload } from "./types";

const ASK_TIMEOUT_MS = 45_000;

export function apiBase(): string {
  return (process.env.NEXT_PUBLIC_MF_API_URL || "http://127.0.0.1:8000").replace(
    /\/$/,
    "",
  );
}

export async function fetchHealth(): Promise<HealthPayload> {
  const resp = await fetch(`${apiBase()}/health`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!resp.ok) {
    throw new Error(`health ${resp.status}`);
  }
  return resp.json();
}

export async function askQuestion(
  query: string,
): Promise<AskEnvelope | { detail: string; status: number }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ASK_TIMEOUT_MS);
  try {
    const resp = await fetch(`${apiBase()}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ query }),
      signal: controller.signal,
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        detail:
          typeof body.detail === "string"
            ? body.detail
            : "The assistant could not complete that lookup just now.",
        status: resp.status,
      };
    }
    return body as AskEnvelope;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return {
        detail:
          "That lookup took too long. Try a shorter factual question about one of the five Groww schemes.",
        status: 408,
      };
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
