/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        editorial: {
          bg: '#F4F1EA',
          text: '#1A1A1A',
          accent: '#E0D7C6',
          card: '#E8E5DF',
          paper: '#FDFDFB',
          dark: '#2D2D2D',
          line: 'rgba(26, 26, 26, 0.12)',
        },
      },
      fontFamily: {
        serif: ['"Georgia"', '"Times New Roman"', '"Playfair Display"', 'serif'],
        sans: ['"Inter"', '"Helvetica Neue"', '"Arial"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
