import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // 長野県のイメージ: 山・緑・空
        brand: {
          50: '#f0f7f4',
          100: '#dceee5',
          200: '#bbdccb',
          300: '#8fc2a8',
          400: '#5fa481',
          500: '#3f8763',
          600: '#2f6c4d',
          700: '#27553f',
          800: '#214434',
          900: '#1c382c',
        },
      },
      fontFamily: {
        sans: ['Hiragino Sans', '"Yu Gothic"', 'Meiryo', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
