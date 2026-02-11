"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";

import { useAppStore } from "@/lib/store";
import type {
  CommunityDTO,
  MaterialDTO,
  NodeDTO,
  ProjectDTO,
  QuestionDTO,
  UserDTO,
} from "@/lib/types";
import { getProjects, createProject, deleteProject } from "@/lib/api/project";
import { listNodes, createNode } from "@/lib/api/graph";
import {
  listQuestions as listQuestionBank,
  createQuestion,
  deleteQuestion,
  updateQuestion,
} from "@/lib/api/question";
import {
  listMaterials,
  createMaterial,
  deleteMaterial,
  fetchMaterial,
  updateMaterial,
  replaceMaterialNodes,
} from "@/lib/api/material";
import {
  listCommunities,
  createCommunity,
  deleteCommunity,
  updateCommunity,
} from "@/lib/api/community";
import { getCurrentUser } from "@/lib/api/user";

type StatusState = {
  type: "idle" | "success" | "error";
  message: string;
};

function SectionCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-[0_0_30px_rgba(107,24,44,0.35)]">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

const parseCsv = (value: string) =>
  value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectDTO[]>([]);
  const [nodes, setNodes] = useState<NodeDTO[]>([]);
  const [questions, setQuestions] = useState<QuestionDTO[]>([]);
  const [materials, setMaterials] = useState<MaterialDTO[]>([]);
  const [communities, setCommunities] = useState<CommunityDTO[]>([]);
  const [currentUser, setCurrentUser] = useState<UserDTO | null>(null);
  const [status, setStatus] = useState<StatusState>({
    type: "idle",
    message: "",
  });
  const [busy, setBusy] = useState(false);

  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [projectVisibility, setProjectVisibility] = useState<
    "private" | "shared" | "public"
  >("private");

  const [nodeTopic, setNodeTopic] = useState("");
  const [nodeImportance, setNodeImportance] = useState(0.6);
  const [nodeRelevance, setNodeRelevance] = useState(0.7);

  const [questionText, setQuestionText] = useState("");
  const [questionAnswer, setQuestionAnswer] = useState("");
  const [questionType, setQuestionType] = useState("OPEN");
  const [questionDifficulty, setQuestionDifficulty] = useState(1);
  const [questionTags, setQuestionTags] = useState("");
  const [questionNodeIds, setQuestionNodeIds] = useState("");
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [editQuestionText, setEditQuestionText] = useState("");
  const [editQuestionAnswer, setEditQuestionAnswer] = useState("");
  const [editQuestionType, setEditQuestionType] = useState("OPEN");
  const [editQuestionDifficulty, setEditQuestionDifficulty] = useState(1);
  const [editQuestionTags, setEditQuestionTags] = useState("");
  const [editQuestionNodeIds, setEditQuestionNodeIds] = useState("");

  const [materialTitle, setMaterialTitle] = useState("");
  const [materialText, setMaterialText] = useState("");
  const [materialFiles, setMaterialFiles] = useState<FileList | null>(null);
  const [editingMaterialId, setEditingMaterialId] = useState<string | null>(null);
  const [editMaterialTitle, setEditMaterialTitle] = useState("");
  const [editMaterialText, setEditMaterialText] = useState("");
  const [editingMaterialNodesId, setEditingMaterialNodesId] = useState<string | null>(null);
  const [materialNodeSearch, setMaterialNodeSearch] = useState("");
  const [materialNodeSelection, setMaterialNodeSelection] = useState<string[]>([]);

  const [communityName, setCommunityName] = useState("");
  const [communityDescription, setCommunityDescription] = useState("");
  const [communityProjectIds, setCommunityProjectIds] = useState("");
  const [editingCommunityId, setEditingCommunityId] = useState<string | null>(null);
  const [editCommunityName, setEditCommunityName] = useState("");
  const [editCommunityDescription, setEditCommunityDescription] = useState("");
  const [editCommunityProjectIds, setEditCommunityProjectIds] = useState("");

  const currentProjectId = useAppStore((state) => state.currentProjectId);
  const setCurrentProjectId = useAppStore((state) => state.setCurrentProjectId);
  const setCurrentProjectName = useAppStore((state) => state.setCurrentProjectName);

  const currentProject = useMemo(
    () => projects.find((project) => project.id === currentProjectId) ?? null,
    [projects, currentProjectId]
  );

  const materialNodeMap = useMemo(() => {
    const map = new Map<string, NodeDTO[]>();
    materials.forEach((material) => {
      const linkedNodes = nodes.filter((node) =>
        (node.source_material_ids ?? []).includes(material.id)
      );
      map.set(material.id, linkedNodes);
    });
    return map;
  }, [materials, nodes]);

  const resetStatus = () => setStatus({ type: "idle", message: "" });

  const refreshProjects = async () => {
    const data = await getProjects();
    setProjects(data);
    const projectIds = new Set(data.map((project) => project.id));
    if (data.length > 0 && (!currentProjectId || !projectIds.has(currentProjectId))) {
      setCurrentProjectId(data[0].id);
      setCurrentProjectName(data[0].name);
    }
  };

  const refreshProjectData = async (projectId: string) => {
    const [nodeData, questionData, materialData] = await Promise.all([
      listNodes(projectId),
      listQuestionBank(projectId),
      listMaterials(projectId),
    ]);
    setNodes(nodeData);
    setQuestions(questionData);
    setMaterials(materialData);
  };

  const refreshCommunities = async () => {
    const data = await listCommunities();
    setCommunities(data);
  };

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const [user] = await Promise.all([getCurrentUser()]);
        if (mounted) {
          setCurrentUser(user);
        }
      } catch {
        if (mounted) {
          setCurrentUser(null);
        }
      }
      try {
        await refreshProjects();
        await refreshCommunities();
      } catch (error) {
        if (mounted) {
          setStatus({
            type: "error",
            message: "Failed to load project data",
          });
        }
      }
    };

    load();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!currentProjectId) {
      setNodes([]);
      setQuestions([]);
      setMaterials([]);
      return;
    }
    let mounted = true;
    refreshProjectData(currentProjectId)
      .catch(() => {
        if (mounted) {
          setStatus({
            type: "error",
            message: "Failed to load project details",
          });
        }
      })
      .finally(() => {
        if (mounted) {
          setBusy(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [currentProjectId]);

  const handleCreateProject = async () => {
    if (!projectName.trim()) {
      setStatus({ type: "error", message: "Project name is required" });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      const created = await createProject(
        projectName.trim(),
        projectDescription.trim(),
        projectVisibility
      );
      await refreshProjects();
      setCurrentProjectId(created.id);
      setCurrentProjectName(created.name);
      setProjectName("");
      setProjectDescription("");
      setStatus({ type: "success", message: "Project created" });
    } catch (error) {
      setStatus({ type: "error", message: "Failed to create project" });
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    resetStatus();
    setBusy(true);
    try {
      await deleteProject(projectId);
      const remaining = projects.filter((project) => project.id !== projectId);
      setProjects(remaining);
      if (currentProjectId === projectId) {
        const nextProject = remaining[0] ?? null;
        setCurrentProjectId(nextProject?.id ?? null);
        setCurrentProjectName(nextProject?.name ?? null);
      }
      setStatus({ type: "success", message: "Project deleted" });
    } catch {
      setStatus({ type: "error", message: "Failed to delete project" });
    } finally {
      setBusy(false);
    }
  };

  const handleCreateNode = async () => {
    if (!currentProjectId) {
      setStatus({ type: "error", message: "Select a project first" });
      return;
    }
    if (!nodeTopic.trim()) {
      setStatus({ type: "error", message: "Node topic is required" });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      await createNode(currentProjectId, nodeTopic.trim(), nodeImportance, nodeRelevance);
      await refreshProjectData(currentProjectId);
      setNodeTopic("");
      setStatus({ type: "success", message: "Node added" });
    } catch {
      setStatus({ type: "error", message: "Failed to add node" });
    } finally {
      setBusy(false);
    }
  };

  const handleCreateQuestion = async () => {
    if (!currentProjectId) {
      setStatus({ type: "error", message: "Select a project first" });
      return;
    }
    if (!questionText.trim() || !questionAnswer.trim()) {
      setStatus({
        type: "error",
        message: "Question text and answer are required",
      });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      await createQuestion({
        project_id: currentProjectId,
        text: questionText.trim(),
        answer: questionAnswer.trim(),
        question_type: questionType,
        difficulty: questionDifficulty,
        tags: parseCsv(questionTags),
        covered_node_ids: parseCsv(questionNodeIds),
        created_by: currentUser?.username ?? undefined,
      });
      await refreshProjectData(currentProjectId);
      setQuestionText("");
      setQuestionAnswer("");
      setQuestionTags("");
      setQuestionNodeIds("");
      setStatus({ type: "success", message: "Question created" });
    } catch {
      setStatus({ type: "error", message: "Failed to create question" });
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteQuestion = async (questionId: string) => {
    if (!currentProjectId) {
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      await deleteQuestion(questionId);
      await refreshProjectData(currentProjectId);
      setStatus({ type: "success", message: "Question deleted" });
    } catch {
      setStatus({ type: "error", message: "Failed to delete question" });
    } finally {
      setBusy(false);
    }
  };

  const beginEditQuestion = (question: QuestionDTO) => {
    setEditingQuestionId(question.id);
    setEditQuestionText(question.text);
    setEditQuestionAnswer(question.answer);
    setEditQuestionType(question.question_type ?? "OPEN");
    setEditQuestionDifficulty(question.difficulty ?? 1);
    setEditQuestionTags((question.tags ?? []).join(", "));
    setEditQuestionNodeIds((question.covered_node_ids ?? []).join(", "));
  };

  const cancelEditQuestion = () => {
    setEditingQuestionId(null);
  };

  const handleUpdateQuestion = async (questionId: string) => {
    if (!currentProjectId) {
      return;
    }
    if (!editQuestionText.trim() || !editQuestionAnswer.trim()) {
      setStatus({
        type: "error",
        message: "Question text and answer are required",
      });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      await updateQuestion(questionId, {
        text: editQuestionText.trim(),
        answer: editQuestionAnswer.trim(),
        question_type: editQuestionType,
        difficulty: editQuestionDifficulty,
        tags: parseCsv(editQuestionTags),
        covered_node_ids: parseCsv(editQuestionNodeIds),
      });
      await refreshProjectData(currentProjectId);
      setEditingQuestionId(null);
      setStatus({ type: "success", message: "Question updated" });
    } catch {
      setStatus({ type: "error", message: "Failed to update question" });
    } finally {
      setBusy(false);
    }
  };

  const handleCreateMaterial = async () => {
    if (!currentProjectId) {
      setStatus({ type: "error", message: "Select a project first" });
      return;
    }
    if (!materialTitle.trim() || !materialText.trim()) {
      setStatus({
        type: "error",
        message: "Material title and text are required",
      });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      await createMaterial(
        currentProjectId,
        materialTitle.trim(),
        materialText.trim(),
        currentUser?.username ?? undefined
      );
      await refreshProjectData(currentProjectId);
      setMaterialTitle("");
      setMaterialText("");
      setStatus({ type: "success", message: "Material created" });
    } catch {
      setStatus({ type: "error", message: "Failed to create material" });
    } finally {
      setBusy(false);
    }
  };

  const beginEditMaterial = async (material: MaterialDTO) => {
    resetStatus();
    setBusy(true);
    try {
      const fullMaterial = await fetchMaterial(material.id);
      setEditingMaterialId(material.id);
      setEditMaterialTitle(material.title);
      setEditMaterialText(fullMaterial.chunks.join("\n\n"));
    } catch {
      setStatus({ type: "error", message: "Failed to load material" });
    } finally {
      setBusy(false);
    }
  };

  const cancelEditMaterial = () => {
    setEditingMaterialId(null);
  };

  const beginEditMaterialNodes = (material: MaterialDTO) => {
    const linked = materialNodeMap.get(material.id) ?? [];
    setEditingMaterialNodesId(material.id);
    setMaterialNodeSelection(linked.map((node) => node.id));
    setMaterialNodeSearch("");
  };

  const cancelEditMaterialNodes = () => {
    setEditingMaterialNodesId(null);
    setMaterialNodeSelection([]);
    setMaterialNodeSearch("");
  };

  const handleSaveMaterialNodes = async (materialId: string) => {
    if (!currentProjectId) {
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      await replaceMaterialNodes(materialId, materialNodeSelection);
      await refreshProjectData(currentProjectId);
      setEditingMaterialNodesId(null);
      setStatus({ type: "success", message: "Material links updated" });
    } catch {
      setStatus({ type: "error", message: "Failed to update material links" });
    } finally {
      setBusy(false);
    }
  };

  const handleUpdateMaterial = async (materialId: string) => {
    if (!currentProjectId) {
      return;
    }
    if (!editMaterialTitle.trim() || !editMaterialText.trim()) {
      setStatus({
        type: "error",
        message: "Material title and text are required",
      });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      await updateMaterial(materialId, {
        title: editMaterialTitle.trim(),
        content_text: editMaterialText.trim(),
      });
      await refreshProjectData(currentProjectId);
      setEditingMaterialId(null);
      setStatus({ type: "success", message: "Material updated" });
    } catch {
      setStatus({ type: "error", message: "Failed to update material" });
    } finally {
      setBusy(false);
    }
  };

  const handleUploadMaterialFiles = async () => {
    if (!currentProjectId) {
      setStatus({ type: "error", message: "Select a project first" });
      return;
    }
    if (!materialFiles || materialFiles.length === 0) {
      setStatus({ type: "error", message: "Choose .txt files to upload" });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      for (const file of Array.from(materialFiles)) {
        const content = await file.text();
        const title = file.name.replace(/\.txt$/i, "").trim() || "Untitled";
        await createMaterial(
          currentProjectId,
          title,
          content,
          currentUser?.username ?? undefined
        );
      }
      await refreshProjectData(currentProjectId);
      setMaterialFiles(null);
      setStatus({ type: "success", message: "Materials uploaded" });
    } catch {
      setStatus({ type: "error", message: "Failed to upload materials" });
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteMaterial = async (materialId: string) => {
    if (!currentProjectId) {
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      await deleteMaterial(materialId);
      await refreshProjectData(currentProjectId);
      setStatus({ type: "success", message: "Material deleted" });
    } catch {
      setStatus({ type: "error", message: "Failed to delete material" });
    } finally {
      setBusy(false);
    }
  };

  const handleCreateCommunity = async () => {
    if (!communityName.trim()) {
      setStatus({ type: "error", message: "Community name is required" });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      const projectIds = parseCsv(communityProjectIds);
      if (currentProjectId && !projectIds.includes(currentProjectId)) {
        projectIds.unshift(currentProjectId);
      }
      await createCommunity({
        name: communityName.trim(),
        description: communityDescription.trim(),
        project_ids: projectIds,
        created_by: currentUser?.username ?? undefined,
      });
      await refreshCommunities();
      setCommunityName("");
      setCommunityDescription("");
      setCommunityProjectIds("");
      setStatus({ type: "success", message: "Community created" });
    } catch {
      setStatus({ type: "error", message: "Failed to create community" });
    } finally {
      setBusy(false);
    }
  };

  const beginEditCommunity = (community: CommunityDTO) => {
    setEditingCommunityId(community.id);
    setEditCommunityName(community.name);
    setEditCommunityDescription(community.description ?? "");
    setEditCommunityProjectIds((community.project_ids ?? []).join(", "));
  };

  const cancelEditCommunity = () => {
    setEditingCommunityId(null);
  };

  const handleUpdateCommunity = async (communityId: string) => {
    if (!editCommunityName.trim()) {
      setStatus({ type: "error", message: "Community name is required" });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      await updateCommunity(communityId, {
        name: editCommunityName.trim(),
        description: editCommunityDescription.trim(),
        project_ids: parseCsv(editCommunityProjectIds),
      });
      await refreshCommunities();
      setEditingCommunityId(null);
      setStatus({ type: "success", message: "Community updated" });
    } catch {
      setStatus({ type: "error", message: "Failed to update community" });
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteCommunity = async (communityId: string) => {
    resetStatus();
    setBusy(true);
    try {
      await deleteCommunity(communityId);
      await refreshCommunities();
      setStatus({ type: "success", message: "Community deleted" });
    } catch {
      setStatus({ type: "error", message: "Failed to delete community" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top_left,rgba(178,38,76,0.18),transparent_45%),radial-gradient(circle_at_bottom_right,rgba(120,24,46,0.2),transparent_40%)] p-6 text-slate-200">
      <div className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">Projects</h2>
        <p className="text-sm text-slate-400">
          Create projects, add nodes, attach materials, and manage questions and communities.
        </p>
        {currentProject && (
          <div className="text-xs uppercase tracking-[0.24em] text-slate-500">
            Active project: {currentProject.name}
          </div>
        )}
      </div>

      {status.type !== "idle" && (
        <div
          className={`mb-6 rounded-lg border px-4 py-3 text-sm ${
            status.type === "error"
              ? "border-red-500/50 bg-red-500/10 text-red-200"
              : "border-emerald-500/50 bg-emerald-500/10 text-emerald-200"
          }`}
        >
          {status.message}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <SectionCard title="Projects" subtitle="Create, switch, and prune projects">
          <div className="grid gap-4">
            <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950 p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <input
                  value={projectName}
                  onChange={(event) => setProjectName(event.target.value)}
                  placeholder="Project name"
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <select
                  value={projectVisibility}
                  onChange={(event) =>
                    setProjectVisibility(event.target.value as "private" | "shared" | "public")
                  }
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                >
                  <option value="private">Private</option>
                  <option value="shared">Shared</option>
                  <option value="public">Public</option>
                </select>
              </div>
              <textarea
                value={projectDescription}
                onChange={(event) => setProjectDescription(event.target.value)}
                placeholder="Short project description"
                className="min-h-[80px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              />
              <button
                onClick={handleCreateProject}
                disabled={busy}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Add project
              </button>
            </div>

            <div className="grid gap-3">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className={`flex flex-wrap items-center justify-between gap-2 rounded-xl border px-4 py-3 text-sm transition ${
                    project.id === currentProjectId
                      ? "border-blue-500/60 bg-blue-500/10"
                      : "border-slate-800 bg-slate-950"
                  }`}
                >
                  <div>
                    <div className="font-semibold text-white">{project.name}</div>
                    <div className="text-xs text-slate-400">{project.description || "No description"}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setCurrentProjectId(project.id);
                        setCurrentProjectName(project.name);
                      }}
                      className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 transition hover:border-slate-500"
                    >
                      Use
                    </button>
                    <button
                      onClick={() => handleDeleteProject(project.id)}
                      disabled={busy}
                      className="rounded-lg border border-red-500/60 px-3 py-1.5 text-xs text-red-200 transition hover:border-red-400 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
              {projects.length === 0 && (
                <div className="rounded-lg border border-dashed border-slate-700 p-4 text-xs text-slate-500">
                  No projects yet. Create one to begin.
                </div>
              )}
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title="Nodes"
          subtitle="Add and review knowledge nodes in the active project"
        >
          {!currentProjectId && (
            <div className="text-sm text-slate-400">Select a project to add nodes.</div>
          )}
          {currentProjectId && (
            <div className="grid gap-4">
              <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950 p-4">
                <input
                  value={nodeTopic}
                  onChange={(event) => setNodeTopic(event.target.value)}
                  placeholder="Node topic"
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.1}
                    value={nodeImportance}
                    onChange={(event) => setNodeImportance(Number(event.target.value))}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                  />
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.1}
                    value={nodeRelevance}
                    onChange={(event) => setNodeRelevance(Number(event.target.value))}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <button
                  onClick={handleCreateNode}
                  disabled={busy}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Add node
                </button>
              </div>
              <div className="grid gap-2">
                {nodes.map((node) => (
                  <div
                    key={node.id}
                    className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200"
                  >
                    <div className="font-semibold text-sm text-white">{node.topic_name}</div>
                    <div className="text-slate-400">Importance: {node.importance.toFixed(2)}</div>
                  </div>
                ))}
                {nodes.length === 0 && (
                  <div className="rounded-lg border border-dashed border-slate-700 p-4 text-xs text-slate-500">
                    No nodes yet for this project.
                  </div>
                )}
              </div>
            </div>
          )}
        </SectionCard>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <SectionCard title="Questions" subtitle="Build a question bank for recall">
          {!currentProjectId && (
            <div className="text-sm text-slate-400">Select a project to manage questions.</div>
          )}
          {currentProjectId && (
            <div className="grid gap-4">
              <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950 p-4">
                <textarea
                  value={questionText}
                  onChange={(event) => setQuestionText(event.target.value)}
                  placeholder="Question prompt"
                  className="min-h-[80px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <textarea
                  value={questionAnswer}
                  onChange={(event) => setQuestionAnswer(event.target.value)}
                  placeholder="Answer"
                  className="min-h-[60px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  <select
                    value={questionType}
                    onChange={(event) => setQuestionType(event.target.value)}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="OPEN">Open</option>
                    <option value="FLASHCARD">Flashcard</option>
                    <option value="CLOZE">Cloze</option>
                    <option value="MCQ">Multiple choice</option>
                  </select>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={questionDifficulty}
                    onChange={(event) => setQuestionDifficulty(Number(event.target.value))}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                    placeholder="Difficulty"
                  />
                </div>
                <input
                  value={questionTags}
                  onChange={(event) => setQuestionTags(event.target.value)}
                  placeholder="Tags (comma separated)"
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <input
                  value={questionNodeIds}
                  onChange={(event) => setQuestionNodeIds(event.target.value)}
                  placeholder="Covered node ids (comma separated)"
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <button
                  onClick={handleCreateQuestion}
                  disabled={busy}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Add question
                </button>
              </div>
              <div className="grid gap-2">
                {questions.map((question) => {
                  const isEditing = editingQuestionId === question.id;
                  return (
                    <div
                      key={question.id}
                      className="rounded-lg border border-slate-800 bg-slate-950 p-3"
                    >
                      {isEditing ? (
                        <div className="grid gap-2">
                          <textarea
                            value={editQuestionText}
                            onChange={(event) => setEditQuestionText(event.target.value)}
                            className="min-h-[70px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                          />
                          <textarea
                            value={editQuestionAnswer}
                            onChange={(event) => setEditQuestionAnswer(event.target.value)}
                            className="min-h-[60px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                          />
                          <div className="grid gap-2 sm:grid-cols-2">
                            <select
                              value={editQuestionType}
                              onChange={(event) => setEditQuestionType(event.target.value)}
                              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                            >
                              <option value="OPEN">Open</option>
                              <option value="FLASHCARD">Flashcard</option>
                              <option value="CLOZE">Cloze</option>
                              <option value="MCQ">Multiple choice</option>
                            </select>
                            <input
                              type="number"
                              min={1}
                              max={5}
                              value={editQuestionDifficulty}
                              onChange={(event) => setEditQuestionDifficulty(Number(event.target.value))}
                              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                            />
                          </div>
                          <input
                            value={editQuestionTags}
                            onChange={(event) => setEditQuestionTags(event.target.value)}
                            placeholder="Tags (comma separated)"
                            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                          />
                          <input
                            value={editQuestionNodeIds}
                            onChange={(event) => setEditQuestionNodeIds(event.target.value)}
                            placeholder="Covered node ids"
                            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                          />
                          <div className="flex flex-wrap gap-2">
                            <button
                              onClick={() => handleUpdateQuestion(question.id)}
                              disabled={busy}
                              className="rounded-lg bg-blue-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              Save
                            </button>
                            <button
                              onClick={cancelEditQuestion}
                              disabled={busy}
                              className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="text-sm font-semibold text-white">{question.text}</div>
                          <div className="text-xs text-slate-400">Answer: {question.answer}</div>
                          <div className="mt-2 flex flex-wrap gap-2">
                            <button
                              onClick={() => beginEditQuestion(question)}
                              disabled={busy}
                              className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteQuestion(question.id)}
                              disabled={busy}
                              className="rounded-lg border border-red-500/60 px-3 py-1 text-xs text-red-200 transition hover:border-red-400 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              Delete
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
                {questions.length === 0 && (
                  <div className="rounded-lg border border-dashed border-slate-700 p-4 text-xs text-slate-500">
                    No questions yet for this project.
                  </div>
                )}
              </div>
            </div>
          )}
        </SectionCard>

        <SectionCard title="Materials" subtitle="Upload .txt notes or paste content">
          {!currentProjectId && (
            <div className="text-sm text-slate-400">Select a project to manage materials.</div>
          )}
          {currentProjectId && (
            <div className="grid gap-4">
              <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950 p-4">
                <input
                  value={materialTitle}
                  onChange={(event) => setMaterialTitle(event.target.value)}
                  placeholder="Material title"
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <textarea
                  value={materialText}
                  onChange={(event) => setMaterialText(event.target.value)}
                  placeholder="Paste notes or study material"
                  className="min-h-[100px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <button
                  onClick={handleCreateMaterial}
                  disabled={busy}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Add material
                </button>
              </div>

              <div className="grid gap-3 rounded-xl border border-dashed border-slate-700 bg-slate-950/60 p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">
                  Upload .txt files
                </div>
                <input
                  type="file"
                  accept=".txt,text/plain"
                  multiple
                  onChange={(event) => setMaterialFiles(event.target.files)}
                  className="text-sm text-slate-300"
                />
                <button
                  onClick={handleUploadMaterialFiles}
                  disabled={busy}
                  className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Upload files
                </button>
              </div>

              <div className="grid gap-2">
                {materials.map((material) => {
                  const isEditing = editingMaterialId === material.id;
                  const isEditingNodes = editingMaterialNodesId === material.id;
                  const linkedNodes = materialNodeMap.get(material.id) ?? [];
                  const searchValue = materialNodeSearch.trim().toLowerCase();
                  const filteredNodes = nodes.filter((node) => {
                    if (!searchValue) {
                      return true;
                    }
                    return (
                      node.topic_name.toLowerCase().includes(searchValue) ||
                      node.id.toLowerCase().includes(searchValue)
                    );
                  });
                  return (
                    <div
                      key={material.id}
                      className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2"
                    >
                      {isEditing ? (
                        <div className="grid gap-2">
                          <input
                            value={editMaterialTitle}
                            onChange={(event) => setEditMaterialTitle(event.target.value)}
                            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                          />
                          <textarea
                            value={editMaterialText}
                            onChange={(event) => setEditMaterialText(event.target.value)}
                            className="min-h-[90px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                          />
                          <div className="flex flex-wrap gap-2">
                            <button
                              onClick={() => handleUpdateMaterial(material.id)}
                              disabled={busy}
                              className="rounded-lg bg-blue-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              Save
                            </button>
                            <button
                              onClick={cancelEditMaterial}
                              disabled={busy}
                              className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="grid gap-3">
                          <div className="flex items-center justify-between gap-2">
                            <div>
                              <div className="text-sm font-semibold text-white">{material.title}</div>
                              <div className="text-xs text-slate-400">
                                {material.chunk_count} chunks
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => beginEditMaterial(material)}
                                disabled={busy}
                                className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteMaterial(material.id)}
                                disabled={busy}
                                className="rounded-lg border border-red-500/60 px-3 py-1 text-xs text-red-200 transition hover:border-red-400 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                Delete
                              </button>
                            </div>
                          </div>

                          <div className="flex flex-wrap items-center gap-2">
                            <div className="text-xs text-slate-500">Linked nodes:</div>
                            {linkedNodes.length === 0 && (
                              <div className="text-xs text-slate-400">None</div>
                            )}
                            {linkedNodes.map((node) => (
                              <span
                                key={node.id}
                                className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-200"
                              >
                                {node.topic_name}
                              </span>
                            ))}
                            <button
                              onClick={() => beginEditMaterialNodes(material)}
                              disabled={busy}
                              className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                              title="Edit linked nodes"
                            >
                              ✎
                            </button>
                          </div>

                          {isEditingNodes && (
                            <div className="grid gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                              <input
                                value={materialNodeSearch}
                                onChange={(event) => setMaterialNodeSearch(event.target.value)}
                                placeholder="Search nodes"
                                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                              />
                              <div className="max-h-40 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/80">
                                {filteredNodes.map((node) => {
                                  const isSelected = materialNodeSelection.includes(node.id);
                                  return (
                                    <button
                                      key={node.id}
                                      type="button"
                                      onClick={() => {
                                        setMaterialNodeSelection((prev) =>
                                          prev.includes(node.id)
                                            ? prev.filter((id) => id !== node.id)
                                            : [...prev, node.id]
                                        );
                                      }}
                                      className={`flex w-full items-center justify-between gap-3 border-b border-slate-800 px-3 py-2 text-left text-xs transition last:border-b-0 ${
                                        isSelected
                                          ? "bg-rose-600/20 text-rose-100"
                                          : "text-slate-200 hover:bg-slate-800/60"
                                      }`}
                                    >
                                      <span className="font-medium">{node.topic_name}</span>
                                      <span className="text-[10px] text-slate-500">{node.id}</span>
                                    </button>
                                  );
                                })}
                                {filteredNodes.length === 0 && (
                                  <div className="px-3 py-2 text-xs text-slate-500">
                                    No matching nodes.
                                  </div>
                                )}
                              </div>
                              <div className="flex flex-wrap gap-2">
                                <button
                                  onClick={() => handleSaveMaterialNodes(material.id)}
                                  disabled={busy}
                                  className="rounded-lg bg-blue-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  Save links
                                </button>
                                <button
                                  onClick={cancelEditMaterialNodes}
                                  disabled={busy}
                                  className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
                {materials.length === 0 && (
                  <div className="rounded-lg border border-dashed border-slate-700 p-4 text-xs text-slate-500">
                    No materials yet for this project.
                  </div>
                )}
              </div>
            </div>
          )}
        </SectionCard>

        <SectionCard title="Communities" subtitle="Group projects into shared spaces">
          <div className="grid gap-4">
            <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950 p-4">
              <input
                value={communityName}
                onChange={(event) => setCommunityName(event.target.value)}
                placeholder="Community name"
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              />
              <textarea
                value={communityDescription}
                onChange={(event) => setCommunityDescription(event.target.value)}
                placeholder="Community description"
                className="min-h-[70px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              />
              <input
                value={communityProjectIds}
                onChange={(event) => setCommunityProjectIds(event.target.value)}
                placeholder="Project ids (comma separated)"
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              />
              <button
                onClick={handleCreateCommunity}
                disabled={busy}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Add community
              </button>
            </div>

            <div className="grid gap-2">
              {communities.map((community) => {
                const isEditing = editingCommunityId === community.id;
                return (
                  <div
                    key={community.id}
                    className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2"
                  >
                    {isEditing ? (
                      <div className="grid gap-2">
                        <input
                          value={editCommunityName}
                          onChange={(event) => setEditCommunityName(event.target.value)}
                          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                        />
                        <textarea
                          value={editCommunityDescription}
                          onChange={(event) => setEditCommunityDescription(event.target.value)}
                          className="min-h-[70px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                        />
                        <input
                          value={editCommunityProjectIds}
                          onChange={(event) => setEditCommunityProjectIds(event.target.value)}
                          placeholder="Project ids (comma separated)"
                          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                        />
                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={() => handleUpdateCommunity(community.id)}
                            disabled={busy}
                            className="rounded-lg bg-blue-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Save
                          </button>
                          <button
                            onClick={cancelEditCommunity}
                            disabled={busy}
                            className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-sm font-semibold text-white">{community.name}</div>
                          <div className="text-xs text-slate-400">
                            {community.description || "No description"}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => beginEditCommunity(community)}
                            disabled={busy}
                            className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteCommunity(community.id)}
                            disabled={busy}
                            className="rounded-lg border border-red-500/60 px-3 py-1 text-xs text-red-200 transition hover:border-red-400 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
              {communities.length === 0 && (
                <div className="rounded-lg border border-dashed border-slate-700 p-4 text-xs text-slate-500">
                  No communities yet.
                </div>
              )}
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
