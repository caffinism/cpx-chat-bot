#!/usr/bin/env python3
"""
간단한 LLM 호출 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aoai_client import AOAIClient

def test_simple_llm():
    """간단한 LLM 호출 테스트"""
    
    try:
        # AOAI 클라이언트 초기화
        aoai_client = AOAIClient(
            endpoint="https://your-endpoint.openai.azure.com/",
            deployment="your-deployment",
            api_version="2023-12-01-preview"
        )
        print("AOAI 클라이언트 초기화 성공")
        
        # 간단한 메시지로 테스트
        test_message = "안녕하세요"
        
        print(f"테스트 메시지: {test_message}")
        print("=" * 50)
        
        # 1. 기본 호출 테스트
        print("1. 기본 호출 테스트:")
        try:
            response = aoai_client.chat_completion(test_message)
            print(f"응답: {response}")
        except Exception as e:
            print(f"기본 호출 실패: {e}")
        
        print()
        
        # 2. response_format 없이 테스트
        print("2. response_format 없이 테스트:")
        try:
            response = aoai_client.chat_completion(
                test_message,
                use_rag=False,
                function_calling=False
            )
            print(f"응답: {response}")
        except Exception as e:
            print(f"response_format 없이 호출 실패: {e}")
        
        print()
        
        # 3. response_format과 함께 테스트
        print("3. response_format과 함께 테스트:")
        try:
            response = aoai_client.chat_completion(
                test_message,
                use_rag=False,
                function_calling=False,
                response_format={"type": "json_object"}
            )
            print(f"응답: {response}")
        except Exception as e:
            print(f"response_format과 함께 호출 실패: {e}")
        
    except Exception as e:
        print(f"AOAI 클라이언트 초기화 실패: {e}")
        print("환경 변수를 확인해주세요.")

if __name__ == "__main__":
    test_simple_llm()
