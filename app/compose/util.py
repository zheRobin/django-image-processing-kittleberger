import json
def event_stream(data): 
    for e in data:
        dict = json.dumps(e)
        yield f"data:{dict}\n"