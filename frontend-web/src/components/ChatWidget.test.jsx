import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ChatWidget from "./ChatWidget";
import { apiFetch, ApiError } from "../api/client";

vi.mock("../api/client", () => {
  class MockApiError extends Error {
    constructor(status, message) {
      super(message);
      this.status = status;
    }
  }
  return {
    apiFetch: vi.fn(),
    ApiError: MockApiError,
  };
});

describe("ChatWidget", () => {
  it("처음에는 플로팅 버튼만 보이고 패널은 닫혀있다", () => {
    render(<ChatWidget />);

    expect(screen.getByLabelText("채팅 열기")).toBeInTheDocument();
    expect(screen.queryByText("433 채팅")).not.toBeInTheDocument();
  });

  it("버튼을 누르면 패널이 열리고 안내 문구가 보인다", async () => {
    render(<ChatWidget />);

    await userEvent.click(screen.getByLabelText("채팅 열기"));

    expect(screen.getByText("433 채팅")).toBeInTheDocument();
    expect(screen.getByText(/근거해서만 답변합니다/)).toBeInTheDocument();
  });

  it("메시지를 보내면 사용자 말풍선과 답변 말풍선이 순서대로 보인다", async () => {
    apiFetch.mockResolvedValue({ reply: "리버풀은 최근 미드필더를 영입했습니다.", matchedArticleCount: 1, sourceType: "ARTICLE" });

    render(<ChatWidget />);
    await userEvent.click(screen.getByLabelText("채팅 열기"));
    await userEvent.type(screen.getByPlaceholderText("메시지를 입력하세요"), "누구 영입했어요?");
    await userEvent.click(screen.getByText("전송"));

    expect(screen.getByText("누구 영입했어요?")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText("리버풀은 최근 미드필더를 영입했습니다.")).toBeInTheDocument()
    );

    expect(apiFetch).toHaveBeenCalledWith(
      "/chat",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ message: "누구 영입했어요?", history: [] }),
      })
    );

    const tag = screen.getByText("저장된 기사 기반");
    expect(tag.dataset.source).toBe("article");
  });

  it("관련 기사를 못 찾으면 AI 일반 지식 태그를 보여준다", async () => {
    apiFetch.mockResolvedValue({
      reply: "발롱도르는 최우수 선수에게 주는 상입니다.",
      matchedArticleCount: 0,
      sourceType: "GENERAL_KNOWLEDGE",
    });

    render(<ChatWidget />);
    await userEvent.click(screen.getByLabelText("채팅 열기"));
    await userEvent.type(screen.getByPlaceholderText("메시지를 입력하세요"), "발롱도르가 뭐야?");
    await userEvent.click(screen.getByText("전송"));

    await waitFor(() => expect(screen.getByText("AI 일반 지식")).toBeInTheDocument());
    expect(screen.getByText("AI 일반 지식").dataset.source).toBe("general");
  });

  it("에러가 나면 에러 말풍선을 보여준다", async () => {
    apiFetch.mockRejectedValue(new ApiError(429, "메시지를 너무 많이 보냈습니다. 잠시 후 다시 시도해주세요."));

    render(<ChatWidget />);
    await userEvent.click(screen.getByLabelText("채팅 열기"));
    await userEvent.type(screen.getByPlaceholderText("메시지를 입력하세요"), "질문");
    await userEvent.click(screen.getByText("전송"));

    await waitFor(() =>
      expect(screen.getByText("메시지를 너무 많이 보냈습니다. 잠시 후 다시 시도해주세요.")).toBeInTheDocument()
    );
  });

  it("닫기 버튼을 누르면 패널이 다시 닫힌다", async () => {
    render(<ChatWidget />);
    await userEvent.click(screen.getByLabelText("채팅 열기"));

    await userEvent.click(screen.getByLabelText("채팅 패널 닫기"));

    expect(screen.queryByText("433 채팅")).not.toBeInTheDocument();
  });
});
