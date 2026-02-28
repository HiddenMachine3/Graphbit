import { getPKRColor } from "../../lib/colors";

export default function GraphLegend() {
  return (
    <div className="rounded-2xl border border-border-default bg-bg-surface p-4 text-sm font-body text-text-secondary">
      <div className="font-semibold font-heading text-text-primary">Legend</div>
      <div className="mt-3 space-y-2">
        <div className="text-xs font-medium font-body text-text-secondary">Node color = PKR level</div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: getPKRColor(0.8) }} />
          <span className="text-xs font-body">Mastered (≥ 0.7)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: getPKRColor(0.5) }} />
          <span className="text-xs font-body">Learning (≥ 0.4)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: getPKRColor(0.2) }} />
          <span className="text-xs font-body">Weak (&lt; 0.4)</span>
        </div>
      </div>
      <ul className="mt-3 space-y-1">
        <li>Brightness = attribute intensity</li>
        <li>Border intensity = forgetting (higher decay)</li>
        <li>Node size = importance</li>
      </ul>
    </div>
  );
}
