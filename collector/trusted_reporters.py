"""기사 본문 인용에서 감지할 유명 기자/계정 목록과 신뢰도 등급.

tier는 sources.py의 source_tier와 같은 체계를 사용한다 (낮을수록 신뢰도 높음).
기사에 아래 기자/계정이 인용된 것으로 감지되면(reporter_detector.py 참고),
"더 신뢰도 높은 쪽으로만" 즉 기존 매체 자체의 source_tier보다 이 tier가 더
낮을 때만 source_tier를 덮어쓴다 (reporter_detector.resolve_source_tier 참고).

등급 판단 근거:
- Fabrizio Romano, Paul Joyce: 소속 매체(각각 다수 매체 공동 기고 / The Times)가
  있는 정식 저널리스트로 오랜 기간 검증된 트랙레코드를 가진다
  → tier 1 (sources.py의 "공식/대형 매체"와 동급).
- IndyKaila: 익명 X(트위터) 계정. 굵직한 특종을 맞힌 이력이 있지만 오보도 있어
  트랙레코드가 들쭉날쭉하다 → tier 2. Romano/Joyce와 같은 tier 1로 묶지 않되,
  일반 팬 블로그(tier 3)보다는 신뢰도를 높게 쳐서 구분한다.
"""

TRUSTED_REPORTERS = [
    {
        "name": "Fabrizio Romano",
        "aliases": ["Fabrizio Romano", "Romano"],
        "tier": 1,
    },
    {
        "name": "Paul Joyce",
        "aliases": ["Paul Joyce"],
        "tier": 1,
    },
    {
        "name": "IndyKaila",
        "aliases": ["IndyKaila", "Indy Kaila"],
        "tier": 2,
    },
]
