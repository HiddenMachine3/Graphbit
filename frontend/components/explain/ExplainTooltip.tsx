'use client';

type ExplainTooltipProps = {
  label: string;
  text: string;
  className?: string;
};

export default function ExplainTooltip({ label, text, className }: ExplainTooltipProps) {
  return (
    <span className={`group relative inline-flex items-center gap-1 text-xs font-body text-text-muted ${className ?? ""}`}>
      {label}
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-text-muted" />
      <span className="pointer-events-none absolute left-0 top-full z-10 mt-2 hidden w-56 rounded border border-border-default bg-bg-elevated p-2 text-xs font-body text-text-secondary shadow-sm group-hover:block">
        {text}
      </span>
    </span>
  );
}
