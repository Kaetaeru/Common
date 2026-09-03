# APU Syllabus Collector V1.7

APU Schedule Builder와 분리된 **독립 자동 수집 유틸리티**입니다.

목표는 현재 학기의 Class code 목록을 APU 공식 timetable에서 읽은 뒤, APU 공개 syllabus 검색을 Chrome/Edge로 자동 순회하여 `Class code -> direct syllabus URL`을 확보하는 것입니다.

## 실행

Windows에서 `run_windows.bat`를 더블클릭합니다. 브라우저 UI는 기본적으로 `http://127.0.0.1:8766/`에서 열립니다.

1. College(APM/APS/ST)를 선택합니다.
2. `자동 수집 시작`을 누릅니다. Class 목록이 없으면 공식 timetable도 자동으로 준비합니다. (`Class 목록 불러오기`는 사전 확인용입니다.)
3. 수집 중에는 현재 Class, 확보/남음/실패 수, 진행률, Output Log를 확인합니다.
4. 실패 항목은 마지막에 `실패 N개 집중 재시도`로 더 깊게 다시 돌릴 수 있습니다.

## 저장 방식

- 결과: `data/syllabus_links.json`
- 실행 상태: `data/collector_state.json`
- 텍스트 로그: `data/collector.log`
- 공식 timetable 캐시: `data/source/`

성공한 direct URL은 **한 건씩 즉시** `data/syllabus_links.json`에 저장합니다. 프로그램이 중간에 종료되어도 다음 실행에서 이미 확보한 Class는 건너뜁니다.

URL은 다음 조건을 모두 만족할 때만 성공으로 저장합니다.

- host가 `syllabus.apu.ac.jp`
- path가 `/syllabus/s/a-syllabus/<record-id>/<year><class-code>` 형식
- URL의 연도와 현재 timetable 연도가 일치
- URL 마지막 Class code가 현재 검색 중인 Class code와 정확히 일치

Salesforce record ID는 추측하지 않습니다.

## 자동 수집 동작

검색은 **Class code 전용**입니다. Subject 이름 검색은 사용하지 않습니다. 화면에서 실제 Class Code/Course Code 입력창을 찾지 못하면 다른 검색창을 대신 쓰지 않고 실패로 기록하며, 정확한 Class Code 필드가 확인된 경우에만 숫자 code를 입력합니다.

숫자를 입력한 뒤에는 실제로 표시된 **Search 버튼을 클릭한 경우에만** 검색을 제출한 것으로 인정합니다. Enter 키는 Salesforce가 아무 동작 없이 받아들이는 경우가 있어 검색 제출 수단으로 사용하지 않습니다. 검색 결과에 direct URL이 바로 노출되지 않으면 정확한 Class code가 표시된 결과 행/링크만 클릭하고, 열린 상세 페이지의 URL에서 direct link를 회수합니다. 결과 렌더링도 최대 몇 초 기다립니다.

검색창 값이 제대로 바뀌지 않거나 검색이 실패하면 포털을 다시 열고 재시도합니다. 그래도 찾지 못하면 실패로 기록하고 다음 Class로 넘어갑니다.

## Schedule Builder 연동

이 프로젝트가 `Common/apu-syllabus-collector/`에 있고 Schedule Builder가 형제 폴더 `Common/apu-schedule-builder/`에 있으면, Schedule Builder는 이 Collector의 `data/syllabus_links.json`을 자동으로 읽습니다. Collector 자체는 Schedule Builder를 import하거나 실행하지 않습니다.

## 검증

```powershell
py -3 -m unittest discover -s tests -v
```

실제 APU Salesforce 페이지의 DOM은 외부 서비스이므로, 단위 테스트와 별도로 Windows Chrome/Edge에서 실제 수집 로그를 확인해야 최종 통합 검증이 됩니다.

## V1.6 shared-queue parallel collection

- 브라우저 수는 UI에서 **1~10개**로 직접 정합니다. 기본값은 안정성을 위해 5개입니다.
- 미확보 Class를 고정 파트로 나누지 않습니다. 모든 worker가 **하나의 공유 작업 목록**에서 다음 Class를 하나씩 가져갑니다.
- 한 worker가 느린 Class를 처리하는 동안 먼저 끝난 worker는 즉시 다음 남은 Class를 가져가므로 고정 파트의 완료 시간 불균형이 없습니다.
- queue에서 꺼낸 Class는 한 worker에게만 배정되므로 같은 실행에서 두 worker가 같은 Class를 동시에 처리하지 않습니다.
- 브라우저 session이 중간에 종료되면 해당 worker만 브라우저를 다시 띄우고 **방금 처리하던 같은 Class부터 재시도**합니다. Class 하나당 자동 browser restart는 최대 2회입니다.
- browser restart 자체가 계속 실패해 worker 하나가 종료되어도 아직 가져가지 않은 shared work는 다른 살아 있는 worker가 계속 처리합니다.
- 검색과 browser session은 worker별로 독립적이지만 `data/syllabus_links.json`, 실패 상태, state 저장은 lock으로 직렬화합니다.
- Output Log에는 `[W01] [123/835]`처럼 worker 번호와 전체 작업 목록 기준 위치를 표시합니다.
- 중지/일시정지는 실행 중인 모든 worker에 적용됩니다.

## V1.5 Windows-safe result saving

- `syllabus_links.json` 저장 시 worker/process별로 겹치지 않는 고유 임시 파일을 사용합니다.
- Windows Defender, 동기화 도구 등의 짧은 파일 잠금으로 `WinError 5/32/33`이 발생하면 짧은 backoff로 최대 6번 자동 재시도합니다.
- 재시도 후에도 저장이 실패하면 해당 Class를 `save-failed`로 기록하고 다음 Class로 계속 진행합니다. 저장 실패 하나 때문에 browser worker 전체가 종료되지 않습니다.

## V1.7 focused retry

`실패 N개 집중 재시도`는 `data/collector_state.json`의 현재 `failed` Class만 대상으로 합니다. 이미 저장된 Class는 제외합니다. 일반 수집은 기존 빠른 설정(2회 시도, 최대 4페이지, 결과 대기 4초)을 유지하고, 집중 재시도에서만 Class code 검색을 최대 4회 수행하며 결과를 더 오래 기다리고 최대 6페이지까지 확인합니다. Subject Name 검색은 사용하지 않습니다.
