import { ApiError } from "../api/client";

// 로그인된 상태로 화면에 들어온 뒤 세션이 만료되는 등 인증이 필요한 API 호출이
// 401을 반환하면, 에러 메시지를 보여주는 대신 로그인 페이지로 보낸다.
export function isUnauthorized(err) {
  return err instanceof ApiError && err.status === 401;
}
