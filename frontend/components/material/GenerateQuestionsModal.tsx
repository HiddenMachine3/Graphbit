"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Hash, X } from "lucide-react";

import type { MaterialDTO, NodeDTO } from "@/lib/types";
import { fetchMaterial } from "@/lib/api/material";
import {
  createQuestion,
  generateQuestionsFromText,
  replaceQuestionNodes,
  suggestQuestionNodesByText,
} from "@/lib/api/question";

type SuggestionItem = {
  node_id?: string | null;
  suggested_title?: string | null;
  confidence: number;
  suggestion_type: "EXISTING" | "NEW" | string;
};

type DraftQuestion = {
  id: string;
  text: string;
  answer: string;
  question_type: "OPEN" | "FLASHCARD" | "CLOZE" | "MCQ";
  difficulty: number;
  tags: string;
  options: string[];
  correctOptionIndex: number;
  nodePickerOpen: boolean;
  nodeSearch: string;
  selectedNodeIds: string[];
  newNodeTitles: string[];
  suggestionLoading: boolean;
  suggestionError: string | null;
  strongSuggestions: SuggestionItem[];
  weakSuggestions: SuggestionItem[];
};

type GenerateQuestionsModalProps = {
  isOpen: boolean;
  material: MaterialDTO | null;
  projectId: string | null;
  nodes: NodeDTO[];
  onClose: () => void;
  onCompleted: (count: number) => Promise<void> | void;
  onError: (message: string) => void;
};

const EMPTY_MCQ_OPTIONS = ["", "", "", ""];

const optionLabel = (index: number) => String.fromCharCode(65 + index);

const parseCsv = (value: string) =>
  value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);

const normalizeMcqOptions = (options: string[]) =>
  options.map((option) => option.trim()).filter(Boolean);

const QA_MAX_INPUT_CHARS = 18000;

const truncateCombinedSourceText = (
  notesText: string,
  transcriptText: string,
  maxChars: number
) => {
  const notes = notesText.trim();
  const transcript = transcriptText.trim();

  if (!notes && !transcript) {
    return "";
  }

  if (!notes) {
    return transcript.slice(0, maxChars).trim();
  }

  if (!transcript) {
    return notes.slice(0, maxChars).trim();
  }

  const separator = "\n\n";
  const available = Math.max(0, maxChars - separator.length);
  const notesLimit = Math.floor(available / 2);
  const transcriptLimit = available - notesLimit;

  return `${notes.slice(0, notesLimit).trim()}${separator}${transcript
    .slice(0, transcriptLimit)
    .trim()}`.trim();
};

const toDraftQuestion = (question: string, answer: string, index: number): DraftQuestion => ({
  id: `draft-${Date.now()}-${index}`,
  text: question,
  answer,
  question_type: "OPEN",
  difficulty: 1,
  tags: "",
  options: EMPTY_MCQ_OPTIONS,
  correctOptionIndex: 0,
  nodePickerOpen: false,
  nodeSearch: "",
  selectedNodeIds: [],
  newNodeTitles: [],
  suggestionLoading: false,
  suggestionError: null,
  strongSuggestions: [],
  weakSuggestions: [],
});

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

export default function GenerateQuestionsModal({
  isOpen,
  material,
  projectId,
  nodes,
  onClose,
  onCompleted,
  onError,
}: GenerateQuestionsModalProps) {
  const [count, setCount] = useState(3);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [hasGeneratedOnce, setHasGeneratedOnce] = useState(false);
  const [draftQuestions, setDraftQuestions] = useState<DraftQuestion[]>([]);
  const [localError, setLocalError] = useState<string | null>(null);
  const [suggestionThreshold, setSuggestionThreshold] = useState(0.75);
  const [semanticWeight, setSemanticWeight] = useState(0.6);
  const [keywordWeight, setKeywordWeight] = useState(0.4);
  const [dedupThreshold, setDedupThreshold] = useState(0.9);
  const [showBulkSuggestSettings, setShowBulkSuggestSettings] = useState(false);
  const bulkSuggestSettingsRef = useRef<HTMLDivElement | null>(null);

  const nodeLookup = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);

  const updateDraftQuestion = (questionId: string, updater: (draft: DraftQuestion) => DraftQuestion) => {
    setDraftQuestions((prev) =>
      prev.map((question) => (question.id === questionId ? updater(question) : question))
    );
  };

  const buildQuestionContextText = (question: DraftQuestion) => {
    const prompt = question.text.trim();
    if (!prompt) {
      return "";
    }
    if (question.question_type === "MCQ") {
      const options = question.options.map((option) => option.trim()).filter(Boolean);
      const selectedCorrectOption = question.options[question.correctOptionIndex]?.trim() ?? "";
      const parts = [prompt];
      if (options.length > 0) {
        parts.push(
          `Options:\n${options.map((option, index) => `${optionLabel(index)}. ${option}`).join("\n")}`
        );
      }
      if (selectedCorrectOption) {
        parts.push(`Correct option: ${selectedCorrectOption}`);
      }
      return parts.filter(Boolean).join("\n\n").trim();
    }
    return `${prompt}\n\n${question.answer.trim()}`.trim();
  };

  const loadGeneratedQuestions = async (nextCount: number) => {
    if (!projectId || !material) {
      setLocalError("Select a project and material first.");
      return;
    }

    setLoading(true);
    setLocalError(null);
    try {
      const materialDetail = await fetchMaterial(material.id);
      const chunksText = (materialDetail.chunks ?? []).join("\n\n").trim();
      const transcriptText =
        (materialDetail.transcript_text ?? "").trim() ||
        (materialDetail.transcript_chunks ?? []).join("\n\n").trim() ||
        (materialDetail.transcript_segments ?? [])
          .map((segment) => segment.text?.trim())
          .filter((text): text is string => Boolean(text))
          .join("\n");
      const sourceText = truncateCombinedSourceText(
        chunksText,
        transcriptText,
        QA_MAX_INPUT_CHARS
      );

      if (!sourceText) {
        setLocalError("Selected material has no text to generate questions from.");
        setDraftQuestions([]);
        return;
      }

      const response = await generateQuestionsFromText({
        text: sourceText,
        n: nextCount,
      });

      const drafts = (response.qa_pairs ?? []).map((item, index) =>
        toDraftQuestion(item.question ?? "", item.answer ?? "", index)
      );
      setDraftQuestions(drafts);
      setHasGeneratedOnce(true);
    } catch (error) {
      const message =
        error && typeof error === "object" && "message" in error
          ? String((error as { message?: string }).message || "")
          : "";
      setLocalError(
        message
          ? `Failed to generate questions from selected material: ${message}`
          : "Failed to generate questions from selected material."
      );
      setDraftQuestions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestNodesForQuestion = async (question: DraftQuestion) => {
    if (!projectId) {
      return;
    }

    const text = buildQuestionContextText(question);
    if (!text) {
      updateDraftQuestion(question.id, (draft) => ({
        ...draft,
        suggestionError: "Enter question text (and answer) before suggesting nodes",
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

  const handleBulkSuggestNodes = async () => {
    for (const question of draftQuestions) {
      await handleSuggestNodesForQuestion(question);
    }
  };

  const handleAddEmptyQuestion = () => {
    setDraftQuestions((prev) => [
      ...prev,
      toDraftQuestion("", "", prev.length),
    ]);
  };

  const handleBulkAdd = async () => {
    if (!projectId || !material) {
      onError("Select a project and material first");
      return;
    }

    if (draftQuestions.length === 0) {
      onError("Generate questions first");
      return;
    }

    setSubmitting(true);
    setLocalError(null);

    let createdCount = 0;
    try {
      for (const question of draftQuestions) {
        const trimmedQuestionText = question.text.trim();
        if (!trimmedQuestionText) {
          continue;
        }

        const normalizedOptions = normalizeMcqOptions(question.options);
        const selectedCorrectOption = question.options[question.correctOptionIndex]?.trim() ?? "";
        const payloadAnswer =
          question.question_type === "MCQ" ? selectedCorrectOption : question.answer.trim();

        if (question.question_type === "MCQ") {
          if (normalizedOptions.length < 2 || !selectedCorrectOption) {
            continue;
          }
        } else if (!payloadAnswer) {
          continue;
        }

        const createdQuestion = await createQuestion({
          project_id: projectId,
          text: trimmedQuestionText,
          answer: payloadAnswer,
          options: question.question_type === "MCQ" ? normalizedOptions : undefined,
          question_type: question.question_type,
          difficulty: question.difficulty,
          tags: parseCsv(question.tags),
          source_material_ids: [material.id],
          covered_node_ids: question.selectedNodeIds,
        });

        if (question.newNodeTitles.length > 0) {
          const newNodes = question.newNodeTitles.map((title) => ({ title }));
          await replaceQuestionNodes(createdQuestion.id, question.selectedNodeIds, newNodes);
        }

        createdCount += 1;
      }

      if (createdCount === 0) {
        setLocalError("No valid questions to add. Fill required fields first.");
        return;
      }

      await onCompleted(createdCount);
      onClose();
    } catch {
      setLocalError("Failed to bulk add generated questions.");
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    if (!isOpen || !material) {
      return;
    }
    setCount(3);
    setLocalError(null);
    setShowBulkSuggestSettings(false);
    setHasGeneratedOnce(false);
    setDraftQuestions([]);
  }, [isOpen, material?.id]);

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

  if (!isOpen || !material) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4">
      <div className="flex h-[90vh] w-full max-w-6xl flex-col rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl">
        <div className="flex items-start justify-between border-b border-slate-800 p-4">
          <div>
            <div className="text-base font-semibold text-white">Generate questions</div>
            <div className="text-xs text-slate-400">Material: {material.title}</div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <div
              ref={bulkSuggestSettingsRef}
              className="relative inline-flex rounded-lg border border-rose-500/60"
            >
              <button
                type="button"
                onClick={handleBulkSuggestNodes}
                disabled={loading || submitting || draftQuestions.length === 0}
                className="rounded-l-lg border-r border-rose-500/60 px-3 py-1.5 text-xs text-rose-100 transition hover:border-rose-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Bulk suggest nodes
              </button>
              <button
                type="button"
                onClick={() => setShowBulkSuggestSettings((prev) => !prev)}
                disabled={loading || submitting}
                className="rounded-r-lg px-2 py-1.5 text-rose-100 transition hover:bg-rose-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                aria-label="Toggle bulk suggestion settings"
              >
                <ChevronDown className={`h-3.5 w-3.5 transition ${showBulkSuggestSettings ? "rotate-180" : ""}`} />
              </button>
              {showBulkSuggestSettings && (
                <div className="absolute right-0 top-full z-10 mt-1 w-72 rounded-lg border border-slate-700 bg-slate-900 p-3 shadow-xl">
                  <div className="grid gap-3">
                    <label className="grid gap-1 text-[11px] text-slate-300">
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
                    <label className="grid gap-1 text-[11px] text-slate-300">
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
                    <label className="grid gap-1 text-[11px] text-slate-300">
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
                    <label className="grid gap-1 text-[11px] text-slate-300">
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
            <button
              type="button"
              onClick={handleBulkAdd}
              disabled={loading || submitting || draftQuestions.length === 0}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Adding..." : "Bulk add"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-600 px-2 py-1.5 text-xs text-slate-300 transition hover:border-slate-500"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="border-b border-slate-800 p-4">
          <div className="grid gap-3 md:grid-cols-[120px_1fr] md:items-end">
            <label className="grid gap-1 text-xs text-slate-400">
              Number of questions
              <input
                type="number"
                min={1}
                max={20}
                value={count}
                onChange={(event) => setCount(Math.max(1, Math.min(20, Number(event.target.value) || 1)))}
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              />
            </label>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => void loadGeneratedQuestions(count)}
                disabled={loading || submitting}
                className="rounded-lg border border-slate-600 px-3 py-2 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Generating..." : hasGeneratedOnce ? "Redo" : "Generate"}
              </button>
              <button
                type="button"
                onClick={handleAddEmptyQuestion}
                disabled={loading || submitting}
                className="rounded-lg border border-slate-600 px-3 py-2 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Add empty question
              </button>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {localError && <div className="mb-3 text-sm text-red-300">{localError}</div>}

          {loading && draftQuestions.length === 0 && (
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300">
              Generating questions...
            </div>
          )}

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
                <div key={question.id} className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <div className="text-xs font-semibold text-slate-300">Question {index + 1}</div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => void handleSuggestNodesForQuestion(question)}
                        disabled={loading || submitting || question.suggestionLoading}
                        className="rounded-lg border border-rose-500/60 px-2 py-1 text-[11px] text-rose-100 transition hover:border-rose-400 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {question.suggestionLoading ? "Suggesting..." : "Suggest nodes"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setDraftQuestions((prev) => prev.filter((item) => item.id !== question.id));
                        }}
                        className="rounded-lg border border-red-500/60 px-2 py-1 text-[11px] text-red-200 transition hover:border-red-400"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  <div className="grid gap-2">
                    <textarea
                      value={question.text}
                      onChange={(event) =>
                        updateDraftQuestion(question.id, (draft) => ({ ...draft, text: event.target.value }))
                      }
                      placeholder="Question prompt"
                      className="min-h-[70px] rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                    />

                    <div className="grid gap-2 sm:grid-cols-2">
                      <select
                        value={question.question_type}
                        onChange={(event) =>
                          updateDraftQuestion(question.id, (draft) => ({
                            ...draft,
                            question_type: event.target.value as DraftQuestion["question_type"],
                            correctOptionIndex: 0,
                          }))
                        }
                        className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
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
                        className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                      />
                    </div>

                    {question.question_type === "MCQ" ? (
                      <div className="grid gap-2 rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                        <div className="text-[11px] text-slate-300">Multiple choice options</div>
                        {question.options.map((option, optionIndex) => (
                          <div key={`${question.id}-option-${optionIndex}`} className="grid grid-cols-[auto_1fr] items-center gap-2">
                            <label className="flex items-center gap-1 text-[11px] text-slate-300">
                              <input
                                type="radio"
                                name={`bulk-correct-${question.id}`}
                                checked={question.correctOptionIndex === optionIndex}
                                onChange={() =>
                                  updateDraftQuestion(question.id, (draft) => ({
                                    ...draft,
                                    correctOptionIndex: optionIndex,
                                  }))
                                }
                                className="h-3.5 w-3.5"
                              />
                              {optionLabel(optionIndex)}
                            </label>
                            <input
                              value={option}
                              onChange={(event) =>
                                updateDraftQuestion(question.id, (draft) => {
                                  const next = [...draft.options];
                                  next[optionIndex] = event.target.value;
                                  return { ...draft, options: next };
                                })
                              }
                              placeholder={`Option ${optionLabel(optionIndex)}`}
                              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                            />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <textarea
                        value={question.answer}
                        onChange={(event) =>
                          updateDraftQuestion(question.id, (draft) => ({ ...draft, answer: event.target.value }))
                        }
                        placeholder="Answer"
                        className="min-h-[60px] rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                      />
                    )}

                    <input
                      value={question.tags}
                      onChange={(event) =>
                        updateDraftQuestion(question.id, (draft) => ({ ...draft, tags: event.target.value }))
                      }
                      placeholder="Tags (comma separated)"
                      className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
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
                        className="rounded-lg border border-slate-600 px-3 py-1 text-[11px] text-slate-200 transition hover:border-slate-500"
                      >
                        {question.nodePickerOpen ? "Hide node picker" : "Add nodes"}
                      </button>
                      <div className="text-[11px] text-slate-400">
                        {question.selectedNodeIds.length} selected
                      </div>
                    </div>

                    {question.nodePickerOpen && (
                      <div className="grid gap-2 rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                        {question.suggestionError && (
                          <div className="text-xs text-red-300">{question.suggestionError}</div>
                        )}

                        {newSuggestions.length > 0 && (
                          <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
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
                              className="rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-100 transition hover:border-amber-400"
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
                                className="rounded-full border border-rose-400 bg-rose-500/20 px-2 py-0.5 text-rose-100 transition"
                              >
                                {label}
                              </button>
                            );
                          })}
                          {question.selectedNodeIds.length === 0 && (
                            <span className="text-[11px] text-slate-500">None selected</span>
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
                          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                        />

                        <div className="max-h-36 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/80">
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
                                className={`flex w-full items-center justify-between gap-2 border-b border-slate-800 px-3 py-2 text-left text-xs transition last:border-b-0 ${
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
                            <div className="px-3 py-2 text-xs text-slate-500">No matching nodes.</div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {!loading && draftQuestions.length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-700 p-4 text-sm text-slate-400">
              No generated questions yet. Click Generate to start.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function GenerateQuestionsButton({
  onClick,
  disabled,
}: {
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1 rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
    >
      <Hash className="h-3.5 w-3.5" />
      Generate questions
    </button>
  );
}
