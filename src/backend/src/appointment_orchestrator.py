import re
import json
from typing import Tuple, Optional
from aoai_client import AOAIClient, get_prompt
from services.appointment_service import AppointmentService
from models.appointment import BookingInfo

class AppointmentOrchestrator:
    """예약 처리 오케스트레이터"""
    
    def __init__(self, aoai_client: AOAIClient):
        self.aoai_client = aoai_client
        self.booking_prompt = get_prompt("appointment_booking.txt")
        self.booking_extraction_prompt = get_prompt("booking_info_extraction.txt")
        self.department_extraction_prompt = get_prompt("department_extraction.txt")
        self.appointment_service = AppointmentService()
    
    def extract_department_from_consultation(self, consultation_text: str) -> Optional[str]:
        """상담 내용에서 진료과 추출 (LLM 기반)"""
        print(f"[DEBUG] Extracting department from: {consultation_text}")
        
        try:
            # LLM에 진료과 추출 요청
            prompt = self.department_extraction_prompt.format(consultation_text=consultation_text)
            raw_response = self.aoai_client.chat_completion(prompt)
            print(f"[DEBUG] LLM department extraction response: {raw_response}")
            
            # 응답에서 진료과명 추출 (한글만)
            response_clean = raw_response.strip()
            dept_match = re.search(r'([가-힣]+과)', response_clean)
            if dept_match:
                dept = dept_match.group(1).strip()
                print(f"[DEBUG] Extracted department: {dept}")
                return dept
            else:
                print(f"[DEBUG] No department found in LLM response: '{response_clean}', using default: 내과")
                return "내과"
                
        except Exception as e:
            print(f"[ERROR] LLM department extraction failed: {e}")
            # 폴백: 정규식으로 추출 시도
            offer_match = re.search(r"([가-힣]+과)에 예약을 잡아드릴까요\?", consultation_text)
            if offer_match:
                dept = offer_match.group(1).strip()
                print(f"[DEBUG] Fallback: Found department from offer pattern: {dept}")
                return dept
            print(f"[DEBUG] Fallback: No department found, using default: 내과")
            return "내과"
    
    def handle_booking_request(self, chat_id: str, consultation_text: str, message: str) -> Tuple[str, bool]:
        """Starts a booking session and processes the first user message."""
        
        # 1. Start the session
        department = self.extract_department_from_consultation(consultation_text)
        self.appointment_service.start_booking_session(
            chat_id=chat_id,
            department=department,
            consultation_summary=consultation_text
        )

        # 2. Process the first message using the same logic as subsequent messages
        return self.process_booking_message(chat_id, message)
    
    def process_booking_message(self, chat_id: str, message: str) -> Tuple[str, bool]:
        """예약 관련 메시지 처리 (LLM 기반)"""
        booking_info = self.appointment_service.get_booking_info(chat_id)
        if not booking_info:
            return "예약 세션을 찾을 수 없습니다. 다시 시작해주세요.", False
        
        # LLM으로 정보 추출
        extraction_result = self._extract_booking_info_with_llm(message)
        print(f"[DEBUG] LLM extraction result: {extraction_result}")
        
        # 정규식 기반 추출 (주요 추출 방법)
        regex_extracted = self._extract_booking_info(message)
        print(f"[DEBUG] Regex extraction result: {regex_extracted}")
        
        # 추출된 정보 업데이트 (정규식 우선, LLM 보조)
        update_data: dict = {}
        
        # 1. 정규식으로 추출한 정보를 먼저 사용
        for k, v in regex_extracted.items():
            if v:
                update_data[k] = v
                print(f"[DEBUG] Using regex extracted {k}: {v}")
        
        # 2. LLM 추출 결과로 보강 (정규식에서 누락된 것만)
        if extraction_result and extraction_result.get("extracted"):
            for k, v in extraction_result["extracted"].items():
                if v is not None and k not in update_data:
                    update_data[k] = v
                    print(f"[DEBUG] Using LLM extracted {k}: {v}")
        
        print(f"[DEBUG] Final update_data: {update_data}")
        
        if update_data:
            self.appointment_service.update_booking_info(chat_id, **update_data)
            # 업데이트된 정보로 다시 로드
            booking_info = self.appointment_service.get_booking_info(chat_id)
            print(f"[DEBUG] Updated booking_info: {booking_info}")
            print(f"[DEBUG] booking_info.is_complete(): {booking_info.is_complete()}")
        
        # 프롬프트에 전달할 현재까지 수집된 정보 문자열 생성
        collected_info_str = booking_info.to_summary_string()

        # 누락된 필드 계산
        missing_labels: list[str] = []
        if not booking_info.patient_name:
            missing_labels.append("성함")
        if not booking_info.phone_number:
            missing_labels.append("연락처")
        if not booking_info.preferred_date:
            missing_labels.append("희망 날짜")
        if not booking_info.preferred_time:
            missing_labels.append("희망 시간")
        missing_fields_str = ", ".join(missing_labels) if missing_labels else "없음"
        
        print(f"[DEBUG] Missing fields: {missing_labels}")
        print(f"[DEBUG] Missing fields string: {missing_fields_str}")

        # 예약 완료 확인 (정보가 완전하고 확인 의도가 있으면 예약 완료)
        is_confirmation = extraction_result and extraction_result.get("confirmation_intent", False)
        if booking_info.is_complete() and is_confirmation:
            try:
                appointment_response = self.appointment_service.create_appointment(chat_id)
                response = f"예약이 완료되었습니다!\n예약번호: {appointment_response.appointment_id}\n{appointment_response.appointment_date} {appointment_response.appointment_time}에 {appointment_response.department}로 오시면 됩니다."
                return response, True  # 예약 완료
            except Exception as e:
                response = f"예약 처리 중 오류가 발생했습니다: {str(e)}"
                return response, False
        
        # 예약 프롬프트로 응답 생성 (정보가 부족한 경우만)
        prompt = self.booking_prompt.format(
            department=booking_info.department,
            consultation_summary=booking_info.consultation_summary,
            collected_info=collected_info_str,
            missing_fields=missing_fields_str,
            query=message
        )
        
        response = self.aoai_client.chat_completion(prompt)
        return response, False
    
    def _extract_booking_info_with_llm(self, message: str) -> dict:
        """LLM을 사용한 예약 정보 추출"""
        try:
            print(f"[DEBUG] Starting LLM extraction for message: {message}")
            
            # LLM에 정보 추출 요청
            prompt = self.booking_extraction_prompt.format(query=message)
            print(f"[DEBUG] Using prompt: {prompt[:200]}...")
            
            raw_response = self.aoai_client.chat_completion(
                prompt,
                use_rag=False,
                function_calling=False,
                response_format={"type": "json_object"}
            )
            print(f"[DEBUG] LLM extraction raw response: {raw_response}")
            print(f"[DEBUG] Raw response length: {len(raw_response) if raw_response else 0}")
            print(f"[DEBUG] Raw response type: {type(raw_response)}")
            
            if not raw_response:
                print("[ERROR] LLM returned empty response")
                return {"extracted": {}, "missing": ["patient_name", "phone_number", "preferred_date", "preferred_time"], "confirmation_intent": False}
            
            # JSON 파싱 (aoai_client에서 이미 수정됨)
            response_clean = raw_response.strip()
            print(f"[DEBUG] Raw response: {repr(response_clean)}")
            
            # JSON 파싱
            try:
                extraction_result = json.loads(response_clean)
                print(f"[DEBUG] Successfully parsed JSON: {extraction_result}")
                
                # 결과 검증
                if not isinstance(extraction_result, dict):
                    print(f"[ERROR] Parsed result is not a dict: {type(extraction_result)}")
                    return {"extracted": {}, "missing": ["patient_name", "phone_number", "preferred_date", "preferred_time"], "confirmation_intent": False}
                
                # 필수 키 확인
                required_keys = ["extracted", "missing", "confirmation_intent"]
                for key in required_keys:
                    if key not in extraction_result:
                        print(f"[ERROR] Missing required key '{key}' in result")
                        return {"extracted": {}, "missing": ["patient_name", "phone_number", "preferred_date", "preferred_time"], "confirmation_intent": False}
                
                return extraction_result
                
            except json.JSONDecodeError as json_err:
                print(f"[ERROR] JSON parsing failed: {json_err}")
                print(f"[ERROR] Failed to parse: {repr(response_clean)}")
                return {"extracted": {}, "missing": ["patient_name", "phone_number", "preferred_date", "preferred_time"], "confirmation_intent": False}
            
        except Exception as e:
            print(f"[ERROR] LLM extraction failed with exception: {e}")
            print(f"[ERROR] Exception type: {type(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {"extracted": {}, "missing": ["patient_name", "phone_number", "preferred_date", "preferred_time"], "confirmation_intent": False}
    
    def _extract_booking_info(self, message: str) -> dict:
        """메시지에서 예약 정보 추출"""
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
                # Remove non-digits then format if 11 digits
                digits = re.sub(r"\D", "", token)
                if len(digits) == 11:
                    phone = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                    extracted["phone_number"] = phone
                    break
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
                    time_str = match.group(1)
                    if "시" in time_str:
                        # '오전/오후' 없이 '10시' 등
                        m = re.search(r"(\d{1,2})\s*시", time_str)
                        if m:
                            hour = int(m.group(1))
                            extracted["preferred_time"] = f"{hour:02d}:00"
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
    
    def _is_confirmation_request(self, message: str) -> bool:
        """확인 요청인지 확인"""
        confirmation_indicators = [
            "맞습니다", "맞아요", "네", "예", "확인", "맞네요",
            "그래요", "그렇습니다", "좋습니다", "좋아요"
        ]
        return any(indicator in message for indicator in confirmation_indicators)
