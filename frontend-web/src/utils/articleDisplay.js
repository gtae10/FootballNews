// 기사 sourceTier(1~5, 낮을수록 신뢰도 높음)를 뱃지로 보여줄 때 쓰는 라벨/색상.
// RedFeed.dc.html 시안의 TIERS 표기를 그대로 참고했다.
export const TIER_BADGES = {
  1: { label: "T1 공식 발표", color: "var(--rf-tier-1)" },
  2: { label: "T2 검증된 매체", color: "var(--rf-tier-2)" },
  3: { label: "T3 유력 기자", color: "var(--rf-tier-3)" },
  4: { label: "T4 지역 매체", color: "var(--rf-tier-4)" },
  5: { label: "T5 루머", color: "var(--rf-tier-5)" },
};

export function tierBadge(sourceTier) {
  const num = Math.min(Math.max(sourceTier ?? 5, 1), 5);
  return TIER_BADGES[num];
}

export function timeAgo(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const minutes = Math.floor((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return "방금";
  if (minutes < 60) return `${minutes}분 전`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}시간 전`;
  if (minutes < 10080) return `${Math.floor(minutes / 1440)}일 전`;
  return `${date.getMonth() + 1}월 ${date.getDate()}일`;
}
