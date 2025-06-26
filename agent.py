import asyncio
import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
    get_job_context,
)
from livekit.api import DeleteRoomRequest
from livekit.plugins import (
    deepgram,
    elevenlabs,
    openai,
    silero,
)
from livekit.plugins.turn_detector.english import EnglishModel

logger = logging.getLogger("customer_service_agent")
logger.setLevel(logging.INFO)

load_dotenv()


async def hangup_call():
    ctx = get_job_context()
    if ctx is None:
        # Not running in a job context
        return

    await ctx.api.room.delete_room(
        DeleteRoomRequest(
            room=ctx.room.name,
        )
    )


class Assistant(Agent):
    def __init__(self) -> None:
        # Hardcode customer data for testing
        customer_name = "John Smith"
        service_type = "HVAC maintenance"

        super().__init__(
            instructions=f"You are Sarah from Dan and Dave's AI Consulting in Tahoe, CA. You are calling {customer_name} about their {service_type}.\n\nAfter your initial greeting, listen for the response:\n\n• LIVE CUSTOMER: If they respond conversationally, have a normal business conversation about their service.\n\n• VOICEMAIL: If you hear voicemail prompts ('at the tone', 'leave a message', 'please record'), use the leave_voicemail tool. Provide a complete professional message including: your name (Sarah), company (Dan and Dave's AI Consulting in Tahoe), reason for calling ({service_type}), and request to call back.\n\nSpeak directly to the customer, not about them."
        )

    @function_tool
    async def leave_voicemail(self, voicemail_message: str):
        """Leave a voicemail message after detecting a voicemail system. Use AFTER hearing the greeting/beep. The voicemail_message parameter should contain the complete message you want to leave for the customer."""
        await self.session.say(voicemail_message, allow_interruptions=False)
        await asyncio.sleep(0.5)

        # let the agent finish speaking
        current_speech = self.session.current_speech
        if current_speech:
            await current_speech.wait_for_playout()

        await self.session.aclose()
        await hangup_call()


async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(),
        vad=silero.VAD.load(),
        turn_detection=EnglishModel(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(),
    )

    logger.info(f"CONNECTING TO ROOM: '{ctx.room.name}'")
    await ctx.connect()
    logger.info(f"CONNECTED TO ROOM: '{ctx.room.name}'")

    await session.generate_reply(
        instructions="Greet the customer and introduce yourself as Sarah from Dan and Dave's AI Consulting calling about their service.",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
