-- Enterprise Agent Management System - Database Schema
--
-- This migration creates tables for managing custom agents, credentials,
-- executions, metrics, and health monitoring with full multi-tenant isolation.
--
-- Tables:
--   1. custom_agents - User-created agent configurations
--   2. agent_credentials - Encrypted credentials for agents
--   3. agent_executions - Execution history and logs
--   4. agent_metrics - Performance metrics and analytics
--   5. agent_health_checks - Health monitoring data
--
-- Security:
--   - Row Level Security (RLS) enabled on all tables
--   - Multi-tenant isolation via tenant_id
--   - Encrypted credential storage
--   - Audit logging for all operations

-- ==================== Table 1: custom_agents ====================

CREATE TABLE IF NOT EXISTS custom_agents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Basic Information
  name text NOT NULL,
  description text,
  agent_type text NOT NULL CHECK (agent_type IN (
    'langchain',
    'langgraph',
    'crewai',
    'n8n',
    'make',
    'zapier',
    'webhook',
    'custom'
  )),
  
  -- Configuration
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  capabilities jsonb DEFAULT '{}'::jsonb,
  
  -- Status
  status text NOT NULL DEFAULT 'inactive' CHECK (status IN (
    'active',
    'inactive',
    'error',
    'configuring'
  )),
  
  -- Sharing & Versioning
  is_public boolean DEFAULT false,
  version text DEFAULT '1.0.0',
  
  -- Metadata
  tags text[] DEFAULT ARRAY[]::text[],
  metadata jsonb DEFAULT '{}'::jsonb,
  
  -- Timestamps
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  last_executed_at timestamptz,
  
  -- Constraints
  CONSTRAINT custom_agents_name_tenant_unique UNIQUE (tenant_id, name)
);

-- Enable RLS
ALTER TABLE custom_agents ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_custom_agents_tenant_id ON custom_agents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_custom_agents_user_id ON custom_agents(user_id);
CREATE INDEX IF NOT EXISTS idx_custom_agents_agent_type ON custom_agents(agent_type);
CREATE INDEX IF NOT EXISTS idx_custom_agents_status ON custom_agents(status);
CREATE INDEX IF NOT EXISTS idx_custom_agents_tags ON custom_agents USING gin(tags);

-- RLS Policies
CREATE POLICY "Users can view agents in their tenant"
  ON custom_agents FOR SELECT
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "Users can create agents in their tenant"
  ON custom_agents FOR INSERT
  TO authenticated
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
    AND user_id = auth.uid()
  );

CREATE POLICY "Users can update their own agents"
  ON custom_agents FOR UPDATE
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
    AND (user_id = auth.uid() OR is_public = true)
  )
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "Users can delete their own agents"
  ON custom_agents FOR DELETE
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
    AND user_id = auth.uid()
  );

-- ==================== Table 2: agent_credentials ====================

CREATE TABLE IF NOT EXISTS agent_credentials (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES custom_agents(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  
  -- Credential Information
  credential_type text NOT NULL CHECK (credential_type IN (
    'api_key',
    'oauth',
    'webhook',
    'basic_auth',
    'bearer_token',
    'custom'
  )),
  
  -- Encrypted Storage
  encrypted_value text NOT NULL,
  encryption_key_id text,
  
  -- Metadata
  metadata jsonb DEFAULT '{}'::jsonb,
  
  -- Expiration
  expires_at timestamptz,
  
  -- Timestamps
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  last_used_at timestamptz
);

-- Enable RLS
ALTER TABLE agent_credentials ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agent_credentials_agent_id ON agent_credentials(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_credentials_tenant_id ON agent_credentials(tenant_id);

-- RLS Policies
CREATE POLICY "Users can view credentials for their agents"
  ON agent_credentials FOR SELECT
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
    AND agent_id IN (
      SELECT id FROM custom_agents WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create credentials for their agents"
  ON agent_credentials FOR INSERT
  TO authenticated
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
    AND agent_id IN (
      SELECT id FROM custom_agents WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update credentials for their agents"
  ON agent_credentials FOR UPDATE
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
    AND agent_id IN (
      SELECT id FROM custom_agents WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete credentials for their agents"
  ON agent_credentials FOR DELETE
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
    AND agent_id IN (
      SELECT id FROM custom_agents WHERE user_id = auth.uid()
    )
  );

-- ==================== Table 3: agent_executions ====================

CREATE TABLE IF NOT EXISTS agent_executions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES custom_agents(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Execution Information
  session_id text,
  input_data jsonb NOT NULL,
  output_data jsonb,
  
  -- Status
  status text NOT NULL DEFAULT 'running' CHECK (status IN (
    'running',
    'completed',
    'failed',
    'timeout',
    'cancelled'
  )),
  
  -- Performance Metrics
  execution_time_ms integer,
  tokens_used integer,
  cost_usd numeric(10, 6),
  
  -- Error Information
  error_message text,
  error_stack text,
  
  -- Metadata
  metadata jsonb DEFAULT '{}'::jsonb,
  
  -- Timestamps
  started_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

-- Enable RLS
ALTER TABLE agent_executions ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agent_executions_agent_id ON agent_executions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_tenant_id ON agent_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_user_id ON agent_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_status ON agent_executions(status);
CREATE INDEX IF NOT EXISTS idx_agent_executions_started_at ON agent_executions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_executions_session_id ON agent_executions(session_id);

-- RLS Policies
CREATE POLICY "Users can view executions in their tenant"
  ON agent_executions FOR SELECT
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "Users can create executions for agents in their tenant"
  ON agent_executions FOR INSERT
  TO authenticated
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
    AND user_id = auth.uid()
  );

CREATE POLICY "Users can update their own executions"
  ON agent_executions FOR UPDATE
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
    AND user_id = auth.uid()
  );

-- ==================== Table 4: agent_metrics ====================

CREATE TABLE IF NOT EXISTS agent_metrics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES custom_agents(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  
  -- Metric Information
  metric_type text NOT NULL CHECK (metric_type IN (
    'execution_count',
    'avg_response_time',
    'success_rate',
    'error_rate',
    'token_usage',
    'cost',
    'uptime',
    'custom'
  )),
  
  metric_value numeric NOT NULL,
  metric_unit text,
  
  -- Time Bucket (for time-series data)
  time_bucket timestamptz NOT NULL,
  time_bucket_size text DEFAULT 'hour' CHECK (time_bucket_size IN (
    'minute',
    'hour',
    'day',
    'week',
    'month'
  )),
  
  -- Metadata
  metadata jsonb DEFAULT '{}'::jsonb,
  
  -- Timestamp
  created_at timestamptz DEFAULT now(),
  
  -- Unique constraint for time-series data
  CONSTRAINT agent_metrics_unique UNIQUE (agent_id, metric_type, time_bucket)
);

-- Enable RLS
ALTER TABLE agent_metrics ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent_id ON agent_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_tenant_id ON agent_metrics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_metric_type ON agent_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_time_bucket ON agent_metrics(time_bucket DESC);

-- RLS Policies
CREATE POLICY "Users can view metrics for agents in their tenant"
  ON agent_metrics FOR SELECT
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "System can insert metrics"
  ON agent_metrics FOR INSERT
  TO authenticated
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

-- ==================== Table 5: agent_health_checks ====================

CREATE TABLE IF NOT EXISTS agent_health_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES custom_agents(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  
  -- Health Status
  status text NOT NULL CHECK (status IN (
    'healthy',
    'degraded',
    'unhealthy',
    'unknown'
  )),
  
  -- Performance
  response_time_ms integer,
  
  -- Error Information
  error_message text,
  error_code text,
  
  -- Details
  details jsonb DEFAULT '{}'::jsonb,
  
  -- Timestamp
  checked_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE agent_health_checks ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agent_health_checks_agent_id ON agent_health_checks(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_health_checks_tenant_id ON agent_health_checks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_agent_health_checks_status ON agent_health_checks(status);
CREATE INDEX IF NOT EXISTS idx_agent_health_checks_checked_at ON agent_health_checks(checked_at DESC);

-- RLS Policies
CREATE POLICY "Users can view health checks for agents in their tenant"
  ON agent_health_checks FOR SELECT
  TO authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

CREATE POLICY "System can insert health checks"
  ON agent_health_checks FOR INSERT
  TO authenticated
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles WHERE id = auth.uid()
    )
  );

-- ==================== Triggers ====================

-- Update updated_at timestamp for custom_agents
CREATE TRIGGER update_custom_agents_updated_at
  BEFORE UPDATE ON custom_agents
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Update updated_at timestamp for agent_credentials
CREATE TRIGGER update_agent_credentials_updated_at
  BEFORE UPDATE ON agent_credentials
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ==================== Functions ====================

-- Function to get agent statistics
CREATE OR REPLACE FUNCTION get_agent_statistics(p_agent_id uuid)
RETURNS jsonb AS $$
DECLARE
  result jsonb;
BEGIN
  SELECT jsonb_build_object(
    'total_executions', COUNT(*),
    'successful_executions', COUNT(*) FILTER (WHERE status = 'completed'),
    'failed_executions', COUNT(*) FILTER (WHERE status = 'failed'),
    'avg_execution_time_ms', AVG(execution_time_ms),
    'total_tokens_used', SUM(tokens_used),
    'total_cost_usd', SUM(cost_usd),
    'last_execution', MAX(started_at)
  )
  INTO result
  FROM agent_executions
  WHERE agent_id = p_agent_id;
  
  RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get tenant-wide agent statistics
CREATE OR REPLACE FUNCTION get_tenant_agent_statistics(p_tenant_id uuid)
RETURNS jsonb AS $$
DECLARE
  result jsonb;
BEGIN
  SELECT jsonb_build_object(
    'total_agents', COUNT(DISTINCT ca.id),
    'active_agents', COUNT(DISTINCT ca.id) FILTER (WHERE ca.status = 'active'),
    'total_executions', COUNT(ae.id),
    'successful_executions', COUNT(ae.id) FILTER (WHERE ae.status = 'completed'),
    'failed_executions', COUNT(ae.id) FILTER (WHERE ae.status = 'failed'),
    'avg_execution_time_ms', AVG(ae.execution_time_ms),
    'total_tokens_used', SUM(ae.tokens_used),
    'total_cost_usd', SUM(ae.cost_usd)
  )
  INTO result
  FROM custom_agents ca
  LEFT JOIN agent_executions ae ON ca.id = ae.agent_id
  WHERE ca.tenant_id = p_tenant_id;
  
  RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to clean up old execution records (for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_agent_executions(days_to_keep integer DEFAULT 90)
RETURNS integer AS $$
DECLARE
  deleted_count integer;
BEGIN
  DELETE FROM agent_executions
  WHERE started_at < now() - (days_to_keep || ' days')::interval;
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to clean up old health checks (for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_health_checks(days_to_keep integer DEFAULT 30)
RETURNS integer AS $$
DECLARE
  deleted_count integer;
BEGIN
  DELETE FROM agent_health_checks
  WHERE checked_at < now() - (days_to_keep || ' days')::interval;
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==================== Comments ====================

COMMENT ON TABLE custom_agents IS 'User-created agent configurations with multi-tenant isolation';
COMMENT ON TABLE agent_credentials IS 'Encrypted credentials for agent authentication';
COMMENT ON TABLE agent_executions IS 'Execution history and performance logs for agents';
COMMENT ON TABLE agent_metrics IS 'Time-series performance metrics for agents';
COMMENT ON TABLE agent_health_checks IS 'Health monitoring data for agents';

COMMENT ON COLUMN custom_agents.config IS 'Agent-specific configuration in JSON format';
COMMENT ON COLUMN custom_agents.capabilities IS 'Agent capabilities (streaming, tools, RAG, etc.)';
COMMENT ON COLUMN custom_agents.is_public IS 'Whether agent is shared within tenant';
COMMENT ON COLUMN agent_credentials.encrypted_value IS 'Encrypted credential value (API key, token, etc.)';
COMMENT ON COLUMN agent_executions.execution_time_ms IS 'Total execution time in milliseconds';
COMMENT ON COLUMN agent_executions.tokens_used IS 'Total tokens consumed (for LLM agents)';
COMMENT ON COLUMN agent_metrics.time_bucket IS 'Time bucket for aggregated metrics';
