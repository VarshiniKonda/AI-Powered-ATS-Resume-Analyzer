import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AuthProvider } from "./context/AuthContext";
import { AuthPage } from "./pages/AuthPage";

afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
});

function renderAuthPage(mode: "login" | "register") {
  return render(
    <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <AuthProvider>
        <AuthPage mode={mode} />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("account pages", () => {
  it("renders a login form with accessible email and password inputs", () => {
    renderAuthPage("login");

    expect(screen.getByRole("heading", { name: "Sign in to your workspace" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email address")).toHaveAttribute("type", "email");
    expect(screen.getByLabelText("Password")).toHaveAttribute("autocomplete", "current-password");
  });

  it("renders registration fields and an eight-character password minimum", () => {
    renderAuthPage("register");

    expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Full name")).toBeRequired();
    expect(screen.getByLabelText(/Password/)).toHaveAttribute("minlength", "8");
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
  });
});