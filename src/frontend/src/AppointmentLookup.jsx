import { useState } from 'react';
import './App.css';

const AppointmentLookup = () => {
    const [appointmentId, setAppointmentId] = useState('');
    const [appointment, setAppointment] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleLookup = async (e) => {
        e.preventDefault();
        if (!appointmentId.trim()) {
            setError('예약번호를 입력해주세요.');
            return;
        }

        setLoading(true);
        setError('');
        setAppointment(null);

        try {
            const response = await fetch(`/appointments/${appointmentId.trim()}`);
            if (response.ok) {
                const data = await response.json();
                setAppointment(data);
            } else if (response.status === 404) {
                setError('예약을 찾을 수 없습니다. 예약번호를 다시 확인해주세요.');
            } else {
                setError('예약 조회 중 오류가 발생했습니다.');
            }
        } catch (err) {
            setError('네트워크 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateStr) => {
        // "10월 27일" 형태를 그대로 표시
        return dateStr;
    };

    const formatTime = (timeStr) => {
        // "15:00" 형태를 "오후 3시"로 변환
        const [hour, minute] = timeStr.split(':');
        const hourNum = parseInt(hour);
        if (hourNum < 12) {
            return `오전 ${hourNum}시`;
        } else if (hourNum === 12) {
            return `오후 12시`;
        } else {
            return `오후 ${hourNum - 12}시`;
        }
    };

    return (
        <div className="appointment-lookup">
            <div className="lookup-container">
                <h2>예약 조회</h2>
                <p className="lookup-description">
                    예약번호를 입력하시면 예약 정보를 확인할 수 있습니다.
                </p>
                
                <form onSubmit={handleLookup} className="lookup-form">
                    <div className="input-group">
                        <label htmlFor="appointmentId">예약번호</label>
                        <input
                            type="text"
                            id="appointmentId"
                            value={appointmentId}
                            onChange={(e) => setAppointmentId(e.target.value)}
                            placeholder="예: APT000001"
                            className="appointment-input"
                        />
                    </div>
                    <button 
                        type="submit" 
                        className="lookup-button"
                        disabled={loading}
                    >
                        {loading ? '조회 중...' : '예약 조회'}
                    </button>
                </form>

                {error && (
                    <div className="error-message">
                        {error}
                    </div>
                )}

                {appointment && (
                    <div className="appointment-details">
                        <h3>예약 정보</h3>
                        <div className="appointment-info">
                            <div className="info-row">
                                <span className="label">예약번호:</span>
                                <span className="value">{appointment.appointment_id}</span>
                            </div>
                            <div className="info-row">
                                <span className="label">환자명:</span>
                                <span className="value">{appointment.patient_name}</span>
                            </div>
                            <div className="info-row">
                                <span className="label">진료과:</span>
                                <span className="value">{appointment.department}</span>
                            </div>
                            <div className="info-row">
                                <span className="label">예약일시:</span>
                                <span className="value">
                                    {formatDate(appointment.appointment_date)} {formatTime(appointment.appointment_time)}
                                </span>
                            </div>
                            <div className="info-row">
                                <span className="label">상태:</span>
                                <span className={`status ${appointment.status}`}>
                                    {appointment.status === 'confirmed' ? '확정' : 
                                     appointment.status === 'pending' ? '대기' :
                                     appointment.status === 'cancelled' ? '취소' : '완료'}
                                </span>
                            </div>
                        </div>
                        
                        <div className="appointment-actions">
                            <button 
                                className="action-button cancel-button"
                                onClick={() => {
                                    if (window.confirm('예약을 취소하시겠습니까?')) {
                                        // 취소 로직 구현
                                        alert('예약 취소 기능은 준비 중입니다.');
                                    }
                                }}
                            >
                                예약 취소
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AppointmentLookup;
