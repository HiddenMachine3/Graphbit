// ──────────────────────────────────────────────
// PKR (Proven Knowledge Rating) semantic colors
// ──────────────────────────────────────────────
// These map a 0-1 knowledge score to a three-tier
// green / amber / red color scale used across the
// graph, node lists, detail panels, and progress bars.

/** RGB tuples for each PKR tier */
const PKR_RGB = {
  high: [61, 184, 122] as const,   // green
  medium: [224, 148, 58] as const, // amber
  low: [224, 85, 85] as const,     // red
} as const;

/** Pick the RGB tuple for a given PKR value */
export function getPKRTier(pkr: number): readonly [number, number, number] {
  if (pkr >= 0.7) return PKR_RGB.high;
  if (pkr >= 0.4) return PKR_RGB.medium;
  return PKR_RGB.low;
}

/** CSS var color string — for Tailwind-style usage via style prop */
export function getPKRColor(pkr: number): string {
  if (pkr >= 0.7) return 'var(--pkr-high)';
  if (pkr >= 0.4) return 'var(--pkr-medium)';
  return 'var(--pkr-low)';
}

/** CSS var background string — low-opacity tinted bg */
export function getPKRBg(pkr: number): string {
  if (pkr >= 0.7) return 'var(--pkr-high-bg)';
  if (pkr >= 0.4) return 'var(--pkr-medium-bg)';
  return 'var(--pkr-low-bg)';
}

/** rgba() string with custom alpha — for inline styles (graph nodes, glows) */
export function getPKRRgba(pkr: number, alpha: number): string {
  const [r, g, b] = getPKRTier(pkr);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Tailwind class name for text color */
export function getPKRTextClass(pkr: number): string {
  if (pkr >= 0.7) return 'text-pkr-high';
  if (pkr >= 0.4) return 'text-pkr-medium';
  return 'text-pkr-low';
}

/** Tailwind class name for border color */
export function getPKRBorderClass(pkr: number): string {
  if (pkr >= 0.7) return 'border-pkr-high';
  if (pkr >= 0.4) return 'border-pkr-medium';
  return 'border-pkr-low';
}
