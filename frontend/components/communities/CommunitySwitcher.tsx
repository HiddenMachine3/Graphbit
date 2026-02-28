import type { CommunityDTO } from "../../lib/types";

type CommunitySwitcherProps = {
  communities: CommunityDTO[];
  activeCommunityId: string | null;
  onSelect: (community: CommunityDTO) => void;
  loading?: boolean;
};

export default function CommunitySwitcher({
  communities,
  activeCommunityId,
  onSelect,
  loading = false,
}: CommunitySwitcherProps) {
  return (
    <div className="rounded border border-border-default bg-bg-surface p-4">
      <div className="text-sm font-semibold font-heading text-text-primary">Switch Community</div>
      <div className="mt-3 flex flex-col gap-2">
        {communities.map((community) => (
          <button
            key={community.id}
            onClick={() => onSelect(community)}
            disabled={loading}
            className={`flex items-start justify-between rounded border px-3 py-2 text-left text-sm font-body transition ${
              community.id === activeCommunityId
                ? "border-accent bg-bg-elevated text-text-primary"
                : "border-border-default bg-bg-surface text-text-secondary hover:bg-bg-hover"
            }`}
          >
            <div>
              <div className="font-medium">{community.name}</div>
              <div className="text-xs font-body text-text-muted">{community.description}</div>
            </div>
          </button>
        ))}
        {communities.length === 0 && (
          <div className="text-xs font-body text-text-muted">No communities available.</div>
        )}
      </div>
    </div>
  );
}
