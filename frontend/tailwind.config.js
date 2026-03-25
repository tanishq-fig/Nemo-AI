/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ocean: {
          50: '#e6f7ff',
          100: '#b3e5ff',
          200: '#80d4ff',
          300: '#4dc2ff',
          400: '#1ab1ff',
          500: '#009fff',
          600: '#007acc',
          700: '#005999',
          800: '#003d66',
          900: '#002233',
          950: '#001119',
        },
        coral: {
          50: '#fff1f0',
          100: '#ffd4cf',
          200: '#ffb8ae',
          300: '#ff9c8d',
          400: '#ff7f6c',
          500: '#ff634b',
          600: '#cc4f3c',
          700: '#993b2d',
          800: '#66271e',
          900: '#33140f',
        },
      },
      backgroundImage: {
        'ocean-gradient': 'linear-gradient(180deg, #001119 0%, #003d66 50%, #005999 100%)',
        'ocean-radial': 'radial-gradient(ellipse at center, #005999 0%, #002233 100%)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'bubble': 'bubble 8s ease-in-out infinite',
        'wave': 'wave 8s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        bubble: {
          '0%': { transform: 'translateY(0) scale(1)', opacity: '0' },
          '10%': { opacity: '0.8' },
          '90%': { opacity: '0.8' },
          '100%': { transform: 'translateY(-100vh) scale(1.5)', opacity: '0' },
        },
        wave: {
          '0%, 100%': { transform: 'translateX(0)' },
          '50%': { transform: 'translateX(20px)' },
        },
      },
    },
  },
  plugins: [],
}
