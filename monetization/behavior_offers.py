def focus_to_text(focus: dict) -> str:
    mode = (focus or {}).get("mode")
    exam = (focus or {}).get("exam")
    subject = (focus or {}).get("subject")
    if not mode:
        return ""
    if mode == "ege":
        parts = []
        if exam:
            parts.append(exam.upper())
        if subject:
            parts.append(subject)
        return "ОГЭ/ЕГЭ: " + " • ".join(parts) if parts else "ОГЭ/ЕГЭ"
    if mode == "study":
        return "Учёба/ДЗ"
    if mode == "chill":
        return "Игры/Отвлечься"
    return str(mode)
