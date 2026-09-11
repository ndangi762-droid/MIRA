from pathlib import Path

def test_core_files_exist():
    required = [
        "app/main.py", "app/config.py", "app/core/assistant.py",
        "app/llm/ollama.py", "app/memory/store.py", "app/api/routes.py"
    ]
    for item in required:
        assert Path(item).exists()
