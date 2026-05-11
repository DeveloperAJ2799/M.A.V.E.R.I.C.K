"""UX integration layer for the agent - with thinking capabilities."""
import asyncio
import os
import re
from typing import Optional, List, Dict, Any, Tuple
from loguru import logger

from .user_input import IntentParser, Intent, ActionType
from .file_finder import FileFinder
from .confirm import ConfirmationUI, ConfirmationContext, ConfirmationResult
from .friendly import FriendlyResponse
from ..agent.thinking_agent import ThinkingAgent, ExecutionMode


class UXAgent:
    """Agent wrapper with UX-first processing - uses thinking for better understanding."""
    
    def __init__(self, agent_runner):
        self.agent = agent_runner
        self.intent_parser = IntentParser()
        self.file_finder = FileFinder()
        self.confirm_ui = ConfirmationUI()
        self.friendly = FriendlyResponse()
        
        # Thinking agent for deep analysis
        self.thinking_agent: Optional[ThinkingAgent] = None
        
        # State
        self.pending_files: List[str] = []
        self.last_intent: Optional[Intent] = None
        self.awaiting_confirmation: bool = False
        self.awaiting_file_selection: bool = False
        self.last_file_candidates: List[Any] = []
        self.last_plan: Optional[Any] = None
    
    def init_thinking(self, tool_registry, llm_provider):
        """Initialize the thinking agent with tool registry and LLM."""
        self.thinking_agent = ThinkingAgent(tool_registry, llm_provider)
    
    async def process(self, user_input: str) -> str:
        """Process user input with deep thinking first."""
        
        # Handle file selection flow
        if self.awaiting_file_selection:
            return await self._handle_file_selection(user_input)

        # Handle confirmation
        if self.awaiting_confirmation:
            return await self._handle_confirmation(user_input)

        # Check for special commands
        if user_input.strip().lower().startswith("/plan"):
            return await self._handle_plan_command(user_input)
        
        # Check for /think command
        if user_input.strip().lower().startswith("/think"):
            return await self._handle_think_command(user_input)

        # Extract any file paths from input
        paths = self._extract_paths(user_input)
        if paths:
            for p in paths:
                if p not in self.pending_files:
                    self.pending_files.append(p)
            if self._is_path_only_input(user_input, paths):
                return "Got it! I've saved that file. What would you like me to do with it?"
        
        # Use thinking agent for deep analysis (if available)
        # Skip thinking for now - go directly to intent-based for speed
        return await self._process_intent_based(user_input)
    
    async def _process_with_thinking(self, user_input: str) -> str:
        """Process using the thinking agent - deeper understanding."""
        
        # Detect mode from input
        mode = self._detect_mode(user_input)
        
        try:
            # Get thinking result
            result, plan = await self.thinking_agent.process(user_input)
            
            self.last_plan = plan
            
            if mode == ExecutionMode.PLAN:
                return result
            
            if mode == ExecutionMode.THINK_ONLY:
                return result
            
            # Execute mode - check if needs clarification
            if plan.needs_clarification:
                return self._ask_clarification(plan)
            
            # Check if tool is valid
            if not plan.tool_to_use or plan.tool_to_use == "chat":
                return await self.agent.chat(user_input, skip_workflow=True)
            
            # Execute directly
            return await self._execute_plan(plan, user_input)
        except Exception as e:
            # Fall back to intent-based
            return await self._process_intent_based(user_input)
    
    def _detect_mode(self, text: str) -> ExecutionMode:
        """Detect execution mode from input."""
        text_lower = text.lower().strip()
        
        if text_lower.startswith("/plan") or "show your plan" in text_lower:
            return ExecutionMode.PLAN
        if text_lower.startswith("/think") or text_lower.startswith("analyze"):
            return ExecutionMode.THINK_ONLY
        
        return ExecutionMode.EXECUTE
    
    def _ask_clarification(self, plan) -> str:
        """Ask user for clarification."""
        if not plan.clarification_questions:
            return "I need some clarification. Could you provide more details?"
        
        lines = ["I need some clarification:", ""]
        for i, q in enumerate(plan.clarification_questions, 1):
            lines.append(f"  {i}. {q}")
        return "\n".join(lines)
    
    async def _execute_plan(self, plan, original_input: str) -> str:
        """Execute the plan directly without asking."""
        
        tool_name = plan.tool_to_use
        args = plan.arguments.copy()
        
        # Check for valid tool - if chat or empty, use main agent
        if not tool_name or tool_name == "chat":
            return await self.agent.chat(original_input, skip_workflow=True)
        
        # Route to Downloads if mentioned
        if any(w in original_input.lower() for w in ["downloads", "download"]):
            from pathlib import Path
            args["output"] = str(Path.home() / "Downloads" / "output.pdf")
        
        # Ensure output path
        if "output" in args and not os.path.isabs(args["output"]):
            args["output"] = os.path.abspath(args["output"])
        
        try:
            result = await self.agent.tool_registry.execute(tool_name, **args)
            
            if result.success:
                return self.friendly.format_success(tool_name, result.result, args.get("output"))
            else:
                repaired = await self._try_repair(tool_name, args, result.error)
                if repaired:
                    return repaired
                return self.friendly.format_error(tool_name, result.error or "Unknown error")
        except Exception as e:
            return self.friendly.format_error(tool_name, str(e))
    
    async def _enrich_with_context(self, args: Dict, user_input: str) -> Dict:
        """Enrich arguments with pending files and context."""
        
        text_lower = user_input.lower()
        
        # Check for source_pdf argument that needs filling
        if "source_pdf" in args:
            source = args.get("source_pdf", "")
            
            # If source is empty or doesn't exist, try pending files
            if not source or not os.path.exists(source):
                if self.pending_files:
                    # Find a valid PDF in pending
                    for p in reversed(self.pending_files):
                        if os.path.exists(p) and p.lower().endswith('.pdf'):
                            args["source_pdf"] = p
                            break
        
        # Check for file argument
        if "file" in args and not args.get("file"):
            if self.pending_files:
                for p in reversed(self.pending_files):
                    if os.path.exists(p):
                        args["file"] = p
                        break
        
        return args
    
    async def _try_repair(self, tool_name: str, args: Dict, error: str) -> Optional[str]:
        """Try to repair failed execution."""
        
        error_lower = error.lower()
        
        # File not found - try different path
        if "not found" in error_lower or "does not exist" in error_lower:
            if "source_pdf" in args:
                candidates = self.file_finder.find(hint="", file_type="pdf", max_results=3)
                if candidates:
                    args["source_pdf"] = str(candidates[0].path)
                    try:
                        result = await self.agent.tool_registry.execute(tool_name, **args)
                        if result.success:
                            return self.friendly.format_success(tool_name, result.result, args.get("output"))
                    except:
                        pass
        
        return None
    
    async def _handle_plan_command(self, user_input: str) -> str:
        """Handle /plan command - show thinking and plan."""
        user_input = user_input.replace("/plan", "").strip()
        if not user_input:
            return "Please provide what you want me to do. Example: /plan create a PDF from my document"
        
        if not self.thinking_agent:
            return "Thinking not available. Using default processing."
        
        # Force plan mode
        original_detect = self.thinking_agent._detect_mode
        self.thinking_agent._detect_mode = lambda x: ExecutionMode.PLAN
        
        result, _ = await self.thinking_agent.process(user_input)
        
        self.thinking_agent._detect_mode = original_detect
        
        return result + "\n\nShall I execute this plan? (yes/no)"
    
    async def _handle_think_command(self, user_input: str) -> str:
        """Handle /think command - analyze only, don't execute."""
        user_input = user_input.replace("/think", "").strip()
        if not user_input:
            return "Please provide what you want me to analyze. Example: /think what should I do with this file"
        
        if not self.thinking_agent:
            return "Thinking not available."
        
        # Force think mode
        original_detect = self.thinking_agent._detect_mode
        self.thinking_agent._detect_mode = lambda x: ExecutionMode.THINK_ONLY
        
        result, _ = await self.thinking_agent.process(user_input)
        
        self.thinking_agent._detect_mode = original_detect
        
        return result
    
    async def _process_intent_based(self, user_input: str) -> str:
        """Fallback intent-based processing."""
        
        # 1. Parse the intent
        intent = self.intent_parser.parse(user_input)
        self.last_intent = intent
        
        # 2. If intent needs clarification, ask for it
        if intent.needs_file_clarification:
            return await self._request_file_clarification(intent)
        
        # 3. Build workflow from intent
        workflow_args = self.intent_parser.intent_to_workflow_args(intent)
        
        # 4. Request confirmation before proceeding - SKIP for direct execution to make it smooth
        # Only use /plan to see plan first
        # if intent.action in [ActionType.EXPAND_PDF, ActionType.CREATE_PDF, ActionType.CREATE_DOCUMENT]:
        #     return await self._request_confirmation(intent, workflow_args)
        
        # 5. Execute directly
        return await self._execute_intent(intent, workflow_args)
    
    async def _handle_confirmation(self, user_input: str) -> str:
        """Handle user response to confirmation request."""
        self.awaiting_confirmation = False
        
        result = self.confirm_ui.parse_user_response(user_input)
        
        if result == ConfirmationResult.CONFIRMED:
            intent = self.last_intent
            workflow_args = self.intent_parser.intent_to_workflow_args(intent)
            return await self._execute_intent(intent, workflow_args)
        
        elif result == ConfirmationResult.CHANGED:
            return "Okay, no problem. Please provide the file path or drag it into this window."
        
        else:
            return "No problem! What would you like to do instead?"
    
    async def _request_file_clarification(self, intent: Intent) -> str:
        """Ask user to clarify which file they mean."""
        hint = intent.clarification_hint or ""
        file_type = intent.file_type or "pdf"

        if hint == "pdf_source_or_scratch":
            return (
                "I understand you want to create a PDF.\n\n"
                "Would you like to:\n"
                "  1. Create a fresh new PDF from scratch (I'll help you write the content)\n"
                "  2. Use an existing PDF and expand/extract from it\n\n"
                "Please tell me which one, or provide the file path if you have an existing PDF."
            )

        candidates = self.file_finder.find(hint=hint, file_type=file_type, max_results=5)
        self.last_file_candidates = candidates
        self.awaiting_file_selection = True

        if not candidates:
            return (
                f"I'm not sure which {file_type.upper()} you mean.\n\n"
                f"I couldn't find any {file_type.upper()} files in your common folders.\n\n"
                "Try:\n"
                "  • Paste the full file path\n"
                "  • Or drag the file into this window"
            )

        lines = [
            f"I'm not sure which {file_type.upper()} you mean.",
            "",
            f"Here are some recent {file_type.upper()} files I found:",
            "",
            self.file_finder.format_candidates_for_ui(candidates),
            "",
            "Which one did you mean? (type the number or name)",
        ]
        return "\n".join(lines)

    async def _handle_file_selection(self, user_input: str) -> str:
        """Handle user's selection from candidate files."""
        choice = user_input.strip().lower()
        candidates = self.last_file_candidates or []

        selected = None
        if candidates:
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(candidates):
                    selected = candidates[idx]
            if selected is None:
                for c in candidates:
                    if choice in c.name.lower():
                        selected = c
                        break

        if selected is None:
            return "I couldn't match that selection. Please type the number from the list (like 1 or 2)."

        self.awaiting_file_selection = False
        self.last_file_candidates = []
        path = str(selected.path)
        if path not in self.pending_files:
            self.pending_files.append(path)

        intent = self.last_intent or self.intent_parser.parse("create pdf")
        workflow_args = self.intent_parser.intent_to_workflow_args(intent)
        if not workflow_args.get("source_pdf"):
            workflow_args["source_pdf"] = path
        return await self._request_confirmation(intent, workflow_args)
    
    async def _request_confirmation(self, intent: Intent, workflow_args: Dict) -> str:
        """Request user confirmation before executing action."""
        from pathlib import Path
        
        source = workflow_args.get("source_pdf", "")
        if source and not os.path.exists(source):
            source = ""
        if not source and self.pending_files:
            existing = [p for p in reversed(self.pending_files) if os.path.exists(p)]
            source = existing[0] if existing else self.pending_files[-1]
        
        output = workflow_args.get("output", "new file")
        
        text_lower = intent.original_text.lower()
        if any(word in text_lower for word in ["downloads", "download"]):
            output = str(Path.home() / "Downloads" / "expanded.pdf")
        
        has_source = bool(source) and os.path.exists(source)
        
        if intent.action == ActionType.EXPAND_PDF:
            if has_source:
                description = f"I'll read the existing PDF and create a new expanded version."
            else:
                description = f"I'll extract content and create a new PDF for you."
        elif intent.action == ActionType.CREATE_PDF:
            description = f"I'll create a fresh new PDF document from scratch."
        else:
            description = f"I'll create a new document."
        
        context = self.confirm_ui.create_context(
            action=intent.action.value,
            source_path=source,
            target_path=output,
            description=description
        )
        
        message = self.confirm_ui.build_confirmation_message(context)
        self.awaiting_confirmation = True
        
        return message
    
    async def _execute_intent(self, intent: Intent, workflow_args: Dict) -> str:
        """Execute the intent via the agent."""
        from pathlib import Path
        
        if intent.action == ActionType.CHAT:
            return await self.agent.chat(intent.original_text, skip_workflow=True)
        
        current_source = workflow_args.get("source_pdf", "")
        if current_source and not os.path.exists(current_source):
            current_source = ""
        if not current_source and not workflow_args.get("file"):
            if self.pending_files:
                existing = [p for p in reversed(self.pending_files) if os.path.exists(p)]
                workflow_args["source_pdf"] = existing[0] if existing else self.pending_files[-1]
        elif current_source:
            workflow_args["source_pdf"] = current_source
        
        if intent.action in [ActionType.EXPAND_PDF, ActionType.CREATE_PDF]:
            # For CREATE_PDF, we need to generate content using the main agent
            if intent.action == ActionType.CREATE_PDF:
                # Extract the actual topic from user input
                topic = self._extract_topic_from_input(intent.original_text)

                # Build a clean, focused prompt for content generation
                # Use a direct LLM call that doesn't pollute session state
                content_prompt = f"""Generate detailed content for a PDF document about: {topic}

Requirements:
- Generate at least 500 words
- Use markdown formatting with ## for main section headings
- Cover the topic comprehensively with multiple sections
- Do NOT include any meta-commentary, tool instructions, or system messages
- Output ONLY the content, nothing else

Structure the content with clear sections and subsections."""

                try:
                    content_result = await self._generate_pdf_content(content_prompt)

                    # Clean the content - remove any tool results or artifacts that got included
                    content = self._clean_content_for_pdf(content_result)

                    # Verify content is not empty
                    if not content or len(content.strip()) < 50:
                        return self.friendly.format_error("content_generation", "Generated content is too short or empty")

                    # Use the cleaned content
                    tool_args = {
                        "content": content,
                        "output": workflow_args.get("output", "document.pdf"),
                        "title": intent.title or ""
                    }
                except Exception as e:
                    return self.friendly.format_error("create_pdf", f"Failed to generate content: {str(e)}")
            else:
                # For EXPAND_PDF with source
                tool_args = {
                    "output": workflow_args.get("output", "document.pdf"),
                    "title": intent.title or ""
                }
                source_pdf = workflow_args.get("source_pdf", "")
                if source_pdf and os.path.exists(source_pdf):
                    tool_args["source_pdf"] = source_pdf
            
            text_lower = intent.original_text.lower()
            if any(word in text_lower for word in ["downloads", "download"]):
                tool_args["output"] = str(Path.home() / "Downloads" / "expanded.pdf")
            
            tool_args = {k: v for k, v in tool_args.items() if v}
            
            try:
                result = await self.agent.tool_registry.execute("create_pdf", **tool_args)
                if result.success:
                    return self.friendly.format_success("create_pdf", result.result, tool_args.get("output"))
                else:
                    return self.friendly.format_error("create_pdf", result.error or "Unknown error")
            except Exception as e:
                return self.friendly.format_error("create_pdf", str(e))
        
        elif intent.action == ActionType.READ_PDF:
            tool_args = {"file": workflow_args.get("file", "")}
            try:
                result = await self.agent.tool_registry.execute("read_pdf", **tool_args)
                if result.success:
                    return self.friendly.format_success("read_pdf", result.result)
                else:
                    return self.friendly.format_error("read_pdf", result.error or "Unknown error")
            except Exception as e:
                return self.friendly.format_error("read_pdf", str(e))
        
        return await self.agent.chat(intent.original_text, skip_workflow=True)
    
    def _extract_paths(self, text: str) -> List[str]:
        """Extract Windows-like file paths from free-form user text."""
        import re
        paths = []
        for m in re.findall(r'"([A-Za-z]:\\[^\"]+)"', text):
            paths.append(m)
        for m in re.findall(r"'([A-Za-z]:\\[^']+)'", text):
            paths.append(m)
        for m in re.findall(r'([A-Za-z]:\\[^\s<>"|?*]+)', text):
            paths.append(m)
        seen = set()
        out = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def _is_path_only_input(self, text: str, paths: List[str]) -> bool:
        """True if input is basically just a path and no action words."""
        cleaned = text.strip().strip('"').strip("'")
        if len(paths) == 1 and cleaned == paths[0]:
            return True
        if cleaned.lower().startswith("& ") and len(paths) >= 1 and len(cleaned.split()) <= 3:
            return True
        return False
    
    def _extract_topic_from_input(self, user_input: str) -> str:
        """Extract the actual topic from user input, removing action words."""
        text_lower = user_input.lower()
        
        # Remove common action phrases to extract the topic
        topic = user_input
        
        # Remove common prefixes
        prefixes_to_remove = [
            "make a pdf on ", "make a pdf about ", "make pdf on ", "make pdf about ",
            "create a pdf on ", "create a pdf about ", "create pdf on ", "create pdf about ",
            "generate a pdf on ", "generate a pdf about ", "generate pdf on ", "generate pdf about ",
            "write a pdf on ", "write a pdf about ", "write pdf on ", "write pdf about ",
            "create a document on ", "create a document about ", 
            "make a document on ", "make a document about ",
            "make me a pdf on ", "make me a pdf about ", 
            "create me a pdf on ", "create me a pdf about ",
        ]
        
        for prefix in prefixes_to_remove:
            if topic.lower().startswith(prefix):
                topic = topic[len(prefix):]
                break
        
        # Remove trailing instructions like "with 500 words" or "with 300+ words"
        topic = re.sub(r'\s+with\s+\d+\.?\d*\s*(?:plus|\+)?\s*(?:words|word).*$', '', topic, flags=re.IGNORECASE)
        topic = re.sub(r'\s+with\s+\d+\s*-\s*\d+\s*words.*$', '', topic, flags=re.IGNORECASE)
        
        # Clean up
        topic = topic.strip()
        topic = topic.strip('"').strip("'").strip()
        
        return topic if topic else user_input

    def _clean_content_for_pdf(self, content: str) -> str:
        """Clean content by removing tool results, system messages, and other artifacts."""
        if not content:
            return content

        lines = content.split('\n')
        cleaned_lines = []
        skip_mode = False

        for line in lines:
            # Skip lines that look like tool results or system messages
            if re.match(r'^Created\s+\S+(\s+using|\.pdf)', line, re.IGNORECASE):
                continue  # Skip "Created D:\path\to\file.pdf using high-fidelity generator"
            if re.match(r'^This JSON function call', line, re.IGNORECASE):
                skip_mode = True
                continue
            if re.match(r'^###?\s+Note:', line, re.IGNORECASE):
                continue  # Skip "Note:" sections that are meta-comments
            if re.match(r'^References?\s*:', line, re.IGNORECASE) and len(line) < 50:
                # If "References:" appears very early, it's likely a meta comment
                continue
            if re.match(r'^(Function call|Tool call|Tool result)', line, re.IGNORECASE):
                skip_mode = True
                continue
            if re.match(r'^```', line):
                skip_mode = not skip_mode
                continue
            if skip_mode:
                continue

            # Skip lines that look like they contain file paths or tool artifacts
            if re.search(r'\.pdf.*high-fidelity|using.*generator', line, re.IGNORECASE):
                continue
            if re.search(r'^(Error|Warning|Info):', line, re.IGNORECASE):
                continue

            cleaned_lines.append(line)

        # Rejoin and do final cleanup
        result = '\n'.join(cleaned_lines)

        # Remove any leading tool result artifacts from the start
        result = re.sub(r'^Created\s+\S+\s*using[^\n]*\n?', '', result, flags=re.IGNORECASE)
        result = re.sub(r'^This JSON[^\n]*\n?', '', result, flags=re.IGNORECASE)

        # If content still starts with something that looks like a section 5+, it might be missing content
        # Check for "## 5." without preceding sections and add a marker
        if re.match(r'^##\s+\d+\.', result):
            # Content might be a continuation - look for where actual content starts
            match = re.search(r'^##\s+\d+\.', result, re.MULTILINE)
            if match:
                # Check if there's no ## 1, 2, 3, or 4 before this
                before = result[:match.start()]
                if not re.search(r'^##\s+[1-4]\.', before, re.MULTILINE):
                    # This looks like a partial/continuation - add a note
                    result = "## Overview\n\nThis document covers the requested topic in detail.\n\n" + result

        return result.strip()

    async def _generate_pdf_content(self, prompt: str) -> str:
        """Generate PDF content without polluting the conversation session."""
        session = self.agent.session_manager.get_current_session()
        msg_count_before = len(session.get_messages()) if session else 0

        try:
            return await self.agent.chat(prompt, skip_workflow=True)
        finally:
            if session:
                session.replace_messages(session.get_messages()[:msg_count_before])


def create_ux_agent(agent_runner) -> UXAgent:
    """Create a UX-enabled agent wrapper."""
    return UXAgent(agent_runner)