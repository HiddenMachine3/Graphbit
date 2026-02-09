"use client";

import { Search } from "lucide-react";
import ActiveCommunityBadge from "./communities/ActiveCommunityBadge";
import { ProjectSwitcher } from "./ProjectSwitcher";

export default function Topbar() {
  return (
    <header className="border-b border-slate-800 bg-[#0a0a0f] px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-blue-600">
              <span className="text-sm font-bold text-white">R</span>
            </div>
            <h1 className="text-xl font-semibold text-white">RecallGraph</h1>
          </div>
          
          {/* Project Switcher */}
          <ProjectSwitcher />
          
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search knowledge..."
              className="w-64 rounded-lg border border-slate-700 bg-slate-800 py-2 pl-9 pr-4 text-sm text-slate-200 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 rounded border border-slate-600 bg-slate-700 px-1.5 py-0.5 text-xs text-slate-400">
              ⌘K
            </kbd>
          </div>
        </div>

        <div className="flex items-center space-x-6">
          <nav className="flex space-x-1">
            <a href="/" className="rounded-lg px-4 py-2 text-sm font-medium text-blue-400 bg-blue-950 border border-blue-800">
              Dashboard
            </a>
            <a href="/graph" className="rounded-lg px-4 py-2 text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800">
              Graph
            </a>
          </nav>
          
          <div className="flex items-center space-x-3">
            <button className="relative rounded-lg p-2 text-slate-400 hover:text-white hover:bg-slate-800">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5-5-5h5v-5a7 7 0 1114 0v5z" />
              </svg>
            </button>
            
            <ActiveCommunityBadge />
            
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-500"></div>
          </div>
        </div>
      </div>
    </header>
  );
}
