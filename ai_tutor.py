import json
import os
import time
from pathlib import Path

import streamlit as st

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"

# Free-tier friendly defaults. Quota is project-level, so retrying 429s or
# switching models does not bypass an exhausted project quota.
MAX_RETRIES = 1
RETRY_DELAYS = (2.0,)
DEFAULT_MODEL = "gemini-2.5-flash-lite"
MAX_KNOWLEDGE_CHARS = 8000
MAX_OUTPUT_TOKENS = 800


def _secret(name, default=None):
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)


def ai_configured():
    return bool(_secret("GEMINI_API_KEY"))


def _knowledge_text(question=""):
    """Return a small relevant knowledge slice to reduce Free Tier token usage."""
    if not KNOWLEDGE_DIR.exists():
        return ""

    question_words = {
        word.strip(".,?!:;()[]{}").lower()
        for word in question.split()
        if len(word.strip(".,?!:;()[]{}")) >= 4
    }
    candidates = []

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue

        haystack = f"{path.stem} {content}".lower()
        score = sum(1 for word in question_words if word in haystack)
        candidates.append((score, path.name, content))

    candidates.sort(key=lambda item: (-item[0], item[1]))

    chunks = []
    remaining = MAX_KNOWLEDGE_CHARS
    for _, _, content in candidates:
        if remaining <= 0:
            break
        excerpt = content[:remaining]
        chunks.append(excerpt)
        remaining -= len(excerpt)

    return "\n\n".join(chunks)


def _is_quota_error(exc):
    message = str(exc).lower()
    return any(marker in message for marker in (
        "429", "resource_exhausted", "quota", "rate limit",
        "too many requests", "requests per minute", "requests per day",
        "tokens per minute",
    ))


def _is_transient_error(exc):
    message = str(exc).lower()
    return any(marker in message for marker in (
        "503", "unavailable", "500 internal", "502 bad gateway", "504 gateway",
    ))


def ask_tutor(question, context=None):
    key = _secret("GEMINI_API_KEY")
    if not key:
        return None, "AI Tutor is not configured yet. Add GEMINI_API_KEY to Streamlit secrets to enable it."

    model = _secret("GEMINI_MODEL", DEFAULT_MODEL)
    context = context or {}

    # Google Search grounding consumes additional quota. Only enable it for
    # questions that explicitly need current/live information.
    lowered_question = question.lower()
    needs_web = any(marker in lowered_question for marker in (
        "latest", "today", "current", "recent", "this week", "this month",
        "news", "2026", "now", "as of", "updated",
    ))

    system = """You are TradeWar AI, the general-purpose research assistant inside TradeWar AI Simulator.
Answer questions related to international trade, tariffs, trade policy, economics, macroeconomics, financial markets, demographics, supply chains, historical trade shocks, and how the TradeWar AI Simulator works. For current or changing information, use Google Search grounding and cite useful sources. Prefer primary sources, official statistics, central banks, government agencies, international organizations, and reputable financial/news sources. Completely unrelated questions should be politely redirected back to the app topic.
Never invent data, coefficients, market observations, or app capabilities. Treat the app's statistical/economic models as the source of quantitative results; AI is only an explanation layer.
Keep answers concise but complete and easy to understand. For most questions, aim for roughly 150-300 words; use short paragraphs or 3-6 bullets when appropriate. For simple questions, answer more briefly. For complex questions, include only the key details needed for understanding and expand only when genuinely necessary. Avoid repeating the question, unnecessary background, long lists, and filler. Do not try to use the full output limit. Always finish the explanation clearly rather than stopping mid-thought.
Distinguish observed data, model estimates, assumptions, scenarios and forecasts. Explain correlation versus causation and uncertainty when relevant.
Do not give personalized investment advice. If asked for an investment recommendation, explain the relevant concepts and limitations instead.
If the user asks about a value produced by the app, use the supplied APP CONTEXT and explain what that value means; do not fabricate missing values.
"""

    prompt = f"""APP CONTEXT:
{json.dumps(context, default=str, indent=2)}

KNOWLEDGE:
{_knowledge_text(question)}

QUESTION:
{question}"""

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    last_error = None

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            config_kwargs = dict(
                system_instruction=system,
                temperature=0.3,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
            if needs_web:
                config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            text = getattr(response, "text", None)
            sources = []
            try:
                metadata = response.candidates[0].grounding_metadata
                for chunk in getattr(metadata, "grounding_chunks", []) or []:
                    web = getattr(chunk, "web", None)
                    uri = getattr(web, "uri", None) if web else None
                    title = getattr(web, "title", None) if web else None
                    if uri and uri not in {item["url"] for item in sources}:
                        sources.append({"title": title or uri, "url": uri})
            except Exception:
                sources = []
            return {"text": text or "I received a response but could not extract the tutor text.", "sources": sources[:6]}, None

        except Exception as exc:
            last_error = exc

            # A quota 429 is a hard project-level limit. Retrying or switching
            # models would only consume more requests, so fail immediately.
            if _is_quota_error(exc):
                break

            if not _is_transient_error(exc) or attempt >= MAX_RETRIES:
                break

            time.sleep(RETRY_DELAYS[attempt])

    message = str(last_error)
    lowered = message.lower()

    if _is_quota_error(last_error):
        return None, (
            "Gemini Free Tier quota has been reached for this project. "
            "The chatbot is working, but Google is currently rejecting API requests. "
            "Wait for the quota window to reset, or use a project/model with available Free Tier quota."
        )

    if _is_transient_error(last_error):
        return None, "Gemini is temporarily unavailable. Please try again in a few seconds."

    if "api key" in lowered or "authentication" in lowered or "permission" in lowered:
        return None, "AI authentication failed. Check the configured API key in Streamlit Secrets."

    if "not found" in lowered or ("model" in lowered and "not found" in lowered):
        return None, "The configured AI model was not found. Check the model setting in Streamlit Secrets."

    return None, "The TradeWar AI assistant encountered an unexpected Gemini API error. Please check the Gemini API project settings."


def render_global_chatbot():
    """Render one app-wide floating TradeWar AI chatbot with live web-grounded answers."""
    history_key = "tradewar_global_chat_history"
    input_key = "tradewar_global_chat_input"

    if history_key not in st.session_state:
        st.session_state[history_key] = []

    # Streamlit locks a widget's session-state key once that widget is created.
    # Apply deferred input changes before the text_area is instantiated.
    if st.session_state.pop("tradewar_global_chat_clear_input", False):
        st.session_state[input_key] = ""

    st.markdown(
        """
        <style>
        .st-key-tradewar-global-chatbot {
            position: fixed !important;
            right: 24px !important;
            bottom: 24px !important;
            z-index: 999999 !important;
        }
        .st-key-tradewar-global-chatbot > div { width: auto !important; }
        .st-key-tradewar-global-chatbot button {
            border-radius: 999px !important;
            min-width: 52px !important;
            width: 52px !important;
            height: 52px !important;
            padding: 0 !important;
            box-shadow: 0 6px 22px rgba(0,0,0,.22) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    popover = st.popover(
        "",
        icon=":material/smart_toy:",
        type="primary",
        help="Ask TradeWar AI — web-grounded answers about trade, tariffs, economics and this simulator.",
        width=430,
        key="tradewar-global-chatbot",
    )

    with popover:
        st.markdown("### 🤖 TradeWar AI")
        st.caption(
            "Ask about trade, tariffs, economics, markets, supply chains, macro data "
            "or how this simulator works. It can search the live web when needed."
        )

        if not ai_configured():
            st.warning("Add GEMINI_API_KEY in Streamlit Secrets to enable the chatbot.")
        else:
            st.markdown("**Try asking:**")
            default_questions = [
                "What happens to GDP when tariffs increase?",
                "How do tariffs affect consumers and businesses?",
                "What is the difference between a tariff and a quota?",
                "How can a trade war affect supply chains?",
                "How should I interpret the scenario results?",
            ]
            qcols = st.columns(2)
            for i, default_question in enumerate(default_questions):
                with qcols[i % 2]:
                    if st.button(default_question, use_container_width=True, key=f"tradewar-default-question-{i}"):
                        st.session_state[input_key] = default_question
                        st.rerun()

            question = st.text_area(
                "Ask a question",
                key=input_key,
                height=90,
                placeholder="e.g. What are the latest US-China tariff developments?",
                label_visibility="collapsed",
            )

            col1, col2 = st.columns([1, 1])
            with col1:
                ask = st.button("Ask", type="primary", use_container_width=True, key="tradewar-global-chat-ask")
            with col2:
                clear = st.button("Clear", use_container_width=True, key="tradewar-global-chat-clear")

            if clear:
                st.session_state[history_key] = []
                st.session_state["tradewar_global_chat_clear_input"] = True
                st.rerun()

            if ask:
                question = question.strip()
                if not question:
                    st.warning("Please enter a question.")
                else:
                    context = {
                        "app": "TradeWar AI Simulator",
                        "scope": "International trade, tariffs, trade policy, economics, macroeconomics, financial markets, demographics, supply chains, historical trade shocks, and simulator usage.",
                    }
                    with st.spinner("Searching the web and preparing an answer…"):
                        result, error = ask_tutor(question, context)

                    if error:
                        st.error(error)
                    else:
                        st.session_state[history_key].append({"role": "user", "text": question})
                        st.session_state[history_key].append({
                            "role": "assistant",
                            "text": result["text"],
                            "sources": result.get("sources", []),
                        })
                        # Defer clearing the widget value until the next rerun.
                        # Do not rerun here: keeping this run alive lets the newly
                        # added question/answer render immediately in the popover.
                        st.session_state["tradewar_global_chat_clear_input"] = True

            # Show the conversation below the question controls. Because the
            # Ask action is processed before this block, the latest question and
            # answer appear immediately in the same session/run.
            if st.session_state[history_key]:
                st.divider()
                for message in st.session_state[history_key]:
                    with st.chat_message(message["role"]):
                        st.markdown(message["text"])
                        if message.get("sources"):
                            with st.expander("Sources"):
                                for source in message["sources"]:
                                    st.markdown(f"- [{source['title']}]({source['url']})")


def render_ai_tutor(page, context=None, suggestions=None):
    context = dict(context or {})
    context.setdefault("page", page)
    suggestions = suggestions or [
        "Explain what this page is doing in simple terms.",
        "What should I look at first?",
        "What are the main limitations of this analysis?",
    ]

    input_key = f"tutor_input_{page}"
    answer_key = f"tutor_answer_{page}"
    error_key = f"tutor_error_{page}"

    with st.sidebar.expander("🤖 TradeWar AI Tutor", expanded=False):
        st.caption("Economics tutor + app guide. AI explains results; the app's models calculate them.")

        if not ai_configured():
            st.info("Tutor is ready in the UI but disabled until GEMINI_API_KEY is added to Streamlit secrets.")

        for i, suggestion in enumerate(suggestions[:3]):
            if st.button(suggestion, key=f"tutor_suggestion_{page}_{i}", use_container_width=True):
                st.session_state[input_key] = suggestion
                st.session_state.pop(answer_key, None)
                st.session_state.pop(error_key, None)
                st.rerun()

        st.text_area(
            "Ask a question",
            key=input_key,
            height=90,
            placeholder="e.g. What does this coefficient mean?",
        )

        if st.button("Ask Tutor", key=f"tutor_ask_{page}", type="primary", use_container_width=True):
            question = st.session_state.get(input_key, "").strip()
            if not question:
                st.session_state[error_key] = "Please enter a question first."
                st.session_state.pop(answer_key, None)
            else:
                with st.spinner("Tutor is thinking…"):
                    answer, error = ask_tutor(question, context)
                if error:
                    st.session_state[error_key] = error
                    st.session_state.pop(answer_key, None)
                else:
                    st.session_state[answer_key] = answer
                    st.session_state.pop(error_key, None)

        if st.session_state.get(error_key):
            st.warning(st.session_state[error_key])

        if st.session_state.get(answer_key):
            st.markdown("### 💡 Tutor")
            st.markdown(st.session_state[answer_key])

        st.caption("For sensitive or high-stakes decisions, verify results with primary sources and qualified professionals.")
