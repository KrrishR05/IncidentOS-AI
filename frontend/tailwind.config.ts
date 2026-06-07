import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        // IncidentOS custom colors
        neon: {
          blue: "#00f2fe",
          purple: "#a855f7",
          cyan: "#06b6d4",
          green: "#10b981",
          red: "#ef4444",
          orange: "#f59e0b",
        },
        surface: {
          1: "#0a0a0f",
          2: "#0f1117",
          3: "#141520",
          4: "#1a1d2e",
          5: "#1e2235",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 5px rgba(0, 242, 254, 0.3)" },
          "50%": { boxShadow: "0 0 20px rgba(0, 242, 254, 0.7), 0 0 40px rgba(0, 242, 254, 0.3)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
        "fade-in": "fade-in 0.3s ease-out",
        float: "float 3s ease-in-out infinite",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "neon-glow": "linear-gradient(135deg, rgba(0,242,254,0.1), rgba(168,85,247,0.1))",
        "card-glass": "linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01))",
        "shimmer-gradient": "linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)",
      },
      boxShadow: {
        "neon-blue": "0 0 15px rgba(0, 242, 254, 0.3), 0 0 30px rgba(0, 242, 254, 0.1)",
        "neon-purple": "0 0 15px rgba(168, 85, 247, 0.3), 0 0 30px rgba(168, 85, 247, 0.1)",
        "neon-green": "0 0 15px rgba(16, 185, 129, 0.3)",
        "neon-red": "0 0 15px rgba(239, 68, 68, 0.3)",
        "card-glow": "0 0 0 1px rgba(255,255,255,0.05), 0 4px 16px rgba(0,0,0,0.4)",
        glass: "inset 0 1px 0 rgba(255,255,255,0.05), 0 4px 24px rgba(0,0,0,0.4)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
