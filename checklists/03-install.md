# 03. 설치 파일 준비와 자동 설치

이 단계부터 실제 설치를 진행합니다.

## 체크리스트

- [ ] 설치 파일이 들어 있는 폴더를 PC에 받았다
- [ ] 그 폴더의 위치를 알고 있다
- [ ] 관리자 권한 PowerShell을 열었다
- [ ] PowerShell에서 설치 폴더로 이동했다
- [ ] `setup-windows.ps1` 파일이 보인다
- [ ] `./setup-windows.ps1`을 실행했다
- [ ] 설치가 큰 오류 없이 끝났다
- [ ] 설치 후 터미널을 닫고 다시 열었다

## 1. 설치 폴더 준비

운영자가 제공한 설치 폴더 안에 최소한 다음 파일이 있는지 확인합니다.

```text
setup-windows.ps1
setup-common.ts
SETUP_ko.md
SETUP_CHECKLIST_ko.md
```

완전히 새 Windows라면 아직 Git이 없을 수 있으므로, 영상에서는 처음부터 `git clone`을 요구하기보다 ZIP 다운로드 또는 운영자가 제공한 폴더를 기준으로 설명하는 편이 쉽습니다.

## 2. 관리자 PowerShell 열기

Windows 시작 메뉴에서 `PowerShell`을 검색한 뒤 **관리자 권한으로 실행**합니다.

## 3. 설치 폴더로 이동

예를 들어 다운로드 폴더 아래 `workshop-setup`에 파일이 있다면:

```powershell
cd C:\Users\내이름\Downloads\workshop-setup
```

현재 폴더의 파일 확인:

```powershell
dir
```

목록에 다음 파일이 보여야 합니다.

```text
setup-windows.ps1
```

## 4. 설치 실행

기본 설치:

```powershell
.\setup-windows.ps1
```

기본 설치에서 준비하는 주요 도구:

- PowerShell 7+
- Windows Terminal
- Git
- bun
- Python
- uv
- GitHub CLI (`gh`)
- Claude Code CLI
- Antigravity CLI
- Google Chrome
- Claude Desktop

## 5. 선택 옵션

운영자가 따로 안내한 경우에만 사용합니다.

```powershell
.\setup-windows.ps1 -WSL2
.\setup-windows.ps1 -WezTerm
.\setup-windows.ps1 -Docker
```

전체 선택 옵션:

```powershell
.\setup-windows.ps1 -WSL2 -WezTerm -Docker
```

## 6. 설치 후 반드시 터미널 재시작

설치가 끝나면 PowerShell 또는 Windows Terminal을 **완전히 닫고 다시 엽니다.**

새로 설치된 명령어의 경로(PATH)를 Windows가 새 터미널에서 다시 읽어야 하기 때문입니다.

## 영상에서 꼭 설명할 것

### `cd`는 “폴더 이동” 명령어
초보자에게는 `cd` 자체보다 **지금 PowerShell이 어느 폴더를 보고 있는지**가 더 중요합니다.

### `dir`로 파일을 먼저 확인
바로 스크립트를 실행하지 말고 `dir`로 `setup-windows.ps1`이 실제로 보이는 장면을 보여주세요.

### Docker / WSL2를 기본 과정처럼 보여주지 않기
운영자가 별도로 요구하지 않는다면 건너뜁니다.

### 설치 중 메시지가 많이 나오는 것은 정상
여러 도구를 자동으로 설치하므로 화면에 긴 로그가 출력될 수 있습니다.
