"use client";

import { useEffect, useState } from "react";
import { Composer } from "./Composer";
import { Icon } from "./Icon";
import { SchemeRail } from "./SchemeRail";
import { ChatMessage, DISCLAIMER } from "@/lib/types";

type Panel = "chat" | "history" | "about" | "disclaimers";

type ChatViewProps = {
  messages: ChatMessage[];
  query: string;
  onQueryChange: (value: string) => void;
  onAsk: () => void;
  onReset: () => void;
  busy: boolean;
  status: string;
  disclaimer?: string;
  schemes?: string[];
};

export function ChatView({
  messages,
  query,
  onQueryChange,
  onAsk,
  onReset,
  busy,
  status,
  disclaimer = DISCLAIMER,
  schemes = [],
}: ChatViewProps) {
  const [panel, setPanel] = useState<Panel>("chat");
  const [mobileNav, setMobileNav] = useState(false);

  useEffect(() => {
    const el = document.getElementById("thread-end");
    el?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  return (
    <div className="h-screen w-screen overflow-hidden bg-transparent text-on-surface flex">
      {busy ? (
        <div className="absolute top-0 left-0 right-0 h-0.5 overflow-hidden z-50">
          <div className="h-full w-1/3 bg-gradient-to-r from-transparent via-groww to-transparent animate-pulse-bar" />
        </div>
      ) : null}

      {/* Mobile sidebar overlay */}
      {mobileNav ? (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileNav(false)}
        />
      ) : null}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[300px] flex-col border-r border-white/[0.08] bg-[#0E1013]/78 backdrop-blur-xl px-4 py-5 transition-transform duration-300 ease-lumina md:static md:translate-x-0 ${
          mobileNav ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-5 flex items-center gap-3 px-1">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-groww">
            <Icon name="insights" className="text-[22px] text-[#003D2E]" filled />
          </div>
          <div className="min-w-0">
            <p className="truncate text-[15px] font-semibold tracking-tight text-[#E8EAED]">
              RAG Workspace
            </p>
            <p className="text-[12px] text-[#9AA0A6]">Groww corpus · facts-only</p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            onReset();
            setPanel("chat");
            setMobileNav(false);
          }}
          className="btn-groww mb-4 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-[14px] font-semibold transition-all duration-200"
        >
          <Icon name="add" className="text-[20px]" />
          New Chat
        </button>

        <SchemeRail schemes={schemes} variant="sidebar" className="mb-4" />

        <nav className="flex flex-col gap-1">
          {(
            [
              { id: "history" as const, icon: "history", label: "History" },
              { id: "about" as const, icon: "info", label: "About" },
              { id: "disclaimers" as const, icon: "gavel", label: "Disclaimers" },
            ]
          ).map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                setPanel(item.id);
                setMobileNav(false);
              }}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-[14px] transition-all duration-200 ${
                panel === item.id
                  ? "bg-white/[0.08] text-[#E8EAED]"
                  : "text-[#9AA0A6] hover:bg-white/[0.05] hover:text-[#E8EAED]"
              }`}
            >
              <Icon name={item.icon} className="text-[20px]" />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="mt-auto rounded-xl border border-white/[0.08] bg-white/[0.03] p-3">
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-groww">
            {disclaimer}
          </p>
          <p className="mt-1 text-[12px] leading-relaxed text-[#9AA0A6]">
            Ask only about the five schemes in this sidebar.
          </p>
        </div>
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col bg-transparent">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-white/[0.08] bg-[#0A0B0D]/35 px-4 backdrop-blur-md md:px-6">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              className="md:hidden inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-[#9AA0A6]"
              onClick={() => setMobileNav(true)}
              aria-label="Open menu"
            >
              <Icon name="menu" className="text-[20px]" />
            </button>
            <h1 className="truncate text-[16px] font-semibold tracking-tight text-[#E8EAED]">
              Mutual Fund FAQ Assistant
            </h1>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setPanel("history")}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-[#9AA0A6] transition-colors hover:bg-white/[0.06] hover:text-[#E8EAED]"
              aria-label="History"
            >
              <Icon name="history" className="text-[20px]" />
            </button>
            <button
              type="button"
              onClick={() => setPanel("about")}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-[#9AA0A6] transition-colors hover:bg-white/[0.06] hover:text-[#E8EAED]"
              aria-label="About"
            >
              <Icon name="settings" className="text-[20px]" />
            </button>
          </div>
        </header>

        <div className="relative flex-1 overflow-y-auto">
          {panel === "chat" ? (
            <div className="relative mx-auto flex max-w-[860px] flex-col gap-5 px-4 py-6 pb-36 md:px-8">
              <SchemeRail schemes={schemes} variant="strip" className="md:hidden" />
              <div className="flex justify-center">
                <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[11px] font-medium uppercase tracking-[0.08em] text-[#9AA0A6]">
                  Today
                </span>
              </div>

              {messages.map((message) =>
                message.role === "user" ? (
                  <div key={message.id} className="flex justify-end animate-fade-up">
                    <div className="max-w-[min(78%,640px)] rounded-2xl border border-white/10 bg-[#1C1F24] px-4 py-3 text-[15px] leading-relaxed text-[#E8EAED] shadow-[0_12px_32px_rgba(0,0,0,0.35)]">
                      {message.text}
                    </div>
                  </div>
                ) : (
                  <div key={message.id} className="flex gap-3 animate-fade-up">
                    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05]">
                      <Icon name="smart_toy" className="text-[18px] text-groww" filled />
                    </div>
                    <div className="max-w-[min(85%,680px)] rounded-2xl border border-white/[0.08] bg-[#121418]/95 px-4 py-3.5 shadow-[0_16px_40px_rgba(0,0,0,0.35)] backdrop-blur-md">
                      <span
                        className="mb-2.5 inline-block rounded-md border px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.08em]"
                        style={{
                          color: message.accent,
                          borderColor: `${message.accent}55`,
                          background: `${message.accent}14`,
                        }}
                      >
                        {message.badge}
                      </span>
                      <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-[#E8EAED]">
                        {message.answer}
                      </p>
                      {message.note ? (
                        <p className="mt-2.5 text-[13px] leading-relaxed text-[#9AA0A6]">
                          {message.note}
                        </p>
                      ) : null}
                      {message.citationUrl ? (
                        <a
                          href={message.citationUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-white/[0.05] px-2.5 py-1.5 font-mono text-[12px] text-groww transition-all duration-200 hover:bg-white/[0.08]"
                        >
                          <Icon name="link" className="text-[14px]" />
                          {message.citationLabel || "Source"}
                        </a>
                      ) : null}
                      {message.footer ? (
                        <p className="mt-3 border-t border-dashed border-white/10 pt-2.5 font-mono text-[11px] leading-relaxed text-[#9AA0A6]">
                          {message.footer}
                        </p>
                      ) : null}
                    </div>
                  </div>
                ),
              )}
              <div id="thread-end" />
            </div>
          ) : (
            <SidePanel
              panel={panel}
              disclaimer={disclaimer}
              schemes={schemes}
              messages={messages}
              onSelectHistory={() => setPanel("chat")}
              onBack={() => setPanel("chat")}
            />
          )}
        </div>

        {panel === "chat" ? (
          <div className="absolute bottom-0 left-0 right-0 z-20 border-t border-white/[0.08] bg-[#0A0B0D]/55 px-4 pb-4 pt-3 backdrop-blur-xl md:px-8">
            <div className="mx-auto max-w-[860px]">
              <Composer
                value={query}
                onChange={onQueryChange}
                onSubmit={onAsk}
                disabled={busy}
                size="workspace"
                placeholder="Ask about funds, ratios, or scheme facts…"
              />
              {status ? (
                <p className="mt-2 text-center text-[12px] text-[#ffb4ab]">{status}</p>
              ) : (
                <p className="mt-2 text-center text-[11px] text-[#6B7280]">
                  Facts-only · five Groww Direct Growth schemes · no investment advice
                </p>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function SidePanel({
  panel,
  disclaimer,
  schemes,
  messages,
  onSelectHistory,
  onBack,
}: {
  panel: Exclude<Panel, "chat">;
  disclaimer: string;
  schemes: string[];
  messages: ChatMessage[];
  onSelectHistory: () => void;
  onBack: () => void;
}) {
  const userTurns = messages.filter((m) => m.role === "user");

  return (
    <div className="relative mx-auto max-w-[720px] px-4 py-8 md:px-8">
      <button
        type="button"
        onClick={onBack}
        className="mb-6 inline-flex items-center gap-2 text-[13px] text-[#94A3B8] hover:text-[#F8FAFC]"
      >
        <Icon name="arrow_back" className="text-[18px]" />
        Back to chat
      </button>

      {panel === "history" ? (
        <div className="space-y-3">
          <h2 className="text-[20px] font-semibold text-[#F8FAFC]">History</h2>
          <p className="text-[14px] text-[#94A3B8]">
            This session stays in your browser tab only — nothing is saved on the server.
          </p>
          {userTurns.length === 0 ? (
            <p className="rounded-xl border border-white/8 bg-white/[0.03] p-4 text-[14px] text-[#94A3B8]">
              No questions in this chat yet.
            </p>
          ) : (
            <ul className="space-y-2">
              {userTurns.map((m) => (
                <li key={m.id}>
                  <button
                    type="button"
                    onClick={onSelectHistory}
                    className="w-full rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3 text-left text-[14px] text-[#F8FAFC] transition-colors hover:bg-white/[0.06]"
                  >
                    {m.text}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      {panel === "about" ? (
        <div className="space-y-4">
          <h2 className="text-[20px] font-semibold text-[#F8FAFC]">About</h2>
          <p className="text-[14px] leading-relaxed text-[#94A3B8]">
            Mutual Fund FAQ Assistant is a facts-only RAG demo over exactly five Groww
            Direct Growth scheme pages. It retrieves corpus context and phrases short
            grounded answers — never investment advice.
          </p>
          <h3 className="text-[13px] font-semibold uppercase tracking-[0.08em] text-groww">
            Covered schemes
          </h3>
          <SchemeRail schemes={schemes} variant="card" />
        </div>
      ) : null}

      {panel === "disclaimers" ? (
        <div className="space-y-4">
          <h2 className="text-[20px] font-semibold text-[#F8FAFC]">Disclaimers</h2>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
            <p className="text-[16px] font-semibold text-groww">{disclaimer}</p>
            <p className="mt-3 text-[14px] leading-relaxed text-[#9AA0A6]">
              Answers cite Groww scheme pages only. No rankings, comparisons across funds,
              performance quotes, or personalized recommendations.
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
