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
    <div className="rounded border border-slate-200 bg-white p-4">
      <div className="text-sm font-semibold text-slate-800">Switch Community</div>
      <div className="mt-3 flex flex-col gap-2">
        {communities.map((community) => (
          <button
            key={community.id}
            onClick={() => onSelect(community)}
            disabled={loading}
            className={`flex items-start justify-between rounded border px-3 py-2 text-left text-sm transition ${
              community.id === activeCommunityId
                ? "border-slate-900 bg-slate-900 text-white"
                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            <div>
              <div className="font-medium">{community.name}</div>
              <div className="text-xs text-slate-400">{community.description}</div>
            </div>
          </button>
        ))}
        {communities.length === 0 && (
          <div className="text-xs text-slate-500">No communities available.</div>
        )}
      </div>
    </div>
  );
}
