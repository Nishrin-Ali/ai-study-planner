import asyncio
import json
import logging
import re
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models.notes import UploadedNotes
from app.models.plans import Answer, PlanItem, StudyPlan
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.services.gemini import get_genai_client

logger = logging.getLogger("vtu_planner.chat")

router = APIRouter(prefix="/api/chat", tags=["Study Buddy Chat"])

PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "prompts" / "study_buddy.txt"


def load_system_prompt() -> str:
    """Read the Study Buddy prompt template from disk."""
    try:
        if PROMPT_TEMPLATE_PATH.exists():
            return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read study_buddy.txt, using fallback template: %s", e)
    return (
        "You are 'Study Buddy', a friendly senior VTU engineering student. "
        "Explain concepts simply with analogies, scoring tips, and offer to quiz the student. "
        "Ground answers strictly in: <<<UNTRUSTED_STUDY_MATERIAL>>>{context_material}<<<UNTRUSTED_STUDY_MATERIAL>>>"
    )


def detect_language(text: str) -> str:
    """
    Detect whether the student prompt is in Kannada, Hindi, or English.
    Checks unicode ranges for Kannada and Devanagari, plus common phonetic keywords.
    """
    # Kannada Unicode block: \u0C80 - \u0CFF
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "kn"
    # Hindi / Devanagari Unicode block: \u0900 - \u097F
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    lower = text.lower()
    # Check Romanized Kannada keywords
    if any(k in lower for k in ["hege", "enu", "arthavagilla", "dayavittu", "namaskara", "kannadadalli", "kannada"]):
        return "kn"
    # Check Romanized Hindi keywords
    if any(h in lower for h in ["namaste", "bhaiya", "kaise", "samjha", "batao", "kya hai", "hindi me"]):
        return "hi"

    return "en"


def generate_fallback_reply(
    user_message: str,
    question_text: str,
    context_material: str,
    attribution: str,
    grounded: bool,
) -> str:
    """
    Generate an offline/graceful senior VTU student response when GEMINI_API_KEY
    is not configured or live streaming fails.
    """
    lang = detect_language(user_message + " " + question_text)
    user_lower = user_message.lower()

    if lang == "kn":
        disclaimer = ""
        if not grounded:
            disclaimer = "\n\n*(ಗಮನಿಸಿ: ಈ ನಿರ್ದಿಷ್ಟ ವಿವರ ನಿಮ್ಮ ನೋಟ್ಸ್‌ನಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ, ಆದರೆ ಸಾಮಾನ್ಯ ವಿವರಣೆ ಇಲ್ಲಿದೆ:)*\n"
        return (
            f"ಹಲೋ ಜೂನಿಯರ್! VTU ಪರೀಕ್ಷೆಗಾಗಿ '{question_text}' ಬಗ್ಗೆ ಚಿಂತೆ ಮಾಡಬೇಡಿ.{disclaimer}\n\n"
            f"1. **ಮುಖ್ಯ ಪರಿಕಲ್ಪನೆ (Core Concept):**\n"
            f"ಇದು VTU ಪರೀಕ್ಷೆಯಲ್ಲಿ ಪದೇ ಪದೇ ಕೇಳಲಾಗುವ ಪ್ರಮುಖ ವಿಷಯ. ಸರಳವಾಗಿ ಹೇಳುವುದಾದರೆ, "
            f"ಇದು ಸಿಸ್ಟಮ್‌ನ ಮೂಲಭೂತ ನಿಯಮಗಳನ್ನು ಅನುಸರಿಸುತ್ತದೆ.\n\n"
            f"2. **VTU ಪರೀಕ್ಷಾ ಸಲಹೆ (Exam Tip):**\n"
            f"- 5 ಮಾರ್ಕ್ಸ್‌ ಪ್ರಶ್ನೆಗೆ ಕನಿಷ್ಠ 4 ಪ್ರಮುಖ ಪಾಯಿಂಟ್ಸ್ ಮತ್ತು ಒಂದು ಬ್ಲಾಕ್ ಡಯಾಗ್ರಾಮ್ ಬರೆಯಿರಿ.\n"
            f"- ವ್ಯಾಲ್ಯುಯೇಶನ್‌ನಲ್ಲಿ ಡಯಾಗ್ರಾಮ್‌ಗೆ 1.5 - 2 ಮಾರ್ಕ್ಸ್ ಇರುತ್ತದೆ.\n\n"
            f"ನೀವು ಸಿದ್ಧರಿದ್ದರೆ, ನಾನು ಇದರ ಮೇಲೆ ಒಂದು ಸಣ್ಣ 5-ಮಾರ್ಕ್ಸ್ ಕ್ವಿಜ್ (Quiz) ಕೇಳಲೇ?"
        )

    if lang == "hi":
        disclaimer = ""
        if not grounded:
            disclaimer = "\n\n*(नोट: यह विवरण आपके अपलोडेड नोट्स में सीधे नहीं है, पर समझने के लिए यह सामान्य व्याख्या है:)*\n"
        return (
            f"नमस्ते जूनियर! VTU एग्जाम के लिए '{question_text}' को लेकर टेंशन मत लो.{disclaimer}\n\n"
            f"1. **मूल विचार (Core Concept):**\n"
            f"यह VTU पेपर्स का काफी पसंदीदा सवाल है। इसे सरल शब्दों में समझें तो यह "
            f"डेटा और सिस्टम के बीच सुचारू प्रवाह सुनिश्चित करता है।\n\n"
            f"2. **VTU 5/10 मार्क्स स्कोरिंग टिप्स:**\n"
            f"- पहले 2 लाइन में स्पष्ट परिभाषा लिखें।\n"
            f"- 3-4 बुलेट पॉइंट्स में कार्यप्रणाली (Working) और एक साफ ब्लॉक डायग्राम जरूर बनाएं।\n"
            f"- VTU एग्जामिनर हेडिंग्स और डायग्राम्स पर पूरे अंक देते हैं।\n\n"
            f"क्या आप चाहते हैं कि मैं आपकी तैयारी जांचने के लिए एक छोटा सा क्विज़ पूछूं?"
        )

    # English fallback
    disclaimer = ""
    if not grounded:
        disclaimer = "\n\n> **Note:** This specific detail isn't in your uploaded notes or syllabus excerpt, but here is a general senior explanation to help you understand:"

    if any(q in user_lower for q in ["5 mark", "5 marks", "scoring", "marks"]):
        return (
            f"Hey junior! Here is how you tackle **{question_text}** for a 5-mark question in VTU:{disclaimer}\n\n"
            f"### 1. Definition (1 Mark)\n"
            f"State a precise, one or two-sentence definition highlighting the primary purpose and context.\n\n"
            f"### 2. Key Working Points (2.5 Marks)\n"
            f"- **Core Mechanism:** Explain the step-by-step logic sequentially.\n"
            f"- **Properties:** List 3 distinguishing characteristics or operational rules.\n"
            f"- **Complexity / Formula:** Mention time/space efficiency or governing formulas where applicable.\n\n"
            f"### 3. Diagram & Example (1.5 Marks)\n"
            f"- Draw a clean labeled block diagram (VTU evaluators look for neat ASCII/box layouts).\n"
            f"- Provide a 2-line practical example.\n\n"
            f"💡 *Senior Exam Tip:* Keep this within 1.5 sides of the answer sheet.\n\n"
            f"Would you like me to quiz you right now to test if you've memorized these points?"
        )

    if "example" in user_lower or "analogy" in user_lower:
        return (
            f"Hey! Here is an intuitive analogy for **{question_text}**:{disclaimer}\n\n"
            f"Think of it like a train ticket counter: orderly, predictable, and following strict protocols. "
            f"Each incoming request is placed in queue, validated, and processed sequentially without collisions.\n\n"
            f"- **Real-world Example:** In daily computing, this behaves just like print spooling or OS task queues.\n"
            f"- **Why VTU Asks This:** They want to see if you can connect theoretical definitions to concrete system behavior.\n\n"
            f"💡 *Senior Exam Tip:* Always mention one real-world application in your 5-mark answers — examiners award bonus marks for it!\n\n"
            f"Shall we do a quick 2-minute quiz on this topic?"
        )

    if "quiz" in user_lower or "test" in user_lower:
        return (
            f"Alright junior, time for a quick VTU recall check on **{question_text}**! 🎯\n\n"
            f"**Practice Question (VTU 5-Mark Pattern):**\n"
            f"> What are the key differences between linear and non-linear implementations in {question_text}, "
            f"and which one offers O(1) direct access?\n\n"
            f"Reply with your answer in 2-3 brief bullet points, and I'll grade it for you like a VTU examiner!"
        )

    # General simple explanation
    summary_excerpt = context_material[:400].strip() if context_material else ""
    return (
        f"Hey junior! Don't stress, here is the quick breakdown for **{question_text}**:{disclaimer}\n\n"
        f"### The Big Picture\n"
        f"In VTU exams, this topic is tested to verify your understanding of core engineering fundamentals. "
        f"The primary goal is to ensure reliable processing while minimizing resource overhead.\n\n"
        f"### High-Yield Points for Your Notes\n"
        f"- **Core Function:** Coordinates foundational operations cleanly.\n"
        f"- **Key Characteristic:** Follows deterministic steps and strict modular interfaces.\n"
        f"- **Common Pitfall:** Don't forget to define edge cases (like overflow/underflow or boundary conditions).\n\n"
        f"💡 *Senior Exam Tip:* For a 5-mark question, write 4 bullet points and draw a quick labeled box diagram.\n\n"
        f"Would you like me to quiz you on this, or would you like a 5-mark model answer outline?"
    )


@router.post("", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat_with_study_buddy(
    request: Request,
    body: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Study Buddy AI Chatbot endpoint:
    - Grounded strictly in uploaded notes or curriculum data.
    - Friendly senior VTU student persona.
    - Multilingual: Kannada, Hindi, and English.
    - Streaming SSE response by default, or JSON response if Accept: application/json or stream: false.
    - Rate limited to 20 requests per minute per IP.
    """
    # 1. Verify Study Plan exists
    plan = db.query(StudyPlan).filter(StudyPlan.id == body.plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan '{body.plan_id}' not found.",
        )

    # 2. Extract grounded context from PlanItem, Answer, or UploadedNotes
    module_str = "All Modules"
    answer_content = ""
    attribution = ""
    grounded = False

    if body.item_id:
        item = db.query(PlanItem).filter(
            PlanItem.plan_id == body.plan_id,
            PlanItem.id == body.item_id,
        ).first()
        if item:
            if item.module:
                module_str = f"Module {item.module}"
            if item.answer_id:
                ans = db.query(Answer).filter(Answer.id == item.answer_id).first()
                if ans:
                    answer_content = ans.content
                    attribution = ans.source_attribution
                    grounded = True

    # Fallback to matching Answer by question_text if not found via item_id
    if not answer_content:
        ans = db.query(Answer).filter(
            Answer.plan_id == body.plan_id,
            Answer.question_or_topic.ilike(f"%{body.question_text[:30]}%"),
        ).first()
        if ans:
            answer_content = ans.content
            attribution = ans.source_attribution
            if ans.module:
                module_str = f"Module {ans.module}"
            grounded = True

    # Check for uploaded notes belonging to this course
    notes = db.query(UploadedNotes).filter(
        UploadedNotes.course_code == plan.course_code
    ).order_by(UploadedNotes.created_at.desc()).first()

    notes_excerpt = ""
    if notes and notes.text_excerpt:
        notes_excerpt = notes.text_excerpt[:2000]
        if not attribution:
            attribution = f"Uploaded notes: {notes.filename}"
        grounded = True

    # Build context material for injection defense
    context_parts: List[str] = []
    if answer_content:
        context_parts.append(f"Model Answer / Key Points:\n{answer_content}")
    if notes_excerpt:
        context_parts.append(f"Lecture Notes Excerpt:\n{notes_excerpt}")
    if attribution:
        context_parts.append(f"Source Attribution: {attribution}")

    if context_parts:
        context_material = "\n\n".join(context_parts)
    else:
        context_material = "No specific lecture notes or model answers uploaded for this item."
        attribution = "VTU General Curriculum Reference"
        grounded = False

    # 3. Assemble prompt template with injection demarcation
    template = load_system_prompt()
    system_instruction = template.format(
        course_code=plan.course_code,
        module=module_str,
        question_text=body.question_text,
        context_material=context_material,
    )

    # 4. Check if client explicitly requests non-streaming JSON
    wants_json = (
        body.stream is False
        or request.headers.get("accept") == "application/json"
    )

    # Try live Gemini streaming if client and key are configured
    genai_client = get_genai_client() if settings.has_gemini else None

    # Helper for building non-streaming JSON response
    if wants_json:
        if genai_client:
            try:
                from google.genai import types

                contents = []
                # History (max 10)
                for h in body.history[-10:]:
                    role = "user" if h.role == "user" else "model"
                    contents.append(types.Content(role=role, parts=[types.Part.from_text(text=h.text)]))
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=body.user_message)]))

                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
                response = await genai_client.aio.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=contents,
                    config=config,
                )
                reply_text = (response.text or "").strip()
                return ChatResponse(
                    reply=reply_text,
                    source_attribution=attribution,
                    grounded=grounded,
                )
            except Exception as e:
                logger.warning("Gemini JSON call failed (%s), falling back to offline generator.", e)

        # Fallback offline reply
        fallback_text = generate_fallback_reply(
            user_message=body.user_message,
            question_text=body.question_text,
            context_material=context_material,
            attribution=attribution,
            grounded=grounded,
        )
        return ChatResponse(
            reply=fallback_text,
            source_attribution=attribution,
            grounded=grounded,
        )

    # 5. SSE Streaming Generator
    async def sse_event_stream() -> AsyncGenerator[str, None]:
        streamed_any = False
        if genai_client:
            try:
                from google.genai import types

                contents = []
                for h in body.history[-10:]:
                    role = "user" if h.role == "user" else "model"
                    contents.append(types.Content(role=role, parts=[types.Part.from_text(text=h.text)]))
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=body.user_message)]))

                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
                response_stream = await genai_client.aio.models.generate_content_stream(
                    model=settings.GEMINI_MODEL,
                    contents=contents,
                    config=config,
                )
                async for chunk in response_stream:
                    if chunk.text:
                        streamed_any = True
                        payload = {"text": chunk.text, "done": False}
                        yield f"data: {json.dumps(payload)}\n\n"

                # Send completion event
                yield f"data: {json.dumps({'text': '', 'done': True, 'attribution': attribution, 'grounded': grounded})}\n\n"
                return
            except Exception as e:
                logger.warning("Live Gemini SSE streaming error: %s. Using graceful fallback stream.", e)

        # If live stream did not yield or genai client unavailable: stream fallback chunks
        if not streamed_any:
            fallback_text = generate_fallback_reply(
                user_message=body.user_message,
                question_text=body.question_text,
                context_material=context_material,
                attribution=attribution,
                grounded=grounded,
            )
            # Break into comfortable token-like words/chunks
            words = fallback_text.split(" ")
            chunk_buffer: List[str] = []
            for i, word in enumerate(words):
                chunk_buffer.append(word)
                if len(chunk_buffer) >= 3 or i == len(words) - 1:
                    chunk_str = (" " if i > len(chunk_buffer) - 1 else "") + " ".join(chunk_buffer)
                    payload = {"text": chunk_str + " ", "done": False}
                    yield f"data: {json.dumps(payload)}\n\n"
                    chunk_buffer = []
                    await asyncio.sleep(0.015)

            yield f"data: {json.dumps({'text': '', 'done': True, 'attribution': attribution, 'grounded': grounded})}\n\n"

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
