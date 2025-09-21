#!/usr/bin/env python3
"""
매우 간단한 MCP 서버 - 표준 MCP 사용
"""

import asyncio
import json
import sys
import logging

# 로깅 비활성화
logging.getLogger().setLevel(logging.CRITICAL)

async def main():
    """간단한 MCP 서버"""

    # 초기화 대기
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            message = json.loads(line.strip())
            method = message.get("method")
            msg_id = message.get("id")

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": "Simple Portfolio Test",
                            "version": "1.0.0"
                        }
                    }
                }
                print(json.dumps(response))
                sys.stdout.flush()

            elif method == "notifications/initialized":
                pass  # 초기화 완료 알림

            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": [
                            {
                                "name": "hello",
                                "description": "간단한 인사 도구",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            }
                        ]
                    }
                }
                print(json.dumps(response))
                sys.stdout.flush()

            elif method == "tools/call":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": "✅ Simple MCP server is working!"
                            }
                        ]
                    }
                }
                print(json.dumps(response))
                sys.stdout.flush()

            else:
                if msg_id:
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown method: {method}"
                        }
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()

        except json.JSONDecodeError:
            continue
        except Exception:
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        sys.exit(1)