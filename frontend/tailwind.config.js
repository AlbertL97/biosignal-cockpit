/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Biohacker-cockpit palette (DESIGN agent may refine in src/design/tokens)
        base: { 900: "#06090f", 800: "#0b111b", 700: "#121a28", 600: "#1a2536" },
        cyan: { DEFAULT: "#22d3ee", glow: "#67e8f9" },
        // semantic status
        ok: "#34d399",
        watch: "#fbbf24",
        alert: "#f87171",
        muted: "#64748b",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
        sans: ["Inter", "ui-sans-serif", "system-ui"],
      },
    },
  },
  plugins: [],
};
