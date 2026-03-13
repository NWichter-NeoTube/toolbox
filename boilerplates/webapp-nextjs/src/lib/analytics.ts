// Analytics via Umami (privacy-friendly, no cookies)

const UMAMI_HOST = process.env.NEXT_PUBLIC_UMAMI_HOST || '';
const WEBSITE_ID = process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID || '';

export function hasConsent(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem('toolbox_consent') === 'granted';
}

export function grantConsent(): void {
  localStorage.setItem('toolbox_consent', 'granted');
  window.dispatchEvent(new CustomEvent('toolbox:consent', { detail: 'granted' }));
}

export function revokeConsent(): void {
  localStorage.setItem('toolbox_consent', 'denied');
  window.dispatchEvent(new CustomEvent('toolbox:consent', { detail: 'denied' }));
}

export function trackEvent(name: string, data?: Record<string, string | number>): void {
  if (!hasConsent()) return;
  if (typeof window !== 'undefined' && (window as any).umami) {
    (window as any).umami.track(name, data);
  }
}

export function trackPageview(url?: string): void {
  if (!hasConsent()) return;
  if (typeof window !== 'undefined' && (window as any).umami) {
    (window as any).umami.track((props: any) => ({
      ...props,
      url: url || window.location.pathname,
    }));
  }
}

export function getUmamiScriptUrl(): string {
  if (!UMAMI_HOST || !WEBSITE_ID) return '';
  return `${UMAMI_HOST}/script.js`;
}

export function getUmamiWebsiteId(): string {
  return WEBSITE_ID;
}
