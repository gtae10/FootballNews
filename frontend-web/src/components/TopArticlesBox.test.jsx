import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import TopArticlesBox from "./TopArticlesBox";
import { apiFetch } from "../api/client";

vi.mock("../api/client", () => ({
  apiFetch: vi.fn(),
}));

function makeArticle(id) {
  return {
    id,
    titleKo: `기사 ${id}`,
    source: "BBC Sport",
    originalUrl: `https://example.com/${id}`,
  };
}

function renderTopArticlesBox() {
  return render(
    <MemoryRouter>
      <TopArticlesBox />
    </MemoryRouter>
  );
}

describe("TopArticlesBox", () => {
  it("기본적으로 3건만 보여주고, 더보기를 누르면 전체가 보인다", async () => {
    apiFetch.mockResolvedValue([1, 2, 3, 4, 5].map(makeArticle));

    renderTopArticlesBox();

    await waitFor(() => expect(screen.getByText("기사 1")).toBeInTheDocument());

    expect(screen.getByText("기사 3")).toBeInTheDocument();
    expect(screen.queryByText("기사 4")).not.toBeInTheDocument();

    await userEvent.click(screen.getByText("더보기"));

    expect(screen.getByText("기사 4")).toBeInTheDocument();
    expect(screen.getByText("기사 5")).toBeInTheDocument();
  });

  it("기사가 3건 이하이면 더보기 버튼이 없다", async () => {
    apiFetch.mockResolvedValue([1, 2].map(makeArticle));

    renderTopArticlesBox();

    await waitFor(() => expect(screen.getByText("기사 1")).toBeInTheDocument());

    expect(screen.queryByText("더보기")).not.toBeInTheDocument();
  });

  it("기사가 없으면 아무것도 렌더링하지 않는다", async () => {
    apiFetch.mockResolvedValue([]);

    const { container } = renderTopArticlesBox();

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
