"use client";

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { ProjectDTO } from "@/lib/types";
import { getProjects } from "@/lib/api/project";

export function ProjectSwitcher() {
	const [projects, setProjects] = useState<ProjectDTO[]>([]);
	const [loading, setLoading] = useState(true);
	const { currentProjectId, currentProjectName, setCurrentProjectId, setCurrentProjectName } = useAppStore();

	useEffect(() => {
		fetchProjects();
	}, []);

	const fetchProjects = async () => {
		try {
			setLoading(true);
			const data = await getProjects();
			setProjects(data);

			const projectIds = new Set(data.map((project) => project.id));
			if (data.length > 0 && (!currentProjectId || !projectIds.has(currentProjectId))) {
				setCurrentProjectId(data[0].id);
				setCurrentProjectName(data[0].name);
			}
		} catch (error) {
			console.error("Failed to fetch projects:", error);
		} finally {
			setLoading(false);
		}
	};

	const handleProjectChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
		const projectId = event.target.value;
		const project = projects.find((p) => p.id === projectId);
		if (project) {
			setCurrentProjectId(project.id);
			setCurrentProjectName(project.name);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center gap-2">
				<span className="text-sm font-body text-gray-500">Loading projects...</span>
			</div>
		);
	}

	return (
		<div className="flex items-center gap-2">
			<label htmlFor="project-select" className="text-sm font-medium font-body text-text-secondary">
				Project:
			</label>
			<select
				id="project-select"
				value={currentProjectId || ""}
				onChange={handleProjectChange}
				className="w-32 max-w-full truncate rounded-md border border-border-default bg-bg-elevated px-2 py-1.5 text-sm font-body text-text-primary focus:border-accent-dim focus:outline-none focus:ring-1 focus:ring-accent-dim sm:w-40"
			>
				{projects.length === 0 ? (
					<option value="">No projects available</option>
				) : (
					projects.map((project) => (
						<option key={project.id} value={project.id}>
							{project.name}
						</option>
					))
				)}
			</select>
		</div>
	);
}
