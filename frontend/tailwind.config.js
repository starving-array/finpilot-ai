/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        score: {
          high: '#16a34a',
          medium: '#ca8a04',
          low: '#ea580c',
          'very-low': '#dc2626',
        },
      },
    },
  },
  plugins: [],
}
