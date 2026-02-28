import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontSize: {
        'xs': '11px',
        'sm': '13px',
        'base': '15px',
        'lg': '18px',
        'xl': '22px',
        '2xl': '28px',
        '3xl': '36px',
      },
      fontFamily: {
        heading: ['var(--font-heading)', 'sans-serif'],
        body: ['var(--font-body)', 'sans-serif'],
      },
      colors: {
        'bg-base': 'var(--bg-base)',
        'bg-surface': 'var(--bg-surface)',
        'bg-elevated': 'var(--bg-elevated)',
        'bg-hover': 'var(--bg-hover)',
        'accent': 'var(--accent)',
        'accent-hover': 'var(--accent-hover)',
        'accent-dim': 'var(--accent-dim)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'pkr-high': 'var(--pkr-high)',
        'pkr-medium': 'var(--pkr-medium)',
        'pkr-low': 'var(--pkr-low)',
        'border-default': 'var(--border)',
        'border-accent': 'var(--border-accent)',
      },
    },
  },
  plugins: [],
};

export default config;
