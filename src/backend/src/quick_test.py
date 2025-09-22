#!/usr/bin/env python3
"""
빠른 테스트 스크립트
"""

import re

def test_extraction():
    """추출 테스트"""
    message = "박영재 01054226448 10월27일 13시"
    print(f"테스트 메시지: {message}")
    print("=" * 50)
    
    extracted = {}
    
    # 이름 추출
    name_patterns = [
        r"^\s*([가-힣]{2,4})\s+",   # '박영재 010-...' 형태
        r"([가-힣]{2,4})\s+010",    # '박영재 010-...' 형태
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, message)
        if match:
            extracted["patient_name"] = match.group(1)
            print(f"이름 추출: {pattern} -> {match.group(1)}")
            break
    
    # 전화번호 추출
    phone_patterns = [
        r"(\d{3}\s*\d{4}\s*\d{4})",     # 010 1234 5678
        r"(\d{11})"                          # 11 digits contiguous
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, message)
        if match:
            token = match.group(1)
            digits = re.sub(r"\D", "", token)
            if len(digits) == 11:
                phone = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                extracted["phone_number"] = phone
                print(f"전화번호 추출: {pattern} -> {token} -> {phone}")
            break
    
    # 날짜 추출
    date_patterns = [
        r"(\d{1,2}월\d{1,2}일)",     # 10월27일
        r"(\d{1,2}\s*월\s*\d{1,2}\s*일)",  # 10월 27일
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, message)
        if match:
            extracted["preferred_date"] = match.group(1)
            print(f"날짜 추출: {pattern} -> {match.group(1)}")
            break
    
    # 시간 추출
    time_patterns = [
        r"(\d{1,2}시)",  # 13시
        r"(\d{1,2}\s*시)",  # 13 시
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, message)
        if match:
            time_str = match.group(1)
            if "시" in time_str:
                m = re.search(r"(\d{1,2})\s*시", time_str)
                if m:
                    hour = int(m.group(1))
                    extracted["preferred_time"] = f"{hour:02d}:00"
                    print(f"시간 추출: {pattern} -> {time_str} -> {extracted['preferred_time']}")
            break
    
    print(f"\n최종 추출 결과: {extracted}")
    return extracted

if __name__ == "__main__":
    test_extraction()
