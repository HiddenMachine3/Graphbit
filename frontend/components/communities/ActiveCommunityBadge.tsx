'use client';

import { useAppStore } from "../../lib/store";

export default function ActiveCommunityBadge() {
  const currentCommunityName = useAppStore((state) => state.currentCommunityName);

  return (
    <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600">
      {currentCommunityName ? `Community: ${currentCommunityName}` : "Community: none"}
    </div>
  );
}
