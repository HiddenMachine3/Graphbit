import { apiFetch } from "./client";
import type { SessionDTO } from "../types";

export async function getCurrentSession(): Promise<SessionDTO | null> {
  try {
    return await apiFetch<SessionDTO>("/sessions/current");
  } catch {
    return null;
  }
}

export async function startSession(): Promise<SessionDTO> {
  return apiFetch<SessionDTO>("/sessions", {
    method: "POST",
    body: JSON.stringify({}),
  });
}
