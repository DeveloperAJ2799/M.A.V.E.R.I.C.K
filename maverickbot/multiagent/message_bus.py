"""Message bus for inter-agent communication."""
import asyncio
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import uuid


class MessageType(Enum):
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    STATUS = "status"
    HANDSHAKE = "handshake"


@dataclass
class AgentMessage:
    """Message between agents."""
    id: str
    sender: str
    receiver: Optional[str]  # None = broadcast
    type: MessageType
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None  # For tracking request/response


class MessageBus:
    """Pub/sub message bus for agent communication."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._processor_task = None

    async def start(self):
        """Start the message bus."""
        self._running = True
        self._processor_task = asyncio.create_task(self._process_messages())
        logger.info("MessageBus started")

    async def stop(self):
        """Stop the message bus."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("MessageBus stopped")

    async def publish(self, message: AgentMessage):
        """Publish a message to the bus."""
        await self._message_queue.put(message)

    async def send_to(self, sender: str, receiver: str, message_type: MessageType, payload: Dict[str, Any]) -> AgentMessage:
        """Send a message to a specific agent."""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=sender,
            receiver=receiver,
            type=message_type,
            payload=payload,
        )
        await self.publish(message)
        return message

    async def broadcast(self, sender: str, message_type: MessageType, payload: Dict[str, Any]) -> AgentMessage:
        """Broadcast a message to all subscribers."""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=sender,
            receiver=None,
            type=message_type,
            payload=payload,
        )
        await self.publish(message)
        return message

    def subscribe(self, agent_name: str, callback: Callable):
        """Subscribe an agent to receive messages."""
        if agent_name not in self._subscribers:
            self._subscribers[agent_name] = []
        self._subscribers[agent_name].append(callback)

    def unsubscribe(self, agent_name: str):
        """Unsubscribe an agent from messages."""
        if agent_name in self._subscribers:
            del self._subscribers[agent_name]

    async def _process_messages(self):
        """Process messages from the queue."""
        while self._running:
            try:
                message = await asyncio.wait_for(self._message_queue.get(), timeout=0.1)
                await self._deliver_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def _deliver_message(self, message: AgentMessage):
        """Deliver message to relevant subscribers."""
        if message.receiver:
            callbacks = self._subscribers.get(message.receiver, [])
        else:
            callbacks = []
            for subs in self._subscribers.values():
                callbacks.extend(subs)

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Error delivering message to callback: {e}")