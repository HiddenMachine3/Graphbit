-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Nodes: embeddings and search vector
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS embedding vector(768);
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS search_vector tsvector;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'nodes'
      AND column_name = 'embedding'
      AND udt_name <> 'vector'
  ) THEN
    ALTER TABLE nodes ALTER COLUMN embedding TYPE vector(768) USING NULL;
  END IF;
END $$;

UPDATE nodes
SET search_vector = to_tsvector('english', COALESCE(topic_name, ''))
WHERE search_vector IS NULL;

CREATE INDEX IF NOT EXISTS idx_nodes_embedding
  ON nodes USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_nodes_search_vector
  ON nodes USING GIN (search_vector);

-- Materials: summary and embedding
ALTER TABLE materials ADD COLUMN IF NOT EXISTS summary text;
ALTER TABLE materials ADD COLUMN IF NOT EXISTS embedding vector(768);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'materials'
      AND column_name = 'embedding'
      AND udt_name <> 'vector'
  ) THEN
    ALTER TABLE materials ALTER COLUMN embedding TYPE vector(768) USING NULL;
  END IF;
END $$;

-- Material node suggestions
CREATE TABLE IF NOT EXISTS material_node_suggestions (
  id text PRIMARY KEY,
  material_id text NOT NULL,
  node_id text NULL,
  suggested_title text NULL,
  suggested_description text NULL,
  confidence double precision NOT NULL DEFAULT 0,
  suggestion_type text NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_material_node_suggestions_material
  ON material_node_suggestions (material_id);
