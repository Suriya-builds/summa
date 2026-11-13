/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 50: "#f5f7fa", 100: "#e9edf3", 200: "#d3dae5", 300: "#a9b5c7", 400: "#7a8aa3", 500: "#56667f", 600: "#3f4d64", 700: "#2c384c", 800: "#1c2638", 900: "#111a2b" },
        brand: { 50: "#ecfdf6", 100: "#d1fae8", 200: "#a6f2d3", 400: "#34d39a", 500: "#10b37c", 600: "#079467", 700: "#067655", 800: "#085e46" },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"] },
      boxShadow: { card: "0 1px 2px rgba(17,26,43,.06), 0 1px 3px rgba(17,26,43,.04)" },
    },
  },
  plugins: [],
};
