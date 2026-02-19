---
description: Deploy landing page to GitHub Pages after making changes to the website/ folder
---

# Deploy Landing Page

After editing files in `website/`, run this workflow to push changes live.

// turbo-all

1. Sync website files to docs folder:
```
Copy-Item -Path "c:\Users\Admin\Desktop\renmaeai\website\index.html" -Destination "c:\Users\Admin\Desktop\renmaeai\docs\index.html" -Force; Copy-Item -Path "c:\Users\Admin\Desktop\renmaeai\website\style.css" -Destination "c:\Users\Admin\Desktop\renmaeai\docs\style.css" -Force
```

2. Stage, commit, and push:
```
cd c:\Users\Admin\Desktop\renmaeai && git add docs/ website/ && git commit -m "update: landing page" && git push origin master
```

3. Landing page will auto-update at: https://baophamvuquoc-cmyk.github.io/renmaeai/ (1-2 min delay)
