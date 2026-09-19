from django.conf import settings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def get_llm(
    temperature=None,
    model=None,
):
    """
    Return an LLM through OpenRouter.

    Any OpenRouter chat model can be selected
    through AUTOHIRE_CHAT_MODEL.
    """

    if temperature is None:
        temperature = settings.AUTOHIRE_AI_TEMPERATURE

    if model is None:
        model = settings.AUTOHIRE_CHAT_MODEL

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        timeout=settings.AUTOHIRE_AI_TIMEOUT,
        max_retries=settings.AUTOHIRE_AI_MAX_RETRIES,
        default_headers={
            "HTTP-Referer": settings.OPENROUTER_SITE_URL,
            "X-OpenRouter-Title": settings.OPENROUTER_APP_NAME,
        },
    )


def get_embeddings(
    model=None,
):
    """
    Return embeddings through OpenRouter.
    """

    if model is None:
        model = settings.AUTOHIRE_EMBED_MODEL

    return OpenAIEmbeddings(
        model=model,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        dimensions=settings.AUTOHIRE_EMBED_DIMENSIONS,
    )


# _CHAT_MODEL = getattr(settings, "AUTOHIRE_CHAT_MODEL", "gpt-4o-mini")
# _EMBED_MODEL = getattr(settings, "AUTOHIRE_EMBED_MODEL", "text-embedding-3-small")

# def get_llm(temperature : float = 0.0):
#     return ChatOpenAI(
#         model=_CHAT_MODEL,
#         temperature=temperature,
#         api_key=settings.OPENAI_API_KEY,
#         timeout=60,
#         max_retries=2,
#     )
 
 
# def get_embeddings():
#     return OpenAIEmbeddings(model=_EMBED_MODEL, api_key=settings.OPENAI_API_KEY)


# _CHAT_MODEL = getattr(
#     settings,
#     "AUTOHIRE_CHAT_MODEL",
#     "gemini-3.6-flash",
# )

# _EMBED_MODEL = getattr(
#     settings,
#     "AUTOHIRE_EMBED_MODEL",
#     "gemini-embedding-001",
# )


# def get_llm(temperature: float = 0.0):

#     return ChatGoogleGenerativeAI(
#         model=_CHAT_MODEL,
#         temperature=temperature,
#         google_api_key=settings.GOOGLE_API_KEY,
#         timeout=settings.AUTOHIRE_AI_TIMEOUT,
#         max_retries=settings.AUTOHIRE_AI_MAX_RETRIES,
#     )
# def get_embeddings():
#     return GoogleGenerativeAIEmbeddings(
#         model=_EMBED_MODEL,
#         google_api_key=settings.GOOGLE_API_KEY,
#         output_dimensionality=1536
#     )