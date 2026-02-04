import type { CommunityProgressDTO } from "../../lib/types";

type CommunityProgressProps = {
  progress: CommunityProgressDTO | null;
};

export default function CommunityProgress({ progress }: CommunityProgressProps) {
  if (!progress) {
    return (
      <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
        Select a community to view progress.
      </div>
    );
  }

  const percent = Math.round(progress.overall_progress * 100);

  return (
    <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-600">
      <div className="text-sm font-semibold text-slate-800">Community Progress</div>
      <div className="mt-2 text-2xl font-semibold text-slate-900">{percent}%</div>
      <div className="mt-1 text-xs text-slate-500">Relevant topics: {progress.relevant_topics}</div>
    </div>
  );
}
