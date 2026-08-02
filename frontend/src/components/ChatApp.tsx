"use client";

import { useCallback, useEffect, useState } from "react";
import { askQuestion, fetchHealth } from "@/lib/api";
import {
  AnswerRoute,
  ChatMessage,
  DISCLAIMER,
  FALLBACK_SCHEMES,
  ROUTE_STYLE,
} from "@/lib/types";
import { ChatView } from "./ChatView";
import { WelcomeView } from "./WelcomeView";
import { AiBackdrop } from "./AiBackdrop";

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function assistantFromEnvelope(envelope: {
  route?: string;
  answer?: string;
  footer?: string;
  citation?: { url?: string; label?: string };
}): ChatMessage {
  const route = (envelope.route || "NO_ANSWER") as AnswerRoute;
  const style = ROUTE_STYLE[route] || ROUTE_STYLE.NO_ANSWER;
  const showLink = route === "FACTUAL" && Boolean(envelope.citation?.url);
  return {
    id: uid(),
    role: "assistant",
    route,
    answer: envelope.answer || "",
    note: style.note,
    footer: showLink ? envelope.footer || "" : "",
    citationUrl: showLink ? envelope.citation?.url || null : null,
    citationLabel: showLink ? envelope.citation?.label || "Source" : "",
    accent: style.accent,
    badge: style.badge,
  };
}

export function ChatApp() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [schemes, setSchemes] = useState<string[]>([...FALLBACK_SCHEMES]);
  const [disclaimer, setDisclaimer] = useState(DISCLAIMER);

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((health) => {
        if (cancelled) return;
        if (health.disclaimer) setDisclaimer(health.disclaimer);
        if (health.schemes?.length) setSchemes(health.schemes);
        if (health.status !== "ok" || health.index_ready === false) {
          setStatus("Backend is degraded — index may be missing.");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("Cannot reach API. Set NEXT_PUBLIC_MF_API_URL / check CORS.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const ask = useCallback(
    async (raw?: string) => {
      const text = (raw ?? query).trim();
      if (!text || busy) return;
      if (text.length > 500) {
        setStatus("Questions are capped at 500 characters.");
        return;
      }
      setStatus("");
      setQuery("");
      setMessages((prev) => [...prev, { id: uid(), role: "user", text }]);
      setBusy(true);
      try {
        const result = await askQuestion(text);
        if ("status" in result && "detail" in result) {
          setMessages((prev) => [
            ...prev,
            assistantFromEnvelope({
              route: result.status === 429 ? "REFUSAL" : "NO_ANSWER",
              answer: result.detail,
            }),
          ]);
          return;
        }
        setMessages((prev) => [...prev, assistantFromEnvelope(result)]);
      } catch {
        setMessages((prev) => [
          ...prev,
          assistantFromEnvelope({
            route: "NO_ANSWER",
            answer:
              "The assistant could not complete that lookup just now. Try again, or ask about a different scheme detail.",
          }),
        ]);
      } finally {
        setBusy(false);
      }
    },
    [busy, query],
  );

  function reset() {
    setMessages([]);
    setQuery("");
    setStatus("");
  }

  if (messages.length === 0) {
    return (
      <div className="relative min-h-dvh">
        <AiBackdrop />
        <div className="relative z-10">
          <WelcomeView
            query={query}
            onQueryChange={setQuery}
            onAsk={ask}
            schemes={schemes}
            busy={busy}
            status={status}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-dvh">
      <AiBackdrop intensity="subtle" />
      <div className="relative z-10">
        <ChatView
          messages={messages}
          query={query}
          onQueryChange={setQuery}
          onAsk={() => ask()}
          onReset={reset}
          busy={busy}
          status={status}
          disclaimer={disclaimer}
          schemes={schemes}
        />
      </div>
    </div>
  );
}
