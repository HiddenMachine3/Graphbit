import type { SessionDTO } from "../types";

export async function getCurrentSession(): Promise<SessionDTO | null> {
  return Promise.resolve(null);
}

export async function startSession(): Promise<SessionDTO> {
  return Promise.resolve({
    session_id: "mock-session",
    material_id: "mock-material",
    user_id: "mock-user",
    started_at: new Date().toISOString(),
    last_interjection_at: null,
    consumed_chunks: 0,
  });
}
