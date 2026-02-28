"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Eye, EyeOff, FileUp, Import, Loader2, X } from "lucide-react";

import type { NodeDTO } from "@/lib/types";
import {
  createQuestion,
  importQuestionsFromFile,
  previewQuestionsFromFile,
  replaceQuestionNodes,
  suggestQuestionNodesByText,
} from "@/lib/api/question";

type ImportQuestionsModalProps = {
  isOpen: boolean;
  projectId: string | null;
  nodes: NodeDTO[];
  createdBy?: string;
  onClose: () => void;
  onImported: (count: number) => Promise<void> | void;
  onError: (message: string) => void;
};

type SuggestionItem = {
  node_id?: string | null;
  suggested_title?: string | null;
  confidence: number;
  suggestion_type: "EXISTING" | "NEW" | string;
};

type DraftImportQuestion = {
  id: string;
  text: string;
  answer: string;
  question_type: "OPEN" | "FLASHCARD" | "CLOZE" | "MCQ";
  difficulty: number;
  tags: string;
  previewOpen: boolean;
  nodePickerOpen: boolean;
  nodeSearch: string;
  selectedNodeIds: string[];
  newNodeTitles: string[];
  suggestionLoading: boolean;
  suggestionError: string | null;
  strongSuggestions: SuggestionItem[];
  weakSuggestions: SuggestionItem[];
};

const PREVIEW_PAGE_SIZE = 10;

const topNewSuggestionTitles = (weak: SuggestionItem[]) => {
  const newCandidates = weak
    .filter((item) => item.suggestion_type === "NEW" && item.suggested_title)
    .sort((a, b) => b.confidence - a.confidence);
  const newTopCount = Math.ceil(newCandidates.length * 0.5);
  return newCandidates
    .slice(0, newTopCount)
    .map((item) => (item.suggested_title as string).trim())
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
      (item) =>
        item.suggestion_type === "EXISTING" &&
        Boolean(item.node_id) &&
        Number(item.confidence) >= minAutoSelectConfidence
    )
    .sort((a, b) => b.confidence - a.confidence)
    .map((item) => item.node_id as string);
};

const toDraftImportQuestion = (
  question: {
    text: string;
    answer: string;
    question_type: string;
    difficulty: number;
    tags: string[];
  },
  index: number
): DraftImportQuestion => ({
  id: `import-draft-${index}`,
  text: question.text ?? "",
  answer: question.answer ?? "",
  question_type: ["OPEN", "FLASHCARD", "CLOZE", "MCQ"].includes(question.question_type)
    ? (question.question_type as DraftImportQuestion["question_type"])
    : "FLASHCARD",
  difficulty: Math.max(1, Math.min(5, Number(question.difficulty) || 1)),
  tags: (question.tags ?? []).join(", "),
  previewOpen: false,
  nodePickerOpen: false,
  nodeSearch: "",
  selectedNodeIds: [],
  newNodeTitles: [],
  suggestionLoading: false,
  suggestionError: null,
  strongSuggestions: [],
  weakSuggestions: [],
});

const SOURCE_OPTIONS = [
  {
    value: "auto",
    label: "Auto detect",
    accept: ".json,.csv,.txt,.tsv,.apkg,.colpkg",
    hint: "Supports JSON, CSV, TXT/TSV, and Anki packages (.apkg/.colpkg).",
  },
  {
    value: "anki",
    label: "Anki package",
    accept: ".apkg,.colpkg",
    hint: "Imports flashcards with HTML and embedded image previews.",
  },
  {
    value: "flat",
    label: "Flat file",
    accept: ".json,.csv,.txt,.tsv",
    hint: "Imports Q/A from JSON/CSV/TXT/TSV files.",
  },
] as const;

export default function ImportQuestionsModal({
  isOpen,
  projectId,
  nodes,
  createdBy,
  onClose,
  onImported,
  onError,
}: ImportQuestionsModalProps) {
  const [source, setSource] = useState<(typeof SOURCE_OPTIONS)[number]["value"]>("auto");
  const [file, setFile] = useState<File | null>(null);
  const [previewEnabled, setPreviewEnabled] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewQuestions, setPreviewQuestions] = useState<
    Array<{
      text: string;
      answer: string;
      question_type: string;
      difficulty: number;
      tags: string[];
    }>
  >([]);
  const [previewTotalCount, setPreviewTotalCount] = useState(0);
  const [previewHasMore, setPreviewHasMore] = useState(false);
  const [draftQuestions, setDraftQuestions] = useState<DraftImportQuestion[]>([]);
  const [suggestionThreshold, setSuggestionThreshold] = useState(0.75);
  const [semanticWeight, setSemanticWeight] = useState(0.6);
  const [keywordWeight, setKeywordWeight] = useState(0.4);
  const [dedupThreshold, setDedupThreshold] = useState(0.9);
  const [showBulkSuggestSettings, setShowBulkSuggestSettings] = useState(false);
  const [showPerQuestionSuggestSettingsId, setShowPerQuestionSuggestSettingsId] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const bulkSuggestSettingsRef = useRef<HTMLDivElement | null>(null);

  const selectedSource = useMemo(
    () => SOURCE_OPTIONS.find((option) => option.value === source) ?? SOURCE_OPTIONS[0],
    [source]
  );
  const nodeLookup = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);

  useEffect(() => {
    if (!showBulkSuggestSettings) {
      return;
    }

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (!target) {
        return;
      }
      if (!bulkSuggestSettingsRef.current?.contains(target)) {
        setShowBulkSuggestSettings(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setShowBulkSuggestSettings(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [showBulkSuggestSettings]);

  if (!isOpen) {
    return null;
  }

  const renderHtml = (value: string) => ({
    __html: /<\/?[a-z][\s\S]*>/i.test(value)
      ? value
      : (value || "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/\n/g, "<br />"),
  });

  const updateDraftQuestion = (
    questionId: string,
    updater: (question: DraftImportQuestion) => DraftImportQuestion
  ) => {
    setDraftQuestions((prev) =>
      prev.map((question) => (question.id === questionId ? updater(question) : question))
    );
  };

  const parseCsv = (value: string) =>
    value
      .split(",")
      .map((entry) => entry.trim())
      .filter(Boolean);

  const buildQuestionContextText = (question: DraftImportQuestion) => {
    const prompt = question.text.trim();
    const answer = question.answer.trim();
    if (!prompt) {
      return "";
    }
    return `${prompt}\n\n${answer}`.trim();
  };

  const handleSuggestNodesForQuestion = async (question: DraftImportQuestion) => {
    if (!projectId) {
      return;
    }

    const text = buildQuestionContextText(question);
    if (!text) {
      updateDraftQuestion(question.id, (draft) => ({
        ...draft,
        suggestionError: "Enter question text before suggesting nodes",
      }));
      return;
    }

    updateDraftQuestion(question.id, (draft) => ({
      ...draft,
      suggestionError: null,
      suggestionLoading: true,
      strongSuggestions: [],
      weakSuggestions: [],
    }));

    try {
      const response = await suggestQuestionNodesByText({
        project_id: projectId,
        text,
        threshold: suggestionThreshold,
        semantic_weight: semanticWeight,
        keyword_weight: keywordWeight,
        dedup_threshold: dedupThreshold,
        top_k: 20,
      });

      updateDraftQuestion(question.id, (draft) => {
        const autoSelectedNodeIds = autoSelectExistingNodeIds(
          response.strong,
          response.weak,
          suggestionThreshold
        );
        const nextSelected = Array.from(new Set([...draft.selectedNodeIds, ...autoSelectedNodeIds]));
        return {
          ...draft,
          suggestionLoading: false,
          strongSuggestions: response.strong,
          weakSuggestions: response.weak,
          selectedNodeIds: nextSelected,
          newNodeTitles: topNewSuggestionTitles(response.weak),
        };
      });
    } catch {
      updateDraftQuestion(question.id, (draft) => ({
        ...draft,
        suggestionLoading: false,
        suggestionError: "Failed to suggest nodes",
      }));
    }
  };

  const ensureAllPreviewLoaded = async () => {
    if (!file) {
      return [...draftQuestions];
    }

    let loadedQuestions = [...draftQuestions];

    while (loadedQuestions.length < previewTotalCount) {
      const nextOffset = loadedQuestions.length;
      const result = await previewQuestionsFromFile({
        file,
        offset: nextOffset,
        limit: PREVIEW_PAGE_SIZE,
      });
      const nextRaw = result.questions ?? [];
      if (nextRaw.length === 0) {
        break;
      }

      const nextDrafts = nextRaw.map((question, index) =>
        toDraftImportQuestion(question, nextOffset + index)
      );
      setPreviewQuestions((prev) => [...prev, ...nextRaw]);
      setDraftQuestions((prev) => [...prev, ...nextDrafts]);
      setPreviewTotalCount(result.total_count ?? previewTotalCount);
      setPreviewHasMore(Boolean(result.has_more));
      loadedQuestions = [...loadedQuestions, ...nextDrafts];
    }

    return loadedQuestions;
  };

  const handleBulkSuggestNodes = async () => {
    const questionsToSuggest = await ensureAllPreviewLoaded();

    for (const question of questionsToSuggest) {
      await handleSuggestNodesForQuestion(question);
    }
  };

  const handlePreview = async () => {
    if (!file) {
      setLocalError("Choose a file to preview");
      return;
    }

    setPreviewLoading(true);
    setLocalError(null);
    try {
      const result = await previewQuestionsFromFile({ file, offset: 0, limit: PREVIEW_PAGE_SIZE });
      const nextRaw = result.questions ?? [];
      setPreviewQuestions(nextRaw);
      setPreviewTotalCount(result.total_count ?? 0);
      setPreviewHasMore(Boolean(result.has_more));
      setDraftQuestions(nextRaw.map((question, index) => toDraftImportQuestion(question, index)));
      setShowPerQuestionSuggestSettingsId(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to preview questions";
      setLocalError(message);
      setPreviewQuestions([]);
      setPreviewTotalCount(0);
      setPreviewHasMore(false);
      setDraftQuestions([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleLoadMorePreview = async () => {
    if (!file) {
      return;
    }

    const nextOffset = draftQuestions.length;
    if (nextOffset >= previewTotalCount && previewTotalCount > 0) {
      return;
    }

    setPreviewLoading(true);
    setLocalError(null);
    try {
      const result = await previewQuestionsFromFile({
        file,
        offset: nextOffset,
        limit: PREVIEW_PAGE_SIZE,
      });
      const nextRaw = result.questions ?? [];
      const nextDrafts = nextRaw.map((question, index) =>
        toDraftImportQuestion(question, nextOffset + index)
      );
      setPreviewQuestions((prev) => [...prev, ...nextRaw]);
      setDraftQuestions((prev) => [...prev, ...nextDrafts]);
      setPreviewTotalCount(result.total_count ?? previewTotalCount);
      setPreviewHasMore(Boolean(result.has_more));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load more questions";
      setLocalError(message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleLoadAllPreview = async () => {
    if (!file) {
      return;
    }

    setPreviewLoading(true);
    setLocalError(null);
    try {
      await ensureAllPreviewLoaded();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load all questions";
      setLocalError(message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const resetModalState = () => {
    setFile(null);
    setSource("auto");
    setPreviewEnabled(false);
    setPreviewQuestions([]);
    setPreviewTotalCount(0);
    setPreviewHasMore(false);
    setDraftQuestions([]);
    setShowBulkSuggestSettings(false);
    setShowPerQuestionSuggestSettingsId(null);
  };

  const handleImportDraftQuestions = async () => {
    if (!projectId) {
      onError("Select a project first");
      return;
    }
    if (draftQuestions.length === 0) {
      setLocalError("Load an Anki preview first");
      return;
    }

    setGenerating(true);
    setLocalError(null);
    let createdCount = 0;

    try {
      const questionsToImport = await ensureAllPreviewLoaded();

      for (const question of questionsToImport) {
        const text = question.text.trim();
        const answer = question.answer.trim();
        if (!text || !answer) {
          continue;
        }

        const created = await createQuestion({
          project_id: projectId,
          text,
          answer,
          question_type: question.question_type,
          difficulty: question.difficulty,
          tags: parseCsv(question.tags),
          covered_node_ids: question.selectedNodeIds,
          created_by: createdBy,
        });

        if (question.newNodeTitles.length > 0) {
          const newNodes = question.newNodeTitles.map((title) => ({ title }));
          await replaceQuestionNodes(created.id, question.selectedNodeIds, newNodes);
        }

        createdCount += 1;
      }

      if (createdCount === 0) {
        setLocalError("No valid questions to generate. Fill required fields first.");
        return;
      }

      onClose();
      resetModalState();
      await onImported(createdCount);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate questions";
      setLocalError(message);
    } finally {
      setGenerating(false);
    }
  };

  const handleImport = async () => {
    if (!projectId) {
      onError("Select a project first");
      return;
    }
    if (!file) {
      setLocalError("Choose a file to import");
      return;
    }

    setLoading(true);
    setLocalError(null);
    try {
      if (previewEnabled && previewQuestions.length === 0) {
        const preview = await previewQuestionsFromFile({ file, offset: 0, limit: PREVIEW_PAGE_SIZE });
        setPreviewQuestions(preview.questions ?? []);
        setPreviewTotalCount(preview.total_count ?? 0);
        setPreviewHasMore(Boolean(preview.has_more));
      }

      const result = await importQuestionsFromFile({
        projectId,
        file,
        createdBy,
      });
      onClose();
      resetModalState();
      await onImported(result.imported_count ?? 0);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to import questions";
      setLocalError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg-elevated p-4">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border-default bg-bg-elevated shadow-2xl">
        <div className="flex items-start justify-between border-b border-border-default p-4">
          <div>
            <div className="text-base font-semibold font-heading text-text-primary">Import questions</div>
            <div className="text-xs font-body text-text-secondary">Choose where to import from and upload a source file.</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border-default px-2 py-1.5 text-xs font-body text-text-secondary transition hover:border-border-accent"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 overflow-y-auto p-4">
          <div className="grid gap-4">
          <label className="grid gap-1 text-sm font-body text-text-secondary">
            Import source
            <select
              value={source}
              onChange={(event) => setSource(event.target.value as (typeof SOURCE_OPTIONS)[number]["value"])}
              className="rounded-lg border border-border-default bg-bg-elevated px-3 py-2 text-sm font-body text-text-primary focus:border-accent-dim focus:outline-none"
            >
              {SOURCE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <div className="rounded-lg border border-border-default bg-bg-surface p-3 text-xs font-body text-text-secondary">
            {selectedSource.hint}
          </div>

          <label className="grid gap-2 text-sm font-body text-text-secondary">
            Select file
            <input
              type="file"
              accept={selectedSource.accept}
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
                setPreviewQuestions([]);
                setPreviewTotalCount(0);
                setPreviewHasMore(false);
                setDraftQuestions([]);
                setShowPerQuestionSuggestSettingsId(null);
              }}
              className="rounded-lg border border-border-default bg-bg-elevated px-3 py-2 text-sm font-body text-text-primary file:mr-3 file:rounded file:border-0 file:bg-bg-hover file:px-2 file:py-1 file:text-xs file:text-text-primary"
            />
          </label>

          <label className="flex items-center gap-2 text-sm font-body text-text-secondary">
            <input
              type="checkbox"
              checked={previewEnabled}
              onChange={(event) => {
                setPreviewEnabled(event.target.checked);
                if (!event.target.checked) {
                  setPreviewQuestions([]);
                  setPreviewTotalCount(0);
                  setPreviewHasMore(false);
                  setDraftQuestions([]);
                  setShowPerQuestionSuggestSettingsId(null);
                }
              }}
              className="h-4 w-4"
            />
            Preview before import
          </label>

          {file && (
            <div className="flex items-center gap-2 rounded-lg border border-border-default bg-bg-surface px-3 py-2 text-sm font-body text-text-primary">
              <FileUp className="h-4 w-4 text-text-secondary" />
              <span className="break-all">{file.name}</span>
            </div>
          )}

          {localError && <div className="text-sm font-body text-pkr-low">{localError}</div>}

          {previewEnabled && (
            <div className="grid gap-3 rounded-lg border border-border-default bg-bg-surface p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-body text-text-secondary">Preview questions</div>
                <button
                  type="button"
                  onClick={handlePreview}
                  disabled={!file || previewLoading || loading}
                  className="rounded-lg border border-border-default px-3 py-1.5 text-xs font-body text-text-primary transition hover:border-border-accent disabled:opacity-60"
                >
                  {previewLoading ? "Loading preview..." : "Load preview"}
                </button>
              </div>

              {previewQuestions.length > 0 && (
                <div className="grid gap-2 rounded-lg border border-border-default bg-bg-surface p-2">
                  <div className="text-xs font-body text-text-secondary">
                    {previewQuestions.length} loaded
                    {previewTotalCount > previewQuestions.length ? ` (total parsed: ${previewTotalCount})` : ""}
                  </div>
                </div>
              )}

              {!previewLoading && previewQuestions.length === 0 && (
                <div className="text-xs font-body text-text-muted">No preview loaded yet.</div>
              )}
            </div>
          )}

          {draftQuestions.length > 0 && (
            <div className="grid gap-3 rounded-lg border border-border-default bg-bg-surface p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-body text-text-secondary">Question suggestions panel</div>
                <div className="flex flex-wrap items-center gap-2">
                  <div
                    ref={bulkSuggestSettingsRef}
                    className="relative inline-flex rounded-lg border border-accent/60"
                  >
                    <button
                      type="button"
                      onClick={handleBulkSuggestNodes}
                      disabled={loading || generating}
                      className="rounded-l-lg border-r border-accent/60 px-3 py-1.5 text-xs font-body text-text-primary transition hover:border-accent disabled:opacity-60"
                    >
                      Bulk suggest nodes
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowBulkSuggestSettings((prev) => !prev)}
                      disabled={loading || generating}
                      className="rounded-r-lg px-2 py-1.5 text-text-primary transition hover:bg-accent/10 disabled:opacity-60"
                      aria-label="Toggle bulk suggestion settings"
                    >
                      <ChevronDown className={`h-3.5 w-3.5 transition ${showBulkSuggestSettings ? "rotate-180" : ""}`} />
                    </button>
                    {showBulkSuggestSettings && (
                      <div className="absolute right-0 top-full z-10 mt-1 w-72 rounded-lg border border-border-default bg-bg-elevated p-3 shadow-xl">
                        <div className="grid gap-3">
                          <label className="grid gap-1 text-xs font-body text-text-secondary">
                            Threshold: {suggestionThreshold.toFixed(2)}
                            <input
                              type="range"
                              min={0}
                              max={1}
                              step={0.01}
                              value={suggestionThreshold}
                              onChange={(event) => setSuggestionThreshold(Number(event.target.value))}
                              className="w-full"
                            />
                          </label>
                          <label className="grid gap-1 text-xs font-body text-text-secondary">
                            Semantic weight: {semanticWeight.toFixed(2)}
                            <input
                              type="range"
                              min={0}
                              max={1}
                              step={0.05}
                              value={semanticWeight}
                              onChange={(event) => setSemanticWeight(Number(event.target.value))}
                              className="w-full"
                            />
                          </label>
                          <label className="grid gap-1 text-xs font-body text-text-secondary">
                            Keyword weight: {keywordWeight.toFixed(2)}
                            <input
                              type="range"
                              min={0}
                              max={1}
                              step={0.05}
                              value={keywordWeight}
                              onChange={(event) => setKeywordWeight(Number(event.target.value))}
                              className="w-full"
                            />
                          </label>
                          <label className="grid gap-1 text-xs font-body text-text-secondary">
                            Dedup threshold: {dedupThreshold.toFixed(2)}
                            <input
                              type="range"
                              min={0}
                              max={1}
                              step={0.01}
                              value={dedupThreshold}
                              onChange={(event) => setDedupThreshold(Number(event.target.value))}
                              className="w-full"
                            />
                          </label>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid gap-3">
                {draftQuestions.map((question, index) => {
                  const strongIds = new Set(
                    question.strongSuggestions
                      .filter((item) => item.suggestion_type === "EXISTING" && item.node_id)
                      .map((item) => item.node_id as string)
                  );
                  const weakIds = new Set(
                    question.weakSuggestions
                      .filter((item) => item.suggestion_type === "EXISTING" && item.node_id)
                      .map((item) => item.node_id as string)
                  );
                  const newSuggestions = question.weakSuggestions.filter(
                    (item) => item.suggestion_type === "NEW"
                  );
                  const searchValue = question.nodeSearch.trim().toLowerCase();
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
                    <div key={question.id} className="rounded-lg border border-border-default bg-bg-elevated p-3">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <div className="text-xs font-semibold font-body text-text-secondary">Question {index + 1}</div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() =>
                              updateDraftQuestion(question.id, (draft) => ({
                                ...draft,
                                previewOpen: !draft.previewOpen,
                              }))
                            }
                            className="inline-flex items-center rounded-lg border border-border-default px-2 py-1 text-xs font-body text-text-primary transition hover:border-border-accent"
                            title={question.previewOpen ? "Hide preview" : "Preview"}
                            aria-label={question.previewOpen ? "Hide preview" : "Preview"}
                          >
                            {question.previewOpen ? (
                              <EyeOff className="h-3.5 w-3.5" />
                            ) : (
                              <Eye className="h-3.5 w-3.5" />
                            )}
                          </button>
                          <div className="inline-flex rounded-lg border border-accent/60">
                            <button
                              type="button"
                              onClick={() => void handleSuggestNodesForQuestion(question)}
                              disabled={loading || generating || question.suggestionLoading}
                              className="rounded-l-lg border-r border-accent/60 px-2 py-1 text-xs font-body text-text-primary transition hover:border-accent disabled:opacity-60"
                            >
                              {question.suggestionLoading ? "Suggesting..." : "Suggest nodes"}
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                setShowPerQuestionSuggestSettingsId((prev) =>
                                  prev === question.id ? null : question.id
                                )
                              }
                              disabled={loading || generating || question.suggestionLoading}
                              className="rounded-r-lg px-2 py-1 text-text-primary transition hover:bg-accent/10 disabled:opacity-60"
                              aria-label="Toggle suggestion settings"
                            >
                              <ChevronDown
                                className={`h-3.5 w-3.5 transition ${
                                  showPerQuestionSuggestSettingsId === question.id ? "rotate-180" : ""
                                }`}
                              />
                            </button>
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              setDraftQuestions((prev) => prev.filter((item) => item.id !== question.id));
                            }}
                            className="rounded-lg border border-pkr-low/60 px-2 py-1 text-xs font-body text-pkr-low transition hover:border-red-400"
                          >
                            Delete
                          </button>
                        </div>
                      </div>

                      <div className="grid gap-2">
                        {showPerQuestionSuggestSettingsId === question.id && (
                          <div className="grid gap-2 rounded-lg border border-border-default bg-bg-surface p-2">
                            <label className="grid gap-1 text-xs font-body text-text-secondary">
                              Threshold: {suggestionThreshold.toFixed(2)}
                              <input
                                type="range"
                                min={0}
                                max={1}
                                step={0.01}
                                value={suggestionThreshold}
                                onChange={(event) => setSuggestionThreshold(Number(event.target.value))}
                                className="w-full"
                              />
                            </label>
                            <label className="grid gap-1 text-xs font-body text-text-secondary">
                              Semantic weight: {semanticWeight.toFixed(2)}
                              <input
                                type="range"
                                min={0}
                                max={1}
                                step={0.05}
                                value={semanticWeight}
                                onChange={(event) => setSemanticWeight(Number(event.target.value))}
                                className="w-full"
                              />
                            </label>
                            <label className="grid gap-1 text-xs font-body text-text-secondary">
                              Keyword weight: {keywordWeight.toFixed(2)}
                              <input
                                type="range"
                                min={0}
                                max={1}
                                step={0.05}
                                value={keywordWeight}
                                onChange={(event) => setKeywordWeight(Number(event.target.value))}
                                className="w-full"
                              />
                            </label>
                            <label className="grid gap-1 text-xs font-body text-text-secondary">
                              Dedup threshold: {dedupThreshold.toFixed(2)}
                              <input
                                type="range"
                                min={0}
                                max={1}
                                step={0.01}
                                value={dedupThreshold}
                                onChange={(event) => setDedupThreshold(Number(event.target.value))}
                                className="w-full"
                              />
                            </label>
                          </div>
                        )}
                        {question.previewOpen && (
                          <div className="grid gap-2 rounded-lg border border-border-default bg-bg-surface p-3">
                            <div>
                              <div className="text-xs font-body text-text-secondary">Prompt</div>
                              <div
                                className="mt-1 text-sm font-body text-text-primary [&_img]:max-h-48 [&_img]:max-w-full [&_img]:rounded [&_img]:border [&_img]:border-border-default"
                                dangerouslySetInnerHTML={renderHtml(question.text)}
                              />
                            </div>
                            <div>
                              <div className="text-xs font-body text-text-secondary">Answer</div>
                              <div
                                className="mt-1 text-sm font-body text-text-primary [&_img]:max-h-48 [&_img]:max-w-full [&_img]:rounded [&_img]:border [&_img]:border-border-default"
                                dangerouslySetInnerHTML={renderHtml(question.answer)}
                              />
                            </div>
                          </div>
                        )}
                        <textarea
                          value={question.text}
                          onChange={(event) =>
                            updateDraftQuestion(question.id, (draft) => ({ ...draft, text: event.target.value }))
                          }
                          placeholder="Question prompt"
                          className="min-h-[60px] rounded-lg border border-border-default bg-bg-elevated px-3 py-2 text-xs font-body text-text-primary focus:border-accent-dim focus:outline-none"
                        />
                        <textarea
                          value={question.answer}
                          onChange={(event) =>
                            updateDraftQuestion(question.id, (draft) => ({ ...draft, answer: event.target.value }))
                          }
                          placeholder="Answer"
                          className="min-h-[60px] rounded-lg border border-border-default bg-bg-elevated px-3 py-2 text-xs font-body text-text-primary focus:border-accent-dim focus:outline-none"
                        />

                        <div className="grid gap-2 sm:grid-cols-2">
                          <select
                            value={question.question_type}
                            onChange={(event) =>
                              updateDraftQuestion(question.id, (draft) => ({
                                ...draft,
                                question_type: event.target.value as DraftImportQuestion["question_type"],
                              }))
                            }
                            className="rounded-lg border border-border-default bg-bg-elevated px-3 py-2 text-xs font-body text-text-primary focus:border-accent-dim focus:outline-none"
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
                            value={question.difficulty}
                            onChange={(event) =>
                              updateDraftQuestion(question.id, (draft) => ({
                                ...draft,
                                difficulty: Math.max(1, Math.min(5, Number(event.target.value) || 1)),
                              }))
                            }
                            className="rounded-lg border border-border-default bg-bg-elevated px-3 py-2 text-xs font-body text-text-primary focus:border-accent-dim focus:outline-none"
                          />
                        </div>

                        <input
                          value={question.tags}
                          onChange={(event) =>
                            updateDraftQuestion(question.id, (draft) => ({ ...draft, tags: event.target.value }))
                          }
                          placeholder="Tags (comma separated)"
                          className="rounded-lg border border-border-default bg-bg-elevated px-3 py-2 text-xs font-body text-text-primary focus:border-accent-dim focus:outline-none"
                        />

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() =>
                              updateDraftQuestion(question.id, (draft) => ({
                                ...draft,
                                nodePickerOpen: !draft.nodePickerOpen,
                              }))
                            }
                            className="rounded-lg border border-border-default px-3 py-1 text-xs font-body text-text-primary transition hover:border-border-accent"
                          >
                            {question.nodePickerOpen ? "Hide node picker" : "Add nodes"}
                          </button>
                          <div className="text-xs font-body text-text-secondary">
                            {question.selectedNodeIds.length} selected
                          </div>
                        </div>

                        {question.nodePickerOpen && (
                          <div className="grid gap-2 rounded-lg border border-border-default bg-bg-elevated p-3">
                            {question.suggestionError && (
                              <div className="text-xs font-body text-pkr-low">{question.suggestionError}</div>
                            )}

                            {newSuggestions.length > 0 && (
                              <div className="flex flex-wrap items-center gap-2 text-xs font-body text-text-secondary">
                                New candidates:
                                <button
                                  type="button"
                                  onClick={() =>
                                    updateDraftQuestion(question.id, (draft) => ({
                                      ...draft,
                                      newNodeTitles: Array.from(
                                        new Set(
                                          newSuggestions
                                            .map((item) => item.suggested_title?.trim())
                                            .filter((title): title is string => Boolean(title))
                                        )
                                      ),
                                    }))
                                  }
                                  className="rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-0.5 text-xs font-body text-amber-100 transition hover:border-amber-400"
                                >
                                  Select all
                                </button>
                                {newSuggestions.map((item, suggestionIndex) => {
                                  const title = item.suggested_title?.trim();
                                  if (!title) {
                                    return null;
                                  }
                                  const isSelected = question.newNodeTitles.includes(title);
                                  return (
                                    <button
                                      key={`${question.id}-new-${title}-${suggestionIndex}`}
                                      type="button"
                                      onClick={() =>
                                        updateDraftQuestion(question.id, (draft) => ({
                                          ...draft,
                                          newNodeTitles: draft.newNodeTitles.includes(title)
                                            ? draft.newNodeTitles.filter((entry) => entry !== title)
                                            : [...draft.newNodeTitles, title],
                                        }))
                                      }
                                      className={`rounded-full border px-2 py-0.5 transition ${
                                        isSelected
                                          ? "border-amber-400 bg-amber-500/20 text-amber-100"
                                          : "border-border-default bg-bg-elevated text-text-primary hover:border-border-accent"
                                      }`}
                                    >
                                      {title}
                                    </button>
                                  );
                                })}
                              </div>
                            )}

                            <div className="flex flex-wrap items-center gap-2 text-xs font-body text-text-secondary">
                              Selected nodes:
                              {question.selectedNodeIds.map((nodeId) => {
                                const node = nodeLookup.get(nodeId);
                                const label = node?.topic_name ?? nodeId;
                                return (
                                  <button
                                    key={`${question.id}-selected-${nodeId}`}
                                    type="button"
                                    onClick={() =>
                                      updateDraftQuestion(question.id, (draft) => ({
                                        ...draft,
                                        selectedNodeIds: draft.selectedNodeIds.filter((id) => id !== nodeId),
                                      }))
                                    }
                                    className="rounded-full border border-accent bg-accent/20 px-2 py-0.5 text-text-primary transition"
                                  >
                                    {label}
                                  </button>
                                );
                              })}
                              {question.selectedNodeIds.length === 0 && (
                                <span className="text-xs font-body text-text-muted">None selected</span>
                              )}
                            </div>

                            <input
                              value={question.nodeSearch}
                              onChange={(event) =>
                                updateDraftQuestion(question.id, (draft) => ({
                                  ...draft,
                                  nodeSearch: event.target.value,
                                }))
                              }
                              onKeyDown={(event) => {
                                if (event.key === "Enter" && event.shiftKey) {
                                  event.preventDefault();
                                  const raw = question.nodeSearch.trim();
                                  if (!raw) {
                                    return;
                                  }
                                  const existing = nodes.find(
                                    (node) => node.topic_name.toLowerCase() === raw.toLowerCase()
                                  );
                                  if (existing) {
                                    updateDraftQuestion(question.id, (draft) => ({
                                      ...draft,
                                      selectedNodeIds: draft.selectedNodeIds.includes(existing.id)
                                        ? draft.selectedNodeIds
                                        : [...draft.selectedNodeIds, existing.id],
                                      nodeSearch: "",
                                    }));
                                  } else {
                                    updateDraftQuestion(question.id, (draft) => ({
                                      ...draft,
                                      newNodeTitles: draft.newNodeTitles.includes(raw)
                                        ? draft.newNodeTitles
                                        : [...draft.newNodeTitles, raw],
                                      nodeSearch: "",
                                    }));
                                  }
                                }
                              }}
                              placeholder="Search nodes"
                              className="rounded-lg border border-border-default bg-bg-elevated px-3 py-2 text-xs font-body text-text-primary focus:border-accent-dim focus:outline-none"
                            />

                            <div className="max-h-36 overflow-y-auto rounded-lg border border-border-default bg-bg-elevated">
                              {filteredNodes.map((node) => {
                                const isSelected = question.selectedNodeIds.includes(node.id);
                                const isStrongSuggested = strongIds.has(node.id);
                                const isWeakSuggested = weakIds.has(node.id);
                                return (
                                  <button
                                    key={`${question.id}-node-${node.id}`}
                                    type="button"
                                    onClick={() =>
                                      updateDraftQuestion(question.id, (draft) => ({
                                        ...draft,
                                        selectedNodeIds: draft.selectedNodeIds.includes(node.id)
                                          ? draft.selectedNodeIds.filter((id) => id !== node.id)
                                          : [...draft.selectedNodeIds, node.id],
                                      }))
                                    }
                                    className={`flex w-full items-center justify-between gap-2 border-b border-border-default px-3 py-2 text-left text-xs transition last:border-b-0 ${
                                      isSelected
                                        ? "bg-accent/20 text-text-primary"
                                        : isStrongSuggested
                                          ? "bg-accent/10 text-text-primary"
                                          : isWeakSuggested
                                            ? "bg-bg-hover text-text-primary"
                                            : "text-text-primary hover:bg-bg-hover"
                                    }`}
                                  >
                                    <span className="font-medium">{node.topic_name}</span>
                                    <span className="text-xs font-body text-text-muted">{node.id}</span>
                                  </button>
                                );
                              })}
                              {filteredNodes.length === 0 && (
                                <div className="px-3 py-2 text-xs font-body text-text-muted">No matching nodes.</div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {previewHasMore && (
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={handleLoadMorePreview}
                      disabled={previewLoading || loading || generating}
                      className="rounded-lg border border-border-default px-3 py-1.5 text-xs font-body text-text-primary transition hover:border-border-accent disabled:opacity-60"
                    >
                      {previewLoading ? "Loading..." : "Load more"}
                    </button>
                    <button
                      type="button"
                      onClick={handleLoadAllPreview}
                      disabled={previewLoading || loading || generating}
                      className="rounded-lg border border-border-default px-3 py-1.5 text-xs font-body text-text-primary transition hover:border-border-accent disabled:opacity-60"
                    >
                      {previewLoading ? "Loading..." : "Load all"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading || generating}
              className="rounded-lg border border-border-default px-3 py-2 text-sm font-body text-text-primary transition hover:border-border-accent disabled:opacity-60"
            >
              Cancel
            </button>
            {draftQuestions.length > 0 ? (
              <button
                type="button"
                onClick={handleImportDraftQuestions}
                disabled={loading || generating || draftQuestions.length === 0}
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-semibold font-body text-text-primary transition hover:bg-accent-hover disabled:opacity-60"
              >
                {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Import className="h-4 w-4" />}
                {generating ? "Importing..." : "Import"}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleImport}
                disabled={loading || !file}
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-semibold font-body text-text-primary transition hover:bg-accent-hover disabled:opacity-60"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Import className="h-4 w-4" />}
                {loading ? "Importing..." : "Import questions"}
              </button>
            )}
          </div>
        </div>
        </div>
      </div>
    </div>
  );
}
