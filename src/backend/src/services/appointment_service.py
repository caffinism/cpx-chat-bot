import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from models.appointment import AppointmentRequest, AppointmentResponse, AppointmentStatus, BookingInfo

class AppointmentService:
    """예약 관리 서비스"""
    
    def __init__(self):
        # 실제 운영에서는 데이터베이스 사용
        self.appointments: List[AppointmentRequest] = []
        self.booking_sessions: dict = {}  # chat_id -> BookingInfo
        
        # 샘플 예약 추가
        self._add_sample_appointment()
    
    def start_booking_session(self, chat_id: str, department: str, consultation_summary: str) -> None:
        """예약 세션 시작"""
        self.booking_sessions[chat_id] = BookingInfo(
            department=department,
            consultation_summary=consultation_summary
        )
    
    def update_booking_info(self, chat_id: str, **kwargs) -> BookingInfo:
        """예약 정보 업데이트"""
        if chat_id not in self.booking_sessions:
            raise ValueError("Booking session not found")
        
        booking_info = self.booking_sessions[chat_id]
        for key, value in kwargs.items():
            if hasattr(booking_info, key):
                setattr(booking_info, key, value)
        
        return booking_info
    
    def get_booking_info(self, chat_id: str) -> Optional[BookingInfo]:
        """예약 정보 조회"""
        return self.booking_sessions.get(chat_id)
    
    def create_appointment(self, chat_id: str) -> AppointmentResponse:
        """예약 생성"""
        booking_info = self.get_booking_info(chat_id)
        if not booking_info or not booking_info.is_complete():
            raise ValueError("Incomplete booking information")
        
        appointment_request = booking_info.to_appointment_request()
        appointment_id = self._generate_appointment_id()
        
        # 예약 생성
        appointment_request.appointment_id = appointment_id
        appointment_request.status = AppointmentStatus.CONFIRMED
        self.appointments.append(appointment_request)
        
        # 세션 정리
        del self.booking_sessions[chat_id]
        
        return AppointmentResponse(
            appointment_id=appointment_id,
            patient_name=appointment_request.patient_name,
            department=appointment_request.department,
            appointment_date=appointment_request.preferred_date,
            appointment_time=appointment_request.preferred_time,
            status=appointment_request.status,
            created_at=appointment_request.created_at
        )
    
    def get_appointment(self, appointment_id: str) -> Optional[AppointmentRequest]:
        """예약 조회"""
        for appointment in self.appointments:
            if appointment.appointment_id == appointment_id:
                return appointment
        return None
    
    def cancel_appointment(self, appointment_id: str) -> bool:
        """예약 취소"""
        appointment = self.get_appointment(appointment_id)
        if appointment:
            appointment.status = AppointmentStatus.CANCELLED
            return True
        return False
    
    def get_available_slots(self, department: str, date: str) -> List[str]:
        """가용 시간 조회 (간단한 구현)"""
        # 실제로는 의료진 스케줄과 기존 예약을 확인해야 함
        base_slots = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
            "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"
        ]
        
        # 해당 날짜의 기존 예약 확인
        existing_appointments = [
            apt for apt in self.appointments 
            if apt.department == department 
            and apt.preferred_date == date 
            and apt.status == AppointmentStatus.CONFIRMED
        ]
        
        booked_times = [apt.preferred_time for apt in existing_appointments]
        available_slots = [slot for slot in base_slots if slot not in booked_times]
        
        return available_slots
    
    def _generate_appointment_id(self) -> str:
        """예약번호 생성"""
        return f"APT{len(self.appointments) + 1:06d}"
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> None:
        """만료된 예약 세션 정리"""
        current_time = datetime.now()
        expired_sessions = []
        
        for chat_id, booking_info in self.booking_sessions.items():
            if (current_time - booking_info.created_at).total_seconds() > max_age_hours * 3600:
                expired_sessions.append(chat_id)
        
        for chat_id in expired_sessions:
            del self.booking_sessions[chat_id]
    
    def _add_sample_appointment(self) -> None:
        """샘플 예약 추가"""
        sample_appointment = AppointmentRequest(
            appointment_id="SAMPLE001",
            patient_name="홍길동",
            phone_number="010-1234-1234",
            preferred_date="12월 12일",
            preferred_time="15:00",
            department="외과",
            consultation_summary="샘플 예약입니다.",
            status=AppointmentStatus.CONFIRMED
        )
        self.appointments.append(sample_appointment)

# 전역 서비스 인스턴스
appointment_service = AppointmentService()
