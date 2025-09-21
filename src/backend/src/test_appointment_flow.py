#!/usr/bin/env python3
"""
예약 시스템 테스트 스크립트
의료 상담 후 예약 플로우를 테스트합니다.
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from appointment_orchestrator import AppointmentOrchestrator
from aoai_client import AOAIClient
from services.appointment_service import appointment_service

async def test_appointment_flow():
    """예약 플로우 테스트"""
    
    # Mock AOAI client for testing
    class MockAOAIClient:
        def chat_completion(self, prompt):
            if "성함을 알려주세요" in prompt:
                return "김철수님, 감사합니다. 연락처를 알려주세요."
            elif "연락처를 알려주세요" in prompt:
                return "010-1234-5678입니다."
            elif "희망하시는 날짜" in prompt:
                return "내일 오후가 좋겠어요."
            elif "몇 시 정도가 편하신가요" in prompt:
                return "2시 정도요."
            elif "확인해보겠습니다" in prompt:
                return "네, 맞습니다."
            else:
                return "안녕하세요! 의료 상담을 완료하셨네요. 소화기내과에 예약을 잡아드릴게요. 먼저 성함을 알려주세요."
    
    # Initialize orchestrator
    mock_client = MockAOAIClient()
    orchestrator = AppointmentOrchestrator(mock_client)
    
    # Test consultation text
    consultation_text = """
    1) 추정진단 및 감별진단: 소화불량 가능성 높음; 위염, 위궤양 감별 필요
    2) 권장 검사 및 술기: 상부위내시경, 위산분비검사
    3) 치료 및 처치: 제산제, 위장관 보호제, 식이조절
    4) 의료진 연계: 소화기내과; 1주일 내 방문 권장
    5) 환자교육 및 안전지침: 자극적 음식 피하기, 규칙적 식사
    6) 예후 및 경과: 대부분 2-4주 내 호전 예상
    """
    
    print("=== 의료 상담 후 예약 플로우 테스트 ===\n")
    
    # Step 1: 다양한 예약 요청 감지 테스트
    test_messages = [
        "네, 예약 잡아주세요",  # 명시적 예약 요청
        "네",                   # 단순 긍정 응답
        "좋아요",               # 긍정 응답
        "해주세요",             # 긍정 응답
        "그래요",               # 긍정 응답
        "아니요",               # 부정 응답
        "괜찮아요",             # 부정 응답 (괜찮다는 의미)
        "안할래요",             # 부정 응답
        "머리가 아파요"         # 의료 상담 요청
    ]
    
    print("=== 예약 요청 감지 테스트 ===")
    for message in test_messages:
        is_booking = orchestrator.is_booking_request(message)
        print(f"'{message}' -> 예약 요청: {is_booking}")
    print()
    
    # Step 2: 예약 프로세스 시작
    chat_id = "test_chat_001"
    response = orchestrator.start_booking_process(chat_id, consultation_text)
    print(f"예약 시작 응답: {response}\n")
    
    # Step 3: 예약 정보 수집 시뮬레이션
    booking_messages = [
        "김철수입니다",
        "010-1234-5678입니다", 
        "내일 오후가 좋겠어요",
        "2시 정도요",
        "네, 맞습니다"
    ]
    
    print("=== 예약 정보 수집 테스트 ===")
    for i, message in enumerate(booking_messages, 1):
        print(f"Step {i}: {message}")
        response, complete = orchestrator.process_booking_message(chat_id, message)
        print(f"응답: {response}")
        print(f"완료 여부: {complete}\n")
        
        if complete:
            break
    
    # Step 4: 예약 정보 확인
    booking_info = appointment_service.get_booking_info(chat_id)
    if booking_info:
        print(f"예약 정보: {booking_info.dict()}")
    else:
        print("예약이 완료되어 세션이 정리되었습니다.")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    asyncio.run(test_appointment_flow())
