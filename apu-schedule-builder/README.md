# APU Schedule Builder V1.2

Ritsumeikan APU AY2026 Fall 2023 Curriculum용 로컬 시간표 생성기입니다.

## 실행 (Windows)

1. 이 폴더에서 `run_windows.bat`를 더블클릭합니다.
2. Python이 없으면 설치 스크립트가 자동으로 준비합니다.
3. 브라우저가 열리면 우측 상단 **설정**에서 College/Semester를 확인합니다. 공식 데이터가 없을 때만 설정 안의 **공식 데이터 불러오기**를 누릅니다.
4. 이전에 한 번 불러온 데이터가 있으면 다음 실행부터 자동으로 다시 표시됩니다.

직접 실행하려면:

```powershell
py -3 -m pip install -r requirements.txt
py -3 app.py
```

## V1.2 UX 흐름

V1.2는 다크모드/강한 경계 UI와 Class 중심 시간표를 유지하면서, 실라버스 동기화를 Subject 묶음 검색보다 Class code 개별 검색 우선으로 바꿔 Salesforce가 첫 검색어를 반복하는 문제를 방지합니다.

1. 왼쪽 `수업 찾기`에서 과목을 검색합니다.
2. 같은 과목 아래 실제 `Class code`별 시간표를 각각 확인합니다.
3. 추가 버튼은 **과목이 아니라 실제 Class**를 시간표에 넣습니다. 여러 요일에 걸친 언어과목도 Class의 모든 meeting이 한 번에 들어갑니다.
4. 시간표 빈 칸을 클릭하면 `이 시간에 열리는 수업 찾기` 또는 `이 시간 비우기`를 선택할 수 있습니다.
5. 선택한 Class가 충돌하면 추가하는 순간 바로 이유를 보여주고 막습니다.
6. University-registered 수업은 설정에서 Class code로 추가하며 잠금 상태로 유지됩니다.
7. 필요할 때만 `빈 학점 자동 채우기`로 현재 Class들을 고정한 채 대안을 계산합니다.
8. 기본적으로 `127.0.0.1:8765`를 사용해 선택한 Class와 설정이 브라우저에 계속 유지됩니다. 포트가 이미 사용 중일 때만 임시 포트를 사용합니다.

### 기본 데이터 모델

- **Subject**: 검색과 분류를 위한 과목 묶음
- **Class / Enrollment Option**: 학생이 실제로 선택하는 단위 (`classCode`)
- **Meeting**: 한 Class를 구성하는 요일/교시 블록

따라서 같은 일본어 과목에 Class A/B/C가 있고 시간표가 서로 다르면 세 Class를 별개의 선택지로 표시합니다. Class B를 선택하면 Class B의 모든 meeting이 함께 시간표에 들어갑니다.

### V1.2 실라버스 direct link 전체 동기화

- 설정 → **실라버스 링크 전체 동기화**를 누르면 Chrome 또는 Edge가 APU 공개 실라버스 검색을 엽니다.
- 기본 동기화는 각 Class code를 하나씩 검색합니다. 검색창의 실제 값이 새 code로 바뀌지 않으면 성공으로 처리하지 않고 포털을 다시 연 뒤 재시도합니다.
- Class code로 못 찾은 항목에만 Subject 이름 검색을 최종 fallback으로 사용합니다.
- 결과 페이지가 여러 장이면 `Next / 次へ`를 따라가며 direct link를 수집합니다.
- direct URL은 `연도 + Class code`가 현재 timetable과 정확히 일치할 때만 저장합니다.
- 찾은 링크는 즉시 `data/syllabus_links.json`에 저장하므로 중간에 끊겨도 다음 실행에서 이미 확보한 Class를 다시 찾지 않습니다.
- 설정 화면에서 현재 `direct link 확보 수 / 전체 Class 수`를 표시합니다.
- Salesforce Lightning의 일반 DOM뿐 아니라 중첩된 open Shadow DOM 안의 검색 입력, 버튼, 결과 링크까지 재귀적으로 찾습니다.
- Salesforce 컴포넌트가 늦게 렌더링되는 경우를 위해 고정 sleep 대신 검색 컨트롤이 실제 나타날 때까지 기다립니다.
- 그래도 검색 UI를 찾지 못하면 `data/syllabus_sync_debug/page.html`, `page.png`, `controls.json`을 남깁니다.

### 기존 direct link 처리

- 모든 Class 카드와 상세 패널에 실라버스 버튼을 표시합니다.
- `syllabusUrl`이 확보된 Class는 `실라버스 바로가기 ↗`로 표시되고 APU 상세 실라버스 페이지를 바로 엽니다.
- 확인된 Psychology Class `10121`은 `https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZQ8000004S4L9MAK/202610121?language=en_US`로 직접 연결됩니다.
- 시간표 XLSX의 셀에 APU 상세 실라버스 하이퍼링크가 포함되어 있으면 파서가 해당 URL을 자동 추출합니다.
- 추가로 확인된 direct URL은 `data/syllabus_links.json`에 `"연도:ClassCode" -> URL` 형식으로 저장할 수 있습니다.
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
