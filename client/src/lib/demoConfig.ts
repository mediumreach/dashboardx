let demoConfig: {
  tenantId: string;
  userId: string;
  sessionId: string;
} | null = null;

export async function getDemoConfig() {
  if (!demoConfig) {
    const res = await fetch('/api/demo/config');
    demoConfig = await res.json();
  }
  return demoConfig;
}
