/** @type {import('tailwindcss').Config} */
// Passbook theme: paper, ink, a banknote green and a rubber-stamp vermilion.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    borderRadius: { none: "0", sm: "1px", DEFAULT: "2px", md: "2px", lg: "2px", xl: "2px", "2xl": "3px", "3xl": "4px", full: "9999px" },
    extend: {
      colors: {
        white: "#fcf9f2",
        paper: "#f1ecdf",
        ink: { 50: "#f1ecdf", 100: "#e4dccb", 200: "#d0c6b0", 300: "#ada28a", 400: "#877d69", 500: "#665d4e", 600: "#4a4337", 700: "#353028", 800: "#24201a", 900: "#161411" },
        brand: { 50: "#e9f1e8", 100: "#d2e4d4", 200: "#a8cbae", 400: "#4c9766", 500: "#2e7a4b", 600: "#1e6943", 700: "#165538", 800: "#10412b" },
        red: { 50: "#fbebe6", 100: "#f5d3c9", 200: "#ecad9d", 500: "#cf4129", 600: "#bd331c", 700: "#9d2916", 800: "#7c2011", 900: "#5c180d" },
        amber: { 50: "#f9f0d9", 100: "#f2e0b4", 200: "#e6c97f", 400: "#d1a237", 500: "#bd8c22", 600: "#a07318", 700: "#825d13", 800: "#684a0f", 900: "#4d370b" },
        sky: { 50: "#e8ecf7", 200: "#b7c3e8", 700: "#1f3fa8", 900: "#142968" },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        display: ['"Fraunces Variable"', "Georgia", "serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "Menlo", "monospace"],
      },
      boxShadow: { card: "none", hard: "4px 4px 0 0 #161411", "hard-sm": "2px 2px 0 0 #161411" },
    },
  },
  plugins: [],
};
