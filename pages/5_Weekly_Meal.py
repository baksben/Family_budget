import json
import os
from datetime import date, timedelta
from dotenv import load_dotenv

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Weekly Meal Ideas", page_icon="🥗", layout="wide")

load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7)  # weekday: Mon=0

def build_prompt(
    family_size: int,
    dietary_style: str,
    exclusions: str,
    time_budget: str,
    budget_level: str,
    extra_notes: str,
    week_start: str,
) -> str:
    return f"""
You are a nutrition-focused meal planner.

Create a 7-day meal plan starting on {week_start} (Monday to Sunday).
The plan must be:
- Low-fat overall (avoid frying; prefer grilling/baking/steaming; minimal added oils; lean proteins).
- Highly nutritious (whole foods; vegetables; legumes; whole grains; lean proteins).
- Include fruit every day (at least 1 serving/day; can be part of breakfast or meal).
- Practical for a household of {family_size} people.
- Dietary style preference: {dietary_style}.
- Exclusions/allergies: {exclusions if exclusions.strip() else "none"}.
- Time budget: {time_budget}.
- Budget level: {budget_level}.
- Notes: {extra_notes if extra_notes.strip() else "none"}.

Return ONLY valid JSON that matches exactly this schema:

{{
  "week_start": "{week_start}",
  "days": [
    {{
      "day": "Monday",
      "breakfast": {{
        "name": "...",
        "key_ingredients": ["...", "..."],
        "fruit_included": ["..."],
        "prep_time_minutes": 0
      }},
      "lunch": {{
        "name": "...",
        "key_ingredients": ["...", "..."],
        "fruit_included": ["..."],
        "prep_time_minutes": 0
      }},
      "dinner": {{
        "name": "...",
        "key_ingredients": ["...", "..."],
        "fruit_included": ["..."],
        "prep_time_minutes": 0
      }},
      "nutrition_notes": ["1 short bullet", "1 short bullet"]
    }}
  ],
  "overall_tips": ["...", "..."]
}}

Rules:
- Exactly 7 elements in "days", in order Monday..Sunday.
- Each day must include fruit in at least one meal. Put fruit items in that meal’s fruit_included list.
- Keep names simple and family-friendly.
- Keep prep_time_minutes realistic (5–45 typically).
- Do NOT include any text before or after the JSON.
- Do NOT wrap JSON in ``` fences.
""".strip()

def validate_plan(plan: dict) -> tuple[bool, str]:
    if "days" not in plan or not isinstance(plan["days"], list) or len(plan["days"]) != 7:
        return False, "Plan must contain exactly 7 days."
    for i, day in enumerate(plan["days"]):
        expected_day = DAYS[i]
        if day.get("day") != expected_day:
            return False, f"Day {i+1} should be {expected_day}."
        for meal in ["breakfast", "lunch", "dinner"]:
            if meal not in day:
                return False, f"Missing {meal} for {expected_day}."
            fruit = day[meal].get("fruit_included", [])
            # fruit can be empty for a meal, but we need at least one fruit serving in the day overall
        day_fruit = (
            day["breakfast"].get("fruit_included", [])
            + day["lunch"].get("fruit_included", [])
            + day["dinner"].get("fruit_included", [])
        )
        if not day_fruit:
            return False, f"No fruit included on {expected_day}."
    return True, "OK"

# @st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
# def generate_weekly_plan(prompt: str, model: str) -> dict:
#     # Using Responses API style via the OpenAI python client
#     resp = client.responses.create(
#         model=model,
#         input=prompt,
#         # You can set temperature lower for more consistent formatting
#         temperature=0.3,
#     )
#     text = resp.output_text
#     return json.loads(text)

def try_parse_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        return None

def repair_to_json(bad_text: str, model: str) -> dict:
    repair_prompt = f"""
Fix the following so it becomes VALID JSON matching the schema.
Return ONLY the corrected JSON.

BAD OUTPUT:
{bad_text}
""".strip()

    resp = client.responses.create(
        model=model,
        input=repair_prompt,
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.output_text)

@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def generate_weekly_plan(prompt: str, model: str) -> dict:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    text = resp.choices[0].message.content
    return json.loads(text)


def render_day(day_obj: dict):
    st.subheader(day_obj["day"])
    cols = st.columns(3)
    for idx, meal in enumerate(["breakfast", "lunch", "dinner"]):
        with cols[idx]:
            m = day_obj[meal]
            st.markdown(f"**{meal.capitalize()}: {m['name']}**")
            st.caption(f"Prep: {m['prep_time_minutes']} min")
            st.write("**Key ingredients:** " + ", ".join(m["key_ingredients"]))
            st.write("**Fruit:** " + ", ".join(m["fruit_included"]))

    st.write("**Nutrition notes:**")
    for note in day_obj.get("nutrition_notes", []):
        st.write(f"- {note}")

# ---------------- UI ----------------
st.title("🥗 Weekly Meal Ideas (Low-fat, Nutritious, Fruit daily)")

today = date.today()
week_start = next_monday(today)
week_start_str = week_start.isoformat()

with st.sidebar:
    st.header("Preferences")
    family_size = st.number_input("Family size", min_value=1, max_value=12, value=4)
    dietary_style = st.selectbox(
        "Dietary style",
        ["Balanced", "Mediterranean", "High-protein", "Vegetarian", "Pescatarian", "Dairy-free", "Gluten-free"],
        index=1,
    )
    exclusions = st.text_input("Exclusions / allergies (comma-separated)", "")
    time_budget = st.selectbox("Time budget", ["Quick (≤20 min)", "Normal (20–40 min)", "Batch-cook friendly"], index=1)
    budget_level = st.selectbox("Budget level", ["Low", "Medium", "Flexible"], index=1)
    extra_notes = st.text_area("Extra notes", "Prefer simple ingredients and repeat some lunches as leftovers.")
    model = st.selectbox("Model", ["gpt-4.1-mini", "gpt-4.1"], index=0)

st.info(f"Generating a plan for week starting **{week_start_str}** (Monday).")

generate = st.button("Generate weekly meal plan", type="primary")

if generate:
    prompt = build_prompt(
        family_size=family_size,
        dietary_style=dietary_style,
        exclusions=exclusions,
        time_budget=time_budget,
        budget_level=budget_level,
        extra_notes=extra_notes,
        week_start=week_start_str,
    )

    # with st.spinner("Creating your weekly plan..."):
    #     try:
    #         plan = generate_weekly_plan(prompt, model=model)
    #     except json.JSONDecodeError:
    #         st.error("The model response wasn't valid JSON. Try again (or lower temperature).")
    #         st.stop()
    #     except Exception as e:
    #         st.error(f"Error generating plan: {e}")
    #         st.stop()

    with st.spinner("Creating your weekly plan..."):
        try:
            plan = generate_weekly_plan(prompt, model=model)
        except Exception as e:
            st.error(f"Error generating plan: {e}")
            st.stop()


    ok, msg = validate_plan(plan)
    if not ok:
        st.error(f"Plan failed validation: {msg}")
        st.json(plan)
        st.stop()

    st.success("Meal plan ready!")

    # Display
    st.markdown("## Week overview")
    if "overall_tips" in plan:
        for tip in plan["overall_tips"]:
            st.write(f"- {tip}")

    st.markdown("---")

    for d in plan["days"]:
        render_day(d)
        st.markdown("---")

    # Download JSON
    st.download_button(
        "Download plan as JSON",
        data=json.dumps(plan, indent=2),
        file_name=f"meal_plan_{week_start_str}.json",
        mime="application/json",
    )
