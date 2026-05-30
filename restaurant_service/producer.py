import json
import pika
from dataclasses import dataclass, asdict
from datetime import datetime

QUEUE_NAME = "dinner_events"

@dataclass
class DinnerEvent:
    amount: float
    card_number: str
    restaurant_code: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def validate(self):
        if self.amount <= 0:
            raise ValueError("El monto debe ser positivo")
        if not self.card_number:
            raise ValueError("El número de tarjeta es necesario")
        if not self.restaurant_code:
            raise ValueError("El código del restaurante es requerido.")
        return True
    
class RabbitMQConnection:
    def __init__(self, host: str, port: int, user: str, password: str, vhost: str = "/"):
        self.credentials = pika.PlainCredentials(user, password)
        self.parameters = pika.ConnectionParameters(host=host, port=port, virtual_host=vhost, credentials=self.credentials)


class DinnerEventPublisher:
    def __init__(self, connection_params: pika.ConnectionParameters, queue_name: str):
        self._params = connection_params
        self._queue_name = queue_name

    def publish(self, event: DinnerEvent) -> bool:
        event.validate()
        connection = pika.BlockingConnection(self._params)

        try:
            channel = connection.channel()
            channel.queue_declare(queue=self._queue_name, durable=True)
            message = json.dumps(asdict(event))
            channel.basic_publish(exchange="", routing_key=self._queue_name, body=message, properties=pika.BasicProperties(delivery_mode=2))
            print(f"Evento publicado: {message}")
            return True
        finally:
            connection.close()

if __name__ == "__main__":
    conn = RabbitMQConnection(host="213.199.42.57", port=5672, user="students", password="Ut3c2026", vhost="/")
    publisher = DinnerEventPublisher(conn.parameters, QUEUE_NAME)

    event = DinnerEvent(
        amount=150.50, card_number="4111111111111111", restaurant_code="REST_123",)
    publisher.publish(event)

