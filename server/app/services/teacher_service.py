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

    rubric_categories = [cat.get("name") for cat in rubrics]

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
        נתח את הפרויקט בכתובת {project_url} על סמך הקריטריונים והנתונים הבאים.

        ### 1. מחוון הערכה (Rubrics):
        {formatted_rubric_text}

        ### 2. נתוני קוד הפרויקט (Project Summary):
        {project_summary}

        ### הנחיות קריטיות למבנה הפלט:
        1. החזר JSON תקין בלבד, ללא טקסט חופשי לפניו או אחריו.
        2. הציון בשדה "suggested_score" חייב להיות מספר שלם (Integer) בין 0 ל-100.
        3. בשדה "details", השתמש בדיוק בשמות הקטגוריות האלו כמפתחות: {rubric_categories}. לכל קטגוריה תן ציון מ-0 עד 100.
        4. בשדה "suggested_feedback", כתוב משוב בעברית רהוטה כפסקאות זורמות.
        5. חל איסור מוחלט להשתמש במילה 'כותרת' או בנקודות (bullets), כוכביות (*) או מקפים (-) בתחילת שורות.
        6. השתמש בפורמט Markdown להדגשת שמות קטגוריות (למשל **יצירתיות**) והפרד בין נושאים באמצעות ירידת שורה כפולה.

        ### הנחיות פדגוגיות לניתוח:
        1. הצלבת נתונים: השתמש ברשימות ה-`broadcast_messages`, `total_sprites` ו-`logic_summary` כדי לבסס את הציון.
        2. נימוק מבוסס ראיות: עבור כל קריטריון, ציין דוגמה ספציפית מהקוד (שם דמות, הודעת Broadcast או בלוק מסוים).
        3. רמה פדגוגית: קבע האם הפרויקט ברמת "זיהוי", "יישום" או "סינתזה" והסבר מדוע.
        4. חישוב מתמטי: בצע חישוב מדויק של הציון הסופי על בסיס המשקלים המופיעים במחוון. 

        ### פורמט פלט נדרש (JSON):
        {{
            "suggested_score": [הכנס מספר שלם כאן],
            "suggested_feedback": "[הכנס משוב פסקאות ללא בולטים כאן]",
            "details": {{
                {", ".join([f'"{cat}": [ציון]' for cat in rubric_categories])}
            }},
            "evidence_found": ["ראיה 1", "ראיה 2"]
        }}

        התחל את התשובה שלך ב-{{ 
        הציון המומלץ הסופי הוא:
        """

    # 6. שליחה ל-AI
    try:
        ai_response_raw = generate_text(prompt)

        # ניקוי ה-Markdown Blocks אם קיימים
        clean_json = ai_response_raw.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.split("```")[1]
            if clean_json.startswith("json"):
                clean_json = clean_json[4:]

        # --- התיקון הקריטי כאן ---
        # הוספת strict=False מאפשרת לפענח JSON עם תווים מיוחדים בתוך מחרוזות
        ai_response = json.loads(clean_json, strict=False)
        # -----------------------

        raw_score = ai_response.get("suggested_score", 0)
        try:
            final_score = int(raw_score)
        except:
            final_score = 0

        return {
            "suggested_score": final_score,
            "suggested_feedback": ai_response.get("suggested_feedback", "לא ניתן לייצר משוב"),
            "details": ai_response.get("details", {}),
        }
    except Exception as e:
    # בדיקה אם זו שגיאת עומס של גוגל (כמו שקרה לך בלוג)
        error_str = str(e).lower()
        if "503" in error_str or "high demand" in error_str:
            print(f"AI Service busy: {error_str}")
            raise HTTPException(
                status_code=503,
                detail="המודל עמוס כרגע (High Demand). אנא נסו שוב בעוד דקה או שתיים."
            )

        # הדפסה בטוחה של השגיאה (עכשיו ai_response_raw תמיד קיים)
        print(f"AI Error: {str(e)} | Raw response: {ai_response_raw}")
        raise HTTPException(status_code=500, detail=f"שגיאה בעיבוד ה-AI: {str(e)}")


def submit_grade(data: dict):
    update_submission_grade(data["project_id"], data["total_score"], data["feedback"])
    return {"message": "Grade Saved"}


def edit_rubric(assignment_id: str, title: str, class_name: str, criteria: list[dict]):
    return update_assignment(assignment_id, title, class_name, criteria)