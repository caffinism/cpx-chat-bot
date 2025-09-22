#!/usr/bin/env python3
"""
간단한 추출 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from appointment_orchestrator import AppointmentOrchestrator
from aoai_client import AOAIClient

def test_extraction():
    """추출 로직 테스트"""
    
    # AOAI 클라이언트 초기화 (실제 설정 필요)
    try:
        aoai_client = AOAIClient(
            endpoint="https://your-endpoint.openai.azure.com/",
            deployment="your-deployment",
            api_version="2023-12-01-preview"
        )
    except Exception as e:
        print(f"AOAI 클라이언트 초기화 실패: {e}")
        print("환경 변수를 확인해주세요.")
        return
    
    orchestrator = AppointmentOrchestrator(aoai_client)
    
    # 테스트 메시지
    test_message = "박영재 01054226448 10월27일 13시"
    
    print(f"테스트 메시지: {test_message}")
    print("=" * 50)
    
    # 정규식 추출 테스트
    print("1. 정규식 추출 테스트:")
    regex_result = orchestrator._extract_booking_info(test_message)
    print(f"결과: {regex_result}")
    print()
    
    # LLM 추출 테스트 (실제 호출)
    print("2. LLM 추출 테스트:")
    try:
        llm_result = orchestrator._extract_booking_info_with_llm(test_message)
        print(f"결과: {llm_result}")
    except Exception as e:
        print(f"LLM 추출 실패: {e}")
    print()

if __name__ == "__main__":
    test_extraction()
