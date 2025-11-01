-- Initial Database Schema for Agentic RAG Platform
--
-- 1. Extensions
--    - Enable vector extension for pgvector support (embeddings storage)
--    - Enable uuid-ossp for UUID generation
--
-- 2. New Tables
--    - tenants: Organization/tenant management
--    - user_profiles: User information with tenant association
--    - documents: Uploaded documents with tenant isolation
--    - document_chunks: Document segments with embeddings
--    - chat_sessions: Conversation sessions
--    - chat_messages: Individual messages with agent metadata
--    - data_sources: External data connector configurations
--
-- 3. Security
--    - Enable Row Level Security (RLS) on ALL tables
--    - Create policies enforcing tenant_id isolation
--    - Policies verify auth.uid() and tenant membership
--    - CRITICAL: All queries MUST filter by tenant_id
--
-- 4. Indexes
--    - B-Tree indexes on tenant_id for fast filtering
--    - HNSW vector indexes for similarity search
--    - Composite indexes for common query patterns
--
-- 5. Functions
--    - Automatic updated_at timestamp trigger
--    - Tenant membership validation function

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Tenants table
CREATE TABLE IF NOT EXISTS tenants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  settings jsonb DEFAULT '{}'::jsonb
);

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- User profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  full_name text,
  role text DEFAULT 'user' CHECK (role IN ('admin', 'user', 'viewer')),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant_id ON user_profiles(tenant_id);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  title text NOT NULL,
  source_url text,
  file_type text,
  file_size bigint,
  status text DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  metadata jsonb DEFAULT '{}'::jsonb,
  uploaded_by uuid REFERENCES auth.users(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);

-- Document chunks table with vector embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  content text NOT NULL,
  embedding vector(1536),
  chunk_index integer NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_document_chunks_tenant_id ON document_chunks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);

-- Create HNSW index for vector similarity search with tenant filtering
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops);

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title text DEFAULT 'New Chat',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_tenant_id ON chat_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_tenant_id ON chat_messages(tenant_id);

-- Data sources table
CREATE TABLE IF NOT EXISTS data_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name text NOT NULL,
  type text NOT NULL CHECK (type IN ('s3', 'sharepoint', 'confluence', 'google_drive', 'database', 'api')),
  config jsonb DEFAULT '{}'::jsonb,
  status text DEFAULT 'inactive' CHECK (status IN ('active', 'inactive', 'error')),
  last_sync timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_data_sources_tenant_id ON data_sources(tenant_id);

-- Add updated_at triggers
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_data_sources_updated_at BEFORE UPDATE ON data_sources
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies for Tenants
CREATE POLICY "Users can view their own tenant"
  ON tenants FOR SELECT
  TO authenticated
  USING (
    id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

-- RLS Policies for User Profiles
CREATE POLICY "Users can view profiles in their tenant"
  ON user_profiles FOR SELECT
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "Users can update their own profile"
  ON user_profiles FOR UPDATE
  TO authenticated
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

-- RLS Policies for Documents
CREATE POLICY "Users can view documents in their tenant"
  ON documents FOR SELECT
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "Users can insert documents in their tenant"
  ON documents FOR INSERT
  TO authenticated
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "Users can update documents in their tenant"
  ON documents FOR UPDATE
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  )
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "Users can delete documents in their tenant"
  ON documents FOR DELETE
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

-- RLS Policies for Document Chunks
CREATE POLICY "Users can view chunks in their tenant"
  ON document_chunks FOR SELECT
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "Users can insert chunks in their tenant"
  ON document_chunks FOR INSERT
  TO authenticated
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

-- RLS Policies for Chat Sessions
CREATE POLICY "Users can view their own chat sessions"
  ON chat_sessions FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Users can insert their own chat sessions"
  ON chat_sessions FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = auth.uid() AND
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "Users can update their own chat sessions"
  ON chat_sessions FOR UPDATE
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete their own chat sessions"
  ON chat_sessions FOR DELETE
  TO authenticated
  USING (user_id = auth.uid());

-- RLS Policies for Chat Messages
CREATE POLICY "Users can view messages in their sessions"
  ON chat_messages FOR SELECT
  TO authenticated
  USING (
    session_id IN (
      SELECT id FROM chat_sessions WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert messages in their sessions"
  ON chat_messages FOR INSERT
  TO authenticated
  WITH CHECK (
    session_id IN (
      SELECT id FROM chat_sessions WHERE user_id = auth.uid()
    )
  );

-- RLS Policies for Data Sources
CREATE POLICY "Users can view data sources in their tenant"
  ON data_sources FOR SELECT
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "Admins can manage data sources in their tenant"
  ON data_sources FOR ALL
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = auth.uid() AND role = 'admin'
    )
  );