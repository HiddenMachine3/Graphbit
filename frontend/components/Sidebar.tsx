"use client";

import { Play, Plus, Minus, Settings, Share } from "lucide-react";
import Link from "next/link";

export default function Sidebar() {
  return (
    <>
      <aside className="w-64 border-r border-slate-800 bg-[#0f0f14] p-4">
        {/* Daily Recall Section */}
        <div className="mb-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Daily Recall</h2>
          </div>
          <p className="mb-4 text-sm text-slate-400">
            Your knowledge queue for today.
          </p>
          <Link href="/session">
            <button className="flex w-full items-center justify-center space-x-2 rounded-lg bg-blue-600 py-3 font-medium text-white transition hover:bg-blue-700">
              <Play className="h-4 w-4 fill-white" />
              <span>Start Session</span>
            </button>
          </Link>
        </div>

      </aside>

      {/* Floating Action Buttons */}
      <div className="fixed bottom-4 right-4 flex flex-col space-y-2 z-50">
        <button className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg transition hover:bg-blue-700">
          <Plus className="h-5 w-5" />
        </button>
        <button className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-700 text-slate-300 shadow-lg transition hover:bg-slate-600">
          <Minus className="h-5 w-5" />
        </button>
        <button className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-700 text-slate-300 shadow-lg transition hover:bg-slate-600">
          <Settings className="h-5 w-5" />
        </button>
        <button className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-700 text-slate-300 shadow-lg transition hover:bg-slate-600">
          <Share className="h-5 w-5" />
        </button>
      </div>
    </>
  );
}
