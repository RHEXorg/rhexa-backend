import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import generate_answer

def test():
    try:
        res = generate_answer(
            organization_id=1,
            query="hello",
            conversation_history=[],
            document_ids=None,
            database_ids=None
        )
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test()
