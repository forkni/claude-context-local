# Global VSCode Settings Update

**File to edit**: `C:\Users\Inter\AppData\Roaming\Code\User\settings.json`

## Quick Instructions

1. Press `Ctrl+Shift+P` in VSCode
2. Type "Preferences: Open User Settings (JSON)"
3. Apply the changes below
4. Save and reload VSCode

---

## Changes to Make

### 1. Update Python Section

**Find this** (around lines 6-14):
```json
"[python]": {
  "editor.defaultFormatter": "charliermarsh.ruff",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit",
    "source.organizeImports": "explicit"
  }
},
```

**Replace with**:
```json
"[python]": {
  "editor.defaultFormatter": "charliermarsh.ruff",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll": "explicit",
    "source.organizeImports": "explicit"
  }
},
```

**Change**: `source.fixAll.ruff` → `source.fixAll` (let workspace control Ruff-specific settings)

---

### 2. Remove Ruff Configuration Section

**Find and DELETE** (around lines 58-66):
```json
"ruff.configuration": {
  "lint": {
    "per-file-ignores": {
      "*.py": [
        "F821"
      ]
    }
  }
},
```

**Reason**: This is now handled by `pyproject.toml` in each project.

---

### 3. Update Global Code Actions

**Find this** (around lines 108-112):
```json
"editor.codeActionsOnSave": {
  "source.fixAll.ruff": "explicit",
  "source.fixAll.markdownlint": "explicit",
  "source.organizeImports": "explicit"
},
```

**Replace with**:
```json
"editor.codeActionsOnSave": {
  "source.fixAll.markdownlint": "explicit"
},
```

**Changes**:
- Removed `source.fixAll.ruff` (handled by Python-specific section)
- Removed `source.organizeImports` (handled by Python-specific section)
- Kept `source.fixAll.markdownlint` for Markdown files

---

## Final Result

Your global settings should now have:

```json
{
  // ... other settings ...

  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },

  // ... other settings ...

  "editor.codeActionsOnSave": {
    "source.fixAll.markdownlint": "explicit"
  },

  // ... rest of settings ...
  // (ruff.configuration section removed)
}
```

---

## Why These Changes?

1. **No duplicates**: Removed duplicate `codeActionsOnSave` entries
2. **Workspace control**: Let each project's `.vscode/settings.json` control Ruff-specific behavior
3. **Centralized config**: Ruff rules now in `pyproject.toml`, not VSCode settings
4. **Consistent**: Same behavior across CLI tools, VSCode, and CI

---

## Testing

After updating and reloading VSCode:

1. Open a Python file in this project
2. Add extra spaces or mess up imports
3. Save (`Ctrl+S`)
4. Should auto-format and organize imports

If it doesn't work, see `docs/VSCODE_SETUP.md` → Troubleshooting section.
