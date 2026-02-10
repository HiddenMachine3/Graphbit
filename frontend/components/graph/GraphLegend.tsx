export default function GraphLegend() {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-300">
      <div className="font-semibold text-white">Legend</div>
      <ul className="mt-2 space-y-1">
        <li>Brightness = PKR (higher mastery)</li>
        <li>Border intensity = forgetting (higher decay)</li>
        <li>Node size = fixed (layout only)</li>
      </ul>
    </div>
  );
}
