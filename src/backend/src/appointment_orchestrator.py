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
        """예약 요청인지 확인"""
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
    
    def start_booking_process(self, chat_id: str, consultation_text: str) -> str:
        """예약 프로세스 시작"""
        department = self.extract_department_from_consultation(consultation_text)
        
        # 예약 세션 시작
        self.appointment_service.start_booking_session(
            chat_id=chat_id,
            department=department,
            consultation_summary=consultation_text
        )
        
        # 예약 프롬프트로 응답 생성
        prompt = self.booking_prompt.format(
            query=f"안녕하세요! 의료 상담을 완료하셨네요. {department}에 예약을 잡아드릴게요. 먼저 성함을 알려주세요.",
            consultation_summary=consultation_text
        )
        
        return self.aoai_client.chat_completion(prompt)
    
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
