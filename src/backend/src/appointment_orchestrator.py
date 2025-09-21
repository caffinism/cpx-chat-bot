import re
from typing import Tuple, Optional
from aoai_client import AOAIClient, get_prompt
from services.appointment_service import AppointmentService
from models.appointment import BookingInfo

class AppointmentOrchestrator:
    """예약 처리 오케스트레이터"""
    
    def __init__(self, aoai_client: AOAIClient):
        self.aoai_client = aoai_client
        self.booking_prompt = get_prompt("appointment_booking.txt")
        self.appointment_service = AppointmentService()
    
    def extract_department_from_consultation(self, consultation_text: str) -> Optional[str]:
        """상담 내용에서 진료과 추출 (강화된 로직)"""
        # 1. "XX과에 예약을 잡아드릴까요?" 패턴에서 직접 추출 (가장 정확)
        offer_match = re.search(r"([가-힣]+과)에 예약을 잡아드릴까요\?", consultation_text)
        if offer_match:
            return offer_match.group(1).strip()

        # 2. "의료진 연계" 섹션에서 추출
        department_patterns = [
            r"의료진 연계[:\s]*([^:\n]+)",
        ]
        for pattern in department_patterns:
            match = re.search(pattern, consultation_text)
            if match:
                department_text = match.group(1)
                # "방문" 등의 단어를 제외하고 진료과만 추출
                dept_match = re.search(r"([가-힣]+과)", department_text)
                if dept_match:
                    return dept_match.group(1).strip()
        
        # 3. 일반적인 "XX과" 패턴으로 찾기
        general_match = re.search(r"([가-힣]+과)", consultation_text)
        if general_match:
            return general_match.group(1).strip()

        return "내과"  # 모든 패턴 실패 시 기본값
    
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
        """예약 관련 메시지 처리"""
        booking_info = self.appointment_service.get_booking_info(chat_id)
        if not booking_info:
            return "예약 세션을 찾을 수 없습니다. 다시 시작해주세요.", False
        
        # 정보 추출 시도
        extracted_info = self._extract_booking_info(message)
        
        # 추출된 정보 업데이트
        if extracted_info:
            self.appointment_service.update_booking_info(chat_id, **extracted_info)
            # 업데이트된 정보로 다시 로드
            booking_info = self.appointment_service.get_booking_info(chat_id)
        
        # 프롬프트에 전달할 현재까지 수집된 정보 문자열 생성
        collected_info_str = booking_info.to_summary_string()

        # 예약 프롬프트로 응답 생성
        prompt = self.booking_prompt.format(
            department=booking_info.department,
            consultation_summary=booking_info.consultation_summary,
            collected_info=collected_info_str,
            query=message
        )
        
        response = self.aoai_client.chat_completion(prompt)
        
        # 예약 완료 확인
        if booking_info.is_complete() and self._is_confirmation_request(message):
            try:
                appointment_response = self.appointment_service.create_appointment(chat_id)
                response += f"\n\n예약이 완료되었습니다!\n예약번호: {appointment_response.appointment_id}\n{appointment_response.appointment_date} {appointment_response.appointment_time}에 {appointment_response.department}로 오시면 됩니다."
                return response, True  # 예약 완료
            except Exception as e:
                response += f"\n\n예약 처리 중 오류가 발생했습니다: {str(e)}"
        
        return response, False
    
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
            r"이름은\s*([가-힣]{2,4})"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message)
            if match:
                extracted["patient_name"] = match.group(1)
                break
        
        # 전화번호 추출
        phone_patterns = [
            r"(\d{3}-\d{4}-\d{4})",
            r"(\d{3}\s*\d{4}\s*\d{4})",
            r"(\d{11})"
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, message)
            if match:
                phone = match.group(1).replace(" ", "-")
                if len(phone) == 11 and not "-" in phone:
                    phone = f"{phone[:3]}-{phone[3:7]}-{phone[7:]}"
                extracted["phone_number"] = phone
                break
        
        # 날짜 추출
        date_patterns = [
            r"내일",
            r"모레",
            r"(\d{1,2}월\s*\d{1,2}일)",
            r"(\d{1,2}일)",
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
            r"(\d{1,2}시)",
            r"(\d{1,2}:\d{2})",
            r"오전",
            r"오후",
            r"아침",
            r"점심",
            r"저녁"
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, message)
            if match:
                if "오전" in message or "아침" in message:
                    extracted["preferred_time"] = "09:00"
                elif "오후" in message:
                    extracted["preferred_time"] = "14:00"
                elif "점심" in message:
                    extracted["preferred_time"] = "12:00"
                elif "저녁" in message:
                    extracted["preferred_time"] = "18:00"
                else:
                    time_str = match.group(1)
                    if "시" in time_str:
                        hour = int(time_str.replace("시", ""))
                        extracted["preferred_time"] = f"{hour:02d}:00"
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
