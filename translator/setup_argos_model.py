"""Argos Translate의 영어->한국어 번역 모델을 다운로드/설치하는 1회성 스크립트.

번역을 실행하기 전에 딱 한 번만 실행하면 된다. 모델은 로컬에 설치되며(수십~수백MB
수준), 이후 translate.py는 완전히 오프라인으로 동작한다. 이미 설치돼 있으면
아무 것도 하지 않고 끝나므로 여러 번 실행해도 안전하다(idempotent).

사용법:
    python setup_argos_model.py
"""

import argostranslate.package

from argos_engine import FROM_CODE, TO_CODE, is_model_installed


def main() -> None:
    if is_model_installed():
        print(f"이미 설치되어 있습니다: {FROM_CODE} -> {TO_CODE}. 다시 설치할 필요 없습니다.")
        return

    print("Argos Translate 패키지 인덱스를 갱신하는 중... (네트워크 필요)")
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()

    package_to_install = next(
        (pkg for pkg in available_packages if pkg.from_code == FROM_CODE and pkg.to_code == TO_CODE),
        None,
    )
    if package_to_install is None:
        raise RuntimeError(f"{FROM_CODE} -> {TO_CODE} 번역 패키지를 찾을 수 없습니다.")

    print(f"다운로드 중: {package_to_install}")
    downloaded_path = package_to_install.download()

    print("설치하는 중...")
    argostranslate.package.install_from_path(downloaded_path)

    print(f"설치 완료: {FROM_CODE} -> {TO_CODE}. 이후로는 오프라인으로 번역할 수 있습니다.")


if __name__ == "__main__":
    main()
