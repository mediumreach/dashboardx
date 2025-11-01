import type { Express } from "express";
import type { IStorage } from "./storage";
import {
  insertUserProfileSchema,
  insertDocumentSchema,
  insertChatSessionSchema,
  insertChatMessageSchema,
  insertDataSourceSchema,
  insertCustomAgentSchema,
  insertAgentExecutionSchema
} from "@shared/schema";

export function registerRoutes(app: Express, storage: IStorage) {
  
  // Health check
  app.get("/api/health", (_req, res) => {
    res.json({ status: "ok", timestamp: new Date().toISOString() });
  });

  // User routes
  app.get("/api/users/:tenantId", async (req, res) => {
    try {
      const users = await storage.getUsersByTenant(req.params.tenantId);
      res.json(users);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch users" });
    }
  });

  app.post("/api/users", async (req, res) => {
    try {
      const data = insertUserProfileSchema.parse(req.body);
      const user = await storage.createUser(data);
      res.status(201).json(user);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid user data" });
    }
  });

  app.patch("/api/users/:id", async (req, res) => {
    try {
      const user = await storage.updateUser(req.params.id, req.body);
      res.json(user);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to update user" });
    }
  });

  // Document routes
  app.get("/api/documents/:tenantId", async (req, res) => {
    try {
      const documents = await storage.getDocuments(req.params.tenantId);
      res.json(documents);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch documents" });
    }
  });

  app.post("/api/documents", async (req, res) => {
    try {
      const data = insertDocumentSchema.parse(req.body);
      const document = await storage.createDocument(data);
      res.status(201).json(document);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid document data" });
    }
  });

  app.patch("/api/documents/:id", async (req, res) => {
    try {
      const document = await storage.updateDocument(req.params.id, req.body);
      res.json(document);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to update document" });
    }
  });

  app.delete("/api/documents/:id", async (req, res) => {
    try {
      await storage.deleteDocument(req.params.id);
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to delete document" });
    }
  });

  // Chat session routes
  app.get("/api/chat/sessions/:userId", async (req, res) => {
    try {
      const sessions = await storage.getChatSessions(req.params.userId);
      res.json(sessions);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch chat sessions" });
    }
  });

  app.get("/api/chat/sessions/:id/messages", async (req, res) => {
    try {
      const messages = await storage.getChatMessages(req.params.id);
      res.json(messages);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch messages" });
    }
  });

  app.post("/api/chat/sessions", async (req, res) => {
    try {
      const data = insertChatSessionSchema.parse(req.body);
      const session = await storage.createChatSession(data);
      res.status(201).json(session);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid session data" });
    }
  });

  app.post("/api/chat/messages", async (req, res) => {
    try {
      const data = insertChatMessageSchema.parse(req.body);
      const message = await storage.createChatMessage(data);
      res.status(201).json(message);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid message data" });
    }
  });

  app.delete("/api/chat/sessions/:id", async (req, res) => {
    try {
      await storage.deleteChatSession(req.params.id);
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to delete session" });
    }
  });

  // Data source routes
  app.get("/api/data-sources/:tenantId", async (req, res) => {
    try {
      const dataSources = await storage.getDataSources(req.params.tenantId);
      res.json(dataSources);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch data sources" });
    }
  });

  app.post("/api/data-sources", async (req, res) => {
    try {
      const data = insertDataSourceSchema.parse(req.body);
      const dataSource = await storage.createDataSource(data);
      res.status(201).json(dataSource);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid data source" });
    }
  });

  app.patch("/api/data-sources/:id", async (req, res) => {
    try {
      const dataSource = await storage.updateDataSource(req.params.id, req.body);
      res.json(dataSource);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to update data source" });
    }
  });

  app.delete("/api/data-sources/:id", async (req, res) => {
    try {
      await storage.deleteDataSource(req.params.id);
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to delete data source" });
    }
  });

  // Custom agent routes
  app.get("/api/agents/:tenantId", async (req, res) => {
    try {
      const agents = await storage.getCustomAgents(req.params.tenantId);
      res.json(agents);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch agents" });
    }
  });

  app.get("/api/agents/:id/executions", async (req, res) => {
    try {
      const executions = await storage.getAgentExecutions(req.params.id);
      res.json(executions);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch executions" });
    }
  });

  app.post("/api/agents", async (req, res) => {
    try {
      const data = insertCustomAgentSchema.parse(req.body);
      const agent = await storage.createCustomAgent(data);
      res.status(201).json(agent);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid agent data" });
    }
  });

  app.patch("/api/agents/:id", async (req, res) => {
    try {
      const agent = await storage.updateCustomAgent(req.params.id, req.body);
      res.json(agent);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to update agent" });
    }
  });

  app.delete("/api/agents/:id", async (req, res) => {
    try {
      await storage.deleteCustomAgent(req.params.id);
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to delete agent" });
    }
  });

  app.post("/api/agents/:id/execute", async (req, res) => {
    try {
      const executionData = insertAgentExecutionSchema.parse({
        ...req.body,
        agentId: req.params.id
      });
      const execution = await storage.createAgentExecution(executionData);
      
      // Simulate agent execution (this is where you'd integrate LangChain/LangGraph)
      setTimeout(async () => {
        await storage.updateAgentExecution(execution.id, {
          status: "completed",
          outputData: { result: "Agent execution simulated" },
          completedAt: new Date(),
          executionTimeMs: 1000
        });
      }, 1000);
      
      res.status(201).json(execution);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to execute agent" });
    }
  });
}
