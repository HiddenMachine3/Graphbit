import { create } from "zustand";

type AppState = {
  currentProjectId: string | null;
  currentProjectName: string | null;
  currentSessionId: string | null;
  currentCommunityId: string | null;
  currentCommunityName: string | null;
  isQuestioningMode: boolean;
  setCurrentProjectId: (id: string | null) => void;
  setCurrentProjectName: (name: string | null) => void;
  setCurrentSessionId: (id: string | null) => void;
  setCurrentCommunityId: (id: string | null) => void;
  setCurrentCommunityName: (name: string | null) => void;
  setIsQuestioningMode: (value: boolean) => void;
};

export const useAppStore = create<AppState>((set) => ({
  currentProjectId: null,
  currentProjectName: null,
  currentSessionId: null,
  currentCommunityId: null,
  currentCommunityName: null,
  isQuestioningMode: false,
  setCurrentProjectId: (id) => set({ currentProjectId: id }),
  setCurrentProjectName: (name) => set({ currentProjectName: name }),
  setCurrentSessionId: (id) => set({ currentSessionId: id }),
  setCurrentCommunityId: (id) => set({ currentCommunityId: id }),
  setCurrentCommunityName: (name) => set({ currentCommunityName: name }),
  setIsQuestioningMode: (value) => set({ isQuestioningMode: value }),
}));
