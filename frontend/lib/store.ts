import { create } from "zustand";

type AppState = {
  currentProjectId: string | null;
  currentProjectName: string | null;
  currentSessionId: string | null;
  currentCommunityId: string | null;
  currentCommunityName: string | null;
  setCurrentProjectId: (id: string | null) => void;
  setCurrentProjectName: (name: string | null) => void;
  setCurrentSessionId: (id: string | null) => void;
  setCurrentCommunityId: (id: string | null) => void;
  setCurrentCommunityName: (name: string | null) => void;
};

export const useAppStore = create<AppState>((set) => ({
  currentProjectId: null,
  currentProjectName: null,
  currentSessionId: null,
  currentCommunityId: null,
  currentCommunityName: null,
  setCurrentProjectId: (id) => set({ currentProjectId: id }),
  setCurrentProjectName: (name) => set({ currentProjectName: name }),
  setCurrentSessionId: (id) => set({ currentSessionId: id }),
  setCurrentCommunityId: (id) => set({ currentCommunityId: id }),
  setCurrentCommunityName: (name) => set({ currentCommunityName: name }),
}));
