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
				<span className="text-sm text-gray-500">Loading projects...</span>
			</div>
		);
	}

	return (
		<div className="flex items-center gap-2">
			<label htmlFor="project-select" className="text-sm font-medium text-slate-300">
				Project:
			</label>
			<select
				id="project-select"
				value={currentProjectId || ""}
				onChange={handleProjectChange}
				className="w-32 max-w-full truncate rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 sm:w-40"
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
