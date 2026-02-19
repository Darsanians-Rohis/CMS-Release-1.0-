import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from typing import List, Dict
import json
import logging
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Support two providers: Resend (preferred) and Mailjet (fallback)
        self.resend_api_key = os.environ.get('RESEND_API_KEY')
        self.mailjet_api_key = os.environ.get('MAILJET_API_KEY')
        self.mailjet_api_secret = os.environ.get('MAILJET_API_SECRET')
        self.sender_email = os.environ.get('SENDER_EMAIL', 'rohisdarsa@gmail.com')
        self.sender_name = os.environ.get('SENDER_NAME', 'Rohis Attendance System')

        if self.resend_api_key:
            self.provider = 'resend'
            self.api_url = 'https://api.resend.com/emails'
            logger.info('EmailService: using Resend provider')
        elif self.mailjet_api_key and self.mailjet_api_secret:
            self.provider = 'mailjet'
            self.api_url = 'https://api.mailjet.com/v3.1/send'
            logger.info('EmailService: using Mailjet provider')
        else:
            raise ValueError(
                "No email provider configured. Set RESEND_API_KEY or MAILJET_API_KEY and MAILJET_API_SECRET"
            )
    
    def send_piket_reminder(
        self, 
        recipients: List[str], 
        day_name: str,
        date_str: str,
        additional_info: str = ""
    ) -> Dict[str, any]:
        """
        Send piket reminder email to a list of recipients using Mailjet API.
        
        Args:
            recipients: List of email addresses
            day_name: Name of the day (e.g., "Monday")
            date_str: Formatted date string (e.g., "05 February 2026")
            additional_info: Optional additional message
            
        Returns:
            Dict with 'success' (bool), 'message' (str), 'failed_emails' (list)
        """
        if not recipients:
            return {
                'success': False,
                'message': 'No recipients provided',
                'failed_emails': []
            }
        
        # Email content
        subject = f"Reminder: Jadwal Piket {day_name}"
        
        html_body = self._generate_email_html(
            day_name=day_name,
            date_str=date_str,
            additional_info=additional_info
        )
        
        text_body = self._generate_email_text(
            day_name=day_name,
            date_str=date_str,
            additional_info=additional_info
        )
        
        # Send emails using the configured provider
        failed_emails = []
        successful_count = 0

        for recipient in recipients:
            try:
                if self.provider == 'mailjet':
                    # Prepare email payload for Mailjet
                    payload = {
                        "Messages": [
                            {
                                "From": {
                                    "Email": self.sender_email,
                                    "Name": self.sender_name
                                },
                                "To": [
                                    {
                                        "Email": recipient,
                                        "Name": recipient.split('@')[0].replace('.', ' ').title()
                                    }
                                ],
                                "Subject": subject,
                                "TextPart": text_body,
                                "HTMLPart": html_body
                            }
                        ]
                    }

                    response = requests.post(
                        self.api_url,
                        auth=HTTPBasicAuth(self.mailjet_api_key, self.mailjet_api_secret),
                        headers={"Content-Type": "application/json"},
                        json=payload,
                        timeout=10
                    )

                    if response.status_code == 200:
                        result = response.json()
                        # Mailjet returns an array of messages; check delivered status
                        if result.get('Messages') and result['Messages'][0].get('Status') == 'success':
                            successful_count += 1
                        else:
                            logger.warning('Mailjet failed for %s: %s', recipient, result)
                            failed_emails.append(recipient)
                    elif response.status_code == 401:
                        # Authentication issue - return clear guidance
                        msg = (
                            'Authentication failed (401) when sending email via Mailjet. '
                            'Check MAILJET_API_KEY and MAILJET_API_SECRET environment variables.'
                        )
                        logger.error(msg + ' Response: %s', response.text)
                        return {'success': False, 'message': msg, 'failed_emails': recipients}
                    else:
                        logger.error('Mailjet HTTP %s: %s', response.status_code, response.text)
                        failed_emails.append(recipient)

                elif self.provider == 'resend':
                    # Resend API expects Authorization: Bearer <key>
                    payload = {
                        'from': { 'email': self.sender_email, 'name': self.sender_name },
                        'to': [ { 'email': recipient } ],
                        'subject': subject,
                        'html': html_body,
                        'text': text_body
                    }

                    response = requests.post(
                        self.api_url,
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {self.resend_api_key}'
                        },
                        json=payload,
                        timeout=10
                    )

                    if response.status_code in (200, 202):
                        successful_count += 1
                    elif response.status_code == 401:
                        msg = (
                            'Authentication failed (401) when sending email via Resend. '
                            'Check RESEND_API_KEY environment variable.'
                        )
                        logger.error(msg + ' Response: %s', response.text)
                        return {'success': False, 'message': msg, 'failed_emails': recipients}
                    else:
                        logger.error('Resend HTTP %s: %s', response.status_code, response.text)
                        failed_emails.append(recipient)

            except Exception as e:
                logger.exception('Error sending email to %s: %s', recipient, e)
                failed_emails.append(recipient)
        
        # Return results
        if failed_emails:
            return {
                'success': True,
                'message': f'Sent {successful_count}/{len(recipients)} emails. Some failed.',
                'failed_emails': failed_emails
            }
        else:
            return {
                'success': True,
                'message': f'Successfully sent {successful_count} emails',
                'failed_emails': []
            }
    
    def _generate_email_html(self, day_name: str, date_str: str, additional_info: str) -> str:
        """Generate HTML email body"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Jadwal Piket Reminder</title>
        </head>

        <body style="margin:0;padding:0;background-color:#f8fafc;font-family:Arial,Helvetica,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f8fafc;padding:20px 0;">
        <tr>
        <td align="center">

        <table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:10px;overflow:hidden;">
            
            <!-- Header -->
            <tr>
                <td align="center" style="background:#059669;color:white;padding:28px;">
                    <div style="font-size:26px;font-weight:bold;margin-bottom:6px;">
                        Reminder
                    </div>
                    <div style="font-size:15px;opacity:0.9;">
                        Rohis Attendance System
                    </div>
                </td>
            </tr>

            <!-- Date Badge -->
            <tr>
                <td align="center" style="padding:30px 20px 10px 20px;">
                    <div style="display:inline-block;background:#dcfce7;color:#065f46;
                                padding:10px 18px;border-radius:6px;
                                font-weight:bold;font-size:16px;">
                        {day_name} • {date_str}
                    </div>
                </td>
            </tr>

            <!-- Greeting -->
            <tr>
                <td style="padding:10px 30px;color:#1e293b;font-size:16px;line-height:1.6;">
                    Assalamu'alaikum,
                </td>
            </tr>

            <!-- Message -->
            <tr>
                <td style="padding:0 30px 10px 30px;color:#1e293b;font-size:16px;line-height:1.6;">
                    This is a reminder that <strong>you are scheduled for piket duty today ({day_name})</strong>.
                </td>
            </tr>

            <!-- Responsibilities -->
            <tr>
                <td style="padding:20px 30px;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;border-left:4px solid #059669;border-radius:6px;">
                        <tr>
                            <td style="padding:18px;">
                                <div style="color:#059669;font-weight:bold;margin-bottom:10px;">
                                    📋 Your Responsibilities
                                </div>
                                <ul style="margin:0;padding-left:18px;color:#475569;line-height:1.7;font-size:15px;">
                                    <li>Arrive 10 minutes before the scheduled time</li>
                                    <li>Clean the designated area thoroughly</li>
                                    <li>Remind members when prayer time is approaching</li>
                                    <li>Remind members to tidy and return the Qur'an after use</li>
                                    <li>Remind members to bring their wirid/dua book</li>
                                    <li>Maintain order inside the mosque (especially during adzan and dzikir)</li>
                                    <li>Ensure bags are placed near the south-side window</li>
                                    <li>Remind members to wear the mosque uniform (weekday prayers)</li>
                                    <li>Report any issues to PIC or admin</li>
                                </ul>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>

            {f'''
            <tr>
                <td style="padding:0 30px 20px 30px;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="background:#fef3c7;border-left:4px solid #f59e0b;border-radius:6px;">
                        <tr>
                            <td style="padding:16px;color:#92400e;font-size:15px;line-height:1.6;">
                                <strong>📢 Additional Info</strong><br>
                                {additional_info}
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            ''' if additional_info else ""}

            <!-- Closing -->
            <tr>
                <td style="padding:10px 30px 25px 30px;color:#1e293b;font-size:16px;">
                    JazakAllah khair for your cooperation 🙏
                </td>
            </tr>

            <!-- Footer -->
            <tr>
                <td style="border-top:1px solid #e2e8f0;padding:20px 30px;
                        color:#64748b;font-size:13px;text-align:center;">
                    <em>This is an automated reminder from Rohis Attendance System.</em>
                    <div style="margin-top:6px;">Rohis Management System — GDA Jogja</div>
                </td>
            </tr>

        </table>

        </td>
        </tr>
        </table>
        </body>
        </html>
        """
        
    def _generate_email_text(self, day_name: str, date_str: str, additional_info: str) -> str:
        """Generate plain text email body (fallback)"""
        text = f"""
            JADWAL PIKET REMINDER
            Rohis Attendance System

            {day_name} • {date_str}

            Assalamu'alaikum,

            This is a friendly reminder that you are scheduled for piket duty today ({day_name}).

            YOUR RESPONSIBILITIES:
            - Arrive 10 minutes before the scheduled time
            - Clean the designated area thoroughly
            - Ensure all tasks are completed before leaving
            - Report any issues to your PIC or admin
            """
        
        if additional_info:
            text += f"\nADDITIONAL INFO:\n{additional_info}\n"
        
        text += """
            JazakAllah khair for your cooperation!

            ---
            This is an automated reminder from Rohis Attendance System.
            If you have any questions, please contact your admin.

            Rohis Management System
            GDA Jogja
            """
        return text.strip()
    # Singleton instance
_email_service = None

def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

if __name__ == "__main__":
    service = get_email_service()

    result = service.send_piket_reminder(
        recipients=["irfan.ansari@gdajogja.sch.id"],
        day_name="Monday",
        date_str="08 February 2026",
        additional_info="Testing email service."
    )

    print(result)