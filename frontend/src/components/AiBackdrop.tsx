"use client";

import { useEffect, useRef } from "react";

export type BackdropIntensity = "full" | "subtle";

type AiBackdropProps = {
  /** `full` for welcome; `subtle` for chat (quieter ambient mist). */
  intensity?: BackdropIntensity;
};

/**
 * AI backdrop.
 * - full: flowing aurora / signal waves (welcome)
 * - subtle: soft drifting mist orbs + sparse sparks (chat) — quieter so UI stays primary
 */
export function AiBackdrop({ intensity = "full" }: AiBackdropProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const subtle = intensity === "subtle";
    let width = 0;
    let height = 0;
    let raf = 0;
    let running = true;
    let t = 0;
    const mouse = { x: 0.5, y: 0.45, active: false };

    const ribbons = subtle
      ? [
          { amp: 36, freq: 0.0019, speed: 0.008, y: 0.38, alpha: 0.07, thick: 1.3, hue: "0, 179, 134" },
          { amp: 44, freq: 0.0015, speed: 0.006, y: 0.52, alpha: 0.05, thick: 1.5, hue: "148, 163, 184" },
          { amp: 30, freq: 0.0022, speed: 0.009, y: 0.66, alpha: 0.055, thick: 1.2, hue: "0, 208, 156" },
        ]
      : [
          { amp: 42, freq: 0.0022, speed: 0.012, y: 0.28, alpha: 0.11, thick: 1.4, hue: "0, 179, 134" },
          { amp: 56, freq: 0.0016, speed: 0.008, y: 0.42, alpha: 0.08, thick: 1.8, hue: "148, 163, 184" },
          { amp: 34, freq: 0.0028, speed: 0.015, y: 0.55, alpha: 0.09, thick: 1.2, hue: "0, 208, 156" },
          { amp: 48, freq: 0.0019, speed: 0.01, y: 0.68, alpha: 0.06, thick: 2.0, hue: "100, 120, 140" },
        ];

    const orbs = subtle
      ? [
          { x: 0.2, y: 0.28, r: 240, drift: 0.0003, phase: 0, color: "0, 179, 134", a: 0.055 },
          { x: 0.8, y: 0.65, r: 280, drift: 0.00025, phase: 1.7, color: "120, 140, 160", a: 0.04 },
          { x: 0.5, y: 0.45, r: 200, drift: 0.00035, phase: 3.1, color: "0, 208, 156", a: 0.04 },
        ]
      : [
          { x: 0.22, y: 0.3, r: 180, drift: 0.0004, phase: 0, color: "0, 179, 134", a: 0.07 },
          { x: 0.78, y: 0.62, r: 220, drift: 0.0003, phase: 1.7, color: "148, 163, 184", a: 0.05 },
          { x: 0.55, y: 0.2, r: 140, drift: 0.0005, phase: 3.1, color: "0, 208, 156", a: 0.045 },
        ];

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas!.width = Math.floor(width * dpr);
      canvas!.height = Math.floor(height * dpr);
      canvas!.style.width = `${width}px`;
      canvas!.style.height = `${height}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function onMove(event: PointerEvent) {
      mouse.x = event.clientX / Math.max(width, 1);
      mouse.y = event.clientY / Math.max(height, 1);
      mouse.active = true;
    }

    function onLeave() {
      mouse.active = false;
    }

    function drawRibbon(
      amp: number,
      freq: number,
      speed: number,
      baseY: number,
      alpha: number,
      thick: number,
      hue: string,
      time: number,
    ) {
      if (!ctx) return;
      const midY = baseY * height;
      const warpScale = subtle ? 10 : 28;
      const warpRadius = subtle ? 0.22 : 0.35;
      ctx.beginPath();
      for (let x = 0; x <= width; x += 6) {
        const nx = x / width;
        let warp = 0;
        if (mouse.active) {
          const dx = nx - mouse.x;
          const dy = baseY - mouse.y;
          const d = Math.hypot(dx * 1.4, dy);
          if (d < warpRadius) {
            warp = (1 - d / warpRadius) * warpScale * Math.sin(time * 1.4 + nx * 8);
          }
        }
        const y =
          midY +
          Math.sin(x * freq + time * speed * 60 + baseY * 9) * amp +
          Math.sin(x * freq * 2.4 - time * speed * 35) * (amp * 0.28) +
          warp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = `rgba(${hue}, ${alpha})`;
      ctx.lineWidth = thick;
      ctx.lineCap = "round";
      ctx.stroke();

      // Soft wash under ribbons (lighter on subtle)
      ctx.lineTo(width, height);
      ctx.lineTo(0, height);
      ctx.closePath();
      const fill = ctx.createLinearGradient(0, midY - amp * 2, 0, midY + amp * 4);
      fill.addColorStop(0, `rgba(${hue}, ${alpha * (subtle ? 0.22 : 0.35)})`);
      fill.addColorStop(1, `rgba(${hue}, 0)`);
      ctx.fillStyle = fill;
      ctx.fill();
    }

    function step() {
      if (!running || !ctx) return;
      ctx.clearRect(0, 0, width, height);

      const washA = subtle ? 0.022 : 0.03;
      const washG = subtle ? 0.016 : 0.02;
      const wash = ctx.createRadialGradient(
        width * 0.5,
        height * 0.35,
        40,
        width * 0.5,
        height * 0.45,
        Math.max(width, height) * 0.72,
      );
      wash.addColorStop(0, `rgba(255, 255, 255, ${washA})`);
      wash.addColorStop(0.5, `rgba(0, 179, 134, ${washG})`);
      wash.addColorStop(1, "rgba(10, 11, 13, 0)");
      ctx.fillStyle = wash;
      ctx.fillRect(0, 0, width, height);

      if (!reduced) t += subtle ? 0.013 : 0.016;

      for (const orb of orbs) {
        const ox =
          (orb.x + (reduced ? 0 : Math.sin(t * orb.drift * 40 + orb.phase) * 0.04)) *
          width;
        const oy =
          (orb.y + (reduced ? 0 : Math.cos(t * orb.drift * 32 + orb.phase) * 0.03)) *
          height;
        const g = ctx.createRadialGradient(ox, oy, 0, ox, oy, orb.r);
        g.addColorStop(0, `rgba(${orb.color}, ${orb.a})`);
        g.addColorStop(1, `rgba(${orb.color}, 0)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(ox, oy, orb.r, 0, Math.PI * 2);
        ctx.fill();
      }

      for (const r of ribbons) {
        drawRibbon(r.amp, r.freq, r.speed, r.y, r.alpha, r.thick, r.hue, t);
      }

      if (!reduced) {
        const sparkCount = subtle ? 12 : 18;
        for (let i = 0; i < sparkCount; i += 1) {
          const seed = i * 17.13;
          const px = ((Math.sin(seed) * 0.5 + 0.5) * width + t * (8 + (i % 5))) % width;
          const py =
            height - ((t * (14 + (i % 7)) + seed * 40) % (height + 40));
          const pa =
            (subtle ? 0.08 : 0.12) +
            (Math.sin(t * 2 + seed) * 0.5 + 0.5) * (subtle ? 0.1 : 0.18);
          ctx.beginPath();
          ctx.arc(px, py, 1.1 + (i % 3) * 0.35, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(0, 208, 156, ${pa})`;
          ctx.fill();
        }
      }

      if (mouse.active) {
        const mx = mouse.x * width;
        const my = mouse.y * height;
        const haloR = subtle ? 120 : 160;
        const halo = ctx.createRadialGradient(mx, my, 0, mx, my, haloR);
        halo.addColorStop(0, `rgba(0, 179, 134, ${subtle ? 0.055 : 0.1})`);
        halo.addColorStop(0.5, `rgba(0, 179, 134, ${subtle ? 0.018 : 0.03})`);
        halo.addColorStop(1, "rgba(0, 179, 134, 0)");
        ctx.fillStyle = halo;
        ctx.beginPath();
        ctx.arc(mx, my, haloR, 0, Math.PI * 2);
        ctx.fill();
      }

      raf = window.requestAnimationFrame(step);
    }

    resize();
    step();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerleave", onLeave);
    window.addEventListener("blur", onLeave);

    return () => {
      running = false;
      window.cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("blur", onLeave);
    };
  }, [intensity]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0 h-full w-full"
    />
  );
}
