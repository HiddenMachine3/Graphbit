import type { CommunityProgressDTO } from "../../lib/types";

type CommunityProgressProps = {
  progress: CommunityProgressDTO | null;
};

export default function CommunityProgress({ progress }: CommunityProgressProps) {
  if (!progress) {
    return (
      <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-muted">
        Select a community to view progress.
      </div>
    );
  }

  const percent = Math.round(progress.overall_progress * 100);

  return (
    <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-secondary">
      <div className="text-sm font-semibold font-heading text-text-primary">Community Progress</div>
      <div className="mt-2 text-2xl font-semibold font-heading text-text-primary">{percent}%</div>
      <div className="mt-1 text-xs font-body text-text-muted">Relevant topics: {progress.relevant_topics}</div>
    </div>
  );
}
