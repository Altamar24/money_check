/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./tracker/templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        primary: '#2563eb',
        danger:  '#dc2626',
        success: '#16a34a',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    }
  },
  plugins: [],
}
