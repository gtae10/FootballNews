"""수집 대상 뉴스 소스 목록.

각 소스는 RSS를 우선 사용하고, RSS가 없는 경우 크롤링 설정을 사용합니다.
등록 전 각 사이트의 robots.txt와 실제 RSS 응답을 직접 확인했습니다 (2026-09 기준).

- 리버풀 공식 사이트(liverpoolfc.com)는 현재 공개된 RSS 피드를 제공하지 않아 제외했습니다.
- 아래 리버풀 팬 매체 3개 소스는 모두 robots.txt에서 크롤링을 명시적으로 허용하고 있고,
  RSS 피드가 정상적으로 리버풀 관련 기사를 반환하는 것을 확인했습니다. `forced_club`이
  "Liverpool"로 고정되어 있어(club_matcher가 본문에서 감지하는 구단과 별개로) 항상
  Liverpool 태그가 붙는다 — 해당 매체 성격상 팀 이름을 안 쓰고 "Reds"/"the club" 등으로만
  지칭하는 기사도 있기 때문이다.
- 해외축구 전반을 다루는 대형/전문 매체 후보로 BBC Football, Guardian Football, ESPN
  Soccer도 검토했지만 제외했다: BBC와 Guardian은 robots.txt 상단에 "AI 요약/재사용 금지"를
  평문으로 명시하고 있고, Guardian과 ESPN은 robots.txt에서 `anthropic-ai`/`ClaudeBot` 등을
  명시적으로 지목해 사이트 전체를 차단하고 있다 — 이 프로젝트가 하는 일(LLM 요약 번역 후
  게시)과 정면으로 충돌해 추가하지 않았다.
- 대신 robots.txt에 AI 크롤러 차단이나 재사용 금지 문구가 없는 아래 4개 매체를 추가했다.
  Independent와 Sky Sports는 대형 정식 매체라 source_tier 1, Football365와 90min은 축구
  전문 매체지만 대형 매체만큼의 편집 검증 체계는 아니라고 보고 source_tier 2로 뒀다.
  90min은 RSS 피드 항목이 항상 발행일 최신순은 아님을 확인했다(예: 약 11개월 전 기사가
  섞여 나옴) — `published_at`은 피드에 실린 실제 값을 그대로 저장하므로 정렬 자체는 API가
  다시 처리하지만, `?paged=N` 백필이 다른 워드프레스 소스처럼 깔끔하게 과거순으로 안 쌓일
  수 있다는 점은 감안한다.
- 이 4개 소스는 `forced_club`을 지정하지 않는다 — 리버풀 전용이 아니라 다양한 구단을
  다루므로, club_matcher.detect_clubs()가 본문에서 언급된 구단을 그때그때 감지한다.
- 2026-09 추가 조사에서 검토했지만 모두 제외한 후보: Marca(robots.txt에
  `anthropic-ai: Disallow: /` 명시), Football Italia(robots.txt가 링크하는
  `m4ow.uk/socw/2.txt` "Search Only Terms" 계약이 AI 학습/데이터마이닝/임베딩 생성을
  전면 금지하고 위반 시 건당 £500 청구 조항까지 명시 — robots.txt 자체에는 AI 봇을
  개별 차단하는 줄이 없어도 이 링크된 약관이 사실상의 금지 문구다), talkSPORT
  (robots.txt 주석에 "LLM 무단 사용 불허" 명시, GPTBot/ChatGPT-User는 명시적 허용
  목록에 있지만 ClaudeBot/anthropic-ai는 빠져 있어 기본 `Disallow: /`에 걸림),
  Metro(robots.txt 주석에 AI/LLM 개발 목적 금지 명시 + ClaudeBot/anthropic-ai/
  Claude-Web 등을 `Disallow: /`로 차단), Liverpool Echo(robots.txt에 ClaudeBot/
  anthropic-ai/Claude-Web/GPTBot 각각 `Disallow: /`). 다섯 곳 모두 애매한 판단 없이
  명확한 차단 근거가 있어 추가하지 않았다.

source_tier: 낮을수록 신뢰도가 높다고 간주한다 (1=공식/대형 매체, 2=자체 취재를 하는
전문 매체, 3=팬 블로그 성격의 매체). "오늘의 주요 소식" 정렬에 사용된다.
"""

RSS_SOURCES = [
    {
        "name": "The Anfield Wrap",
        "rss_url": "https://theanfieldwrap.com/feed/",
        "forced_club": "Liverpool",
        "source_tier": 2,
    },
    {
        "name": "Empire of The Kop",
        "rss_url": "https://www.empireofthekop.com/feed/",
        "forced_club": "Liverpool",
        "source_tier": 3,
    },
    {
        "name": "Anfield Watch",
        "rss_url": "https://anfieldwatch.co.uk/feed/",
        "forced_club": "Liverpool",
        "source_tier": 3,
    },
    {
        "name": "Sky Sports Football",
        "rss_url": "https://www.skysports.com/rss/11095",
        "forced_club": None,
        "source_tier": 1,
    },
    {
        "name": "Independent Football",
        "rss_url": "https://www.independent.co.uk/sport/football/rss",
        "forced_club": None,
        "source_tier": 1,
    },
    {
        "name": "Football365",
        "rss_url": "https://www.football365.com/rss",
        "forced_club": None,
        "source_tier": 2,
    },
    {
        "name": "90min",
        "rss_url": "https://www.90min.com/feed",
        "forced_club": None,
        "source_tier": 2,
    },
]

CRAWL_SOURCES = [
    # 위 RSS_SOURCES 3곳이 모두 RSS를 제공하므로 현재는 별도 크롤링 대상이 없다.
    # 세 소스 모두 RSS가 `?paged=N` 파라미터로 과거 페이지 조회까지 지원함을
    # 확인했으므로(2026-09 기준, backfill.py 참고), 과거 기사 수집도 크롤링 없이
    # RSS만으로 충분하다. RSS가 없는 매체를 추가할 때는 아래 형식을 사용하고,
    # 등록 전 robots.txt와 이용약관을 먼저 확인한다.
    # {
    #     "name": "매체명",
    #     "list_url": "https://example.com/liverpool",
    #     "article_selector": "a.article-link",
    #     "club": "Liverpool",
    #     "source_tier": 2,
    # },
]
