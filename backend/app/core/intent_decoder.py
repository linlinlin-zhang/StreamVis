import random

class IntentDecoder:
    def __init__(self):
        pass
    
    def detect(self, text, context):
        # Mock intent detection logic
        # In real implementation, this would use a LoRA model
        # For demo, trigger visualization if specific keywords are present
        # This is strictly for the mock, contrary to the report's "Keyword Detection" critique, 
        # but necessary for a skeleton without a trained model.
        triggers = ["chart", "plot", "graph", "visualize", "show"]
        is_visual = any(trigger in text.lower() for trigger in triggers)
        
        return {
            "type": "request-create" if is_visual else "inform",
            "visual_necessity_score": 0.8 if is_visual else 0.1,
            "entities": []
        }
