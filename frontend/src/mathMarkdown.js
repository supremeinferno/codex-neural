const MATH_COMMAND_PATTERN =
  /\\(?:frac|int|sum|prod|sqrt|lim|alpha|beta|gamma|theta|pi|sin|cos|tan|log|ln|cdot|times|neq|leq|geq|approx|infty|partial|Delta|sigma|omega|left|right|text)\b/;

const isEquationLike = (text) =>
  MATH_COMMAND_PATTERN.test(text) &&
  /[=<>^_]/.test(text);

const isStandaloneEquation = (text) =>
  isEquationLike(text) &&
  /^(?:\\(?:frac|int|sum|prod|sqrt|lim|alpha|beta|gamma|theta|pi|sin|cos|tan|log|ln|partial|Delta|sigma|omega)\b|[A-Za-z][A-Za-z0-9_{}^]*\s*[=<>])/.test(text);

const normalizeParentheticalMath = (text) => {
  let result = "";

  for (let index = 0; index < text.length; index += 1) {
    if (text[index] !== "(") {
      result += text[index];
      continue;
    }

    let depth = 1;
    let end = index + 1;
    while (end < text.length && depth > 0) {
      if (text[end] === "(") depth += 1;
      if (text[end] === ")") depth -= 1;
      end += 1;
    }

    if (depth !== 0) {
      result += text[index];
      continue;
    }

    const contents = text.slice(index + 1, end - 1).trim();
    const forIndex = contents.indexOf(" for ");
    const expression = forIndex >= 0
      ? contents.slice(0, forIndex).trim()
      : contents;
    const condition = forIndex >= 0
      ? contents.slice(forIndex + 5).trim()
      : "";
    const parenthesizedCondition = condition.match(/^\(([^()]*)\)$/);

    if (isEquationLike(contents) && forIndex < 0) {
      result += `$${contents}$`;
    } else if (
      forIndex >= 0 &&
      isEquationLike(expression) &&
      parenthesizedCondition &&
      MATH_COMMAND_PATTERN.test(parenthesizedCondition[1])
    ) {
      result += `$${expression}$ for $${parenthesizedCondition[1]}$`;
    } else {
      result += text.slice(index, end);
    }

    index = end - 1;
  }

  return result;
};

const normalizeMathText = (text) => {
  let normalized = text
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, formula) => `\n$$\n${formula.trim()}\n$$\n`)
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, formula) => `$${formula.trim()}$`);

  normalized = normalized
    .split(/(\n\s*\n)/)
    .map((block) => {
      if (/^\n\s*\n$/.test(block)) return block;

      let formula = block.trim();
      const bracketedFormula = formula.match(/^\[\s*([\s\S]*?)\s*\]$/);
      if (bracketedFormula && isEquationLike(bracketedFormula[1])) {
        formula = bracketedFormula[1].trim();
      }

      if (
        !formula.includes("$") &&
        isStandaloneEquation(formula) &&
        !/^(?:#{1,6}\s|[-*+]\s|\d+\.\s|>)/.test(formula)
      ) {
        return `$$\n${formula}\n$$`;
      }

      return normalizeParentheticalMath(block);
    })
    .join("");

  return normalized;
};

export const normalizeMathMarkdown = (markdown) =>
  markdown
    .split(/(```[\s\S]*?```|~~~[\s\S]*?~~~|`+[^`\n]*?`+)/g)
    .map((part) =>
      /^(```|~~~|`)/.test(part) ? part : normalizeMathText(part)
    )
    .join("");
