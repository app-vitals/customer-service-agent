import asyncio
import logging
import os
from collections.abc import AsyncIterable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from langfuse import Langfuse
from langfuse.client import StatefulClient
from livekit.agents import (
    Agent,
    AgentSession,
    ChatContext,
    ChatMessage,
    FunctionTool,
    JobContext,
    ModelSettings,
    RoomInputOptions,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
    get_job_context,
    llm,
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

_langfuse = Langfuse()

# Setup Jinja2 environment for templates
template_dir = Path(__file__).parent / "prompts"
jinja_env = Environment(loader=FileSystemLoader(template_dir))


class CustomerServiceAgent(Agent):
    def __init__(self, ctx: JobContext) -> None:
        # Hardcode customer data for testing
        # Lookup customer and outbound call details using phone number.
        customer_name = "John Smith"
        service_type = "HVAC maintenance"

        # Determine call direction from room name
        is_outbound = ctx.room.name.startswith("outbound")

        # Template context for rendering prompts
        template_context = {
            "customer_name": customer_name,
            "service_type": service_type,
        }

        if is_outbound:
            # Outbound call - agent is calling the customer
            instructions_template = jinja_env.get_template("instructions_outbound.j2")
            instructions = instructions_template.render(template_context)
            
            initial_prompt_template = jinja_env.get_template("initial_prompt_outbound.j2")
            self.initial_prompt = initial_prompt_template.render(template_context)
            tools = [leave_voicemail]
        else:
            # Inbound call - customer is calling the company
            instructions_template = jinja_env.get_template("instructions_inbound.j2")
            instructions = instructions_template.render(template_context)
            
            initial_prompt_template = jinja_env.get_template("initial_prompt_inbound.j2")
            self.initial_prompt = initial_prompt_template.render(template_context)
            tools = []

        super().__init__(instructions=instructions, tools=tools)
        self.ctx = ctx
        self.is_outbound = is_outbound
        self.session_id = str(uuid4())
        self.current_trace = None

    def close(self) -> None:
        if self.current_trace:
            self.current_trace = None
        _langfuse.flush()

    def get_current_trace(self) -> StatefulClient:
        if self.current_trace:
            return self.current_trace
        self.current_trace = _langfuse.trace(
            name="customer_service_agent", session_id=self.session_id
        )
        return self.current_trace

    async def on_user_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        # Reset the span when a new user turn is completed
        if self.current_trace:
            self.current_trace = None
        self.current_trace = _langfuse.trace(
            name="customer_service_agent", session_id=self.session_id
        )

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[FunctionTool],
        model_settings: ModelSettings,
    ) -> AsyncIterable[llm.ChatChunk]:
        generation = self.get_current_trace().generation(
            name="llm_generation",
            model="gpt-4o-mini",
            input=openai.utils.to_chat_ctx(chat_ctx, cache_key=self.llm),
        )
        output = ""
        set_completion_start_time = False
        try:
            async for chunk in Agent.default.llm_node(
                self, chat_ctx, tools, model_settings
            ):
                if not set_completion_start_time:
                    generation.update(
                        completion_start_time=datetime.now(UTC),
                    )
                    set_completion_start_time = True
                if chunk.delta and chunk.delta.content:
                    output += chunk.delta.content
                yield chunk
        except Exception:
            generation.update(level="ERROR")
            raise
        finally:
            generation.end(output=output)

    async def tts_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncIterable:
        span = self.get_current_trace().span(
            name="tts_node", metadata={"model": "elevenlabs"}
        )
        try:
            async for event in Agent.default.tts_node(self, text, model_settings):
                yield event
        except Exception:
            span.update(level="ERROR")
            raise
        finally:
            span.end()


@function_tool
async def leave_voicemail(run_ctx: RunContext, voicemail_message: str):
    """Leave a voicemail message after detecting a voicemail system. Use AFTER hearing the greeting/beep. The voicemail_message parameter should contain the complete message you want to leave for the customer."""
    ctx = get_job_context()
    await run_ctx.session.say(voicemail_message, allow_interruptions=False)
    await asyncio.sleep(1)

    # let the agent finish speaking
    current_speech = run_ctx.session.current_speech
    if current_speech:
        await current_speech.wait_for_playout()

    await ctx.api.room.delete_room(
        DeleteRoomRequest(
            room=ctx.room.name,
        )
    )
    await run_ctx.session.aclose()
    await ctx.shutdown("voicemail_left")


async def connect(ctx: JobContext, timeout: float = 3.0, max_retries: int = 3) -> bool:
    """Connect to LiveKit room with timeout, retries, and error handling."""
    logger.info(f"CONNECTING TO ROOM: '{ctx.room.name}'")

    for attempt in range(max_retries):
        try:
            await asyncio.wait_for(ctx.connect(), timeout=timeout)
            logger.info(f"CONNECTED TO ROOM: '{ctx.room.name}'")
            return True
        except TimeoutError:
            logger.warning(f"Connection attempt {attempt + 1} timed out")
            if attempt == max_retries - 1:
                logger.error("All connection attempts failed")
                ctx.shutdown("connection_timeout")
                return False
            await asyncio.sleep(2.0)  # Wait before retry
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            ctx.shutdown("connection_failed")
            return False

    return False


async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(),
        vad=silero.VAD.load(),
        turn_detection=EnglishModel(),
    )

    agent = CustomerServiceAgent(ctx)
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(),
    )

    if not await connect(ctx):
        return

    await session.generate_reply(
        instructions=agent.initial_prompt,
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
