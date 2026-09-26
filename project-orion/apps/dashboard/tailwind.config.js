/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#090D16',
          secondary: '#0F172A',
          card: '#141E33',
          hover: '#1A2742',
          border: '#1E293B',
          text: '#F8FAFC',
          subtext: '#94A3B8',
          muted: '#64748B',
          accent: '#0284C7',
          glow: '#38BDF8',
          profit: '#10B981',
          loss: '#F43F5E',
          warning: '#F59E0B',
          paper: '#FBBF24',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
};
