import json
import requests
import asyncio
import aiohttp

# NOTE: ollama must be running for this to work, start the ollama app or run `ollama serve`
model = "llama3"  # TODO: update this for whatever model you wish to use


#def chat(messages):
#    r = requests.post(
#        "http://0.0.0.0:11434/api/chat",
#        json={"model": "cielo", "messages": messages, "stream": True},
#	stream=True
#    )
#    r.raise_for_status()
#    output = ""
#
#    for line in r.iter_lines():
#        body = json.loads(line)
#        if "error" in body:
#            raise Exception(body["error"])
#        if body.get("done") is False:
#            message = body.get("message", "")
#            content = message.get("content", "")
#            output += content
#            # the response streams one token at a time, print that as we receive it
#            print(content, end="", flush=True)
#
#        if body.get("done", False):
#            message["content"] = output
#            return message
#
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
                
async def main():
    messages = []

    while True:
        user_input = input("Enter a prompt: ")
        if not user_input:
            break
        print()
        messages.append({"role": "user", "content": user_input})
        message = await chat(messages)
        messages.append(message)
        print("\n\n")


if __name__ == "__main__":
    asyncio.run(main())
    
    
    
#import json
#
#import requests
#
#
#
## NOTE: ollama must be running for this to work, start the ollama app or run `ollama serve`
#
#model = 'stablelm-zephyr' # TODO: update this for whatever model you wish to use
#
#
#
#def generate(prompt, context):
#
#    r = requests.post('http://localhost:11434/api/generate',
#
#                      json={
#
#                          'model': model,
#
#                          'prompt': prompt,
#
#                          'context': context,
#
#                      },
#
#                      stream=True)
#
#    r.raise_for_status()
#
#
#
#    for line in r.iter_lines():
#
#        body = json.loads(line)
#
#        response_part = body.get('response', '')
#
#        # the response streams one token at a time, print that as we receive it
#
#        print(response_part, end='', flush=True)
#
#
#
#        if 'error' in body:
#
#            raise Exception(body['error'])
#
#
#
#        if body.get('done', False):
#
#            return body['context']
#
#
#
#def main():
#
#    context = [] # the context stores a conversation history, you can use this to make the model more context aware
#
#    while True:
#
#        user_input = input("Enter a prompt: ")
#
#        if not user_input:
#
#            exit()
#
#        print()
#
#        context = generate(user_input, context)
#
#        print()
#
#
#
#if __name__ == "__main__":
#
#    main()