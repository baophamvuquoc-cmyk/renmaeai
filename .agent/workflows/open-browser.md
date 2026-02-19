---
description: How to open URLs in the browser using the user's preferred Chrome profile
---

// turbo-all

When opening any URL for the user, use Google Chrome with their default profile:

```powershell
Start-Process "chrome.exe" -ArgumentList "<URL>"
```

- Always use `chrome.exe` (not `Start-Process <URL>` which opens the system default browser)
- The user's profile name is **Mr. Ernesta** (the default Chrome profile)
- No need to specify `--profile-directory` since it's the default profile
