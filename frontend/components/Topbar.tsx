"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Search } from "lucide-react";
import ActiveCommunityBadge from "./communities/ActiveCommunityBadge";
import { ProjectSwitcher } from "./ProjectSwitcher";
import { getCurrentUser } from "../lib/api/user";
import { createNode } from "../lib/api/graph";
import { searchKnowledge } from "../lib/api/search";
import { useAppStore } from "../lib/store";
import type { SearchResultsDTO, UserDTO } from "../lib/types";

export default function Topbar() {
  const [currentUser, setCurrentUser] = useState<UserDTO | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResultsDTO>({
    nodes: [],
    materials: [],
  });
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const currentProjectId = useAppStore((state) => state.currentProjectId);
  const pathname = usePathname();

  const linkClass = (href: string) =>
    pathname === href
      ? "rounded-lg px-4 py-2 text-sm font-medium text-blue-300 bg-blue-950 border border-blue-800"
      : "rounded-lg px-4 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800";

  useEffect(() => {
    let mounted = true;
    getCurrentUser()
      .then((user) => {
        if (mounted) {
          setCurrentUser(user);
        }
      })
      .catch(() => {
        if (mounted) {
          setCurrentUser(null);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const query = searchQuery.trim();
    if (!query || !currentProjectId) {
      setSearchResults({ nodes: [], materials: [] });
      setSearchOpen(false);
      setSearchLoading(false);
      setSearchError(null);
      return undefined;
    }

    setSearchLoading(true);
    setSearchError(null);

    const handle = window.setTimeout(async () => {
      try {
        const data = await searchKnowledge(currentProjectId, query, 8);
        setSearchResults(data);
        setSearchOpen(true);
      } catch {
        setSearchError("Search failed");
        setSearchOpen(true);
      } finally {
        setSearchLoading(false);
      }
    }, 250);

    return () => {
      window.clearTimeout(handle);
    };
  }, [currentProjectId, searchQuery]);

  const normalizedQuery = searchQuery.trim().toLowerCase();
  const hasExactNodeMatch = normalizedQuery
    ? searchResults.nodes.some(
        (item) => item.title.trim().toLowerCase() === normalizedQuery
      )
    : false;

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if (event.key !== "/") {
        return;
      }

      const target = event.target as HTMLElement | null;
      if (!target) {
        return;
      }

      const tagName = target.tagName.toLowerCase();
      if (
        tagName === "input" ||
        tagName === "textarea" ||
        (target as HTMLElement).isContentEditable
      ) {
        return;
      }

      event.preventDefault();
      searchInputRef.current?.focus();
    };

    document.addEventListener("keydown", handleShortcut);
    return () => {
      document.removeEventListener("keydown", handleShortcut);
    };
  }, []);

  return (
    <header className="border-b border-slate-800 bg-slate-950 px-4 py-4">
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
        <div className="flex min-w-0 items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#b2264c]/20 ring-1 ring-[#b2264c]/40">
              <svg
                viewBox="0 0 64 64"
                className="h-6 w-6"
                aria-hidden="true"
              >
                <ellipse cx="20" cy="14" rx="8" ry="12" fill="#b2264c" />
                <ellipse cx="44" cy="14" rx="8" ry="12" fill="#b2264c" />
                <circle cx="32" cy="34" r="18" fill="#b2264c" />
                <circle cx="26" cy="32" r="3" fill="#f9f4f5" />
                <circle cx="38" cy="32" r="3" fill="#f9f4f5" />
              </svg>
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-white">Graphbit</div>
            </div>
          </div>
          
          {/* Project Switcher */}
          <div className="flex items-center gap-3">
            <ProjectSwitcher />
            <ActiveCommunityBadge />
          </div>
        </div>

        <div className="relative hidden md:flex items-center justify-center">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search knowledge..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              onKeyDown={async (event) => {
                if (event.key === "Enter" && event.shiftKey) {
                  const value = searchQuery.trim();
                  if (!value || !currentProjectId || hasExactNodeMatch) {
                    return;
                  }
                  event.preventDefault();
                  try {
                    await createNode(currentProjectId, value, 0, 0.6);
                    setSearchQuery("");
                    setSearchOpen(false);
                    setSearchResults({ nodes: [], materials: [] });
                  } catch {
                    setSearchError("Failed to add node");
                    setSearchOpen(true);
                  }
                }
              }}
              className="w-48 rounded-lg border border-slate-700 bg-slate-800 py-2 pl-9 pr-4 text-sm text-slate-200 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 lg:w-64"
            />
            <kbd className="absolute right-3 top-1/2 hidden -translate-y-1/2 rounded border border-slate-600 bg-slate-700 px-1.5 py-0.5 text-xs text-slate-400 lg:block">
              /
            </kbd>
            {searchOpen && (
              <div className="absolute left-0 right-0 z-20 mt-2 rounded-xl border border-slate-700 bg-slate-900 p-3 shadow-xl">
                <div className="text-[10px] text-slate-500">Shift + Enter to add new node</div>
                {searchLoading && (
                  <div className="text-xs text-slate-400">Searching...</div>
                )}
                {searchError && (
                  <div className="text-xs text-red-300">{searchError}</div>
                )}
                {!searchLoading && !searchError && (
                  <div className="grid gap-3 text-xs text-slate-200">
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                        Nodes
                      </div>
                      {!searchLoading && normalizedQuery && currentProjectId && !hasExactNodeMatch && (
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              await createNode(currentProjectId, searchQuery.trim(), 0, 0.6);
                              setSearchQuery("");
                              setSearchOpen(false);
                              setSearchResults({ nodes: [], materials: [] });
                            } catch {
                              setSearchError("Failed to add node");
                              setSearchOpen(true);
                            }
                          }}
                          className="mt-2 w-full rounded-md border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-left text-xs text-rose-100 transition hover:border-rose-400/70"
                        >
                          Add "{searchQuery.trim()}"
                        </button>
                      )}
                      {searchResults.nodes.length === 0 && (
                        <div className="mt-1 text-slate-500">No node matches.</div>
                      )}
                      {searchResults.nodes.map((item) => (
                        <div key={item.id} className="mt-1 rounded-md border border-slate-800 bg-slate-950/70 px-2 py-1">
                          {item.title}
                        </div>
                      ))}
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                        Materials
                      </div>
                      {searchResults.materials.length === 0 && (
                        <div className="mt-1 text-slate-500">No material matches.</div>
                      )}
                      {searchResults.materials.map((item) => (
                        <div key={item.id} className="mt-1 rounded-md border border-slate-800 bg-slate-950/70 px-2 py-1">
                          {item.title}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <nav className="flex flex-wrap items-center gap-1">
            <a href="/" className={linkClass("/")}>
              Dashboard
            </a>
            <a href="/projects" className={linkClass("/projects")}>
              Projects
            </a>
            <a href="/graph" className={linkClass("/graph")}>
              Graph
            </a>
          </nav>
          <button className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-2 py-1 text-sm text-slate-200 transition hover:border-slate-600">
            <div className="flex h-7 w-7 items-center justify-center overflow-hidden rounded-full bg-slate-700">
              {currentUser?.avatar_url ? (
                <img
                  src={currentUser.avatar_url}
                  alt="User avatar"
                  className="h-full w-full object-cover"
                />
              ) : (
                <span className="text-xs font-semibold text-slate-200">
                  {(currentUser?.name ?? currentUser?.username ?? "U").slice(0, 1)}
                </span>
              )}
            </div>
            <span className="hidden max-w-[140px] truncate sm:inline">
              {currentUser?.name ?? currentUser?.username ?? "User"}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}
