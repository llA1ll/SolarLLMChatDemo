# from https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps

import streamlit as st
from langchain_upstage import ChatUpstage

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage

from solar_util import initialize_solar_llm

from solar_util import prompt_engineering

import re
import json

jai = ChatUpstage(model=st.secrets["JAI_MODEL_NAME"], base_url=st.secrets["JAI_BASE_URL"], api_key=st.secrets["JAI_API_KEY"])
solar_pro = ChatUpstage(model="solar-pro")

st.set_page_config(page_title="Chat")
st.title("SolarLLM")


def is_korean(text):
    return re.search(r'[가-힣]', text) is not None


def korean_to_thai(text):
    translate_prompt = PromptTemplate(
        template="""You are a language translator. Translate the following text from Korean to Thai.
Here are some examples:

Korean: 안녕하세요
{{"translation": "สวัสดีครับ/ค่ะ"}}

Korean: 감사합니다
{{"translation": "ขอบคุณครับ/ค่ะ"}}

Korean: 맛있어요
{{"translation": "อร่อยครับ/ค่ะ"}}

Now translate this:
---
Korean: {text}
---
Response format:
{{"translation": "Thai translation here"}}""",
        input_variables=["text"]
    )
    chain = translate_prompt | jai | StrOutputParser()
    result = chain.invoke({"text": text})
    try:
        return json.loads(result)["translation"]
    except json.JSONDecodeError:
        st.error("Failed to parse translation response")
        return result

def thai_to_korean(text):
    translate_prompt = PromptTemplate(
        template="""You are a language translator. Translate the following text from Thai to Korean.
Here are some examples:

Thai: สวัสดีครับ/ค่ะ
{{"translation": "안녕하세요"}}

Thai: ขอบคุณครับ/ค่ะ
{{"translation": "감사합니다"}}

Thai: อร่อยครับ/ค่ะ
{{"translation": "맛있어요"}}

Now translate this:
---
Thai: {text}
---
Response format:
{{"translation": "Korean translation here"}}""",
        input_variables=["text"]
    )
    chain = translate_prompt | solar_pro | StrOutputParser()
    result = chain.invoke({"text": text})
    try:
        return json.loads(result)["translation"]
    except json.JSONDecodeError:
        st.error("Failed to parse translation response")
        return result

chat_with_history_prompt = ChatPromptTemplate.from_messages(
    [
        ("human", """You are Solar, a smart chatbot by Upstage, loved by many people. 
         Be smart, cheerful, and fun. Give engaging answers and avoid inappropriate language.
         reply in the same language of the user query.
         Solar is now being connected with a human."""),
        MessagesPlaceholder("chat_history"),
        ("human", "{user_query}"),
    ]
)



def get_response(user_query, chat_history):
    chain = chat_with_history_prompt | jai | StrOutputParser()

    return chain.stream(
            {
                "chat_history": chat_history,
                "user_query": user_query,
            }
        )


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    role = "AI" if isinstance(message, AIMessage) else "Human"
    with st.chat_message(role):
        st.markdown(message.content)

enhance_prompt = st.toggle("Enhance prompt", False)
if prompt := st.chat_input("What is up?"):
    # Check if input is Korean and translate if needed
    if is_korean(prompt):
        with st.status("Translating Korean to Thai..."):
            prompt = korean_to_thai(prompt)
            st.write(f"Translated to Thai: {prompt}")

    if enhance_prompt:
        with st.status("Prompt engineering..."):
            new_prompt = prompt_engineering(prompt, st.session_state.messages)
            st.write(new_prompt)

        if 'enhanced_prompt' in new_prompt:
            prompt = new_prompt['enhanced_prompt']
 
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = st.write_stream(get_response(prompt, st.session_state.messages))
        korean_response = thai_to_korean(response)
        st.write(korean_response)


