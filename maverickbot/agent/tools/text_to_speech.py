"""Text to speech tool."""
from typing import Any, Dict
from .base import Tool, ToolResult


class TextToSpeechTool(Tool):
    """Tool for converting text to speech (audio)."""

    def __init__(self):
        super().__init__(
            name="text_to_speech",
            description="Convert text to audio file. Input: JSON with 'text', 'output' (mp3 file), 'lang' (language code).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from gtts import gTTS
            
            text = kwargs.get("text", "")
            output = kwargs.get("output", "speech.mp3")
            lang = kwargs.get("lang", "en")
            
            if not text:
                return ToolResult(success=False, result=None, error="No text specified")
            
            tts = gTTS(text=text, lang=lang)
            tts.save(output)
            
            return ToolResult(success=True, result=f"Created {output}")
        except ImportError:
            return ToolResult(success=False, result=None, error="gTTS not installed. Run: pip install gTTS")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to convert to speech"},
                "output": {"type": "string", "description": "Output MP3 filename"},
                "lang": {"type": "string", "description": "Language code (e.g., en, es, fr)"}
            },
            "required": ["text"]
        }