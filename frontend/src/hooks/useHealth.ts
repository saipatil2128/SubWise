import { useQuery } from "@tanstack/react-query";

import { getHealth } from "../api/client";

/** Backend liveness for the header indicator. Real Ollama status arrives with M1/M7. */
export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 30_000, retry: 1 });
}
