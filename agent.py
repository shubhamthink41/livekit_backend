import logging
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, deepgram, silero
from utils.prompts import LK_role
from utils.patterns import extract_character_data
from utils.get_prompt import fetch_prompt
import re
import json

load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("voice-agent")


LK_prompt = ""


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


tts_instance = openai.TTS(voice="fable")


CHARACTER_NAMES = ["alloy"]


async def initialize():
    global CHARACTER_NAMES, voices

    LK_prompt = await fetch_prompt()

    try:
        story_data = json.loads(LK_prompt) if isinstance(
            LK_prompt, str) else LK_prompt

        story_json = json.loads(story_data['story']) if isinstance(
            story_data['story'], str) else story_data['story']

        CHARACTER_NAMES, voices = extract_character_data(story_json)
        print("CHARACTER_NAMES =", CHARACTER_NAMES)
        print("voices =", voices)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Error processing story data: {e}")
        print("Error processing story data!")
        CHARACTER_NAMES = []
        voices = {}


class TranscriptLogger(logging.Handler):
    def emit(self, record):
        if hasattr(record, 'user_transcript'):
            user_transcript = record.user_transcript
            logger.info(f"TranscriptLogger running.........{CHARACTER_NAMES}")
            if CHARACTER_NAMES:
                for char_name in CHARACTER_NAMES:
                    logger.info(
                        f"TranscriptLogger running......... {char_name}")
                    pattern = (
                        fr"(bring out {re.escape(char_name)}|"
                        fr"activate {re.escape(char_name)}|"
                        fr"bring out {re.escape(char_name)})"
                    )

                    if re.search(pattern, user_transcript, re.IGNORECASE):
                        name = voices[char_name]
                        logger.info(f"voice active is {name}")
                        tts_instance.update_options(
                            model="tts-1",
                            voice=name,
                            speed=1.0
                        )
                        break
            else:
                logger.error(f"CHARACTER_NAMES is empty")


# Configure the logger
logger = logging.getLogger("livekit.agents.pipeline")
logger.setLevel(logging.DEBUG)
handler = TranscriptLogger()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# entrypoint
async def entrypoint(ctx: JobContext):
    await initialize()

    initial_ctx = llm.ChatContext().append(
        role='system',
        text=LK_role,
    )

    initial_ctx.append(
        role='system',
        text=LK_prompt
    )

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()

    logger.info(
        f"starting voice assistant for participant {participant.identity}")

    # Use the global tts_instance
    assistant = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=tts_instance,
        chat_ctx=initial_ctx,
        min_endpointing_delay=0.3,
    )

    assistant.start(ctx.room, participant)

    await assistant.say("Hey, Ready detective?", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
