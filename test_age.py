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
from livekit import rtc
import json
import asyncio
from fuzzywuzzy import fuzz


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


# Add engagement phrases at the top of the file with other constants
engagement_phrases = [
    "hey",
    "hi",
    "hello",
    "can you",
    "could you",
    "would you",
    "please share",
    "please tell me",
    "tell me about",
    "what do you know",
    "talk to",
    "i want to talk to",
    "let's talk about",
    "could we discuss",
    "give me details about",
    "share information on",
    "i need info on",
    "help me with",
    "do you know about",
    "do you have details on",
    "can we go over",
    "explain",
    "walk me through",
    "i’m curious about",
    "enlighten me on",
    "let me know about",
    "inform me about",
    "i want to know about",
    "can we discuss",
    "what’s the deal with",
    "what’s going on with",
    "give me an update on",
    "i’d like to know about",
    "provide details on",
    "do you have info on"
]


class TranscriptLogger(logging.Handler):
    def is_engaging_with_character(self, user_input, character_names):
        user_input = user_input.lower()
        
        for phrase in engagement_phrases:
            if fuzz.partial_ratio(user_input, phrase) > 70:
                for character_name in character_names:
                    if character_name.lower() in user_input:
                        return character_name
        return ""

    def emit(self, record):
        if hasattr(record, 'user_transcript'):
            user_transcript = record.user_transcript
            logger.info(f"TranscriptLogger running.........{CHARACTER_NAMES}")
            
            if CHARACTER_NAMES:
                character = self.is_engaging_with_character(user_transcript, CHARACTER_NAMES)
                
                if character:
                    name = voices[character]
                    logger.info(f"voice active is {name}")
                    tts_instance.update_options(
                        model="tts-1",
                        voice=name,
                        speed=1.0
                    )
                else:
                    logger.info("No character engagement detected")
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
    chat = rtc.ChatManager(ctx.room)

    async def answer_from_text(txt: str):
        chat_ctx = assistant.chat_ctx.copy()
        chat_ctx.append(role="user", text=txt)
        logger.info("Asking suggestions")
        stream = assistant.llm.chat(chat_ctx=chat_ctx)
        await assistant.say(stream)

    @chat.on("message_received")
    def on_chat_received(msg: rtc.ChatMessage):
        assistant._interrupt_if_possible()
        if msg.message:
            asyncio.create_task(answer_from_text(msg.message))

    await assistant.say("Hey, Ready detective?", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
