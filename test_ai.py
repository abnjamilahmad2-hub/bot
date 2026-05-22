import asyncio
from shared.ai_client import ai_client

async def test():
    print("Testing regular chat...")
    resp = await ai_client.chat("You are a bot.", "Say hello.")
    print(f"Response: {resp}")
    
    print("\nTesting json mode...")
    resp_json = await ai_client.chat("You are a bot.", "Return {\"hello\": \"world\"} as JSON", json_mode=True)
    print(f"JSON Response: {resp_json}")
    
    await ai_client.close()

if __name__ == "__main__":
    asyncio.run(test())
