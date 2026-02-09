import { apiFetch } from "./client";
import { ProjectDTO } from "../types";

export async function getProjects(): Promise<ProjectDTO[]> {
	return apiFetch<ProjectDTO[]>("/projects");
}

export async function getProject(projectId: string): Promise<ProjectDTO> {
	return apiFetch<ProjectDTO>(`/projects/${projectId}`);
}

export async function createProject(
	name: string,
	description: string,
	visibility: "private" | "shared" | "public"
): Promise<ProjectDTO> {
	return apiFetch<ProjectDTO>("/projects", {
		method: "POST",
		body: JSON.stringify({
			name,
			description,
			visibility,
		}),
	});
}

export async function updateProject(
	projectId: string,
	updates: { name?: string; description?: string; visibility?: "private" | "shared" | "public" }
): Promise<ProjectDTO> {
	return apiFetch<ProjectDTO>(`/projects/${projectId}`, {
		method: "PATCH",
		body: JSON.stringify(updates),
	});
}

export async function deleteProject(projectId: string): Promise<void> {
	await apiFetch<void>(`/projects/${projectId}`, { method: "DELETE" });
}
