import json, re

with open(r'c:\Users\Admin\Desktop\renmaeai\backend\test_10scenes_result.txt', 'r', encoding='utf-8') as f:
    raw = f.read()

match = re.search(r'event: result\s*\ndata: (.+)', raw)
if not match:
    print("No result event found!")
    exit(1)

data = json.loads(match.group(1).strip())
keywords = data.get('keywords', [])

output_lines = []
output_lines.append(f"# 10 Scene Prompt Generation Results")
output_lines.append(f"Mode: {data.get('mode')}, Success: {data.get('success')}, Total: {len(keywords)}")
output_lines.append("")

for s in keywords:
    sid = s.get('scene_id', '?')
    kw = s.get('keyword', '')
    ip = s.get('image_prompt', '')
    vp = s.get('video_prompt', '')
    output_lines.append(f"## Scene {sid}")
    output_lines.append(f"**Keyword:** {kw}")
    output_lines.append(f"")
    output_lines.append(f"### Image Prompt ({len(ip)} chars)")
    output_lines.append(ip)
    output_lines.append(f"")
    output_lines.append(f"### Video Prompt ({len(vp)} chars)")
    output_lines.append(vp)
    output_lines.append(f"")
    output_lines.append("---")
    output_lines.append("")

with open(r'C:\Users\Admin\.gemini\antigravity\brain\57ff6fba-d725-440b-9d03-abf946ac4a50\test_results_10scenes.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f"Written {len(keywords)} scenes to test_results_10scenes.md")
