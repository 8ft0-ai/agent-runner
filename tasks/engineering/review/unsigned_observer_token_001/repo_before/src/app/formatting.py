def status_line(name, healthy):
    state = "ok" if healthy else "down"
    return f"{name}: {state}"
