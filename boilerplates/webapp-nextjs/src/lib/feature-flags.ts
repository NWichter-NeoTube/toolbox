// Feature flags via environment variables
// Simple ENV-based approach - no external service needed

export function isFeatureEnabled(flag: string): boolean {
  const envKey = `NEXT_PUBLIC_FEATURE_${flag.toUpperCase()}`;
  const value = process.env[envKey];
  return value === 'true' || value === '1';
}

export function getAllFlags(): Record<string, boolean> {
  const flags: Record<string, boolean> = {};
  const prefix = 'NEXT_PUBLIC_FEATURE_';
  for (const [key, value] of Object.entries(process.env)) {
    if (key.startsWith(prefix) && value !== undefined) {
      const flagName = key.slice(prefix.length).toLowerCase();
      flags[flagName] = value === 'true' || value === '1';
    }
  }
  return flags;
}
