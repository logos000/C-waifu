import json
import aiohttp

async def chat(messages):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://127.0.0.1:11434/api/chat",
            json={"model": "cielo", "messages": messages, "stream": True},
        ) as response:
            response.raise_for_status()
            output = ""
            
            async for line in response.content:
                body = json.loads(line)
                if "error" in body:
                    raise Exception(body["error"])
                if body.get("done") is False:
                    message = body.get("message", "")
                    content = message.get("content", "")
                    output += content
                    # the response streams one token at a time, print that as we receive it
                    print(content, end="", flush=True)

                if body.get("done", False):
                    message["content"] = output
                    return message
