# AY2026 Fall syllabus-link batches

한 수집 세션은 자기 batch JSON 파일만 수정합니다.

예: `batch-001.json`

```json
{
  "2026:10121": "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZQ8000004S4L9MAK/202610121?language=en_US"
}
```

규칙:

- key는 반드시 `YYYY:ClassCode`.
- URL은 APU의 `/syllabus/s/a-syllabus/<record-id>/<YYYY><ClassCode>` 상세 링크만 허용.
- Salesforce record ID를 추측하지 않습니다.
- 다른 batch 파일과 같은 key가 같은 URL이면 중복으로 안전하게 무시됩니다.
- 같은 key가 서로 다른 URL을 가리키면 충돌로 처리하며 앱은 그 key를 사용하지 않습니다.
