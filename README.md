# Documento de Arquitectura - Sistema de Recompesas por Cenas

**Curso** Ingeniería de Software

**Reto** Buen diseño: Cohesión y Acoplamiento

---
## 1. Descripción General

El sistema implementa un programa de fidelización de restaurantes. Cada vez que un cliente realiza una cena en un restaurante afiliado, el sistema registra la transacción, la publica como evento en un broker de mensajería (RabbitMQ), y un microservicio independiente calcula y acumula los puntos o cashback del cliente.

---

## 2. Patrón Arquitectónico Utilizado

Para nuestro problema el más adecuado es Event-Driven Architecture (EDA) junto con Clean Architecture. Debido a que el problema:

- EDA
1. Tiene un flujo asíncroníco natural ya que el restaurante registra la cena y no necesita esperar a que se calcule los puntos para seguir atendiendo a otros clientes.

2. Se tendría un volumen de transacciones muy alto por naturaleza. con este patrón logramos que el broker absorba todos los picos y el consumidor procesa a su propio ritmo sin colapsar.

3. El productor y el consumidor tienen tienen responsabilidades completamente distintas y no deberían reconocerse, el restaurante solo sabe que ocurrió una cena.

- Clean Architecture

1. EDA lo que va a resolver es el cómo se comunican entre sí los servicios. Pero dentro de cada servicio se necesita organizar el código.

2. La lógica de calcular los puntos no sabe nada de RabbitMQ, lo que permite hacer pruebas sin el broker real.

3. Podemos hacer pruebas sin necesidad de la conexión real al servidor de la univerdidad para funcionar.

---

## 3. Diagrama de Casos de Uso

![imagen](./img/image1.png)

---
