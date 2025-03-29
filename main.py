import openai
import random
import os
import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Optional

load_dotenv()

client = openai.OpenAI()

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

GPT_MODEL = "gpt-4o-2024-08-06"
CATEGORIES = [
    "Business and Finance",
    "Office and Workplace",
    "Travel and Tourism",
    "Health and Medicine",
    "Shopping and Retail",
    "Technology and Computers",
    "Real Estate and Housing",
    "Human Resources and Management",
    "Marketing and Advertising",
    "Manufacturing and Production",
]

get_word_prompt_template = open(Path("prompts/get_word.txt"), "r").read()
get_word_score_prompt_template = open(Path("prompts/get_word_score.txt"), "r").read()
get_hint_prompt_template = open(Path("prompts/get_hint.txt"), "r").read()


def chat_completion_request(messages, tools=None, tool_choice=None, model=GPT_MODEL):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def detect_multiple_placeholders(sentence):
    pattern = r"_+"
    matches = re.findall(pattern, sentence)
    return len(matches) > 1


def has_duplicates(word_list):
    seen = set()
    for word in word_list:
        word_lower = word.lower()
        if word_lower in seen:
            return True
        seen.add(word_lower)
    return False


def rand_word(word_list: List[str]) -> List[str]:
    if isinstance(word_list, list):
        return random.sample(word_list, 3)
    else:
        raise ValueError("Input should be a list of exactly 20 words.")


class FinalResponse(BaseModel):
    hint: List[dict]
    words: List[dict]
    quiz: dict


def to_final_json(
    word_list: List[str],
    score_list: List[float],
    hint_list: List[str],
    choices: List[str],
) -> FinalResponse:
    in_game_hints = hint_list[:4]
    quiz_question = hint_list[4]

    hints = [
        {"ID": idx + 1, "question": in_game_hints[idx]}
        for idx in range(len(in_game_hints))
    ]

    words = [
        {"ID": idx + 1, "word": word, "score": score}
        for idx, (word, score) in enumerate(zip(word_list, score_list))
    ]

    return FinalResponse(
        hint=hints, words=words, quiz={"question": quiz_question, "choices": choices}
    )


tools = [
    {
        "type": "function",
        "function": {
            "name": "rand_word",
            "description": "Randomly pick a word from the provided list",
            "parameters": {
                "type": "object",
                "properties": {
                    "word_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Python list of 10 words",
                    }
                },
                "required": ["word_list"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_word_score",
            "description": "Get ten word semantic similarity scores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "score_list": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "A list of ten semantic similarity scores between 0 to 1.",
                    }
                },
                "required": ["score_list"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hint",
            "description": "Get five fill-in-the-blank questions where the missing word can be filled in anywhere in the sentence denoted by four underscore symbols.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hint_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Five fill-in-the-blank questions where the missing word can be filled in anywhere in the sentence denoted by four underscore symbols.",
                    }
                },
                "required": ["hint_list"],
            },
        },
    },
]


@app.get("/generate_words", response_model=FinalResponse)
async def generate_words(category_index: Optional[int] = Query(None)):
    if category_index is not None:
        if 0 <= category_index < len(CATEGORIES):
            selected_category = CATEGORIES[category_index]
        else:
            raise HTTPException(status_code=400, detail="Category index out of range")
    else:
        selected_category = random.choice(CATEGORIES)

    get_word_prompt = get_word_prompt_template.replace("<CATEGORY>", selected_category)

    messages = [{"role": "user", "content": get_word_prompt}]

    regen = True
    word_list = None
    quiz_choices = None
    while regen:
        response = chat_completion_request(
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "rand_word"}},
        )
        regen = False
        print(response.choices[0].message.tool_calls)

        try:
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                tool_function_name = tool_calls[0].function.name
                full_word_list = eval(tool_calls[0].function.arguments)["word_list"]
                if tool_function_name == "rand_word":
                    if len(full_word_list) == 10:
                        word_list = full_word_list
                        if has_duplicates(word_list):
                            regen = True
                    else:
                        regen = True
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Response did not contain a list of 10 words",
                )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to parse the response: {str(e)}"
            )

    target_word = word_list[0]
    quiz_choices = [target_word] + rand_word(word_list[1:])
    combined_list = ", ".join(word_list)
    get_word_score_prompt = get_word_score_prompt_template.replace(
        "<TARGET_WORD>", target_word
    ).replace("<WORD_LIST>", combined_list)

    messages = [{"role": "user", "content": get_word_score_prompt}]

    regen = True
    score_list = None
    while regen:
        response = chat_completion_request(
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "get_word_score"}},
        )
        regen = False
        print(response.choices[0].message.tool_calls)

        try:
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                tool_function_name = tool_calls[0].function.name
                score_list = eval(tool_calls[0].function.arguments)["score_list"]
                if score_list:
                    if len(score_list) != 10:
                        regen = True
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to parse the response: {str(e)}"
            )

    get_hint_prompt = (
        get_hint_prompt_template.replace("<TARGET_WORD>", target_word)
        .replace("<WORD_LIST>", combined_list)
        .replace("<INCORRECT_WORD_LIST>", ", ".join(word_list[1:]))
        .replace("<INCORRECT_CHOICES>", ", ".join(quiz_choices[1:]))
    )

    regen = True
    hint_list = None
    while regen:
        messages = [{"role": "user", "content": get_hint_prompt}]
        response = chat_completion_request(
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "get_hint"}},
        )
        regen = False
        print(response.choices[0].message.tool_calls)

        try:
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                tool_function_name = tool_calls[0].function.name
                hint_list = eval(tool_calls[0].function.arguments)["hint_list"]
            if len(hint_list) == 5:
                for i in range(len(hint_list)):
                    if (
                        detect_multiple_placeholders(hint_list[i])
                        or target_word in hint_list[i]
                    ):
                        regen = True
                        break
            else:
                regen = True
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to parse the response: {str(e)}"
            )

    return to_final_json(word_list, score_list, hint_list, quiz_choices)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
