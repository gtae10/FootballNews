import { describe, expect, it } from "vitest";
import { splitIntoParagraphs } from "./articleDisplay";

describe("splitIntoParagraphs", () => {
  it("returns an empty array for empty or missing text", () => {
    expect(splitIntoParagraphs("")).toEqual([]);
    expect(splitIntoParagraphs(null)).toEqual([]);
    expect(splitIntoParagraphs(undefined)).toEqual([]);
  });

  it("splits already-newline-separated text on the newlines", () => {
    const text = "첫 번째 문단입니다.\n\n두 번째 문단입니다.\n세 번째 문단입니다.";

    expect(splitIntoParagraphs(text)).toEqual([
      "첫 번째 문단입니다.",
      "두 번째 문단입니다.",
      "세 번째 문단입니다.",
    ]);
  });

  it("groups a single unbroken summary into two-sentence paragraphs", () => {
    const text = "첫 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다. 네 번째 문장입니다.";

    expect(splitIntoParagraphs(text)).toEqual([
      "첫 문장입니다. 두 번째 문장입니다.",
      "세 번째 문장입니다. 네 번째 문장입니다.",
    ]);
  });

  it("keeps a trailing odd sentence as its own paragraph", () => {
    const text = "첫 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다.";

    expect(splitIntoParagraphs(text)).toEqual([
      "첫 문장입니다. 두 번째 문장입니다.",
      "세 번째 문장입니다.",
    ]);
  });

  it("returns the whole text as one paragraph when it has no sentence-ending punctuation", () => {
    const text = "문장부호가 전혀 없는 텍스트";

    expect(splitIntoParagraphs(text)).toEqual(["문장부호가 전혀 없는 텍스트"]);
  });
});
