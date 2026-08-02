"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef } from "react";
import { Icon } from "./Icon";

type ComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
  size?: "hero" | "bar" | "workspace";
};

export function Composer({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "Ask about any Groww direct fund...",
  autoFocus = false,
  size = "hero",
}: ComposerProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const areaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!autoFocus) return;
    if (size === "hero") inputRef.current?.focus();
    else areaRef.current?.focus();
  }, [autoFocus, size]);

  function handleSubmit(event?: FormEvent) {
    event?.preventDefault();
    if (!value.trim() || disabled) return;
    onSubmit();
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }

  if (size === "workspace") {
    return (
      <form onSubmit={handleSubmit} className="w-full">
        <div className="glow-effect flex items-end gap-2 rounded-[28px] border border-white/10 bg-[#121418]/95 px-3 py-2 shadow-[0_16px_48px_rgba(0,0,0,0.45)] backdrop-blur-xl transition-all duration-300 ease-lumina">
          <button
            type="button"
            disabled
            title="Attachments are not supported"
            className="mb-1 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[#64748B]"
            aria-label="Attachments unavailable"
          >
            <Icon name="attach_file" className="text-[20px]" />
          </button>
          <textarea
            ref={areaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={disabled}
            maxLength={500}
            rows={1}
            placeholder={placeholder}
            className="mb-1 max-h-28 min-h-[40px] flex-1 resize-none bg-transparent py-2.5 text-[15px] text-[#F8FAFC] outline-none placeholder:text-[#64748B] disabled:opacity-60"
          />
          <button
            type="button"
            disabled
            title="Voice input is not supported"
            className="mb-1 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[#64748B]"
            aria-label="Voice input unavailable"
          >
            <Icon name="mic" className="text-[20px]" />
          </button>
          <button
            type="submit"
            disabled={disabled || !value.trim()}
            aria-label="Send"
            className="mb-0.5 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-groww text-[#003D2E] transition-all duration-200 hover:bg-groww-bright disabled:opacity-45"
          >
            <Icon name="send" className="text-[18px]" filled />
          </button>
        </div>
      </form>
    );
  }

  const tall = size === "hero";

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div
        className={`relative glass-panel rounded-full flex items-center glow-effect transition-all duration-300 ease-lumina ${
          tall ? "p-2 pl-5 pr-2" : "p-1.5 pl-5 pr-1.5"
        }`}
      >
        <Icon name="search" className="text-on-surface-variant mr-3 text-[20px]" />
        {tall ? (
          <input
            ref={inputRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={disabled}
            maxLength={500}
            placeholder={placeholder}
            className="flex-1 bg-transparent border-none outline-none text-on-surface placeholder:text-on-surface-variant/50 text-[15px] h-11 py-0 focus:ring-0 disabled:opacity-60"
          />
        ) : (
          <textarea
            ref={areaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={disabled}
            maxLength={500}
            rows={1}
            placeholder={placeholder}
            className="flex-1 bg-transparent border-none outline-none resize-none text-on-surface placeholder:text-on-surface-variant/50 text-body-md max-h-28 py-2.5 focus:ring-0 disabled:opacity-60"
          />
        )}
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label="Send"
          className="bg-groww hover:bg-groww-bright text-[#003D2E] h-11 w-11 rounded-full flex items-center justify-center shadow-[0_0_24px_rgba(0,179,134,0.45)] transition-all duration-200 ml-2 group hover:shadow-[0_0_32px_rgba(0,208,156,0.55)] disabled:opacity-50 disabled:shadow-none"
        >
          <Icon
            name="arrow_forward"
            className="group-hover:translate-x-0.5 transition-transform"
          />
        </button>
      </div>
    </form>
  );
}
