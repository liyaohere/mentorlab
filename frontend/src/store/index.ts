// frontend/src/store/index.ts
import { create } from "zustand";

export type AppPhase =
  | "login"
  | "intake"
  | "analyzing"
  | "diagnosis"
  | "response"
  | "survey"
  | "complete";

interface AppState {
  token: string | null;
  conversationId: string | null;
  condition: string | null;
  phase: AppPhase;
  responsePrompt: string | null;
  readingTime: number;

  setAuth: (token: string) => void;
  setInterviewData: (convId: string, condition: string) => void;
  setPhase: (phase: AppPhase) => void;
  setDiagnosisData: (prompt: string, time: number) => void;
  logout: () => void;
}

export const useStore = create<AppState>((set) => ({
  token: localStorage.getItem("token"),
  conversationId: null,
  condition: null,
  phase: localStorage.getItem("token") ? "intake" : "login",
  responsePrompt: null,
  readingTime: 0,

  setAuth: (token) => {
    localStorage.setItem("token", token);
    set({ token });
  },
  setInterviewData: (convId, condition) =>
    set({ conversationId: convId, condition }),
  setPhase: (phase) => set({ phase }),
  setDiagnosisData: (prompt, time) =>
    set({ responsePrompt: prompt, readingTime: time }),
  logout: () => {
    localStorage.removeItem("token");
    set({
      token: null,
      conversationId: null,
      phase: "login",
      responsePrompt: null,
      readingTime: 0,
    });
  },
}));
