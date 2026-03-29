import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#102a43',
        mist: '#f4efe6',
        ember: '#d97706',
        teal: '#0f766e',
        clay: '#b45309',
      },
      boxShadow: {
        card: '0 24px 60px rgba(16, 42, 67, 0.10)',
      },
      fontFamily: {
        sans: ['"Segoe UI"', '"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
      },
      backgroundImage: {
        grain:
          'radial-gradient(circle at 20% 20%, rgba(217, 119, 6, 0.16), transparent 25%), radial-gradient(circle at 80% 0%, rgba(15, 118, 110, 0.18), transparent 22%), linear-gradient(135deg, #fbf7f1 0%, #eef5f3 48%, #f7efe4 100%)',
      },
    },
  },
  plugins: [],
} satisfies Config;