/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}', './landing/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        orbitron: ['"Plus Jakarta Sans"', 'sans-serif'], // Redirect any orbitron usage to clean Plus Jakarta Sans
        heading: ['"Plus Jakarta Sans"', 'sans-serif'],
      },
      colors: {
        canvas: '#121316',
        surface: '#18191f',
        'surface-elevated': '#22242d',
        'surface-card': '#1c1d24',
        cyan: {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#e4e4e7',
          500: '#d4d4d8',
          600: '#a1a1aa',
          700: '#71717a',
          800: '#3f3f46',
          900: '#27272a',
          950: '#18181b',
        },
      },
    },
  },
  plugins: [],
};
