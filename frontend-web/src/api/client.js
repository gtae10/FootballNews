export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080/api/v1";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let message = `요청에 실패했습니다: ${path} (${response.status})`;
    try {
      const body = await response.json();
      if (body?.message) message = body.message;
    } catch {
      // 응답 본문이 JSON이 아니면(빈 본문 등) 기본 메시지를 그대로 쓴다.
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
