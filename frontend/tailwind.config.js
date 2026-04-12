/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"Share Tech Mono"', '"Courier New"', 'monospace'],
      },
      colors: {
        nerv: {
          bg: '#080808',
          surface: '#0d0d0d',
          border: '#1a1a1a',
          muted: '#2a2a2a',
          text: '#666',
          dim: '#252525',
        },
      },
    },
  },
  plugins: [],
}
