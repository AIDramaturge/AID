import os
from dotenv import load_dotenv
from openai import OpenAI

# Načítaj API kľúč z .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Inicializuj klienta OpenAI
client = OpenAI(api_key=api_key)

# Tvoj dramaturgický prompt
BASE_PROMPT = """
You are an expert dramaturg trained in Anglo-American dramaturgy. Analyze the following dramatic text in full detail. Follow the structure below precisely. For each section, answer every subquestion individually and completely. Use bullet points or numbering. Do not skip any part. Where appropriate, provide direct examples from the text.

---

### I. CHARACTER ANALYSIS

For each major and supporting character:

1. What are their main personality traits and inner life?
2. What is their external goal?
3. What is their internal need (often unconscious)?
4. How do they relate to other characters?
5. Do they evolve over time (character arc)? If so, how?
6. What is their dramatic function (e.g., protagonist, antagonist, mentor, foil)?

**Format your response as:**
- Patrick:
  1. ...
  2. ...
- Father John:
  1. ...
  2. ...
(etc.)

---

### II. PLOT STRUCTURE

1. Identify the following beats: setup, inciting incident, major developments, climax, and resolution.
2. Are the acts well-balanced? Is there a clear midpoint and escalation?
3. How do character decisions drive the plot forward?
4. Are there subplots? If yes, what is their function?

**Provide a chronological outline of the key events.**

---

### III. STORY EVALUATION

1. Is the story original? Why or why not?
2. Is it coherent and causally logical?
3. Are there strong turning points?
4. Where does the pacing feel too slow or too fast?
5. Could anything be cut or merged?

---

### IV. VISUAL STORYTELLING

1. Identify scenes or moments with strong visual or symbolic power.
2. Are there moments that lack visual clarity or impact?
3. Are sensory details (sight, sound, space, movement) used well?
4. Suggest one or two visually compelling additions that could improve stage effectiveness.

---

### V. DIALOGUE QUALITY

1. Does the dialogue reflect each character's unique voice and worldview?
2. Are there moments of subtext, tension, or surprise?
3. Which lines feel too expositional or flat?
4. Suggest specific dialogue that could be sharpened or rewritten.

---

### VI. THEMATIC COHERENCE

1. What is the central theme (or themes)?
2. How is it reflected in the plot, dialogue, and character choices?
3. Are there moments where the theme is unclear or undermined?
4. Suggest ways to reinforce the theme (symbolism, repetition, etc.).

---

### VII. EMOTIONAL IMPACT

1. Which scenes carry the strongest emotional weight? Why?
2. Where does the emotional intensity lag?
3. Are the stakes clear and rising?
4. Suggest a moment where emotional connection could be deepened (through vulnerability, surprise, or loss).

---

### VIII. DRAMATIC STRUCTURE

1. Does each scene serve a clear function in the overall narrative?
2. Are there any scenes that feel redundant, too long, or disconnected?
3. Does tension rise consistently?
4. Suggest changes to scene order, length, or rhythm to improve structure.

---

### IX. CONFLICT (For each main character)

**Respond separately for each character.**

1. Identify internal conflicts (values vs. desires).
2. Identify external conflicts (characters, institutions, society).
3. Are these conflicts dramatized or only mentioned?
4. Rate the strength of conflict: Low / Medium / High – and justify.
5. Does the conflict evolve or shift over time?

---

### X. TOP 3 GLOBAL SUGGESTIONS

List the three most impactful changes that would improve this dramatic work as a whole. Explain briefly why each would help.
---

Begin analysis of the following dramatic text:

{input_text}

"""

def run_aid_analysis(text: str):
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
                "role": "user",
                "content": BASE_PROMPT.replace("{input_text}", text)
            }
        ],
        temperature=0.3–0.5,
        max_tokens=8192
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    with open("libretto_sample.txt", "r", encoding="utf-8") as f:
        input_text = f.read()

    result = run_aid_analysis(input_text)
    print(result)