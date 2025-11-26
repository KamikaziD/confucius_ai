from app.agents.base_agent import BaseAgent
from app.models.agent import AgentType
from app.services.ollama import ollama_service
from app.services.file_service import file_service
from typing import Dict, Any, Optional


class OCRAgent(BaseAgent):
    def __init__(self, model: str, system_prompt: str, client_id: Optional[str] = None):
        super().__init__(AgentType.OCR, model, client_id=client_id)
        self.system_prompt = system_prompt

    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute OCR analysis on text and images from context and URLs."""
        context = context or {}
        all_text_parts = [context.get("text", "")]
        all_image_parts = context.get("images", [])

        urls = context.get("urls", [])
        if urls:
            self.report_activity(f"Fetching content from {len(urls)} URLs...")
            try:
                url_files = await file_service.get_files_from_urls(urls)
                processed_url_files = [
                    file_service.read_file_content(f) for f in url_files]
                
                for item in processed_url_files:
                    if item["type"] == "text":
                        all_text_parts.append(item["content"])
                    elif item["type"] == "image":
                        all_image_parts.append(item["content"])
                self.report_activity("URL content fetched successfully.")
            except Exception as e:
                self.report_activity(
                    f"Error fetching URL content: {e}", is_error=True)

        text_to_analyze = "\n\n".join(
            part for part in all_text_parts if part and part.strip())

        if not text_to_analyze.strip() and not all_image_parts:
            text_to_analyze = query
            self.report_activity(
                "No text or image content found, using query as text to analyze.")

        prompt = f"""Analyze the following text and images based on the user's query: "{query}".
Document Text: "{text_to_analyze}"

Provide your analysis in the following format:
Document Type: [type]
Confidence: [0-1]
Key Information: [bullet points of extracted data]"""

        result, duration = await self._measure_execution(
            ollama_service.generate,
            prompt=prompt,
            system_prompt=self.system_prompt,
            model=self.model,
            images=all_image_parts
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
