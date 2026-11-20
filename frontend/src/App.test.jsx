import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const response = (body, ok = true) => ({
  ok,
  status: ok ? 200 : 400,
  json: async () => body,
});

describe("Technical mode research flow", () => {
  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem("codex_user", JSON.stringify({
      id: 8,
      email: "researcher@example.com",
    }));
    sessionStorage.setItem("codex_token", "test-session-token");
    sessionStorage.setItem("codex_active_tab", "nexus");

    globalThis.fetch = vi.fn(async (input, options = {}) => {
      const url = String(input);
      const method = options.method || "GET";

      if (url.endsWith("/api/session")) return response({ user: { id: 8 } });
      if (url.endsWith("/api/research/clarify")) {
        return response({ success: true, topic: "Clarified draft" });
      }
      if (url.endsWith("/api/conversations") && method === "POST") {
        return response({ id: 42, title: "Clarified draft", kind: "research" });
      }
      if (url.endsWith("/api/research")) {
        return response({ title: "Research title", report: "Research body" });
      }
      return response({ success: true });
    });
  });

  it("waits for draft approval and sends the edited prompt to research and history", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "TECHNICAL MODE OFF" }));
    fireEvent.change(screen.getByPlaceholderText("What do you want to investigate?"), {
      target: { value: "Original topic" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^REVIEW PROMPT/ }));

    await screen.findByRole("textbox", { name: "Review the interpreted research prompt" });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/research\/clarify$/),
      expect.objectContaining({
        body: JSON.stringify({ topic: "Original topic" }),
      }),
    );
    expect(globalThis.fetch).not.toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/conversations$/),
      expect.objectContaining({ method: "POST" }),
    );

    fireEvent.change(screen.getByRole("textbox", {
      name: "Review the interpreted research prompt",
    }), { target: { value: "User-approved topic" } });
    fireEvent.click(screen.getByRole("button", { name: /APPROVE & RESEARCH/ }));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/research$/),
        expect.objectContaining({
          body: JSON.stringify({ topic: "User-approved topic" }),
        }),
      );
    });

    const messageCalls = globalThis.fetch.mock.calls.filter(([url]) =>
      String(url).endsWith("/messages"),
    );
    expect(messageCalls[0][1].body).toContain("User-approved topic");
    expect(await screen.findByRole("heading", { name: "Research title" })).toBeTruthy();
  });
});
