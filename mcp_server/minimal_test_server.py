#!/usr/bin/env python3
"""
최소한의 MCP 서버 테스트 - Claude Desktop 호환성 확인용
"""

import asyncio
import json
import sys
from typing import Any, Sequence

async def main():
    """최소한의 MCP 서버"""

    async def read_message():
        """stdin에서 JSON-RPC 메시지 읽기"""
        line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if not line:
            return None
        try:
            return json.loads(line.strip())
        except json.JSONDecodeError:
            return None

    def write_message(message: dict):
        """stdout으로 JSON-RPC 메시지 쓰기"""
        json.dump(message, sys.stdout, ensure_ascii=False)
        sys.stdout.write('\n')
        sys.stdout.flush()

    # 서버 시작 메시지 (stderr로 출력하여 프로토콜 방해 안함)
    print("🚀 Minimal MCP Server starting...", file=sys.stderr)

    try:
        while True:
            message = await read_message()
            if message is None:
                break

            # 메시지 처리
            method = message.get("method")
            request_id = message.get("id")

            if method == "initialize":
                # 초기화 응답
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "Portfolio BackTester (Minimal)",
                            "version": "1.0.0"
                        }
                    }
                }
                write_message(response)
                print(f"✅ Handled initialize request", file=sys.stderr)

            elif method == "notifications/initialized":
                # 초기화 완료 알림 - 응답 없음
                print(f"✅ Server initialized", file=sys.stderr)

            elif method == "tools/list":
                # 도구 목록 응답
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "test_tool",
                                "description": "테스트용 도구",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {
                                            "type": "string",
                                            "description": "테스트 메시지"
                                        }
                                    },
                                    "required": ["message"]
                                }
                            }
                        ]
                    }
                }
                write_message(response)
                print(f"✅ Handled tools/list request", file=sys.stderr)

            elif method == "tools/call":
                # 도구 호출 응답
                tool_name = message.get("params", {}).get("name")
                arguments = message.get("params", {}).get("arguments", {})

                if tool_name == "test_tool":
                    test_message = arguments.get("message", "No message provided")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"✅ 테스트 성공! 메시지: {test_message}"
                                }
                            ]
                        }
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }

                write_message(response)
                print(f"✅ Handled tools/call request for {tool_name}", file=sys.stderr)

            else:
                # 알 수 없는 메서드
                if request_id is not None:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                    write_message(response)
                print(f"⚠️ Unknown method: {method}", file=sys.stderr)

    except KeyboardInterrupt:
        print("🛑 Server stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"❌ Server error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Failed to start server: {e}", file=sys.stderr)
        sys.exit(1)