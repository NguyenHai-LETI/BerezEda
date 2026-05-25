import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from apps.core.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

logger = logging.getLogger(__name__)


class EmailService:
    def _send(self, to: str, subject: str, html_body: str) -> None:
        if not SMTP_USER or not SMTP_PASSWORD:
            logger.warning(f"[EMAIL STUB] To: {to} | Subject: {subject}")
            return
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM
            msg["To"] = to
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, to, msg.as_string())
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")

    def send_welcome(self, to: str, name: str) -> None:
        html = f"""
        <html><body>
        <h2>Добро пожаловать в БережЕда, {name}!</h2>
        <p>Ваш аккаунт успешно создан. Теперь вы можете покупать свежие продукты по сниженным ценам.</p>
        <p>Вместе мы сокращаем пищевые отходы!</p>
        </body></html>
        """
        self._send(to, "Добро пожаловать в БережЕда!", html)

    def send_order_confirmation(self, to: str, order_data: dict) -> None:
        html = f"""
        <html><body>
        <h2>Заказ подтверждён!</h2>
        <p><b>Номер заказа:</b> {order_data.get("order_id", "")}</p>
        <p><b>Сумма:</b> {order_data.get("amount", 0)} ₽</p>
        <p><b>Ячейка:</b> {order_data.get("locker_name", "")} — Бокс №{order_data.get("unit_number", "")}</p>
        <p><b>Код доступа:</b> <strong style="font-size:24px;">{order_data.get("access_code", "")}</strong></p>
        <p><b>Забрать до:</b> {order_data.get("pickup_deadline", "")}</p>
        <p>Спасибо за покупку и за вклад в сокращение пищевых отходов!</p>
        </body></html>
        """
        self._send(to, "Ваш заказ в БережЕда подтверждён", html)

    def send_password_reset(self, to: str, code: str) -> None:
        html = f"""
        <html><body>
        <h2>Сброс пароля</h2>
        <p>Ваш код подтверждения: <strong style="font-size:28px;">{code}</strong></p>
        <p>Код действителен 15 минут. Если вы не запрашивали сброс пароля — проигнорируйте это письмо.</p>
        </body></html>
        """
        self._send(to, "Сброс пароля — БережЕда", html)

    def send_combo_available(self, to: str, combo_data: dict) -> None:
        html = f"""
        <html><body>
        <h2>Новый набор доступен!</h2>
        <p>Магазин <b>{combo_data.get("shop_name", "")}</b> выставил новый набор:</p>
        <p><b>{combo_data.get("title", "")}</b></p>
        <p>Цена: <b>{combo_data.get("sale_price", 0)} ₽</b> (скидка {combo_data.get("discount_rate", 0)}%)</p>
        <p>Ячейка: {combo_data.get("locker_name", "")}</p>
        <p>Успевайте забрать!</p>
        </body></html>
        """
        self._send(to, f"Новый набор от {combo_data.get('shop_name', '')}", html)


email_service = EmailService()
