function configuredApiBase(): string | null {
  if (typeof document === 'undefined') return null;
  const value = document
    .querySelector<HTMLMetaElement>('meta[name="netspout-api-base"]')
    ?.content.trim();
  return value || null;
}

export function getApiBaseUrl(): string {
  if (typeof window === 'undefined') return '';

  const configured = configuredApiBase();
  if (configured) return configured.replace(/\/$/, '');

  if (window.location.port === '8081') return window.location.origin;
  if (window.location.port === '5173') return '';

  const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
  return `${protocol}//${window.location.hostname}:8081`;
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
