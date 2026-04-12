import json
import random
from typing import List, Any

from fastapi import HTTPException

from ..repositories import rubrics_repo
from ..repositories.projects_repo import list_submissions_by_student, update_submission_grade
from ..repositories.rubrics_repo import insert_assignment, list_all_assignments, get_assignment, \
    update_assignment
from ..repositories.users_repo import list_students
from ..services.gemini_client import generate_text
from ..services.scratch_parser import download_and_parse_scratch


def get_students():
    students = list_students()
    for s in students:
        subs = list_submissions_by_student(s["id"])
        s["project_count"] = len(subs)
    return students

def create_rubric(teacher_id: str, title: str, class_name: str, criteria: list[dict]):
    # קריאה לרפוזיטורי
    return rubrics_repo.insert_assignment(teacher_id, title, class_name, criteria)

def get_rubrics():
    return list_all_assignments()


def get_student_projects(student_id: str):
    submissions = list_submissions_by_student(student_id)
    all_assigns = {a["id"]: a["title"] for a in list_all_assignments()}
    for sub in submissions:
        aid = sub.get("assignment_id")
        sub["title"] = all_assigns.get(aid, "Unknown Assignment")
    return submissions


def analyze_ai(project_url: str, rubrics: List[Any]):
    """
    מנתחת פרויקט סקראץ' בעזרת AI על בסיס רשימת רובריקות שנשלחה מהקליאנט.
    """
    # 1. עיבוד רשימת הרובריקות שהתקבלה מהבקשה
    # אנחנו רצים על הרשימה כדי לוודא שכל המידע (שם, משקל ותתי-קריטריונים) עובר
    formatted_rubric_text = ""
    for idx, category in enumerate(rubrics, 1):
        cat_name = category.get("name")
        cat_weight = category.get("weight")

        formatted_rubric_text += f"\n{idx}. {cat_name} (משקל {cat_weight}%):\n"

        sub_criteria = category.get("sub_criteria", [])
        for sub in sub_criteria:
            sub_name = sub.get("name")
            sub_weight = sub.get("weight")
            formatted_rubric_text += f"   - {sub_name} (משקל פנימי בתוך הקטגוריה: {sub_weight}%)\n"

    # 3. ניתוח קוד ה-Scratch (הורדת ה-JSON)
    try:
        project_summary = download_and_parse_scratch(project_url)
        print("\n" + "=" * 50)
        print("SCRATCH PROJECT SUMMARY LOG:")
        print(json.dumps(project_summary, ensure_ascii=False, indent=4))
        print("=" * 50 + "\n")
        # -----------------------
    except Exception as e:
        project_summary = f"Could not parse blocks. Error: {str(e)}"

    prompt = f"""
    עליך לשמש כמעריך פדגוגי מומחה ל-Scratch המנתח פרויקטים לעומק.
    נתח את הפרויקט בכתובת {project_url} על סמך הקריטריונים הבאים.

    ### מחוון הערכה (Rubrics):
    {formatted_rubric_text}

    ### נתוני קוד הפרויקט (Project Summary):
    {project_summary}

    ### הנחיות עבודה למשוב:
    1. הצלבת נתונים: השתמש ברשימת ה-`broadcast_messages` ו-`total_sprites` מתוך נתוני הקוד כדי לקבוע את הציון בקטגוריית "ניהול אירועים ומסרים" ו"מספר אובייקטים".
    2. נימוק מבוסס ראיות: עבור כל קריטריון, ציין דוגמה ספציפית (שם של דמות, הודעת Broadcast ספציפית או בלוק מיוחד) שתומכת בציון שנתת.
    3. ניתוח פדגוגי: הסבר בעברית רהוטה מדוע הפרויקט נמצא ברמת "יישום" או "סינטזה" על סמך מורכבות הבלוקים.
    4. שקלול מתמטי: בצע חישוב מדויק לפי המשקלים (יצירתיות 30%, שימושיות 30%, קוד 40%).
    5. שקלול מתמטי מדויק: עליך לחשב את הציון הסופי (0-100) על בסיס המשקלים המדויקים המופיעים במחוון לעיל.

    ### פורמט פלט נדרש (JSON בלבד):
    {{
        "suggested_score": 85,
        "suggested_feedback": "כותרת: יצירתיות... [נימוק]. כותרת: שימושיות... [נימוק]. כותרת: קוד... [נימוק].",
        "details": {{
            "innovation": 8,
            "ux": 5,
            "messages_management": 10,
            "independent_learning": 7
        }},
        "evidence_found": ["שמות הבלוקים או המסרים שהשפיעו על הציון"]
    }}
    """

    # 6. שליחה ל-AI
    try:
        ai_response_raw = generate_text(prompt)
        clean_json = ai_response_raw.replace("```json", "").replace("```", "").strip()
        ai_response = json.loads(clean_json)
    except Exception as e:
        error_msg = str(e)
        if "503" in error_msg or "high demand" in error_msg:
            detail = "המודל עמוס כרגע (שגיאה 503). אנא נסו שוב בעוד דקה."
        else:
            detail = f"שגיאה בעיבוד ה-AI: {error_msg}"
        raise HTTPException(status_code=500, detail=detail)
    return {
        "suggested_score": ai_response.get("suggested_score", 0),
        "suggested_feedback": ai_response.get("suggested_feedback", "לא ניתן לייצר משוב"),
        "details": ai_response.get("details", {}),
    }


def submit_grade(data: dict):
    update_submission_grade(data["project_id"], data["total_score"], data["feedback"])
    return {"message": "Grade Saved"}


def edit_rubric(assignment_id: str, title: str, class_name: str, criteria: list[dict]):
    return update_assignment(assignment_id, title, class_name, criteria)