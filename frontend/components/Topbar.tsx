"use client";

import ActiveCommunityBadge from "./communities/ActiveCommunityBadge";

export default function Topbar() {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
      <div className="text-sm font-medium text-slate-600">Active Recall System</div>
      <div className="flex items-center gap-3">
        <ActiveCommunityBadge />
        <div className="text-xs text-slate-400">Frontend Phase 1</div>
      </div>
    </header>
  );
}
