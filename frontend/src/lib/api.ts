// Inside Splunk Web (static/app/netspout) API calls go through the app's authenticated REST gateway on the Splunk
// origin; Splunk forwards them to the backend server-side, so the browser never contacts the backend port.
function splunkGatewayBase(): string | null {
  const m = typeof window === 'undefined' ? null : window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\/static\/app\/netspout\//);
  return m ? `/${m[1]}/splunkd/__raw/services/netspout_gateway` : null;
}

// Splunk rejects POSTs to splunkd/__raw without its CSRF header; add it to gateway calls only.
if (typeof window !== 'undefined' && splunkGatewayBase()) {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes('/splunkd/__raw/services/netspout_gateway')) return nativeFetch(input, init);
    const token = document.cookie.split('; ').find((c) => c.startsWith('splunkweb_csrf_token'))?.split('=')[1] ?? '';
    const headers = new Headers(init?.headers);
    headers.set('X-Splunk-Form-Key', token);
    headers.set('X-Requested-With', 'XMLHttpRequest');
    return nativeFetch(input, { ...init, headers });
  };
}

function configuredApiBase(): string | null {
  if (typeof document === 'undefined') return null;
  const value = document
    .querySelector<HTMLMetaElement>('meta[name="netspout-api-base"]')
    ?.content.trim();
  if (value) return value;
  const gateway = splunkGatewayBase();
  if (gateway) return gateway;
  // Splunk-hosted iframe: the canvas passes the backend origin. Loopback only, matching the backend CORS policy,
  // so a crafted link cannot redirect API calls (and credentials) to another host.
  const param = new URLSearchParams(window.location.search).get('api_base') ?? '';
  return /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$/.test(param) ? param : null;
}

export function getApiBaseUrl(): string {
  if (typeof window === 'undefined') return '';

  const configured = configuredApiBase();
  if (configured) return configured.replace(/\/$/, '');

  if (window.location.port === '5173') return '';
  return window.location.origin;
}

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalizedPath}`;
}

export async function fetchJson<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = 5000,
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(apiUrl(path), {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...init?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timeout);
  }
}
