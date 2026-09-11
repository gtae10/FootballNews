# API 명세 (초안)

기본 경로: `/api/v1`

## 기사 목록 조회

```
GET /articles
```

쿼리 파라미터
- `page` (기본 0)
- `size` (기본 20)
- `club`: 특정 구단 기사만 필터링 (선택, 예: `club=Liverpool`). 기사 하나가 여러 구단을 언급할 수 있어
  응답의 `clubs`는 배열이지만, 이 필터 파라미터는 단일 구단명만 받는다 — 그 구단이 `clubs` 배열에
  포함된 기사가 매칭된다. 프론트의 "전체" 탭 안 보조 필터(개별 구단 드롭다운)가 사용한다.
- `clubs`: 구단 목록 중 하나라도 겹치는 기사를 모두 반환 (선택, 콤마 구분, 예: `clubs=Liverpool,Arsenal`).
  프론트의 "관심구단" 탭이 사용자가 팔로우한 구단 전체를 조회할 때 쓴다(`docs/FEATURE_STATUS.md` 참고).
  `club`과 `clubs`를 동시에 넘기면 `clubs`가 우선한다(둘 다 비어있지 않을 경우). 목록이 비어 있으면
  아무 필터도 적용되지 않은 것으로 취급한다(빈 IN 목록으로 인해 결과가 0건이 되는 것을 방지).
- `category`: 카테고리 필터링 (선택, `MATCH`/`TRANSFER`/`PLAYER`/`OTHER` 중 하나, 대소문자 구분 없음).
  `docs/DB_SCHEMA.md`의 `articles.category` 참고. 알 수 없는 값을 넘기면 400을 반환한다.
- `from`, `to`: 발행일 범위 필터 (선택, 미구현)
- `keyword`: 제목 검색 (선택, 구현됨). 번역 제목(`titleKo`) 또는 원문 제목(`titleOriginal`) 중
  하나라도 검색어를 포함하면 매칭된다 (대소문자 구분 없음, 부분 일치). 아직 번역되지 않은 기사는
  `titleOriginal` 기준으로만 매칭된다. 본문(`content`)은 검색 대상이 아니다.
- `club`(또는 `clubs`), `category`, `keyword`를 함께 지정하면 모두 AND 조건으로 적용된다.

응답 예시 (Spring Data `Page` 직렬화 형식 그대로 반환됨. 현재 페이지 인덱스는 `page`가 아니라 `number`)
```json
{
  "content": [
    {
      "id": 1,
      "titleKo": "리버풀, 다음 시즌 새 유니폼 공개",
      "source": "Liverpool FC 공식",
      "publishedAt": "2026-08-30T10:00:00Z",
      "originalUrl": "https://...",
      "clubs": ["Liverpool"],
      "sourceTier": 1,
      "imageUrl": "https://source-site.com/images/thumb.jpg",
      "category": "TRANSFER"
    }
  ],
  "number": 0,
  "size": 20,
  "totalElements": 132,
  "totalPages": 7,
  "first": true,
  "last": false,
  "numberOfElements": 20,
  "empty": false
}
```

`clubs`는 기사 본문에서 자동 감지된 구단명 배열이다 (이적 기사 등 여러 구단을 언급하면 2개 이상 담긴다).
리그 전반 이슈처럼 특정 구단이 감지되지 않은 기사는 빈 배열(`[]`)로 내려온다.

`category`는 `MATCH`/`TRANSFER`/`PLAYER`/`OTHER` 중 하나이며, 아직 분류되지 않은 기사는
`null`이다 (`docs/DB_SCHEMA.md`의 `articles.category` 참고).

`imageUrl`은 RSS에서 찾은 대표 이미지의 원본 URL이다 (이미지 자체는 우리 서버에 저장하지 않는다 —
`docs/DB_SCHEMA.md`의 `articles.image_url` 참고). 찾지 못했거나 이 컬럼 도입 이전에 수집된 기사는
`null`이며, 프론트엔드는 이 경우 이미지 영역 없이 텍스트만 표시해야 한다. 원본 서버가 핫링크를
차단하거나 이미지를 삭제하면 로드에 실패할 수 있으므로, 프론트는 이미지 로드 실패 시에도 텍스트만으로
정상 표시되게 처리한다.

## 오늘의 주요 소식

```
GET /articles/top
```

쿼리 파라미터
- `limit` (기본 10)

당일(00:00 이후) 발행된 기사 중 발행 시각 최신순 → 소스 신뢰도(`sourceTier`, 낮을수록 신뢰도 높음, 없으면 최하위 취급)순으로
정렬해 상위 `limit`건을 반환한다. 인증 불필요. 응답 형식은 `GET /articles`의 `content` 배열 원소와 동일하다.

## 기사 상세 조회

```
GET /articles/{id}
```

응답 예시
```json
{
  "id": 1,
  "titleKo": "리버풀, 다음 시즌 새 유니폼 공개",
  "titleOriginal": "Liverpool unveil new kit for next season",
  "contentKo": "번역된 본문 요약...",
  "source": "Liverpool FC 공식",
  "originalUrl": "https://...",
  "publishedAt": "2026-08-30T10:00:00Z",
  "translatedAt": "2026-08-30T10:05:00Z",
  "sourceTier": 1,
  "imageUrl": "https://source-site.com/images/thumb.jpg",
  "category": "TRANSFER",
  "images": [
    "https://source-site.com/images/body1.jpg",
    "https://source-site.com/images/body2.jpg"
  ]
}
```

`images`는 원문 기사 페이지 본문을 크롤링해 추가로 찾은 이미지 URL 목록이다(원문에 실린 순서
그대로, 최대 5개, `collector/body_image_extractor.py` 참고). `imageUrl`과 마찬가지로 이미지
파일 자체는 저장하지 않고 원본 서버 URL만 담는다. 크롤링이 실패했거나(네트워크 오류, 소스가
크롤링을 막음 등) 본문에서 이미지를 찾지 못하면 빈 배열(`[]`)이며, 이 경우 프론트엔드는
`imageUrl` 하나만 대표 이미지로 표시하는 것으로 자연스럽게 폴백해야 한다.

## 상태 코드

| 코드 | 의미 |
|---|---|
| 200 | 정상 응답 |
| 404 | 존재하지 않는 기사 |
| 500 | 서버 오류 |

에러 응답 본문은 API 전체에서 공통적으로 아래 형식을 따른다 (스택트레이스 등 민감 정보는 포함하지 않음).
```json
{ "message": "기사를 찾을 수 없습니다: 999999" }
```

## 인증

로그인은 Google OAuth2로 처리한다. 인증 성공 시 서버가 발급한 JWT를 httpOnly 쿠키(`access_token`)로 내려주며,
이후 요청은 이 쿠키를 통해 인증된다 (별도 Authorization 헤더 불필요, `credentials: 'include'`로 요청).

```
GET /oauth2/authorization/google   # 구글 로그인 시작 (풀 페이지 리다이렉트)
```

로그인 성공 시 `app.frontend-base-url`(기본 `http://localhost:5173`)로 리다이렉트되며 쿠키가 설정된다.

### 현재 사용자 조회

```
GET /auth/me
```

인증 쿠키가 없거나 유효하지 않으면 401을 반환한다.

응답 예시
```json
{
  "id": 1,
  "email": "user@example.com",
  "nickname": null,
  "onboarded": false
}
```

### 로그아웃

```
POST /auth/logout
```

인증 쿠키를 만료시킨다.

## 상태 코드 (인증 포함)

| 코드 | 의미 |
|---|---|
| 401 | 인증이 필요한 API에 인증 없이 접근 |

## 구단 목록

```
GET /clubs
```

인증 불필요. 5대 리그 주요 구단을 리그/이름순으로 반환한다 (프론트에서 `league` 기준으로 그룹핑).

응답 예시
```json
[
  { "id": 1, "name": "Arsenal", "league": "EPL" },
  { "id": 2, "name": "Real Madrid", "league": "LA_LIGA" }
]
```

## 루머 스레드 타임라인

같은 이적 건(선수 + 구단)으로 묶인 기사들의 타임라인. 규칙 기반 클러스터링 결과이며
(LLM 미사용), 선수명은 제목에서 정규식으로 추출한 후보라 완벽하지 않을 수 있다
(`docs/DB_SCHEMA.md`의 `rumor_threads` 절 참고).

```
GET /rumor-threads
```

쿼리 파라미터
- `sort`: `independent`(기본값) — `independentSourceCount` 내림차순, 동률이면 최근 갱신순.
  `latest` — 최근 갱신순만.

인증 불필요.

응답 예시
```json
[
  {
    "id": 793,
    "playerName": "Lamine Camara",
    "clubName": "Chelsea",
    "latestStage": "NEGOTIATION",
    "independentSourceCount": 2,
    "crossReported": true,
    "articleCount": 2,
    "createdAt": "2026-09-05T08:12:19.978472",
    "updatedAt": "2026-09-05T08:12:20.103558"
  }
]
```

`latestStage`는 스레드에 포함된 기사들 중 가장 진전된 단계다: `UNKNOWN` < `INTEREST` <
`NEGOTIATION` < `CONFIRMED` < `OFFICIAL`.

**`independentSourceCount`/`crossReported`에 대한 중요한 주의**: 이 값은 스레드 최초
기사 발행 후 48시간 이내에 서로 다른 매체(`source`)가 몇 곳이나 같은 건을 독립적으로
보도했는지를 뜻한다. **"여러 매체가 같은 이야기를 하고 있다"는 뜻이지, "이적이 사실로
확인됐다"는 뜻이 아니다.** `verified_source_count`처럼 "검증됨"으로 오해할 수 있는
이름 대신 `independent`/`cross_reported`를 의도적으로 사용했다 — 오보를 여러 매체가
동시에 베껴 쓴 경우도 이 값이 높게 나올 수 있다.

## 루머 스레드 상세 (타임라인)

```
GET /rumor-threads/{id}
```

인증 불필요. 소속 기사를 발행 시각 오름차순으로 포함한다 — "8/28 최초 보도 → 8/30
확인 → 9/1 공식 발표" 같은 타임라인을 그대로 재구성할 수 있다.

응답 예시
```json
{
  "id": 793,
  "playerName": "Lamine Camara",
  "clubName": "Chelsea",
  "latestStage": "NEGOTIATION",
  "independentSourceCount": 2,
  "crossReported": true,
  "createdAt": "2026-09-05T08:12:19.978472",
  "updatedAt": "2026-09-05T08:12:20.103558",
  "articles": [
    {
      "id": 240,
      "source": "Empire of The Kop",
      "titleKo": null,
      "titleOriginal": "Liverpool may be encouraged by what Monaco chief told Lamine Camara after deadline day drama",
      "originalUrl": "https://www.empireofthekop.com/...",
      "publishedAt": "2026-09-02T15:01:42",
      "storyStage": "NEGOTIATION"
    }
  ]
}
```

`articles[].titleKo`는 해당 기사가 아직 번역되지 않았으면 `null`이다 (그 경우
`titleOriginal`을 사용). 존재하지 않는 스레드 id를 조회하면 404를 반환한다.

## 온보딩 / 관심 구단 설정

```
GET /users/me/preferences
PUT /users/me/preferences
```

인증 필요. `GET`은 온보딩을 완료하지 않은 사용자에 대해 400을 반환한다.

`PUT` 요청 본문
```json
{
  "clubIds": [1, 2],
  "notificationTrustLevel": 3,
  "favoriteClubId": 1
}
```

`notificationTrustLevel`은 1(공식 소스만) ~ 5(모든 소스) 범위만 허용하며, 벗어나면 400을 반환한다.
최초 저장 시 온보딩이 완료된 것으로 간주된다 (`GET /auth/me`의 `onboarded`가 `true`로 바뀜).

구독 구단을 추가/삭제할 때도 동일한 `PUT`을 사용한다 (원하는 `clubIds` 전체 목록을 다시 보낸다).

`favoriteClubId`는 관심 구단 중 대표로 지정할 "최애팀"의 구단 id다 (선택, 생략하거나 `null`을
보내면 최애팀 미지정 상태가 된다). 존재하지 않는 구단 id를 넘기면 400을 반환한다. `clubIds`에
포함되지 않은 구단을 `favoriteClubId`로 지정하면 에러 대신 그 구단을 `clubIds`에 자동으로
포함시켜 저장한다 (`docs/DB_SCHEMA.md`의 `user_preferences` 절 참고).

응답 예시 (`GET`/`PUT` 동일한 형식)
```json
{
  "clubs": [
    { "id": 1, "name": "Liverpool", "league": "EPL" },
    { "id": 2, "name": "Arsenal", "league": "EPL" }
  ],
  "notificationTrustLevel": 3,
  "favoriteClub": { "id": 1, "name": "Liverpool", "league": "EPL" }
}
```

최애팀을 지정하지 않았으면 `favoriteClub`은 `null`이다.

## 닉네임 변경

```
PATCH /users/me/nickname
```

인증 필요. 요청 본문
```json
{ "nickname": "리버풀팬" }
```

`nickname`은 빈 문자열을 허용하지 않으며(400), 응답은 `GET /auth/me`와 동일한 형식이다.

## 계정 탈퇴

```
DELETE /users/me
```

인증 필요. 해당 사용자의 `user_preferences`, `reporter_suggestions`, `users` row를 모두 삭제하고
인증 쿠키를 만료시킨 뒤 204를 반환한다. 이 작업은 되돌릴 수 없다.

## 기자 제보

```
POST /reporter-suggestions
GET /reporter-suggestions/me
```

인증 필요. `POST` 요청 본문
```json
{
  "twitterHandle": "@some_reporter",
  "name": "김기자",
  "league": "EPL",
  "memo": "이적 소식을 빠르게 전함"
}
```

`twitterHandle`만 필수(빈 문자열이면 400)이며 `name`, `league`, `memo`는 선택이다.
`league`는 `clubs.league`와 동일한 값(EPL/LA_LIGA/BUNDESLIGA/SERIE_A/LIGUE_1)만 인식하며,
값이 없거나 알 수 없는 값이면 에러 없이 `null`로 저장된다. 성공 시 201과 저장된 제보를 반환한다.

`GET /reporter-suggestions/me`는 로그인한 사용자 본인이 제출한 제보 목록을 최신순으로 반환한다.

향후 추가 예정: 즐겨찾기
