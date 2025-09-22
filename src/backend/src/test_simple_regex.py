#!/usr/bin/env python3
"""
간단한 정규식 테스트
"""

import re

def test_regex_patterns():
    """정규식 패턴 테스트"""
    
    test_message = "박영재 01054226448 10월27일 13시"
    print(f"테스트 메시지: {test_message}")
    print("=" * 50)
    
    # 이름 추출 테스트
    print("1. 이름 추출 테스트:")
    name_patterns = [
        r"^\s*([가-힣]{2,4})\s+",   # '박영재 010-...' 형태 (공백으로 구분)
        r"([가-힣]{2,4})\s+010",    # '박영재 010-...' 형태 (전화번호 앞)
    ]
    
    for i, pattern in enumerate(name_patterns):
        match = re.search(pattern, test_message)
        if match:
            print(f"  패턴 {i+1} 매치: {pattern} -> {match.group(1)}")
        else:
            print(f"  패턴 {i+1} 미매치: {pattern}")
    
    print()
    
    # 전화번호 추출 테스트
    print("2. 전화번호 추출 테스트:")
    phone_patterns = [
        r"(\d{3}\s*\d{4}\s*\d{4})",     # 010 1234 5678 / 01012345678
        r"(\d{11})"                          # 11 digits contiguous
    ]
    
    for i, pattern in enumerate(phone_patterns):
        match = re.search(pattern, test_message)
        if match:
            token = match.group(1)
            digits = re.sub(r"\D", "", token)
            if len(digits) == 11:
                phone = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                print(f"  패턴 {i+1} 매치: {pattern} -> {token} -> {phone}")
            else:
                print(f"  패턴 {i+1} 매치: {pattern} -> {token}")
        else:
            print(f"  패턴 {i+1} 미매치: {pattern}")
    
    print()
    
    # 날짜 추출 테스트
    print("3. 날짜 추출 테스트:")
    date_patterns = [
        r"(\d{1,2}월\d{1,2}일)",     # 10월27일 (공백 없이)
        r"(\d{1,2}\s*월\s*\d{1,2}\s*일)",  # 10월 27일 (공백 있이)
    ]
    
    for i, pattern in enumerate(date_patterns):
        match = re.search(pattern, test_message)
        if match:
            print(f"  패턴 {i+1} 매치: {pattern} -> {match.group(1)}")
        else:
            print(f"  패턴 {i+1} 미매치: {pattern}")
    
    print()
    
    # 시간 추출 테스트
    print("4. 시간 추출 테스트:")
    time_patterns = [
        r"(\d{1,2}시)",  # 13시 (공백 없이)
        r"(\d{1,2}\s*시)",  # 13 시 (공백 있이)
    ]
    
    for i, pattern in enumerate(time_patterns):
        match = re.search(pattern, test_message)
        if match:
            print(f"  패턴 {i+1} 매치: {pattern} -> {match.group(1)}")
        else:
            print(f"  패턴 {i+1} 미매치: {pattern}")

if __name__ == "__main__":
    test_regex_patterns()
