from dataclasses import dataclass


@dataclass
class ValidationError:
    message: str


def validate_question_payload(payload):
    errors = []
    if len(payload) != 15:
        errors.append(ValidationError("Exactly 15 questions are required."))
        return errors

    for idx, question in enumerate(payload, start=1):
        if not question.get("text", "").strip():
            errors.append(ValidationError(f"Question {idx}: text is required."))
        for key in ["option_a", "option_b", "option_c", "option_d"]:
            if not question.get(key, "").strip():
                errors.append(ValidationError(f"Question {idx}: {key} is required."))
        if question.get("correct_option") not in {"A", "B", "C", "D"}:
            errors.append(ValidationError(f"Question {idx}: correct option must be A, B, C, or D."))
    return errors
