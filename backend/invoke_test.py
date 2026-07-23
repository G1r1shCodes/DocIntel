import asyncio
from dotenv import load_dotenv
load_dotenv()
from database.session import SessionLocal
from api.chat_router import process_chat_query, ChatQueryRequest
from pipeline.retrieval import retriever_instance

async def main():
    retriever_instance.load()
    db = SessionLocal()
    try:
        # Mock user
        current_user = {"user_id": "test_1", "username": "Test User", "role": "Admin"}
        req = ChatQueryRequest(query="what is name of the candidate")
        res = await process_chat_query(req, db, current_user)
        print("SUCCESS:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
