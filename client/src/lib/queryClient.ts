import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: async ({ queryKey }) => {
        try {
          const res = await fetch(queryKey[0] as string);

          if (!res.ok) {
            const errorText = await res.text();
            let errorMessage;
            try {
              const errorJson = JSON.parse(errorText);
              errorMessage = errorJson.message || errorText;
            } catch {
              errorMessage = errorText;
            }

            throw new Error(
              `API Error ${res.status}: ${errorMessage}`
            );
          }

          return res.json();
        } catch (error) {
          if (error instanceof Error) {
            throw error;
          }
          throw new Error("Failed to fetch data");
        }
      },
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: Infinity,
      retry: false,
    },
    mutations: {
      retry: false,
    }
  },
});