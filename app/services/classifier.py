import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib

from app.config import get_settings

logger = logging.getLogger(__name__)

# words that almost always mean the customer is in a hurry
URGENT_WORDS = re.compile(r"\b(urgent|urgently|asap|immediately|outage)\b", re.IGNORECASE)


@dataclass
class Prediction:
    category: str
    priority: str
    confidence: float


class TicketClassifier:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.models = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists():
            logger.warning(
                "model file %s not found, tickets will get default labels", self.model_path
            )
            return
        self.models = joblib.load(self.model_path)
        logger.info("loaded classifier from %s", self.model_path)

    @property
    def ready(self) -> bool:
        return self.models is not None

    def predict(self, text: str) -> Prediction:
        if not self.ready:
            return Prediction(category="general", priority="medium", confidence=0.0)

        category_model = self.models["category"]
        probs = category_model.predict_proba([text])[0]
        best = probs.argmax()
        category = str(category_model.classes_[best])
        confidence = float(probs[best])

        priority = str(self.models["priority"].predict([text])[0])
        # model is trained on a small dataset so urgent keywords always win
        if priority != "high" and URGENT_WORDS.search(text):
            priority = "high"

        return Prediction(category=category, priority=priority, confidence=round(confidence, 3))


@lru_cache
def get_classifier() -> TicketClassifier:
    return TicketClassifier(get_settings().model_path)
