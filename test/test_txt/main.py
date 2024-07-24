import asyncio
from chat_module import chat

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
