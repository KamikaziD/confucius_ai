from app.agents.base_agent import BaseAgent
from app.models.agent import AgentType
from app.services.ollama import ollama_service
from typing import Dict, Any, Optional

class OCRAgent(BaseAgent):
    def __init__(self, model: str, system_prompt: str):
        super().__init__(AgentType.OCR, model)
        self.system_prompt = system_prompt
    
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute OCR analysis"""
        text_to_analyze = context.get("text", query)
        
        prompt = f"""Analyze the following text and extract key information based on the user's query: "{query}".
Document Text: "{text_to_analyze}"

Provide your analysis in the following format:
Document Type: [type]
Confidence: [0-1]
Key Information: [bullet points of extracted data]"""
        
        result, duration = await self._measure_execution(
            ollama_service.generate,
            prompt,
            self.system_prompt,
            self.model
        )
        
        return {
            "text": text_to_analyze,
            "analysis": result,
            "confidence": 0.95,
            "detected_type": self._detect_document_type(text_to_analyze),
            "model": self.model,
            "execution_time": duration
        }
    
    def _detect_document_type(self, text: str) -> str:
        """Simple document type detection"""
        text_lower = text.lower()
        if "invoice" in text_lower:
            return "invoice"
        elif "receipt" in text_lower:
            return "receipt"
        elif "contract" in text_lower:
            return "contract"
        elif "report" in text_lower:
            return "report"
        return "general document"
