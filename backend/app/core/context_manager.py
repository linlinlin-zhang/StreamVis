class ContextManager:
    def __init__(self):
        self.history = []
        # Mock KV Cache and Vector DB
    
    def add_user_input(self, text):
        self.history.append({"role": "user", "content": text})
    
    def get_recent_context(self, k=5):
        return self.history[-k:]
    
    def get_context_vector(self):
        # Mock vector retrieval
        return [0.1, 0.2, 0.3]
