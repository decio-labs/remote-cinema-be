from jinja2 import Environment, FileSystemLoader, select_autoescape
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from src.config.settings import setting

from datetime import datetime
import logging  

logger = logging.getLogger(__name__)

class EmailService: 

    def __init__(self):
        self.api_key =  setting.BREVO_API_KEY
        self.from_email = setting.FROMEMAIL
        self.from_name = setting.FROMNAME

    def render_html_template(self, template_name: str, context: dict):
        env = Environment(loader=FileSystemLoader('src/services/helpers/templates'), 
                          autoescape=select_autoescape("html"))
        
        template = env.get_template(f"emails/{template_name}")

        context.update({
            "app_name": setting.APP_NAME,
            "year": datetime.now().year
        })
        return template.render(**context)
    


    async def brevo_email_handler(self, recipient_email: str, subject: str, html_content: str):
        # logic to send email using Brevo API
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = self.api_key
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        sender = {
            "email": self.from_email,
            "name": self.from_name
        }
        recipient = [{
            "email": recipient_email
        }]

        email_body = sib_api_v3_sdk.SendSmtpEmail(
            sender=sender,
            to=recipient,
            subject=subject,
            html_content=html_content
        )

        try:
            api_response = api_instance.send_transac_email(email_body)
            logger.info(f"Email sent successfully to {recipient_email}. Response: {api_response}")
            return True
        except ApiException as e:
            logger.error(f"Exception when sending email to {recipient_email}: {e}")
            return False

    async def send_email(self, recipient_email: str, subject: str, body: str = None, template_name: str = None, extra_data: dict = {}):
        # email sending logic here
        if template_name:
            html_content = self.render_html_template(template_name, extra_data)
        else:
            html_content = body

        return await self.brevo_email_handler(recipient_email, subject, html_content)

    async def send_otp_email(self, name: str, otp_code: str, recipient_email: str):
        await self.send_email(
            recipient_email=recipient_email,
            subject="Your OTP Code",
            template_name="otp.html",
            extra_data={"name": name, "expiry": setting.OTP_Expiry, "otp_code": otp_code, 
                        "email_category": "Security", "email_headline": "Verify your\nidentity", 
                        "support_url": "https://remote-cinema.com/support",}
        )


    async def send_welcome_email(self, name: str, recipient_email: str):
        await self.send_email(
            recipient_email=recipient_email,
            subject="Welcome to Remote Cinema!",
            template_name="welcome.html",
            extra_data={"name": name, "login_url": "https://remote-cinema.com/login"}
        )

    async def send_password_reset_email(self, name: str, reset_code: str, recipient_email: str):
        reset_link = f"{setting.BASE_URL}/api/auth/password-reset?code={reset_code}".strip()
        await self.send_email(
            recipient_email=recipient_email, 
            subject="Password Reset Request",
            template_name="password_reset.html",
            extra_data={"name": name, "reset_link": reset_link,
                        "email_category": "Password Reset", "email_headline": "Change your password", 
                        "support_url": "https://remote-cinema.com/support", "expiry": setting.OTP_Expiry}
        )

    async def send_subscription_renewal_email(self, name: str, recipient_email: str, renewal_date: datetime):
        await self.send_email(
            recipient_email=recipient_email,
            subject="Subscription Renewal Reminder",
            template_name="subscription_renewal.html",
            extra_data={"name": name, "renewal_date": renewal_date.strftime("%B %d, %Y")}
        )

    async def send_subscription_alert_email(self, name: str, recipient_email: str, alert_message: str):
        await self.send_email(
            recipient_email=recipient_email,
            subject="Subscription Alert",
            template_name="subscription_alert.html",
            extra_data={"name": name, "alert_message": alert_message, "trail_period_days": setting.TRIAL_PERIOD_DAYS}
        )