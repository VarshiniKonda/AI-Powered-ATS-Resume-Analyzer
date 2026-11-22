/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#142238",
        muted: "#66758a",
        brand: "#3767e8",
        canvas: "#f5f7fb",
      },
    },
  },
  plugins: [],
};