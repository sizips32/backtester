#!/usr/bin/env python3
"""
최소한의 MCP 서버 테스트
"""

import subprocess
import json
import time
import sys

def test_minimal_server():
    """최소 MCP 서버 연결 테스트"""

    server_cmd = [
        '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3',
        'mcp_server/minimal_test_server.py'
    ]

    try:
        print("🧪 최소 MCP 서버 테스트 시작...")

        process = subprocess.Popen(
            server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd='/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester'
        )

        # 서버 시작 대기
        time.sleep(1)

        # 초기화 요청
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        print("📤 초기화 요청 전송...")
        process.stdin.write(json.dumps(init_request) + '\n')
        process.stdin.flush()

        # 응답 대기
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            server_name = response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')
            print(f"✅ 초기화 성공: {server_name}")

            # 도구 목록 요청
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            print("📤 도구 목록 요청...")
            process.stdin.write(json.dumps(tools_request) + '\n')
            process.stdin.flush()

            # 도구 목록 응답
            tools_response = process.stdout.readline()
            if tools_response:
                tools_data = json.loads(tools_response.strip())
                tools = tools_data.get('result', {}).get('tools', [])
                print(f"✅ 도구 목록 수신: {len(tools)}개 도구")
                for tool in tools:
                    print(f"  - {tool.get('name')}: {tool.get('description')}")

                # stderr 출력 확인
                stderr_output = process.stderr.read()
                if stderr_output:
                    print(f"📝 서버 로그:\n{stderr_output}")

                return True
            else:
                print("❌ 도구 목록 응답 없음")
                return False
        else:
            stderr_output = process.stderr.read()
            print(f"❌ 초기화 응답 없음. stderr: {stderr_output}")
            return False

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False
    finally:
        if 'process' in locals():
            process.terminate()
            process.wait()

if __name__ == "__main__":
    success = test_minimal_server()
    if success:
        print("✅ 최소 서버 테스트 성공!")
        sys.exit(0)
    else:
        print("❌ 최소 서버 테스트 실패!")
        sys.exit(1)