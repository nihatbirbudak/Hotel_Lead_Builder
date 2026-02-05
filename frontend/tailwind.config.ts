import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          500: '#1e293b',
          600: '#0f172a',
        },
      },
    },
  },
  plugins: [],
}
export default config
