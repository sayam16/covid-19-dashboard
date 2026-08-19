import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#f4efe7",
        ink: "#1f2937",
        ember: "#c2410c",
        emberSoft: "#fed7aa",
        tealDeep: "#0f766e",
        tealSoft: "#ccfbf1",
        roseSoft: "#ffe4e6",
        slateSoft: "#e2e8f0"
      },
      boxShadow: {
        float: "0 24px 60px rgba(15, 23, 42, 0.12)"
      },
      fontFamily: {
        sans: ["Avenir Next", "Segoe UI", "Helvetica Neue", "sans-serif"],
        display: ["Georgia", "Times New Roman", "serif"]
      }
    }
  },
  plugins: []
};

export default config;
