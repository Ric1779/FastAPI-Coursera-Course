from pathlib import Path
from time import sleep

from asgiref.sync import async_to_sync
from celery import Celery  # type: ignore
from fastapi_mail import (  # type:ignore
    ConnectionConfig,
    FastMail,
    MessageSchema,
    MessageType,
    NameEmail,
)
from redis.asyncio import Redis
from twilio.rest import Client  # type: ignore

from app.config import db_settings, notification_settings
from app.utils import TEMPLATE_DIR

# The API runs on the Windows host, where Redis is published at localhost:6380.
# This worker runs in Docker, where localhost is the worker itself.
_redis_host = (
    "host.docker.internal" if Path("/.dockerenv").exists() else db_settings.REDIS_HOST
)

_celery_broker = Redis(
    host=_redis_host,
    port=db_settings.REDIS_PORT,
    db=9,
)

fast_mail = FastMail(
    ConnectionConfig(
        **notification_settings.model_dump(
            exclude={"TWILIO_SID", "TWILIO_AUTH_TOKEN", "TWILIO_NUMBER"}
        ),
        TEMPLATE_FOLDER=TEMPLATE_DIR,
    ),
)


twilio_client = Client(
    notification_settings.TWILIO_SID, notification_settings.TWILIO_AUTH_TOKEN
)


send_message = async_to_sync(fast_mail.send_message)

app = Celery(
    "api_tasks",
    broker=f"redis://{_redis_host}:{db_settings.REDIS_PORT}/9",
    backend=f"redis://{_redis_host}:{db_settings.REDIS_PORT}/9",
    broker_connection_retry_on_startup=True,
)


def _name_emails(recipients: list[str]) -> list[NameEmail]:
    return [NameEmail(name="", email=address) for address in recipients]


@app.task
def send_mail(
    recipients: list[str],
    subject: str,
    body: str,
):
    send_message(
        MessageSchema(
            recipients=_name_emails(recipients),
            subject=subject,
            body=body,
            subtype=MessageType.plain,
        ),
    )

    return "Message Sent!"


@app.task
def send_email_with_template(
    recipients: list[str],
    subject: str,
    context: dict,
    template_name: str,
):
    send_message(
        message=MessageSchema(
            recipients=_name_emails(recipients),
            subject=subject,
            template_body=context,
            subtype=MessageType.html,
        ),
        template_name=template_name,
    )


@app.task
def send_sms(to: str, body: str):
    twilio_client.messages.create(
        from_=notification_settings.TWILIO_NUMBER,
        to=to,
        body=body,
    )


@app.task
def background_task(name: str, data: dict):
    sleep(5)
    return name
