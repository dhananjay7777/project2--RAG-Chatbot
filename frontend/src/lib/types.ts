export const DISCLAIMER = "Facts-only. No investment advice.";

export const FALLBACK_SCHEMES = [
  "Nippon India Value Fund Direct Growth",
  "Tata Multi Asset Allocation Fund Direct Growth",
  "Kotak Multi Asset Allocation Fund Direct Growth",
  "Franklin India Multi Cap Fund Direct Growth",
  "Samco Mid Cap Fund Direct Growth",
] as const;

export const SUGGESTION_CHIPS = [
  "What is expense ratio?",
  "Minimum SIP?",
  "Fund Manager?",
  "Exit Load?",
  "Risk Level?",
] as const;

export const FALLBACK_EXAMPLES = [
  "What is the exit load on Nippon India Value Fund Direct Growth?",
  "What is the minimum SIP for Samco Mid Cap Fund Direct Growth?",
  "Should I invest in Tata Multi Asset Allocation Fund?",
] as const;

export type AnswerRoute =
  | "FACTUAL"
  | "REFUSAL"
  | "PERFORMANCE_REDIRECT"
  | "NO_ANSWER"
  | "CLARIFY";

export type HealthPayload = {
  status: string;
  phase: string;
  disclaimer: string;
  registry_count: number;
  index_ready: boolean;
  schemes?: string[];
  example_questions?: string[];
  rate_limit_per_ip_per_hour?: number;
};

export type AskEnvelope = {
  route: AnswerRoute;
  answer: string;
  footer?: string;
  citation?: {
    url?: string;
    label?: string;
    source_id?: string;
  };
};

export type ChatMessage =
  | { id: string; role: "user"; text: string }
  | {
      id: string;
      role: "assistant";
      route: AnswerRoute;
      answer: string;
      note: string;
      footer: string;
      citationUrl: string | null;
      citationLabel: string;
      accent: string;
      badge: string;
    };

export const ROUTE_STYLE: Record<
  AnswerRoute,
  { badge: string; accent: string; note: string }
> = {
  FACTUAL: { badge: "Answer", accent: "#00D09C", note: "" },
  REFUSAL: {
    badge: "Out of bounds",
    accent: "#7DFFD0",
    note: "This assistant states facts and never gives investment advice.",
  },
  PERFORMANCE_REDIRECT: {
    badge: "Performance redirect",
    accent: "#00B386",
    note: "Returns and performance figures are only available on the source page.",
  },
  NO_ANSWER: {
    badge: "No answer found",
    accent: "#9BB5A8",
    note: "Nothing in the five source pages verifies an answer to that question.",
  },
  CLARIFY: {
    badge: "Needs detail",
    accent: "#00D09C",
    note: "Name one scheme so the lookup stays unambiguous.",
  },
};
