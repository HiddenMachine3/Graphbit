import { getPKRColor } from "../../lib/colors";

export default function GraphLegend() {
  return (
    <div className="rounded-2xl border border-border-default bg-bg-surface p-4 text-sm font-body text-text-secondary">
      <div className="font-semibold font-heading text-text-primary">Legend</div>

      <div className="mt-3 space-y-1">
        <div className="text-xs font-medium font-body text-text-secondary">Topic node color = PKR</div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: getPKRColor(0.8) }} />
          <span className="text-xs font-body">Mastered (&ge; 0.7)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: getPKRColor(0.5) }} />
          <span className="text-xs font-body">Learning (&ge; 0.4)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: getPKRColor(0.2) }} />
          <span className="text-xs font-body">Weak (&lt; 0.4)</span>
        </div>
      </div>

      <div className="mt-3 space-y-1">
        <div className="text-xs font-medium font-body text-text-secondary">Chapter nodes (YouTube videos)</div>
        {["#a78bfa", "#f97316", "#2dd4bf", "#f43f5e"].map((color, i) => (
          <div key={color} className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 rounded-full border-2"
              style={{ borderColor: color, backgroundColor: `${color}26` }}
            />
            <span className="text-xs font-body">Video #{i + 1} (and every {i === 3 ? "5th+" : ""}...)</span>
          </div>
        ))}
      </div>

      <div className="mt-3 space-y-1">
        <div className="text-xs font-medium font-body text-text-secondary">Edges</div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-8" style={{ borderTop: "2.5px dashed rgba(255,255,255,0.70)", display: "block" }} />
          <span className="text-xs font-body">Video sequence</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-8" style={{ borderTop: "2px solid rgba(255,255,255,0.25)", display: "block" }} />
          <span className="text-xs font-body">Knowledge edge</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-8" style={{ borderTop: "1.5px dashed rgba(255,255,255,0.12)", display: "block" }} />
          <span className="text-xs font-body">Material link</span>
        </div>
      </div>

      <ul className="mt-3 space-y-1 text-xs">
        <li>Border glow = forgetting decay</li>
        <li>Node size = importance</li>
        <li>Brightness = attribute intensity</li>
      </ul>
    </div>
  );
}
