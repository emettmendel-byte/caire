/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        clinical: {
          blue: '#0ea5e9',
          green: '#059669',
          yellow: '#ca8a04',
          slate: '#475569',
          paper: '#f8fafc',
        },
      },
    },
  },
  plugins: [],
}
