"""Intent parser for natural language user input."""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from .constants import ACTION_VERBS, FILE_TYPES


class ActionType(Enum):
    CREATE_PDF = "create_pdf"
    READ_PDF = "read_pdf"
    EXPAND_PDF = "expand_pdf"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    CREATE_DOCUMENT = "create_document"
    LIST_FILES = "list_files"
    SEARCH = "search"
    CHAT = "chat"  # Default - no tool needed
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """Parsed intent from user input."""
    action: ActionType = ActionType.CHAT
    source_paths: List[str] = field(default_factory=list)
    target_path: Optional[str] = None
    file_type: Optional[str] = None
    content_hint: Optional[str] = None
    title: Optional[str] = None
    confidence: float = 0.5
    original_text: str = ""
    needs_file_clarification: bool = False
    clarification_hint: Optional[str] = None
    raw_args: Dict[str, Any] = field(default_factory=dict)


class IntentParser:
    """Parse natural language into actionable intents."""
    
    # Pronouns and references that need clarification
    REFERENCES = ["that", "this", "it", "the", "those", "these"]
    REFERENCE_PATTERNS = [
        r"(?:that|this|the)\s+(\w+)",
        r"from\s+(?:my\s+)?(\w+)",
        r"in\s+(?:my\s+)?(\w+)",
    ]
    
    def parse(self, user_input: str) -> Intent:
        """Parse user input into an intent."""
        text = user_input.strip()
        intent = Intent(original_text=text, confidence=0.5)
        
        # Lowercase for matching
        text_lower = text.lower()
        
        # 1. Detect file type
        intent.file_type = self._detect_file_type(text_lower)
        
        # 2. Detect action type
        intent.action = self._detect_action(text_lower, intent.file_type)
        
        # 3. Extract file references
        intent.source_paths = self._extract_file_references(text, text_lower)
        
        # 4. Extract target path if any
        intent.target_path = self._extract_target(text, text_lower)
        
        # 5. Check if we need clarification
        needs_clarification = self._check_needs_clarification(intent, text_lower)
        if needs_clarification:
            intent.needs_file_clarification = True
            intent.clarification_hint = self._get_clarification_hint(intent, text_lower)
        
        # 6. Extract title if creating document
        intent.title = self._extract_title(text)
        
        # 7. Calculate confidence
        intent.confidence = self._calculate_confidence(intent, text_lower)
        
        return intent
    
    def _detect_file_type(self, text: str) -> Optional[str]:
        """Detect the file type mentioned."""
        for file_type, extensions in FILE_TYPES.items():
            if file_type in text:
                return file_type
            # Check for extension mentions
            for ext in extensions:
                if ext.replace(".", "") in text:
                    return file_type
        return None
    
    def _detect_action(self, text: str, file_type: Optional[str]) -> ActionType:
        """Detect what action the user wants."""
        text_lower = text.lower()
        
        # First, check for "extract from PDF" patterns - user wants to extract content from existing
        extract_patterns = [
            "extract", "take out", "pull out", "get from", "read from",
            "convert this", "convert the", "from this pdf", "from the pdf",
            "expand this", "expand the", "improve this", "improve the",
            "enhance this", "enhance the", "create from"
        ]
        
        has_source_reference = any(p in text_lower for p in ["this pdf", "the pdf", "that pdf", "existing", "current"]) or \
                               (any(" " + w + " " in " " + text_lower + " " for w in ["it", "this", "that"]) and file_type == "pdf" and any(p in text_lower for p in ["file", "document", "pdf"]))
        
        # Check for action verbs
        for action_type, verbs in ACTION_VERBS.items():
            for verb in verbs:
                if verb in text_lower:
                    # Map to ActionType
                    if action_type == "create":
                        # CRITICAL: Distinguish between creating from scratch vs from existing PDF
                        is_extraction = any(p in text_lower for p in extract_patterns)
                        if is_extraction or has_source_reference:
                            return ActionType.EXPAND_PDF
                        if file_type == "pdf" or "pdf" in text:
                            return ActionType.CREATE_PDF
                        return ActionType.CREATE_DOCUMENT
                    elif action_type == "read":
                        if file_type == "pdf" or "pdf" in text:
                            return ActionType.READ_PDF
                        return ActionType.READ_FILE
                    elif action_type == "expand":
                        return ActionType.EXPAND_PDF
                    elif action_type == "convert":
                        return ActionType.EXPAND_PDF
                    elif action_type == "write":
                        return ActionType.WRITE_FILE
                    elif action_type == "search":
                        return ActionType.SEARCH
        
        # If user mentions "pdf" with no clear action but has source reference context, default to EXPAND
        if file_type == "pdf" and has_source_reference:
            return ActionType.EXPAND_PDF
        
        # Default to chat if no action detected
        return ActionType.CHAT
    
    def _extract_file_references(self, text: str, text_lower: str) -> List[str]:
        """Extract file paths or references from text."""
        paths = []
        
        # 1. Find explicit Windows paths
        path_patterns = [
            r'[A-Za-z]:\\[^\s<>"|?*]+',  # C:\path\to\file
            r'"[^"]+\.(?:pdf|docx|txt|xlsx)"',  # "quoted path"
            r"'[^']+\.(?:pdf|docx|txt|xlsx)'",  # 'quoted path'
        ]
        
        for pattern in path_patterns:
            matches = re.findall(pattern, text)
            paths.extend(matches)
        
        # 2. Look for Downloads/Desktop/Documents references
        common_dirs = ["downloads", "desktop", "documents", "pictures"]
        for dir_name in common_dirs:
            if dir_name in text_lower:
                # Extract potential filename
                parts = text_lower.split(dir_name)
                if len(parts) > 1:
                    potential = parts[1].strip()
                    if potential:
                        # Clean up
                        potential = re.sub(r'[^\w\s\-\.]', '', potential)
                        paths.append(f"~{dir_name}/{potential}")
        
        # 3. Look for quoted filenames
        quoted = re.findall(r'"([^"]+)"', text)
        paths.extend(quoted)
        
        return paths
    
    def _extract_target(self, text: str, text_lower: str) -> Optional[str]:
        """Extract target/output path from text."""
        # Look for "as", "to", "save as", "output"
        output_keywords = ["save as", "output to", "as ", "named "]
        
        for keyword in output_keywords:
            if keyword in text_lower:
                idx = text_lower.find(keyword) + len(keyword)
                remaining = text[idx:].strip()
                # Get the next tokenized chunk
                target = remaining.split()[0] if remaining.split() else ""
                if target:
                    return target
        return None
    
    def _check_needs_clarification(self, intent: Intent, text_lower: str) -> bool:
        """Check if we need user clarification for file paths."""
        # No explicit path but mentions a file
        if intent.action in [ActionType.EXPAND_PDF, ActionType.READ_PDF]:
            if not intent.source_paths and any(ref in text_lower for ref in self.REFERENCES):
                return True
            if not intent.source_paths and intent.file_type:
                return True
        
        # For CREATE_PDF: check if user mentioned a source file implicitly
        if intent.action == ActionType.CREATE_PDF:
            # If user says "make a PDF" without source, they likely want to create from scratch
            # But if they say "make PDF from this" or mention "this pdf" etc, need clarification
            has_implicit_source = any(p in text_lower for p in ["this", "that", "existing", "current", "from this", "from the"])
            if has_implicit_source and not intent.source_paths:
                return True
        
        return False
    
    def _get_clarification_hint(self, intent: Intent, text_lower: str) -> str:
        """Get hint for what to ask user."""
        # Check for specific patterns to give better hints
        if intent.action == ActionType.CREATE_PDF:
            # User wants to create a PDF - check if they want from scratch or from existing
            has_source_ref = any(p in text_lower for p in ["this", "that", "existing", "from"])
            if has_source_ref:
                return "pdf_source_or_scratch"  # Special marker
        
        if "downloads" in text_lower:
            return "downloads"
        elif "desktop" in text_lower:
            return "desktop"
        elif "documents" in text_lower:
            return "documents"
        elif intent.file_type:
            return f"{intent.file_type} files"
        return "files"
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract potential title from text."""
        # Look for quoted text that could be a title
        quoted = re.findall(r'"([^"]+)"', text)
        if quoted:
            return quoted[0]
        
        # Look for "titled" or "called"
        titled_match = re.search(r"(?:titled|called|named)\s+[\"']?([^\"']+)[\"']?", text, re.IGNORECASE)
        if titled_match:
            return titled_match.group(1).strip()
        
        return None
    
    def _calculate_confidence(self, intent: Intent, text_lower: str) -> float:
        """Calculate confidence score for the intent."""
        confidence = 0.5
        
        # Higher confidence with explicit paths
        if intent.source_paths:
            confidence += 0.3
        
        # Higher confidence with clear action verb
        for action_list in ACTION_VERBS.values():
            if any(verb in text_lower for verb in action_list):
                confidence += 0.2
                break
        
        # Lower confidence if needing clarification
        if intent.needs_file_clarification:
            confidence -= 0.2
        
        return max(0.0, min(1.0, confidence))
    
    def intent_to_workflow_args(self, intent: Intent) -> Dict[str, Any]:
        """Convert intent to workflow planner arguments."""
        args = {}
        
        if intent.action == ActionType.EXPAND_PDF:
            if intent.source_paths:
                args["source_pdf"] = intent.source_paths[0]
            args["output"] = intent.target_path or "expanded.pdf"
        elif intent.action == ActionType.CREATE_PDF:
            if intent.source_paths:
                args["source_pdf"] = intent.source_paths[0]
            args["output"] = intent.target_path or "document.pdf"
        elif intent.action == ActionType.READ_PDF:
            if intent.source_paths:
                args["file"] = intent.source_paths[0]
        elif intent.action == ActionType.WRITE_FILE:
            args["output"] = intent.target_path or "document.txt"
            if intent.content_hint:
                args["content"] = intent.content_hint
        
        return args
