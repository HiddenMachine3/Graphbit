export type ProjectVisibility = "private" | "shared" | "public";

export interface ProjectDTO {
  id: string;
  name: string;
  description: string;
  owner_id?: string;
  created_by: string;
  visibility: ProjectVisibility;
  created_at: string;
  updated_at: string;
}

export interface NodeDTO {
  id: string;
  project_id: string;
  created_by?: string;
  topic_name: string;
  proven_knowledge_rating: number;
  user_estimated_knowledge_rating: number;
  importance: number;
  relevance: number;
  view_frequency: number;
  source_material_ids: string[];
}

export interface GraphNodeDTO extends NodeDTO {
  forgetting_score: number;
  linked_questions_count: number;
  linked_materials_count: number;
  node_type?: "topic" | "material" | "chapter";
  sequence_number?: number | null;
}

export interface GraphEdgeDTO {
  id: string;
  project_id: string;
  source: string;
  target: string;
  type: string;
  weight: number;
}

export interface GraphSummaryDTO {
  nodes: GraphNodeDTO[];
  edges: GraphEdgeDTO[];
}

export interface QuestionMetadataDTO {
  created_by: string;
  created_at: string;
  importance: number;
  hits: number;
  misses: number;
}

export type QuestionType = "FLASHCARD" | "CLOZE" | "MCQ" | "OPEN";

export interface QuestionDTO {
  id: string;
  project_id: string;
  text: string;
  answer: string;
  question_type: QuestionType;
  knowledge_type: string;
  covered_node_ids: string[];
  metadata?: QuestionMetadataDTO;
  question_metadata?: QuestionMetadataDTO;
  difficulty: number;
  tags: string[];
  last_attempted_at: string | null;
  source_material_ids: string[];
  options?: string[];
}

export interface SessionDTO {
  session_id: string;
  material_id: string;
  user_id: string;
  started_at: string;
  last_interjection_at: string | null;
  consumed_chunks: number;
}

export type ContentSessionDTO = SessionDTO;

export interface InterjectionDecisionDTO {
  should_interject: boolean;
  reason?: string | null;
}

export interface RevisionSessionDTO {
  session_id: string;
  max_questions: number | null;
  project_id?: string | null;
}

export interface RevisionFeedbackDTO {
  correct: boolean;
  correct_answer?: string | null;
  explanation?: string | null;
  performance?: "bad" | "ok" | "good" | "great";
}

export interface CommunityDTO {
  id: string;
  name: string;
  description: string;
  created_by?: string;
  project_ids?: string[];
  member_ids?: string[];
  node_importance_overrides: Record<string, Record<string, number>>;
  question_importance_overrides?: Record<string, Record<string, number>>;
}

export interface CommunityProgressDTO {
  community_id: string;
  overall_progress: number;
  relevant_topics: number;
}

export interface LeaderboardEntryDTO {
  user_id: string;
  score: number;
  rank: number;
}

export interface WhyThisQuestionDTO {
  target_nodes: string[];
  weakness_level: "low" | "medium" | "high";
  forgetting_cue: string;
}

export interface WeaknessNodeDTO {
  node_id: string;
  topic: string;
  weakness_level: "low" | "medium" | "high";
  explanation: string;
}

export interface RevisionPlanItemDTO {
  node_id: string;
  topic: string;
  reason: string;
  timing: string;
}

export interface MaterialDTO {
  id: string;
  project_id: string;
  created_by: string;
  title: string;
  source_url?: string | null;
  chunk_count: number;
  transcript_chunk_count?: number;
  has_transcript?: boolean;
}

export interface SearchResultItemDTO {
  id: string;
  title: string;
  score: number;
}

export interface SearchResultsDTO {
  nodes: SearchResultItemDTO[];
  materials: SearchResultItemDTO[];
}

export interface UserDTO {
  id: string;
  username: string;
  name: string;
  avatar_url: string | null;
  active_community_id: string | null;
}
