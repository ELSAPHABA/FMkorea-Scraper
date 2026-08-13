# FMkorea-Scraper
에펨코리아 게시글 및 댓글 스크래퍼

## 실행

권장 실행:

```powershell
python -m fmkorea_scraper.adapters.cli --help
```

DCinside-Scraper와 같은 루트 호환 wrapper도 제공합니다.

```powershell
python main.py --help
```

패키지로 설치한 뒤에는 console script도 사용할 수 있습니다.

```powershell
fmkorea-scraper --help
```

## 의존성 고정

`requirements.lock`은 기본 런타임 의존성과 test extra를 고정한 파일입니다. 선택 extra인 S3, PostgreSQL, MCP, Polars 의존성은 배포 목적에 맞게 별도로 설치합니다.
