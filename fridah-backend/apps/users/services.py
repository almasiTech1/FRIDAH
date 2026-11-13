import random
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('django')


def generate_otp(user, purpose):
    from .models import OTP
    code = f"{random.randint(100000, 999999)}"
    expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    OTP.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)  # invalidate old
    otp = OTP.objects.create(user=user, code=code, purpose=purpose, expires_at=expires_at)
    send_otp_sms(user.phone_number, code, purpose)
    return otp


def verify_otp(user, code, purpose):
    from .models import OTP
    otp = OTP.objects.filter(user=user, purpose=purpose, is_used=False).order_by('-created_at').first()
    if not otp:
        return False, "No active OTP found. Please request a new one."
    if otp.is_expired():
        return False, "OTP has expired. Please request a new one."
    otp.attempts += 1
    otp.save(update_fields=['attempts'])
    if otp.attempts > 5:
        return False, "Too many attempts. Please request a new OTP."
    if otp.code != code:
        return False, "Invalid OTP code."
    otp.is_used = True
    otp.save(update_fields=['is_used'])
    return True, "OTP verified successfully."


def send_otp_sms(phone_number, code, purpose):
    message = f"Your FRIDAH verification code is {code}. It expires in {settings.OTP_EXPIRY_MINUTES} minutes. Do not share this code."
    send_sms(phone_number, message)


def send_sms(phone_number, message):
    """Send SMS via Africa's Talking. Falls back to logging in DEBUG/sandbox without keys."""
    if settings.DEBUG and not settings.AT_API_KEY:
        logger.info("[SMS:DEV] To %s: %s", phone_number, message)
        return True
    try:
        import africastalking
        africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
        sms = africastalking.SMS
        response = sms.send(message, [phone_number], sender_id=settings.AT_SENDER_ID or None)
        logger.info("SMS sent to %s: %s", phone_number, response)
        return True
    except Exception as e:
        logger.error("Failed to send SMS to %s: %s", phone_number, e)
        return False
