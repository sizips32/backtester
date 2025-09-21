#!/bin/bash

# Portfolio BackTester 통합 실행 스크립트
echo "🚀 Portfolio BackTester 실행 중..."

# MCP 서버 백그라운드 실행
echo "📡 MCP 서버 시작..."
cd mcp_server
python portfolio_mcp_server.py &
MCP_PID=$!
cd ..

# 서버 시작 대기
sleep 2

# Streamlit 앱 실행
echo "🌐 Streamlit 앱 시작..."
streamlit run app.py --server.port=7700 &
STREAMLIT_PID=$!

# 프로세스 정리 함수
cleanup() {
    echo "🔄 프로세스 정리 중..."
    kill $MCP_PID 2>/dev/null
    kill $STREAMLIT_PID 2>/dev/null
    echo "✅ 정리 완료"
}

# Ctrl+C 시그널 처리
trap cleanup SIGINT SIGTERM

echo "✅ 모든 서비스가 시작되었습니다:"
echo "   🌐 Streamlit 앱: http://localhost:7700"
echo "   📡 MCP 서버: 백그라운드 실행 중"
echo ""
echo "⚠️  종료하려면 Ctrl+C를 누르세요"

# 프로세스 대기
wait
