import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Login from "./login";

describe("Login form", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  it("submits credentials and passes the returned user and token to the app", async () => {
    const onLogin = vi.fn();
    globalThis.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        user: { id: 12, email: "researcher@example.com" },
        token: "session-token",
      }),
    });

    render(<Login onLogin={onLogin} />);
    fireEvent.change(screen.getByPlaceholderText("Enter your email"), {
      target: { value: "  researcher@example.com  " },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter your password"), {
      target: { value: "test-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /SIGN IN/ }));

    await waitFor(() => {
      expect(onLogin).toHaveBeenCalledWith(
        { id: 12, email: "researcher@example.com" },
        "session-token",
      );
    });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/login$/),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "researcher@example.com",
          password: "test-password",
        }),
      }),
    );
  });

  it("shows a rejected login message without starting a session", async () => {
    const onLogin = vi.fn();
    globalThis.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        success: false,
        message: "Invalid email or password.",
      }),
    });

    render(<Login onLogin={onLogin} />);
    fireEvent.change(screen.getByPlaceholderText("Enter your email"), {
      target: { value: "researcher@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter your password"), {
      target: { value: "wrong-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /SIGN IN/ }));

    expect(await screen.findByText("Invalid email or password.")).toBeTruthy();
    expect(onLogin).not.toHaveBeenCalled();
  });
});
