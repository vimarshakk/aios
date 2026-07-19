/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
      colors: {
        "aios-bg":      "#0a0a0f",
        "aios-bg-2":    "#10101a",
        "aios-text":    "#f0f0ff",
        "aios-text-2":  "#a0a0c0",
        "aios-accent":  "#6e7cff",
        "aios-accent-2":"#a78bfa",
        "aios-green":   "#10b981",
        "aios-red":     "#ef4444",
        "aios-yellow":  "#f59e0b",
      },
      animation: {
        "slide-up":   "slide-up 0.2s ease forwards",
        "fade-in":    "fade-in 0.3s ease forwards",
        "glow-pulse": "glow-pulse 2s infinite",
        "typing":     "typing-bounce 1.2s infinite",
      },
      backdropBlur: {
        "2xl": "40px",
      },
    },
  },
  plugins: [],
};
