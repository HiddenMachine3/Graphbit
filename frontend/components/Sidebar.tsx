"use client";

import { Play, Plus, Minus, Settings, Share } from "lucide-react";
import Link from "next/link";

interface DeckItem {
  id: string;
  name: string;
  count: number;
  color: string;
}

const priorityDecks: DeckItem[] = [
  { id: "1", name: "React Hooks", count: 12, color: "bg-blue-500" },
  { id: "2", name: "System Design", count: 8, color: "bg-purple-500" },
  { id: "3", name: "Philosophy", count: 25, color: "bg-green-500" },
];

const recentlyAdded: DeckItem[] = [
  { id: "4", name: "Medieval History", count: 0, color: "bg-gray-500" },
];

export default function Sidebar() {
  return (
    <>
      <aside className="w-64 border-r border-slate-800 bg-[#0f0f14] p-4">
        {/* Daily Recall Section */}
        <div className="mb-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Daily Recall</h2>
            <span className="rounded bg-blue-600 px-2 py-0.5 text-xs font-medium text-white">
              45 due
            </span>
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

        {/* Priority Decks */}
        <div className="mb-6">
          <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-400">
            Priority Decks
          </h3>
          <div className="space-y-2">
            {priorityDecks.map((deck) => (
              <div
                key={deck.id}
                className="flex items-center justify-between rounded-lg bg-slate-800 p-3 transition hover:bg-slate-700 cursor-pointer"
              >
                <div className="flex items-center space-x-3">
                  <div className={`h-3 w-3 rounded-full ${deck.color}`}></div>
                  <span className="text-sm font-medium text-slate-200">{deck.name}</span>
                </div>
                <span className="text-sm font-bold text-slate-400">{deck.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recently Added */}
        <div className="mb-6">
          <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-400">
            Recently Added
          </h3>
          <div className="space-y-2">
            {recentlyAdded.map((deck) => (
              <div
                key={deck.id}
                className="flex items-center justify-between rounded-lg bg-slate-800 p-3 transition hover:bg-slate-700 cursor-pointer"
              >
                <div className="flex items-center space-x-3">
                  <div className={`h-3 w-3 rounded-full ${deck.color}`}></div>
                  <span className="text-sm font-medium text-slate-200">{deck.name}</span>
                </div>
                <span className="rounded bg-blue-500 px-1.5 py-0.5 text-xs font-medium text-white">
                  New
                </span>
              </div>
            ))}
          </div>
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
