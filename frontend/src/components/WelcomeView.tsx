"use client";

import { Composer } from "./Composer";
import { Icon } from "./Icon";
import { SchemeRail } from "./SchemeRail";
import { DISCLAIMER, SUGGESTION_CHIPS } from "@/lib/types";

type WelcomeViewProps = {
  query: string;
  onQueryChange: (value: string) => void;
  onAsk: (question?: string) => void;
  schemes: string[];
  busy: boolean;
  status: string;
};

export function WelcomeView({
  query,
  onQueryChange,
  onAsk,
  schemes,
  busy,
  status,
}: WelcomeViewProps) {
  return (
    <main className="relative flex min-h-dvh flex-col items-center overflow-y-auto bg-transparent px-4 py-8 md:px-8 md:py-10">
      <div className="pointer-events-none absolute left-1/2 top-[28%] h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-groww/[0.05] blur-[130px]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[360px] w-[360px] rounded-full bg-white/[0.02] blur-[100px]" />

      <div className="z-10 flex w-full max-w-[820px] flex-1 flex-col items-center justify-center gap-7 md:gap-8">
        <div className="flex animate-fade-up flex-col items-center text-center opacity-0 delay-100">
          <p className="mb-4 inline-flex items-center rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-[11px] font-medium uppercase tracking-[0.06em] text-[#9AA0A6]">
            {DISCLAIMER}
          </p>
          <h1 className="gradient-text mb-3 text-[34px] font-bold leading-tight tracking-tight text-balance md:text-[42px]">
            Mutual Fund FAQ Assistant
          </h1>
          <p className="mx-auto max-w-lg text-[15px] leading-relaxed text-on-surface-variant text-balance">
            Ask a factual question about one of the five Groww Direct Growth schemes.
          </p>
        </div>

        <div className="relative mx-auto w-full max-w-2xl animate-fade-up opacity-0 delay-200">
          <div
            aria-hidden
            className="pointer-events-none absolute -inset-4 rounded-[40px] bg-groww/[0.07] blur-2xl"
          />
          <div className="relative">
            <Composer
              value={query}
              onChange={onQueryChange}
              onSubmit={() => onAsk()}
              disabled={busy}
              autoFocus
              size="hero"
            />
          </div>
          {status ? (
            <p className="relative mt-3 text-center text-[13px] text-[#ffb4ab]">{status}</p>
          ) : null}
        </div>

        <div className="flex flex-wrap justify-center gap-2.5 animate-fade-up opacity-0 delay-200">
          {SUGGESTION_CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              disabled={busy}
              onClick={() => onAsk(chip)}
              className="rounded-lg border border-white/10 bg-white/[0.03] px-3.5 py-2 text-[13px] text-on-surface-variant transition-all duration-200 ease-lumina hover:border-groww/35 hover:bg-groww/10 hover:text-on-surface disabled:opacity-50"
            >
              {chip}
            </button>
          ))}
        </div>

        <div className="grid w-full grid-cols-1 gap-4 animate-fade-up opacity-0 delay-300 sm:grid-cols-2">
          <article className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 text-left">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/[0.04]">
              <Icon name="shield_with_heart" className="text-[18px] text-[#9AA0A6]" />
            </div>
            <div className="min-w-0">
              <h3 className="mb-1 text-[14px] font-semibold text-[#E8EAED]">
                Facts-only
              </h3>
              <p className="text-[12px] leading-relaxed text-[#9AA0A6]">
                Grounded in Groww scheme pages — no advice, rankings, or performance
                quotes.
              </p>
            </div>
          </article>

          <article className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 text-left">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/[0.04]">
              <Icon name="memory" className="text-[18px] text-[#9AA0A6]" />
            </div>
            <div className="min-w-0">
              <h3 className="mb-1 text-[14px] font-semibold text-[#E8EAED]">
                Powered by RAG
              </h3>
              <p className="text-[12px] leading-relaxed text-[#9AA0A6]">
                Retrieves corpus context, then Groq phrases a short grounded answer.
              </p>
            </div>
          </article>
        </div>
      </div>

      <div className="z-10 mt-8 w-full max-w-[820px] animate-fade-up opacity-0 delay-300 md:mt-10">
        <SchemeRail schemes={schemes} variant="strip" />
      </div>
    </main>
  );
}
