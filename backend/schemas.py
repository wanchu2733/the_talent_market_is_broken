from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Literal


class TaskGeneratorResponse(BaseModel):
    task_id: str
    topic: str
    difficulty: Literal["easy", "medium", "hard"]
    question_text: str
    visual_specification: Dict[str, str] = Field(
        ...,
        description="Keys must be 'type' (svg_code/matplotlib_script/image_generation_prompt) and 'content'"
    )
    options: List[str]
    correct_answer: str
    explanation: str

    @field_validator("visual_specification")
    @classmethod
    def validate_visual_specification(cls, v: Dict[str, str]) -> Dict[str, str]:
        if "type" not in v or "content" not in v:
            raise ValueError("visual_specification must contain 'type' and 'content' keys")
        if v["type"] not in ("svg_code", "matplotlib_script", "image_generation_prompt"):
            raise ValueError("visual_specification.type must be one of: svg_code, matplotlib_script, image_generation_prompt")
        return v

    @field_validator("correct_answer")
    @classmethod
    def validate_correct_answer_in_options(cls, value: str, info: Any) -> str:
        if "options" in info.data and value not in info.data["options"]:
            raise ValueError("correct_answer must be present inside the options array")
        return value


class AIJudgeResponse(BaseModel):
    prompt_craft_score: float = Field(..., ge=0.0, le=1.0)
    process_depth_score: float = Field(..., ge=0.0, le=1.0)
    analysis: Dict[str, Any]


class UserPromptRequest(BaseModel):
    session_id: int
    user_prompt: str = Field(..., min_length=1)


class SubmitAnswerRequest(BaseModel):
    session_id: int
    selected_answer: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[int] = None
    context: str = ""


class ChatStatusResponse(BaseModel):
    available: bool
    provider: str
    model: str


class ProfileLoadRequest(BaseModel):
    email: Optional[str] = None
    github_username: Optional[str] = None
    leetcode_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    stackoverflow_user_id: Optional[int] = None
    force_refresh: bool = False
