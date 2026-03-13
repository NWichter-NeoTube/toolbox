// Server-side analytics via Umami HTTP API

const UMAMI_HOST = process.env.NEXT_PUBLIC_UMAMI_HOST || '';
const WEBSITE_ID = process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID || '';

export async function trackServerEvent(
  name: string,
  data?: Record<string, string | number>,
  options?: { url?: string; referrer?: string }
): Promise<void> {
  if (!UMAMI_HOST || !WEBSITE_ID) return;

  try {
    await fetch(`${UMAMI_HOST}/api/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        payload: {
          website: WEBSITE_ID,
          name,
          data,
          url: options?.url || '/',
          referrer: options?.referrer || '',
        },
        type: 'event',
      }),
    });
  } catch {
    // Silently fail - analytics should never break the app
  }
}
