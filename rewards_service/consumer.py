import json
import sys
import os
import pika
from dataclasses import dataclass

QUEUE_NAME = "dinner_events"
POINTS_RATE = 10
CASHBACK_RATE = 0.05

@dataclass
class RewardResult:
    amount: float
    card_number: str
    restaurant_code: str
    points: int
    cashback: float
    timestamp: str

class  RewardCalculator:
    def __init__(self, points_rate: float= POINTS_RATE, cashback_rate: float= CASHBACK_RATE):
        self._points_rate= points_rate
        self._cashback_rate= cashback_rate

    def calculate(self, event: dict) -> RewardResult:
        amount= float(event.get("amount", 0))
        if amount <= 0:
            raise ValueError("El monto debe ser positivo")
        return RewardResult( card_number=event["card_number"], restaurant_code=event["restaurant_code"], amount=amount, points=int(amount * self._points_rate), cashback=round(amount * self._cashback_rate, 2),timestamp=event.get("timestamp", ""),
        )
    
class RewardsAccountRepository:
    def __init__(self): self._accounts: dict = {}

    def update(self, result: RewardResult) -> None:
        card= result.card_number
        if card not in self._accounts: self._accounts[card] = {"points": 0, "cashback": 0.0}
        self._accounts[card]["points"]+= result.points
        self._accounts[card]["cashback"]+= result.cashback
        print(f"[✓] Cuenta actualizada para {card} | " f"+{result.points} puntos | " f"+{result.cashback} cashback | " f"Total: {self._accounts[card]}")

    def get(self, card_number: str) -> dict: return self._accounts.get(card_number, {"points": 0, "cashback": 0.0})


class DinnerEventConsumer:
    def __init__(self, connection_params: pika.ConnectionParameters, queue_name: str, calculator: RewardCalculator, repository: RewardsAccountRepository,):
        self._params= connection_params
        self._queue_name= queue_name
        self._calculator= calculator
        self._repository= repository

    def _on_message(self, ch, method, properties, body):
        try:
            event= json.loads(body.decode())
            result= self._calculator.calculate(event)
            self._repository.update(result)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except (ValueError, KeyError) as e:
            print(f"[!] Mensaje inválido, descartado: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start(self):
        connection= pika.BlockingConnection(self._params)
        channel= connection.channel()
        channel.queue_declare(queue=self._queue_name, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=self._queue_name,
            on_message_callback=self._on_message
        )
        print(f"[*] Esperando mensajes en '{self._queue_name}'. CTRL+C para salir.")
        channel.start_consuming()

if __name__ == "__main__":
    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER", "students"),
        os.getenv("RABBITMQ_PASSWORD", "Ut3c2026")
    )
    params = pika.ConnectionParameters(
        os.getenv("RABBITMQ_HOST", "213.199.42.57"),
        int(os.getenv("RABBITMQ_PORT", "5672")),
        os.getenv("RABBITMQ_VHOST", "/"),
        credentials
    )

    consumer = DinnerEventConsumer(
        connection_params=params,
        queue_name=QUEUE_NAME,
        calculator=RewardCalculator(),
        repository=RewardsAccountRepository(),
    )
    try:
        consumer.start()
    except KeyboardInterrupt:
        print("\n[*] Consumer detenido.")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)