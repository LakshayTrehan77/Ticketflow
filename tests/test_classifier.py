from app.services.classifier import TicketClassifier
from tests.conftest import MODEL_FILE


def test_predicts_known_categories():
    clf = TicketClassifier(str(MODEL_FILE))
    assert clf.ready

    assert (
        clf.predict("I was charged twice and need a refund for the invoice").category == "billing"
    )
    assert (
        clf.predict("The app crashes with a 500 error on the upload endpoint").category
        == "technical"
    )
    assert clf.predict("I forgot my password and cannot log in").category == "account"
    assert (
        clf.predict("It would be great if you could add an export to PDF option").category
        == "feature_request"
    )


def test_urgent_words_force_high_priority():
    clf = TicketClassifier(str(MODEL_FILE))
    result = clf.predict("Can you tell me about pricing for teams, I need this urgently")
    assert result.priority == "high"


def test_confidence_is_a_probability():
    clf = TicketClassifier(str(MODEL_FILE))
    result = clf.predict("Please add dark mode")
    assert 0 < result.confidence <= 1


def test_missing_model_falls_back_to_defaults(tmp_path):
    clf = TicketClassifier(str(tmp_path / "does-not-exist.joblib"))
    assert not clf.ready

    result = clf.predict("anything at all")
    assert result.category == "general"
    assert result.priority == "medium"
    assert result.confidence == 0.0
