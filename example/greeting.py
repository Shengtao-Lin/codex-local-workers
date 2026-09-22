def build_greeting(name: str) -> str:
    """Build a friendly greeting for a person's name."""
    stripped_name = name.strip()
    if not stripped_name:
        raise ValueError("name must not be blank")
    return f"Hello, {stripped_name}!"
