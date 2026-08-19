# Windows — 복사·붙여넣기 명령어 모음

영상이나 설치 중에 바로 복사해서 사용할 명령어만 모아둔 페이지입니다.

> **중요:** 아래 명령을 한꺼번에 전부 붙여넣지 마세요. 위에서부터 단계별로 실행합니다.
> 이름, 이메일, 폴더 경로처럼 본인 환경에 맞게 바꿔야 하는 값이 있습니다.

---

## 1. 시작 전 — winget 확인

```powershell
winget --version
```

버전 숫자가 나오면 다음 단계로 진행합니다.

`winget`을 찾을 수 없으면 Microsoft Store에서 **App Installer**를 설치한 뒤 다시 확인합니다.

---

## 2. 설치 폴더로 이동

아래 경로는 예시입니다. 실제 설치 파일을 받은 폴더 경로로 바꿉니다.

```powershell
cd "C:\Users\내이름\Downloads\workshop-setup"
```

현재 폴더의 파일 확인:

```powershell
dir
```

목록에 `setup-windows.ps1`이 보이는지 확인합니다.

---

## 3. Windows 자동 설치 실행

```powershell
.\setup-windows.ps1
```

이 스크립트가 Git for Windows, GitHub CLI(`gh`), PowerShell 7+, Windows Terminal, bun, Python, uv 등 필요한 주요 도구를 자동으로 설치합니다.

설치가 끝나면 **PowerShell / Windows Terminal을 완전히 닫고 다시 엽니다.**

---

## 4. 설치 확인

새 터미널에서 실행합니다.

```powershell
git --version
gh --version
bun --version
python --version
uv --version
```

각 명령에서 버전 정보가 나오면 정상입니다.

---

## 5. Git 사용자 설정

아래 `홍길동`을 본인 이름으로 바꿉니다.

```powershell
git config --global user.name "홍길동"
```

아래 이메일을 본인의 GitHub 이메일로 바꿉니다.

```powershell
git config --global user.email "you@example.com"
```

설정 확인:

```powershell
git config --global user.name
git config --global user.email
```

---

## 6. GitHub 로그인

```powershell
gh auth login
```

터미널과 브라우저의 안내에 따라 로그인을 완료합니다.

로그인 확인:

```powershell
gh auth status
```

`Logged in` 상태가 나오면 완료입니다.

---

## 7. 프로젝트 환경 설정 — 필요한 프로젝트만

프로젝트 폴더에 `.env.sample`이 있을 때만 실행합니다.

```powershell
copy .env.sample .env
```

Python 프로젝트가 `pyproject.toml`을 사용하는 경우:

```powershell
uv sync
```

`requirements.txt`를 사용하는 경우:

```powershell
uv pip install -r requirements.txt
```

> `uv sync`와 `uv pip install -r requirements.txt`를 둘 다 무조건 실행하는 것이 아닙니다. 프로젝트 구조에 맞는 명령 하나를 사용합니다.

---

## 8. 마지막 전체 검사

프로젝트 루트 폴더에서 실행합니다.

```powershell
bun setup-common.ts
```

필요한 항목이 모두 ✅로 표시되면 준비 완료입니다.

---

# 문제가 생겼을 때만 사용하는 명령

## PowerShell 스크립트 실행이 차단될 때

기본적으로 `setup-windows.ps1`이 실행 정책을 자동 조정하므로 평소에는 필요하지 않습니다.

오류가 있을 때만:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 설치 로그 폴더 열기

```powershell
explorer "$env:USERPROFILE\workshop-setup-logs"
```

---

# 가장 짧은 실행 순서

```text
winget --version
↓
cd "설치 파일이 있는 폴더"
↓
dir
↓
.\setup-windows.ps1
↓
터미널 완전히 닫기 / 다시 열기
↓
git --version
gh --version
↓
git config --global user.name "내 이름"
git config --global user.email "내 이메일"
↓
gh auth login
gh auth status
↓
bun setup-common.ts
```
