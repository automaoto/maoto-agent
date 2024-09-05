from maoto_agent import *
from dotenv import load_dotenv

load_dotenv('.secrets_02') # Should contain OPENAI_API_KEY and MAOTO_API_KEY

if __name__ == "__main__":
    personal_assistant = PersonalAssistant(working_dir="./work_dir_provider")

    # Test the audio_to_text action
    personal_assistant.run(
        input_text="I want to convert the speech into text.",
        attachment_path="./test_audiofile.mp3"
    )
    while True:
        personal_assistant.run(
            input_text=input("Prompt: ")
        )
