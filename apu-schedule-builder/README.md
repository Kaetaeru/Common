# APU Schedule Builder V1.6

Ritsumeikan APU AY2026 Fall 2023 Curriculum용 로컬 시간표 생성기입니다.

## 쓰는 방법

V1.6부터 이 앱은 **브라우저에서만 도는 정적 웹앱**입니다. 로컬 서버도, Python도, 설치도 필요 없습니다.

배포된 주소를 열면 끝입니다. macOS · Windows · 아이패드 · 휴대폰 모두 동일하게 동작하고, 선택한 Class와 설정은 브라우저에 저장됩니다.

```text
https://kaetaeru.github.io/Common/apu-schedule-builder/
```

## 데이터 갱신 (관리자만)

APU가 timetable이나 subject list를 갱신했을 때만, 이 레포를 가진 사람이 한 번 실행합니다.

- Windows: `build_windows.bat` 더블클릭
- macOS / Linux: `chmod +x build_unix.sh && ./build_unix.sh`

직접 실행하려면:

```bash
python3 -m pip install -r requirements.txt
python3 build_site.py            # 공식 XLSX 다운로드 → 파싱 → ../docs/apu-schedule-builder/ 생성
python3 build_site.py --serve    # 만든 결과를 바로 미리보기
python3 build_site.py --offline  # data/source/*.xlsx 를 그대로 사용 (다운로드 실패 시)
```

빌드 결과(`Common/docs/`)를 커밋하면 GitHub Pages가 그대로 서비스합니다. 최초 1회만 GitHub의 **Settings → Pages → Deploy from branch → main / docs** 를 켜면 됩니다.

### 구조

| 위치 | 역할 |
| --- | --- |
| `build_site.py` | XLSX 다운로드·파싱·실라버스 링크 결합 → 정적 사이트 생성 (Python 필요) |
| `app_backend.py` / `app.py` | 파서·Solver 기준 구현. 테스트가 검증하는 원본 |
| `web/solver.js` | 브라우저에서 도는 Solver. `app_backend.py`의 beam search를 그대로 이식 |
| `web/*.js`, `web/index.html` | 정적 앱 본체 |
| `docs/apu-schedule-builder/` | 빌드 산출물. GitHub Pages가 서비스하는 실제 파일 |

`web/solver.js`는 손으로 옮긴 코드이므로 Python 원본과 갈라지면 안 됩니다. `tests/test_solver_parity.py`가 실제 APU 데이터로 두 구현의 결과를 통째로 비교합니다.

## V1.5 Standalone Syllabus Collector 연동

Syllabus 수집은 Schedule Builder 안에서 하지 않습니다. 별도 프로젝트 `Common/apu-syllabus-collector/`가 APU 공개 syllabus를 자동 순회하고 `data/syllabus_links.json`을 생성합니다.

Schedule Builder의 역할은 **수집된 mapping을 읽고 Class에 연결하는 것뿐**입니다. 두 프로젝트가 `Common/` 아래 형제 폴더로 있으면 다음 파일을 자동으로 읽습니다.

```text
Common/apu-syllabus-collector/data/syllabus_links.json
```

기존 `apu-schedule-builder/data/syllabus_links.json`과 `data/syllabus-links/**/*.json`도 수동 override/기존 데이터 호환을 위해 계속 읽습니다. 같은 Class에 서로 다른 direct URL이 들어오면 conflict로 보고 해당 mapping을 사용하지 않습니다.

Schedule Builder에는 Selenium 수집 코드가 남아 있지 않습니다. 빌드에 필요한 의존성은 `openpyxl` 하나뿐입니다. 자동 수집의 진행률, 현재 Class, 성공/실패, 재시도, Output Log는 standalone Collector UI에서 확인합니다.

## V1.3 Windows HTTPS 인증서 처리

APU 공식 XLSX 다운로드에서 Python/OpenSSL이 Windows가 신뢰하는 인증서 체인을 찾지 못해 `CERTIFICATE_VERIFY_FAILED`가 발생하는 환경을 처리합니다.

- 평소에는 기존 Python HTTPS 다운로드를 그대로 사용합니다.
- Windows에서 **인증서 검증 오류일 때만** PowerShell `Invoke-WebRequest`로 다시 다운로드합니다.
- 이 fallback은 Windows의 신뢰된 인증서 저장소를 사용하며 TLS 인증서 검증을 끄지 않습니다.
- `verify=False`, `-k`, `SkipCertificateCheck` 같은 우회 옵션은 사용하지 않습니다.
- 인증서 오류가 아닌 네트워크 오류는 숨기지 않고 원래 오류를 그대로 반환합니다.

Windows fallback까지 실패하면 Windows 날짜/시간, VPN·프록시·보안 프로그램, Windows 루트 인증서 업데이트 상태를 확인해야 합니다.

## V1.2 UX 흐름

V1.2부터 다크모드/강한 경계 UI와 Class 중심 시간표를 유지합니다.

1. 왼쪽 `수업 찾기`에서 과목을 검색합니다.
2. 같은 과목 아래 실제 `Class code`별 시간표를 각각 확인합니다.
3. 추가 버튼은 **과목이 아니라 실제 Class**를 시간표에 넣습니다. 여러 요일에 걸친 언어과목도 Class의 모든 meeting이 한 번에 들어갑니다.
4. 시간표 빈 칸을 클릭하면 `이 시간에 열리는 수업 찾기` 또는 `이 시간 비우기`를 선택할 수 있습니다.
5. 선택한 Class가 충돌하면 추가하는 순간 바로 이유를 보여주고 막습니다.
6. University-registered 수업은 설정에서 Class code로 추가하며 잠금 상태로 유지됩니다.
7. 필요할 때만 `빈 학점 자동 채우기`로 현재 Class들을 고정한 채 대안을 계산합니다.
8. 선택한 Class와 설정은 브라우저 localStorage에 저장되어 다음 방문 때 그대로 복원됩니다.

### 기본 데이터 모델

- **Subject**: 검색과 분류를 위한 과목 묶음
- **Class / Enrollment Option**: 학생이 실제로 선택하는 단위 (`classCode`)
- **Meeting**: 한 Class를 구성하는 요일/교시 블록

따라서 같은 일본어 과목에 Class A/B/C가 있고 시간표가 서로 다르면 세 Class를 별개의 선택지로 표시합니다. Class B를 선택하면 Class B의 모든 meeting이 함께 시간표에 들어갑니다.

### 기존 direct link 처리

- 모든 Class 카드와 상세 패널에 실라버스 버튼을 표시합니다.
- `syllabusUrl`이 확보된 Class는 `실라버스 바로가기 ↗`로 표시되고 APU 상세 실라버스 페이지를 바로 엽니다.
- 확인된 Psychology Class `10121`은 `https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZQ8000004S4L9MAK/202610121?language=en_US`로 직접 연결됩니다.
- 시간표 XLSX의 셀에 APU 상세 실라버스 하이퍼링크가 포함되어 있으면 파서가 해당 URL을 자동 추출합니다.
- 추가로 확인된 direct URL은 `data/syllabus_links.json` 또는 `data/syllabus-links/<term>/batch-XXX.json`에 `"연도:ClassCode" -> URL` 형식으로 저장할 수 있습니다.
- Collector가 여러 Class code를 하나의 syllabus record로 묶어 내보낸 경우, canonical 항목이 같은 파일에 함께 있으면 그 그룹 전체에 direct link를 붙입니다.
- APU 상세 URL의 Salesforce record ID는 Class code에서 계산할 수 없으므로, 확인되지 않은 Class는 `실라버스 검색 ↗`으로 안전하게 fallback합니다.

### 가독성 / 다크모드

- 기본 테마는 다크모드이며 상단 버튼으로 라이트모드 전환 가능
- 시간표 전체 외곽선과 요일/교시 축은 강한 2px 경계로 고정
- 모든 시간 셀에 독립적인 그리드선을 표시해 행/열 경계가 항상 보임
- 비활성 시간은 사선 패턴으로 일반 빈칸과 구분
- Subject 자체를 하나의 외곽 카드로 묶고 그 안의 각 Class도 별도 카드로 분리
- 선택/확정/불가 Class는 border 두께와 배경을 함께 바꿔 색상만으로 구분하지 않음
- 왼쪽 Class에 hover하면 시간표의 같은 Class 블록들이 동시에 강조되고 반대 방향도 동일

## Solver 규칙

직접 편집에서는 학생이 고른 **실제 Class code**가 강제 선택입니다. `빈 학점 자동 채우기`를 눌렀을 때만 Solver가 남은 학점을 채웁니다.

강제 조건:

- 선택한 Class의 모든 meeting을 한 묶음으로 배치
- 사용자가 비워둔 1Q / 2Q 시간 블록 사용 금지
- Semester / 1Q / 2Q 시간 충돌 금지
- 같은 시간의 1Q + 2Q는 허용
- University-registered Class는 잠금 상태로 반드시 포함
- 같은 Subject의 서로 다른 Class를 동시에 선택하지 않음
- 현재 Semester보다 높은 최소 Semester의 Class는 기본적으로 추가 불가
- 학점 상한 초과 금지

자동 채우기에서는 현재 고른 Class와 확정수업을 그대로 유지한 채 남은 후보를 계산합니다. 선수조건 텍스트의 복잡한 AND/OR 판정은 아직 자동 강제하지 않습니다.

## 공식 데이터

- Course Timetable: https://en.apu.ac.jp/academic/class_info/timetable/
- APS Subject List: https://en.apu.ac.jp/academic/aps/subject_list/
- APM Subject List: https://en.apu.ac.jp/academic/apm/subject_list/
- ST Subject List: https://en.apu.ac.jp/academic/st/subject_list/

현재 설정 기준:

- Timetable updated 2026-09-01
- Subject List updated 2026-03-13

APU는 timetable/syllabus를 갱신할 수 있으므로 실제 수강신청 직전 공식 페이지와 CAMPUS WEB을 다시 확인하세요.

## 아직 자동 판정하지 않는 것

- CAMPUS WEB 로그인/자동 등록
- 실시간 잔여석
- Lottery 당첨 여부
- 개인별 University Registration 자동 조회
- 졸업요건 전체 판정
- prerequisite 문장의 복잡한 AND/OR 조건 자동 판정

## 테스트

```bash
python3 -m unittest discover -s tests -v
```

Solver 이식 검증은 Node와 빌드된 데이터가 있을 때만 돕니다. 기본은 빠른 표본이고, 전체 대조는 다음과 같이 돌립니다.

```bash
APU_PARITY_FULL=1 python3 -m unittest tests.test_solver_parity -v
```
