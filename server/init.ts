import type { IStorage } from "./storage.js";

export interface DemoData {
  tenantId: string;
  userId: string;
  sessionId: string;
}

export async function initializeDemoData(storage: IStorage): Promise<DemoData> {
  try {
    // Try to get existing demo user
    const existingUser = await storage.getUserByEmail("demo@example.com");
    
    if (existingUser) {
      // User exists, get their session or create one
      const sessions = await storage.getChatSessions(existingUser.id);
      let sessionId = sessions[0]?.id;
      
      if (!sessionId) {
        const session = await storage.createChatSession({
          tenantId: existingUser.tenantId,
          userId: existingUser.id,
          title: "Demo Chat"
        });
        sessionId = session.id;
      }
      
      console.log(`Using existing demo data:
        Tenant ID: ${existingUser.tenantId}
        User ID: ${existingUser.id}
        Session ID: ${sessionId}`);
      
      return {
        tenantId: existingUser.tenantId,
        userId: existingUser.id,
        sessionId,
      };
    }
  } catch (error) {
    // User doesn't exist, create new demo data
  }

  // Create new demo tenant
  const tenant = await storage.createTenant({
    name: "Demo Organization",
    settings: {}
  });

  // Create demo user
  const user = await storage.createUser({
    id: crypto.randomUUID(),
    tenantId: tenant.id,
    email: "demo@example.com",
    fullName: "Demo User",
    role: "admin",
    isActive: true
  });

  // Create demo chat session
  const session = await storage.createChatSession({
    tenantId: tenant.id,
    userId: user.id,
    title: "Demo Chat"
  });

  console.log(`Demo data initialized:
    Tenant ID: ${tenant.id}
    User ID: ${user.id}
    Session ID: ${session.id}`);

  return {
    tenantId: tenant.id,
    userId: user.id,
    sessionId: session.id
  };
}
