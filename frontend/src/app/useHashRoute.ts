import { useCallback, useEffect, useState } from 'react';
import { isAppRoute, type AppRoute } from './navigation';

function routeFromHash(): AppRoute {
  if (typeof window === 'undefined') return '/';
  const rawRoute = window.location.hash.replace(/^#/, '') || '/';
  return isAppRoute(rawRoute) ? rawRoute : '/';
}

export function useHashRoute() {
  const [route, setRoute] = useState<AppRoute>(routeFromHash);

  useEffect(() => {
    const handleHashChange = () => setRoute(routeFromHash());
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigate = useCallback((nextRoute: AppRoute) => {
    if (routeFromHash() === nextRoute) {
      setRoute(nextRoute);
      return;
    }
    window.location.hash = nextRoute;
  }, []);

  return { route, navigate };
}
