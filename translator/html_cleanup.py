"""RSS 요약(content_original)에 섞여 있는 HTML을 번역 직전에만 정리한다.

collector가 저장하는 content_original은 RSS 원문 그대로다(HTML 태그/엔티티 포함) —
원문 보존을 위해 저장 시점에는 건드리지 않는다. 하지만 이 HTML을 그대로 번역
엔진(특히 Argos Translate 같은 NMT)에 넣으면 문제가 생긴다:

- `&#8217;` 같은 HTML 엔티티가 텍스트로 그대로 번역되어 깨진다.
- `<a href="...">` 안의 URL까지 NMT가 통째로 "번역"하려다 알아볼 수 없이
  훼손하는 경우가 실제로 발견됐다.
- 워드프레스 RSS가 공통으로 붙이는 "The post ... appeared first on ..." 푸터가
  실제 기사 내용이 아닌데도 번역 대상에 섞여 들어간다.

그래서 이 모듈은 번역 직전에만 정리를 적용한다 — DB에 저장된 content_original
자체는 이 모듈과 무관하게 원문 그대로 유지된다.
"""

import html
import re

_WORDPRESS_FOOTER = re.compile(
    r"\s*The post .*? appeared first on .*?\.\s*$", re.IGNORECASE | re.DOTALL
)
_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE_RUN = re.compile(r"\s+")


def clean_for_translation(raw_text: str) -> str:
    """HTML 태그/엔티티와 워드프레스 RSS 푸터를 제거해 번역하기 좋은 평문으로 만든다.

    태그 제거를 먼저 해야 한다 — 원문은 보통
    "...<a href=\"...\">appeared first on ...</a>.</p>"처럼 마침표 뒤에도
    닫는 태그가 남아있어서, 태그를 남긴 채로 문자열 끝(`$`) 기준 푸터 패턴을
    찾으면 매칭에 실패한다.
    """
    without_tags = _HTML_TAG.sub(" ", raw_text)
    unescaped = html.unescape(without_tags)
    collapsed = _WHITESPACE_RUN.sub(" ", unescaped).strip()
    return _WORDPRESS_FOOTER.sub("", collapsed).strip()
