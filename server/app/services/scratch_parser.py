import requests
import re
import json


def download_and_parse_scratch(url: str, token: str = None):
    # חילוץ ID
    project_id_match = re.search(r'projects/(\d+)', url)
    project_id = project_id_match.group(1) if project_id_match else (url if url.isdigit() else None)

    if not project_id:
        return {"error": "Invalid Scratch URL or ID"}

    # השגת Token (אם לא סופק)
    if not token:
        try:
            meta_url = f"https://api.scratch.mit.edu/projects/{project_id}"
            meta_res = requests.get(meta_url, timeout=5)
            if meta_res.status_code == 200:
                token = meta_res.json().get('project_token')
        except Exception:
            pass

    # ניסיון הורדה
    assets_url = f"https://projects.scratch.mit.edu/{project_id}"
    params = {"token": token} if token else {}

    try:
        response = requests.get(assets_url, params=params, timeout=10)
        if response.status_code != 200:
            return {"error": f"Failed to download. Status: {response.status_code}"}

        project_data = response.json()
        summary = {"project_id": project_id, "total_sprites": 0, "sprites_details": []}

        # Scratch 3.0
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
        # Scratch 2.0
        elif 'children' in project_data:
            # ... (המשך הקוד של גרסה 2.0 שכתבנו קודם)
            summary["total_sprites"] = len([c for c in project_data.get('children', []) if 'objName' in c]) + 1
            # (תוודאי שכל הקוד של Scratch 2.0 נמצא כאן כפי שסידרנו)

        return summary
    except Exception as e:
        return {"error": str(e)}