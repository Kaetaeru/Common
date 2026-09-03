# AY2026 Fall Syllabus collection workflow

## 1. Collector에서 배치 뽑기

`run_syllabus_collector.bat` 실행 → College 선택 → `상태 새로고침` → `다음 미매핑 Class 복사`.

권장 배치 크기: 40~60 Class.

## 2. 새 ChatGPT 세션에 아래 프롬프트 사용

```text
Repository: Kaetaeru/Common
Branch: main
Project folder: apu-schedule-builder
Academic term: AY2026 Fall

Goal:
Collect verified official APU direct syllabus URLs for ONLY the assigned Class list below and write them to one new batch JSON file.

Before writing:
1. Read apu-schedule-builder/data/syllabus-links/2026-fall/README.md.
2. Read existing syllabus batch files so already-mapped Class codes are not duplicated unnecessarily.
3. Do not modify another collector session's batch file.

Verification rules:
- Use only official syllabus.apu.ac.jp detail pages.
- Accepted shape:
  https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/<record-id>/2026<ClassCode>?language=en_US
- The URL final path must equal 2026 + the exact assigned Class code.
- Do not guess Salesforce record IDs.
- If a Class cannot be verified, leave it unresolved rather than inventing a URL.

Write verified results to:
apu-schedule-builder/data/syllabus-links/2026-fall/batch-XXX.json

JSON format:
{
  "2026:10121": "https://syllabus.apu.ac.jp/.../202610121?language=en_US"
}

Commit the batch file to GitHub main.
At the end report: attempted, verified, unresolved, already-known/duplicate, batch path, commit SHA.

ASSIGNED CLASS LIST:
<paste the Collector output here>
```

각 세션의 `batch-XXX.json` 번호는 겹치지 않게 지정합니다.

## 3. 결과 검증

GitHub 결과를 로컬 작업 폴더에 반영한 뒤 Collector에서 `상태 새로고침`을 누릅니다.

초록색 `앱 판독 확인됨 · repository mapping N/N Class에 정확히 연결됨`이 떠야 해당 mapping이 실제 Schedule Builder까지 연결된 것입니다. `오류 / 충돌`이 0이 아니면 Output Log에서 어느 파일/key가 문제인지 확인합니다.
