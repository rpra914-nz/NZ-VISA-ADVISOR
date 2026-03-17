import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

# ── QUESTIONS TO ASK ─────────────────────────────────────────────────
# These are the fields we need to build the applicant profile
# Each has a key, a human-friendly question, and a type

INTAKE_QUESTIONS = [
    {
        "key": "nationality",
        "question": "What is your client's nationality / country of citizenship?",
        "type": "text"
    },
    {
        "key": "age",
        "question": "How old is your client?",
        "type": "number"
    },
    {
        "key": "occupation",
        "question": "What is your client's current occupation or job title?",
        "type": "text"
    },
    {
        "key": "job_offer",
        "question": "Does your client have a current job offer from a NZ employer?",
        "type": "boolean"
    },
    {
        "key": "years_experience",
        "question": "How many years of work experience does your client have in their field?",
        "type": "number"
    },
    {
        "key": "qualification",
        "question": "What is your client's highest qualification? (e.g. Bachelor's, Master's, PhD)",
        "type": "text"
    },
    {
        "key": "english_level",
        "question": "What is your client's English level? (e.g. IELTS score, or Native speaker)",
        "type": "text"
    },
    {
        "key": "family",
        "question": "Will any family members be included in the application? (e.g. spouse, children)",
        "type": "text"
    },
    {
        "key": "currently_in_nz",
        "question": "Is your client currently in New Zealand?",
        "type": "boolean"
    }
]


# ── EXTRACT ANSWER USING CLAUDE ──────────────────────────────────────
# Instead of rigid parsing, we use Claude to extract
# the answer from whatever the user typed
def extract_answer(user_input, question_key, question_type):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": f"""Extract the answer from this user input.

Question field: {question_key}
Expected type: {question_type}
User input: "{user_input}"

Rules:
- If type is "boolean": respond with only true or false
- If type is "number": respond with only the number
- If type is "text": respond with a clean, concise version of the answer
- If unclear or unanswered: respond with null

Respond with ONLY the extracted value, nothing else."""
            }
        ]
    )

    raw = message.content[0].text.strip().lower()

    # Convert to correct Python type
    if question_type == "boolean":
        return True if raw == "true" else False if raw == "false" else None
    elif question_type == "number":
        try:
            return float(raw) if "." in raw else int(raw)
        except:
            return None
    else:
        return raw if raw != "null" else None


# ── INTAKE AGENT CLASS ───────────────────────────────────────────────
class IntakeAgent:
    def __init__(self):
        self.profile = {}
        self.current_question_index = 0
        self.complete = False

    def get_current_question(self):
        """Returns the current question to ask"""
        if self.current_question_index < len(INTAKE_QUESTIONS):
            return INTAKE_QUESTIONS[self.current_question_index]["question"]
        return None

    def process_answer(self, user_input):
        """
        Takes the user's answer, extracts the value,
        stores it in profile, moves to next question
        """
        if self.current_question_index >= len(INTAKE_QUESTIONS):
            self.complete = True
            return

        current_q = INTAKE_QUESTIONS[self.current_question_index]

        # Use Claude to extract clean answer
        extracted = extract_answer(
            user_input,
            current_q["key"],
            current_q["type"]
        )

        # Store in profile
        self.profile[current_q["key"]] = extracted

        # Move to next question
        self.current_question_index += 1

        # Check if we're done
        if self.current_question_index >= len(INTAKE_QUESTIONS):
            self.complete = True

    def get_progress(self):
        """Returns progress as percentage"""
        return int(
            (self.current_question_index / len(INTAKE_QUESTIONS)) * 100
        )

    def get_profile_summary(self):
        """Returns a formatted summary of collected profile"""
        return json.dumps(self.profile, indent=2)


# ── TEST IN TERMINAL ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("🛂 NZ Visa Advisor — Client Intake")
    print("=" * 40)

    agent = IntakeAgent()

    while not agent.complete:
        # Show progress
        print(f"\nProgress: {agent.get_progress()}%")

        # Ask current question
        question = agent.get_current_question()
        print(f"\n❓ {question}")

        # Get user input
        answer = input("   Your answer: ")

        # Process it
        agent.process_answer(answer)

    # Show final profile
    print("\n" + "=" * 40)
    print("✅ Intake complete! Client profile:")
    print("=" * 40)
    print(agent.get_profile_summary())