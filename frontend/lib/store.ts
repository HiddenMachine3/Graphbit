import { create } from "zustand";

type AppState = {
  currentSessionId: string | null;
  currentCommunityId: string | null;
  currentCommunityName: string | null;
  setCurrentSessionId: (id: string | null) => void;
  setCurrentCommunityId: (id: string | null) => void;
  setCurrentCommunityName: (name: string | null) => void;
};

export const useAppStore = create<AppState>((set) => ({
  currentSessionId: null,
  currentCommunityId: null,
  currentCommunityName: null,
  setCurrentSessionId: (id) => set({ currentSessionId: id }),
  setCurrentCommunityId: (id) => set({ currentCommunityId: id }),
  setCurrentCommunityName: (name) => set({ currentCommunityName: name }),
}));
