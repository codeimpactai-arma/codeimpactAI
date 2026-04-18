import requests
import re
import json


def download_and_parse_scratch(url: str, token: str = None):
    # 1. חילוץ ה-Project ID
    project_id_match = re.search(r'projects/(\d+)', url)
    project_id = project_id_match.group(1) if project_id_match else (url if url.isdigit() else None)

    if not project_id:
        return {"error": "Invalid Scratch URL or ID"}

    # 2. השגת Token (חשוב מאוד לפרויקטים לא משותפים או ישנים)
    if not token:
        try:
            meta_url = f"https://api.scratch.mit.edu/projects/{project_id}"
            meta_res = requests.get(meta_url, timeout=5)
            if meta_res.status_code == 200:
                token = meta_res.json().get('project_token')
        except Exception:
            pass

    # 3. ניסיון הורדה מ-Assets API (תומך ב-Scratch 3.0)
    assets_url = f"https://projects.scratch.mit.edu/{project_id}"
    params = {"token": token} if token else {}

    try:
        response = requests.get(assets_url, params=params, timeout=10)

        # אם נכשל ב-3.0, ננסה להביא את הגרסה הישנה (2.0)
        if response.status_code != 200:
            return {"error": f"Failed to download. Status: {response.status_code}"}

        project_data = response.json()

        # 4. זיהוי גרסת הפרויקט וניתוח (Parsing)
        summary = {
            "project_id": project_id,
            "total_sprites": 0,
            "sprites_details": []
        }

        # --- מקרה א': Scratch 3.0 (שימוש ב-targets) ---
        if 'targets' in project_data:
            summary["total_sprites"] = len(project_data['targets'])
            for target in project_data['targets']:
                blocks = target.get('blocks', {})
                opcodes = [b.get('opcode') for b in blocks.values() if isinstance(b, dict)]

                summary["sprites_details"].append({
                    "name": target.get('name'),
                    "role": "Stage" if target.get('isStage') else "Sprite",
                    "block_count": len([b for b in blocks.values() if isinstance(b, dict)]),
                    "logic_summary": list(set(opcodes))[:15],
                    "variables": list(target.get('variables', {}).keys()),
                    "broadcast_messages": list(target.get('broadcasts', {}).values())
                })

        # --- מקרה ב': Scratch 2.0 (שימוש ב-children - הפרויקט ששלחת!) ---
        elif 'children' in project_data:
            # הוספת הבמה (Stage)
            summary["sprites_details"].append({
                "name": "Stage",
                "role": "Stage",
                "block_count": len(project_data.get('scripts', [])),
                "logic_summary": ["v2_script_detected"],  # ב-2.0 המבנה של הבלוקים הוא רשימות מקוננות
                "variables": [v[0] for v in project_data.get('variables', [])],
                "broadcast_messages": []
            })

            for child in project_data.get('children', []):
                if 'objName' in child:  # זו דמות
                    summary["total_sprites"] += 1
                    summary["sprites_details"].append({
                        "name": child.get('objName'),
                        "role": "Sprite",
                        "block_count": len(child.get('scripts', [])),
                        "logic_summary": ["v2_sprite_detected"],
                        "variables": [v[0] for v in child.get('variables', [])],
                        "broadcast_messages": []
                    })
            summary["total_sprites"] += 1  # +1 עבור הבמה

        return summary

    except Exception as e:
        return {"error": f"Parsing failed: {str(e)}"}