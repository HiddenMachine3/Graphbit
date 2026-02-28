'use client';

import { useAppStore } from "../../lib/store";

export default function ActiveCommunityBadge() {
  const currentCommunityName = useAppStore((state) => state.currentCommunityName);

  return (
    <div className="rounded-full border border-border-default bg-bg-elevated px-3 py-1 text-xs font-medium font-body text-text-secondary">
      {currentCommunityName ? `Community: ${currentCommunityName}` : "Community: none"}
    </div>
  );
}
