import json
import unittest
from unittest.mock import MagicMock, patch
from dataclasses import asdict

from restaurant_service.producer import DinnerEvent, DinnerEventPublisher, RabbitMQConnection
from rewards_service.consumer import ( RewardCalculator,
RewardsAccountRepository, RewardResult, DinnerEventConsumer,)


class TestDinnerEvent(unittest.TestCase):

    def test_crear_evento_con_timestamp_automatico(self):
        event = DinnerEvent(amount=100.0, card_number="4111", restaurant_code="R01")
        self.assertIsNotNone(event.timestamp)
        self.assertTrue(len(event.timestamp) > 0)

    def test_crear_evento_con_timestamp_manual(self):
        event = DinnerEvent(amount=100.0, card_number="4111", restaurant_code="R01", timestamp="2026-01-01")
        self.assertEqual(event.timestamp, "2026-01-01")

    def test_validar_evento_correcto(self):
        event = DinnerEvent(amount=100.0, card_number="4111", restaurant_code="R01")
        self.assertTrue(event.validate())

    def test_validar_monto_cero_lanza_error(self):
        event = DinnerEvent(amount=0, card_number="4111", restaurant_code="R01")
        with self.assertRaises(ValueError):
            event.validate()

    def test_validar_monto_negativo_lanza_error(self):
        event = DinnerEvent(amount=-10.0, card_number="4111", restaurant_code="R01")
        with self.assertRaises(ValueError):
            event.validate()

    def test_validar_tarjeta_vacia_lanza_error(self):
        event = DinnerEvent(amount=100.0, card_number="", restaurant_code="R01")
        with self.assertRaises(ValueError):
            event.validate()

    def test_validar_restaurante_vacio_lanza_error(self):
        event = DinnerEvent(amount=100.0, card_number="4111", restaurant_code="")
        with self.assertRaises(ValueError):
            event.validate()

    def test_evento_serializable_a_dict(self):
        event = DinnerEvent(amount=75.5, card_number="4333", restaurant_code="R03", timestamp="2026-05-01")
        d = asdict(event)
        self.assertEqual(d["amount"], 75.5)
        self.assertEqual(d["card_number"], "4333")

class TestRewardCalculator(unittest.TestCase):

    def setUp(self):
        self.calculator = RewardCalculator(points_rate=10, cashback_rate=0.05)

    def _evento(self, amount=100.0, card="4111", restaurant="R01"):
        return {"amount": amount, "card_number": card,          "restaurant_code": restaurant, "timestamp": "2026-05-01T10:00:00",}

    def test_calcular_puntos_correctos(self):
        result = self.calculator.calculate(self._evento(amount=100.0))
        self.assertEqual(result.points, 1000)

    def test_calcular_cashback_correcto(self):
        result = self.calculator.calculate(self._evento(amount=200.0))
        self.assertAlmostEqual(result.cashback, 10.0, places=2)

    def test_monto_cero_lanza_error(self):
        with self.assertRaises(ValueError):
            self.calculator.calculate(self._evento(amount=0))

    def test_monto_negativo_lanza_error(self):
        with self.assertRaises(ValueError):
            self.calculator.calculate(self._evento(amount=-50))

    def test_resultado_contiene_tarjeta(self):
        result = self.calculator.calculate(self._evento(card="9999"))
        self.assertEqual(result.card_number, "9999")

    def test_resultado_contiene_restaurante(self):
        result = self.calculator.calculate(self._evento(restaurant="REST_VIP"))
        self.assertEqual(result.restaurant_code, "REST_VIP")

    def test_resultado_es_reward_result(self):
        result = self.calculator.calculate(self._evento())
        self.assertIsInstance(result, RewardResult)

    def test_tasas_personalizadas(self):
        calc = RewardCalculator(points_rate=5, cashback_rate=0.10)
        result = calc.calculate(self._evento(amount=100.0))
        self.assertEqual(result.points, 500)
        self.assertAlmostEqual(result.cashback, 10.0, places=2)

    def test_monto_string_se_convierte(self):
        result = self.calculator.calculate(self._evento(amount="200.0"))
        self.assertEqual(result.points, 2000)


class TestRewardsAccountRepository(unittest.TestCase):

    def _resultado(self, card="4111", points=100, cashback=5.0):
        return RewardResult( card_number=card, restaurant_code="R01", amount=100.0, points=points, cashback=cashback, timestamp="2026-05-01",)

    def test_cuenta_nueva_empieza_en_cero(self):
        repo = RewardsAccountRepository()
        account = repo.get("desconocida")
        self.assertEqual(account["points"], 0)
        self.assertEqual(account["cashback"], 0.0)

    def test_actualizar_crea_cuenta(self):
        repo = RewardsAccountRepository()
        repo.update(self._resultado(card="4111", points=100, cashback=5.0))
        account = repo.get("4111")
        self.assertEqual(account["points"], 100)
        self.assertAlmostEqual(account["cashback"], 5.0)

    def test_actualizar_acumula_puntos(self):
        repo = RewardsAccountRepository()
        repo.update(self._resultado(card="4111", points=100, cashback=5.0))
        repo.update(self._resultado(card="4111", points=200, cashback=10.0))
        self.assertEqual(repo.get("4111")["points"], 300)

    def test_tarjetas_distintas_son_independientes(self):
        repo = RewardsAccountRepository()
        repo.update(self._resultado(card="CARD_A", points=500, cashback=25.0))
        repo.update(self._resultado(card="CARD_B", points=100, cashback=5.0))
        self.assertEqual(repo.get("CARD_A")["points"], 500)
        self.assertEqual(repo.get("CARD_B")["points"], 100)

class TestDinnerEventPublisher(unittest.TestCase):

    def test_publicar_evento_valido_retorna_true(self):
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel

        with patch("restaurant_service.producer.pika.BlockingConnection", return_value=mock_connection):
            publisher = DinnerEventPublisher(MagicMock(), "dinner_events")
            event = DinnerEvent(amount=100.0, card_number="4111", restaurant_code="R01", timestamp="2026-01-01")
            result = publisher.publish(event)

        self.assertTrue(result)

    def test_publicar_llama_queue_declare(self):
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel

        with patch("restaurant_service.producer.pika.BlockingConnection", return_value=mock_connection):
            publisher = DinnerEventPublisher(MagicMock(), "dinner_events")
            event = DinnerEvent(amount=100.0, card_number="4111", restaurant_code="R01", timestamp="2026-01-01")
            publisher.publish(event)

        mock_channel.queue_declare.assert_called_once_with(queue="dinner_events", durable=True)

    def test_publicar_cierra_conexion(self):
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel

        with patch("restaurant_service.producer.pika.BlockingConnection", return_value=mock_connection):
            publisher = DinnerEventPublisher(MagicMock(), "dinner_events")
            event = DinnerEvent(amount=100.0, card_number="4111", restaurant_code="R01", timestamp="2026-01-01")
            publisher.publish(event)

        mock_connection.close.assert_called_once()

    def test_publicar_evento_invalido_lanza_error(self):
        publisher = DinnerEventPublisher(MagicMock(), "dinner_events")
        event = DinnerEvent(amount=-1.0, card_number="4111", restaurant_code="R01")
        with self.assertRaises(ValueError):
            publisher.publish(event)


class TestDinnerEventConsumer(unittest.TestCase):

    def _make_consumer(self):
        calculator = RewardCalculator()
        repository = RewardsAccountRepository()
        consumer = DinnerEventConsumer(MagicMock(), "dinner_events", calculator, repository)
        return consumer, repository

    def _make_ch(self):
        ch = MagicMock()
        method = MagicMock()
        method.delivery_tag = 1
        return ch, method

    def test_mensaje_valido_actualiza_cuenta(self):
        consumer, repo = self._make_consumer()
        ch, method = self._make_ch()
        event = {"amount": 100.0, "card_number": "4111", "restaurant_code": "R01", "timestamp": "2026-01-01"}
        consumer._on_message(ch, method, None, json.dumps(event).encode())
        self.assertGreater(repo.get("4111")["points"], 0)
        ch.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_mensaje_invalido_hace_nack(self):
        consumer, repo = self._make_consumer()
        ch, method = self._make_ch()
        consumer._on_message(ch, method, None, b"NO_ES_JSON")
        ch.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)

    def test_monto_cero_hace_nack(self):
        consumer, repo = self._make_consumer()
        ch, method = self._make_ch()
        event = {"amount": 0, "card_number": "4111", "restaurant_code": "R01", "timestamp": "2026-01-01"}
        consumer._on_message(ch, method, None, json.dumps(event).encode())
        ch.basic_nack.assert_called_once()

    def test_multiples_mensajes_acumulan(self):
        consumer, repo = self._make_consumer()
        ch, method = self._make_ch()
        for amount in [100.0, 200.0, 50.0]:
            event = {"amount": amount, "card_number": "MULTI", "restaurant_code": "R01", "timestamp": "2026-01-01"}
            consumer._on_message(ch, method, None, json.dumps(event).encode())
        self.assertEqual(repo.get("MULTI")["points"], 3500)


class TestDinnerEventConsumerStart(unittest.TestCase):

    def test_start_configura_canal_y_consume(self):
        calculator = RewardCalculator()
        repository = RewardsAccountRepository()
        consumer = DinnerEventConsumer(MagicMock(), "dinner_events", calculator, repository)

        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel

        with patch("rewards_service.consumer.pika.BlockingConnection", return_value=mock_connection):
            consumer.start()

        mock_channel.queue_declare.assert_called_once_with(queue="dinner_events", durable=True)
        mock_channel.basic_qos.assert_called_once_with(prefetch_count=1)
        mock_channel.basic_consume.assert_called_once()
        mock_channel.start_consuming.assert_called_once()


class TestRabbitMQConnection(unittest.TestCase):

    def test_crea_parametros_de_conexion(self):
        import pika
        conn = RabbitMQConnection(host="localhost", port=5672, user="guest", password="guest")
        self.assertIsInstance(conn.parameters, pika.ConnectionParameters)

    def test_vhost_por_defecto(self):
        conn = RabbitMQConnection(host="localhost", port=5672, user="u", password="p")
        self.assertEqual(conn.parameters.virtual_host, "/")

if __name__ == "__main__":
    unittest.main()