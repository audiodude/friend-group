"""Telegram bot management — one bot per friend, all in one process."""

import asyncio
import logging
import time

import anthropic
from telegram import Bot, Update
from telegram.error import TelegramError

from .config import (
    load_config, load_friend_config, get_friend_names,
)
from .chat_history import ChatMessage, append_message, load_messages, maybe_compact
from .schedule import should_respond, get_availability
from .brain import think_and_respond, maybe_initiate

logger = logging.getLogger(__name__)


class FriendBot:
    """A single friend bot instance."""

    def __init__(self, name: str, config: dict, global_config: dict,
                 claude: anthropic.AsyncAnthropic):
        self.name = name
        self.config = config
        self.global_config = global_config
        self.claude = claude
        self.bot = Bot(token=config["telegram_token"])
        self.group_chat_id = int(global_config["group_chat_id"])
        self._bot_user_id: int | None = None
        self._bot_username: str | None = None

    async def init(self):
        """Initialize bot and get its user info."""
        me = await self.bot.get_me()
        self._bot_user_id = me.id
        self._bot_username = me.username
        logger.info(f"Initialized {self.name} as @{self._bot_username} (id: {self._bot_user_id})")

    @property
    def user_id(self) -> int:
        return self._bot_user_id

    @property
    def username(self) -> str:
        return self._bot_username

    async def send_message(self, text: str, reply_to_message_id: int | None = None):
        """Send a message to the group chat."""
        kwargs = {
            "chat_id": self.group_chat_id,
            "text": text,
        }
        if reply_to_message_id:
            kwargs["reply_to_message_id"] = reply_to_message_id
        try:
            result = await self.bot.send_message(**kwargs)
            return result
        except TelegramError as e:
            logger.error(f"{self.name} failed to send message: {e}")
            return None


class FriendGroup:
    """Manages the group of friend bots."""

    def __init__(self):
        self.global_config = load_config()
        self.claude = anthropic.AsyncAnthropic(
            api_key=self.global_config["anthropic_api_key"]
        )
        self.model = self.global_config.get("model", "claude-sonnet-4-6-20250514")
        self.bots: dict[str, FriendBot] = {}
        self._bot_user_ids: set[int] = set()
        self._last_update_id: int = 0
        self._processing_lock = asyncio.Lock()

    async def setup(self):
        """Initialize all friend bots."""
        friend_names = get_friend_names()
        logger.info(f"Setting up {len(friend_names)} friends: {friend_names}")

        for name in friend_names:
            config = load_friend_config(name)
            if not config.get("telegram_token"):
                logger.warning(f"Skipping {name} — no telegram token configured")
                continue
            bot = FriendBot(name, config, self.global_config, self.claude)
            await bot.init()
            self.bots[name] = bot
            self._bot_user_ids.add(bot.user_id)

        logger.info(f"Ready with {len(self.bots)} friends")

    async def poll_and_respond(self):
        """Main loop: poll for messages + periodically let bots initiate."""
        poll_bot = next(iter(self.bots.values()))
        poll_interval = self.global_config.get("poll_interval", 2)

        logger.info("Starting message polling...")

        # Run polling and initiation concurrently
        await asyncio.gather(
            self._poll_loop(poll_bot, poll_interval),
            self._initiation_loop(),
        )

    async def _poll_loop(self, poll_bot, poll_interval):
        """Poll Telegram for new messages."""
        while True:
            try:
                updates = await poll_bot.bot.get_updates(
                    offset=self._last_update_id + 1,
                    timeout=30,
                    allowed_updates=["message"],
                )

                for update in updates:
                    self._last_update_id = update.update_id
                    if update.message and update.message.chat.id == poll_bot.group_chat_id:
                        await self._handle_message(update.message)

            except TelegramError as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.exception(f"Unexpected error in poll loop: {e}")
                await asyncio.sleep(5)

            await asyncio.sleep(poll_interval)

    async def _initiation_loop(self):
        """Periodically give bots a chance to start conversations."""
        import random

        # Wait a bit before first check so polling can start
        await asyncio.sleep(60)

        while True:
            # Check every 15-45 minutes (randomized to feel natural)
            wait = random.randint(15 * 60, 45 * 60)
            await asyncio.sleep(wait)

            try:
                # How long has the chat been quiet?
                messages = load_messages(limit=1)
                if messages:
                    silence_minutes = int((time.time() - messages[-1].timestamp) / 60)
                else:
                    silence_minutes = 999

                # Only try to initiate if chat has been quiet for at least 10 min
                if silence_minutes < 10:
                    continue

                # Pick one random bot to consider initiating
                name = random.choice(list(self.bots.keys()))
                bot = self.bots[name]
                friend_config = load_friend_config(name)
                availability = get_availability(friend_config)

                if not availability["awake"]:
                    continue

                # Chattier friends are more likely to initiate
                chattiness = friend_config.get("chattiness", 0.5)
                if random.random() > chattiness:
                    continue

                logger.info(f"{name} considering starting a conversation (quiet for {silence_minutes}min)...")

                result = await maybe_initiate(
                    client=self.claude,
                    model=self.model,
                    friend_name=name,
                    friend_config=friend_config,
                    silence_minutes=silence_minutes,
                )

                if result and result.get("message"):
                    # Random typing delay
                    await asyncio.sleep(random.randint(2, 10))

                    sent = await bot.send_message(result["message"])
                    if sent:
                        msg = ChatMessage(
                            timestamp=time.time(),
                            sender=name,
                            text=result["message"],
                            message_id=sent.message_id,
                        )
                        append_message(msg)
                        logger.info(f"{name} initiated: {result['message'][:50]}...")

            except Exception as e:
                logger.exception(f"Error in initiation loop: {e}")

    async def _handle_message(self, message):
        """Process an incoming message and let friends respond."""
        if not message.text:
            return

        sender_id = message.from_user.id
        sender_name = message.from_user.first_name or message.from_user.username

        # Figure out if this is from Travis or from one of the bots
        is_bot_message = sender_id in self._bot_user_ids
        if is_bot_message:
            # Find which bot sent it
            for name, bot in self.bots.items():
                if bot.user_id == sender_id:
                    sender_name = name
                    break

        # Log the message to chat history
        chat_msg = ChatMessage(
            timestamp=time.time(),
            sender=sender_name,
            text=message.text,
            message_id=message.message_id,
            reply_to=message.reply_to_message.message_id if message.reply_to_message else 0,
        )
        append_message(chat_msg)

        # Don't respond to ourselves
        if is_bot_message:
            # Other bots might respond to bot messages, but the sending bot shouldn't
            pass

        # Each friend independently decides whether to respond
        tasks = []
        for name, bot in self.bots.items():
            # Don't respond to own messages
            if is_bot_message and bot.user_id == sender_id:
                continue

            friend_config = load_friend_config(name)

            # Schedule gate — are they even "around" right now?
            if not should_respond(friend_config, is_bot_message=is_bot_message):
                logger.debug(f"{name} is unavailable (schedule/chance)")
                continue

            tasks.append(self._friend_consider_response(
                name, bot, friend_config, sender_name, message.text, message.message_id
            ))

        if tasks:
            # Run all friend "thinking" concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

        # Periodically compact chat history
        chat_config = self.global_config.get("chat", {})
        await maybe_compact(
            self.claude, self.model,
            max_messages=chat_config.get("max_messages", 100),
            compact_to=chat_config.get("compact_to", 30),
        )

    async def _friend_consider_response(
        self, name: str, bot: FriendBot, friend_config: dict,
        sender: str, message: str, message_id: int
    ):
        """Have one friend consider and optionally respond to a message."""
        try:
            result = await think_and_respond(
                client=self.claude,
                model=self.model,
                friend_name=name,
                sender=sender,
                message=message,
                message_id=message_id,
                friend_config=friend_config,
            )

            if result and result.get("message"):
                # Simulate natural delay
                delay = result.get("delay_seconds", 3)
                await asyncio.sleep(delay)

                reply_to = result.get("reply_to_message_id")
                sent = await bot.send_message(result["message"], reply_to_message_id=reply_to)

                if sent:
                    # Log the bot's response
                    bot_msg = ChatMessage(
                        timestamp=time.time(),
                        sender=name,
                        text=result["message"],
                        message_id=sent.message_id,
                    )
                    append_message(bot_msg)
                    logger.info(f"{name} responded: {result['message'][:50]}...")

        except Exception as e:
            logger.exception(f"Error in {name}'s response: {e}")
