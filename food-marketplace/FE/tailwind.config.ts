import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-manrope)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains)', 'ui-monospace', 'monospace'],
      },
      colors: {
        // Brand
        primary: {
          DEFAULT: '#FFC629',
          hover: '#e6ae00',
          soft: '#FFF8E1',
          ink: '#1a1a1a',
        },
        // Semantic
        accent: {
          DEFAULT: '#E8553D',
          soft: '#FFEDE7',
        },
        eco: {
          DEFAULT: '#2E7D5B',
          soft: '#EAF3ED',
        },
        warn: {
          DEFAULT: '#C88A1B',
          soft: '#FFF4DE',
        },
        danger: '#C44536',
        // App surfaces
        bg: '#f7f6f3',
        surface: '#ffffff',
        ink: {
          100: '#1a1a1a',
          60: '#4a4a4a',
          40: '#8a8a8a',
        },
        line: '#ececea',
        line2: '#e1e0db',
        // Backward-compat aliases (used by existing components)
        background: '#ffffff',
        text: '#1a1a1a',
        muted: '#8a8a8a',
        divider: '#ececea',
        countdown: '#E8553D',
      },
      borderRadius: {
        // Updated design tokens
        card: '14px',
        button: '10px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(20,20,20,.04), 0 0 0 1px rgba(20,20,20,.04)',
        md: '0 8px 24px rgba(20,20,20,.08), 0 0 0 1px rgba(20,20,20,.04)',
      },
      fontSize: {
        // Design typography scale
        'display': ['44px', { fontWeight: '800', letterSpacing: '-0.025em', lineHeight: '1.1' }],
        'h1': ['32px', { fontWeight: '800', letterSpacing: '-0.02em', lineHeight: '1.2' }],
        'h2': ['24px', { fontWeight: '800', letterSpacing: '-0.02em', lineHeight: '1.25' }],
        'h3': ['20px', { fontWeight: '800', letterSpacing: '-0.02em', lineHeight: '1.3' }],
        'panel-title': ['17px', { fontWeight: '700', letterSpacing: '-0.01em', lineHeight: '1.35' }],
        'body': ['15px', { fontWeight: '400', lineHeight: '1.55' }],
        'body-sm': ['13.5px', { fontWeight: '500', lineHeight: '1.5' }],
        'caption': ['12.5px', { fontWeight: '600', lineHeight: '1.4' }],
        'eyebrow': ['11.5px', { fontWeight: '700', letterSpacing: '0.12em', lineHeight: '1.4' }],
      },
    },
  },
  plugins: [],
};

export default config;
