import { useState } from "react";
import { apiFetch, ApiError } from "../api/client";

// 백엔드 ChatRequest의 방어적 상한(300자, 최근 10턴)과 맞춘다 — 여기서 먼저
// 막으면 사용자가 400 응답을 보기 전에 바로 피드백을 받는다.
const MAX_MESSAGE_LENGTH = 300;
const MAX_HISTORY_TURNS = 10;

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    const userMessage = { role: "user", content: text };
    const history = messages.slice(-MAX_HISTORY_TURNS).map(({ role, content }) => ({ role, content }));

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);

    try {
      const response = await apiFetch("/chat", {
        method: "POST",
        body: JSON.stringify({ message: text, history }),
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.reply, sourceType: response.sourceType },
      ]);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "채팅 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.";
      setMessages((prev) => [...prev, { role: "error", content: message }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      {isOpen && (
        <div className="rf-chat-panel">
          <div className="rf-chat-header">
            <span>433 채팅</span>
            <button type="button" className="rf-chat-close" onClick={() => setIsOpen(false)} aria-label="채팅 패널 닫기">
              ✕
            </button>
          </div>
          <div className="rf-chat-messages">
            {messages.length === 0 && (
              <p className="rf-chat-empty">
                궁금한 이적설이나 소식을 물어보세요. 지금까지 수집된 기사에 근거해서만 답변합니다.
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className="rf-chat-bubble" data-role={m.role}>
                {m.role === "assistant" && (
                  <span
                    className="rf-chat-source-tag"
                    data-source={m.sourceType === "ARTICLE" ? "article" : "general"}
                  >
                    {m.sourceType === "ARTICLE" ? "저장된 기사 기반" : "AI 일반 지식"}
                  </span>
                )}
                {m.content}
              </div>
            ))}
            {sending && (
              <div className="rf-chat-bubble" data-role="assistant">
                답변 작성 중...
              </div>
            )}
          </div>
          <form className="rf-chat-form" onSubmit={handleSubmit}>
            <input
              type="text"
              className="rf-chat-input"
              value={input}
              maxLength={MAX_MESSAGE_LENGTH}
              placeholder="메시지를 입력하세요"
              onChange={(e) => setInput(e.target.value)}
              disabled={sending}
            />
            <button type="submit" className="rf-chat-send" disabled={sending || !input.trim()}>
              전송
            </button>
          </form>
        </div>
      )}
      <button
        type="button"
        className="rf-chat-button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={isOpen ? "채팅 닫기" : "채팅 열기"}
      >
        {isOpen ? "✕" : "💬"}
      </button>
    </>
  );
}
