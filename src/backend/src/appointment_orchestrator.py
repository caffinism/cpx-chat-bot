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
    
    def is_booking_request(self, message: str) -> bool:
        """예약 요청인지 확인 (정교화된 로직)"""
        message_clean = message.strip().lower()

        # 1. "예약", "잡아줘" 등 명시적인 예약 키워드가 포함되어 있는지 확인
        explicit_booking_indicators = ["예약", "잡아줘", "잡아주", "예약해"]
        if any(indicator in message_clean for indicator in explicit_booking_indicators):
            return True

        # 2. "아니요", "싫어요" 등 명확한 거절 표현으로 시작하는지 확인
        # "괜찮아요"는 긍정과 부정 모두 가능하므로 제외
        negative_starters = ["아니요", "아니", "싫어", "필요 없어", "안할래", "안해"]
        if any(message_clean.startswith(starter) for starter in negative_starters):
            return False

        # 3. "네", "좋아요" 등 긍정적인 답변으로 문장이 시작하는지 확인 (짧은 응답 위주)
        positive_starters = ["네", "예", "응", "좋아요", "좋습니다", "해주세요", "해줘", "그래요", "그래"]
        # 문장 전체가 긍정 스타터 중 하나이거나, 긍정 스타터로 시작하고 짧은 추가 정보가 붙는 경우
        if any(message_clean.startswith(starter) for starter in positive_starters):
            # "네", "네 좋아요" 같은 경우는 True
            # "네, 내일 12시요" 같은 경우도 True
            # 하지만 "네, 그런데 다른 증상은 없어요" 같은 긴 문장은 제외 (5단어 이상)
            if len(message_clean.split()) < 5:
                return True

        # 위 조건에 모두 해당하지 않으면 예약 요청이 아님
        return False
    
    def extract_department_from_consultation(self, consultation_text: str) -> Optional[str]:
        """상담 내용에서 진료과 추출"""
        # 의료진 연계 섹션에서 진료과 추출
        department_patterns = [
            r"의료진 연계[:\s]*([^:]+)",
            r"([가-힣]+과)",
            r"([가-힣]+내과)",
            r"([가-힣]+외과)",
            r"([가-힣]+소아과)",
            r"([가-힣]+산부인과)",
            r"([가-힣]+정신과)",
            r"([가-힣]+피부과)",
            r"([가-힣]+안과)",
            r"([가-힣]+이비인후과)",
            r"([가-힣]+정형외과)",
            r"([가-힣]+신경과)",
            r"([가-힣]+흉부외과)",
            r"([가-힣]+비뇨기과)",
            r"([가-힣]+마취과)"
        ]
        
        for pattern in department_patterns:
            match = re.search(pattern, consultation_text)
            if match:
                department = match.group(1).strip()
                # 일반적인 진료과명으로 정리
                if "내과" in department and "소화기" not in department:
                    return "소화기내과"
                elif "외과" in department and "정형" not in department:
                    return "일반외과"
                return department
        
        return "내과"  # 기본값
    
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
            booking_info = self.appointment_service.get_booking_info(chat_id)
        
        # 예약 프롬프트로 응답 생성
        prompt = self.booking_prompt.format(
            query=message,
            consultation_summary=booking_info.consultation_summary
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
