"use client";

type SchemeRailProps = {
  schemes: string[];
  /** Compact list for sidebar; full strip for welcome */
  variant?: "sidebar" | "strip" | "card";
  className?: string;
};

export function SchemeRail({
  schemes,
  variant = "sidebar",
  className = "",
}: SchemeRailProps) {
  if (variant === "strip") {
    return (
      <div
        className={`w-full border-t border-white/[0.06] pt-4 ${className}`}
      >
        <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.12em] text-[#6B7280]">
          Covered in corpus · 5 Groww Direct Growth schemes
        </p>
        <ul className="grid grid-cols-1 gap-x-8 gap-y-2 sm:grid-cols-2">
          {schemes.map((name, i) => (
            <li
              key={name}
              className="flex items-start gap-2 text-[12px] leading-snug text-[#7A8088]"
            >
              <span className="mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center font-mono text-[10px] text-[#5F666E]">
                {i + 1}.
              </span>
              <span>{name}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div className={`glass-panel rounded-xl p-5 ${className}`}>
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.1em] text-groww">
          Covered schemes (always in corpus)
        </p>
        <ol className="space-y-2">
          {schemes.map((name, i) => (
            <li
              key={name}
              className="flex gap-2.5 text-[13px] leading-snug text-[#E8EAED]"
            >
              <span className="font-mono text-groww/90">{i + 1}.</span>
              <span>{name}</span>
            </li>
          ))}
        </ol>
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl border border-white/[0.08] bg-white/[0.03] p-3 ${className}`}
    >
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-groww">
        Covered schemes
      </p>
      <ol className="space-y-2">
        {schemes.map((name, i) => (
          <li
            key={name}
            className="flex gap-2 text-[12px] leading-snug text-[#C4C7C5]"
          >
            <span className="shrink-0 font-mono text-groww">{i + 1}.</span>
            <span>{name}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
