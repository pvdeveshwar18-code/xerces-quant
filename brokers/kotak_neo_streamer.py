import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional

# Optional: import websocket client library if available
try:
    import websocket  # type: ignore
except ImportError:
    websocket = None

logger = logging.getLogger(__name__)


class BaseLiveStreamer(ABC):
    """Abstract base class for live market data streaming.

    Sub‑classes must implement ``connect`` and an internal ``_listen`` loop.
    They emit 1‑minute candle data and optionally depth snapshots via callbacks.
    """

    def __init__(self, on_candle: Callable[[Dict], None], on_depth: Optional[Callable[[Dict], None]] = None):
        self.on_candle = on_candle
        self.on_depth = on_depth
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the broker's streaming endpoint."""
        pass

    @abstractmethod
    def _listen(self) -> None:
        """Internal listener loop that receives raw messages and processes them."""
        pass

    def run(self) -> None:
        """Start a background thread that keeps the streamer alive.

        Calling ``run`` when already active is a no‑op.
        """
        if self._running:
            logger.debug("Live streamer already running.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info("Live streamer thread started.")

    def stop(self) -> None:
        """Signal the listener to stop and wait for cleanup."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            logger.info("Live streamer stopped.")

    def _handle_message(self, message: str) -> None:
        """Parse incoming JSON and dispatch to callbacks.

        Expected payload examples::

            {"type": "candle", "data": {...}}
            {"type": "depth",  "data": {...}}
        """
        try:
            payload = json.loads(message)
            msg_type = payload.get("type")
            data = payload.get("data")
            if msg_type == "candle" and data:
                self.on_candle(data)
            elif msg_type == "depth" and data and self.on_depth:
                self.on_depth(data)
            else:
                logger.debug(f"Unrecognized message type: {msg_type}")
        except json.JSONDecodeError:
            logger.warning("Failed to decode message as JSON: %s", message)


class KotakNeoStreamer(BaseLiveStreamer):
    """Concrete implementation for Kotak Neo WebSocket streaming.

    The Kotak Neo API streams 1‑minute OHLCV candles and optional level‑2 depth.
    """

    WS_URL = "wss://api.kotakneo.com/v1/stream"

    def __init__(self, api_key: str, api_secret: str, symbols: List[str], on_candle: Callable[[Dict], None], on_depth: Optional[Callable[[Dict], None]] = None):
        super().__init__(on_candle=on_candle, on_depth=on_depth)
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbols = symbols
        self.ws: Optional[websocket.WebSocketApp] = None

    def connect(self) -> None:
        # If the websocket-client library is unavailable, inform the user via Streamlit UI
        if websocket is None:
            try:
                import streamlit as st
                st.error(
                    "❌ Live streaming requires the `websocket-client` library. "
                    "Please install it (see requirements.txt) and restart the app."
                )
            except Exception:
                # Fallback to logger if Streamlit import fails (e.g., during tests)
                logger.error(
                    "websocket-client library not installed; cannot connect to Kotak Neo."
                )
            # Abort connection attempt without raising an exception that crashes the app
            return

        def _on_open(ws):
            logger.info("WebSocket connection opened.")
            auth_msg = json.dumps({
                "action": "authenticate",
                "api_key": self.api_key,
                "api_secret": self.api_secret,
            })
            ws.send(auth_msg)
            sub_msg = json.dumps({
                "action": "subscribe",
                "symbols": self.symbols,
                "interval": "1min",
                "include_depth": bool(self.on_depth),
            })
            ws.send(sub_msg)
            logger.debug("Sent authentication and subscription messages.")

        def _on_message(ws, message):
            self._handle_message(message)

        def _on_error(ws, error):
            logger.error(f"WebSocket error: {error}")

        def _on_close(ws, close_status_code, close_msg):
            logger.info(f"WebSocket closed: {close_status_code} {close_msg}")

        self.ws = websocket.WebSocketApp(
            self.WS_URL,
            on_open=_on_open,
            on_message=_on_message,
            on_error=_on_error,
            on_close=_on_close,
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
        time.sleep(1)  # give the connection a moment to establish
        logger.info("KotakNeoStreamer connection initiated.")

    def _listen(self) -> None:
        # The websocket callbacks drive data; keep the thread alive.
        while self._running:
            time.sleep(0.5)
        if self.ws:
            self.ws.close()
            logger.info("WebSocket connection closed by streamer.")
