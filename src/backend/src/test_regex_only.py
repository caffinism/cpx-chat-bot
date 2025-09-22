#!/usr/bin/env python3
"""
정규식 추출만 테스트하는 스크립트
"""

import re

def extract_booking_info(message: str) -> dict:
    """메시지에서 예약 정보 추출 (정규식만)"""
    extracted = {}
    
    # 이름 추출
    name_patterns = [
        r"([가-힣]{2,4})입니다",
        r"([가-힣]{2,4})이에요",
        r"([가-힣]{2,4})이라고",
        r"([가-힣]{2,4})라고",
        r"성함은\s*([가-힣]{2,4})",
        r"이름은\s*([가-힣]{2,4})",
        r"^\s*([가-힣]{2,4})\s*,",  # '박영재, 010-...' 형태
        r"^\s*([가-힣]{2,4})\s+",   # '박영재 010-...' 형태 (공백으로 구분)
        r"([가-힣]{2,4})\s+010",    # '박영재 010-...' 형태 (전화번호 앞)
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, message)
        if match:
            extracted["patient_name"] = match.group(1)
            print(f"이름 패턴 매치: {pattern} -> {match.group(1)}")
            break
    
    # 전화번호 추출
    phone_patterns = [
        r"(\d{3}-\d{4}-\d{4})",           # 010-1234-5678
        r"(\d{3}\s*\d{4}\s*\d{4})",     # 010 1234 5678 / 01012345678
        r"(\d{3}-\d{8})",                  # 010-12345678 (normalize to 010-1234-5678)
        r"(\d{11})"                          # 11 digits contiguous
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, message)
        if match:
            token = match.group(1)
            print(f"전화번호 패턴 매치: {pattern} -> {token}")
            # Remove non-digits then format if 11 digits
            digits = re.sub(r"\D", "", token)
            if len(digits) == 11:
                phone = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                extracted["phone_number"] = phone
                print(f"전화번호 포맷팅: {phone}")
            else:
                # Fallback: keep token as-is
                extracted["phone_number"] = token
            break
    
    # 날짜 추출
    date_patterns = [
        r"내일",
        r"모레",
        r"(\d{1,2}월\d{1,2}일)",     # 10월27일 (공백 없이)
        r"(\d{1,2}\s*월\s*\d{1,2}\s*일)",  # 10월 27일 (공백 있이)
        r"(\d{1,2}\s*일)",
        r"오늘"
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, message)
        if match:
            print(f"날짜 패턴 매치: {pattern} -> {match.group(0) if match.groups() else '매치됨'}")
            if "내일" in message:
                from datetime import datetime, timedelta
                tomorrow = datetime.now() + timedelta(days=1)
                extracted["preferred_date"] = tomorrow.strftime("%m월 %d일")
            elif "모레" in message:
                from datetime import datetime, timedelta
                day_after_tomorrow = datetime.now() + timedelta(days=2)
                extracted["preferred_date"] = day_after_tomorrow.strftime("%m월 %d일")
            elif "오늘" in message:
                from datetime import datetime
                today = datetime.now()
                extracted["preferred_date"] = today.strftime("%m월 %d일")
            else:
                extracted["preferred_date"] = match.group(1)
            break
    
    # 시간 추출
    time_patterns = [
        r"(오전\s*\d{1,2}\s*시)",
        r"(오후\s*\d{1,2}\s*시)",
        r"(\d{1,2}시)",  # 13시 (공백 없이)
        r"(\d{1,2}\s*시)",  # 13 시 (공백 있이)
        r"(\d{1,2}:\d{2})",  # HH:MM 형식
        r"((?:오전|오후)?\s*(?:한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s*시)",
        r"오전",
        r"오후",
        r"아침",
        r"점심",
        r"저녁"
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, message)
        if match:
            print(f"시간 패턴 매치: {pattern} -> {match.group(0) if match.groups() else '매치됨'}")
            if re.search(r"오전|아침", message):
                # 오전 N시 → 09/10 등으로 보정
                m = re.search(r"오전\s*(\d{1,2})\s*시", message)
                if m:
                    hour = int(m.group(1))
                    extracted["preferred_time"] = f"{hour:02d}:00"
                else:
                    extracted["preferred_time"] = "09:00"
            elif re.search(r"오후", message):
                m = re.search(r"오후\s*(\d{1,2})\s*시", message)
                if m:
                    hour = int(m.group(1))
                    if hour < 12:
                        hour += 12
                    extracted["preferred_time"] = f"{hour:02d}:00"
                else:
                    extracted["preferred_time"] = "14:00"
            elif "점심" in message:
                extracted["preferred_time"] = "12:00"
            elif "저녁" in message:
                extracted["preferred_time"] = "18:00"
            else:
                time_str = match.group(1) if match.groups() else match.group(0)
                if "시" in time_str:
                    # '오전/오후' 없이 '10시' 등
                    m = re.search(r"(\d{1,2})\s*시", time_str)
                    if m:
                        hour = int(m.group(1))
                        extracted["preferred_time"] = f"{hour:02d}:00"
                        print(f"시간 추출: {hour}시 -> {extracted['preferred_time']}")
                    else:
                        # 한/두/세... 시 처리
                        num_map = {"한":1, "두":2, "셋":3, "세":3, "넷":4, "다섯":5, "여섯":6, "일곱":7, "여덟":8, "아홉":9, "열":10}
                        m2 = re.search(r"(한|두|셋|세|넷|다섯|여섯|일곱|여덟|아홉|열)\s*시", time_str)
                        if m2:
                            hour = num_map[m2.group(1)]
                            extracted["preferred_time"] = f"{hour:02d}:00"
                        else:
                            extracted["preferred_time"] = time_str
                elif ":" in time_str:
                    # HH:MM 형식
                    extracted["preferred_time"] = time_str
                else:
                    extracted["preferred_time"] = time_str
            break
    
    return extracted

def test_extraction():
    """추출 테스트"""
    test_cases = [
        "박영재 01054226448 10월27일 13시",
        "홍길동 010-1234-5678 내일 오후 3시",
        "김민수 01012345678 모레 12시",
        "이영희 010 9876 5432 오늘 점심",
    ]
    
    for message in test_cases:
        print(f"\n테스트 메시지: {message}")
        print("=" * 50)
        result = extract_booking_info(message)
        print(f"최종 결과: {result}")
        print()

if __name__ == "__main__":
    test_extraction()
