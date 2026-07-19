"""
Brevo Email Service for SwimTrackPro
-----------------------------------
This module provides a reusable function to send email notifications
using the Brevo transactional email API.

Environment Variables Required:
- BREVO_API_KEY
- BREVO_SENDER_EMAIL
- BREVO_SENDER_NAME
- ADMIN_ALERT_EMAIL
"""

import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException   
from config import (
    BREVO_API_KEY,
    BREVO_SENDER_EMAIL,
    BREVO_SENDER_NAME,
    ADMIN_ALERT_EMAIL,
    )



def send_email(subject, html_content, to_email=None, to_name="Admin"):
    """
    Send an email using Brevo.

    Parameters:
        subject (str): Email subject.
        html_content (str): HTML body content.
        to_email (str, optional): Recipient email address.
            If not provided, ADMIN_ALERT_EMAIL will be used.
        to_name (str, optional): Recipient display name.

    Returns:
        bool: True if email was sent successfully, False otherwise.
    """
    # api_key = os.getenv("BREVO_API_KEY")
    # sender_email = os.getenv("BREVO_SENDER_EMAIL")
    # sender_name = os.getenv("BREVO_SENDER_NAME", "SwimTrackPro")
    # default_recipient = os.getenv("ADMIN_ALERT_EMAIL")
    api_key = BREVO_API_KEY
    sender_email = BREVO_SENDER_EMAIL
    sender_name = BREVO_SENDER_NAME
    default_recipient = ADMIN_ALERT_EMAIL

    # print("DEBUG API KEY:", bool(api_key))
    # print("DEBUG SENDER:", sender_email)
    # print("DEBUG ADMIN:", default_recipient)

    # Validate required configuration.
    if not api_key:
        print("Brevo email skipped: BREVO_API_KEY is not configured.")
        return False

    if not sender_email:
        print("Brevo email skipped: BREVO_SENDER_EMAIL is not configured.")
        return False

    recipient_email = to_email or default_recipient
    if not recipient_email:
        print("Brevo email skipped: No recipient email configured.")
        return False

    try:
        # Configure Brevo API client.
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = api_key

        api_client = sib_api_v3_sdk.ApiClient(configuration)
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

        # Construct email payload.
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[
                {
                    "email": recipient_email,
                    "name": to_name,
                }
            ],
            sender={
                "email": sender_email,
                "name": sender_name,
            },
            subject=subject,
            html_content=html_content,
        )

        # Send the email.
        api_instance.send_transac_email(send_smtp_email)
        print(f"Brevo email sent successfully to {recipient_email}.")
        return True

    except ApiException as exc:
        print(f"Brevo API error: {exc}")
        return False

    except Exception as exc:
        print(f"Unexpected email error: {exc}")
        return False


# --- Booking Confirmation Email to Swimmer ---
def send_booking_confirmation_email(booking):
    """Send booking confirmation email to swimmer."""

    try:
        email = (booking.get('email') or '').strip()

        if not email:
            return

        subject = f"🏊 Booking Confirmed - {booking.get('booking_code', 'SwimTrackPro')}"

        html_content = f"""
        <h2>🏊 Booking Confirmation</h2>

        <p>Hello {booking.get('owner_name', 'Swimmer')},</p>

        <p>Your booking for <strong>{booking.get('student', '')}</strong> has been successfully created.</p>

        <table border="0" cellpadding="4" cellspacing="0">
            <tr><td><strong>Booking ID</strong></td><td>: {booking.get('booking_code', '')}</td></tr>
            <tr><td><strong>Package</strong></td><td>: {booking.get('package', '')}</td></tr>
            <tr><td><strong>Start Date</strong></td><td>: {booking.get('start_date', '')}</td></tr>
            <tr><td><strong>Time</strong></td><td>: {booking.get('time', '')}</td></tr>
            <tr><td><strong>Fee</strong></td><td>: ₹{booking.get('fee', 0)}</td></tr>
            <tr><td><strong>Payment</strong></td><td>: {booking.get('payment_request', 'Not Paid')}</td></tr>
        </table>

        <br>

        <p>
        Track your booking:<br>
        <a href="https://swimtrackpro.onrender.com">https://swimtrackpro.onrender.com</a>
        </p>

        <p>Thank you for choosing SwimTrackPro 🏊</p>
        """

        send_email(
            subject=subject,
            html_content=html_content,
            to_email=email,
            to_name=booking.get('owner_name', 'Swimmer')
        )

    except Exception as exc:
        print(f"Booking confirmation email failed: {exc}")


# --- Payment Reminder Email to Swimmer ---
def send_payment_reminder_email(booking):
    """Send payment reminder email when package is nearing completion."""
    try:
        email = (booking.get('email') or '').strip()

        if not email:
            return

        subject = f"💰 Payment Reminder - {booking.get('booking_code', 'SwimTrackPro')}"

        html_content = f"""
        <h2>💰 Payment Reminder</h2>

        <p>Hello {booking.get('owner_name', 'Swimmer')},</p>

        <p>Your swimming package is nearing completion and payment is still pending.</p>

        <table border="0" cellpadding="4" cellspacing="0">
            <tr><td><strong>Booking ID</strong></td><td>: {booking.get('booking_code', '')}</td></tr>
            <tr><td><strong>Swimmer</strong></td><td>: {booking.get('student', '')}</td></tr>
            <tr><td><strong>Package</strong></td><td>: {booking.get('package', '')}</td></tr>
            <tr><td><strong>Remaining Sessions</strong></td><td>: {booking.get('remaining_classes', 0)}</td></tr>
            <tr><td><strong>Amount Due</strong></td><td>: ₹{booking.get('fee', 0)}</td></tr>
        </table>

        <br>

        <p>Please complete the payment and update your payment status in SwimTrackPro.</p>

        <p>
        Track your booking:<br>
        <a href="https://swimtrackpro.onrender.com">https://swimtrackpro.onrender.com</a>
        </p>

        <p>Thank you for choosing SwimTrackPro 🏊</p>
        """

        send_email(
            subject=subject,
            html_content=html_content,
            to_email=email,
            to_name=booking.get('owner_name', 'Swimmer')
        )

    except Exception as exc:
        print(f"Payment reminder email failed: {exc}")


# --- Package Completion Email to Swimmer ---
def send_package_completion_email(booking):
    """Send package completion email when all sessions are completed."""
    try:
        email = (booking.get('email') or '').strip()

        if not email:
            return

        subject = f"🎉 Package Completed - {booking.get('booking_code', 'SwimTrackPro')}"

        html_content = f"""
        <h2>🎉 Package Completed</h2>

        <p>Hello {booking.get('owner_name', 'Swimmer')},</p>

        <p>Congratulations! Your swimming package has been successfully completed.</p>

        <table border="0" cellpadding="4" cellspacing="0">
            <tr><td><strong>Booking ID</strong></td><td>: {booking.get('booking_code', '')}</td></tr>
            <tr><td><strong>Swimmer</strong></td><td>: {booking.get('student', '')}</td></tr>
            <tr><td><strong>Package</strong></td><td>: {booking.get('package', '')}</td></tr>
            <tr><td><strong>Sessions Completed</strong></td><td>: {booking.get('total_classes', 0)}/{booking.get('total_classes', 0)}</td></tr>
        </table>

        <br>

        <p>Ready for the next level?</p>

        <p>
        Book your next package:<br>
        <a href="https://swimtrackpro.onrender.com">https://swimtrackpro.onrender.com</a>
        </p>

        <p>Thank you for choosing SwimTrackPro 🏊</p>
        """

        send_email(
            subject=subject,
            html_content=html_content,
            to_email=email,
            to_name=booking.get('owner_name', 'Swimmer')
        )

    except Exception as exc:
        print(f"Package completion email failed: {exc}")
