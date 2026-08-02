import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Groww accent only — surfaces stay neutral charcoal
        groww: {
          DEFAULT: "#00B386",
          bright: "#00D09C",
          deep: "#008F6B",
          mist: "#121418",
          fog: "#1A1D22",
        },
        background: "#0B0D10",
        surface: "#121418",
        "surface-dim": "#0B0D10",
        "surface-bright": "#1C1F24",
        "surface-container-lowest": "#0A0B0D",
        "surface-container-low": "#101214",
        "surface-container": "#15171B",
        "surface-container-high": "#1C1F24",
        "surface-container-highest": "#262A30",
        "on-surface": "#E8EAED",
        "on-surface-variant": "#9AA0A6",
        outline: "#3C4043",
        "outline-variant": "#2A2E32",
        primary: "#00D09C",
        "primary-container": "#00B386",
        "on-primary": "#003D2E",
        secondary: "#8AB4A8",
        "secondary-container": "#1A2E28",
        tertiary: "#A8ADB3",
        void: "#0A0B0D",
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        "2xl": "1rem",
        "3xl": "1.5rem",
        full: "9999px",
      },
      spacing: {
        gutter: "24px",
        "margin-mobile": "16px",
        "margin-desktop": "40px",
        "sidebar-width": "280px",
        "container-max": "1280px",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        "display-lg": [
          "48px",
          { lineHeight: "56px", letterSpacing: "-0.04em", fontWeight: "700" },
        ],
        "headline-lg": [
          "32px",
          { lineHeight: "40px", letterSpacing: "-0.02em", fontWeight: "600" },
        ],
        "headline-md": [
          "24px",
          { lineHeight: "32px", letterSpacing: "-0.01em", fontWeight: "600" },
        ],
        "body-lg": ["18px", { lineHeight: "28px", fontWeight: "400" }],
        "body-md": ["16px", { lineHeight: "24px", fontWeight: "400" }],
        "body-sm": ["14px", { lineHeight: "20px", fontWeight: "400" }],
        "label-md": [
          "12px",
          { lineHeight: "16px", letterSpacing: "0.05em", fontWeight: "500" },
        ],
      },
      keyframes: {
        fadeUp: {
          from: { opacity: "0", transform: "translateY(20px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pulseBar: {
          "0%, 100%": { transform: "translateX(-100%)" },
          "50%": { transform: "translateX(200%)" },
        },
      },
      animation: {
        "fade-up": "fadeUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "pulse-bar": "pulseBar 1.4s ease-in-out infinite",
      },
      transitionTimingFunction: {
        lumina: "cubic-bezier(0.4, 0, 0.2, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
