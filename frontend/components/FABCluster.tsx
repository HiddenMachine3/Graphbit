"use client";

import { Plus, Minus, Settings, Share } from "lucide-react";

export default function FABCluster() {
  return (
    <div className="fixed bottom-6 right-6 flex flex-col gap-2 z-50">
      <button className="flex h-12 w-12 items-center justify-center rounded-full bg-accent text-white shadow-lg transition hover:bg-accent-hover">
        <Plus className="h-5 w-5" />
      </button>
      <button className="flex h-12 w-12 items-center justify-center rounded-full bg-bg-elevated text-text-secondary shadow-lg transition hover:bg-bg-hover">
        <Minus className="h-5 w-5" />
      </button>
      <button className="flex h-12 w-12 items-center justify-center rounded-full bg-bg-elevated text-text-secondary shadow-lg transition hover:bg-bg-hover">
        <Settings className="h-5 w-5" />
      </button>
      <button className="flex h-12 w-12 items-center justify-center rounded-full bg-bg-elevated text-text-secondary shadow-lg transition hover:bg-bg-hover">
        <Share className="h-5 w-5" />
      </button>
    </div>
  );
}
