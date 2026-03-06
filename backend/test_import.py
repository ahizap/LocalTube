try:
    from task_queue import task_queue
    print("task_queue OK")
    from main import app
    print("main OK")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
