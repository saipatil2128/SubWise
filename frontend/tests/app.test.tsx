import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { routes } from "../src/router";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("app shell", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders navigation and the dashboard placeholder", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ version: "0.1.0" }))));
    renderAt("/");
    expect(screen.getByRole("link", { name: "AI Optimizer" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(await screen.findByText("API 0.1.0")).toBeInTheDocument();
  });

  it.each([
    ["/subscriptions", "My Subscriptions", "M12"],
    ["/optimizer", "AI Optimizer", "M13"],
    ["/prices", "Price Intelligence", "M13"],
    ["/history", "Optimization History", "M13"],
    ["/profile", "Profile & Preferences", "M12"],
  ])("%s shows its placeholder naming module %s", (path, heading, module) => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    renderAt(path);
    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`roadmap module ${module}`))).toBeInTheDocument();
  });

  it("shows the backend as offline when /health fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    renderAt("/");
    expect(await screen.findByText("API offline", {}, { timeout: 3000 })).toBeInTheDocument();
  });
});
