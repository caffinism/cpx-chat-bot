#!/usr/bin/env python3
"""
예약 감지 로직 단위 테스트
의존성 없이 예약 감지 로직만 테스트합니다.
"""

def is_booking_request(message: str) -> bool:
    """예약 요청인지 확인 (appointment_orchestrator.py의 로직 복사)"""
    # 명시적 예약 키워드
    explicit_booking_indicators = [
        "예약", "예약해", "예약해주", "예약하고", "예약할래", "예약하자",
        "잡아", "잡아주", "잡아줘", "잡아드릴까요", "예약잡아", "예약잡아주"
    ]
    
    # 긍정 응답 (예약 제안에 대한 긍정적 답변)
    positive_response_indicators = [
        "네", "예", "좋아요", "좋습니다", "네요", "예요", "어요",
        "해주세요", "해주", "해줘", "해줄래", "해줄게", "해줄게요",
        "그래요", "그래", "그렇습니다", "그렇네요", "맞아요", "맞습니다",
        "괜찮아요", "괜찮습니다", "괜찮네요", "좋네요", "좋겠어요",
        "해도", "해도돼", "해도돼요", "해도됩니다", "해도괜찮아요",
        "좋은데요", "좋은데", "좋겠는데요", "좋겠는데"
    ]
    
    # 부정 응답 (예약을 원하지 않는 경우)
    negative_response_indicators = [
        "아니요", "아니", "싫어요", "싫습니다", "안돼요", "안됩니다",
        "괜찮아요", "괜찮습니다", "필요없어요", "필요없습니다",
        "안할래요", "안할래", "안해요", "안합니다"
    ]
    
    message_lower = message.lower().strip()
    
    # 명시적 예약 키워드가 있으면 예약 요청
    if any(indicator in message for indicator in explicit_booking_indicators):
        return True
    
    # 부정 응답이 있으면 예약 요청이 아님
    if any(indicator in message for indicator in negative_response_indicators):
        return False
    
    # 긍정 응답이 있으면 예약 요청
    if any(indicator in message for indicator in positive_response_indicators):
        # 명시적 긍정 응답은 길이에 관계없이 예약 요청으로 인식
        explicit_positive = ["네", "예", "응", "해줘", "해주", "좋아요", "좋습니다"]
        if message.strip() in explicit_positive:
            return True
        # 긴 문장에서 긍정 응답이 포함된 경우
        elif len(message.strip()) > 2:
            return True
    
    return False

def test_booking_detection():
    """예약 감지 테스트"""
    
    print("=== 예약 요청 감지 테스트 ===\n")
    
    # 테스트 케이스들
    test_cases = [
        # 명시적 예약 요청 (True 예상)
        ("네, 예약 잡아주세요", True),
        ("예약해주세요", True),
        ("예약 잡아주", True),
        ("잡아주세요", True),
        ("예약잡아주세요", True),
        
        # 긍정 응답 (True 예상)
        ("네", True),
        ("예", True),
        ("좋아요", True),
        ("좋습니다", True),
        ("해주세요", True),
        ("해줘", True),
        ("그래요", True),
        ("맞아요", True),
        ("좋겠어요", True),
        ("해도돼요", True),
        
        # 부정 응답 (False 예상)
        ("아니요", False),
        ("아니", False),
        ("싫어요", False),
        ("안돼요", False),
        ("괜찮아요", False),  # "괜찮다"는 부정의 의미
        ("필요없어요", False),
        ("안할래요", False),
        
        # 의료 상담 요청 (False 예상)
        ("머리가 아파요", False),
        ("배가 아파요", False),
        ("열이 나요", False),
        ("어지러워요", False),
        
        # 애매한 케이스들
        ("네, 그런데", True),  # 긍정 응답이 포함됨
        ("좋은데요", True),    # 긍정 응답이 포함됨
        ("아니, 괜찮아요", False),  # 부정 응답이 먼저
        ("괜찮아요, 안해도 돼요", False),  # 부정 응답이 포함됨
    ]
    
    # 테스트 실행
    passed = 0
    failed = 0
    
    for message, expected in test_cases:
        result = is_booking_request(message)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} '{message}' -> {result} (예상: {expected})")
    
    print(f"\n=== 테스트 결과 ===")
    print(f"통과: {passed}")
    print(f"실패: {failed}")
    print(f"성공률: {passed/(passed+failed)*100:.1f}%")
    
    return failed == 0

if __name__ == "__main__":
    success = test_booking_detection()
    exit(0 if success else 1)
