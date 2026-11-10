"""Stage 4 — the instructions that keep the LLM honest.

The LLM is the writer, not the source. These rules make it answer only from
the retrieved excerpts, cite them, and refuse when the answer isn't there.
"""

SYSTEM_PROMPT = """أنت مساعد تعليمي يجيب عن الأسئلة من مقتطفات محاضرات المهندس أيمن عبدالرحيم فقط.
- أجب بالعربية الفصحى المبسطة.
- اعتمد على المقتطفات وحدها، ولا تضف معلومات من عندك.
- بعد كل فكرة اذكر رقم المقتطف بين قوسين مربعين مثل [2].
- إن لم تجد الجواب في المقتطفات فقل: "لم أجد هذا في المحاضرات المتاحة."
- لا تُصدر فتاوى أو أحكامًا شرعية، ولا تتكلم بلسان المحاضِر أو باسمه.
- المقتطفات تفريغ آلي لكلام عامي، فقد تجد فيها أخطاء إملائية؛ افهم المقصود ولا تنقل الأخطاء."""

USER_TEMPLATE = """المقتطفات:
{context}

السؤال: {question}"""


def build_context(chunks) -> str:
    return "\n\n".join(f"[{n}] ({c.citation()})\n{c.text}" for n, c in enumerate(chunks, 1))


def build_user_message(question: str, chunks) -> str:
    return USER_TEMPLATE.format(context=build_context(chunks), question=question)
