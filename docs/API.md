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
  응답의 `clubs`는 배열이지만, 필터 파라미터는 단일 구단명만 받는다 — 그 구단이 `clubs` 배열에 포함된
  기사가 매칭된다.
- `from`, `to`: 발행일 범위 필터 (선택, 미구현)
- `keyword`: 제목 검색 (선택, 구현됨). 번역 제목(`titleKo`) 또는 원문 제목(`titleOriginal`) 중
  하나라도 검색어를 포함하면 매칭된다 (대소문자 구분 없음, 부분 일치). 아직 번역되지 않은 기사는
  `titleOriginal` 기준으로만 매칭된다. 본문(`content`)은 검색 대상이 아니다.
- `club`과 `keyword`를 동시에 지정하면 AND 조건으로 적용된다 (해당 구단이면서 검색어를 포함하는 기사만 반환).

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
      "sourceTier": 1
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
  "sourceTier": 1
}
```

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
  "notificationTrustLevel": 3
}
```

`notificationTrustLevel`은 1(공식 소스만) ~ 5(모든 소스) 범위만 허용하며, 벗어나면 400을 반환한다.
최초 저장 시 온보딩이 완료된 것으로 간주된다 (`GET /auth/me`의 `onboarded`가 `true`로 바뀜).

구독 구단을 추가/삭제할 때도 동일한 `PUT`을 사용한다 (원하는 `clubIds` 전체 목록을 다시 보낸다).

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

향후 추가 예정: 즐겨찾기, 태그/카테고리 필터
