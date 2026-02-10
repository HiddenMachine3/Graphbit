import type { Config } from "tailwindcss";
import colors from "tailwindcss/colors";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    colors: {
      ...colors,
      slate: {
        50: "#f9f4f5",
        100: "#f2e8eb",
        200: "#e2cdd2",
        300: "#c9a6af",
        400: "#a37b86",
        500: "#7d5b63",
        600: "#604149",
        700: "#4a2f36",
        800: "#352125",
        900: "#241518",
        950: "#14090b",
      },
      blue: {
        50: "#fdf2f3",
        100: "#fbe5e7",
        200: "#f6c8cd",
        300: "#f0a1ab",
        400: "#e56d80",
        500: "#d43f5c",
        600: "#b1264c",
        700: "#8a1b3c",
        800: "#68142d",
        900: "#450d1e",
        950: "#2a0712",
      },
    },
    extend: {},
  },
  plugins: [],
};

export default config;
