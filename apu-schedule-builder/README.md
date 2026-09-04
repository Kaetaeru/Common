# APU Schedule Builder V1.5

Ritsumeikan APU AY2026 Fall 2023 Curriculum용 시간표 생성기입니다.

## 사용 (설치 불필요)

브라우저에서 아래 주소를 열면 됩니다. macOS · Windows · 휴대폰 모두 동일하게 동작하며 설치할 것이 없습니다.

```
https://kaetaeru.github.io/Common/apu-schedule-builder/
```

선택한 Class와 설정은 그 브라우저의 localStorage에 남습니다. 새로고침이나 재부팅으로는 사라지지 않고, 브라우저 데이터를 지우거나 시크릿 창을 닫을 때만 초기화됩니다. Safari는 7일간 방문이 없으면 자동으로 지우므로, 오래 보관하려면 Chrome을 쓰는 편이 안전합니다.

## 데이터 갱신 (관리자용)

APU가 timetable을 갱신했을 때만 실행합니다. Python이 필요한 부분은 이 단계뿐입니다.

```powershell
py -3 build_site.py            # Windows  (build_windows.bat 더블클릭도 동일)
python3 build_site.py          # macOS / Linux  (./build_unix.sh)
```

공식 XLSX를 내려받아 파싱하고, 검증된 syllabus 링크·언어 사다리 메타데이터·A+ 평점을 합쳐 `../docs/apu-schedule-builder/`에 정적 사이트를 씁니다. 결과를 커밋해서 push하면 GitHub Pages가 배포합니다.

유용한 옵션:

- `--colleges APM ST` 특정 College만 빌드
- `--offline` 다운로드 없이 `data/source/*.xlsx` 재사용
- `--serve` 빌드 후 `http://127.0.0.1:8000/`으로 미리보기

### A+ 평점을 빌드 시점에 굽는 이유

`api.apluscoursereview.com`은 CORS 헤더를 보내지 않아 브라우저에서 직접 호출할 수 없습니다. 그래서 Python 빌드 단계에서 받아 데이터에 합쳐 넣습니다. 사용자 입장에서는 추가 요청이 없어 더 빠르고, 대신 평점은 **마지막 빌드 시점의 스냅샷**입니다. A+ API가 응답하지 않아도 빌드는 성공하고 평점만 빠집니다.

## V1.5 Standalone Syllabus Collector 연동

Syllabus 수집은 Schedule Builder 안에서 하지 않습니다. 별도 프로젝트 `Common/apu-syllabus-collector/`가 APU 공개 syllabus를 자동 순회하고 `data/syllabus_links.json`을 생성합니다.

Schedule Builder의 역할은 **수집된 mapping을 읽고 Class에 연결하는 것뿐**입니다. 두 프로젝트가 `Common/` 아래 형제 폴더로 있으면 다음 파일을 자동으로 읽습니다.

```text
Common/apu-syllabus-collector/data/syllabus_links.json
```

기존 `apu-schedule-builder/data/syllabus_links.json`과 `data/syllabus-links/**/*.json`도 수동 override/기존 데이터 호환을 위해 계속 읽습니다. 같은 Class에 서로 다른 direct URL이 들어오면 conflict로 보고 해당 mapping을 사용하지 않습니다.

Schedule Builder에서 Selenium 자동 수집 버튼과 내장 Collector는 제거했습니다. 자동 수집의 진행률, 현재 Class, 성공/실패, 재시도, Output Log는 standalone Collector UI에서 확인합니다.

## V1.3 Windows HTTPS 인증서 처리

APU 공식 XLSX 다운로드에서 Python/OpenSSL이 Windows가 신뢰하는 인증서 체인을 찾지 못해 `CERTIFICATE_VERIFY_FAILED`가 발생하는 환경을 처리합니다.

- 평소에는 기존 Python HTTPS 다운로드를 그대로 사용합니다.
- Windows에서 **인증서 검증 오류일 때만** PowerShell `Invoke-WebRequest`로 다시 다운로드합니다.
- 이 fallback은 Windows의 신뢰된 인증서 저장소를 사용하며 TLS 인증서 검증을 끄지 않습니다.
- `verify=False`, `-k`, `SkipCertificateCheck` 같은 우회 옵션은 사용하지 않습니다.
- 인증서 오류가 아닌 네트워크 오류는 숨기지 않고 원래 오류를 그대로 반환합니다.

Windows fallback까지 실패하면 Windows 날짜/시간, VPN·프록시·보안 프로그램, Windows 루트 인증서 업데이트 상태를 확인해야 합니다.

## V1.2 UX 흐름

V1.2부터 다크모드/강한 경계 UI와 Class 중심 시간표를 유지하면서, 실라버스 동기화를 Subject 묶음 검색보다 Class code 개별 검색 우선으로 바꿔 Salesforce가 첫 검색어를 반복하는 문제를 방지합니다.

1. 왼쪽 `수업 찾기`에서 과목을 검색합니다.
2. 같은 과목 아래 실제 `Class code`별 시간표를 각각 확인합니다.
3. 추가 버튼은 **과목이 아니라 실제 Class**를 시간표에 넣습니다. 여러 요일에 걸친 언어과목도 Class의 모든 meeting이 한 번에 들어갑니다.
4. 시간표 빈 칸을 클릭하면 `이 시간에 열리는 수업 찾기` 또는 `이 시간 비우기`를 선택할 수 있습니다.
5. 선택한 Class가 충돌하면 추가하는 순간 바로 이유를 보여주고 막습니다.
6. University-registered 수업은 설정에서 Class code로 추가하며 잠금 상태로 유지됩니다.
7. 필요할 때만 `빈 학점 자동 채우기`로 현재 Class들을 고정한 채 대안을 계산합니다.
8. 선택한 Class와 설정은 브라우저 localStorage에 유지되어 다음 방문에도 그대로 남습니다.

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

```powershell
py -3 -m unittest discover -s tests -v
```

`web/solver.js`는 `app_backend.py`의 beam search를 그대로 옮긴 것이고, 브라우저는 이 JS를 실행합니다. 두 구현이 어긋나면 안 되므로 `tests/test_solver_parity.py`가 같은 config 행렬을 양쪽에 돌려 점수·학점·Class code·metrics·설명까지 비교합니다. 기본은 빠른 표본 검사이고, 전체 스윕은 다음과 같이 돌립니다.

```powershell
$env:APU_PARITY_FULL=1; py -3 -m unittest tests.test_solver_parity -v
```
