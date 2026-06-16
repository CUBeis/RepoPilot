from pathlib import Path

IGNORED_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".next",
        ".turbo",
    }
)

SUPPORTED_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".md",
        ".txt",
        ".json",
        ".toml",
        ".yaml",
        ".yml",
        ".html",
        ".css",
        ".sql",
    }
)

LANGUAGE_BY_EXTENSION: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".md": "markdown",
    ".txt": "text",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
}


def get_extension(path: Path) -> str:
    """Return a normalized file extension."""
    return path.suffix.lower()


def detect_language(path: Path) -> str | None:
    """Detect a basic language name from a file extension."""
    return LANGUAGE_BY_EXTENSION.get(get_extension(path))


def is_ignored_directory(directory_name: str) -> bool:
    """Return whether a directory should be skipped while scanning."""
    return directory_name in IGNORED_DIRECTORIES


def is_supported_text_file(path: Path) -> bool:
    """Return whether a file extension is supported for text scanning."""
    return get_extension(path) in SUPPORTED_TEXT_EXTENSIONS
