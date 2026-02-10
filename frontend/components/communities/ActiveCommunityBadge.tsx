'use client';

import { useAppStore } from "../../lib/store";

export default function ActiveCommunityBadge() {
  const currentCommunityName = useAppStore((state) => state.currentCommunityName);

  return (
    <div className="rounded-full border border-blue-800 bg-blue-950 px-3 py-1 text-xs font-medium text-blue-300">
      {currentCommunityName ? `Community: ${currentCommunityName}` : "Community: none"}
    </div>
  );
}
