import { useSearchParams } from "react-router-dom";
import { API_BASE_URL } from "../api/client";

const AUTH_BASE_URL = API_BASE_URL.replace(/\/api\/v1$/, "");

const ERROR_MESSAGES = {
  email_missing: "구글 계정에서 이메일 정보를 가져올 수 없습니다. 이메일 제공에 동의했는지 확인해 주세요.",
  oauth_failed: "구글 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.",
};

export default function LoginPage() {
  const [searchParams] = useSearchParams();
  const error = searchParams.get("error");
  const errorMessage = error ? ERROR_MESSAGES[error] ?? ERROR_MESSAGES.oauth_failed : null;

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 44,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div className="rf-wordmark">리버풀 뉴스</div>
        <h1 style={{ fontSize: 40, fontWeight: 700, lineHeight: 1.25, letterSpacing: "-.02em", margin: 0 }}>
          해외 축구 뉴스를
          <br />
          한국어로, 신뢰도까지
        </h1>
        <p style={{ fontSize: 15, lineHeight: 1.7, color: "var(--rf-muted-1)", maxWidth: 460, margin: 0 }}>
          전 세계 여러 구단의 원문 기사를 번역해 모아 보고, 출처 신뢰도 등급으로 루머와 사실을 구분합니다.
        </p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start" }}>
        <a
          className="rf-btn-primary"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            background: "var(--rf-text)",
            color: "#111",
            flex: "none",
          }}
          href={`${AUTH_BASE_URL}/oauth2/authorization/google`}
        >
          <span className="rf-mono" style={{ fontWeight: 500, color: "var(--rf-red-dim)" }}>
            G
          </span>
          <span>Google로 시작하기</span>
        </a>
        <div style={{ fontSize: 12, color: "var(--rf-muted-4)", lineHeight: 1.6 }}>
          로그인하면 관심 구단과 알림 설정이 저장됩니다.
        </div>
        {errorMessage && (
          <p role="alert" className="rf-error">
            {errorMessage}
          </p>
        )}
      </div>
    </div>
  );
}
