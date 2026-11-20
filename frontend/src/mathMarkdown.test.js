import { describe, expect, it } from "vitest";
import { normalizeMathMarkdown } from "./mathMarkdown";

describe("normalizeMathMarkdown", () => {
  it("converts alternate inline and display delimiters", () => {
    expect(normalizeMathMarkdown(String.raw`Inline \(x^2\) and \[y^2\]`))
      .toBe("Inline $x^2$ and \n$$\ny^2\n$$\n");
  });

  it("wraps a standalone bracketed formula as display math", () => {
    const result = normalizeMathMarkdown(String.raw`[ a_n = \frac{1}{n} ]`);

    expect(result).toContain("$$\na_n = \\frac{1}{n}\n$$");
  });

  it("normalizes formulae inside prose without wrapping the whole paragraph", () => {
    const result = normalizeMathMarkdown(
      String.raw`Because (\int_{-L}^{L} f(x)\,dx = 0 for (m\neq n)) the functions are orthogonal.`,
    );

    expect(result).toContain("$\\int_{-L}^{L} f(x)\\,dx = 0$ for $m\\neq n$");
    expect(result.startsWith("$$")).toBe(false);
  });

  it("preserves inline code, fenced code and ordinary currency", () => {
    const source = [
      String.raw`Code: \`$not math$\``,
      "",
      "```tex",
      String.raw`\int x`,
      "```",
      "",
      String.raw`A price is $5.`,
    ].join("\n");

    expect(normalizeMathMarkdown(source)).toBe(source);
  });
});
