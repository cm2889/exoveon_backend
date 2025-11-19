from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import pytz
from backend.models import BookCalendar


@receiver(post_save, sender=BookCalendar)
def send_booking_email(sender, instance, created, **kwargs):
    if not created:
        return

    start_local = instance.start_datetime
    end_local = instance.end_datetime

    safe_name = (instance.full_name or '').strip()
    safe_summary = (instance.summary or '').strip()
    subject = f"Booking confirmed: {safe_summary}" if safe_summary else "Your booking is confirmed"

    # Build a professional message
    lines = []
    if safe_name:
        lines.append(f"Dear {safe_name},")
    else:
        lines.append("Hello,")

    lines.append("\nWe are pleased to confirm that your appointment has been successfully scheduled. We appreciate the opportunity to connect with you and look forward to our upcoming session.")

    if safe_summary:
        lines.append(f"\nTopic: {safe_summary}")

    if start_local and end_local:
        lines.append(f"Date & Time: {start_local.strftime('%A, %B %d, %Y')} | {start_local.strftime('%H:%M')} - {end_local.strftime('%H:%M %Z')}")
    elif start_local:
        lines.append(f"Date & Time: {start_local.strftime('%A, %B %d, %Y at %H:%M %Z')}")

    if instance.location:
        lines.append(f"Location: {instance.location}")

    if instance.meet_link:
        lines.append(f"Meeting Link: {instance.meet_link}")

    if instance.book_link:
        lines.append(f"Calendar Link: {instance.book_link}")

    lines.append("\nTo ensure we make the most of our time together, please ensure you are ready 5-10 minutes prior to the scheduled start time. If this is a virtual meeting, we recommend checking your internet connection and audio/video settings beforehand to avoid any technical delays.")

    lines.append("\nIf you need to reschedule or cancel this appointment, please kindly notify us at your earliest convenience. This allows us to manage our schedule effectively and accommodate other clients who may be waiting for an appointment.")

    lines.append("\nShould you have any questions or require any specific preparations for this meeting, please do not hesitate to reach out to us. We are here to assist you and ensure a smooth experience.")

    lines.append("\nThank you for choosing OrbitX. We value your trust and look forward to a productive meeting.")
    
    lines.append("\nBest regards,\n\nThe OrbitX Team")

    primary_email = (instance.email or '').strip()
    attendees = []
    if instance.attendees:
        attendees = [e.strip() for e in instance.attendees.split(',') if e and e.strip()]

    recipients = [primary_email] if primary_email else []
    recipients.extend(attendees)

    message = "\n".join(lines)

    seen = set()
    recipient_list = []

    for r in recipients:
        if r and r not in seen:
            seen.add(r)
            recipient_list.append(r)

    if not recipient_list:
        return

    # Choose from email
    from_email = settings.EMAIL_HOST_USER 

    try:
        send_mail(message=message, subject=subject,  from_email=from_email,  recipient_list=recipient_list,  fail_silently=False,)
    except Exception:
        pass