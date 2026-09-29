import { QueryClient } from '@tanstack/react-query';
import { retryOnceOnAuthError } from '../shared/api/client';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: retryOnceOnAuthError,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});
