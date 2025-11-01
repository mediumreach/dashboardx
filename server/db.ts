import { Pool, neonConfig } from '@neondatabase/serverless';
import { drizzle } from 'drizzle-orm/neon-serverless';
import ws from "ws";
import * as schema from "../shared/schema.js";

neonConfig.webSocketConstructor = ws;

// Make DATABASE_URL optional for development
// The frontend uses Supabase client directly, so this is only needed for server-side operations
const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) {
  console.warn("⚠️  DATABASE_URL not set. Server-side database operations will be limited.");
  console.warn("   Frontend will use Supabase client directly.");
}

export const pool = databaseUrl ? new Pool({ connectionString: databaseUrl }) : null;
export const db = pool ? drizzle({ client: pool, schema }) : null as any;
