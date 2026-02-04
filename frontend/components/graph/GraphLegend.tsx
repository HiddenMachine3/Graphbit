export default function GraphLegend() {
  return (
    <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-600">
      <div className="font-semibold text-slate-900">Legend</div>
      <ul className="mt-2 space-y-1">
        <li>Brightness = PKR (higher mastery)</li>
        <li>Border intensity = forgetting (higher decay)</li>
        <li>Node size = fixed (layout only)</li>
      </ul>
    </div>
  );
}
