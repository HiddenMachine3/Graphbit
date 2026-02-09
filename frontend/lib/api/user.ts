import { apiFetch } from "./client";
import type { UserDTO } from "../types";

export async function getCurrentUser(): Promise<UserDTO> {
  return apiFetch<UserDTO>("/users/me");
}
