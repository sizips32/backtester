# 포트폴리오 백테스터 (Portfolio BackTester)

## 프로젝트 개요

이 프로젝트는 투자 포트폴리오의 자산배분을 분석하고 최적화하는 고급 백테스팅 시스템입니다. 다양한 투자 전략을 시뮬레이션하고, 포트폴리오 성과를 분석하며, 리스크 관리를 위한 종합적인 도구를 제공합니다.

## 주요 기능

### 포트폴리오 분석

- **자산 배분 분석**: 포트폴리오 구성 요소 분석 및 최적화
- **백테스팅**: 과거 데이터를 기반으로 한 투자 전략 검증
- **리스크 분석**: 변동성, 샤프 비율, 최대 낙폭 등 다양한 리스크 지표 분석
- **포지션 사이징**: 효율적인 자금 배분 전략 구현
- **포트폴리오 리밸런싱**: 자동화된 포트폴리오 조정 기능

### 데이터 처리

- 실시간 시장 데이터 연동 (yfinance 활용)
- 효율적인 데이터 캐싱 시스템
- 데이터 유효성 검증

### 시각화

- 포트폴리오 성과 대시보드
- 리스크 지표 시각화
- 자산 배분 차트
- 백테스팅 결과 분석 그래프

## 프로젝트 구조

```
├── app.py                     # 메인 웹 애플리케이션
├── portfolio_app.py           # 포트폴리오 관리 핵심 로직
├── config/                    # 설정 폴더
│   └── app_config.py          # 통합 설정 파일
├── data/                      # 데이터 저장소
├── utils/                     # 유틸리티 함수
│   └── logger.py              # 로깅 유틸리티
├── services/                  # 서비스 레이어
│   └── data_service.py        # 통합 데이터 서비스
├── asset_allocation.py        # 자산 배분 로직
├── backtesting.py             # 백테스팅 엔진
├── risk_analysis.py           # 리스크 분석 도구
├── portfolio_rebalancing.py  # 리밸런싱 로직
├── position_sizing.py        # 포지션 사이징 전략
├── run.py                     # 커스텀 포트로 앱 실행 스크립트
├── run.sh                     # 쉘 스크립트로 앱 실행
├── .streamlit/               # Streamlit 설정 폴더
│   └── config.toml           # Streamlit 설정 파일
└── requirements.txt           # 프로젝트 의존성
```

## 기술 스택

- **Python 3.9+**: 주 프로그래밍 언어
- **데이터 처리**: NumPy, Pandas
- **데이터 시각화**: Plotly, Matplotlib, Seaborn
- **웹 인터페이스**: Streamlit
- **금융 데이터**: yfinance
- **수학/통계/TA**: SciPy, ta

## 설치 방법

1. 저장소 클론

```bash
git clone [repository-url]
cd BackTester
```

2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 설치

```bash
pip install -r requirements.txt
```

4. 환경 변수 설정

```bash
cp .env.example .env  # 환경 변수 템플릿 복사
# .env 파일을 편집하여 필요한 설정 추가
```

5. 애플리케이션 실행

```bash
# 기본 방법 (포트 8501 사용)
streamlit run app.py

# 커스텀 포트(7700) 지정 실행
streamlit run app.py --server.port=7700

# 또는 제공된 실행 스크립트 사용
python run.py   # Python 스크립트 방식
./run.sh        # Shell 스크립트 방식 (chmod +x run.sh로 권한 부여 필요)
```

## 사용 방법

1. 웹 브라우저에서 `http://localhost:7700` 접속 (기본 설정된 포트 사용)
2. 분석하고자 하는 자산 목록 입력
3. 백테스팅 기간 및 전략 설정
4. 분석 실행 및 결과 확인

## 주요 기능 상세 설명

### 백테스팅 엔진

- 다양한 투자 전략 시뮬레이션
- 거래 비용 및 슬리피지 고려
- 상세한 성과 지표 제공

### 리스크 분석

- 변동성 분석
- 샤프 비율, 소티노 비율 계산
- 최대 낙폭(MDD) 분석
- VaR(Value at Risk) 계산

### 포트폴리오 최적화

- 현대 포트폴리오 이론 기반 최적화
- 효율적 투자선 도출
- 리스크 파리티 전략 구현

## 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 문의사항

프로젝트에 대한 문의사항이나 버그 리포트는 GitHub Issues를 통해 제출해 주세요.
