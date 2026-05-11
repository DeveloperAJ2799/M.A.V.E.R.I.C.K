"""M.A.V.E.R.I.C.K agent tools."""
from maverickbot.agent.tools.base import Tool, ToolResult
from maverickbot.agent.tools.registry import ToolRegistry
from maverickbot.agent.tools.read_file import ReadFileTool
from maverickbot.agent.tools.write_file import WriteFileTool, AppendFileTool
from maverickbot.agent.tools.file_management import (
    DeleteFileTool, ListDirectoryTool, CopyFileTool, MoveFileTool, 
    CreateDirectoryTool, FileExistsTool, GetFileInfoTool
)
from maverickbot.agent.tools.shell_tool import ShellTool
from maverickbot.agent.tools.search_tool import SearchTool
from maverickbot.agent.tools.create_pptx import CreatePPTXTool
from maverickbot.agent.tools.create_pdf import CreatePdfTool
from maverickbot.agent.tools.read_pdf import ReadPdfTool
from maverickbot.agent.tools.create_docx import CreateDocxTool
from maverickbot.agent.tools.read_docx import ReadDocxTool
from maverickbot.agent.tools.create_xlsx import CreateXlsxTool
from maverickbot.agent.tools.read_xlsx import ReadXlsxTool
from maverickbot.agent.tools.create_image import CreateImageTool
from maverickbot.agent.tools.read_image import ReadImageTool
from maverickbot.agent.tools.text_to_speech import TextToSpeechTool
from maverickbot.agent.tools.read_csv import ReadCsvTool
from maverickbot.agent.tools.fetch_url import FetchUrlTool
from maverickbot.agent.tools.execute_code import ExecuteCodeTool
from maverickbot.agent.tools.git_tools import GitStatusTool, GitLogTool, GitDiffTool, GitBranchTool
from maverickbot.agent.tools.data_tools import ParseJsonTool, ToYamlTool, FromYamlTool, ValidateJsonTool
from maverickbot.agent.tools.system_tools import SystemInfoTool, ClipboardReadTool, ClipboardWriteTool, NotifyTool
from maverickbot.agent.tools.grep_tool import GrepTool
from maverickbot.agent.tools.glob_tool import GlobTool
from maverickbot.agent.tools.edit_tool import EditFileTool, ReplaceAllTool
from maverickbot.agent.tools.plan_tool import PlanTool, TodoListTool
from maverickbot.agent.tools.mcp_tools import AddMCPServerTool, AddMCPServerStdioTool, ListMCPServersTool, RemoveMCPServerTool, CallMCPToolTool
from maverickbot.agent.tools.workspace_tool import WorkspaceTool, WorkspaceCopyTool
from maverickbot.agent.tools.pdf_tools import PdfToPdfTool, QuickPdfTool
from maverickbot.agent.tools.universal_data import UniversalReadTool, ConvertDataTool, CreateDataFileTool

__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "ReadFileTool",
    "WriteFileTool",
    "AppendFileTool",
    "DeleteFileTool",
    "ListDirectoryTool",
    "CopyFileTool",
    "MoveFileTool",
    "CreateDirectoryTool",
    "FileExistsTool",
    "GetFileInfoTool",
    "ShellTool",
    "SearchTool",
    "CreatePPTXTool",
    "CreatePdfTool",
    "ReadPdfTool",
    "CreateDocxTool",
    "ReadDocxTool",
    "CreateXlsxTool",
    "ReadXlsxTool",
    "CreateImageTool",
    "ReadImageTool",
    "TextToSpeechTool",
    "ReadCsvTool",
    "FetchUrlTool",
    "ExecuteCodeTool",
    "GitStatusTool",
    "GitLogTool",
    "GitDiffTool",
    "GitBranchTool",
    "ParseJsonTool",
    "ToYamlTool",
    "FromYamlTool",
    "ValidateJsonTool",
    "SystemInfoTool",
    "ClipboardReadTool",
    "ClipboardWriteTool",
    "NotifyTool",
    "GrepTool",
    "GlobTool",
    "EditFileTool",
    "ReplaceAllTool",
    "PlanTool",
    "TodoListTool",
    "AddMCPServerTool",
    "AddMCPServerStdioTool",
    "ListMCPServersTool",
    "RemoveMCPServerTool",
    "CallMCPToolTool",
    "WorkspaceTool",
    "WorkspaceCopyTool",
    "PdfToPdfTool",
    "QuickPdfTool",
    "UniversalReadTool",
    "ConvertDataTool",
    "CreateDataFileTool",
]