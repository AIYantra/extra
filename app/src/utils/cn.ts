import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/** Theme color tokens from src/styles/variable.css (for bg, text, border) */
const themeColors = [
  "background-1", "background-2", "background-3", "background-4", "background-5",
  "background-6", "background-7", "background-8", "background-9", "background-10",
  "background-11", "background-12", "background-13", "background-14",
  "stroke-1", "stroke-2", "stroke-3",
  "opai-yellow", "opai-purple", "opai-blue", "opai-lemon", "opai-green",
  "opai-red", "opai-orange", "opai-cyan", "opai-indigo",
  "gradient-1", "gradient-2", "gradient-3", "gradient-4", "gradient-5",
  "gradient-6", "gradient-7", "gradient-8", "gradient-9", "gradient-10",
  "gradient-11", "gradient-12", "gradient-13", "gradient-14", "gradient-15",
  "gradient-16", "gradient-17", "gradient-18", "gradient-19", "gradient-20",
  "gradient-22", "gradient-23", "gradient-24", "gradient-25", "gradient-26", "gradient-27",
] as const;

/** Theme fonts from src/styles/variable.css */
const themeFonts = [
  "inter-tight", "ibm-plex-mono", "instrument-serif", "manrope", "sora",
  "space-grotesk", "funnel-display",
] as const;

/** Theme typography (text-* sizes) from src/styles/variable.css */
const themeTextSizes = [
  "it-heading-1", "it-heading-2", "it-heading-3", "it-heading-4", "it-heading-5", "it-heading-6",
  "is-heading-1", "is-heading-2", "is-heading-3", "is-heading-4", "is-heading-5", "is-heading-6",
  "sora-heading-1", "sora-heading-2", "sora-heading-3", "sora-heading-4", "sora-heading-5", "sora-heading-6",
  "manrope-heading-1", "manrope-heading-2", "manrope-heading-3", "manrope-heading-4", "manrope-heading-5", "manrope-heading-6",
  "sg-heading-1", "sg-heading-2", "sg-heading-3", "sg-heading-4", "sg-heading-5", "sg-heading-6",
  "fd-heading-1", "fd-heading-2", "fd-heading-3", "fd-heading-4", "fd-heading-5", "fd-heading-6",
  "tagline-1", "tagline-2", "tagline-3", "tagline-4",
] as const;

/**
 * Custom tailwind-merge extended with theme classes from src/styles/variable.css
 * so conflicting custom utilities (e.g. bg-background-1 vs bg-background-2) merge correctly.
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "bg-color": [{ bg: [...themeColors] }],
      "text-color": [{ text: [...themeColors] }],
      "border-color": [{ border: [...themeColors] }],
      "font-family": [{ font: [...themeFonts] }],
      "font-size": [{ text: [...themeTextSizes] }],
      shadow: [{ shadow: ["1", "2", "3", "4", "5"] }],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
