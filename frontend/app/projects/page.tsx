"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

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
  replaceQuestionNodes,
  suggestQuestionNodes,
  suggestQuestionNodesByText,
} from "@/lib/api/question";
import {
  listMaterials,
  checkYoutubeTranscript,
  createMaterial,
  deleteMaterial,
  fetchMaterial,
  updateMaterial,
  replaceMaterialNodes,
  suggestMaterialNodes,
  suggestMaterialNodesByText,
} from "@/lib/api/material";
import {
  listCommunities,
  createCommunity,
  deleteCommunity,
  updateCommunity,
} from "@/lib/api/community";
import { getCurrentUser } from "@/lib/api/user";
import GenerateQuestionsModal, {
  GenerateQuestionsButton,
} from "@/components/material/GenerateQuestionsModal";

type StatusState = {
  type: "idle" | "success" | "error";
  message: string;
};

type SuggestionItem = {
  node_id?: string | null;
  suggested_title?: string | null;
  suggested_description?: string | null;
  confidence: number;
  suggestion_type: "EXISTING" | "NEW" | string;
};

type ApiLikeError = {
  message?: string;
};

type MaterialSuggestionDraft = {
  notes: string;
  transcript: string;
};

type TranscriptSegment = {
  text: string;
  start?: number;
  duration?: number;
};

const formatTimestamp = (seconds: number) => {
  const totalSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remainingSeconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
  }
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
};

const formatTranscriptPreview = (segments: TranscriptSegment[] | null | undefined, fallbackText: string) => {
  const validSegments = (segments ?? []).filter((segment) => segment.text?.trim());
  if (validSegments.length === 0) {
    return fallbackText;
  }

  return validSegments
    .map((segment) => {
      const text = segment.text.trim();
      if (typeof segment.start === "number" && Number.isFinite(segment.start)) {
        return `[${formatTimestamp(segment.start)}] ${text}`;
      }
      return text;
    })
    .join("\n");
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

const isValidYoutubeUrl = (value: string) => {
  if (!value.trim()) {
    return true;
  }
  try {
    const parsed = new URL(value.trim());
    const host = parsed.hostname.toLowerCase();
    const path = parsed.pathname.replace(/^\/+/, "");

    if ((host === "youtu.be" || host === "www.youtu.be") && path.length > 0) {
      return true;
    }

    if (host === "youtube.com" || host === "www.youtube.com" || host === "m.youtube.com") {
      if (path === "watch" && parsed.searchParams.get("v")) {
        return true;
      }
      if (path.startsWith("shorts/") || path.startsWith("embed/")) {
        return true;
      }
    }

    return false;
  } catch {
    return false;
  }
};

const EMPTY_MCQ_OPTIONS = ["", "", "", ""];

const normalizeMcqOptions = (options: string[]) =>
  options.map((option) => option.trim()).filter(Boolean);

const toEditableMcqOptions = (options?: string[] | null) => {
  const normalized = normalizeMcqOptions(options ?? []);
  if (normalized.length >= 4) {
    return normalized;
  }
  return [...normalized, ...Array.from({ length: 4 - normalized.length }, () => "")];
};

const optionLabel = (index: number) => String.fromCharCode(65 + index);
const DRAFT_QUESTION_ID = "__create__";
const DRAFT_MATERIAL_ID = "__create_material__";
const SLIDER_HELP = {
  threshold:
    "Higher threshold = fewer, stricter matches. Lower threshold = more, broader matches.",
  semantic:
    "Higher semantic weight prioritizes meaning/context similarity. Lower semantic weight relies less on embeddings.",
  keyword:
    "Higher keyword weight prioritizes exact term overlap. Lower keyword weight emphasizes semantic similarity instead.",
  dedup:
    "Higher dedup threshold removes only near-duplicates. Lower dedup threshold merges more loosely similar suggestions.",
} as const;

const topNewSuggestionTitles = (weak: SuggestionItem[]) => {
  const newCandidates = weak
    .filter((item: SuggestionItem) => item.suggestion_type === "NEW" && item.suggested_title)
    .sort((a: SuggestionItem, b: SuggestionItem) => b.confidence - a.confidence);
  const newTopCount = Math.ceil(newCandidates.length * 0.5);
  return newCandidates
    .slice(0, newTopCount)
    .map((item: SuggestionItem) => (item.suggested_title as string).trim())
    .filter(Boolean);
};

const autoSelectExistingNodeIds = (
  strong: SuggestionItem[],
  weak: SuggestionItem[],
  threshold: number
) => {
  const minAutoSelectConfidence = Math.min(0.98, Math.max(0.85, threshold + 0.1));
  return [...strong, ...weak]
    .filter(
      (item: SuggestionItem) =>
        item.suggestion_type === "EXISTING" &&
        Boolean(item.node_id) &&
        Number(item.confidence) >= minAutoSelectConfidence
    )
    .sort((a: SuggestionItem, b: SuggestionItem) => b.confidence - a.confidence)
    .map((item: SuggestionItem) => item.node_id as string);
};

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
  const [questionMcqOptions, setQuestionMcqOptions] = useState<string[]>(EMPTY_MCQ_OPTIONS);
  const [questionCorrectOptionIndex, setQuestionCorrectOptionIndex] = useState(0);
  const [questionDifficulty, setQuestionDifficulty] = useState(1);
  const [questionTags, setQuestionTags] = useState("");
  const [isCreateQuestionNodesOpen, setIsCreateQuestionNodesOpen] = useState(false);
  const [createQuestionNodeSearch, setCreateQuestionNodeSearch] = useState("");
  const [createQuestionNodeSelection, setCreateQuestionNodeSelection] = useState<string[]>([]);
  const [createQuestionNewNodeSelection, setCreateQuestionNewNodeSelection] = useState<string[]>([]);
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [editQuestionText, setEditQuestionText] = useState("");
  const [editQuestionAnswer, setEditQuestionAnswer] = useState("");
  const [editQuestionType, setEditQuestionType] = useState("OPEN");
  const [editQuestionMcqOptions, setEditQuestionMcqOptions] = useState<string[]>(EMPTY_MCQ_OPTIONS);
  const [editQuestionCorrectOptionIndex, setEditQuestionCorrectOptionIndex] = useState(0);
  const [editQuestionDifficulty, setEditQuestionDifficulty] = useState(1);
  const [editQuestionTags, setEditQuestionTags] = useState("");
  const [editingQuestionNodesId, setEditingQuestionNodesId] = useState<string | null>(null);
  const [questionNodeSearch, setQuestionNodeSearch] = useState("");
  const [questionNodeSelection, setQuestionNodeSelection] = useState<string[]>([]);
  const [questionNewNodeSelection, setQuestionNewNodeSelection] = useState<string[]>([]);
  const [questionSuggestionLoading, setQuestionSuggestionLoading] = useState(false);
  const [questionSuggestionError, setQuestionSuggestionError] = useState<string | null>(null);
  const createQuestionTextRef = useRef<HTMLTextAreaElement | null>(null);
  const createQuestionAnswerRef = useRef<HTMLTextAreaElement | null>(null);
  const draftSuggestionRequestRef = useRef(0);
  const editSuggestionRequestRef = useRef(0);
  const [questionSuggestions, setQuestionSuggestions] = useState<{
    questionId: string | null;
    strong: SuggestionItem[];
    weak: SuggestionItem[];
  }>({ questionId: null, strong: [], weak: [] });

  const [materialTitle, setMaterialTitle] = useState("");
  const [materialText, setMaterialText] = useState("");
  const [materialSourceUrl, setMaterialSourceUrl] = useState("");
  const [questionGeneratorMaterial, setQuestionGeneratorMaterial] = useState<MaterialDTO | null>(null);
  const [materialCheckedTranscriptText, setMaterialCheckedTranscriptText] = useState<string | null>(null);
  const [materialCheckedTranscriptSegments, setMaterialCheckedTranscriptSegments] = useState<TranscriptSegment[]>([]);
  const [isCreateMaterialNodesOpen, setIsCreateMaterialNodesOpen] = useState(false);
  const [createMaterialNodeSearch, setCreateMaterialNodeSearch] = useState("");
  const [createMaterialNodeSelection, setCreateMaterialNodeSelection] = useState<string[]>([]);
  const [createMaterialNewNodeSelection, setCreateMaterialNewNodeSelection] = useState<string[]>([]);
  const [materialFiles, setMaterialFiles] = useState<FileList | null>(null);
  const [materialTranscriptStatus, setMaterialTranscriptStatus] = useState<string | null>(null);
  const [materialTranscriptChecking, setMaterialTranscriptChecking] = useState(false);
  const [editingMaterialId, setEditingMaterialId] = useState<string | null>(null);
  const [editMaterialTitle, setEditMaterialTitle] = useState("");
  const [editMaterialText, setEditMaterialText] = useState("");
  const [editMaterialSourceUrl, setEditMaterialSourceUrl] = useState("");
  const [editMaterialTranscriptText, setEditMaterialTranscriptText] = useState("");
  const [editMaterialCheckedTranscriptText, setEditMaterialCheckedTranscriptText] = useState<string | null>(null);
  const [editMaterialCheckedTranscriptSegments, setEditMaterialCheckedTranscriptSegments] = useState<TranscriptSegment[] | null>(null);
  const [editMaterialTranscriptStatus, setEditMaterialTranscriptStatus] = useState<string | null>(null);
  const [editMaterialTranscriptChecking, setEditMaterialTranscriptChecking] = useState(false);
  const [materialSuggestionDrafts, setMaterialSuggestionDrafts] = useState<Record<string, MaterialSuggestionDraft>>({});
  const [editingMaterialNodesId, setEditingMaterialNodesId] = useState<string | null>(null);
  const [materialNodeSearch, setMaterialNodeSearch] = useState("");
  const [materialNodeSelection, setMaterialNodeSelection] = useState<string[]>([]);
  const [materialNewNodeSelection, setMaterialNewNodeSelection] = useState<string[]>([]);
  const [suggestionThreshold, setSuggestionThreshold] = useState(0.75);
  const [semanticWeight, setSemanticWeight] = useState(0.6);
  const [keywordWeight, setKeywordWeight] = useState(0.4);
  const [dedupThreshold, setDedupThreshold] = useState(0.9);
  const [suggestionTopK] = useState(20);
  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);
  const [createMaterialSuggestionLoading, setCreateMaterialSuggestionLoading] = useState(false);
  const [createMaterialSuggestionError, setCreateMaterialSuggestionError] = useState<string | null>(null);
  const createMaterialSuggestionRequestRef = useRef(0);
  const [materialSuggestions, setMaterialSuggestions] = useState<{
    materialId: string | null;
    strong: SuggestionItem[];
    weak: SuggestionItem[];
  }>({ materialId: null, strong: [], weak: [] });

  const createMaterialLinkInvalid =
    Boolean(materialSourceUrl.trim()) && !isValidYoutubeUrl(materialSourceUrl);
  const editMaterialLinkInvalid =
    Boolean(editMaterialSourceUrl.trim()) && !isValidYoutubeUrl(editMaterialSourceUrl);
  const createTranscriptPreview = formatTranscriptPreview(
    materialCheckedTranscriptSegments,
    materialCheckedTranscriptText ?? ""
  );
  const editTranscriptPreview = formatTranscriptPreview(
    editMaterialCheckedTranscriptSegments,
    editMaterialTranscriptText
  );

  const getErrorMessage = (error: unknown, fallback: string) => {
    if (error && typeof error === "object") {
      const candidate = (error as ApiLikeError).message;
      if (candidate) {
        return candidate;
      }
    }
    return fallback;
  };

  const updateMaterialSuggestionDraft = (materialId: string, updates: Partial<MaterialSuggestionDraft>) => {
    setMaterialSuggestionDrafts((prev) => {
      const existing = prev[materialId] ?? { notes: "", transcript: "" };
      return {
        ...prev,
        [materialId]: {
          ...existing,
          ...updates,
        },
      };
    });
  };

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

  const isQuestionMcq = questionType === "MCQ";
  const isEditQuestionMcq = editQuestionType === "MCQ";
  const createQuestionSearchValue = createQuestionNodeSearch.trim().toLowerCase();
  const createQuestionFilteredNodes = nodes.filter((node) => {
    if (!createQuestionSearchValue) {
      return true;
    }
    return (
      node.topic_name.toLowerCase().includes(createQuestionSearchValue) ||
      node.id.toLowerCase().includes(createQuestionSearchValue)
    );
  });
  const questionSearchValue = questionNodeSearch.trim().toLowerCase();
  const questionFilteredNodes = nodes.filter((node) => {
    if (!questionSearchValue) {
      return true;
    }
    return (
      node.topic_name.toLowerCase().includes(questionSearchValue) ||
      node.id.toLowerCase().includes(questionSearchValue)
    );
  });
  const createQuestionSuggestionData =
    questionSuggestions.questionId === DRAFT_QUESTION_ID
      ? questionSuggestions
      : { questionId: null, strong: [], weak: [] };
  const createQuestionStrongIds = new Set(
    createQuestionSuggestionData.strong
      .filter((item) => item.suggestion_type === "EXISTING" && item.node_id)
      .map((item) => item.node_id as string)
  );
  const createQuestionWeakIds = new Set(
    createQuestionSuggestionData.weak
      .filter((item) => item.suggestion_type === "EXISTING" && item.node_id)
      .map((item) => item.node_id as string)
  );
  const createQuestionNewSuggestions = createQuestionSuggestionData.weak.filter(
    (item) => item.suggestion_type === "NEW"
  );

  const createMaterialSearchValue = createMaterialNodeSearch.trim().toLowerCase();
  const createMaterialFilteredNodes = nodes.filter((node) => {
    if (!createMaterialSearchValue) {
      return true;
    }
    return (
      node.topic_name.toLowerCase().includes(createMaterialSearchValue) ||
      node.id.toLowerCase().includes(createMaterialSearchValue)
    );
  });
  const createMaterialSuggestionData =
    materialSuggestions.materialId === DRAFT_MATERIAL_ID
      ? materialSuggestions
      : { materialId: null, strong: [], weak: [] };
  const createMaterialStrongIds = new Set(
    createMaterialSuggestionData.strong
      .filter((item) => item.suggestion_type === "EXISTING" && item.node_id)
      .map((item) => item.node_id as string)
  );
  const createMaterialWeakIds = new Set(
    createMaterialSuggestionData.weak
      .filter((item) => item.suggestion_type === "EXISTING" && item.node_id)
      .map((item) => item.node_id as string)
  );
  const createMaterialNewSuggestions = createMaterialSuggestionData.weak.filter(
    (item) => item.suggestion_type === "NEW"
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

  const nodeLookup = useMemo(() => {
    return new Map(nodes.map((node) => [node.id, node]));
  }, [nodes]);

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
    setNodes(nodeData.filter((node) => !node.id.startsWith("material:")));
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
    const trimmedQuestionText = questionText.trim();
    if (!trimmedQuestionText) {
      setStatus({
        type: "error",
        message: "Question text is required",
      });
      return;
    }

    const normalizedOptions = normalizeMcqOptions(questionMcqOptions);
    const selectedCorrectOption = questionMcqOptions[questionCorrectOptionIndex]?.trim() ?? "";
    const payloadAnswer = isQuestionMcq ? selectedCorrectOption : questionAnswer.trim();

    if (isQuestionMcq) {
      if (normalizedOptions.length < 2) {
        setStatus({
          type: "error",
          message: "MCQ requires at least 2 non-empty options",
        });
        return;
      }
      if (!selectedCorrectOption) {
        setStatus({
          type: "error",
          message: "Select a non-empty correct option",
        });
        return;
      }
    } else if (!payloadAnswer) {
      setStatus({
        type: "error",
        message: "Answer is required",
      });
      return;
    }

    resetStatus();
    setBusy(true);
    try {
      const createdQuestion = await createQuestion({
        project_id: currentProjectId,
        text: trimmedQuestionText,
        answer: payloadAnswer,
        options: isQuestionMcq ? normalizedOptions : undefined,
        question_type: questionType,
        difficulty: questionDifficulty,
        tags: parseCsv(questionTags),
        covered_node_ids: createQuestionNodeSelection,
        created_by: currentUser?.username ?? undefined,
      });
      if (createQuestionNewNodeSelection.length > 0) {
        const newNodes = createQuestionNewNodeSelection.map((title) => ({ title }));
        await replaceQuestionNodes(createdQuestion.id, createQuestionNodeSelection, newNodes);
      }
      await refreshProjectData(currentProjectId);
      setQuestionText("");
      setQuestionAnswer("");
      setQuestionMcqOptions(EMPTY_MCQ_OPTIONS);
      setQuestionCorrectOptionIndex(0);
      setQuestionTags("");
      setCreateQuestionNodeSelection([]);
      setCreateQuestionNodeSearch("");
      setCreateQuestionNewNodeSelection([]);
      setQuestionSuggestionError(null);
      setQuestionSuggestions({ questionId: null, strong: [], weak: [] });
      setIsCreateQuestionNodesOpen(false);
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
    const nextType = question.question_type ?? "OPEN";
    const editableOptions = toEditableMcqOptions(question.options);
    const matchingAnswerIndex = editableOptions.findIndex(
      (option) => option.trim() === (question.answer ?? "").trim()
    );
    setEditingQuestionId(question.id);
    setEditQuestionText(question.text);
    setEditQuestionAnswer(question.answer);
    setEditQuestionType(nextType);
    setEditQuestionMcqOptions(editableOptions);
    setEditQuestionCorrectOptionIndex(matchingAnswerIndex >= 0 ? matchingAnswerIndex : 0);
    setEditQuestionDifficulty(question.difficulty ?? 1);
    setEditQuestionTags((question.tags ?? []).join(", "));
  };

  const cancelEditQuestion = () => {
    setEditingQuestionId(null);
  };

  const beginEditQuestionNodes = (question: QuestionDTO) => {
    setIsCreateQuestionNodesOpen(false);
    setEditingQuestionNodesId(question.id);
    setQuestionNodeSelection(question.covered_node_ids ?? []);
    setQuestionNewNodeSelection([]);
    setQuestionNodeSearch("");
    setQuestionSuggestionError(null);
    setQuestionSuggestions({ questionId: question.id, strong: [], weak: [] });
  };

  const cancelEditQuestionNodes = () => {
    setEditingQuestionNodesId(null);
    setQuestionNodeSelection([]);
    setQuestionNewNodeSelection([]);
    setQuestionNodeSearch("");
    setQuestionSuggestionError(null);
    setQuestionSuggestions({ questionId: null, strong: [], weak: [] });
  };

  const handleAddNodeFromQuestionSearch = async () => {
    if (!currentProjectId) {
      return;
    }
    const value = questionNodeSearch.trim();
    if (!value) {
      return;
    }
    setBusy(true);
    setQuestionSuggestionError(null);
    try {
      const created = await createNode(currentProjectId, value, 0, 0.6);
      setNodes((prev) => [created, ...prev]);
      setQuestionNodeSelection((prev) =>
        prev.includes(created.id) ? prev : [...prev, created.id]
      );
      setQuestionNodeSearch("");
    } catch {
      setQuestionSuggestionError("Failed to add node");
    } finally {
      setBusy(false);
    }
  };

  const handleAddNodeFromCreateQuestionSearch = async () => {
    if (!currentProjectId) {
      return;
    }
    const value = createQuestionNodeSearch.trim();
    if (!value) {
      return;
    }
    setBusy(true);
    setQuestionSuggestionError(null);
    try {
      const created = await createNode(currentProjectId, value, 0, 0.6);
      setNodes((prev) => [created, ...prev]);
      setCreateQuestionNodeSelection((prev) =>
        prev.includes(created.id) ? prev : [...prev, created.id]
      );
      setCreateQuestionNodeSearch("");
    } catch {
      setQuestionSuggestionError("Failed to add node");
    } finally {
      setBusy(false);
    }
  };

  const handleSuggestQuestionNodes = async (questionId: string) => {
    if (!currentProjectId) {
      return;
    }
    setQuestionSuggestionError(null);
    setQuestionSuggestionLoading(true);
    const requestId = editSuggestionRequestRef.current + 1;
    editSuggestionRequestRef.current = requestId;
    const priorSelection = new Set(questionNodeSelection);
    try {
      const response = await suggestQuestionNodes(questionId, {
        project_id: currentProjectId,
        threshold: suggestionThreshold,
        semantic_weight: semanticWeight,
        keyword_weight: keywordWeight,
        dedup_threshold: dedupThreshold,
        top_k: suggestionTopK,
      });
      if (requestId !== editSuggestionRequestRef.current || editingQuestionNodesId !== questionId) {
        return;
      }
      setQuestionSuggestions({ questionId, strong: response.strong, weak: response.weak });
      const newTopTitles = topNewSuggestionTitles(response.weak);

      const topNodeIds = autoSelectExistingNodeIds(
        response.strong,
        response.weak,
        suggestionThreshold
      );
      const mergedSelection = new Set(priorSelection);
      topNodeIds.forEach((nodeId) => mergedSelection.add(nodeId));
      setQuestionNodeSelection(Array.from(mergedSelection));
      setQuestionNewNodeSelection(newTopTitles);
    } catch {
      if (requestId !== editSuggestionRequestRef.current || editingQuestionNodesId !== questionId) {
        return;
      }
      setQuestionSuggestionError("Failed to fetch suggestions");
    } finally {
      if (requestId === editSuggestionRequestRef.current) {
        setQuestionSuggestionLoading(false);
      }
    }
  };

  const handleSuggestDraftQuestionNodes = async () => {
    if (!currentProjectId) {
      return;
    }

    const currentQuestionText = (createQuestionTextRef.current?.value ?? questionText).trim();
    let text = "";

    if (isQuestionMcq) {
      const options = questionMcqOptions.map((option) => option.trim()).filter(Boolean);
      const selectedCorrectOption = questionMcqOptions[questionCorrectOptionIndex]?.trim() ?? "";
      const parts = [currentQuestionText];
      if (options.length > 0) {
        parts.push(
          `Options:\n${options.map((option, index) => `${optionLabel(index)}. ${option}`).join("\n")}`
        );
      }
      if (selectedCorrectOption) {
        parts.push(`Correct option: ${selectedCorrectOption}`);
      }
      text = parts.filter(Boolean).join("\n\n").trim();
    } else {
      const currentAnswerText = (createQuestionAnswerRef.current?.value ?? questionAnswer).trim();
      text = `${currentQuestionText}\n\n${currentAnswerText}`.trim();
    }

    if (!text) {
      setQuestionSuggestionError("Enter question text (and answer) before suggesting nodes");
      return;
    }

    const requestId = draftSuggestionRequestRef.current + 1;
    draftSuggestionRequestRef.current = requestId;

    setQuestionSuggestionError(null);
    setQuestionSuggestionLoading(true);
    setQuestionSuggestions({ questionId: DRAFT_QUESTION_ID, strong: [], weak: [] });
    try {
      const response = await suggestQuestionNodesByText({
        project_id: currentProjectId,
        text,
        threshold: suggestionThreshold,
        semantic_weight: semanticWeight,
        keyword_weight: keywordWeight,
        dedup_threshold: dedupThreshold,
        top_k: suggestionTopK,
      });
      if (requestId !== draftSuggestionRequestRef.current) {
        return;
      }
      setQuestionSuggestions({ questionId: DRAFT_QUESTION_ID, strong: response.strong, weak: response.weak });

      const topNodeIds = autoSelectExistingNodeIds(
        response.strong,
        response.weak,
        suggestionThreshold
      );
      setCreateQuestionNodeSelection(Array.from(new Set(topNodeIds)));
      setCreateQuestionNewNodeSelection(topNewSuggestionTitles(response.weak));
    } catch {
      if (requestId !== draftSuggestionRequestRef.current) {
        return;
      }
      setQuestionSuggestionError("Failed to suggest nodes for new question");
    } finally {
      if (requestId === draftSuggestionRequestRef.current) {
        setQuestionSuggestionLoading(false);
      }
    }
  };

  const handleSaveQuestionNodes = async (questionId: string) => {
    if (!currentProjectId) {
      return;
    }
    setBusy(true);
    setQuestionSuggestionError(null);
    try {
      const newNodes = questionNewNodeSelection.map((title) => ({ title }));
      await replaceQuestionNodes(questionId, questionNodeSelection, newNodes);
      await refreshProjectData(currentProjectId);
      setEditingQuestionNodesId(null);
      setQuestionNewNodeSelection([]);
      setStatus({ type: "success", message: "Question links updated" });
    } catch {
      setStatus({ type: "error", message: "Failed to update question links" });
    } finally {
      setBusy(false);
    }
  };

  const handleUpdateQuestion = async (questionId: string) => {
    if (!currentProjectId) {
      return;
    }
    const trimmedQuestionText = editQuestionText.trim();
    if (!trimmedQuestionText) {
      setStatus({
        type: "error",
        message: "Question text is required",
      });
      return;
    }

    const normalizedOptions = normalizeMcqOptions(editQuestionMcqOptions);
    const selectedCorrectOption =
      editQuestionMcqOptions[editQuestionCorrectOptionIndex]?.trim() ?? "";
    const payloadAnswer = isEditQuestionMcq ? selectedCorrectOption : editQuestionAnswer.trim();

    if (isEditQuestionMcq) {
      if (normalizedOptions.length < 2) {
        setStatus({
          type: "error",
          message: "MCQ requires at least 2 non-empty options",
        });
        return;
      }
      if (!selectedCorrectOption) {
        setStatus({
          type: "error",
          message: "Select a non-empty correct option",
        });
        return;
      }
    } else if (!payloadAnswer) {
      setStatus({
        type: "error",
        message: "Answer is required",
      });
      return;
    }

    resetStatus();
    setBusy(true);
    try {
      await updateQuestion(questionId, {
        text: trimmedQuestionText,
        answer: payloadAnswer,
        options: isEditQuestionMcq ? normalizedOptions : [],
        question_type: editQuestionType,
        difficulty: editQuestionDifficulty,
        tags: parseCsv(editQuestionTags),
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
    if (!materialTitle.trim() || (!materialText.trim() && !materialSourceUrl.trim())) {
      setStatus({
        type: "error",
        message: "Material title and either text or a YouTube link are required",
      });
      return;
    }
    if (materialSourceUrl.trim() && !isValidYoutubeUrl(materialSourceUrl)) {
      setStatus({
        type: "error",
        message: "Please enter a valid YouTube link",
      });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      const created = await createMaterial(
        currentProjectId,
        materialTitle.trim(),
        materialText.trim(),
        currentUser?.username ?? undefined,
        materialSourceUrl.trim() || undefined,
        materialCheckedTranscriptText ?? undefined,
        materialCheckedTranscriptSegments
      );
      if (createMaterialNodeSelection.length > 0 || createMaterialNewNodeSelection.length > 0) {
        const newNodes = createMaterialNewNodeSelection.map((title) => ({ title }));
        await replaceMaterialNodes(created.id, createMaterialNodeSelection, newNodes);
      }
      await refreshProjectData(currentProjectId);
      setMaterialTitle("");
      setMaterialText("");
      setMaterialSourceUrl("");
      setMaterialCheckedTranscriptText(null);
      setMaterialCheckedTranscriptSegments([]);
      setMaterialTranscriptStatus(null);
      setCreateMaterialNodeSelection([]);
      setCreateMaterialNewNodeSelection([]);
      setCreateMaterialNodeSearch("");
      setCreateMaterialSuggestionError(null);
      setMaterialSuggestions({ materialId: null, strong: [], weak: [] });
      setIsCreateMaterialNodesOpen(false);
      if (created.imported_from_youtube) {
        setStatus({
          type: "success",
          message: `Material imported from YouTube transcript (${created.transcript_chunk_count ?? 0} chunks)`,
        });
      } else {
        setStatus({ type: "success", message: "Material created" });
      }
    } catch (error) {
      setStatus({
        type: "error",
        message: getErrorMessage(error, "Failed to create material"),
      });
    } finally {
      setBusy(false);
    }
  };

  const handleCheckMaterialTranscript = async () => {
    if (!materialSourceUrl.trim()) {
      setMaterialTranscriptStatus("Unable to fetch transcript.");
      return;
    }
    if (!isValidYoutubeUrl(materialSourceUrl)) {
      setMaterialTranscriptStatus("Unable to fetch transcript.");
      return;
    }

    setMaterialTranscriptChecking(true);
    setMaterialTranscriptStatus(null);
    try {
      const result = await checkYoutubeTranscript(materialSourceUrl.trim());
      setMaterialCheckedTranscriptText(result.transcript_text?.trim() || "");
      setMaterialCheckedTranscriptSegments(result.segments ?? []);
      setMaterialTranscriptStatus(
        `Transcript found for video ${result.video_id ?? "unknown"} (${result.chunk_count} chunks). It will be saved when you click Create material.`
      );
    } catch (error) {
      setMaterialCheckedTranscriptText(null);
      setMaterialCheckedTranscriptSegments([]);
      setMaterialTranscriptStatus("Unable to fetch transcript.");
    } finally {
      setMaterialTranscriptChecking(false);
    }
  };

  const handleAddNodeFromCreateMaterialSearch = async () => {
    if (!currentProjectId) {
      return;
    }
    const value = createMaterialNodeSearch.trim();
    if (!value) {
      return;
    }
    setBusy(true);
    setCreateMaterialSuggestionError(null);
    try {
      const created = await createNode(currentProjectId, value, 0, 0.6);
      setNodes((prev) => [created, ...prev]);
      setCreateMaterialNodeSelection((prev) =>
        prev.includes(created.id) ? prev : [...prev, created.id]
      );
      setCreateMaterialNodeSearch("");
    } catch {
      setCreateMaterialSuggestionError("Failed to add node");
    } finally {
      setBusy(false);
    }
  };

  const handleSuggestDraftMaterialNodes = async () => {
    if (!currentProjectId) {
      return;
    }

    const notesText = materialText.trim();
    const sourceUrl = materialSourceUrl.trim();
    const textParts: string[] = [];

    if (notesText) {
      textParts.push(notesText);
    }

    if (materialCheckedTranscriptText?.trim()) {
      textParts.push(materialCheckedTranscriptText.trim());
    }

    if (sourceUrl && isValidYoutubeUrl(sourceUrl)) {
      if (!materialCheckedTranscriptText?.trim()) {
        try {
          const transcriptResult = await checkYoutubeTranscript(sourceUrl);
          if (transcriptResult.transcript_text?.trim()) {
            textParts.push(transcriptResult.transcript_text.trim());
          }
        } catch {
          if (!notesText) {
            setCreateMaterialSuggestionError("Transcript unavailable and notes are empty.");
            return;
          }
        }
      }
    }

    const text = textParts.join("\n\n").trim();
    if (!text) {
      setCreateMaterialSuggestionError("Enter notes and/or a valid YouTube link with transcript before suggesting nodes");
      return;
    }

    const requestId = createMaterialSuggestionRequestRef.current + 1;
    createMaterialSuggestionRequestRef.current = requestId;

    setCreateMaterialSuggestionError(null);
    setCreateMaterialSuggestionLoading(true);
    setMaterialSuggestions({ materialId: DRAFT_MATERIAL_ID, strong: [], weak: [] });

    try {
      const response = await suggestMaterialNodesByText({
        project_id: currentProjectId,
        text,
        threshold: suggestionThreshold,
        semantic_weight: semanticWeight,
        keyword_weight: keywordWeight,
        dedup_threshold: dedupThreshold,
        top_k: suggestionTopK,
      });
      if (requestId !== createMaterialSuggestionRequestRef.current) {
        return;
      }

      setMaterialSuggestions({ materialId: DRAFT_MATERIAL_ID, strong: response.strong, weak: response.weak });

      const existingSuggestions = [...response.strong, ...response.weak]
        .filter((item: SuggestionItem) => item.suggestion_type === "EXISTING" && item.node_id)
        .sort((a: SuggestionItem, b: SuggestionItem) => b.confidence - a.confidence);
      const topCount = Math.ceil(existingSuggestions.length * 0.5);
      const topNodeIds = existingSuggestions
        .slice(0, topCount)
        .map((item: SuggestionItem) => item.node_id as string);
      setCreateMaterialNodeSelection(Array.from(new Set(topNodeIds)));
      setCreateMaterialNewNodeSelection(topNewSuggestionTitles(response.weak));
    } catch (error) {
      if (requestId !== createMaterialSuggestionRequestRef.current) {
        return;
      }
      setCreateMaterialSuggestionError(
        getErrorMessage(error, "Failed to suggest nodes for new material")
      );
    } finally {
      if (requestId === createMaterialSuggestionRequestRef.current) {
        setCreateMaterialSuggestionLoading(false);
      }
    }
  };

  const loadEditMaterialTranscript = async (link: string) => {
    const trimmed = link.trim();
    if (!trimmed) {
      setEditMaterialCheckedTranscriptText(null);
      setEditMaterialTranscriptText("");
      setEditMaterialTranscriptStatus("No source link attached to this material.");
      return;
    }
    if (!isValidYoutubeUrl(trimmed)) {
      setEditMaterialCheckedTranscriptText(null);
      setEditMaterialTranscriptText("");
      setEditMaterialTranscriptStatus("Transcript preview is available only for valid YouTube links.");
      return;
    }

    setEditMaterialTranscriptChecking(true);
    setEditMaterialTranscriptStatus(null);
    try {
      const result = await checkYoutubeTranscript(trimmed);
      const transcript = result.transcript_text?.trim() ?? "";
      setEditMaterialTranscriptText(transcript);
      setEditMaterialCheckedTranscriptText(transcript);
      setEditMaterialCheckedTranscriptSegments(result.segments ?? []);
      if (editingMaterialId) {
        updateMaterialSuggestionDraft(editingMaterialId, { transcript });
      }
      setEditMaterialTranscriptStatus(
        `Transcript found for video ${result.video_id ?? "unknown"} (${result.chunk_count} chunks). Save to persist changes.`
      );
    } catch (error) {
      setEditMaterialCheckedTranscriptText(null);
      setEditMaterialCheckedTranscriptSegments(null);
      setEditMaterialTranscriptText("");
      setEditMaterialTranscriptStatus("Unable to fetch transcript.");
    } finally {
      setEditMaterialTranscriptChecking(false);
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
      const sourceUrl = fullMaterial.source_url ?? material.source_url ?? "";
      setEditMaterialSourceUrl(sourceUrl);
      const persistedTranscript = fullMaterial.transcript_text?.trim() ?? "";
      setEditMaterialTranscriptText(persistedTranscript);
      setEditMaterialCheckedTranscriptText(null);
      setEditMaterialCheckedTranscriptSegments(fullMaterial.transcript_segments ?? null);
      updateMaterialSuggestionDraft(material.id, {
        notes: fullMaterial.chunks.join("\n\n"),
        transcript: persistedTranscript,
      });
      setEditMaterialTranscriptStatus(
        persistedTranscript
          ? `Transcript loaded from saved material (${fullMaterial.transcript_chunks?.length ?? 0} chunks).`
          : sourceUrl
            ? "No saved transcript for this material. Use Check transcript, then Save."
            : "No source link attached to this material."
      );
    } catch {
      setStatus({ type: "error", message: "Failed to load material" });
    } finally {
      setBusy(false);
    }
  };

  const cancelEditMaterial = () => {
    setEditingMaterialId(null);
    setEditMaterialSourceUrl("");
    setEditMaterialTranscriptText("");
    setEditMaterialCheckedTranscriptText(null);
    setEditMaterialCheckedTranscriptSegments(null);
    setEditMaterialTranscriptStatus(null);
    setEditMaterialTranscriptChecking(false);
  };

  const beginEditMaterialNodes = (material: MaterialDTO) => {
    const linked = materialNodeMap.get(material.id) ?? [];
    setEditingMaterialNodesId(material.id);
    setMaterialNodeSelection(linked.map((node) => node.id));
    setMaterialNewNodeSelection([]);
    setMaterialNodeSearch("");
    setSuggestionError(null);
    setMaterialSuggestions({ materialId: material.id, strong: [], weak: [] });
  };

  const cancelEditMaterialNodes = () => {
    setEditingMaterialNodesId(null);
    setMaterialNodeSelection([]);
    setMaterialNewNodeSelection([]);
    setMaterialNodeSearch("");
    setSuggestionError(null);
    setMaterialSuggestions({ materialId: null, strong: [], weak: [] });
  };

  const handleSaveMaterialNodes = async (materialId: string) => {
    if (!currentProjectId) {
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      const newNodes = materialNewNodeSelection.map((title) => ({ title }));
      await replaceMaterialNodes(materialId, materialNodeSelection, newNodes);
      await refreshProjectData(currentProjectId);
      setEditingMaterialNodesId(null);
      setMaterialNewNodeSelection([]);
      setStatus({ type: "success", message: "Material links updated" });
    } catch {
      setStatus({ type: "error", message: "Failed to update material links" });
    } finally {
      setBusy(false);
    }
  };

  const handleSuggestMaterialNodes = async (materialId: string) => {
    if (!currentProjectId) {
      return;
    }
    resetStatus();
    setSuggestionError(null);
    setSuggestionLoading(true);
    const priorSelection = new Set(materialNodeSelection);
    try {
      const draft = materialSuggestionDrafts[materialId];
      const draftText = [draft?.notes?.trim() ?? "", draft?.transcript?.trim() ?? ""]
        .filter(Boolean)
        .join("\n\n");
      const response = draftText
        ? await suggestMaterialNodesByText({
            project_id: currentProjectId,
            text: draftText,
            threshold: suggestionThreshold,
            semantic_weight: semanticWeight,
            keyword_weight: keywordWeight,
            dedup_threshold: dedupThreshold,
            top_k: suggestionTopK,
          })
        : await suggestMaterialNodes(materialId, {
            project_id: currentProjectId,
            threshold: suggestionThreshold,
            semantic_weight: semanticWeight,
            keyword_weight: keywordWeight,
            dedup_threshold: dedupThreshold,
            top_k: suggestionTopK,
          });
      setMaterialSuggestions({ materialId, strong: response.strong, weak: response.weak });
      const newCandidates = response.weak
        .filter((item: SuggestionItem) => item.suggestion_type === "NEW" && item.suggested_title)
        .sort((a: SuggestionItem, b: SuggestionItem) => b.confidence - a.confidence);
      const newTopCount = Math.ceil(newCandidates.length * 0.5);
      const newTopTitles = newCandidates
        .slice(0, newTopCount)
        .map((item: SuggestionItem) => (item.suggested_title as string).trim())
        .filter(Boolean);
      const existingSuggestions = [...response.strong, ...response.weak]
        .filter((item: SuggestionItem) => item.suggestion_type === "EXISTING" && item.node_id)
        .sort((a: SuggestionItem, b: SuggestionItem) => b.confidence - a.confidence);
      const topCount = Math.ceil(existingSuggestions.length * 0.5);
      const topNodeIds = existingSuggestions
        .slice(0, topCount)
        .map((item: SuggestionItem) => item.node_id as string);
      const mergedSelection = new Set(priorSelection);
      topNodeIds.forEach((nodeId) => mergedSelection.add(nodeId));
      setMaterialNodeSelection(Array.from(mergedSelection));
      setMaterialNewNodeSelection(newTopTitles);
    } catch {
      setSuggestionError("Failed to fetch suggestions");
    } finally {
      setSuggestionLoading(false);
    }
  };

  const handleAddNodeFromMaterialSearch = async () => {
    if (!currentProjectId) {
      return;
    }
    const value = materialNodeSearch.trim();
    if (!value) {
      return;
    }
    setBusy(true);
    setSuggestionError(null);
    try {
      const created = await createNode(currentProjectId, value, 0, 0.6);
      setNodes((prev) => [created, ...prev]);
      setMaterialNodeSelection((prev) =>
        prev.includes(created.id) ? prev : [...prev, created.id]
      );
      setMaterialNodeSearch("");
    } catch {
      setSuggestionError("Failed to add node");
    } finally {
      setBusy(false);
    }
  };

  const handleUpdateMaterial = async (materialId: string) => {
    if (!currentProjectId) {
      return;
    }
    if (!editMaterialTitle.trim()) {
      setStatus({
        type: "error",
        message: "Material title is required",
      });
      return;
    }
    if (editMaterialSourceUrl.trim() && !isValidYoutubeUrl(editMaterialSourceUrl)) {
      setStatus({
        type: "error",
        message: "Please enter a valid YouTube link",
      });
      return;
    }
    resetStatus();
    setBusy(true);
    try {
      await updateMaterial(materialId, {
        title: editMaterialTitle.trim(),
        content_text: editMaterialText,
        source_url: editMaterialSourceUrl.trim() || undefined,
        transcript_text: !editMaterialSourceUrl.trim()
          ? ""
          : editMaterialCheckedTranscriptText ?? undefined,
        transcript_segments: !editMaterialSourceUrl.trim()
          ? []
          : editMaterialCheckedTranscriptSegments ?? undefined,
      });
      setMaterialSuggestionDrafts((prev) => {
        const next = { ...prev };
        delete next[materialId];
        return next;
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
              <div className="grid min-w-0 gap-2">
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
                  ref={createQuestionTextRef}
                  value={questionText}
                  onChange={(event) => setQuestionText(event.target.value)}
                  placeholder="Question prompt"
                  className="min-h-[80px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  <select
                    value={questionType}
                    onChange={(event) => {
                      setQuestionType(event.target.value);
                      setQuestionCorrectOptionIndex(0);
                    }}
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
                {isQuestionMcq ? (
                  <div className="grid gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <div className="text-xs font-semibold text-slate-200">Multiple choice options</div>
                    {questionMcqOptions.map((option, index) => (
                      <div key={`create-option-${index}`} className="grid grid-cols-[auto_1fr] items-center gap-2">
                        <label className="flex items-center gap-1 text-xs text-slate-300">
                          <input
                            type="radio"
                            name="create-correct-option"
                            checked={questionCorrectOptionIndex === index}
                            onChange={() => setQuestionCorrectOptionIndex(index)}
                            className="h-3.5 w-3.5"
                          />
                          {optionLabel(index)}
                        </label>
                        <input
                          value={option}
                          onChange={(event) =>
                            setQuestionMcqOptions((prev) => {
                              const next = [...prev];
                              next[index] = event.target.value;
                              return next;
                            })
                          }
                          placeholder={`Option ${optionLabel(index)}`}
                          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                        />
                      </div>
                    ))}
                    <div className="text-[11px] text-slate-400">
                      Select the radio button for the correct option.
                    </div>
                  </div>
                ) : (
                  <textarea
                    ref={createQuestionAnswerRef}
                    value={questionAnswer}
                    onChange={(event) => setQuestionAnswer(event.target.value)}
                    placeholder={
                      questionType === "FLASHCARD"
                        ? "Flashcard back"
                        : questionType === "CLOZE"
                          ? "Expected completion"
                          : "Answer"
                    }
                    className="min-h-[60px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                  />
                )}
                <input
                  value={questionTags}
                  onChange={(event) => setQuestionTags(event.target.value)}
                  placeholder="Tags (comma separated)"
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingQuestionNodesId(null);
                      setQuestionSuggestionError(null);
                      setQuestionSuggestions({ questionId: null, strong: [], weak: [] });
                      setIsCreateQuestionNodesOpen((prev) => !prev);
                    }}
                    disabled={busy}
                    className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isCreateQuestionNodesOpen ? "Hide node picker" : "Add nodes"}
                  </button>
                  <div className="text-xs text-slate-400">
                    {createQuestionNodeSelection.length} node{createQuestionNodeSelection.length === 1 ? "" : "s"} selected
                  </div>
                </div>
                {isCreateQuestionNodesOpen && (
                  <div className="grid gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        onClick={handleSuggestDraftQuestionNodes}
                        disabled={busy || questionSuggestionLoading}
                        className="rounded-lg bg-rose-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {questionSuggestionLoading ? "Suggesting..." : "Suggest nodes"}
                      </button>
                      <div className="text-[11px] text-slate-400">
                        Adjust threshold + weights before suggesting.
                      </div>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label
                        className="grid gap-1 pr-2 text-[11px] text-slate-400"
                        title={SLIDER_HELP.threshold}
                      >
                        Threshold: {suggestionThreshold.toFixed(2)}
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.01}
                          value={suggestionThreshold}
                          onChange={(event) => setSuggestionThreshold(Number(event.target.value))}
                          className="w-[calc(100%-8px)] max-w-full"
                          title={SLIDER_HELP.threshold}
                        />
                      </label>
                      <label
                        className="grid gap-1 pr-2 text-[11px] text-slate-400"
                        title={SLIDER_HELP.semantic}
                      >
                        Semantic weight: {semanticWeight.toFixed(2)}
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.05}
                          value={semanticWeight}
                          onChange={(event) => setSemanticWeight(Number(event.target.value))}
                          className="w-[calc(100%-8px)] max-w-full"
                          title={SLIDER_HELP.semantic}
                        />
                      </label>
                      <label
                        className="grid gap-1 pr-2 text-[11px] text-slate-400"
                        title={SLIDER_HELP.keyword}
                      >
                        Keyword weight: {keywordWeight.toFixed(2)}
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.05}
                          value={keywordWeight}
                          onChange={(event) => setKeywordWeight(Number(event.target.value))}
                          className="w-[calc(100%-8px)] max-w-full"
                          title={SLIDER_HELP.keyword}
                        />
                      </label>
                      <label
                        className="grid gap-1 pr-2 text-[11px] text-slate-400"
                        title={SLIDER_HELP.dedup}
                      >
                        Dedup threshold: {dedupThreshold.toFixed(2)}
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.01}
                          value={dedupThreshold}
                          onChange={(event) => setDedupThreshold(Number(event.target.value))}
                          className="w-[calc(100%-8px)] max-w-full"
                          title={SLIDER_HELP.dedup}
                        />
                      </label>
                    </div>
                    {questionSuggestionError && (
                      <div className="text-xs text-red-300">{questionSuggestionError}</div>
                    )}
                    {createQuestionSuggestionData.strong.length > 0 && (
                      <div className="text-[11px] text-slate-400">
                        Strong suggestions preselected: {createQuestionSuggestionData.strong.length}
                      </div>
                    )}
                    {createQuestionNewSuggestions.length > 0 && (
                      <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                        New candidates (click to add):
                        <button
                          type="button"
                          onClick={() => {
                            const titles = createQuestionNewSuggestions
                              .map((item) => item.suggested_title?.trim())
                              .filter((title): title is string => Boolean(title));
                            setCreateQuestionNewNodeSelection(Array.from(new Set(titles)));
                          }}
                          className="rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-100 transition hover:border-amber-400"
                        >
                          Select all
                        </button>
                        {createQuestionNewSuggestions.map((item, index) => {
                          const title = item.suggested_title?.trim();
                          if (!title) {
                            return null;
                          }
                          const isSelected = createQuestionNewNodeSelection.includes(title);
                          return (
                            <button
                              key={`create-${title}-${index}`}
                              type="button"
                              onClick={() => {
                                setCreateQuestionNewNodeSelection((prev) =>
                                  prev.includes(title)
                                    ? prev.filter((entry) => entry !== title)
                                    : [...prev, title]
                                );
                              }}
                              className={`rounded-full border px-2 py-0.5 transition ${
                                isSelected
                                  ? "border-amber-400 bg-amber-500/20 text-amber-100"
                                  : "border-slate-700 bg-slate-900 text-slate-200 hover:border-slate-500"
                              }`}
                            >
                              {title}
                            </button>
                          );
                        })}
                      </div>
                    )}
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                      Selected nodes (click to toggle):
                      {createQuestionNodeSelection.map((nodeId) => {
                        const node = nodeLookup.get(nodeId);
                        const label = node?.topic_name ?? nodeId;
                        return (
                          <button
                            key={`create-selected-${nodeId}`}
                            type="button"
                            onClick={() => {
                              setCreateQuestionNodeSelection((prev) => prev.filter((id) => id !== nodeId));
                            }}
                            className="rounded-full border border-rose-400 bg-rose-500/20 px-2 py-0.5 text-rose-100 transition"
                          >
                            {label}
                          </button>
                        );
                      })}
                      {createQuestionNodeSelection.length === 0 && (
                        <span className="text-[11px] text-slate-500">None selected</span>
                      )}
                    </div>
                    <input
                      value={createQuestionNodeSearch}
                      onChange={(event) => setCreateQuestionNodeSearch(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && event.shiftKey) {
                          event.preventDefault();
                          handleAddNodeFromCreateQuestionSearch();
                        }
                      }}
                      placeholder="Search nodes"
                      className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                    />
                    {createQuestionNodeSearch.trim() &&
                      !nodes.some(
                        (node) => node.topic_name.toLowerCase() === createQuestionNodeSearch.trim().toLowerCase()
                      ) && (
                        <button
                          type="button"
                          onClick={handleAddNodeFromCreateQuestionSearch}
                          disabled={busy}
                          className="flex w-full items-center justify-between rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-left text-xs text-rose-100 transition hover:border-rose-400/70 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <span>Add "{createQuestionNodeSearch.trim()}"</span>
                          <span className="text-[10px] text-slate-400">Shift + Enter</span>
                        </button>
                      )}
                    <div className="max-h-40 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/80">
                      {createQuestionFilteredNodes.map((node) => {
                        const isSelected = createQuestionNodeSelection.includes(node.id);
                        const isStrongSuggested = createQuestionStrongIds.has(node.id);
                        const isWeakSuggested = createQuestionWeakIds.has(node.id);
                        return (
                          <button
                            key={`create-node-${node.id}`}
                            type="button"
                            onClick={() => {
                              setCreateQuestionNodeSelection((prev) =>
                                prev.includes(node.id)
                                  ? prev.filter((id) => id !== node.id)
                                  : [...prev, node.id]
                              );
                            }}
                            className={`flex w-full items-center justify-between gap-3 border-b border-slate-800 px-3 py-2 text-left text-xs transition last:border-b-0 ${
                              isSelected
                                ? "bg-rose-600/20 text-rose-100"
                                : isStrongSuggested
                                  ? "bg-rose-500/10 text-rose-100"
                                  : isWeakSuggested
                                    ? "bg-slate-800/60 text-slate-200"
                                    : "text-slate-200 hover:bg-slate-800/60"
                            }`}
                          >
                            <span className="font-medium">{node.topic_name}</span>
                            <span className="text-[10px] text-slate-500">{node.id}</span>
                          </button>
                        );
                      })}
                      {createQuestionFilteredNodes.length === 0 && (
                        <div className="px-3 py-2 text-xs text-slate-500">No matching nodes.</div>
                      )}
                    </div>
                  </div>
                )}
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
                  const isEditingNodes = editingQuestionNodesId === question.id;
                  const linkedNodes = nodes.filter((node) =>
                    (question.covered_node_ids ?? []).includes(node.id)
                  );
                  const questionSuggestionData =
                    questionSuggestions.questionId === question.id
                      ? questionSuggestions
                      : { questionId: null, strong: [], weak: [] };
                  const questionStrongIds = new Set(
                    questionSuggestionData.strong
                      .filter((item) => item.suggestion_type === "EXISTING" && item.node_id)
                      .map((item) => item.node_id as string)
                  );
                  const questionWeakIds = new Set(
                    questionSuggestionData.weak
                      .filter((item) => item.suggestion_type === "EXISTING" && item.node_id)
                      .map((item) => item.node_id as string)
                  );
                  const questionNewSuggestions = questionSuggestionData.weak.filter(
                    (item) => item.suggestion_type === "NEW"
                  );
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
                            placeholder={
                              editQuestionType === "FLASHCARD"
                                ? "Flashcard back"
                                : editQuestionType === "CLOZE"
                                  ? "Expected completion"
                                  : "Answer"
                            }
                            className="min-h-[60px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                          />
                          <div className="grid gap-2 sm:grid-cols-2">
                            <select
                              value={editQuestionType}
                              onChange={(event) => {
                                setEditQuestionType(event.target.value);
                                setEditQuestionCorrectOptionIndex(0);
                              }}
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
                          {isEditQuestionMcq && (
                            <div className="grid gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                              <div className="text-[11px] font-semibold text-slate-200">
                                Multiple choice options
                              </div>
                              {editQuestionMcqOptions.map((option, index) => (
                                <div
                                  key={`edit-option-${index}`}
                                  className="grid grid-cols-[auto_1fr] items-center gap-2"
                                >
                                  <label className="flex items-center gap-1 text-[11px] text-slate-300">
                                    <input
                                      type="radio"
                                      name={`edit-correct-option-${question.id}`}
                                      checked={editQuestionCorrectOptionIndex === index}
                                      onChange={() => setEditQuestionCorrectOptionIndex(index)}
                                      className="h-3 w-3"
                                    />
                                    {optionLabel(index)}
                                  </label>
                                  <input
                                    value={option}
                                    onChange={(event) =>
                                      setEditQuestionMcqOptions((prev) => {
                                        const next = [...prev];
                                        next[index] = event.target.value;
                                        return next;
                                      })
                                    }
                                    placeholder={`Option ${optionLabel(index)}`}
                                    className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                                  />
                                </div>
                              ))}
                              <div className="text-[10px] text-slate-400">
                                Select the radio button for the correct option.
                              </div>
                            </div>
                          )}
                          <input
                            value={editQuestionTags}
                            onChange={(event) => setEditQuestionTags(event.target.value)}
                            placeholder="Tags (comma separated)"
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
                          <div className="mt-2 flex flex-wrap items-center gap-2">
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
                              onClick={() => beginEditQuestionNodes(question)}
                              disabled={busy}
                              className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                              title="Edit linked nodes"
                            >
                              ✎
                            </button>
                          </div>
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
                          {isEditingNodes && (
                            <div className="mt-3 grid gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                              <div className="flex flex-wrap items-center gap-2">
                                <button
                                  onClick={() => handleSuggestQuestionNodes(question.id)}
                                  disabled={busy || questionSuggestionLoading}
                                  className="rounded-lg bg-rose-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {questionSuggestionLoading ? "Suggesting..." : "Suggest nodes"}
                                </button>
                                <div className="text-[11px] text-slate-400">
                                  Adjust threshold + weights before suggesting.
                                </div>
                              </div>
                              <div className="grid gap-3 sm:grid-cols-2">
                                <label
                                  className="grid gap-1 pr-2 text-[11px] text-slate-400"
                                  title={SLIDER_HELP.threshold}
                                >
                                  Threshold: {suggestionThreshold.toFixed(2)}
                                  <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.01}
                                    value={suggestionThreshold}
                                    onChange={(event) => setSuggestionThreshold(Number(event.target.value))}
                                    className="w-[calc(100%-8px)] max-w-full"
                                    title={SLIDER_HELP.threshold}
                                  />
                                </label>
                                <label
                                  className="grid gap-1 pr-2 text-[11px] text-slate-400"
                                  title={SLIDER_HELP.semantic}
                                >
                                  Semantic weight: {semanticWeight.toFixed(2)}
                                  <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.05}
                                    value={semanticWeight}
                                    onChange={(event) => setSemanticWeight(Number(event.target.value))}
                                    className="w-[calc(100%-8px)] max-w-full"
                                    title={SLIDER_HELP.semantic}
                                  />
                                </label>
                                <label
                                  className="grid gap-1 pr-2 text-[11px] text-slate-400"
                                  title={SLIDER_HELP.keyword}
                                >
                                  Keyword weight: {keywordWeight.toFixed(2)}
                                  <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.05}
                                    value={keywordWeight}
                                    onChange={(event) => setKeywordWeight(Number(event.target.value))}
                                    className="w-[calc(100%-8px)] max-w-full"
                                    title={SLIDER_HELP.keyword}
                                  />
                                </label>
                                <label
                                  className="grid gap-1 pr-2 text-[11px] text-slate-400"
                                  title={SLIDER_HELP.dedup}
                                >
                                  Dedup threshold: {dedupThreshold.toFixed(2)}
                                  <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.01}
                                    value={dedupThreshold}
                                    onChange={(event) => setDedupThreshold(Number(event.target.value))}
                                    className="w-[calc(100%-8px)] max-w-full"
                                    title={SLIDER_HELP.dedup}
                                  />
                                </label>
                              </div>
                              {questionSuggestionError && (
                                <div className="text-xs text-red-300">{questionSuggestionError}</div>
                              )}
                              {questionSuggestionData.strong.length > 0 && (
                                <div className="text-[11px] text-slate-400">
                                  Strong suggestions preselected: {questionSuggestionData.strong.length}
                                </div>
                              )}
                              {questionNewSuggestions.length > 0 && (
                                <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                                  New candidates (click to add):
                                  <button
                                    type="button"
                                    onClick={() => {
                                      const titles = questionNewSuggestions
                                        .map((item) => item.suggested_title?.trim())
                                        .filter((title): title is string => Boolean(title));
                                      setQuestionNewNodeSelection(Array.from(new Set(titles)));
                                    }}
                                    className="rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-100 transition hover:border-amber-400"
                                  >
                                    Select all
                                  </button>
                                  {questionNewSuggestions.map((item, index) => {
                                    const title = item.suggested_title?.trim();
                                    if (!title) {
                                      return null;
                                    }
                                    const isSelected = questionNewNodeSelection.includes(title);
                                    return (
                                      <button
                                        key={`${title}-${index}`}
                                        type="button"
                                        onClick={() => {
                                          setQuestionNewNodeSelection((prev) =>
                                            prev.includes(title)
                                              ? prev.filter((entry) => entry !== title)
                                              : [...prev, title]
                                          );
                                        }}
                                        className={`rounded-full border px-2 py-0.5 transition ${
                                          isSelected
                                            ? "border-amber-400 bg-amber-500/20 text-amber-100"
                                            : "border-slate-700 bg-slate-900 text-slate-200 hover:border-slate-500"
                                        }`}
                                      >
                                        {title}
                                      </button>
                                    );
                                  })}
                                </div>
                              )}
                              <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                                Selected nodes (click to toggle):
                                {Array.from(
                                  new Set([
                                    ...linkedNodes.map((node) => node.id),
                                    ...questionNodeSelection,
                                  ])
                                ).map((nodeId) => {
                                  const node = nodeLookup.get(nodeId);
                                  const label = node?.topic_name ?? nodeId;
                                  const isSelected = questionNodeSelection.includes(nodeId);
                                  return (
                                    <button
                                      key={nodeId}
                                      type="button"
                                      onClick={() => {
                                        setQuestionNodeSelection((prev) =>
                                          prev.includes(nodeId)
                                            ? prev.filter((id) => id !== nodeId)
                                            : [...prev, nodeId]
                                        );
                                      }}
                                      className={`rounded-full border px-2 py-0.5 transition ${
                                        isSelected
                                          ? "border-rose-400 bg-rose-500/20 text-rose-100"
                                          : "border-slate-700 bg-slate-900 text-slate-400 hover:border-slate-500"
                                      }`}
                                    >
                                      {label}
                                    </button>
                                  );
                                })}
                              </div>
                              <input
                                value={questionNodeSearch}
                                onChange={(event) => setQuestionNodeSearch(event.target.value)}
                                onKeyDown={(event) => {
                                  if (event.key === "Enter" && event.shiftKey) {
                                    event.preventDefault();
                                    handleAddNodeFromQuestionSearch();
                                  }
                                }}
                                placeholder="Search nodes"
                                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                              />
                              {questionNodeSearch.trim() &&
                                !nodes.some(
                                  (node) =>
                                    node.topic_name.toLowerCase() ===
                                    questionNodeSearch.trim().toLowerCase()
                                ) && (
                                  <button
                                    type="button"
                                    onClick={handleAddNodeFromQuestionSearch}
                                    disabled={busy}
                                    className="flex w-full items-center justify-between rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-left text-xs text-rose-100 transition hover:border-rose-400/70 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    <span>Add "{questionNodeSearch.trim()}"</span>
                                    <span className="text-[10px] text-slate-400">Shift + Enter</span>
                                  </button>
                                )}
                              <div className="max-h-40 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/80">
                                {questionFilteredNodes.map((node) => {
                                  const isSelected = questionNodeSelection.includes(node.id);
                                  const isStrongSuggested = questionStrongIds.has(node.id);
                                  const isWeakSuggested = questionWeakIds.has(node.id);
                                  return (
                                    <button
                                      key={node.id}
                                      type="button"
                                      onClick={() => {
                                        setQuestionNodeSelection((prev) =>
                                          prev.includes(node.id)
                                            ? prev.filter((id) => id !== node.id)
                                            : [...prev, node.id]
                                        );
                                      }}
                                      className={`flex w-full items-center justify-between gap-3 border-b border-slate-800 px-3 py-2 text-left text-xs transition last:border-b-0 ${
                                        isSelected
                                          ? "bg-rose-600/20 text-rose-100"
                                          : isStrongSuggested
                                            ? "bg-rose-500/10 text-rose-100"
                                            : isWeakSuggested
                                              ? "bg-slate-800/60 text-slate-200"
                                              : "text-slate-200 hover:bg-slate-800/60"
                                      }`}
                                    >
                                      <span className="font-medium">{node.topic_name}</span>
                                      <span className="text-[10px] text-slate-500">{node.id}</span>
                                    </button>
                                  );
                                })}
                                {questionFilteredNodes.length === 0 && (
                                  <div className="px-3 py-2 text-xs text-slate-500">
                                    No matching nodes.
                                  </div>
                                )}
                              </div>
                              <div className="flex flex-wrap gap-2">
                                <button
                                  onClick={() => handleSaveQuestionNodes(question.id)}
                                  disabled={busy}
                                  className="rounded-lg bg-blue-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  Save links
                                </button>
                                <button
                                  onClick={cancelEditQuestionNodes}
                                  disabled={busy}
                                  className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          )}
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
              <div className="grid min-w-0 gap-3 overflow-hidden rounded-xl border border-slate-800 bg-slate-950 p-4">
                <input
                  value={materialTitle}
                  onChange={(event) => setMaterialTitle(event.target.value)}
                  placeholder="Material title"
                  className="w-full min-w-0 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <div className="flex w-full min-w-0 items-center gap-2">
                  <input
                    value={materialSourceUrl}
                    onChange={(event) => {
                      setMaterialSourceUrl(event.target.value);
                      setMaterialCheckedTranscriptText(null);
                      setMaterialCheckedTranscriptSegments([]);
                      setMaterialTranscriptStatus(null);
                    }}
                    placeholder="YouTube link (optional if text provided)"
                    className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                  />
                  <button
                    onClick={handleCheckMaterialTranscript}
                    disabled={busy || materialTranscriptChecking || !materialSourceUrl.trim() || createMaterialLinkInvalid}
                    className="whitespace-nowrap rounded-lg border border-slate-600 px-3 py-2 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {materialTranscriptChecking ? "Fetching..." : "Fetch transcript"}
                  </button>
                </div>
                <div className={`text-xs ${createMaterialLinkInvalid ? "text-red-300" : "text-slate-500"}`}>
                  {createMaterialLinkInvalid
                    ? "Invalid YouTube URL format"
                    : "Accepted: youtube.com/watch?v=..., youtu.be/..., /shorts/..."}
                </div>
                {materialTranscriptStatus ? (
                  <div className="text-xs text-slate-300">{materialTranscriptStatus}</div>
                ) : null}
                {Boolean(createTranscriptPreview.trim()) && (
                  <div className="grid gap-1 rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                    <div className="text-[11px] text-slate-400">Fetched transcript preview</div>
                    <textarea
                      value={createTranscriptPreview}
                      readOnly
                      className="min-h-[180px] rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 focus:outline-none"
                    />
                  </div>
                )}
                <textarea
                  value={materialText}
                  onChange={(event) => setMaterialText(event.target.value)}
                  placeholder="Paste notes or study material (optional if YouTube link provided)"
                  className="w-full min-h-[100px] min-w-0 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingMaterialNodesId(null);
                      setCreateMaterialSuggestionError(null);
                      setMaterialSuggestions({ materialId: null, strong: [], weak: [] });
                      setIsCreateMaterialNodesOpen((prev) => !prev);
                    }}
                    disabled={busy}
                    className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isCreateMaterialNodesOpen ? "Hide node picker" : "Add nodes"}
                  </button>
                  <div className="text-xs text-slate-400">
                    {createMaterialNodeSelection.length} node{createMaterialNodeSelection.length === 1 ? "" : "s"} selected
                  </div>
                </div>
                {isCreateMaterialNodesOpen && (
                  <div className="grid gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        onClick={handleSuggestDraftMaterialNodes}
                        disabled={busy || createMaterialSuggestionLoading}
                        className="rounded-lg bg-rose-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {createMaterialSuggestionLoading ? "Suggesting..." : "Suggest nodes"}
                      </button>
                      <div className="text-[11px] text-slate-400">
                        Uses notes + optional valid YouTube transcript.
                      </div>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label
                        className="grid gap-1 pr-2 text-[11px] text-slate-400"
                        title={SLIDER_HELP.threshold}
                      >
                        Threshold: {suggestionThreshold.toFixed(2)}
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.01}
                          value={suggestionThreshold}
                          onChange={(event) => setSuggestionThreshold(Number(event.target.value))}
                          className="w-[calc(100%-8px)] max-w-full"
                          title={SLIDER_HELP.threshold}
                        />
                      </label>
                      <label
                        className="grid gap-1 pr-2 text-[11px] text-slate-400"
                        title={SLIDER_HELP.semantic}
                      >
                        Semantic weight: {semanticWeight.toFixed(2)}
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.05}
                          value={semanticWeight}
                          onChange={(event) => setSemanticWeight(Number(event.target.value))}
                          className="w-[calc(100%-8px)] max-w-full"
                          title={SLIDER_HELP.semantic}
                        />
                      </label>
                      <label
                        className="grid gap-1 pr-2 text-[11px] text-slate-400"
                        title={SLIDER_HELP.keyword}
                      >
                        Keyword weight: {keywordWeight.toFixed(2)}
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.05}
                          value={keywordWeight}
                          onChange={(event) => setKeywordWeight(Number(event.target.value))}
                          className="w-[calc(100%-8px)] max-w-full"
                          title={SLIDER_HELP.keyword}
                        />
                      </label>
                      <label
                        className="grid gap-1 pr-2 text-[11px] text-slate-400"
                        title={SLIDER_HELP.dedup}
                      >
                        Dedup threshold: {dedupThreshold.toFixed(2)}
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.01}
                          value={dedupThreshold}
                          onChange={(event) => setDedupThreshold(Number(event.target.value))}
                          className="w-[calc(100%-8px)] max-w-full"
                          title={SLIDER_HELP.dedup}
                        />
                      </label>
                    </div>
                    {createMaterialSuggestionError && (
                      <div className="text-xs text-red-300">{createMaterialSuggestionError}</div>
                    )}
                    {createMaterialSuggestionData.strong.length > 0 && (
                      <div className="text-[11px] text-slate-400">
                        Strong suggestions preselected: {createMaterialSuggestionData.strong.length}
                      </div>
                    )}
                    {createMaterialNewSuggestions.length > 0 && (
                      <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                        New candidates (click to add):
                        <button
                          type="button"
                          onClick={() => {
                            const titles = createMaterialNewSuggestions
                              .map((item) => item.suggested_title?.trim())
                              .filter((title): title is string => Boolean(title));
                            setCreateMaterialNewNodeSelection(Array.from(new Set(titles)));
                          }}
                          className="rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-100 transition hover:border-amber-400"
                        >
                          Select all
                        </button>
                        {createMaterialNewSuggestions.map((item, index) => {
                          const title = item.suggested_title?.trim();
                          if (!title) {
                            return null;
                          }
                          const isSelected = createMaterialNewNodeSelection.includes(title);
                          return (
                            <button
                              key={`create-material-${title}-${index}`}
                              type="button"
                              onClick={() => {
                                setCreateMaterialNewNodeSelection((prev) =>
                                  prev.includes(title)
                                    ? prev.filter((entry) => entry !== title)
                                    : [...prev, title]
                                );
                              }}
                              className={`rounded-full border px-2 py-0.5 transition ${
                                isSelected
                                  ? "border-amber-400 bg-amber-500/20 text-amber-100"
                                  : "border-slate-700 bg-slate-900 text-slate-200 hover:border-slate-500"
                              }`}
                            >
                              {title}
                            </button>
                          );
                        })}
                      </div>
                    )}
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                      Selected nodes (click to toggle):
                      {createMaterialNodeSelection.map((nodeId) => {
                        const node = nodeLookup.get(nodeId);
                        const label = node?.topic_name ?? nodeId;
                        return (
                          <button
                            key={`create-material-selected-${nodeId}`}
                            type="button"
                            onClick={() => {
                              setCreateMaterialNodeSelection((prev) => prev.filter((id) => id !== nodeId));
                            }}
                            className="rounded-full border border-rose-400 bg-rose-500/20 px-2 py-0.5 text-rose-100 transition"
                          >
                            {label}
                          </button>
                        );
                      })}
                      {createMaterialNodeSelection.length === 0 && (
                        <span className="text-[11px] text-slate-500">None selected</span>
                      )}
                    </div>
                    <input
                      value={createMaterialNodeSearch}
                      onChange={(event) => setCreateMaterialNodeSearch(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && event.shiftKey) {
                          event.preventDefault();
                          handleAddNodeFromCreateMaterialSearch();
                        }
                      }}
                      placeholder="Search nodes"
                      className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                    />
                    {createMaterialNodeSearch.trim() &&
                      !nodes.some(
                        (node) => node.topic_name.toLowerCase() === createMaterialNodeSearch.trim().toLowerCase()
                      ) && (
                        <button
                          type="button"
                          onClick={handleAddNodeFromCreateMaterialSearch}
                          disabled={busy}
                          className="flex w-full items-center justify-between rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-left text-xs text-rose-100 transition hover:border-rose-400/70 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <span>Add "{createMaterialNodeSearch.trim()}"</span>
                          <span className="text-[10px] text-slate-400">Shift + Enter</span>
                        </button>
                      )}
                    <div className="max-h-40 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/80">
                      {createMaterialFilteredNodes.map((node) => {
                        const isSelected = createMaterialNodeSelection.includes(node.id);
                        const isStrongSuggested = createMaterialStrongIds.has(node.id);
                        const isWeakSuggested = createMaterialWeakIds.has(node.id);
                        return (
                          <button
                            key={`create-material-node-${node.id}`}
                            type="button"
                            onClick={() => {
                              setCreateMaterialNodeSelection((prev) =>
                                prev.includes(node.id)
                                  ? prev.filter((id) => id !== node.id)
                                  : [...prev, node.id]
                              );
                            }}
                            className={`flex w-full items-center justify-between gap-3 border-b border-slate-800 px-3 py-2 text-left text-xs transition last:border-b-0 ${
                              isSelected
                                ? "bg-rose-600/20 text-rose-100"
                                : isStrongSuggested
                                  ? "bg-rose-500/10 text-rose-100"
                                  : isWeakSuggested
                                    ? "bg-slate-800/60 text-slate-200"
                                    : "text-slate-200 hover:bg-slate-800/60"
                            }`}
                          >
                            <span className="font-medium">{node.topic_name}</span>
                            <span className="text-[10px] text-slate-500">{node.id}</span>
                          </button>
                        );
                      })}
                      {createMaterialFilteredNodes.length === 0 && (
                        <div className="px-3 py-2 text-xs text-slate-500">No matching nodes.</div>
                      )}
                    </div>
                  </div>
                )}
                <button
                  onClick={handleCreateMaterial}
                  disabled={busy || createMaterialLinkInvalid}
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
                  const suggestionData =
                    materialSuggestions.materialId === material.id
                      ? materialSuggestions
                      : { materialId: null, strong: [], weak: [] };
                  const strongSuggestionIds = new Set(
                    suggestionData.strong
                      .filter((item) => item.suggestion_type === "EXISTING" && item.node_id)
                      .map((item) => item.node_id as string)
                  );
                  const weakSuggestionIds = new Set(
                    suggestionData.weak
                      .filter((item) => item.suggestion_type === "EXISTING" && item.node_id)
                      .map((item) => item.node_id as string)
                  );
                  const newSuggestions = suggestionData.weak.filter(
                    (item) => item.suggestion_type === "NEW"
                  );
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
                      className="min-w-0 overflow-hidden rounded-lg border border-slate-800 bg-slate-950 px-3 py-2"
                    >
                      {isEditing ? (
                        <div className="grid gap-2">
                          <input
                            value={editMaterialTitle}
                            onChange={(event) => setEditMaterialTitle(event.target.value)}
                            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                          />
                          <input
                            value={editMaterialSourceUrl}
                            onChange={(event) => {
                              const nextValue = event.target.value;
                              setEditMaterialSourceUrl(nextValue);
                              setEditMaterialCheckedTranscriptText(null);
                              setEditMaterialCheckedTranscriptSegments(null);
                              setEditMaterialTranscriptText("");
                              if (editingMaterialId) {
                                updateMaterialSuggestionDraft(editingMaterialId, { transcript: "" });
                              }
                              setEditMaterialTranscriptStatus(
                                nextValue.trim()
                                  ? "URL changed. Use Check transcript, then Save to persist the new transcript."
                                  : "Transcript will be cleared when you save."
                              );
                            }}
                            placeholder="YouTube/source link"
                            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                          />
                          <div className={`text-[11px] ${editMaterialLinkInvalid ? "text-red-300" : "text-slate-500"}`}>
                            {editMaterialLinkInvalid
                              ? "Invalid YouTube URL format"
                              : "Accepted: youtube.com/watch?v=..., youtu.be/..., /shorts/..."}
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <button
                              type="button"
                              onClick={() => loadEditMaterialTranscript(editMaterialSourceUrl)}
                              disabled={busy || editMaterialTranscriptChecking || !editMaterialSourceUrl.trim() || editMaterialLinkInvalid}
                              className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              {editMaterialTranscriptChecking ? "Checking transcript..." : "Check transcript"}
                            </button>
                            {editMaterialTranscriptStatus && (
                              <div className="text-[11px] text-slate-400">{editMaterialTranscriptStatus}</div>
                            )}
                          </div>
                          <div className="grid gap-1">
                            <div className="text-[11px] text-slate-400">Notes</div>
                            <textarea
                              value={editMaterialText}
                              onChange={(event) => {
                                const nextValue = event.target.value;
                                setEditMaterialText(nextValue);
                                if (editingMaterialId) {
                                  updateMaterialSuggestionDraft(editingMaterialId, { notes: nextValue });
                                }
                              }}
                              className="min-h-[90px] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                            />
                          </div>
                          {(editMaterialTranscriptChecking || Boolean(editTranscriptPreview.trim())) && (
                            <div className="grid gap-1">
                              <div className="text-[11px] text-slate-400">Transcript (YouTube)</div>
                              <textarea
                                value={
                                  editMaterialTranscriptChecking
                                    ? "Loading transcript..."
                                    : editTranscriptPreview
                                }
                                readOnly
                                className="min-h-[90px] rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 focus:outline-none"
                              />
                            </div>
                          )}
                          <div className="flex flex-wrap gap-2">
                            <button
                              onClick={() => handleUpdateMaterial(material.id)}
                              disabled={busy || editMaterialLinkInvalid}
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
                        <div className="grid min-w-0 gap-3">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="break-words text-sm font-semibold text-white">{material.title}</div>
                              <div className="text-xs text-slate-400">
                                {material.chunk_count} chunks
                              </div>
                              {material.source_url ? (
                                <a
                                  href={material.source_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="break-all text-xs text-blue-300 hover:text-blue-200"
                                >
                                  Source link
                                </a>
                              ) : null}
                            </div>
                            <div className="flex flex-wrap items-center justify-end gap-2">
                              <button
                                onClick={() => beginEditMaterial(material)}
                                disabled={busy}
                                className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                Edit
                              </button>
                              <GenerateQuestionsButton
                                onClick={() => setQuestionGeneratorMaterial(material)}
                                disabled={busy}
                              />
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
                                className="max-w-full break-all rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-200"
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
                              <div className="flex flex-wrap items-center gap-2">
                                <button
                                  onClick={() => handleSuggestMaterialNodes(material.id)}
                                  disabled={busy || suggestionLoading}
                                  className="rounded-lg bg-rose-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {suggestionLoading ? "Suggesting..." : "Suggest nodes"}
                                </button>
                                <div className="text-[11px] text-slate-400">
                                  Adjust threshold + weights before suggesting.
                                </div>
                              </div>
                              <div className="grid gap-3 sm:grid-cols-2">
                                <label
                                  className="grid gap-1 pr-2 text-[11px] text-slate-400"
                                  title={SLIDER_HELP.threshold}
                                >
                                  Threshold: {suggestionThreshold.toFixed(2)}
                                  <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.01}
                                    value={suggestionThreshold}
                                    onChange={(event) => setSuggestionThreshold(Number(event.target.value))}
                                    className="w-[calc(100%-8px)] max-w-full"
                                    title={SLIDER_HELP.threshold}
                                  />
                                </label>
                                <label
                                  className="grid gap-1 pr-2 text-[11px] text-slate-400"
                                  title={SLIDER_HELP.semantic}
                                >
                                  Semantic weight: {semanticWeight.toFixed(2)}
                                  <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.05}
                                    value={semanticWeight}
                                    onChange={(event) => setSemanticWeight(Number(event.target.value))}
                                    className="w-[calc(100%-8px)] max-w-full"
                                    title={SLIDER_HELP.semantic}
                                  />
                                </label>
                                <label
                                  className="grid gap-1 pr-2 text-[11px] text-slate-400"
                                  title={SLIDER_HELP.keyword}
                                >
                                  Keyword weight: {keywordWeight.toFixed(2)}
                                  <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.05}
                                    value={keywordWeight}
                                    onChange={(event) => setKeywordWeight(Number(event.target.value))}
                                    className="w-[calc(100%-8px)] max-w-full"
                                    title={SLIDER_HELP.keyword}
                                  />
                                </label>
                                <label
                                  className="grid gap-1 pr-2 text-[11px] text-slate-400"
                                  title={SLIDER_HELP.dedup}
                                >
                                  Dedup threshold: {dedupThreshold.toFixed(2)}
                                  <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.01}
                                    value={dedupThreshold}
                                    onChange={(event) => setDedupThreshold(Number(event.target.value))}
                                    className="w-[calc(100%-8px)] max-w-full"
                                    title={SLIDER_HELP.dedup}
                                  />
                                </label>
                              </div>
                              {suggestionError && (
                                <div className="text-xs text-red-300">{suggestionError}</div>
                              )}
                              {suggestionData.strong.length > 0 && (
                                <div className="text-[11px] text-slate-400">
                                  Strong suggestions preselected: {suggestionData.strong.length}
                                </div>
                              )}
                              {newSuggestions.length > 0 && (
                                <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                                  New candidates (click to add):
                                  <button
                                    type="button"
                                    onClick={() => {
                                      const titles = newSuggestions
                                        .map((item) => item.suggested_title?.trim())
                                        .filter((title): title is string => Boolean(title));
                                      setMaterialNewNodeSelection(Array.from(new Set(titles)));
                                    }}
                                    className="rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-100 transition hover:border-amber-400"
                                  >
                                    Select all
                                  </button>
                                  {newSuggestions.map((item, index) => {
                                    const title = item.suggested_title?.trim();
                                    if (!title) {
                                      return null;
                                    }
                                    const isSelected = materialNewNodeSelection.includes(title);
                                    return (
                                      <button
                                        key={`${title}-${index}`}
                                        type="button"
                                        onClick={() => {
                                          setMaterialNewNodeSelection((prev) =>
                                            prev.includes(title)
                                              ? prev.filter((entry) => entry !== title)
                                              : [...prev, title]
                                          );
                                        }}
                                        className={`rounded-full border px-2 py-0.5 transition ${
                                          isSelected
                                            ? "border-amber-400 bg-amber-500/20 text-amber-100"
                                            : "border-slate-700 bg-slate-900 text-slate-200 hover:border-slate-500"
                                        }`}
                                      >
                                        {title}
                                      </button>
                                    );
                                  })}
                                </div>
                              )}
                              <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                                Selected nodes (click to toggle):
                                {Array.from(
                                  new Set([
                                    ...linkedNodes.map((node) => node.id),
                                    ...materialNodeSelection,
                                  ])
                                ).map((nodeId) => {
                                  const node = nodeLookup.get(nodeId);
                                  const label = node?.topic_name ?? nodeId;
                                  const isSelected = materialNodeSelection.includes(nodeId);
                                  return (
                                    <button
                                      key={nodeId}
                                      type="button"
                                      onClick={() => {
                                        setMaterialNodeSelection((prev) =>
                                          prev.includes(nodeId)
                                            ? prev.filter((id) => id !== nodeId)
                                            : [...prev, nodeId]
                                        );
                                      }}
                                      className={`rounded-full border px-2 py-0.5 transition ${
                                        isSelected
                                          ? "border-rose-400 bg-rose-500/20 text-rose-100"
                                          : "border-slate-700 bg-slate-900 text-slate-400 hover:border-slate-500"
                                      }`}
                                    >
                                      {label}
                                    </button>
                                  );
                                })}
                              </div>
                              <input
                                value={materialNodeSearch}
                                onChange={(event) => setMaterialNodeSearch(event.target.value)}
                                onKeyDown={(event) => {
                                  if (event.key === "Enter" && event.shiftKey) {
                                    event.preventDefault();
                                    handleAddNodeFromMaterialSearch();
                                  }
                                }}
                                placeholder="Search nodes"
                                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                              />
                              {materialNodeSearch.trim() &&
                                !nodes.some(
                                  (node) =>
                                    node.topic_name.toLowerCase() ===
                                    materialNodeSearch.trim().toLowerCase()
                                ) && (
                                  <button
                                    type="button"
                                    onClick={handleAddNodeFromMaterialSearch}
                                    disabled={busy}
                                    className="flex w-full items-center justify-between rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-left text-xs text-rose-100 transition hover:border-rose-400/70 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    <span>Add "{materialNodeSearch.trim()}"</span>
                                    <span className="text-[10px] text-slate-400">Shift + Enter</span>
                                  </button>
                                )}
                              <div className="max-h-40 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/80">
                                {filteredNodes.map((node) => {
                                  const isSelected = materialNodeSelection.includes(node.id);
                                  const isStrongSuggested = strongSuggestionIds.has(node.id);
                                  const isWeakSuggested = weakSuggestionIds.has(node.id);
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
                                          : isStrongSuggested
                                            ? "bg-rose-500/10 text-rose-100"
                                            : isWeakSuggested
                                              ? "bg-slate-800/60 text-slate-200"
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

      <GenerateQuestionsModal
        isOpen={Boolean(questionGeneratorMaterial)}
        material={questionGeneratorMaterial}
        projectId={currentProjectId}
        nodes={nodes}
        onClose={() => setQuestionGeneratorMaterial(null)}
        onCompleted={async (count) => {
          if (!currentProjectId) {
            return;
          }
          await refreshProjectData(currentProjectId);
          setStatus({
            type: "success",
            message: `${count} question${count === 1 ? "" : "s"} added from material`,
          });
        }}
        onError={(message) => {
          setStatus({ type: "error", message });
        }}
      />

    </div>
  );
}
