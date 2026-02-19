"""
Script Generator Module - Style Cloning & Recursive Writing

Core Features:
1. Style Cloning: Phân tích và học giọng văn từ kịch bản mẫu
2. Recursive Writing: Viết đệ quy từ outline -> draft -> refined -> final
3. Smart Routing: Tự động chọn AI provider phù hợp cho từng task
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import re
from datetime import datetime

from .ai_automation import HybridAIClient, AIProvider
from .logging_config import get_automation_logger
from .exceptions import PromptError

logger = get_automation_logger()


class TaskType(Enum):
    """Task types for smart routing"""
    STYLE_ANALYSIS = "style_analysis"      # -> Gemini API (Fast)
    OUTLINE_GENERATION = "outline"         # -> Gemini API (Fast)  
    DEEP_WRITING = "deep_writing"          # -> GPM Automation (Quality)
    REFINEMENT = "refinement"              # -> GPM Automation (Quality)
    SCENE_BREAKDOWN = "scene_breakdown"    # -> Gemini API (Fast)


@dataclass
class StyleProfile:
    """Kết quả phân tích giọng văn"""
    tone: str = ""                    # Formal, casual, humorous, dramatic
    vocabulary_level: str = ""        # Simple, intermediate, advanced
    sentence_structure: str = ""      # Short, mixed, complex
    pacing: str = ""                  # Fast, moderate, slow
    key_phrases: List[str] = field(default_factory=list)
    emotional_range: str = ""         # Neutral, emotional, mixed
    target_audience: str = ""         # General, professional, youth
    narrative_voice: str = ""          # first_person, second_person, third_person
    audience_address: str = ""          # bạn, các bạn, anh chị, quý vị
    unique_patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StyleProfile':
        return cls(**data)
    
    def to_prompt_context(self) -> str:
        """Chuyển profile thành context cho AI prompt"""
        return f"""
Giọng văn cần tuân theo:
- Tone: {self.tone}
- Vocabulary: {self.vocabulary_level}
- Cấu trúc câu: {self.sentence_structure}
- Nhịp độ: {self.pacing}
- Đối tượng: {self.target_audience}
- Cảm xúc: {self.emotional_range}
- Cụm từ đặc trưng: {', '.join(self.key_phrases[:5])}
"""



# ═══════════════════════════════════════════════════════════════════════════
# DRAFT SECTION - Một phần đã viết nháp (used by AdvancedRemakeWorkflow)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DraftSection:
    """Một phần đã viết nháp"""
    section_id: str
    content: str
    version: int = 1
    word_count: int = 0
    status: str = "draft"  # draft, refined, final
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DetailedStyleAnalysis:
    """Kết quả phân tích chi tiết với từng script và tổng hợp"""
    synthesized_profile: StyleProfile
    individual_results: List[Dict]
    scripts_analyzed: int
    
    def to_dict(self) -> Dict:
        return {
            "synthesized_profile": self.synthesized_profile.to_dict(),
            "individual_results": self.individual_results,
            "scripts_analyzed": self.scripts_analyzed
        }


# ═══════════════════════════════════════════════════════════════════════════
# STYLE A - Phong cách văn đúc kết từ nhiều kịch bản
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ScriptStructure:
    """Nhịp văn/Cấu trúc kịch bản (tổng quan từ nhiều scripts)"""
    avg_word_count: int = 0                    # Số từ trung bình
    hook_duration: str = ""                     # Hook chiếm bao lâu
    intro_segments: int = 0                     # Số đoạn mở bài
    intro_purpose: str = ""                     # Mục đích mở bài
    body_segments: int = 0                      # Số đoạn thân bài
    body_purpose: str = ""                      # Mục đích thân bài
    conclusion_segments: int = 0                # Số đoạn kết bài
    conclusion_purpose: str = ""                # Mục đích kết bài
    climax_position: str = ""                   # Cao trào/payoff nằm ở đâu
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class StyleA:
    """
    Phong cách văn A - Đúc kết từ phân tích nhiều kịch bản mẫu
    
    NHÓM 1: DNA CỐ ĐỊNH (không đổi theo kịch bản)
    NHÓM 2: TÙY BIẾN (thay đổi theo từng kịch bản cụ thể)
    """
    # ═══════════════════════════════════════════════════════════════
    # NHÓM 1: DNA CỐ ĐỊNH (không đổi theo kịch bản)
    # ═══════════════════════════════════════════════════════════════
    voice_description: str = ""               # 🎯 Giọng văn
    storytelling_approach: str = ""           # 📖 Cách dẫn chuyện
    authors_soul: str = ""                    # ✨ HỒN VĂN
    character_embodiment: str = ""            # 👤 Cách nhập vai
    common_hook_types: List[str] = field(default_factory=list)      # 🪝 HOOK patterns
    retention_techniques: List[str] = field(default_factory=list)   # 🔄 Retention patterns
    cta_patterns: List[str] = field(default_factory=list)           # 📢 CTA patterns
    signature_phrases: List[str] = field(default_factory=list)      # 🔑 Cụm từ đặc trưng
    unique_patterns: List[str] = field(default_factory=list)        # ⭐ Pattern độc đáo
    tone_spectrum: str = ""                   # 🎨 Tone (DNA)
    vocabulary_signature: str = ""            # 📚 Từ vựng (DNA)
    emotional_palette: str = ""               # 💜 Cảm xúc (DNA)
    script_structure: Optional[ScriptStructure] = None  # 🎵 Nhịp văn/Cấu trúc (DNA)
    
    # ═══════════════════════════════════════════════════════════════
    # NHÓM 2: TÙY BIẾN (từ phân tích kịch bản gốc, ghép vào Giọng Văn A)
    # ═══════════════════════════════════════════════════════════════
    core_angle: str = ""                      # 🎯 Core Angle (từ kịch bản gốc)
    viewer_insight: str = ""                  # 💡 INSIGHT người xem
    main_ideas: List[str] = field(default_factory=list)  # 📝 Những ý quan trọng
    narrative_perspective: str = ""           # 👤 Ngôi kể
    audience_address: str = ""                # 👥 Xưng hô khán giả
    cultural_markers: str = ""                # 🌏 Văn hóa vùng miền/quốc gia
    
    # ═══════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════
    source_scripts_count: int = 0             # Số kịch bản đã phân tích
    confidence_score: float = 0.0             # Độ tin cậy (0-1)
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        # Convert ScriptStructure to dict if present
        if self.script_structure:
            result['script_structure'] = self.script_structure.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StyleA':
        # Handle script_structure separately
        script_struct_data = data.pop('script_structure', None)
        script_struct = None
        if script_struct_data and isinstance(script_struct_data, dict):
            script_struct = ScriptStructure(**{k: v for k, v in script_struct_data.items() 
                                               if k in ScriptStructure.__dataclass_fields__})
        
        instance = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        instance.script_structure = script_struct
        return instance
    
    def to_prompt_context(self) -> str:
        """Chuyển StyleA thành context cho AI prompt khi viết mới"""
        structure_info = ""
        if self.script_structure:
            s = self.script_structure
            structure_info = f"""
🎵 CẤU TRÚC KỊCH BẢN:
- Số từ trung bình: {s.avg_word_count}
- Hook: {s.hook_duration}
- Mở bài: {s.intro_segments} đoạn - {s.intro_purpose}
- Thân bài: {s.body_segments} đoạn - {s.body_purpose}
- Kết bài: {s.conclusion_segments} đoạn - {s.conclusion_purpose}
- Cao trào: {s.climax_position}
"""
        
        return f"""
PHONG CÁCH VĂN A - Profile Đã Học:

═══ DNA CỐ ĐỊNH ═══

🎯 GIỌNG VĂN:
{self.voice_description}

📖 CÁCH DẪN CHUYỆN:
{self.storytelling_approach}

✨ HỒN VĂN (Author's Soul):
{self.authors_soul}

🎭 CÁCH NHẬP VAI:
{self.character_embodiment}

🪝 HOOK PATTERNS:
{', '.join(self.common_hook_types) if self.common_hook_types else 'Không xác định'}

🔄 RETENTION TECHNIQUES:
{', '.join(self.retention_techniques) if self.retention_techniques else 'Không xác định'}

📢 CTA PATTERNS:
{', '.join(self.cta_patterns) if self.cta_patterns else 'Không xác định'}

🎨 PHONG CÁCH:
- Tone: {self.tone_spectrum}
- Từ vựng: {self.vocabulary_signature}
- Cảm xúc: {self.emotional_palette}
{structure_info}
🔑 SIGNATURE PHRASES:
{', '.join(self.signature_phrases) if self.signature_phrases else 'Không có'}

═══ TÙY BIẾN (Từ kịch bản gốc - Ghép vào Giọng Văn A) ═══

🎯 Core Angle: {self.core_angle}
💡 INSIGHT: {self.viewer_insight}
📝 Ý chính: {', '.join(self.main_ideas) if self.main_ideas else 'Không có'}
👤 Ngôi kể: {self.narrative_perspective}
👥 Xưng hô: {self.audience_address}
🌏 Văn hóa: {self.cultural_markers}
"""


# ═══════════════════════════════════════════════════════════════════════════
# ADVANCED REMAKE - 7 STEP WORKFLOW DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class OriginalScriptAnalysis:
    """
    STEP 1: Bóc tách nội dung gốc
    
    Phân tích sâu kịch bản gốc để hiểu:
    - Core Angle (góc nhìn cốt lõi)
    - INSIGHT người xem
    - HOOK analysis
    - Phong cách, văn phong
    - Cơ chế giữ người xem
    - CTA strategy
    """
    core_angle: str = ""                      # Góc nhìn cốt lõi
    main_ideas: List[str] = field(default_factory=list)  # Ý chính quan trọng
    viewer_insight: str = ""                  # INSIGHT người xem
    hook_analysis: Dict[str, str] = field(default_factory=dict)  # Phân tích HOOK
    writing_style: Dict[str, str] = field(default_factory=dict)  # Phong cách, ngôi kể
    cultural_context: str = ""                # Văn hóa vùng miền/quốc gia
    narrative_voice: str = ""                 # Ngôi kể (first person, second person, etc.)
    retention_engine: str = ""                # Cơ chế giữ người xem
    cta_strategy: str = ""                    # Cách CTA chuyển đổi
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OriginalScriptAnalysis':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StructureAnalysis:
    """
    STEP 2: Phân tích cấu trúc kịch bản
    
    Phân tích nhịp và cấu trúc:
    - Số lượng từ
    - Hook duration
    - Intro/Body/Conclusion breakdown
    - Climax/Payoff locations
    """
    total_word_count: int = 0                 # Số lượng từ
    hook_duration: str = ""                   # Hook chiếm bao lâu (e.g., "first 30 seconds")
    hook_word_count: int = 0                  # Số từ phần hook
    intro_analysis: Dict[str, Any] = field(default_factory=dict)   # Mở bài: segments, word count, issues
    body_analysis: Dict[str, Any] = field(default_factory=dict)    # Thân bài: segments, issues
    conclusion_analysis: Dict[str, Any] = field(default_factory=dict)  # Kết bài: segments, issues
    section_breakdown: List[Dict[str, Any]] = field(default_factory=list)  # Chi tiết từng đoạn
    climax_location: str = ""                 # Cao trào nằm ở đâu
    payoff_location: str = ""                 # Payoff nằm ở đâu
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StructureAnalysis':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class OutlineSectionA:
    """Một phần trong Dàn ý A (Step 3)"""
    id: str
    title: str
    description: str
    order: int
    word_count_target: int = 100              # Số từ mục tiêu
    key_points: List[str] = field(default_factory=list)  # Ý chính cần cover
    special_instructions: str = ""            # Hướng dẫn đặc biệt (hook mode, CTA, quiz, etc.)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class OutlineA:
    """
    STEP 3: Dàn ý A với phân bổ từ
    
    Dàn ý chi tiết với:
    - Chia tối đa 5 phần
    - Phân bổ số từ cho mỗi phần
    - Target word count tổng
    - Phong cách dẫn chuyện và ngôi kể (NEW)
    """
    sections: List[OutlineSectionA] = field(default_factory=list)
    target_word_count: int = 0                # Tổng số từ mục tiêu
    language: str = "en"                      # Ngôn ngữ output
    dialect: str = "American"                 # Giọng (American, British, etc.)
    channel_name: str = ""                    # Tên kênh YouTube
    storytelling_style: str = ""              # Phong cách dẫn chuyện: immersive, documentary, conversational, analytical, narrative
    narrative_voice: str = "first_person"     # Ngôi kể: first_person, second_person, third_person
    audience_address: str = "bạn"             # Cách xưng hô khán giả: bạn, các bạn, anh chị, quý vị
    
    def to_dict(self) -> Dict:
        return {
            "sections": [s.to_dict() for s in self.sections],
            "target_word_count": self.target_word_count,
            "language": self.language,
            "dialect": self.dialect,
            "channel_name": self.channel_name,
            "storytelling_style": self.storytelling_style,
            "narrative_voice": self.narrative_voice,
            "audience_address": self.audience_address
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OutlineA':
        sections = [OutlineSectionA(**s) for s in data.get("sections", [])]
        return cls(
            sections=sections,
            target_word_count=data.get("target_word_count", 0),
            language=data.get("language", "en"),
            dialect=data.get("dialect", "American"),
            channel_name=data.get("channel_name", ""),
            storytelling_style=data.get("storytelling_style", ""),
            narrative_voice=data.get("narrative_voice", "first_person"),
            audience_address=data.get("audience_address", "bạn")
        )


@dataclass
class SimilarityReview:
    """
    STEP 5: Kết quả kiểm tra tương đồng
    
    So sánh với bản gốc:
    - Similarity score
    - Issues found
    - Legal/Ethics check
    """
    similarity_score: float = 0.0             # 0-100%
    content_matches: bool = True              # Nội dung tương đồng?
    repetition_issues: List[str] = field(default_factory=list)  # Lặp lại gây nhàm chán
    youtube_violations: List[str] = field(default_factory=list)  # Vi phạm YouTube guidelines
    legal_violations: List[str] = field(default_factory=list)   # Vi phạm pháp luật
    ethics_violations: List[str] = field(default_factory=list)  # Vi phạm đạo đức
    suggestions: List[str] = field(default_factory=list)        # Đề xuất cải thiện
    country_checked: str = "Vietnam"          # Quốc gia kiểm tra pháp luật
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SimilarityReview':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ConversationStyleAnalyzer:
    """
    Phân tích giọng văn từ nhiều kịch bản sử dụng một cuộc trò chuyện liên tục.
    
    Flow:
    1. Tạo conversation mới
    2. Đưa từng script vào, AI phân tích và ghi nhớ context
    3. Sau script cuối, yêu cầu AI tổng hợp thành giọng văn chuẩn
    4. Kết thúc conversation, trả về kết quả
    """
    
    def __init__(self, ai_client):
        self.ai_client = ai_client
        # Store intermediate results for detailed analysis
        self._stored_results: List[Dict] = []
    
    def analyze_with_details(self, scripts: List[str]) -> 'DetailedStyleAnalysis':
        """
        Phân tích nhiều scripts và trả về kết quả CHI TIẾT.
        
        Returns:
            DetailedStyleAnalysis với cả individual results và synthesized profile
        """
        if not scripts:
            logger.warning("No scripts provided for analysis")
            return DetailedStyleAnalysis(
                synthesized_profile=StyleProfile(tone="neutral", vocabulary_level="intermediate"),
                individual_results=[],
                scripts_analyzed=0
            )
        
        # Reset stored results
        self._stored_results = []
        
        # Giới hạn 20 scripts
        scripts_to_analyze = scripts[:20]
        num_scripts = len(scripts_to_analyze)
        
        logger.info(f"🔄 Starting DETAILED style analysis for {num_scripts} scripts")
        
        # Run the analysis (this will populate self._stored_results)
        # Uses unified conversation API - works with any configured provider
        if self.ai_client.has_conversation_support():
            synthesized = self._fallback_individual_analysis(scripts_to_analyze)
        else:
            synthesized = self._legacy_fallback_analysis(scripts_to_analyze)
        
        return DetailedStyleAnalysis(
            synthesized_profile=synthesized,
            individual_results=self._stored_results.copy(),
            scripts_analyzed=len(self._stored_results)
        )
    
    def analyze_with_conversation(self, scripts: List[str]) -> 'StyleProfile':
        """
        Phân tích nhiều scripts sử dụng một conversation liên tục.
        
        Args:
            scripts: List các kịch bản mẫu (1-20 scripts)
            
        Returns:
            StyleProfile tổng hợp từ tất cả scripts
        """
        if not scripts:
            logger.warning("No scripts provided for analysis")
            return StyleProfile(tone="neutral", vocabulary_level="intermediate")
        
        # Giới hạn 20 scripts
        scripts_to_analyze = scripts[:20]
        num_scripts = len(scripts_to_analyze)
        
        logger.info(f"🔄 Starting conversation-based style analysis for {num_scripts} scripts")
        
        # Check if any provider is configured
        if not self.ai_client.has_conversation_support():
            logger.warning("No AI provider configured, falling back to legacy analysis")
            return self._legacy_fallback_analysis(scripts_to_analyze)

        
        conversation_id = None
        try:
            # Step 1: Start conversation
            conversation_id = self.ai_client.start_conversation()
            logger.info(f"📝 Started conversation: {conversation_id[:8]}...")
            
            # Step 2: Initialize the conversation
            init_prompt = """Bạn là chuyên gia phân tích văn phong. Tôi sẽ gửi cho bạn lần lượt các kịch bản mẫu.

Nhiệm vụ của bạn:
1. Đọc kỹ từng kịch bản tôi gửi
2. Ghi nhớ đặc điểm giọng văn của từng kịch bản
3. Khi tôi yêu cầu "TỔNG HỢP", hãy tổng hợp tất cả thành MỘT giọng văn thống nhất

Hãy xác nhận bạn đã sẵn sàng."""
            
            response = self.ai_client.send_message(conversation_id, init_prompt, temperature=0.3)
            logger.debug(f"Init response: {response[:100]}...")
            
            # Step 3: Send each script for analysis
            for i, script in enumerate(scripts_to_analyze, 1):
                # In conversation mode, use smaller per-message limit to avoid context overflow
                # 20 scripts × 10K = 200K chars ≈ 50K tokens (safe for GPT-5.2 context)
                max_chars = 10000
                script_content = script[:max_chars] if len(script) > max_chars else script
                
                analysis_prompt = f"""📌 SCRIPT #{i}/{num_scripts}:

{script_content}

---
Hãy phân tích ngắn gọn giọng văn của script này:
- Tone (giọng điệu)
- Vocabulary level (mức từ vựng)
- Sentence structure (cấu trúc câu)
- Pacing (nhịp độ)
- 2-3 cụm từ đặc trưng

GHI NHỚ các đặc điểm này để tổng hợp sau. Trả lời ngắn gọn."""
                
                logger.info(f"📝 Analyzing script {i}/{num_scripts} ({len(script_content)} chars)...")
                response = self.ai_client.send_message(conversation_id, analysis_prompt, temperature=0.3)
                logger.debug(f"Script {i} analysis: {response[:200]}...")
            
            # Step 4: Request synthesis
            synthesis_prompt = """🔀 TỔNG HỢP

Bây giờ hãy tổng hợp TẤT CẢ các giọng văn bạn đã phân tích thành MỘT profile thống nhất.

Trả về CHÍNH XÁC JSON sau (chỉ JSON, không có text khác):
{
    "tone": "<giọng điệu phổ biến nhất: formal|casual|humorous|dramatic|inspiring|educational>",
    "vocabulary_level": "<mức từ vựng: simple|intermediate|advanced>",
    "sentence_structure": "<cấu trúc câu: short|mixed|complex>",
    "pacing": "<nhịp độ: fast|moderate|slow>",
    "key_phrases": ["<gộp các cụm từ đặc trưng từ tất cả scripts, tối đa 15>"],
    "emotional_range": "<cảm xúc: neutral|emotional|mixed>",
    "target_audience": "<đối tượng: general|professional|youth|children>",
    "unique_patterns": ["<các pattern đặc biệt, tối đa 10>"]
}

JSON output:"""
            
            logger.info("🔀 Requesting synthesis...")
            response = self.ai_client.send_message(conversation_id, synthesis_prompt, temperature=0.3)
            
            # Parse JSON from response
            result = self._parse_style_json(response)
            
            logger.info(f"✅ Conversation analysis complete:")
            logger.info(f"   - Scripts analyzed: {num_scripts}")
            logger.info(f"   - Final tone: {result.tone}")
            logger.info(f"   - Final vocab: {result.vocabulary_level}")
            logger.info(f"   - Key phrases: {len(result.key_phrases)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Conversation analysis failed: {e}")
            return StyleProfile(tone="neutral", vocabulary_level="intermediate")
            
        finally:
            # Cleanup conversation
            if conversation_id:
                try:
                    self.ai_client.end_conversation(conversation_id)
                except:
                    pass
    
    def _parse_style_json(self, response: str) -> 'StyleProfile':
        """Parse StyleProfile JSON from AI response"""
        import re
        import json
        
        clean_response = response.strip()
        if clean_response.startswith("```"):
            clean_response = re.sub(r'^```(?:json)?\s*', '', clean_response)
            clean_response = re.sub(r'\s*```$', '', clean_response)
        
        start_idx = clean_response.find('{')
        if start_idx != -1:
            brace_count = 0
            end_idx = start_idx
            for i, char in enumerate(clean_response[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            json_str = clean_response[start_idx:end_idx]
            try:
                data = json.loads(json_str)
                
                key_phrases = data.get("key_phrases", [])
                if isinstance(key_phrases, str):
                    key_phrases = [key_phrases]
                unique_patterns = data.get("unique_patterns", [])
                if isinstance(unique_patterns, str):
                    unique_patterns = [unique_patterns]
                
                return StyleProfile(
                    tone=data.get("tone", "neutral"),
                    vocabulary_level=data.get("vocabulary_level", "intermediate"),
                    sentence_structure=data.get("sentence_structure", "mixed"),
                    pacing=data.get("pacing", "moderate"),
                    key_phrases=key_phrases[:15] if key_phrases else [],
                    emotional_range=data.get("emotional_range", "mixed"),
                    target_audience=data.get("target_audience", "general"),
                    unique_patterns=unique_patterns[:10] if unique_patterns else []
                )
            except json.JSONDecodeError as je:
                logger.warning(f"JSON parse error: {je}")
        
        logger.warning("Could not parse style JSON, returning default profile")
        return StyleProfile(tone="neutral", vocabulary_level="intermediate")
    
    def _fallback_individual_analysis(self, scripts: List[str]) -> 'StyleProfile':
        """
        Conversation-based analysis using OpenAI API.
        
        Flow:
        1. Start 1 conversation với OpenAI
        2. Gửi từng script, AI ghi nhớ context
        3. Cuối cùng yêu cầu tổng hợp
        4. End conversation
        
        Đảm bảo AI nhớ context xuyên suốt giống như Gemini.
        """
        logger.info(f"Starting CONVERSATION-BASED analysis for {len(scripts)} scripts")
        
        num_scripts = len(scripts)
        
        # Check if any provider is configured for conversations
        if not self.ai_client.has_conversation_support():
            logger.warning("No AI provider configured, falling back to legacy analysis")
            return self._legacy_fallback_analysis(scripts)
        
        # Reset stored results
        self._stored_results = []
        
        conversation_id = None
        try:
            # ═══════════════════════════════════════════════════════════════
            # STEP 1: START CONVERSATION
            # ═══════════════════════════════════════════════════════════════
            conversation_id = self.ai_client.start_conversation()
            logger.info(f"Started conversation: {conversation_id[:8]}...")
            
            # ═══════════════════════════════════════════════════════════════
            # STEP 2: INITIALIZE THE CONVERSATION
            # ═══════════════════════════════════════════════════════════════
            init_prompt = """Bạn là chuyên gia phân tích văn phong. Tôi sẽ gửi cho bạn lần lượt các kịch bản mẫu.

Nhiệm vụ của bạn:
1. Đọc kỹ từng kịch bản tôi gửi
2. Phân tích ngắn gọn đặc điểm giọng văn của từng kịch bản
3. Ghi nhớ tất cả để TỔNG HỢP khi tôi yêu cầu

Với mỗi script, hãy phân tích và trả về JSON:
{
  "tone": "<giọng điệu>",
  "vocabulary_level": "<mức từ vựng>",
  "sentence_structure": "<cấu trúc câu>",
  "pacing": "<nhịp độ>",
  "key_phrases": ["<cụm từ đặc trưng>"],
  "emotional_range": "<cảm xúc>",
  "target_audience": "<đối tượng>"
}

Hãy xác nhận bạn đã sẵn sàng."""
            
            response = self.ai_client.send_message(conversation_id, init_prompt, temperature=0.3)
            logger.debug(f"Init response: {response[:100]}...")
            
            # ═══════════════════════════════════════════════════════════════
            # STEP 3: SEND EACH SCRIPT FOR ANALYSIS
            # ═══════════════════════════════════════════════════════════════
            for i, script in enumerate(scripts, 1):
                # In conversation mode, use smaller per-message limit to avoid context overflow
                # 20 scripts × 10K = 200K chars ≈ 50K tokens (safe for GPT-5.2 context)
                max_chars = 10000
                script_content = script[:max_chars] if len(script) > max_chars else script
                
                analysis_prompt = f"""📌 SCRIPT #{i}/{num_scripts}:

{script_content}

---
Hãy phân tích giọng văn của script này. Trả về JSON:
{{
  "tone": "<formal|casual|humorous|dramatic|inspiring|educational>",
  "vocabulary_level": "<simple|intermediate|advanced>",
  "sentence_structure": "<short|mixed|complex>",
  "pacing": "<fast|moderate|slow>",
  "key_phrases": ["<2-3 cụm từ đặc trưng>"],
  "emotional_range": "<neutral|emotional|mixed>",
  "target_audience": "<general|professional|youth|children>",
  "unique_patterns": ["<1-2 patterns đặc biệt>"]
}}

GHI NHỚ kết quả này để tổng hợp sau. Trả lời ngắn gọn."""

                logger.info(f"📝 Analyzing script {i}/{num_scripts} ({len(script_content)} chars)...")
                response = self.ai_client.send_message(conversation_id, analysis_prompt, temperature=0.3)
                logger.debug(f"Script {i} response: {response[:200]}...")
                
                # Parse and store individual result
                result = self._parse_json_to_dict(response)
                if result:
                    result['script_num'] = i
                    result['script_title'] = f"Script #{i}: {script[:50]}..."
                    self._stored_results.append(result)
                    logger.info(f"   ✓ Stored result {i}: tone={result.get('tone')}, vocab={result.get('vocabulary_level')}")
                else:
                    # Try to extract from text
                    text_result = self._extract_dict_from_text(response)
                    if text_result:
                        text_result['script_num'] = i
                        text_result['script_title'] = f"Script #{i}: {script[:50]}..."
                        self._stored_results.append(text_result)
                        logger.info(f"   ✓ Stored result {i} (from text)")
                    else:
                        logger.warning(f"   ✗ Could not parse result for script {i}")
            
            # ═══════════════════════════════════════════════════════════════
            # STEP 4: REQUEST SYNTHESIS
            # ═══════════════════════════════════════════════════════════════
            synthesis_prompt = """🔀 TỔNG HỢP

Bây giờ hãy tổng hợp TẤT CẢ các giọng văn bạn đã phân tích thành MỘT profile thống nhất.

NGUYÊN TẮC:
1. Chọn giá trị XUẤT HIỆN NHIỀU NHẤT cho mỗi thuộc tính
2. Gộp các key_phrases và unique_patterns, loại bỏ trùng lặp
3. Tạo một profile ĐẠI DIỆN cho phong cách chung của tác giả

Trả về CHÍNH XÁC JSON sau (chỉ JSON, không có text khác):
{
    "tone": "<giọng điệu phổ biến nhất: formal|casual|humorous|dramatic|inspiring|educational>",
    "vocabulary_level": "<mức từ vựng: simple|intermediate|advanced>",
    "sentence_structure": "<cấu trúc câu: short|mixed|complex>",
    "pacing": "<nhịp độ: fast|moderate|slow>",
    "key_phrases": ["<gộp các cụm từ đặc trưng từ tất cả scripts, tối đa 15>"],
    "emotional_range": "<cảm xúc: neutral|emotional|mixed>",
    "target_audience": "<đối tượng: general|professional|youth|children>",
    "unique_patterns": ["<các pattern đặc biệt, tối đa 10>"]
}

JSON output:"""
            
            logger.info("🔀 Requesting synthesis...")
            response = self.ai_client.send_message(conversation_id, synthesis_prompt, temperature=0.3)
            
            # Parse JSON from response
            result = self._parse_style_json(response)
            
            logger.info(f"Conversation analysis complete:")
            logger.info(f"   - Scripts analyzed: {num_scripts}")
            logger.info(f"   - Results stored: {len(self._stored_results)}")
            logger.info(f"   - Final tone: {result.tone}")
            logger.info(f"   - Final vocab: {result.vocabulary_level}")
            logger.info(f"   - Key phrases: {len(result.key_phrases)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Conversation analysis failed: {e}")
            # Fallback to legacy if conversation fails
            if self._stored_results:
                logger.info("Using partial results for synthesis...")
                return self._synthesize_stored_results(self._stored_results)
            return StyleProfile(tone="neutral", vocabulary_level="intermediate")
            
        finally:
            # Cleanup conversation
            if conversation_id:
                try:
                    self.ai_client.end_conversation(conversation_id)
                    logger.info(f"Ended conversation")
                except:
                    pass
    
    def _legacy_fallback_analysis(self, scripts: List[str]) -> 'StyleProfile':
        """
        Legacy fallback: Two-phase analysis when conversation fails.
        
        PHASE 1: Phân tích từng script riêng lẻ → Lưu trữ kết quả
        PHASE 2: Gộp tất cả kết quả đã lưu → 1 prompt tổng hợp cuối cùng
        """
        logger.info(f"📊 Starting LEGACY analysis for {len(scripts)} scripts")
        
        num_scripts = len(scripts)
        self._stored_results = []
        
        for i, script in enumerate(scripts, 1):
            try:
                logger.info(f"📝 [Legacy] Analyzing script {i}/{num_scripts}...")
                max_chars = self.MAX_SCRIPT_CHARS  # 50K chars - consistent limit
                script_content = script[:max_chars] if len(script) > max_chars else script
                result = self._analyze_single_script_for_storage(script_content, i)
                
                if result:
                    result['script_title'] = f"Script #{i}: {script[:50]}..."
                    self._stored_results.append(result)
                    
            except Exception as e:
                logger.warning(f"   ✗ Script {i} failed: {e}")
                continue
        
        if not self._stored_results:
            return StyleProfile(tone="neutral", vocabulary_level="intermediate")
        
        return self._synthesize_stored_results(self._stored_results)
    
    def _analyze_single_script_for_storage(self, script: str, script_num: int) -> Optional[dict]:
        """
        Phase 1: Phân tích 1 script và trả về dict kết quả để lưu trữ.
        
        Returns dict thay vì StyleProfile để dễ serialize và gửi trong Phase 2.
        """
        from .script_generator import ScriptWorkflow
        workflow = ScriptWorkflow(self.ai_client)
        
        prompt = f"""Phân tích giọng văn của kịch bản sau và trả về JSON:

KỊCH BẢN #{script_num}:
{script}

Trả về CHÍNH XÁC JSON sau (chỉ JSON, không giải thích):
{{
  "tone": "<formal|casual|humorous|dramatic|inspiring|educational>",
  "vocabulary_level": "<simple|intermediate|advanced>",
  "sentence_structure": "<short|mixed|complex>",
  "pacing": "<fast|moderate|slow>",
  "key_phrases": ["<3-5 cụm từ đặc trưng>"],
  "emotional_range": "<neutral|emotional|mixed>",
  "target_audience": "<general|professional|youth|children>",
  "unique_patterns": ["<2-3 patterns đặc biệt>"]
}}"""
        
        try:
            response = workflow._route_task(TaskType.STYLE_ANALYSIS, prompt, temperature=0.3)
            
            # Parse JSON
            result = self._parse_json_to_dict(response)
            if result:
                result['script_num'] = script_num
                return result
            
            # Fallback: extract from text
            text_result = self._extract_dict_from_text(response)
            if text_result:
                text_result['script_num'] = script_num
                return text_result
                
            return None
            
        except Exception as e:
            logger.warning(f"Script {script_num} analysis error: {e}")
            return None
    
    def _parse_json_to_dict(self, response: str) -> Optional[dict]:
        """
        Parse JSON response to dict with multiple fallback strategies.
        
        Strategy:
        1. Try direct JSON parse (clean)
        2. Try fixing common JSON errors (trailing commas, single quotes)
        3. Try extracting partial data from malformed JSON using regex
        4. Use text extraction as last resort
        """
        import re
        import json
        
        if not response or not response.strip():
            logger.warning("Empty response received")
            return None
        
        clean_response = response.strip()
        
        # Remove markdown code blocks
        if clean_response.startswith("```"):
            clean_response = re.sub(r'^```(?:json)?[\s\n]*', '', clean_response)
            clean_response = re.sub(r'[\s\n]*```$', '', clean_response)
        
        # Find JSON object boundaries
        start_idx = clean_response.find('{')
        if start_idx == -1:
            logger.warning("No JSON object found in response")
            # Try text extraction as fallback
            return self._extract_dict_from_text(response)
            
        brace_count = 0
        end_idx = start_idx
        for i, char in enumerate(clean_response[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        json_str = clean_response[start_idx:end_idx]
        
        # STRATEGY 1: Direct parse
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.debug(f"Direct JSON parse failed: {e}")
        
        # STRATEGY 2: Fix common JSON issues
        fixed_json = json_str
        # Remove trailing commas before } or ]
        fixed_json = re.sub(r',\s*([}\]])', r'\1', fixed_json)
        # Replace single quotes with double quotes (careful with apostrophes)
        fixed_json = re.sub(r"(?<=[{,:\[\s])'([^']*)'(?=[},:\]\s])", r'"\1"', fixed_json)
        # Fix unquoted keys
        fixed_json = re.sub(r'(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', fixed_json)
        
        try:
            return json.loads(fixed_json)
        except json.JSONDecodeError as e:
            logger.debug(f"Fixed JSON parse failed: {e}")
        
        # STRATEGY 3: Extract partial data using regex
        extracted = {}
        
        # Extract common fields using regex
        field_patterns = {
            'core_angle': r'"core_angle"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
            'viewer_insight': r'"viewer_insight"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
            'hook_type': r'"hook_type"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
            'writing_style': r'"writing_style"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
            'tone': r'"tone"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
            'cultural_context': r'"cultural_context"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
            'narrative_voice': r'"narrative_voice"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
            'retention_engine': r'"retention_engine"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
            'cta_strategy': r'"cta_strategy"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
        }
        
        for field, pattern in field_patterns.items():
            match = re.search(pattern, json_str, re.DOTALL)
            if match:
                extracted[field] = match.group(1).replace('\\n', '\n').replace('\\"', '"')
        
        # Extract main_ideas array
        ideas_match = re.search(r'"main_ideas"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
        if ideas_match:
            ideas_str = ideas_match.group(1)
            ideas = re.findall(r'"([^"]*(?:\\.[^"]*)*)"', ideas_str)
            if ideas:
                extracted['main_ideas'] = [i.replace('\\n', '\n') for i in ideas]
        
        if extracted:
            logger.info(f"✅ Extracted {len(extracted)} fields using regex fallback")
            return extracted
        
        # STRATEGY 4: Use text extraction as last resort
        logger.warning("All JSON parsing strategies failed, using text extraction")
        return self._extract_dict_from_text(response)
    
    def _extract_dict_from_text(self, response: str) -> Optional[dict]:
        """Extract style info as dict from text response"""
        text = response.lower()
        
        TONE_KEYWORDS = {
            'formal': ['formal', 'trang trọng', 'nghiêm túc'],
            'casual': ['casual', 'thân mật', 'informal', 'gần gũi'],
            'humorous': ['humorous', 'hài hước', 'funny'],
            'dramatic': ['dramatic', 'kịch tính', 'suspense'],
            'inspiring': ['inspiring', 'truyền cảm hứng'],
            'educational': ['educational', 'giáo dục', 'informative']
        }
        
        VOCAB_KEYWORDS = {
            'simple': ['simple', 'đơn giản', 'easy'],
            'intermediate': ['intermediate', 'trung bình'],
            'advanced': ['advanced', 'nâng cao', 'sophisticated']
        }
        
        def find_match(keywords_dict):
            for value, keywords in keywords_dict.items():
                for kw in keywords:
                    if kw in text:
                        return value
            return None
        
        tone = find_match(TONE_KEYWORDS)
        vocab = find_match(VOCAB_KEYWORDS)
        
        if tone or vocab:
            return {
                'tone': tone or 'neutral',
                'vocabulary_level': vocab or 'intermediate',
                'sentence_structure': 'mixed',
                'pacing': 'moderate',
                'key_phrases': [],
                'emotional_range': 'mixed',
                'target_audience': 'general',
                'unique_patterns': []
            }
        
        return None
    
    def _synthesize_stored_results(self, stored_results: List[dict]) -> 'StyleProfile':
        """
        Phase 2: Tổng hợp tất cả kết quả đã lưu thành 1 profile cuối cùng.
        
        Gửi TẤT CẢ kết quả trong 1 prompt để AI tổng hợp thông minh.
        """
        from .script_generator import ScriptWorkflow
        import json as json_module
        workflow = ScriptWorkflow(self.ai_client)
        
        # Format stored results for the synthesis prompt
        results_text = ""
        all_phrases = []
        all_patterns = []
        
        for result in stored_results:
            script_num = result.get('script_num', '?')
            results_text += f"""
📌 Kết quả phân tích Script #{script_num}:
- Tone: {result.get('tone', 'N/A')}
- Vocabulary: {result.get('vocabulary_level', 'N/A')}
- Structure: {result.get('sentence_structure', 'N/A')}
- Pacing: {result.get('pacing', 'N/A')}
- Emotional: {result.get('emotional_range', 'N/A')}
- Audience: {result.get('target_audience', 'N/A')}
- Key phrases: {result.get('key_phrases', [])}
- Patterns: {result.get('unique_patterns', [])}
"""
            # Collect all phrases and patterns
            all_phrases.extend(result.get('key_phrases', []) or [])
            all_patterns.extend(result.get('unique_patterns', []) or [])
        
        synthesis_prompt = f"""Bạn là chuyên gia tổng hợp giọng văn. Dưới đây là kết quả phân tích của {len(stored_results)} kịch bản mẫu từ CÙNG MỘT tác giả.

═══════════════════════════════════════════════════
📊 KẾT QUẢ PHÂN TÍCH TỪNG SCRIPT
═══════════════════════════════════════════════════
{results_text}

═══════════════════════════════════════════════════
🔀 YÊU CẦU TỔNG HỢP
═══════════════════════════════════════════════════

Dựa trên TẤT CẢ kết quả phân tích trên, hãy TỔNG HỢP thành MỘT profile giọng văn thống nhất.

NGUYÊN TẮC:
1. Chọn giá trị XUẤT HIỆN NHIỀU NHẤT cho mỗi thuộc tính
2. Nếu có sự khác biệt lớn, chọn giá trị PHÙ HỢP NHẤT với đa số
3. Gộp các key_phrases và unique_patterns, loại bỏ trùng lặp

Trả về CHÍNH XÁC JSON sau:
{{
  "tone": "<formal|casual|humorous|dramatic|inspiring|educational>",
  "vocabulary_level": "<simple|intermediate|advanced>",
  "sentence_structure": "<short|mixed|complex>",
  "pacing": "<fast|moderate|slow>",
  "key_phrases": ["<gộp tối đa 10 cụm từ đặc trưng nhất>"],
  "emotional_range": "<neutral|emotional|mixed>",
  "target_audience": "<general|professional|youth|children>",
  "unique_patterns": ["<gộp tối đa 5 patterns độc đáo nhất>"]
}}

CHỈ trả về JSON, không giải thích."""

        try:
            logger.info("🔀 Sending SYNTHESIS prompt...")
            response = workflow._route_task(TaskType.STYLE_ANALYSIS, synthesis_prompt, temperature=0.3)
            logger.info(f"📩 Synthesis response ({len(response)} chars)")
            
            # Parse the synthesis result
            result = self._parse_style_json(response)
            
            # If synthesis returned meaningful results, return it
            if result.tone != "neutral" or result.vocabulary_level != "intermediate":
                return result
            
            # If synthesis failed, fall back to algorithmic merge
            logger.warning("Synthesis returned defaults, using algorithmic merge...")
            return self._algorithmic_merge(stored_results, all_phrases, all_patterns)
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return self._algorithmic_merge(stored_results, all_phrases, all_patterns)
    
    def _algorithmic_merge(self, stored_results: List[dict], 
                          all_phrases: List[str], 
                          all_patterns: List[str]) -> 'StyleProfile':
        """Fallback: Merge results using algorithm when AI synthesis fails"""
        from collections import Counter
        
        def most_common(values):
            # Filter out None, empty, and default values
            filtered = [v for v in values if v and v not in ['neutral', 'intermediate', 'mixed', 'moderate', 'general', '']]
            if not filtered:
                filtered = [v for v in values if v]
            if not filtered:
                return None
            return Counter(filtered).most_common(1)[0][0]
        
        tones = [r.get('tone') for r in stored_results]
        vocabs = [r.get('vocabulary_level') for r in stored_results]
        structures = [r.get('sentence_structure') for r in stored_results]
        pacings = [r.get('pacing') for r in stored_results]
        emotions = [r.get('emotional_range') for r in stored_results]
        audiences = [r.get('target_audience') for r in stored_results]
        
        # Deduplicate phrases and patterns
        unique_phrases = list(dict.fromkeys([p for p in all_phrases if p and p.strip()]))[:15]
        unique_patterns = list(dict.fromkeys([p for p in all_patterns if p and p.strip()]))[:10]
        
        return StyleProfile(
            tone=most_common(tones) or "neutral",
            vocabulary_level=most_common(vocabs) or "intermediate",
            sentence_structure=most_common(structures) or "mixed",
            pacing=most_common(pacings) or "moderate",
            key_phrases=unique_phrases,
            emotional_range=most_common(emotions) or "mixed",
            target_audience=most_common(audiences) or "general",
            unique_patterns=unique_patterns
        )
    
    def _extract_style_from_text(self, response: str) -> Optional['StyleProfile']:
        """Extract style info from text response when JSON parsing fails"""
        result = self._extract_dict_from_text(response)
        if result:
            return StyleProfile(
                tone=result.get('tone', 'neutral'),
                vocabulary_level=result.get('vocabulary_level', 'intermediate'),
                sentence_structure=result.get('sentence_structure', 'mixed'),
                pacing=result.get('pacing', 'moderate'),
                key_phrases=result.get('key_phrases', []),
                emotional_range=result.get('emotional_range', 'mixed'),
                target_audience=result.get('target_audience', 'general'),
                unique_patterns=result.get('unique_patterns', [])
            )
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCRIPT CHUNKING UTILITIES - For handling long scripts
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Maximum characters per script chunk (50K chars ≈ 12.5K tokens)
    # GPT-5.2 can handle 100K+ tokens, so this is conservative
    MAX_SCRIPT_CHARS = 50000
    
    def _chunk_script(self, script: str, max_chars: int = None) -> List[str]:
        """
        Split a long script into smaller chunks by paragraph boundaries.
        If script is shorter than max_chars, returns [script] unchanged.
        
        Args:
            script: The script text to chunk
            max_chars: Maximum characters per chunk (default: MAX_SCRIPT_CHARS)
            
        Returns:
            List of script chunks
        """
        max_chars = max_chars or self.MAX_SCRIPT_CHARS
        
        if len(script) <= max_chars:
            return [script]
        
        chunks = []
        # Split by double newline (paragraphs) first
        paragraphs = script.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            # If adding this paragraph would exceed limit
            if len(current_chunk) + len(para) + 2 > max_chars:
                # Save current chunk if not empty
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # If single paragraph is too long, split by sentences
                if len(para) > max_chars:
                    sentences = para.replace('. ', '.\n').split('\n')
                    sub_chunk = ""
                    for sentence in sentences:
                        if len(sub_chunk) + len(sentence) + 1 > max_chars:
                            if sub_chunk.strip():
                                chunks.append(sub_chunk.strip())
                            sub_chunk = sentence + " "
                        else:
                            sub_chunk += sentence + " "
                    current_chunk = sub_chunk
                else:
                    current_chunk = para + "\n\n"
            else:
                current_chunk += para + "\n\n"
        
        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        logger.info(f"📦 Script chunked: {len(script)} chars → {len(chunks)} chunks")
        return chunks
    
    def _merge_chunk_analyses(self, chunk_analyses: List[Dict]) -> Dict:
        """
        Merge multiple chunk analysis results into a single coherent analysis.
        
        Strategy:
        - String fields: Take the most comprehensive/longest description
        - List fields: Combine and deduplicate
        - Nested dicts: Merge recursively
        
        Args:
            chunk_analyses: List of analysis dicts from each chunk
            
        Returns:
            Merged analysis dict
        """
        if not chunk_analyses:
            return {}
        
        if len(chunk_analyses) == 1:
            return chunk_analyses[0]
        
        merged = {}
        
        # Fields to take longest/most comprehensive
        string_fields = ['core_angle', 'viewer_insight', 'cultural_context', 
                        'narrative_voice', 'retention_engine', 'cta_strategy']
        
        for field in string_fields:
            values = [ca.get(field, '') for ca in chunk_analyses if ca.get(field)]
            if values:
                # Take the longest (most detailed) description
                merged[field] = max(values, key=len)
        
        # List fields to combine
        list_fields = ['main_ideas', 'unique_patterns']
        for field in list_fields:
            combined = []
            for ca in chunk_analyses:
                items = ca.get(field, [])
                if isinstance(items, list):
                    combined.extend(items)
            # Deduplicate while preserving order
            merged[field] = list(dict.fromkeys(combined))[:10]
        
        # Nested dict: hook_analysis
        hook_analyses = [ca.get('hook_analysis', {}) for ca in chunk_analyses if ca.get('hook_analysis')]
        if hook_analyses:
            merged['hook_analysis'] = {
                'hook_type': hook_analyses[0].get('hook_type', ''),  # First chunk usually has the hook
                'hook_effectiveness': hook_analyses[0].get('hook_effectiveness', ''),
                'hook_elements': list(dict.fromkeys([
                    elem for ha in hook_analyses 
                    for elem in ha.get('hook_elements', []) if elem
                ]))[:5]
            }
        
        # Nested dict: writing_style
        style_analyses = [ca.get('writing_style', {}) for ca in chunk_analyses if ca.get('writing_style')]
        if style_analyses:
            merged['writing_style'] = {
                'tone': style_analyses[0].get('tone', ''),
                'vocabulary': max([sa.get('vocabulary', '') for sa in style_analyses], key=len) if style_analyses else '',
                'sentence_structure': max([sa.get('sentence_structure', '') for sa in style_analyses], key=len) if style_analyses else ''
            }
        
        logger.info(f"🔗 Merged {len(chunk_analyses)} chunk analyses into 1")
        return merged
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 3-STEP STYLE ANALYSIS → PHONG CÁCH VĂN A
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_to_style_a(self, scripts: List[str], progress_callback=None, analysis_language: str = "auto") -> Tuple['StyleA', List[Dict]]:
        """
        3-Step Style Analysis Workflow → Đúc kết Phong cách văn A
        
        🔄 SỬ DỤNG 1 CONVERSATION LIÊN TỤC để AI ghi nhớ context từ tất cả scripts
        🔄 HỖ TRỢ AUTO-CHUNKING cho scripts dài (>50K chars)
        🔄 AUTO-DETECT ngôn ngữ từ scripts và dùng prompts tương ứng
        
        STEP 1: Init conversation với system context
        STEP 2: Phân tích từng kịch bản (trong conversation) - Core Angle, INSIGHT, HOOK, Văn phong
        STEP 3: Đúc kết thành "Phong cách văn A" - AI tổng hợp từ memory
        
        Returns:
            Tuple[StyleA, List[Dict]]: StyleA profile và danh sách kết quả phân tích từng script
        """
        if not scripts:
            logger.warning("No scripts provided for StyleA analysis")
            return StyleA(), []
        
        scripts_to_analyze = scripts[:20]
        num_scripts = len(scripts_to_analyze)
        
        # ═══════════════════════════════════════════════════════════════════════
        # AUTO-DETECT LANGUAGE from input scripts
        # ═══════════════════════════════════════════════════════════════════════
        def detect_language(text: str) -> str:
            """Detect language from text using character analysis"""
            import re
            
            # Sample first 2000 chars for detection
            sample = text[:2000]
            
            # Count character types
            vietnamese_chars = len(re.findall(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]', sample, re.IGNORECASE))
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', sample))
            japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', sample))  # Hiragana + Katakana
            korean_chars = len(re.findall(r'[\uac00-\ud7af\u1100-\u11ff]', sample))
            
            # Determine primary language
            if vietnamese_chars > 20:
                return 'vi'
            elif japanese_chars > 10 or (chinese_chars > 10 and japanese_chars > 0):
                return 'ja'
            elif korean_chars > 10:
                return 'ko'
            elif chinese_chars > 20:
                return 'zh'
            else:
                return 'en'  # Default to English
        
        # Combine first 3 scripts for better language detection
        combined_text = ' '.join(scripts_to_analyze[:3])
        detected_lang = detect_language(combined_text) if analysis_language == "auto" else analysis_language
        
        # ═══════════════════════════════════════════════════════════════════════
        # MULTI-LANGUAGE PROMPT TEMPLATES
        # ═══════════════════════════════════════════════════════════════════════
        PROMPTS = {
            'vi': {
                'name': 'Tiếng Việt',
                'system': """Bạn là chuyên gia phân tích văn phong và script cho video content.

NHIỆM VỤ: Phân tích từng kịch bản được gửi đến và GHI NHỚ tất cả đặc điểm để cuối cùng tổng hợp thành "Phong cách văn A".

QUY TẮC:
1. Mỗi kịch bản: Trả về phân tích chi tiết dạng JSON
2. GHI NHỚ: Tất cả patterns, style, techniques qua từng kịch bản
3. Khi được yêu cầu TỔNG HỢP: Đúc kết từ TẤT CẢ kịch bản đã phân tích
4. Output PHẢI viết bằng tiếng Việt CÓ DẤU

Hãy sẵn sàng phân tích!""",
                'analyze': """Phân tích chi tiết KỊCH BẢN #{script_num}{chunk_context}. Trả về CHÍNH XÁC JSON sau:

{{
    "core_angle": "Góc nhìn cốt lõi của video - ý tưởng chủ đạo",
    "main_ideas": ["Ý chính 1", "Ý chính 2"],
    "viewer_insight": "INSIGHT người xem - pain point hoặc gain point",
    "hook_analysis": {{
        "hook_type": "loại hook: curiosity/shock/emotional/question/bold_claim/story/list",
        "hook_effectiveness": "đánh giá 1-10 và lý do",
        "hook_elements": ["yếu tố 1", "yếu tố 2"]
    }},
    "writing_style": {{
        "tone": "formal/casual/humorous/serious/inspirational/educational",
        "vocabulary": "đặc điểm từ vựng",
        "sentence_structure": "đặc điểm câu văn"
    }},
    "cultural_context": "văn hóa thể hiện",
    "narrative_voice": "ngôi kể",
    "retention_engine": "cơ chế giữ người xem",
    "cta_strategy": "cách call-to-action",
    "unique_patterns": ["pattern độc đáo 1", "pattern 2"]
}}

KỊCH BẢN #{script_num}{chunk_context}:
\"\"\"
{script_content}
\"\"\"""",
                'progress_init': "StyleA: {n} kịch bản...",
                'progress_connecting': "Kết nối AI...",
                'progress_connected': "AI sẵn sàng",
                'progress_analyzing': "Phân tích {i}/{n} ({chars} ký tự)...",
                'progress_chunking': "Chia {i}: {chunks} phần...",
                'progress_analyzed': "Xong {i}/{n}",
                'progress_synthesizing': "Tổng hợp StyleA: {n} kịch bản...",
                'progress_complete': "StyleA xong, độ tin cậy: {score}",
                'synthesis': """Bây giờ, dựa trên TẤT CẢ {num_scripts} kịch bản bạn vừa phân tích, hãy ĐÚC KẾT thành "PHONG CÁCH VĂN A".

⚠️ QUY TẮC QUAN TRỌNG:
1. KHÔNG được nhắc đến nội dung cụ thể của bất kỳ kịch bản nào (tên người, địa danh, sự kiện)
2. CHỈ mô tả PATTERNS, TECHNIQUES, và STYLE chung xuất hiện xuyên suốt {num_scripts} kịch bản
3. Mỗi trường phải là MÔ TẢ TỔNG QUÁT áp dụng được cho TẤT CẢ scripts

Trả về JSON với 2 NHÓM RÕ RÀNG:

{{
    "_comment_DNA": "=== DNA CỐ ĐỊNH - Không đổi theo kịch bản ===",
    
    "voice_description": "Mô tả GIỌNG VĂN CHUNG: personality, ngữ điệu, cách xưng hô (3-5 câu)",
    "storytelling_approach": "Mô tả CÁCH DẪN CHUYỆN ĐẶC TRƯNG: cấu trúc, tension, flow (3-5 câu)",
    "character_embodiment": "Mô tả CÁCH NHẬP VAI CHUNG: persona, relationship với người xem (2-3 câu)",
    "authors_soul": "HỒN VĂN - essence/chất riêng làm nên style UNIQUE (3-5 câu)",
    
    "common_hook_types": ["hook pattern 1", "hook pattern 2"],
    "retention_techniques": ["kỹ thuật giữ viewer 1", "kỹ thuật 2", "kỹ thuật 3"],
    "cta_patterns": ["CTA pattern 1", "CTA pattern 2"],
    
    "tone_spectrum": "Phổ tone tổng thể",
    "vocabulary_signature": "Đặc điểm từ vựng chung",
    "emotional_palette": "Các cảm xúc thường xuất hiện",
    
    "script_structure": {{
        "avg_word_count": 1500,
        "hook_duration": "10-15 giây đầu",
        "intro_segments": 2,
        "intro_purpose": "Gây tò mò, thiết lập bối cảnh",
        "body_segments": 4,
        "body_purpose": "Triển khai nội dung chính",
        "conclusion_segments": 1,
        "conclusion_purpose": "Kết luận và CTA",
        "climax_position": "70-80% của video"
    }},
    
    "signature_phrases": ["cụm từ hay dùng 1", "cụm từ 2", "cụm từ 3"],
    "unique_patterns": ["pattern độc đáo 1", "pattern 2"],
    
    "_comment_customizable": "=== TÙY BIẾN ===",
    
    "narrative_perspective": "Ngôi kể ưa thích",
    "audience_address": "Cách xưng hô với khán giả",
    "cultural_markers": "Dấu ấn văn hóa/vùng miền",
    
    "confidence_score": 0.85
}}

⚠️ Output PHẢI viết bằng tiếng Việt CÓ DẤU đầy đủ."""
            },
            'en': {
                'name': 'English',
                'system': """You are an expert in writing style and video script analysis.

TASK: Analyze each script sent to you and REMEMBER all characteristics to finally synthesize into "Writing Style Profile A".

RULES:
1. Each script: Return detailed analysis in JSON format
2. REMEMBER: All patterns, styles, techniques across all scripts
3. When asked to SYNTHESIZE: Consolidate from ALL analyzed scripts
4. Output MUST be in English

Ready to analyze!""",
                'analyze': """Analyze SCRIPT #{script_num}{chunk_context} in detail. Return EXACTLY this JSON:

{{
    "core_angle": "Core perspective of the video - main idea driving the content",
    "main_ideas": ["Main idea 1", "Main idea 2"],
    "viewer_insight": "Viewer INSIGHT - pain point or gain point being addressed",
    "hook_analysis": {{
        "hook_type": "hook type: curiosity/shock/emotional/question/bold_claim/story/list",
        "hook_effectiveness": "rating 1-10 and reasoning",
        "hook_elements": ["element 1", "element 2"]
    }},
    "writing_style": {{
        "tone": "formal/casual/humorous/serious/inspirational/educational",
        "vocabulary": "vocabulary characteristics",
        "sentence_structure": "sentence structure patterns"
    }},
    "cultural_context": "cultural elements expressed",
    "narrative_voice": "narrative perspective",
    "retention_engine": "viewer retention mechanism",
    "cta_strategy": "call-to-action approach",
    "unique_patterns": ["unique pattern 1", "pattern 2"]
}}

SCRIPT #{script_num}{chunk_context}:
\"\"\"
{script_content}
\"\"\"""",
                'progress_init': "StyleA: {n} scripts...",
                'progress_connecting': "Connecting to AI...",
                'progress_connected': "AI ready",
                'progress_analyzing': "Analyzing {i}/{n} ({chars} chars)...",
                'progress_chunking': "Splitting {i}: {chunks} parts...",
                'progress_analyzed': "Done {i}/{n}",
                'progress_synthesizing': "Synthesizing StyleA: {n} scripts...",
                'progress_complete': "StyleA done, confidence: {score}",
                'synthesis': """Now, based on ALL {num_scripts} scripts you just analyzed, SYNTHESIZE into "WRITING STYLE PROFILE A".

⚠️ IMPORTANT RULES:
1. DO NOT mention specific content from any script (names, places, events)
2. ONLY describe PATTERNS, TECHNIQUES, and STYLE that appear consistently across all {num_scripts} scripts
3. Each field must be a GENERAL DESCRIPTION applicable to ALL scripts

Return JSON with 2 CLEAR GROUPS:

{{
    "_comment_DNA": "=== FIXED DNA - Does not change per script ===",
    
    "voice_description": "COMMON VOICE description: personality, tone, address style (3-5 sentences)",
    "storytelling_approach": "CHARACTERISTIC STORYTELLING: structure, tension, flow (3-5 sentences)",
    "character_embodiment": "COMMON CHARACTER APPROACH: author persona, relationship with viewer (2-3 sentences)",
    "authors_soul": "WRITING SOUL - unique essence/character that defines the style (3-5 sentences)",
    
    "common_hook_types": ["hook pattern 1", "hook pattern 2"],
    "retention_techniques": ["viewer retention technique 1", "technique 2", "technique 3"],
    "cta_patterns": ["CTA pattern 1", "CTA pattern 2"],
    
    "tone_spectrum": "Overall tone spectrum",
    "vocabulary_signature": "Common vocabulary characteristics",
    "emotional_palette": "Commonly expressed emotions",
    
    "script_structure": {{
        "avg_word_count": 1500,
        "hook_duration": "First 10-15 seconds",
        "intro_segments": 2,
        "intro_purpose": "Create curiosity, establish context",
        "body_segments": 4,
        "body_purpose": "Develop main content",
        "conclusion_segments": 1,
        "conclusion_purpose": "Conclusion and CTA",
        "climax_position": "70-80% of video"
    }},
    
    "signature_phrases": ["commonly used phrase 1", "phrase 2", "phrase 3"],
    "unique_patterns": ["unique pattern 1", "pattern 2"],
    
    "_comment_customizable": "=== CUSTOMIZABLE ===",
    
    "narrative_perspective": "Preferred narrative voice",
    "audience_address": "How the audience is addressed",
    "cultural_markers": "Cultural/regional markers",
    
    "confidence_score": 0.85
}}

⚠️ Output MUST be in English."""
            },
            'zh': {
                'name': '中文',
                'system': """您是视频脚本和写作风格分析专家。

任务：分析发送给您的每个脚本，并记住所有特征，最终综合成"写作风格A"。

规则：
1. 每个脚本：返回JSON格式的详细分析
2. 记住：所有脚本中的模式、风格、技巧
3. 当被要求综合时：从所有已分析的脚本中总结
4. 输出必须使用中文

准备好分析！""",
                'analyze': """详细分析脚本 #{script_num}{chunk_context}。返回以下JSON：

{{
    "core_angle": "视频的核心视角 - 主导内容的核心理念",
    "main_ideas": ["主要观点1", "主要观点2"],
    "viewer_insight": "观众洞察 - 痛点或收益点",
    "hook_analysis": {{
        "hook_type": "钩子类型：curiosity/shock/emotional/question/bold_claim/story/list",
        "hook_effectiveness": "评分1-10及原因",
        "hook_elements": ["元素1", "元素2"]
    }},
    "writing_style": {{
        "tone": "正式/轻松/幽默/严肃/励志/教育",
        "vocabulary": "词汇特点",
        "sentence_structure": "句式结构特点"
    }},
    "cultural_context": "文化元素",
    "narrative_voice": "叙述视角",
    "retention_engine": "观众留存机制",
    "cta_strategy": "行动号召策略",
    "unique_patterns": ["独特模式1", "模式2"]
}}

脚本 #{script_num}{chunk_context}：
\"\"\"
{script_content}
\"\"\"""",
                'progress_init': "StyleA: {n} 个脚本...",
                'progress_connecting': "连接AI...",
                'progress_connected': "AI就绪",
                'progress_analyzing': "分析 {i}/{n}（{chars}字符）...",
                'progress_chunking': "拆分 {i}: {chunks} 部分...",
                'progress_analyzed': "完成 {i}/{n}",
                'progress_synthesizing': "综合StyleA: {n}个脚本...",
                'progress_complete': "StyleA完成，置信度：{score}",
                'synthesis': """现在，根据您刚刚分析的所有 {num_scripts} 个脚本，综合成"写作风格A"。

⚠️ 重要规则：
1. 不要提及任何脚本的具体内容（人名、地名、事件）
2. 只描述在所有 {num_scripts} 个脚本中一致出现的模式、技巧和风格
3. 每个字段必须是适用于所有脚本的一般性描述

返回包含2个明确分组的JSON：

{{
    "_comment_DNA": "=== 固定DNA - 不随脚本变化 ===",
    
    "voice_description": "通用声音描述：个性、语调、称呼方式（3-5句）",
    "storytelling_approach": "特征叙事：结构、张力、流程（3-5句）",
    "character_embodiment": "通用角色方法：作者角色、与观众的关系（2-3句）",
    "authors_soul": "写作灵魂 - 定义风格的独特本质/特征（3-5句）",
    
    "common_hook_types": ["钩子模式1", "钩子模式2"],
    "retention_techniques": ["观众留存技巧1", "技巧2", "技巧3"],
    "cta_patterns": ["CTA模式1", "CTA模式2"],
    
    "tone_spectrum": "整体语调范围",
    "vocabulary_signature": "通用词汇特征",
    "emotional_palette": "常见情感表达",
    
    "script_structure": {{
        "avg_word_count": 1500,
        "hook_duration": "前10-15秒",
        "intro_segments": 2,
        "intro_purpose": "创造好奇心，建立背景",
        "body_segments": 4,
        "body_purpose": "发展主要内容",
        "conclusion_segments": 1,
        "conclusion_purpose": "结论和CTA",
        "climax_position": "视频的70-80%"
    }},
    
    "signature_phrases": ["常用短语1", "短语2", "短语3"],
    "unique_patterns": ["独特模式1", "模式2"],
    
    "_comment_customizable": "=== 可自定义 ===",
    
    "narrative_perspective": "首选叙事视角",
    "audience_address": "如何称呼观众",
    "cultural_markers": "文化/地区标记",
    
    "confidence_score": 0.85
}}

⚠️ 输出必须使用中文。"""
            },
            'ja': {
                'name': '日本語',
                'system': """あなたはビデオスクリプトとライティングスタイルの分析専門家です。

タスク：送られてくる各スクリプトを分析し、すべての特徴を記憶して、最終的に「ライティングスタイルA」に統合します。

ルール：
1. 各スクリプト：JSON形式で詳細な分析を返す
2. 記憶：すべてのスクリプトのパターン、スタイル、テクニック
3. 統合を求められたら：分析したすべてのスクリプトから統合
4. 出力は日本語で

分析開始準備完了！""",
                'analyze': """スクリプト #{script_num}{chunk_context} を詳細に分析してください。以下のJSONを返してください：

{{
    "core_angle": "ビデオのコアな視点 - メインアイデア",
    "main_ideas": ["主要アイデア1", "主要アイデア2"],
    "viewer_insight": "視聴者インサイト - ペインポイントまたはゲインポイント",
    "hook_analysis": {{
        "hook_type": "フックタイプ：curiosity/shock/emotional/question/bold_claim/story/list",
        "hook_effectiveness": "1-10の評価と理由",
        "hook_elements": ["要素1", "要素2"]
    }},
    "writing_style": {{
        "tone": "フォーマル/カジュアル/ユーモラス/シリアス/インスピレーショナル/教育的",
        "vocabulary": "語彙の特徴",
        "sentence_structure": "文構造のパターン"
    }},
    "cultural_context": "文化的要素",
    "narrative_voice": "語り手の視点",
    "retention_engine": "視聴者維持メカニズム",
    "cta_strategy": "CTAアプローチ",
    "unique_patterns": ["ユニークパターン1", "パターン2"]
}}

スクリプト #{script_num}{chunk_context}：
\"\"\"
{script_content}
\"\"\"""",
                'progress_init': "StyleA: {n}個のスクリプト...",
                'progress_connecting': "AIに接続中...",
                'progress_connected': "AI準備完了",
                'progress_analyzing': "分析中 {i}/{n}（{chars}文字）...",
                'progress_chunking': "分割 {i}: {chunks}パート...",
                'progress_analyzed': "完了 {i}/{n}",
                'progress_synthesizing': "StyleA統合: {n}個...",
                'progress_complete': "StyleA完成、信頼度: {score}",
                'synthesis': """さて、分析した {num_scripts} 個のスクリプトすべてに基づいて、「ライティングスタイルA」に統合してください。

⚠️ 重要なルール：
1. スクリプトの具体的な内容（名前、場所、イベント）には言及しないでください
2. {num_scripts} 個すべてのスクリプトで一貫して現れるパターン、テクニック、スタイルのみを記述してください
3. 各フィールドはすべてのスクリプトに適用できる一般的な説明でなければなりません

2つの明確なグループを持つJSONを返してください：

{{
    "_comment_DNA": "=== 固定DNA - スクリプトごとに変わらない ===",
    
    "voice_description": "共通の声の説明：個性、トーン、呼びかけスタイル（3-5文）",
    "storytelling_approach": "特徴的なストーリーテリング：構造、テンション、フロー（3-5文）",
    "character_embodiment": "共通のキャラクターアプローチ：著者のペルソナ、視聴者との関係（2-3文）",
    "authors_soul": "ライティングソウル - スタイルを定義するユニークなエッセンス/特徴（3-5文）",
    
    "common_hook_types": ["フックパターン1", "フックパターン2"],
    "retention_techniques": ["視聴者維持テクニック1", "テクニック2", "テクニック3"],
    "cta_patterns": ["CTAパターン1", "CTAパターン2"],
    
    "tone_spectrum": "全体的なトーンスペクトラム",
    "vocabulary_signature": "共通の語彙特性",
    "emotional_palette": "よく表現される感情",
    
    "script_structure": {{
        "avg_word_count": 1500,
        "hook_duration": "最初の10-15秒",
        "intro_segments": 2,
        "intro_purpose": "好奇心を創造し、コンテキストを確立",
        "body_segments": 4,
        "body_purpose": "メインコンテンツを展開",
        "conclusion_segments": 1,
        "conclusion_purpose": "結論とCTA",
        "climax_position": "動画の70-80%"
    }},
    
    "signature_phrases": ["よく使うフレーズ1", "フレーズ2", "フレーズ3"],
    "unique_patterns": ["ユニークパターン1", "パターン2"],
    
    "_comment_customizable": "=== カスタマイズ可能 ===",
    
    "narrative_perspective": "好みのナラティブボイス",
    "audience_address": "視聴者への呼びかけ方",
    "cultural_markers": "文化的/地域的マーカー",
    
    "confidence_score": 0.85
}}

⚠️ 出力は日本語でなければなりません。"""
            },
            'ko': {
                'name': '한국어',
                'system': """당신은 비디오 스크립트와 글쓰기 스타일 분석 전문가입니다.

작업: 전송된 각 스크립트를 분석하고 모든 특징을 기억하여 최종적으로 "글쓰기 스타일 A"로 통합합니다.

규칙:
1. 각 스크립트: JSON 형식으로 상세 분석 반환
2. 기억: 모든 스크립트의 패턴, 스타일, 기법
3. 통합 요청 시: 분석한 모든 스크립트에서 통합
4. 출력은 한국어로

분석 준비 완료!""",
                'analyze': """스크립트 #{script_num}{chunk_context}을(를) 상세히 분석하세요. 다음 JSON을 반환하세요:

{{
    "core_angle": "비디오의 핵심 관점 - 주요 아이디어",
    "main_ideas": ["주요 아이디어 1", "주요 아이디어 2"],
    "viewer_insight": "시청자 인사이트 - 페인 포인트 또는 게인 포인트",
    "hook_analysis": {{
        "hook_type": "훅 유형: curiosity/shock/emotional/question/bold_claim/story/list",
        "hook_effectiveness": "1-10 점수와 이유",
        "hook_elements": ["요소 1", "요소 2"]
    }},
    "writing_style": {{
        "tone": "공식적/캐주얼/유머러스/진지한/영감을주는/교육적",
        "vocabulary": "어휘 특성",
        "sentence_structure": "문장 구조 패턴"
    }},
    "cultural_context": "문화적 요소",
    "narrative_voice": "서술 시점",
    "retention_engine": "시청자 유지 메커니즘",
    "cta_strategy": "CTA 접근 방식",
    "unique_patterns": ["고유 패턴 1", "패턴 2"]
}}

스크립트 #{script_num}{chunk_context}:
\"\"\"
{script_content}
\"\"\"""",
                'progress_init': "StyleA: {n}개 스크립트...",
                'progress_connecting': "AI 연결중...",
                'progress_connected': "AI 준비 완료",
                'progress_analyzing': "분석 {i}/{n} ({chars}자)...",
                'progress_chunking': "분할 {i}: {chunks}개 파트...",
                'progress_analyzed': "완료 {i}/{n}",
                'progress_synthesizing': "StyleA 통합: {n}개...",
                'progress_complete': "StyleA 완성, 신뢰도: {score}",
                'synthesis': """이제 방금 분석한 모든 {num_scripts}개 스크립트를 기반으로 "글쓰기 스타일 A"로 통합하세요.

⚠️ 중요한 규칙:
1. 스크립트의 구체적인 내용(이름, 장소, 이벤트)을 언급하지 마세요
2. 모든 {num_scripts}개 스크립트에서 일관되게 나타나는 패턴, 기법, 스타일만 설명하세요
3. 각 필드는 모든 스크립트에 적용 가능한 일반적인 설명이어야 합니다

2개의 명확한 그룹을 가진 JSON을 반환하세요:

{{
    "_comment_DNA": "=== 고정 DNA - 스크립트마다 변하지 않음 ===",
    
    "voice_description": "공통 보이스 설명: 개성, 톤, 호칭 스타일 (3-5문장)",
    "storytelling_approach": "특징적인 스토리텔링: 구조, 텐션, 흐름 (3-5문장)",
    "character_embodiment": "공통 캐릭터 접근법: 저자 페르소나, 시청자와의 관계 (2-3문장)",
    "authors_soul": "글쓰기 영혼 - 스타일을 정의하는 고유한 본질/특성 (3-5문장)",
    
    "common_hook_types": ["훅 패턴 1", "훅 패턴 2"],
    "retention_techniques": ["시청자 유지 기법 1", "기법 2", "기법 3"],
    "cta_patterns": ["CTA 패턴 1", "CTA 패턴 2"],
    
    "tone_spectrum": "전체 톤 스펙트럼",
    "vocabulary_signature": "공통 어휘 특성",
    "emotional_palette": "자주 표현되는 감정",
    
    "script_structure": {{
        "avg_word_count": 1500,
        "hook_duration": "처음 10-15초",
        "intro_segments": 2,
        "intro_purpose": "호기심 유발, 맥락 설정",
        "body_segments": 4,
        "body_purpose": "메인 콘텐츠 전개",
        "conclusion_segments": 1,
        "conclusion_purpose": "결론 및 CTA",
        "climax_position": "영상의 70-80%"
    }},
    
    "signature_phrases": ["자주 사용하는 표현 1", "표현 2", "표현 3"],
    "unique_patterns": ["고유 패턴 1", "패턴 2"],
    
    "_comment_customizable": "=== 사용자 정의 가능 ===",
    
    "narrative_perspective": "선호하는 내레이티브 보이스",
    "audience_address": "시청자 호칭 방법",
    "cultural_markers": "문화적/지역적 마커",
    
    "confidence_score": 0.85
}}

⚠️ 출력은 한국어여야 합니다."""
            }
        }
        
        # Get prompts for detected language (fallback to English)
        prompts = PROMPTS.get(detected_lang, PROMPTS['en'])
        
        logger.info(f"🚀 [0%] Starting StyleA analysis for {num_scripts} scripts (detected language: {prompts['name']})...")
        
        def _progress(step: str, percentage: int, message: str):
            """Send progress update"""
            if progress_callback:
                try:
                    progress_callback(step, percentage, message)
                except Exception:
                    pass
        
        _progress("init", 2, prompts['progress_init'].format(n=num_scripts))
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 1: Start conversation với system context
        # ═══════════════════════════════════════════════════════════════════════
        conversation_id = None
        individual_analyses = []
        
        try:
            # Check if any provider supports conversations
            if self.ai_client.has_conversation_support():
                logger.info(f"[5%] Connecting to AI ({prompts['name']})...")
                _progress("connecting", 5, prompts['progress_connecting'])
                
                # Start conversation with system prompt (language-aware)
                system_prompt = prompts['system']

                conversation_id = self.ai_client.start_conversation(system_prompt)
                logger.info(f"📤 [10%] Connected! Conversation: {conversation_id[:8]}...")
                _progress("connected", 10, prompts['progress_connected'])
                
                # ═══════════════════════════════════════════════════════════════════════
                # STEP 2: Analyze each script IN CONVERSATION (with auto-chunking)
                # ═══════════════════════════════════════════════════════════════════════
                for i, script in enumerate(scripts_to_analyze, 1):
                    # Distribute analyzing phase evenly across 10%-65%
                    pct = 10 + ((i - 1) * 55 // max(num_scripts, 1))
                    script_len = len(script)
                    logger.info(f"🔍 [{pct}%] STEP 1: Analyzing script {i}/{num_scripts} ({script_len} chars)...")
                    _progress(f"analyzing_{i}", pct, prompts['progress_analyzing'].format(i=i, n=num_scripts, chars=script_len))
                    
                    # Auto-chunk long scripts
                    script_chunks = self._chunk_script(script)
                    num_chunks = len(script_chunks)
                    
                    if num_chunks > 1:
                        logger.info(f"📦 Script {i} too long, split into {num_chunks} chunks")
                        _progress(f"chunking_{i}", pct, prompts['progress_chunking'].format(i=i, chunks=num_chunks))
                    
                    # Analyze each chunk
                    chunk_analyses = []
                    for chunk_idx, chunk in enumerate(script_chunks, 1):
                        chunk_context = f" (Part {chunk_idx}/{num_chunks})" if num_chunks > 1 else ""
                        
                        # Use language-specific analysis prompt
                        analysis_prompt = prompts['analyze'].format(
                            script_num=i,
                            chunk_context=chunk_context,
                            script_content=chunk
                        )
                        try:
                            response = self.ai_client.send_message(
                                conversation_id, 
                                analysis_prompt, 
                                temperature=0.3
                            )
                            
                            # Parse JSON response
                            parsed = self._parse_json_to_dict(response)
                            if parsed:
                                chunk_analyses.append(parsed)
                                if num_chunks > 1:
                                    logger.info(f"✅ Chunk {chunk_idx}/{num_chunks} of script {i} analyzed")
                        except Exception as e:
                            logger.error(f"❌ Error analyzing chunk {chunk_idx} of script {i}: {e}")
                    
                    # Merge chunk analyses if multiple chunks
                    if chunk_analyses:
                        if len(chunk_analyses) == 1:
                            merged_analysis = chunk_analyses[0]
                        else:
                            # Merge multiple chunk analyses
                            merged_analysis = self._merge_chunk_analyses(chunk_analyses)
                        
                        merged_analysis['script_number'] = i
                        merged_analysis['script_preview'] = script[:200] + "..."
                        merged_analysis['total_chars'] = script_len
                        merged_analysis['num_chunks'] = num_chunks
                        individual_analyses.append(merged_analysis)
                        done_pct = 10 + (i * 55 // max(num_scripts, 1))
                        logger.info(f"✅ [{done_pct}%] Script {i} analyzed ({num_chunks} chunks)")
                        _progress(f"analyzed_{i}", done_pct, prompts['progress_analyzed'].format(i=i, n=num_scripts))
                    else:
                        logger.warning(f"⚠️ Failed to parse analysis for script {i}")
                        individual_analyses.append({
                            'script_number': i,
                            'script_preview': script[:200] + "...",
                            'error': 'Parse failed'
                        })
            else:
                # Fallback: No provider configured - use legacy mode
                logger.info("[10%] No AI provider configured, using legacy mode...")
                for i, script in enumerate(scripts_to_analyze, 1):
                    logger.info(f"🔍 [{20 + (i * 30 // num_scripts)}%] STEP 2: Phân tích kịch bản {i}/{num_scripts} (legacy)...")
                    
                    analysis_prompt = f"""Phân tích chi tiết kịch bản sau. Trả về JSON object:

{{
    "core_angle": "Góc nhìn cốt lõi",
    "main_ideas": ["Ý chính 1", "Ý chính 2"],
    "viewer_insight": "INSIGHT người xem",
    "hook_analysis": {{"hook_type": "loại", "hook_effectiveness": "đánh giá", "hook_elements": []}},
    "writing_style": {{"tone": "tone", "vocabulary": "từ vựng", "sentence_structure": "cấu trúc"}},
    "cultural_context": "văn hóa",
    "narrative_voice": "ngôi kể",
    "retention_engine": "cơ chế giữ viewer",
    "cta_strategy": "CTA strategy",
    "unique_patterns": []
}}

KỊCH BẢN:
\"\"\"
{script[:6000]}
\"\"\"
"""
                    try:
                        response = self.ai_client.smart_task(
                            prompt=analysis_prompt,
                            task_type=TaskType.STYLE_ANALYSIS,
                            temperature=0.3
                        )
                        parsed = self._parse_json_to_dict(response)
                        if parsed:
                            parsed['script_number'] = i
                            parsed['script_preview'] = script[:200] + "..."
                            individual_analyses.append(parsed)
                            logger.info(f"✅ Script {i} analyzed")
                        else:
                            individual_analyses.append({
                                'script_number': i,
                                'script_preview': script[:200] + "...",
                                'error': 'Parse failed'
                            })
                    except Exception as e:
                        logger.error(f"❌ Error analyzing script {i}: {e}")
                        individual_analyses.append({
                            'script_number': i,
                            'script_preview': script[:200] + "...",
                            'error': str(e)
                        })
        
            # ═══════════════════════════════════════════════════════════════════════
            # STEP 3: Synthesize into Writing Style Profile A (IN CONVERSATION)
            # ═══════════════════════════════════════════════════════════════════════
            num_analyzed = len(individual_analyses)
            logger.info(f"🧠 [70%] STEP 3: Synthesizing StyleA from {num_analyzed} scripts...")
            _progress("synthesizing", 70, prompts['progress_synthesizing'].format(n=num_analyzed))
            
            # Send intermediate progress during synthesis wait
            import time
            _progress("synthesizing", 75, prompts['progress_synthesizing'].format(n=num_analyzed))
            
            if conversation_id and self.ai_client.has_conversation_support():
                # Synthesis in conversation mode - AI remembers all previous analyses
                synthesis_prompt = prompts['synthesis'].format(num_scripts=num_analyzed)

                try:
                    synthesis_response = self.ai_client.send_message(
                        conversation_id,
                        synthesis_prompt,
                        temperature=0.4
                    )
                    
                    # End conversation after synthesis
                    self.ai_client.end_conversation(conversation_id)
                    logger.info(f"🔚 Conversation ended: {conversation_id[:8]}...")
                    
                    # Parse and create StyleA
                    logger.info(f"📝 Synthesis response length: {len(synthesis_response) if synthesis_response else 0}")
                    synthesized = self._parse_json_to_dict(synthesis_response)
                    
                    if synthesized:
                        # Parse script_structure if present
                        script_struct = None
                        if 'script_structure' in synthesized:
                            ss = synthesized['script_structure']
                            script_struct = ScriptStructure(
                                avg_word_count=ss.get('avg_word_count', 0),
                                hook_duration=ss.get('hook_duration', ''),
                                intro_segments=ss.get('intro_segments', 0),
                                intro_purpose=ss.get('intro_purpose', ''),
                                body_segments=ss.get('body_segments', 0),
                                body_purpose=ss.get('body_purpose', ''),
                                conclusion_segments=ss.get('conclusion_segments', 0),
                                conclusion_purpose=ss.get('conclusion_purpose', ''),
                                climax_position=ss.get('climax_position', '')
                            )
                        
                        style_a = StyleA(
                            # DNA CỐ ĐỊNH
                            voice_description=synthesized.get('voice_description', ''),
                            storytelling_approach=synthesized.get('storytelling_approach', ''),
                            character_embodiment=synthesized.get('character_embodiment', ''),
                            authors_soul=synthesized.get('authors_soul', ''),
                            common_hook_types=synthesized.get('common_hook_types', []),
                            retention_techniques=synthesized.get('retention_techniques', []),
                            cta_patterns=synthesized.get('cta_patterns', []),
                            signature_phrases=synthesized.get('signature_phrases', []),
                            unique_patterns=synthesized.get('unique_patterns', []),
                            tone_spectrum=synthesized.get('tone_spectrum', ''),
                            vocabulary_signature=synthesized.get('vocabulary_signature', ''),
                            emotional_palette=synthesized.get('emotional_palette', ''),
                            script_structure=script_struct,
                            # TÙY BIẾN
                            narrative_perspective=synthesized.get('narrative_perspective', ''),
                            audience_address=synthesized.get('audience_address', ''),
                            cultural_markers=synthesized.get('cultural_markers', ''),
                            # METADATA
                            source_scripts_count=num_scripts,
                            confidence_score=synthesized.get('confidence_score', 0.7)
                        )
                        logger.info(f"✨ [95%] StyleA created! Confidence: {style_a.confidence_score}")
                        _progress("parsing", 90, prompts['progress_complete'].format(score=style_a.confidence_score))
                        _progress("complete", 100, prompts['progress_complete'].format(score=style_a.confidence_score))
                        return style_a, individual_analyses
                    else:
                        logger.error("❌ Failed to parse conversation synthesis")
                        return StyleA(source_scripts_count=num_scripts), individual_analyses
                        
                except Exception as e:
                    logger.error(f"❌ Error in conversation synthesis: {e}")
                    if conversation_id:
                        self.ai_client.end_conversation(conversation_id)
                    return StyleA(source_scripts_count=num_scripts), individual_analyses
            else:
                # Fallback: Legacy synthesis with full JSON re-send
                analyses_summary = json.dumps(individual_analyses, ensure_ascii=False, indent=2)
                
                synthesis_prompt = f"""Based on ALL the analysis results below, SYNTHESIZE them into a "WRITING STYLE A" profile.

ANALYSIS RESULTS FROM {len(individual_analyses)} SCRIPTS:
{analyses_summary}

Return JSON:
{{
    "voice_description": "Describe the writing voice (3-5 sentences)",
    "storytelling_approach": "How stories are told (3-5 sentences)",
    "character_embodiment": "How characters are embodied (2-3 sentences)",
    "authors_soul": "The SOUL of the writing (3-5 sentences)",
    "common_hook_types": ["hook 1", "hook 2"],
    "retention_techniques": ["technique 1", "technique 2"],
    "cta_patterns": ["CTA 1", "CTA 2"],
    "tone_spectrum": "Tone range",
    "vocabulary_signature": "Signature vocabulary",
    "sentence_rhythm": "Sentence rhythm patterns",
    "emotional_palette": "Emotional palette",
    "cultural_markers": "Cultural markers",
    "narrative_perspective": "Narrative perspective",
    "signature_phrases": ["phrase 1", "phrase 2"],
    "unique_patterns": ["pattern 1", "pattern 2"],
    "confidence_score": 0.85
}}
"""
                try:
                    synthesis_response = self.ai_client.smart_task(
                        prompt=synthesis_prompt,
                        task_type=TaskType.STYLE_ANALYSIS,
                        temperature=0.4
                    )
                    
                    synthesized = self._parse_json_to_dict(synthesis_response)
                    
                    if synthesized:
                        style_a = StyleA(
                            voice_description=synthesized.get('voice_description', ''),
                            storytelling_approach=synthesized.get('storytelling_approach', ''),
                            character_embodiment=synthesized.get('character_embodiment', ''),
                            authors_soul=synthesized.get('authors_soul', ''),
                            common_hook_types=synthesized.get('common_hook_types', []),
                            retention_techniques=synthesized.get('retention_techniques', []),
                            cta_patterns=synthesized.get('cta_patterns', []),
                            tone_spectrum=synthesized.get('tone_spectrum', ''),
                            vocabulary_signature=synthesized.get('vocabulary_signature', ''),
                            sentence_rhythm=synthesized.get('sentence_rhythm', ''),
                            emotional_palette=synthesized.get('emotional_palette', ''),
                            cultural_markers=synthesized.get('cultural_markers', ''),
                            narrative_perspective=synthesized.get('narrative_perspective', ''),
                            audience_address=synthesized.get('audience_address', ''),
                            signature_phrases=synthesized.get('signature_phrases', []),
                            unique_patterns=synthesized.get('unique_patterns', []),
                            source_scripts_count=num_scripts,
                            confidence_score=synthesized.get('confidence_score', 0.7)
                        )
                        logger.info(f"✨ [95%] StyleA đã tạo xong (legacy)! Độ tin cậy: {style_a.confidence_score}")
                        _progress("complete", 100, f"StyleA xong, độ tin cậy: {style_a.confidence_score}")
                        return style_a, individual_analyses
                    else:
                        return StyleA(source_scripts_count=num_scripts), individual_analyses
                        
                except Exception as e:
                    logger.error(f"❌ Error in legacy synthesis: {e}")
                    return StyleA(source_scripts_count=num_scripts), individual_analyses
                    
        except Exception as e:
            # Outer exception handler for entire method
            import traceback
            logger.error(f"❌ Critical error in analyze_to_style_a: {e}")
            logger.error(traceback.format_exc())
            if conversation_id:
                try:
                    self.ai_client.end_conversation(conversation_id)
                except:
                    pass
            return StyleA(source_scripts_count=num_scripts), []



# ═══════════════════════════════════════════════════════════════════════════
# ADVANCED REMAKE WORKFLOW - 7 STEP PROCESS
# ═══════════════════════════════════════════════════════════════════════════

class AdvancedRemakeWorkflow:
    """
    Advanced 7-Step Script Remake Workflow
    
    Quy trình 7 bước để viết lại kịch bản đảm bảo tương đồng với gốc:
    
    1. analyze_original_script() - Bóc tách nội dung gốc
    2. analyze_structure() - Phân tích cấu trúc
    3. create_outline_a() - Tạo Dàn ý A với phân bổ từ
    4. write_section_advanced() - Viết nội dung theo Dàn ý A
    5. review_similarity() - Kiểm tra tương đồng
    6. refine_section_advanced() - Tinh chỉnh từng phần
    7. add_value() - Thêm giá trị mới
    """
    
    def __init__(self, ai_client: Optional[HybridAIClient] = None):
        self.ai_client = ai_client or HybridAIClient()
    
    def _build_style_context(self, style_profile: Optional[Dict[str, Any]], language: str = "vi") -> str:
        """
        Build style context string from StyleA dict for injection into writing prompts.
        
        Uses English labels when language == "en", Vietnamese labels otherwise.
        
        Style A includes:
        - FIXED DNA: voice_description, storytelling_approach, authors_soul, patterns...
        - CUSTOMIZABLE: core_angle, viewer_insight, main_ideas (from original script)
        """
        if not style_profile:
            return ""
        
        is_en = language != "vi"
        context_parts = []
        
        # ═══════════════════════════════════════════════════════════════
        # FIXED DNA
        # ═══════════════════════════════════════════════════════════════
        
        # Voice Description
        if style_profile.get("voice_description"):
            label = "VOICE/STYLE" if is_en else "GIỌNG VĂN"
            context_parts.append(f"🎯 {label}:\n{style_profile['voice_description']}")
        
        # Storytelling Approach
        if style_profile.get("storytelling_approach"):
            label = "STORYTELLING APPROACH" if is_en else "CÁCH DẪN CHUYỆN"
            context_parts.append(f"📖 {label}:\n{style_profile['storytelling_approach']}")
        
        # Author's Soul
        if style_profile.get("authors_soul"):
            label = "AUTHOR'S SOUL" if is_en else "HỒN VĂN"
            context_parts.append(f"✨ {label}:\n{style_profile['authors_soul']}")
        
        # Character Embodiment
        if style_profile.get("character_embodiment"):
            label = "CHARACTER EMBODIMENT" if is_en else "CÁCH NHẬP VAI"
            context_parts.append(f"👤 {label}:\n{style_profile['character_embodiment']}")
        
        # Hook patterns
        if style_profile.get("common_hook_types"):
            hooks = style_profile["common_hook_types"]
            if isinstance(hooks, list) and hooks:
                context_parts.append(f"🪝 HOOK PATTERNS: {', '.join(hooks[:5])}")
        
        # Retention techniques
        if style_profile.get("retention_techniques"):
            retention = style_profile["retention_techniques"]
            if isinstance(retention, list) and retention:
                context_parts.append(f"🔄 RETENTION: {', '.join(retention[:5])}")
        
        # CTA patterns
        if style_profile.get("cta_patterns"):
            cta = style_profile["cta_patterns"]
            if isinstance(cta, list) and cta:
                context_parts.append(f"📢 CTA PATTERNS: {', '.join(cta[:5])}")
        
        # Tone, vocabulary, emotional
        style_info = []
        if style_profile.get("tone_spectrum"):
            style_info.append(f"Tone: {style_profile['tone_spectrum']}")
        if style_profile.get("vocabulary_signature"):
            vocab_label = "Vocabulary" if is_en else "Từ vựng"
            style_info.append(f"{vocab_label}: {style_profile['vocabulary_signature']}")
        if style_profile.get("emotional_palette"):
            emo_label = "Emotion" if is_en else "Cảm xúc"
            style_info.append(f"{emo_label}: {style_profile['emotional_palette']}")
        if style_info:
            style_label = "STYLE" if is_en else "PHONG CÁCH"
            context_parts.append(f"🎨 {style_label}: {' | '.join(style_info)}")
        
        # Signature phrases
        if style_profile.get("signature_phrases"):
            phrases = style_profile["signature_phrases"]
            if isinstance(phrases, list) and phrases:
                label = "SIGNATURE PHRASES" if is_en else "CỤM TỪ ĐẶC TRƯNG"
                context_parts.append(f"🔑 {label}: {', '.join(phrases[:5])}")
        
        # Unique patterns
        if style_profile.get("unique_patterns"):
            unique = style_profile["unique_patterns"]
            if isinstance(unique, list) and unique:
                label = "UNIQUE PATTERNS" if is_en else "PATTERN ĐỘC ĐÁO"
                context_parts.append(f"⭐ {label}: {', '.join(unique[:5])}")
        
        # ═══════════════════════════════════════════════════════════════
        # CUSTOMIZABLE (From original script)
        # ═══════════════════════════════════════════════════════════════
        
        # Core Angle
        if style_profile.get("core_angle"):
            context_parts.append(f"🎯 CORE ANGLE: {style_profile['core_angle']}")
        
        # Viewer Insight
        if style_profile.get("viewer_insight"):
            context_parts.append(f"💡 INSIGHT: {style_profile['viewer_insight']}")
        
        # Main Ideas
        if style_profile.get("main_ideas"):
            ideas = style_profile["main_ideas"]
            if isinstance(ideas, list) and ideas:
                label = "MAIN IDEAS" if is_en else "Ý CHÍNH"
                context_parts.append(f"📝 {label}: {', '.join(ideas[:5])}")
        
        # Narrative perspective & audience
        perspective_info = []
        if style_profile.get("narrative_perspective"):
            narrator_label = "Narrator" if is_en else "Ngôi kể"
            perspective_info.append(f"{narrator_label}: {style_profile['narrative_perspective']}")
        if style_profile.get("audience_address"):
            address_label = "Address" if is_en else "Xưng hô"
            perspective_info.append(f"{address_label}: {style_profile['audience_address']}")
        if style_profile.get("cultural_markers"):
            culture_label = "Culture" if is_en else "Văn hóa"
            perspective_info.append(f"{culture_label}: {style_profile['cultural_markers']}")
        if perspective_info:
            context_parts.append(f"👥 NARRATIVE: {' | '.join(perspective_info)}")
        
        # Legacy fields for backward compatibility
        if "writing_style" in style_profile and isinstance(style_profile["writing_style"], dict):
            ws = style_profile["writing_style"]
            legacy_style = []
            if ws.get("vocabulary"): legacy_style.append(f"Vocabulary: {ws['vocabulary']}")
            if ws.get("sentence_patterns"): legacy_style.append(f"Patterns: {ws['sentence_patterns']}")
            if legacy_style:
                context_parts.append(f"📚 WRITING STYLE: {' | '.join(legacy_style)}")
        
        if context_parts:
            header = "STYLE A (Complete Style Profile)" if is_en else "GIỌNG VĂN A (Complete Style Profile)"
            return f"\n═══ {header} ═══\n" + "\n".join(context_parts) + "\n"
        return ""
    
    def _route_task(self, task_type: TaskType, prompt: str, temperature: float = 0.7) -> str:
        """Smart routing based on task complexity"""
        logger.info(f"[_route_task] Task: {task_type.value}")
        logger.info(f"[_route_task] Gemini configured: {self.ai_client.gemini_api.is_configured()}")
        logger.info(f"[_route_task] OpenAI configured: {self.ai_client.openai.is_configured()}")
        
        if task_type in [TaskType.STYLE_ANALYSIS, TaskType.OUTLINE_GENERATION, TaskType.SCENE_BREAKDOWN]:
            if self.ai_client.gemini_api.is_configured():
                provider = AIProvider.GEMINI_API
            else:
                provider = AIProvider.AUTO
        else:
            provider = AIProvider.AUTO
        
        logger.info(f"[AdvancedRemake] Routing {task_type.value} to {provider.value}")
        logger.info(f"[_route_task] Selected provider: {provider.value}")
        logger.info(f"[_route_task] Calling ai_client.generate with prompt of {len(prompt)} chars...")
        
        try:
            result = self.ai_client.generate(
                prompt=prompt,
                provider=provider,
                temperature=temperature
            )
            logger.info(f"[_route_task] Got result of {len(result)} chars")
            return result
        except Exception as e:
            logger.error(f"[_route_task] Error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _clean_ai_output(self, content: str, language: str = "vi") -> str:
        """
        Post-processing pipeline for AI-generated script content.
        
        1. Remove prompt terminology leakage (banned technical terms)
        2. Fix Vietnamese diacritics errors (ONLY when language == 'vi')
        3. Clean up ellipsis ("..." → proper punctuation)
        4. Normalize whitespace
        """
        import re
        
        # ── Step 1: Remove banned technical terms ─────────────────────
        banned_terms = [
            # English terms
            "Core Angle", "Main Idea", "Hook", "CTA", "Call to Action",
            "Loop", "open loop", "close loop", "mở loop", "đóng loop",
            "Retention", "Climax", "Payoff", "Engagement",
            # Vietnamese terms
            "Core Angle", "Main Idea", "cao trào", "payoff",
            # Meta-commentary patterns
            "phần này tạo", "đây là cao trào", "this creates curiosity",
            "this is the climax", "để tạo sự tò mò", "để giữ chân"
        ]
        
        result = content
        for term in banned_terms:
            result = re.sub(re.escape(term), "", result, flags=re.IGNORECASE)
        
        # ── Step 2: Fix Vietnamese diacritics errors ──────────────────
        # Common AI mistakes: missing diacritics on frequent Vietnamese words
        # Format: (wrong_pattern_regex, correct_replacement)
        # Using word boundary \b to avoid partial matches
        vi_diacritics_fixes = [
            # "ban" → "bạn" (you) — most common error
            (r'\bban\b', 'bạn'),
            (r'\bBan\b', 'Bạn'),
            # "noi" → "nói" (to say)
            (r'\bnoi\b', 'nói'),
            (r'\bNoi\b', 'Nói'),
            # "doi" → "đời" (life) — context: "cuộc doi" → "cuộc đời"
            (r'\bcuoc doi\b', 'cuộc đời'),
            (r'\bCuoc doi\b', 'Cuộc đời'),
            # "nguoi" → "người" (person)
            (r'\bnguoi\b', 'người'),
            (r'\bNguoi\b', 'Người'),
            # "dung" → "đúng" (correct)
            (r'\bdung\b', 'đúng'),
            (r'\bDung\b', 'Đúng'),
            # "duoc" → "được" (can/able)
            (r'\bduoc\b', 'được'),
            (r'\bDuoc\b', 'Được'),
            # "khong" → "không" (no/not)
            (r'\bkhong\b', 'không'),
            (r'\bKhong\b', 'Không'),
            # "gi" → "gì" (what)
            (r'\bgi\b', 'gì'),
            # "la" → "là" (is) when standalone
            (r'\bla\b', 'là'),
            # "cua" → "của" (of)
            (r'\bcua\b', 'của'),
            (r'\bCua\b', 'Của'),
            # "nhung" → "những" (those/plural)
            (r'\bnhung\b', 'những'),
            (r'\bNhung\b', 'Những'),
            # "dieu" → "điều" (thing/matter)
            (r'\bdieu\b', 'điều'),
            (r'\bDieu\b', 'Điều'),
            # "biet" → "biết" (know)
            (r'\bbiet\b', 'biết'),
            (r'\bBiet\b', 'Biết'),
            # "muon" → "muốn" (want)
            (r'\bmuon\b', 'muốn'),
            (r'\bMuon\b', 'Muốn'),
            # "minh" → "mình" (self/me)
            (r'\bminh\b', 'mình'),
            (r'\bMinh\b', 'Mình'),
            # "nay" → "này" (this) when standalone
            (r'\bnay\b', 'này'),
            # "nhieu" → "nhiều" (much/many)
            (r'\bnhieu\b', 'nhiều'),
            (r'\bNhieu\b', 'Nhiều'),
            # "the" → "thế" (so/such) — careful, only Vietnamese context
            (r'\bnhu the\b', 'như thế'),
            (r'\bthe nao\b', 'thế nào'),
            # "vay" → "vậy" (so/like that)
            (r'\bvay\b', 'vậy'),
            # "dang" → "đang" (currently)
            (r'\bdang\b', 'đang'),
            (r'\bDang\b', 'Đang'),
            # "nhu" → "như" (like/as)
            (r'\bnhu\b', 'như'),
            (r'\bNhu\b', 'Như'),
            # "lam" → "làm" (do/make)
            (r'\blam\b', 'làm'),
            (r'\bLam\b', 'Làm'),
            # "day" → "đây" (here) — context-dependent
            (r'\bo day\b', 'ở đây'),
            # "cung" → "cũng" (also)
            (r'\bcung\b', 'cũng'),
            (r'\bCung\b', 'Cũng'),
            # "toi" → "tôi" (I/me)
            (r'\btoi\b', 'tôi'),
            (r'\bToi\b', 'Tôi'),
            # "voi" → "với" (with)
            (r'\bvoi\b', 'với'),
            (r'\bVoi\b', 'Với'),
            # "roi" → "rồi" (already)
            (r'\broi\b', 'rồi'),
            # "cach" → "cách" (way/method)
            (r'\bcach\b', 'cách'),
            (r'\bCach\b', 'Cách'),
            # "phai" → "phải" (must/right)
            (r'\bphai\b', 'phải'),
            (r'\bPhai\b', 'Phải'),
            # "con" → "còn" (still) — careful with "con" (child)
            # Skip "con" as it has valid non-diacritics meaning
        ]
        
        if language == "vi":
            for pattern, replacement in vi_diacritics_fixes:
                result = re.sub(pattern, replacement, result)
        
        # ── Step 3: Clean up ellipsis ─────────────────────────────────
        # Normalize multiple dots to single ellipsis character or period
        # "....." or "...." → "..."
        result = re.sub(r'\.{4,}', '...', result)
        # Remove trailing "..." at end of sentences before newline (keeps meaning)
        # "bạn sẽ hiểu..." → "bạn sẽ hiểu."
        result = re.sub(r'\.{3}\s*\n', '.\n', result)
        # Remove trailing "..." at end of content
        result = re.sub(r'\.{3}\s*$', '.', result)
        # Clean "..." in middle of text: "điều đó... nhưng" → "điều đó, nhưng"
        result = re.sub(r'\.{3}\s+', '. ', result)
        
        # ── Step 4: Normalize whitespace ──────────────────────────────
        result = re.sub(r'\s{3,}', '  ', result)
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 1: Bóc tách nội dung gốc
    # ═══════════════════════════════════════════════════════════════
    
    def analyze_original_script(self, script: str) -> OriginalScriptAnalysis:
        """
        STEP 1: Extract and analyze original script content
        
        Analyzes:
        - Core Angle (unique selling proposition)
        - Main Ideas
        - Viewer INSIGHT
        - HOOK analysis
        - Writing style, narrative voice, cultural context
        - Retention Engine
        - CTA strategy
        """
        prompt = f"""You are an expert video script analyst. Extract and analyze the ORIGINAL CONTENT of the following script:

ORIGINAL SCRIPT:
{script[:5000]}

Analyze and return JSON with the following fields:

{{
    "core_angle": "<Core angle of the video - unique selling proposition>",
    "main_ideas": ["<Main idea 1>", "<Main idea 2>", "<Main idea 3>", ...],
    "viewer_insight": "<Viewer INSIGHT - pain point/desire/need the video addresses>",
    "hook_analysis": {{
        "hook_type": "<curiosity|shock|emotion|question|story|benefit>",
        "hook_content": "<Main hook content>",
        "hook_effectiveness": "<Evaluation of hook effectiveness>"
    }},
    "writing_style": {{
        "tone": "<formal|casual|humorous|dramatic|inspiring|educational>",
        "language_level": "<simple|intermediate|advanced>",
        "formality": "<very formal|formal|neutral|informal|very informal>"
    }},
    "cultural_context": "<Cultural context of the region/country in the script>",
    "narrative_voice": "<first_person|second_person|third_person|mixed>",
    "retention_engine": "<Viewer retention mechanisms: open loops, cliffhangers, promises, pattern interrupts, etc.>",
    "cta_strategy": "<Call to action strategy: subscribe, like, comment, buy, etc.>"
}}

Return only JSON, no explanation.
"""
        try:
            response = self._route_task(TaskType.STYLE_ANALYSIS, prompt, temperature=0.3)
            
            # Parse JSON
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = re.sub(r'^```(?:json)?\s*', '', clean_response)
                clean_response = re.sub(r'\s*```$', '', clean_response)
            
            start_idx = clean_response.find('{')
            if start_idx != -1:
                brace_count = 0
                end_idx = start_idx
                for i, char in enumerate(clean_response[start_idx:], start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                
                json_str = clean_response[start_idx:end_idx]
                data = json.loads(json_str)
                
                return OriginalScriptAnalysis(
                    core_angle=data.get("core_angle", ""),
                    main_ideas=data.get("main_ideas", []),
                    viewer_insight=data.get("viewer_insight", ""),
                    hook_analysis=data.get("hook_analysis", {}),
                    writing_style=data.get("writing_style", {}),
                    cultural_context=data.get("cultural_context", ""),
                    narrative_voice=data.get("narrative_voice", ""),
                    retention_engine=data.get("retention_engine", ""),
                    cta_strategy=data.get("cta_strategy", "")
                )
            
            logger.warning("Could not parse original script analysis JSON")
            return OriginalScriptAnalysis()
            
        except Exception as e:
            logger.error(f"Step 1 failed: {e}")
            return OriginalScriptAnalysis()
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 2: Phân tích cấu trúc kịch bản
    # ═══════════════════════════════════════════════════════════════
    
    def analyze_structure(self, script: str) -> StructureAnalysis:
        """
        STEP 2: Phân tích cấu trúc kịch bản
        
        Phân tích:
        - Số lượng từ
        - Hook duration
        - Intro/Body/Conclusion breakdown
        - Climax/Payoff locations
        """
        logger.info(f"[analyze_structure] Starting with script of {len(script)} chars")
        
        # Calculate word count locally
        words = script.split()
        total_word_count = len(words)
        logger.info(f"[analyze_structure] Word count: {total_word_count}")
        
        prompt = f"""Analyze the STRUCTURE of the following video script:

SCRIPT (total {total_word_count} words):
{script[:5000]}

Analyze the structural rhythm and return JSON:

{{
    "total_word_count": {total_word_count},
    "hook_duration": "<How long the hook lasts: first X seconds/first X words>",
    "hook_word_count": <number of words in hook section>,
    "intro_analysis": {{
        "segments": <number of segments in intro>,
        "word_count": <intro word count>,
        "purpose": "<purpose of the intro>"
    }},
    "body_analysis": {{
        "segments": <number of body segments>,
        "word_count": <body word count>,
        "main_issues": ["<main topic/content 1>", "<topic 2>", ...]
    }},
    "conclusion_analysis": {{
        "segments": <number of conclusion segments>,
        "word_count": <conclusion word count>,
        "purpose": "<purpose of conclusion>"
    }},
    "section_breakdown": [
        {{"order": 1, "title": "<section name>", "word_count": <word count>, "purpose": "<purpose>"}},
        ...
    ],
    "climax_location": "<Where the climax is: which section, % of video>",
    "payoff_location": "<Where the payoff is: which section, % of video>"
}}

Return only JSON.
"""
        try:
            logger.info(f"[analyze_structure] Calling _route_task with prompt of {len(prompt)} chars...")
            response = self._route_task(TaskType.STYLE_ANALYSIS, prompt, temperature=0.3)
            logger.info(f"[analyze_structure] Got response of {len(response)} chars")
            
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = re.sub(r'^```(?:json)?\s*', '', clean_response)
                clean_response = re.sub(r'\s*```$', '', clean_response)
            
            start_idx = clean_response.find('{')
            if start_idx != -1:
                brace_count = 0
                end_idx = start_idx
                for i, char in enumerate(clean_response[start_idx:], start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                
                json_str = clean_response[start_idx:end_idx]
                data = json.loads(json_str)
                logger.info(f"[analyze_structure] Parsed JSON successfully")
                
                return StructureAnalysis(
                    total_word_count=total_word_count,
                    hook_duration=data.get("hook_duration", ""),
                    hook_word_count=data.get("hook_word_count", 0),
                    intro_analysis=data.get("intro_analysis", {}),
                    body_analysis=data.get("body_analysis", {}),
                    conclusion_analysis=data.get("conclusion_analysis", {}),
                    section_breakdown=data.get("section_breakdown", []),
                    climax_location=data.get("climax_location", ""),
                    payoff_location=data.get("payoff_location", "")
                )
            
            logger.warning(f"[analyze_structure] No JSON found in response, returning default")
            return StructureAnalysis(total_word_count=total_word_count)
            
        except Exception as e:
            logger.error(f"[analyze_structure] Error: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Step 2 failed: {e}")
            return StructureAnalysis(total_word_count=total_word_count)
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 3: Tạo Dàn ý A
    # ═══════════════════════════════════════════════════════════════
    
    def create_outline_a(
        self,
        original_analysis: OriginalScriptAnalysis,
        structure_analysis: StructureAnalysis,
        target_word_count: int,
        language: str = "en",
        dialect: str = "American",
        channel_name: str = "",
        max_sections: int = 5,
        storytelling_style: str = "",  # immersive, documentary, conversational, analytical, narrative
        narrative_voice: str = "",  # Empty if disabled
        custom_narrative_voice: str = "",  # Custom cách xưng hô ngôi kể
        audience_address: str = "",  # Cách xưng hô khán giả: 'bạn', 'các bạn', etc. - Empty if disabled
        custom_audience_address: str = "",  # Custom description
        style_profile: dict = None
    ) -> OutlineA:
        """
        STEP 3: Tạo Dàn ý A với phân bổ từ
        
        Dựa vào phân tích ở Step 1 và 2, tạo dàn ý mới:
        - Chia tối đa 5 phần
        - Phân bổ số từ cho mỗi phần
        - Giữ nguyên core angle và main ideas
        - Áp dụng ngôi kể và cách xưng hô đã chọn (if enabled)
        """
        # Language config
        lang_names = {
            "en": "English",
            "vi": "Vietnamese", 
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "es": "Spanish",
            "fr": "French",
            "th": "Thai",
            "de": "German",
            "pt": "Portuguese",
            "ru": "Russian"
        }
        lang_name = lang_names.get(language, "English")
        
        # Storytelling style descriptions - language aware
        storytelling_section = ""
        if storytelling_style:
            if language != "vi":
                storytelling_desc = {
                    "immersive": "🎭 Immersive - Narrator embodies the character, telling as if living the story",
                    "documentary": "🎥 Documentary - Recounting events like a report, objective and informative",
                    "conversational": "💬 Conversational - Speaking directly to viewers like a conversation",
                    "analytical": "🔍 Analytical - Breaking down, explaining logic, providing deep analysis",
                    "narrative": "📖 Narrative - Guiding through a story with beginning, climax, and ending"
                }
                style_desc = storytelling_desc.get(storytelling_style, storytelling_desc.get("narrative", ""))
                storytelling_section = f"- STORYTELLING STYLE: {style_desc}"
            else:
                storytelling_desc = {
                    "immersive": "🎭 Nhập vai (Immersive) - Người kể hóa thân vào nhân vật, kể như đang sống trong câu chuyện",
                    "documentary": "🎥 Thuyết minh (Documentary) - Kể lại sự kiện như phóng sự, khách quan và thông tin",
                    "conversational": "💬 Đối thoại (Conversational) - Như đang trò chuyện trực tiếp với người xem",
                    "analytical": "🔍 Phân tích (Analytical) - Mổ xẻ, giải thích logic, đưa ra phân tích sâu",
                    "narrative": "📖 Kể chuyện (Narrative) - Dẫn dắt qua câu chuyện có mở đầu, cao trào, kết thúc"
                }
                style_desc = storytelling_desc.get(storytelling_style, storytelling_desc.get("narrative", ""))
                storytelling_section = f"- PHONG CÁCH DẪN CHUYỆN: {style_desc}"
        
        # Narrative voice descriptions - language aware
        narrative_section = ""
        if narrative_voice:
            if language != "vi":
                narrative_voice_desc = {
                    "first_person": "First person (I/We) - narrator is the speaker",
                    "second_person": "Second person (You) - speaking directly to viewer",
                    "third_person": "Third person (He/She/They) - narrator observes from outside"
                }
                voice_desc = narrative_voice_desc.get(narrative_voice, narrative_voice_desc.get("first_person", ""))
                narrative_section = f"- NARRATIVE VOICE: {voice_desc}"
            else:
                narrative_voice_desc = {
                    "first_person": "Ngôi thứ nhất (Tôi/Mình) - người kể là chính mình",
                    "second_person": "Ngôi thứ hai (Bạn) - nói trực tiếp với người xem",
                    "third_person": "Ngôi thứ ba (Anh ấy/Cô ấy/Họ) - người kể đứng ngoài quan sát"
                }
                voice_desc = narrative_voice_desc.get(narrative_voice, narrative_voice_desc.get("first_person", ""))
                narrative_section = f"- NGÔI KỂ: {voice_desc}"
            if custom_narrative_voice:
                narrative_section += f'\n- CHI TIẾT NGÔI KỂ: {custom_narrative_voice}'
        
        # Audience address section - cách xưng hô khán giả
        audience_section = ""
        if audience_address:
            if language != "vi":
                audience_section = f'- AUDIENCE ADDRESS: Use "{audience_address}" when addressing the audience (use consistently throughout)'
                if custom_audience_address:
                    audience_section += f'\n- ADDRESS DETAILS: {custom_audience_address}'
            else:
                audience_section = f'- XƯNG HÔ KHÁN GIẢ: Dùng "{audience_address}" khi gọi khán giả (dùng xuyên suốt)'
                if custom_audience_address:
                    audience_section += f'\n- CHI TIẾT CÁCH XƯNG HÔ: {custom_audience_address}'
        
        # Build StyleA context if available - language aware
        style_context = ""
        if style_profile:
            if language != "vi":
                style_context = f"""
STYLE A PROFILE (APPLY THROUGHOUT):
- Voice: {style_profile.get('voice_description', 'N/A')}
- Storytelling approach: {style_profile.get('storytelling_approach', 'N/A')}
- Hook patterns: {', '.join(style_profile.get('common_hook_types', [])[:3]) if style_profile.get('common_hook_types') else 'N/A'}
- Retention techniques: {', '.join(style_profile.get('retention_techniques', [])[:3]) if style_profile.get('retention_techniques') else 'N/A'}
"""
            else:
                style_context = f"""
PHONG CÁCH VĂN A (ÁP DỤNG XUYÊN SUỐT):
- Giọng văn: {style_profile.get('voice_description', 'N/A')}
- Cách dẫn chuyện: {style_profile.get('storytelling_approach', 'N/A')}
- Hook patterns: {', '.join(style_profile.get('common_hook_types', [])[:3]) if style_profile.get('common_hook_types') else 'N/A'}
- Retention techniques: {', '.join(style_profile.get('retention_techniques', [])[:3]) if style_profile.get('retention_techniques') else 'N/A'}
"""
        
        # Language-aware prompt to prevent mixing languages
        if language != "vi":
            prompt = f"""Based on the original script analysis, create a new OUTLINE A in {lang_name} ({dialect}).

ORIGINAL SCRIPT ANALYSIS:
- Core Angle: {original_analysis.core_angle}
- Main Ideas: {', '.join(original_analysis.main_ideas[:5])}
- Viewer Insight: {original_analysis.viewer_insight}
- Hook Type: {original_analysis.hook_analysis.get('hook_type', 'N/A')}
- Retention Engine: {original_analysis.retention_engine}
- CTA Strategy: {original_analysis.cta_strategy}

ORIGINAL STRUCTURE:
- Original word count: {structure_analysis.total_word_count}
- Hook: {structure_analysis.hook_duration}
- Climax: {structure_analysis.climax_location}
- Payoff: {structure_analysis.payoff_location}
{style_context}
STANDARDIZED AIDA 8-STAGE STRUCTURE (MUST FOLLOW):
1. Hook/Intro (8% words): Create STRONG emotions. ❌ NO subscribe/like
2. State the Problem (10% words): Present problem/pain point, create emotional connection
{f'3. CTA#1 Engagement (8% words): ✅ LIGHT CTA - encourage engagement naturally' if channel_name else '3. Interaction (8% words): Ask thought-provoking questions, encourage comments. ❌ NO subscribe/like/share'}
{f'4. Brand Intro (3% words): Brief, natural channel introduction' if channel_name else '4. Transition (3% words): Brief connecting transition to main content'}
5. Main Content (40% words): ⭐ VALUE section - deep analysis, personalization. ❌ NO CTA
6. Create Urgency (12% words): Emphasize benefits/consequences. ❌ NO CTA
{f'7. CTA#2 Call to Action (10% words): ✅ MAIN CTA - subscribe, like, share' if channel_name else '7. Conclusion & Lesson (10% words): Deep lesson, key takeaway. ❌ NO subscribe/like/share'}
8. Outro (9% words): Natural closing, thank you. ❌ NO additional CTA

⚠️ MANDATORY RULES:
- Each stage must have UNIQUE CONTENT, NO repetition
{f'- ONLY 2 CTAs: Stage 3 (light) and Stage 7 (strong)' if channel_name else '- ❌ NO subscribe, like, share, channel promotion anywhere in the script'}
- Stage 5 is the main VALUE section - takes 40%
- Focus on PERSONALIZATION and connecting with viewers

OUTLINE A REQUIREMENTS:
- Language: {lang_name} - {dialect}
- TARGET TOTAL WORDS: {target_word_count} words
- Divide into 8 STAGES following the AIDA structure above
- Allocate words according to given percentages
- Channel name: {channel_name if channel_name else '(none)'}
{storytelling_section}
{narrative_section}
{audience_section}

IMPORTANT:
- This outline is the FOUNDATION for the entire script remake
- All subsequent sections MUST follow this outline
- Keep the Core Angle and Main Ideas from the original script
- Each stage MUST have a distinct purpose, no overlap

Write ONLY in {lang_name}. Do NOT mix any other languages.

Return JSON:
{{
    "sections": [
        {{
            "id": "section_1",
            "title": "<section title in {lang_name}>",
            "description": "<brief description of stage purpose>",
            "order": 1,
            "word_count_target": <word count based on %>",
            "key_points": ["<key point 1>", "<key point 2>"],
            "special_instructions": "<CTA rule: ❌ NO CTA or ✅ LIGHT CTA or ✅ MAIN CTA>"
        }},
        ...
    ],
    "target_word_count": {target_word_count},
    "language": "{language}",
    "dialect": "{dialect}",
    "channel_name": "{channel_name}",
    "storytelling_style": "{storytelling_style}",
    "narrative_voice": "{narrative_voice}",
    "audience_address": "{audience_address}"
}}

Return ONLY JSON.
"""
        else:
            # Vietnamese prompt (only for vi)
            prompt = f"""Dựa vào phân tích kịch bản gốc, tạo DÀN Ý A mới bằng {lang_name} ({dialect}).

PHÂN TÍCH KỊCH BẢN GỐC:
- Core Angle: {original_analysis.core_angle}
- Main Ideas: {', '.join(original_analysis.main_ideas[:5])}
- Viewer Insight: {original_analysis.viewer_insight}
- Hook Type: {original_analysis.hook_analysis.get('hook_type', 'N/A')}
- Retention Engine: {original_analysis.retention_engine}
- CTA Strategy: {original_analysis.cta_strategy}

CẤU TRÚC GỐC:
- Tổng từ gốc: {structure_analysis.total_word_count}
- Hook: {structure_analysis.hook_duration}
- Climax: {structure_analysis.climax_location}
- Payoff: {structure_analysis.payoff_location}
{style_context}
CẤU TRÚC AIDA 8 GIAI ĐOẠN CHUẨN HÓA (BẮT BUỘC FOLLOW):
1. Hook/Intro (8% từ): Gây CẢM GIÁC MẠNH. ❌ KHÔNG subscribe/like
2. Nêu vấn đề (10% từ): Trình bày vấn đề/nỗi đau, tạo kết nối cảm xúc
{f'3. CTA#1 Tương tác (8% từ): ✅ CTA NHẸ - khuyến khích tương tác tự nhiên' if channel_name else '3. Tương tác (8% từ): Đặt câu hỏi suy ngẫm, khuyến khích comment. ❌ KHÔNG nhắc subscribe/đăng ký kênh'}
{f'4. Intro thương hiệu (3% từ): Giới thiệu kênh ngắn gọn, tự nhiên' if channel_name else '4. Chuyển tiếp (3% từ): Câu chuyển tiếp ngắn gọn sang nội dung chính'}
5. Nội dung chính (40% từ): ⭐ PHẦN TẠO GIÁ TRỊ - phân tích sâu, cá nhân hóa. ❌ KHÔNG CTA
6. Kích động nhu cầu (12% từ): Nhấn mạnh lợi ích/hậu quả. ❌ KHÔNG CTA
{f'7. CTA#2 Kêu gọi (10% từ): ✅ CTA CHÍNH - subscribe, like, share' if channel_name else '7. Đúc kết & Bài học (10% từ): Bài học sâu sắc, kết luận. ❌ KHÔNG subscribe/like/share'}
8. Outro (9% từ): Kết thúc tự nhiên, cảm ơn. ❌ KHÔNG thêm CTA

⚠️ QUY TẮC BẮT BUỘC:
- Mỗi giai đoạn phải có NỘI DUNG KHÁC BIỆT, KHÔNG lặp lại ý
{f'- CHỈ có ĐÚNG 2 CTA: Giai đoạn 3 (nhẹ) và Giai đoạn 7 (mạnh)' if channel_name else '- ❌ KHÔNG nhắc subscribe, like, share, đăng ký kênh, quảng bá kênh ở bất kỳ đâu'}
- Giai đoạn 5 là phần TẠO GIÁ TRỊ chính - chiếm 40% 
- Hướng tới CÁ NHÂN HÓA và kết nối với người xem

YÊU CẦU DÀN Ý A:
- Ngôn ngữ: {lang_name} - {dialect}
- TỔNG SỐ TỪ MỤC TIÊU: {target_word_count} từ
- Chia thành 8 GIAI ĐOẠN theo cấu trúc AIDA ở trên
- Phân bổ số từ theo tỷ lệ % đã cho
- Tên kênh: {channel_name if channel_name else '(không có)'}
{storytelling_section}
{narrative_section}
{audience_section}

QUAN TRỌNG: 
- Dàn ý này là NỀN TẢNG cho toàn bộ script remake
- Tất cả các phần sau PHẢI follow theo dàn ý này
- Giữ nguyên Core Angle và Main Ideas từ kịch bản gốc
- Mỗi giai đoạn PHẢI có mục đích riêng biệt, không trùng lặp

CHỈ viết bằng {lang_name}. KHÔNG trộn ngôn ngữ khác.

Trả về JSON:
{{
    "sections": [
        {{
            "id": "section_1",
            "title": "<tiêu đề phần bằng {lang_name}>",
            "description": "<mô tả ngắn mục đích giai đoạn>",
            "order": 1,
            "word_count_target": <số từ theo tỷ lệ %>,
            "key_points": ["<ý chính 1>", "<ý chính 2>"],
            "special_instructions": "<quy tắc CTA: ❌ KHÔNG CTA hoặc ✅ CTA NHẸ hoặc ✅ CTA CHÍNH>"
        }},
        ...
    ],
    "target_word_count": {target_word_count},
    "language": "{language}",
    "dialect": "{dialect}",
    "channel_name": "{channel_name}",
    "storytelling_style": "{storytelling_style}",
    "narrative_voice": "{narrative_voice}",
    "audience_address": "{audience_address}"
}}

Chỉ trả về JSON.
"""
        try:
            response = self._route_task(TaskType.OUTLINE_GENERATION, prompt, temperature=0.5)
            
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = re.sub(r'^```(?:json)?\s*', '', clean_response)
                clean_response = re.sub(r'\s*```$', '', clean_response)
            
            start_idx = clean_response.find('{')
            if start_idx != -1:
                brace_count = 0
                end_idx = start_idx
                for i, char in enumerate(clean_response[start_idx:], start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                
                json_str = clean_response[start_idx:end_idx]
                data = json.loads(json_str)
                
                sections = []
                for s in data.get("sections", []):
                    sections.append(OutlineSectionA(
                        id=s.get("id", f"section_{len(sections)+1}"),
                        title=s.get("title", ""),
                        description=s.get("description", ""),
                        order=s.get("order", len(sections)+1),
                        word_count_target=s.get("word_count_target", 100),
                        key_points=s.get("key_points", []),
                        special_instructions=s.get("special_instructions", "")
                    ))
                
                return OutlineA(
                    sections=sections,
                    target_word_count=target_word_count,
                    language=language,
                    dialect=dialect,
                    channel_name=channel_name,
                    storytelling_style=data.get("storytelling_style", storytelling_style),
                    narrative_voice=data.get("narrative_voice", narrative_voice),
                    audience_address=data.get("audience_address", audience_address)
                )
            
            # Default outline if parsing fails
            return self._create_default_outline_a(target_word_count, language, dialect, channel_name, max_sections, storytelling_style, narrative_voice, audience_address)
            
        except Exception as e:
            logger.error(f"Step 3 failed: {e}")
            return self._create_default_outline_a(target_word_count, language, dialect, channel_name, max_sections, storytelling_style, narrative_voice, audience_address)
    
    def _create_default_outline_a(self, target_word_count: int, language: str, dialect: str, channel_name: str, max_sections: int, storytelling_style: str = "", narrative_voice: str = "", audience_address: str = "") -> OutlineA:
        """Create default AIDA 8-stage outline when AI fails"""
        
        # AIDA 8-stage structure with proper word distribution
        # Stage 5 gets 40% as the main VALUE creation section
        word_distribution = {
            1: 0.08,  # Hook: 8%
            2: 0.10,  # Problem: 10%
            3: 0.08,  # CTA #1: 8%
            4: 0.03,  # Brand: 3%
            5: 0.40,  # Main Content: 40%
            6: 0.12,  # Urgency: 12%
            7: 0.10,  # CTA #2: 10%
            8: 0.09,  # Outro: 9%
        }
        
        brand_intro = f'Giới thiệu kênh {channel_name}' if channel_name else 'Chuyển tiếp sang nội dung chính'
        
        # AIDA 8-stage sections with CTA rules embedded
        # When no channel_name: no subscribe/CTA, replace with natural interaction
        if channel_name:
            default_sections = [
                ("Hook/Intro", 
                 "Mở đầu gây CẢM GIÁC MẠNH, tò mò, sốc hoặc xúc động", 
                 "❌ KHÔNG nhắc subscribe/like ở đây. Tạo ấn tượng mạnh ngay từ đầu.",
                 ["hook gây chú ý", "câu mở đầu ấn tượng"]),
                ("Nêu vấn đề", 
                 "Trình bày VẤN ĐỀ/NỖI ĐAU mà khán giả đang gặp", 
                 "Tạo kết nối cảm xúc, khiến họ thấy 'đúng là mình'. Đánh vào INSIGHT người xem.",
                 ["vấn đề thực tế", "kết nối cảm xúc"]),
                ("CTA Tương tác #1", 
                 "✅ CTA NHẸ - Đặt câu hỏi mở, yêu cầu comment ý kiến", 
                 "Đây là CTA #1 - CHỈ kêu gọi comment/thảo luận. VD: 'Bạn nghĩ sao? Comment nhé!'",
                 ["câu hỏi tương tác", "kêu gọi comment"]),
                ("Intro thương hiệu", 
                 brand_intro, 
                 "Ngắn gọn 3-5s, tự nhiên, cài vào tiềm thức. KHÔNG quảng cáo.",
                 ["giới thiệu kênh"]),
                ("Nội dung chính - Tạo giá trị", 
                 "⭐ PHẦN QUAN TRỌNG NHẤT - Phân tích sâu, giải pháp chi tiết, thông tin CÁ NHÂN HÓA", 
                 "Đây là phần TẠO GIÁ TRỊ chính - chiếm 40% script. ❌ KHÔNG CTA ở đây.",
                 ["giải pháp chi tiết", "giá trị thực sự", "cá nhân hóa"]),
                ("Kích động nhu cầu", 
                 "Nhấn mạnh HẬU QUẢ nếu không hành động, đề cao LỢI ÍCH", 
                 "Tạo urgency tự nhiên, không ép buộc. ❌ KHÔNG CTA ở đây.",
                 ["lợi ích", "urgency"]),
                ("CTA Kêu gọi #2", 
                 "✅ CTA CHÍNH - Kêu gọi subscribe, like, share hoặc hành động cụ thể", 
                 f"Đây là CTA #2 - CTA MẠNH và DUY NHẤT còn lại. Mời tham gia kênh {channel_name}.",
                 ["subscribe", "like", "share"]),
                ("Outro/Kết thúc", 
                 "Kết thúc TỰ NHIÊN, chào tạm biệt, cảm ơn", 
                 "❌ KHÔNG thêm CTA ở đây - đã có ở giai đoạn 7. Hẹn gặp lại.",
                 ["cảm ơn", "hẹn gặp lại"]),
            ]
        else:
            # No channel_name: no CTA, natural interaction only
            default_sections = [
                ("Hook/Intro", 
                 "Mở đầu gây CẢM GIÁC MẠNH, tò mò, sốc hoặc xúc động", 
                 "❌ KHÔNG nhắc subscribe/like/đăng ký kênh. Tạo ấn tượng mạnh ngay từ đầu.",
                 ["hook gây chú ý", "câu mở đầu ấn tượng"]),
                ("Nêu vấn đề", 
                 "Trình bày VẤN ĐỀ/NỖI ĐAU mà khán giả đang gặp", 
                 "Tạo kết nối cảm xúc, khiến họ thấy 'đúng là mình'. Đánh vào INSIGHT người xem.",
                 ["vấn đề thực tế", "kết nối cảm xúc"]),
                ("Tương tác suy ngẫm", 
                 "Đặt câu hỏi suy ngẫm, khuyến khích comment ý kiến", 
                 "❌ KHÔNG nhắc subscribe/đăng ký kênh. CHỈ đặt câu hỏi tự nhiên để tương tác.",
                 ["câu hỏi suy ngẫm", "khuyến khích comment"]),
                ("Chuyển tiếp", 
                 brand_intro, 
                 "Ngắn gọn 3-5s, chuyển tiếp tự nhiên sang nội dung chính.",
                 ["chuyển tiếp"]),
                ("Nội dung chính - Tạo giá trị", 
                 "⭐ PHẦN QUAN TRỌNG NHẤT - Phân tích sâu, giải pháp chi tiết, thông tin CÁ NHÂN HÓA", 
                 "Đây là phần TẠO GIÁ TRỊ chính - chiếm 40% script. ❌ KHÔNG CTA ở đây.",
                 ["giải pháp chi tiết", "giá trị thực sự", "cá nhân hóa"]),
                ("Kích động nhu cầu", 
                 "Nhấn mạnh HẬU QUẢ nếu không hành động, đề cao LỢI ÍCH", 
                 "Tạo urgency tự nhiên, không ép buộc. ❌ KHÔNG CTA ở đây.",
                 ["lợi ích", "urgency"]),
                ("Đúc kết & Bài học", 
                 "Đúc kết sâu sắc, bài học áp dụng vào cuộc sống", 
                 "❌ KHÔNG nhắc subscribe/like/share/đăng ký kênh. CHỈ đúc kết bài học.",
                 ["bài học sâu sắc", "kết luận"]),
                ("Outro/Kết thúc", 
                 "Kết thúc TỰ NHIÊN, chào tạm biệt, cảm ơn", 
                 "❌ KHÔNG thêm CTA ở đây. Hẹn gặp lại.",
                 ["cảm ơn", "hẹn gặp lại"]),
            ]
        
        sections = []
        num_sections = min(max_sections, 8)  # Max 8 sections for AIDA
        
        for i in range(num_sections):
            title, desc, instr, key_points = default_sections[i]
            word_count = int(target_word_count * word_distribution.get(i+1, 0.1))
            
            sections.append(OutlineSectionA(
                id=f"section_{i+1}",
                title=title,
                description=desc,
                order=i+1,
                word_count_target=word_count,
                key_points=key_points,
                special_instructions=instr
            ))
        
        return OutlineA(
            sections=sections,
            target_word_count=target_word_count,
            language=language,
            dialect=dialect,
            channel_name=channel_name,
            storytelling_style=storytelling_style,
            narrative_voice=narrative_voice,
            audience_address=audience_address
        )
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 4: Viết nội dung theo Dàn ý A
    # ═══════════════════════════════════════════════════════════════
    
    def write_section_advanced(
        self,
        section: OutlineSectionA,
        outline_a: OutlineA,
        original_analysis: OriginalScriptAnalysis,
        previous_content: str = "",
        style_profile: Optional[Dict[str, Any]] = None
    ) -> DraftSection:
        """
        STEP 4: Viết nội dung theo Dàn ý A
        
        Viết từng phần đảm bảo:
        - Tương đồng về nội dung với kịch bản gốc
        - Giữ nguyên core angle và insight
        - Theo đúng phong cách gốc
        - Đạt số từ mục tiêu
        """
        lang_names = {"en": "English", "vi": "Vietnamese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese"}
        lang_name = lang_names.get(outline_a.language, "English")
        
        # Build style context from StyleA if provided
        style_context = self._build_style_context(style_profile, language=outline_a.language)
        
        # Use language-specific prompt to prevent mixing languages
        if outline_a.language != "vi":
            context_text = ""
            if previous_content:
                context_text = f"\nPREVIOUS CONTENT (for coherent transition):\n{previous_content[-500:]}\n"
            
            prompt = f"""Write section {section.order} of the new script in {lang_name} ({outline_a.dialect}).

SECTION INFO:
- Title: {section.title}
- Description: {section.description}
- Target word count: {section.word_count_target} words
- Key points to cover: {', '.join(section.key_points) if section.key_points else 'Follow the description'}
- Special instructions: {section.special_instructions}

STYLE FROM ORIGINAL SCRIPT:
- Core Angle: {original_analysis.core_angle}
- Viewer Insight: {original_analysis.viewer_insight}
- Tone: {original_analysis.writing_style.get('tone', 'neutral')}
- Narrative Voice: {original_analysis.narrative_voice}
- Retention Engine: {original_analysis.retention_engine}
{style_context}
{context_text}
OUTLINE A (USE AS GUIDE):
- Target total words: {outline_a.target_word_count}
- Narrative Voice: {outline_a.narrative_voice} - use throughout
- Audience Address: "{outline_a.audience_address}" - use consistently when addressing the audience
- All sections: {[s.title for s in outline_a.sections]}

MAIN REQUIREMENTS:
1. Write EXACTLY {section.word_count_target} words (±10%)
2. Write coherently with emotion, do not break into small sections
3. DO NOT use icons/emoji
4. If opening section: create curiosity, mystery, strong emotions
5. If channel_name "{outline_a.channel_name}": naturally integrate it
6. APPLY THE LEARNED WRITING STYLE (StyleA) if provided above

📋 AIDA 8-STAGE RULES (CRITICAL):
- Section 1 (Hook): Create STRONG emotions. ❌ NO subscribe/like here
{f'- Section 3 (CTA#1): LIGHT CTA only - ask questions, request comments' if outline_a.channel_name else '- Section 3 (Interaction): Ask thought-provoking questions. ❌ NO subscribe/like/share'}
- Section 5 (Main Content): This is the VALUE section. ❌ NO CTA here
- Section 6 (Urgency): Emphasize benefits/consequences. ❌ NO CTA here  
{f'- Section 7 (CTA#2): MAIN CTA - subscribe, like, share' if outline_a.channel_name else '- Section 7 (Conclusion): Deep lesson and takeaway. ❌ NO subscribe/like/share'}
- Section 8 (Outro): Natural closing. ❌ NO additional CTA
- Each section must have UNIQUE content - NO repetition from other sections
- Focus on PERSONALIZATION and VALUE for viewers

AVOID:
- Technical terms: "Core Angle", "Main Idea", "Hook", "CTA", "Loop", "Retention", "Climax", "Payoff"
- Meta-commentary: "this part creates curiosity", "this is the climax"
- Mentioning "like", "subscribe", "share" {f'except in Section 3 (light) and Section 7 (main CTA)' if outline_a.channel_name else 'anywhere in the script'}
- Fabricating statistics, coordinates, or specific dates not in the original
- Quiz format A/B/C
- Repeating "I promise", "I believe", "I guarantee" more than once

📝 NATURAL VOICE:
- Write like a NATIVE SPEAKER telling a story, natural, with rhythm
- Use idioms and expressions natural to the language
- Avoid literal translated metaphors that feel forced
- Sentences should flow naturally, not feel forced

Write ONLY in {lang_name}. Do NOT mix languages.

Write the content (ONLY content, no titles/notes):
"""
        else:
            # Vietnamese prompt (only for vi)
            context_text = ""
            if previous_content:
                context_text = f"\nNỘI DUNG TRƯỚC (để liên kết mạch lạc):\n{previous_content[-500:]}\n"
            
            prompt = f"""Viết phần {section.order} của kịch bản mới bằng {lang_name} ({outline_a.dialect}).

THÔNG TIN PHẦN:
- Tiêu đề: {section.title}
- Mô tả: {section.description}
- Số từ mục tiêu: {section.word_count_target} từ
- Ý chính cần cover: {', '.join(section.key_points) if section.key_points else 'Theo mô tả'}
- Hướng dẫn đặc biệt: {section.special_instructions}

PHONG CÁCH TỪ KỊCH BẢN GỐC:
- Core Angle: {original_analysis.core_angle}
- Viewer Insight: {original_analysis.viewer_insight}
- Tone: {original_analysis.writing_style.get('tone', 'neutral')}
- Narrative Voice: {original_analysis.narrative_voice}
- Retention Engine: {original_analysis.retention_engine}
{style_context}
{context_text}
OUTLINE A (NỀN TẢNG - BẮT BUỘC FOLLOW):
- Tổng số từ mục tiêu: {outline_a.target_word_count}
- Ngôi kể: {outline_a.narrative_voice} - sử dụng xuyên suốt
- Xưng hô khán giả: "{outline_a.audience_address}" - dùng nhất quán khi gọi khán giả (VD: 'bạn ơi', 'các bạn thấy đấy...')
- Các phần: {[s.title for s in outline_a.sections]}

YÊU CẦU CHÍNH:
1. Viết CHÍNH XÁC {section.word_count_target} từ (±10%)
2. Viết mạch lạc, có cảm xúc, không chia từng phần nhỏ
3. KHÔNG dùng icon/emoji
4. Nếu là phần đầu: gây tò mò, bí ẩn, cảm xúc mạnh
5. Nếu có channel_name "{outline_a.channel_name}": chèn tự nhiên
6. ÁP DỤNG PHONG CÁCH VIẾT (StyleA) nếu có ở trên

📋 QUY TẮC AIDA 8 GIAI ĐOẠN (QUAN TRỌNG):
- Giai đoạn 1 (Hook): Tạo CẢM XÚC MẠNH. ❌ KHÔNG subscribe/like ở đây
{f'- Giai đoạn 3 (CTA#1): CTA NHẸ - đặt câu hỏi, yêu cầu comment' if outline_a.channel_name else '- Giai đoạn 3 (Tương tác): Đặt câu hỏi suy ngẫm. ❌ KHÔNG subscribe/đăng ký kênh'}
- Giai đoạn 5 (Nội dung chính): Đây là phần TẠO GIÁ TRỊ. ❌ KHÔNG CTA ở đây
- Giai đoạn 6 (Kích động): Nhấn mạnh lợi ích/hậu quả. ❌ KHÔNG CTA ở đây
{f'- Giai đoạn 7 (CTA#2): CTA CHÍNH - subscribe, like, share' if outline_a.channel_name else '- Giai đoạn 7 (Đúc kết): Bài học sâu sắc, kết luận. ❌ KHÔNG subscribe/like/share'}
- Giai đoạn 8 (Outro): Kết thúc tự nhiên. ❌ KHÔNG thêm CTA
- Mỗi giai đoạn phải có NỘI DUNG KHÁC BIỆT - KHÔNG lặp lại từ giai đoạn khác
- Tập trung vào CÁ NHÂN HÓA và GIÁ TRỊ cho người xem

TRÁNH:
- Thuật ngữ kỹ thuật: "Core Angle", "Hook", "CTA", "Loop", "Retention"
- Viết meta: "phần này tạo tò mò", "đây là cao trào"
- Nhắc "like", "subscribe", "share" {f'ngoài Giai đoạn 3 (nhẹ) và Giai đoạn 7 (CTA chính)' if outline_a.channel_name else 'ở bất kỳ đâu'}
- Bịa số liệu, tọa độ, ngày tháng không có trong gốc
- Format trắc nghiệm A/B/C
- Lặp "tôi hứa", "tôi tin", "tôi cam đoan" quá 1 lần

📝 GIỌNG VĂN TỰ NHIÊN:
- Viết như NGƯỜI BẢN XỨ kể chuyện, tự nhiên, có nhịp thở
- Dùng thành ngữ, tục ngữ phù hợp với ngôn ngữ
- TRÁNH ẩn dụ dịch từ tiếng Anh (VD: "ngọn đèn tò mò sáng", "não mở khóa")
- Câu văn có nhịp điệu tự nhiên, không gượng ép

CHỈ viết bằng {lang_name}. KHÔNG trộn ngôn ngữ khác.

Viết nội dung (CHỈ nội dung, không tiêu đề/ghi chú):
"""
        try:
            response = self._route_task(TaskType.DEEP_WRITING, prompt, temperature=0.8)
            
            content = response.strip()
            # Remove any markdown artifacts
            if content.startswith("```"):
                content = re.sub(r'^```\w*\s*', '', content)
                content = re.sub(r'```$', '', content)
            
            # Post-process to remove prompt terminology leakage
            content = self._clean_ai_output(content, language=outline_a.language)
            
            word_count = len(content.split())
            
            return DraftSection(
                section_id=section.id,
                content=content,
                version=1,
                word_count=word_count,
                status="draft"
            )
            
        except Exception as e:
            logger.error(f"Step 4 write section failed: {e}")
            return DraftSection(
                section_id=section.id,
                content=f"[Error writing section: {e}]",
                version=1,
                word_count=0,
                status="error"
            )
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 5: Kiểm tra tương đồng
    # ═══════════════════════════════════════════════════════════════
    
    def review_similarity(
        self,
        draft: str,
        original: str,
        country: str = ""  # Empty if legal check is disabled
    ) -> SimilarityReview:
        """
        STEP 5: Kiểm tra tương đồng với bản gốc
        
        Kiểm tra:
        - Nội dung có tương đồng với gốc?
        - Có lặp lại gây nhàm chán?
        - Vi phạm YouTube community guidelines?
        - Vi phạm pháp luật của country? (only if country is provided)
        """
        # Build legal check section dynamically
        legal_section = ""
        legal_json_field = ""
        if country:
            legal_section = f"\nQUỐC GIA KIỂM TRA PHÁP LUẬT: {country}"
            legal_json_field = f'''
    "legal_violations": [
        "<nếu vi phạm pháp luật {country}, liệt kê>"
    ],'''
        else:
            legal_json_field = '''
    "legal_violations": [],'''
        
        prompt = f"""Kiểm tra và so sánh kịch bản MỚI với kịch bản GỐC:

KỊCH BẢN GỐC:
{original[:3000]}

KỊCH BẢN MỚI:
{draft[:3000]}
{legal_section}

Trả về JSON:
{{
    "similarity_score": <0-100, mức độ tương đồng về nội dung và ý nghĩa>,
    "content_matches": <true/false, nội dung mới có cover đúng ý chính của gốc?>,
    "repetition_issues": [
        "<nếu có đoạn lặp lại gây nhàm chán, liệt kê>"
    ],
    "youtube_violations": [
        "<nếu vi phạm YouTube guidelines, liệt kê>"
    ],{legal_json_field}
    "ethics_violations": [
        "<nếu vi phạm đạo đức, đả kích, discrimination, liệt kê>"
    ],
    "suggestions": [
        "<đề xuất cải thiện 1>",
        "<đề xuất cải thiện 2>"
    ]
}}

Chỉ trả về JSON.
"""
        try:
            response = self._route_task(TaskType.STYLE_ANALYSIS, prompt, temperature=0.3)
            
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = re.sub(r'^```(?:json)?\s*', '', clean_response)
                clean_response = re.sub(r'\s*```$', '', clean_response)
            
            start_idx = clean_response.find('{')
            if start_idx != -1:
                brace_count = 0
                end_idx = start_idx
                for i, char in enumerate(clean_response[start_idx:], start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                
                json_str = clean_response[start_idx:end_idx]
                data = json.loads(json_str)
                
                return SimilarityReview(
                    similarity_score=float(data.get("similarity_score", 0)),
                    content_matches=data.get("content_matches", True),
                    repetition_issues=data.get("repetition_issues", []),
                    youtube_violations=data.get("youtube_violations", []),
                    legal_violations=data.get("legal_violations", []),
                    ethics_violations=data.get("ethics_violations", []),
                    suggestions=data.get("suggestions", []),
                    country_checked=country
                )
            
            return SimilarityReview(country_checked=country)
            
        except Exception as e:
            logger.error(f"Step 5 review failed: {e}")
            return SimilarityReview(country_checked=country)
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 6: Tinh chỉnh từng phần
    # ═══════════════════════════════════════════════════════════════
    
    def refine_section_advanced(
        self,
        section: DraftSection,
        outline_section: OutlineSectionA,
        outline_a: OutlineA,
        original_analysis: OriginalScriptAnalysis,
        is_first_section: bool = False,
        is_last_section: bool = False,
        add_quiz: bool = False,
        style_profile: Optional[Dict[str, Any]] = None
    ) -> DraftSection:
        """
        STEP 6: Tinh chỉnh từng phần
        
        Tùy theo vị trí phần (3 câu lệnh):
        - Câu lệnh 1 (Phần 1): Hook mạnh, kêu gọi subscribe, thêm quiz A/B
        - Câu lệnh 2 (Phần giữa): Nội dung chính, KHÔNG CTA, kết nối phần trước
        - Câu lệnh 3 (Phần cuối): Đúc kết, bài học, câu hỏi đơn giản, CTA subscribe
        """
        lang_names = {"en": "English", "vi": "Vietnamese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese"}
        lang_name = lang_names.get(outline_a.language, "English")
        
        # Build style context from StyleA if provided
        style_context = self._build_style_context(style_profile, language=outline_a.language)
        
        # Use language-specific prompts to prevent mixing languages
        if outline_a.language != "vi":
            special_instructions = ""
            if is_first_section:
                # COMMAND 1: Opening section - Hook + Subscribe CTA + Quiz
                if outline_a.channel_name:
                    special_instructions = f"""
SPECIAL INSTRUCTIONS FOR OPENING SECTION (COMMAND 1):
1. Write to create curiosity, mystery, and captivation
2. Create strong emotions, shock right from the start to HOOK into the viewer's mind
3. Make them compelled to watch until the end
4. Weave subscription mention for {outline_a.channel_name} NATURALLY - match the narrator's StyleA voice
🚧 AVOID: Generic phrases like "Don't forget to subscribe"
"""
                else:
                    special_instructions = """
SPECIAL INSTRUCTIONS FOR OPENING SECTION (COMMAND 1):
1. Write to create curiosity, mystery, and captivation
2. Create strong emotions, shock right from the start to HOOK into the viewer's mind
3. Make them compelled to watch until the end
❌ DO NOT mention subscribe, like, share, or any channel promotion
❌ NO call to action of any kind in this section
"""
                if add_quiz:
                    special_instructions += """
5. At the end, create a QUIZ question with 2 A/B options
   - Ask viewers to comment A or B to interact
   - Example: "In your opinion, what's most important: A) ... or B) ...? Comment your answer!"
"""
            elif is_last_section:
                # COMMAND 3: Closing section - Summary + Lesson + Subscribe CTA (NO quiz here)
                if outline_a.channel_name:
                    special_instructions = f"""
SPECIAL INSTRUCTIONS FOR CLOSING SECTION (COMMAND 3):
1. Write a profound summary (300-500 words) of all content
2. Provide a deep LESSON that can be applied to current daily life for viewers
3. Weave subscription mention for {outline_a.channel_name} NATURALLY - match the narrator's StyleA voice
4. This is the ONLY section where subscribe/like/share is allowed besides the opening
❌ NO engagement questions - keep it simple
🚧 AVOID: Generic phrases like "Don't forget to subscribe"
"""
                else:
                    special_instructions = """
SPECIAL INSTRUCTIONS FOR CLOSING SECTION (COMMAND 3):
1. Write a profound summary (300-500 words) of all content
2. Provide a deep LESSON that can be applied to current daily life for viewers
3. End with a natural, thoughtful conclusion
❌ DO NOT mention subscribe, like, share, or any channel promotion
❌ NO call to action of any kind - keep it pure content
❌ NO engagement questions - keep it simple
"""
            else:
                # COMMAND 2: Middle sections - Main content, NO CTA
                special_instructions = f"""
INSTRUCTIONS FOR MAIN CONTENT SECTION (COMMAND 2):
1. Use 1 sentence to smoothly connect with the previous section
2. Write coherently with emotion, continuously
3. Follow outline A closely, don't repeat content from previous sections
4. Focus 100% on providing VALUE to viewers

AVOID in this section:
- Mentioning subscribe, like, share, follow, or any call to action
- Interactive questions or quizzes asking for comments
- Channel promotion or engagement requests
- This section is PURE CONTENT ONLY
"""
            
            prompt = f"""Refine and rewrite the following section to be more engaging and profound:

CURRENT CONTENT:
{section.content}

SECTION INFO:
- Title: {outline_section.title}
- Target word count: {outline_section.word_count_target}
- Language: {lang_name} ({outline_a.dialect})

ORIGINAL STYLE:
- Tone: {original_analysis.writing_style.get('tone', 'neutral')}
- Narrative Voice: {original_analysis.narrative_voice}
{style_context}
{special_instructions}
REQUIREMENTS:
1. Write coherently with emotion
2. Write continuously, DO NOT break into sections, DO NOT use icons
3. Achieve exactly {outline_section.word_count_target} words (±10%)
4. Keep the core message but write more profoundly
5. APPLY THE LEARNED WRITING STYLE (StyleA) if provided above

IMPORTANT: Write ONLY in {lang_name}. Do NOT mix any other languages.

Write the refined content (ONLY content):
"""
        else:
            # Vietnamese prompt (only for vi)
            special_instructions = ""
            if is_first_section:
                # CÂU LỆNH 1: Phần mở bài - Hook + Subscribe CTA + Quiz
                if outline_a.channel_name:
                    special_instructions = f"""
HƯỚNG DẪN ĐẶC BIỆT CHO PHẦN MỞ BÀI (CÂU LỆNH 1):
1. Viết gây ra sự tò mò, bí ẩn, thu hút
2. Tạo cảm xúc mạnh, sốc ngay từ đầu để HOOK vào tâm trí khán giả
3. Khiến họ thôi thúc nghe đến cuối video
4. Sau hook, kêu gọi đăng ký kênh: "Đừng quên đăng ký kênh {outline_a.channel_name} để ủng hộ mình có động lực làm tiếp các video hay!"
"""
                else:
                    special_instructions = """
HƯỚNG DẪN ĐẶC BIỆT CHO PHẦN MỞ BÀI (CÂU LỆNH 1):
1. Viết gây ra sự tò mò, bí ẩn, thu hút
2. Tạo cảm xúc mạnh, sốc ngay từ đầu để HOOK vào tâm trí khán giả
3. Khiến họ thôi thúc nghe đến cuối video
❌ KHÔNG nhắc đăng ký kênh, subscribe, like, share
❌ KHÔNG có bất kỳ CTA nào trong phần này
"""
                if add_quiz:
                    special_instructions += """
5. Cuối phần, tạo CÂU HỎI TRẮC NGHIỆM suy ngẫm với 2 đáp án A/B
   - Yêu cầu người xem comment A hoặc B để tương tác
   - Ví dụ: "Theo bạn, điều quan trọng nhất là: A) ... hay B) ...? Comment đáp án của bạn!"
"""
            elif is_last_section:
                # CÂU LỆNH 3: Phần kết - Đúc kết + Bài học + Subscribe CTA (KHÔNG câu hỏi ở đây)
                if outline_a.channel_name:
                    special_instructions = f"""
HƯỚNG DẪN ĐẶC BIỆT CHO PHẦN KẾT (CÂU LỆNH 3):
1. Viết đoạn đúc kết sâu sắc (300-500 từ) về toàn bộ nội dung
2. Đưa ra BÀI HỌC sâu sắc và cách ÁP DỤNG vào cuộc sống hiện tại cho khán giả
3. Lồng ghép đăng ký {outline_a.channel_name} TỰ NHIÊN - match giọng StyleA
4. Đây là phần DUY NHẤT được phép nhắc subscribe/like/share ngoài phần mở bài
❌ KHÔNG thêm câu hỏi engagement - giữ đơn giản
🚧 TRÁNH: Câu generic như "Đừng quên đăng ký"
"""
                else:
                    special_instructions = """
HƯỚNG DẪN ĐẶC BIỆT CHO PHẦN KẾT (CÂU LỆNH 3):
1. Viết đoạn đúc kết sâu sắc (300-500 từ) về toàn bộ nội dung
2. Đưa ra BÀI HỌC sâu sắc và cách ÁP DỤNG vào cuộc sống hiện tại cho khán giả
3. Kết thúc bằng câu kết luận sâu sắc, tự nhiên
❌ KHÔNG nhắc đăng ký kênh, subscribe, like, share
❌ KHÔNG có bất kỳ CTA nào - giữ nội dung thuần túy
❌ KHÔNG thêm câu hỏi engagement - giữ đơn giản
"""
            else:
                # CÂU LỆNH 2: Phần giữa - Nội dung chính, KHÔNG CTA
                special_instructions = f"""
HƯỚNG DẪN CHO PHẦN NỘI DUNG CHÍNH (CÂU LỆNH 2):
1. Dùng 1 câu để kết nối tự nhiên với phần trước
2. Viết mạch lạc, có cảm xúc, xuyên suốt
3. Bám sát dàn ý A, không lặp lại nội dung các phần trước
4. Tập trung 100% vào việc tạo GIÁ TRỊ cho người xem

TRÁNH trong phần này:
- Nhắc subscribe, like, share, đăng ký kênh
- Câu hỏi tương tác hay quiz
- Quảng bá kênh hay kêu gọi engagement
- Phần này chỉ có NỘI DUNG THUẦN TÚY
"""
            
            prompt = f"""Tinh chỉnh và viết lại phần sau cho hay hơn, sâu sắc hơn:

NỘI DUNG HIỆN TẠI:
{section.content}

THÔNG TIN PHẦN:
- Tiêu đề: {outline_section.title}
- Số từ mục tiêu: {outline_section.word_count_target}
- Ngôn ngữ: {lang_name} ({outline_a.dialect})

PHONG CÁCH GỐC:
- Tone: {original_analysis.writing_style.get('tone', 'neutral')}
- Narrative Voice: {original_analysis.narrative_voice}
{style_context}
{special_instructions}
YÊU CẦU:
1. Viết mạch lạc và có cảm xúc
2. Viết xuyên suốt, KHÔNG chia từng phần, KHÔNG dùng icon
3. Đạt đúng {outline_section.word_count_target} từ (±10%)
4. Giữ nguyên core message nhưng viết sâu sắc hơn
5. ÁP DỤNG PHONG CÁCH VIẾT ĐÃ HỌC (StyleA) nếu có ở trên

QUAN TRỌNG: CHỈ viết bằng {lang_name}. KHÔNG trộn lẫn ngôn ngữ khác.

Viết nội dung đã tinh chỉnh (CHỈ nội dung):
"""
        try:
            response = self._route_task(TaskType.REFINEMENT, prompt, temperature=0.7)
            
            content = response.strip()
            if content.startswith("```"):
                content = re.sub(r'^```\w*\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            
            word_count = len(content.split())
            
            return DraftSection(
                section_id=section.section_id,
                content=content,
                version=section.version + 1,
                word_count=word_count,
                status="refined"
            )
            
        except Exception as e:
            logger.error(f"Step 6 refine failed: {e}")
            return section
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 7: Thêm giá trị mới
    # ═══════════════════════════════════════════════════════════════
    
    def add_value(
        self,
        draft: str,
        original_analysis: OriginalScriptAnalysis,
        outline_a: OutlineA,
        value_type: str = "",  # Empty if value type is disabled
        style_profile: Optional[Dict[str, Any]] = None,
        custom_value: str = ""
    ) -> str:
        """
        STEP 7: Đúc kết & CTA - Thêm phần kết luận và kêu gọi hành động
        
        value_type options:
        - sell: Đúc kết + Kêu gọi mua hàng (khóa học, sản phẩm)
        - engage: Đúc kết + Tương tác & Đăng ký (comment + subscribe)
        - community: Đúc kết + Tham gia cộng đồng & Đăng ký
        
        If value_type is empty, returns draft unchanged (user disabled value type toggle)
        """
        # If value_type is empty and no custom_value, skip adding value
        if not value_type and not custom_value:
            logger.info("📝 Step 7: Skipping add_value - value_type is disabled")
            return draft
        lang_names = {"en": "English", "vi": "Vietnamese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese"}
        lang_name = lang_names.get(outline_a.language, "English")
        
        # Build style context from StyleA if provided
        style_context = self._build_style_context(style_profile, language=outline_a.language)
        
        # Use language-specific prompts to prevent mixing languages
        if outline_a.language != "vi":
            value_instructions = {
                "sell": "Write a 300-400 word conclusion with deep lesson, then connect the content to the course/product and call viewers to purchase. Use urgency, scarcity, benefits, and pain points.",
                "engage": "Write a 300-500 word conclusion with deep lesson, then create a SIMPLE easy-to-answer question asking viewers to comment their opinion for discussion, then call for channel subscription.",
                "community": "Write a 300-500 word conclusion with deep lesson, then invite viewers to join the community for more knowledge, then call for channel subscription."
            }
            
            # Use custom_value if provided, otherwise use value_type
            if custom_value and custom_value.strip():
                base = value_instructions.get(value_type, value_instructions["engage"])
                instruction = f"{base}\nAdditional details: {custom_value}"
            else:
                instruction = value_instructions.get(value_type, value_instructions["engage"])
            
            prompt = f"""REWRITE the following script in {lang_name} with new value added throughout:

ORIGINAL SCRIPT TO REWRITE:
{draft}

VALUE TO ADD: {instruction}

Original Core Angle: {original_analysis.core_angle}
Viewer Insight: {original_analysis.viewer_insight}
{style_context}

INSTRUCTIONS:
1. REWRITE THE ENTIRE script from beginning to end
2. Integrate the new value NATURALLY at appropriate positions
3. Keep the same structure, tone and style
4. APPLY THE LEARNED WRITING STYLE (StyleA) if provided above
5. Output must be the COMPLETE ENHANCED SCRIPT, not a description of the value

AVOID:
- Technical terms: "Core Angle", "Hook", "CTA", "Retention"
- Meta-commentary about what you're doing
- Fabricating statistics, coordinates, or specific dates
- Quiz format A/B/C
- Repeating "I promise", "I believe" more than once
- "Subscribe", "like" only at the very end, if appropriate

📝 NATURAL VOICE:
- Write like a NATIVE SPEAKER, natural, with rhythm
- Use natural idioms, avoid literal translated metaphors
- Sentences should flow naturally like conversation

CRITICAL:
- Write ONLY in {lang_name}. Do NOT mix languages.
- Return the COMPLETE SCRIPT WITH VALUE INTEGRATED (no explanations, no titles)

Complete enhanced script:
"""
        else:
            # Vietnamese or other languages
            value_instructions = {
                "sell": "Viết đoạn đúc kết dài 300-400 từ với bài học sâu sắc, sau đó liên hệ nội dung với khóa học/sản phẩm và kêu gọi khán giả mua. Dùng ưu đãi, khan hiếm, khẩn cấp, lợi ích, nỗi đau nếu không mua.",
                "engage": "Viết đoạn đúc kết dài 300-500 từ với bài học sâu sắc, sau đó tạo 1 câu hỏi đơn giản dễ trả lời yêu cầu khán giả comment bình luận quan điểm, rồi kêu gọi đăng ký kênh để ủng hộ.",
                "community": "Viết đoạn đúc kết dài 300-500 từ với bài học sâu sắc, sau đó yêu cầu khán giả tham gia cộng đồng để nhận thêm kiến thức hữu ích, rồi kêu gọi đăng ký kênh."
            }
            
            # Use custom_value if provided, otherwise use value_type
            if custom_value and custom_value.strip():
                base = value_instructions.get(value_type, value_instructions["engage"])
                instruction = f"{base}\nThông tin bổ sung: {custom_value}"
            else:
                instruction = value_instructions.get(value_type, value_instructions["engage"])
            
            prompt = f"""VIẾT LẠI TOÀN BỘ kịch bản sau bằng {lang_name} với giá trị mới được thêm vào:

KỊCH BẢN GỐC CẦN VIẾT LẠI:
{draft}

YÊU CẦU THÊM GIÁ TRỊ: {instruction}

Core Angle gốc: {original_analysis.core_angle}
Viewer Insight: {original_analysis.viewer_insight}
{style_context}

HƯỚNG DẪN:
1. VIẾT LẠI TOÀN BỘ kịch bản từ đầu đến cuối
2. Chèn giá trị mới một cách TỰ NHIÊN vào các vị trí phù hợp
3. KHÔNG thay đổi cấu trúc chính, giữ nguyên tone và style
4. ÁP DỤNG PHONG CÁCH VIẾT ĐÃ HỌC (StyleA) nếu có ở trên  
5. Kết quả phải là SCRIPT HOÀN CHỈNH, không phải mô tả về giá trị

TRÁNH:
- Thuật ngữ kỹ thuật: "Core Angle", "Hook", "CTA", "Retention"
- Viết meta về việc bạn đang làm
- Bịa số liệu, tọa độ, ngày tháng không có trong gốc
- Format trắc nghiệm A/B/C
- Lặp "tôi hứa", "tôi tin" quá 1 lần
- "Subscribe", "like" chỉ ở cuối cùng, nếu phù hợp

📝 GIỌNG VĂN TỰ NHIÊN:
- Viết như NGƯỜI BẢN XỨ, tự nhiên, có nhịp thở
- Dùng thành ngữ phù hợp ngôn ngữ, tránh ẩn dụ dịch từ tiếng Anh
- Câu văn tự nhiên như đang trò chuyện

QUAN TRỌNG: 
- CHỈ viết bằng {lang_name}, KHÔNG trộn ngôn ngữ
- Trả về KỊch BẢN HOÀN CHỈNH ĐÃ THÊM GIÁ TRỊ (không giải thích, không title)

Kịch bản hoàn chỉnh:
"""
        try:
            response = self._route_task(TaskType.REFINEMENT, prompt, temperature=0.7)
            
            content = response.strip()
            if content.startswith("```"):
                content = re.sub(r'^```\w*\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            
            # Post-process to remove prompt terminology leakage
            content = self._clean_ai_output(content, language=outline_a.language)
            
            return content
            
        except Exception as e:
            logger.error(f"Step 7 add value failed: {e}")
            return draft
    
    @staticmethod
    def _detect_language_simple(text: str) -> str:
        """Detect language from text using character analysis. Returns ISO code."""
        import re
        sample = text[:2000]
        
        # Count character types
        cjk = len(re.findall(r'[\u4e00-\u9fff]', sample))
        hangul = len(re.findall(r'[\uac00-\ud7af\u1100-\u11ff]', sample))
        hiragana_katakana = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', sample))
        thai = len(re.findall(r'[\u0e00-\u0e7f]', sample))
        cyrillic = len(re.findall(r'[\u0400-\u04ff]', sample))
        vietnamese = len(re.findall(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', sample, re.IGNORECASE))
        latin = len(re.findall(r'[a-zA-Z]', sample))
        total = len(sample) or 1
        
        if hiragana_katakana > 10 or (cjk > 5 and hiragana_katakana > 3):
            return "ja"
        if hangul > 10:
            return "ko"
        if cjk > total * 0.1:
            return "zh"
        if thai > total * 0.1:
            return "th"
        if cyrillic > total * 0.1:
            return "ru"
        if vietnamese > total * 0.02:
            return "vi"
        if latin > total * 0.3:
            return "en"  # Default Latin = English
        return "en"
    
    # ═══════════════════════════════════════════════════════════════
    # FULL PIPELINE CONVERSATION: 7 bước trong 1 cuộc trò chuyện
    # ═══════════════════════════════════════════════════════════════
    
    def full_pipeline_conversation(
        self,
        original_script: str,
        target_word_count: int,
        source_language: str = "",
        language: str = "vi",
        dialect: str = "Northern Vietnamese",
        channel_name: str = "",
        country: str = "Vietnam",
        add_quiz: bool = False,
        value_type: str = "sell",
        storytelling_style: str = "",
        narrative_voice: str = "",
        custom_narrative_voice: str = "",
        audience_address: str = "",
        custom_audience_address: str = "",
        style_profile: Optional[Dict[str, Any]] = None,
        progress_callback=None,
        custom_value: str = ""
    ) -> Dict[str, Any]:
        """
        12-Step AI Script Generation Pipeline trong 1 CUỘC TRÒ CHUYỆN LIÊN TỤC.
        
        Workflow: AIDA -> Remember Script -> Analyze -> Structure -> StyleA -> Outline -> Write 3 Commands -> Review
        """
        results = {}
        conversation_id = None
        
        def _progress(step: str, percentage: int, message: str, message_en: str = ""):
            """Send progress update. Uses message_en when language is English."""
            if progress_callback:
                try:
                    msg = message_en if (language == "en" and message_en) else message
                    progress_callback(step, percentage, msg)
                except Exception:
                    pass
        
        # STEP 0: Analyze INPUT
        logger.info("📥 STEP 0: Analyzing user inputs...")
        _progress("init", 0, "Phân tích đầu vào...", "Analyzing input data...")
        
        user_inputs = {
            "original_script": original_script[:500] + "..." if len(original_script) > 500 else original_script,
            "target_word_count": target_word_count,
            "language": language,
            "dialect": dialect,
            "channel_name": channel_name,
            "storytelling_style": storytelling_style,
            "narrative_voice": narrative_voice,
            "custom_narrative_voice": custom_narrative_voice,
            "audience_address": audience_address,
            "custom_audience_address": custom_audience_address,
            "value_type": value_type,
            "add_quiz": add_quiz,
            "country": country
        }
        results["user_inputs"] = user_inputs
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 0.5: CROSS-LANGUAGE TRANSLATION (only when source ≠ output)
        # Translate the input script to the output language BEFORE the main pipeline.
        # This way, the pipeline works on a script already in the target language.
        # ═══════════════════════════════════════════════════════════════
        lang_names_pre = {"en": "English", "vi": "Vietnamese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "es": "Spanish", "fr": "French", "th": "Thai", "de": "German", "pt": "Portuguese", "ru": "Russian"}
        
        # Auto-detect source language if not explicitly set
        if source_language and source_language.strip():
            detected_src = source_language.strip()
        else:
            # Auto-detect from script content using character analysis
            detected_src = self._detect_language_simple(original_script)
            logger.info(f"🌐 Auto-detected input language: {detected_src}")
        
        needs_translation = (detected_src and detected_src != language)
        
        if needs_translation:
            source_language = detected_src  # Use detected language
            src_lang = source_language.strip()
            src_name = lang_names_pre.get(src_lang, src_lang)
            out_name = lang_names_pre.get(language, language)
            
            logger.info(f"🌐 STEP 0.5: Translating script from {src_name} to {out_name}...")
            _progress("translate", 2, f"Dịch: {src_name} → {out_name}...", f"Translating: {src_name} → {out_name}...")
            
            try:
                # Use a separate conversation for translation to keep it clean
                trans_conv_id = self.ai_client.create_conversation()
                
                translate_prompt = f"""You are a professional translator. Translate the following script from {src_name} to {out_name}.

Rules:
- Preserve the STRUCTURE (paragraphs, line breaks, sections) exactly.
- Prioritize NATURAL, fluent {out_name} over rigid literal translation.
- Adapt idioms and cultural references to feel natural in {out_name}.
- Keep proper nouns, brand names, and technical terms unchanged.
- Do NOT add commentary, notes, or explanations. Output ONLY the translated text.

--- SCRIPT TO TRANSLATE ---
{original_script}
--- END ---

Translated {out_name} script:"""
                
                translated = self.ai_client.send_message(trans_conv_id, translate_prompt, temperature=0.3)
                
                if translated and len(translated.strip()) > 50:
                    original_len = len(original_script.split())
                    translated_len = len(translated.strip().split())
                    logger.info(f"🌐 Translation done: {original_len} words ({src_name}) → {translated_len} words ({out_name})")
                    
                    # Replace the original script with translated version
                    original_script = translated.strip()
                    results["translation_applied"] = True
                    results["source_language"] = src_lang
                    results["translated_from"] = src_name
                    results["translated_to"] = out_name
                    
                    _progress("translate", 5, f"Dịch xong ({translated_len} từ)", f"Translation complete ({translated_len} words)")
                else:
                    logger.warning("🌐 Translation returned empty/short result, using original script")
                    _progress("translate", 5, "Dịch thất bại, dùng script gốc", "Translation failed, using original")
                    
            except Exception as e:
                logger.error(f"🌐 Translation error: {e}")
                _progress("translate", 5, f"Lỗi dịch, dùng script gốc", f"Translation error, using original")
        
        # Per-language narrative voice defaults
        LANG_NV_FIRST = {"vi": "tôi/mình", "en": "I/me", "ja": "私/僕", "ko": "나/저", "zh": "我", "es": "yo", "fr": "je", "th": "ผม/ฉัน", "de": "ich", "pt": "eu", "ru": "я"}
        LANG_NV_SECOND = {"vi": "bạn", "en": "you", "ja": "あなた", "ko": "당신", "zh": "你", "es": "tú", "fr": "tu/vous", "th": "คุณ", "de": "du/Sie", "pt": "você", "ru": "ты/вы"}
        LANG_NV_THIRD = {"vi": "họ/người đó", "en": "they/the narrator", "ja": "彼/彼女", "ko": "그/그녀", "zh": "他/她", "es": "él/ella", "fr": "il/elle", "th": "เขา/เธอ", "de": "er/sie", "pt": "ele/ela", "ru": "он/она"}
        LANG_AUDIENCE = {"vi": "bạn", "en": "you", "ja": "皆さん", "ko": "여러분", "zh": "大家", "es": "tú", "fr": "vous", "th": "คุณ", "de": "Sie", "pt": "você", "ru": "вы"}
        
        # Resolve narrative voice (language-aware defaults)
        if custom_narrative_voice and custom_narrative_voice.strip():
            resolved_narrative_voice = custom_narrative_voice.strip()
        elif narrative_voice:
            if narrative_voice == "first_person":
                resolved_narrative_voice = LANG_NV_FIRST.get(language, "I/me")
            elif narrative_voice == "second_person":
                resolved_narrative_voice = LANG_NV_SECOND.get(language, "you")
            elif narrative_voice == "third_person":
                resolved_narrative_voice = LANG_NV_THIRD.get(language, "they/the narrator")
            else:
                resolved_narrative_voice = LANG_NV_FIRST.get(language, "I/me")
        else:
            resolved_narrative_voice = LANG_NV_FIRST.get(language, "I/me")
        
        # Resolve audience address (language-aware defaults)
        if custom_audience_address and custom_audience_address.strip():
            resolved_audience_address = custom_audience_address.strip()
        elif audience_address:
            resolved_audience_address = audience_address
        else:
            resolved_audience_address = LANG_AUDIENCE.get(language, "you")
        
        results["resolved_narrative_voice"] = resolved_narrative_voice
        results["resolved_audience_address"] = resolved_audience_address
        logger.info(f"📋 Resolved: narrator='{resolved_narrative_voice}', audience='{resolved_audience_address}'")
        
        # Determine API - Use unified conversation API
        if not self.ai_client.has_conversation_support():
            raise Exception("No AI provider configured")
        
        lang_names = {"en": "English", "vi": "Vietnamese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "es": "Spanish", "fr": "French", "th": "Thai", "de": "German", "pt": "Portuguese", "ru": "Russian"}
        lang_name = lang_names.get(language, "English")
        use_en_prompts = (language != "vi")  # English prompts for all non-Vietnamese

        # ═══════════════════════════════════════════════════════════════
        # LANGUAGE CULTURE CONFIG - Culture-specific rules per language
        # ═══════════════════════════════════════════════════════════════
        LANGUAGE_CULTURE = {
            "en": {
                "writing_system": "",
                "idiom_rule": "Use natural English idioms and expressions. Avoid awkward literal translations.",
                "cultural_notes": "Write for a global English-speaking audience with universally relatable examples.",
                "formality": "Use a conversational but professional tone.",
            },
            "ja": {
                "writing_system": "Use correct kanji (漢字), hiragana (ひらがな), and katakana (カタカナ) throughout.",
                "idiom_rule": "Use natural Japanese expressions (慣用句/ことわざ). NEVER translate English idioms literally — find the authentic Japanese equivalent.",
                "cultural_notes": "Write with Japanese cultural sensitivity: respect hierarchy (上下関係), indirect communication style. Use examples familiar to Japanese viewers (日本の文化・社会). Avoid overly direct statements — prefer suggestion and nuance.",
                "formality": "Use です/ます form (丁寧語) by default for video narration. Adjust keigo (敬語) level based on the narrative voice setting.",
            },
            "ko": {
                "writing_system": "Use correct Korean spelling (맞춤법) and proper spacing (띄어쓰기). Use Hangul primarily with Hanja only when contextually appropriate.",
                "idiom_rule": "Use natural Korean expressions (관용구/속담). NEVER translate English idioms literally — find the authentic Korean equivalent.",
                "cultural_notes": "Write with Korean cultural sensitivity: respect age hierarchy (나이/서열), Confucian values. Use examples familiar to Korean viewers (한국 문화/사회). References should feel authentically Korean.",
                "formality": "Use 합니다체 (formal polite) by default for video narration. Adjust speech level (존댓말/반말) based on the narrative voice setting.",
            },
            "zh": {
                "writing_system": "Use simplified Chinese (简体中文) by default. Ensure correct character usage — no Japanese kanji substitutions.",
                "idiom_rule": "Use natural Chinese expressions (成语/俗语/歇后语). NEVER translate English idioms literally — find the authentic Chinese equivalent.",
                "cultural_notes": "Write with Chinese cultural sensitivity. Use examples familiar to Chinese-speaking viewers (中国文化/历史). Be mindful of cultural nuances. References should feel authentically Chinese.",
                "formality": "Use a conversational yet respectful tone (口语化但不失礼貌). Suitable for video content aimed at general audiences.",
            },
            "es": {
                "writing_system": "Ensure correct use of Spanish accents (á, é, í, ó, ú), ñ, and inverted punctuation (¿ ¡).",
                "idiom_rule": "Use natural Spanish expressions (refranes/modismos). NEVER translate English idioms literally — find the authentic Spanish equivalent.",
                "cultural_notes": "Write for a general Spanish-speaking audience. Be mindful of regional variations (Spain vs Latin America). Use universally understood Spanish.",
                "formality": "Use tú (informal) by default for engaging video content, unless the narrative voice suggests usted (formal).",
            },
            "fr": {
                "writing_system": "Ensure correct French accents (é, è, ê, ë, à, â, ù, û, ç, œ) and proper liaison rules.",
                "idiom_rule": "Use natural French expressions (proverbes/expressions idiomatiques). NEVER translate English idioms literally — find the authentic French equivalent.",
                "cultural_notes": "Write for a general French-speaking audience. Maintain the elegance and precision expected in French communication. Be mindful of francophone diversity.",
                "formality": "Use vous (formal) by default for wider audience appeal. Switch to tu only if the narrative voice explicitly calls for informal register.",
            },
            "th": {
                "writing_system": "Use correct Thai script (อักษรไทย) with proper tone marks and vowel placement.",
                "idiom_rule": "Use natural Thai expressions (สำนวน/สุภาษิต). NEVER translate English idioms literally — find the authentic Thai equivalent.",
                "cultural_notes": "Write with Thai cultural sensitivity: respect for elders and hierarchy, Buddhist values. Use examples familiar to Thai viewers (วัฒนธรรมไทย). Maintain appropriate level of politeness.",
                "formality": "Use polite language with appropriate particles (ครับ/ค่ะ). Maintain สุภาพ register suitable for video narration.",
            },
            "de": {
                "writing_system": "Use correct German orthography with proper Umlauts (ä, ö, ü) and Eszett (ß). Follow current Rechtschreibung rules.",
                "idiom_rule": "Use natural German expressions (Redewendungen/Sprichwörter). NEVER translate English idioms literally — find the authentic German equivalent.",
                "cultural_notes": "Write for a German-speaking audience (DACH region). Use culturally relevant examples. Be mindful of the distinction between formal and informal registers.",
                "formality": "Use Sie (formal) by default for wider audience appeal. Switch to du only if the narrative voice explicitly calls for informal register.",
            },
            "pt": {
                "writing_system": "Use correct Portuguese orthography with proper accents (á, â, ã, à, é, ê, í, ó, ô, õ, ú, ç). Follow Acordo Ortográfico.",
                "idiom_rule": "Use natural Portuguese expressions (provérbios/expressões idiomáticas). NEVER translate English idioms literally — find the authentic Portuguese equivalent.",
                "cultural_notes": "Write for a general Portuguese-speaking audience. Be mindful of Brazilian vs European Portuguese differences. Use universally understood Portuguese.",
                "formality": "Use você (informal polite) by default for engaging video content. Adjust formality based on the narrative voice setting.",
            },
            "ru": {
                "writing_system": "Use correct Russian Cyrillic script (кириллица) with proper spelling and grammar. Ensure correct use of ё when necessary.",
                "idiom_rule": "Use natural Russian expressions (пословицы/поговорки/фразеологизмы). NEVER translate English idioms literally — find the authentic Russian equivalent.",
                "cultural_notes": "Write for a Russian-speaking audience. Use culturally relevant examples from Russian life, history, and culture. Be mindful of formal vs informal contexts.",
                "formality": "Use вы (formal) by default for video narration. Switch to ты only if the narrative voice explicitly calls for informal register.",
            },
        }

        # Build culture_rules string for injection into prompts
        culture_cfg = LANGUAGE_CULTURE.get(language, LANGUAGE_CULTURE.get("en", {}))
        culture_rules_parts = []
        if culture_cfg.get("writing_system"):
            culture_rules_parts.append(f"- {culture_cfg['writing_system']}")
        if culture_cfg.get("idiom_rule"):
            culture_rules_parts.append(f"- {culture_cfg['idiom_rule']}")
        if culture_cfg.get("cultural_notes"):
            culture_rules_parts.append(f"- {culture_cfg['cultural_notes']}")
        if culture_cfg.get("formality"):
            culture_rules_parts.append(f"- {culture_cfg['formality']}")
        culture_rules = "\n".join(culture_rules_parts) if culture_rules_parts else ""


        style_context = self._build_style_context(style_profile, language=language)
        
        try:
            # STEP 1: Start conversation using unified API (auto-routes to configured provider)
            conversation_id = self.ai_client.start_conversation()
            logger.info(f"Started pipeline conversation: {conversation_id[:8]}...")
            
            # BƯỚC 2: Nhập cấu trúc AIDA (flexible ranges)
            logger.info("📚 [3%] Bước 2: Dạy cấu trúc AIDA...")
            _progress("step2_aida", 3, "Học cấu trúc AIDA...", "Learning AIDA structure...")
            
            # Flexible ranges instead of fixed percentages
            wc_opening_approx = int(target_word_count * 0.25)  # stages 1-4 combined
            wc_main_approx = int(target_word_count * 0.45)     # stage 5
            wc_closing_approx = int(target_word_count * 0.30)  # stages 6-8 combined
            
            if use_en_prompts:
                stage3_en = f'3. CTA #1: Light engagement' if channel_name else '3. INTERACTION: Questions, encourage comments. NO subscribe/like'
                stage4_en = f'4. BRAND INTRO: Brief channel intro.' if channel_name else '4. TRANSITION: Brief transition to main content.'
                stage7_en = f'7. CTA #2: Main CTA, subscribe' if channel_name else '7. CONCLUSION: Deep lesson, key takeaway. NO subscribe/like'
                cta_rule_en = 'CTAs ONLY in stages 3 and 7.' if channel_name else 'NO subscribe, like, share, or channel promotion ANYWHERE.'
                
                aida_prompt = f"""You are a video script writer. Learn this 8-stage structure as a FLEXIBLE GUIDE — not a rigid formula.

TARGET WORD COUNT: ~{target_word_count} words (approximate, prioritize natural flow over exact count)

8-STAGE STRUCTURE (proportions are approximate — adjust naturally):
1. HOOK/INTRO: Open with something that immediately pulls the viewer in
2. STATE THE PROBLEM: Present the core issue or question
{stage3_en}
{stage4_en}
5. MAIN CONTENT (~40-50%): The core value — insights, stories, analysis
6. DEEPEN: Go deeper, connect to real life, show why it matters
{stage7_en}
8. OUTRO: Natural ending that feels complete, not abrupt

{cta_rule_en}
The percentages are GUIDES. Let the content breathe naturally.

Reply only "Understood"."""
            else:
                stage3_vi = f'3. CTA #1: Tương tác nhẹ' if channel_name else f'3. TƯƠNG TÁC: Đặt câu hỏi, khuyến khích comment. KHÔNG subscribe'
                stage4_vi = f'4. GIỚI THIỆU KÊNH: Ngắn gọn.' if channel_name else f'4. CHUYỂN TIẾP: Dẫn dắt sang nội dung chính.'
                stage7_vi = f'7. CTA #2: CTA chính, đăng ký' if channel_name else f'7. ĐÚC KẾT: Bài học sâu sắc. KHÔNG subscribe/like'
                cta_rule_vi = 'CHỈ CTA ở giai đoạn 3 và 7.' if channel_name else 'KHÔNG subscribe, like, share, quảng bá kênh ở BẤT KỲ ĐÂU.'
                
                aida_prompt = f"""Bạn là người viết kịch bản video. Học cấu trúc 8 giai đoạn sau như HƯỚNG DẪN LINH HOẠT — không phải công thức cứng.

SỐ TỪ MỤC TIÊU: ~{target_word_count} từ (ước lượng, ưu tiên mạch lạc tự nhiên hơn đếm từ chính xác)

CẤU TRÚC 8 GIAI ĐOẠN (tỷ lệ linh hoạt — điều chỉnh theo nội dung):
1. MỞ ĐẦU: Mở bằng thứ khiến người xem muốn nghe tiếp
2. NÊU VẤN ĐỀ: Trình bày vấn đề/câu hỏi cốt lõi
{stage3_vi}
{stage4_vi}
5. NỘI DUNG CHÍNH (~40-50%): Giá trị cốt lõi — góc nhìn, câu chuyện, phân tích
6. ĐÀO SÂU: Kết nối với đời thực, cho thấy tại sao điều này quan trọng
{stage7_vi}
8. KẾT: Kết thúc tự nhiên, trọn vẹn

{cta_rule_vi}
Các tỷ lệ chỉ là HƯỚNG DẪN. Để nội dung phát triển tự nhiên.

Chỉ trả lời "Đã hiểu"."""

            response = self.ai_client.send_message(conversation_id, aida_prompt, temperature=0.3)
            logger.info(f"📚 Bước 2 done: {response[:30]}...")
            
            # BƯỚC 2.5: Tiền xử lý - Loại bỏ tên kênh gốc và CTA gốc
            logger.info("🧹 [5%] Bước 2.5: Loại bỏ tên kênh và CTA gốc...")
            _progress("step2_5_clean", 5, "Loại bỏ tên kênh & CTA gốc...", "Removing channel name & CTA...")
            
            if use_en_prompts:
                clean_prompt = f"""I will give you a script in {lang_name}. Please REMOVE the following elements and return ONLY the cleaned script:

1. ❌ Remove ALL channel name mentions (e.g. "This is [channel name]", "Welcome to [channel name]")
2. ❌ Remove ALL CTA (Call to Action) content: subscribe, like, share, bell notifications
3. ❌ Remove ALL product/book/course recommendations and purchase links
4. ❌ Remove ALL brand introductions of the original channel

KEEP everything else: the story, analysis, insights, lessons, emotions.

ORIGINAL SCRIPT:
{original_script}

Return ONLY the cleaned script in {lang_name} with no explanations."""
            else:
                clean_prompt = f"""Tôi sẽ đưa bạn một kịch bản. Hãy LOẠI BỎ các yếu tố sau và trả về CHỈ kịch bản đã làm sạch:

1. ❌ Xóa TẤT CẢ đề cập tên kênh (ví dụ: "Đây là [tên kênh]", "Chào mừng đến với [tên kênh]")
2. ❌ Xóa TẤT CẢ CTA (kêu gọi hành động): đăng ký, like, share, bật chuông
3. ❌ Xóa TẤT CẢ giới thiệu/quảng bá sản phẩm, sách, khóa học, link mua hàng
4. ❌ Xóa TẤT CẢ phần giới thiệu thương hiệu/kênh gốc

GIỮ LẠI tất cả phần còn lại: câu chuyện, phân tích, insight, bài học, cảm xúc.

KỊCH BẢN GỐC:
{original_script}

Trả về CHỈ kịch bản đã làm sạch, không giải thích."""
            
            try:
                cleaned_response = self.ai_client.send_message(conversation_id, clean_prompt, temperature=0.3)
                cleaned_script = cleaned_response.strip()
                # Validate: cleaned script should be at least 50% of original length
                if len(cleaned_script) >= len(original_script) * 0.3:
                    logger.info(f"🧹 Cleaned script: {len(original_script)} -> {len(cleaned_script)} chars ({len(cleaned_script)*100//len(original_script)}%)")
                else:
                    logger.warning(f"🧹 Cleaned script too short ({len(cleaned_script)} chars), using original")
                    cleaned_script = original_script
            except Exception as e:
                logger.warning(f"🧹 Cleaning failed: {e}, using original script")
                cleaned_script = original_script
            
            _progress("step2_5_done", 7, "Tên kênh & CTA đã loại bỏ", "Channel name & CTA removed")
            
            # BƯỚC 3: Ghi nhớ kịch bản gốc ĐÃ LÀM SẠCH (CHUNKED cho script dài)
            logger.info("📖 [8%] Bước 3: Ghi nhớ kịch bản đã làm sạch...")
            _progress("step3_remember", 8, "Ghi nhớ kịch bản...", "Memorizing script...")
            
            # Chunk CLEANED script into parts of ~6000 chars each for full memorization
            CHUNK_SIZE = 6000
            script_chunks = []
            for i in range(0, len(cleaned_script), CHUNK_SIZE):
                script_chunks.append(cleaned_script[i:i + CHUNK_SIZE])
            
            total_chunks = len(script_chunks)
            logger.info(f"📖 Cleaned script length: {len(cleaned_script)} chars -> {total_chunks} chunk(s)")
            
            for idx, chunk in enumerate(script_chunks, 1):
                if use_en_prompts:
                    remember_prompt = f"""Please learn and memorize the following content (Part {idx}/{total_chunks}):

{chunk}

Read carefully and memorize. Reply only "Memorized part {idx}"."""
                else:
                    remember_prompt = f"""Hãy học và ghi nhớ đoạn sau (Phần {idx}/{total_chunks}):

{chunk}

Đọc kỹ và ghi nhớ. Chỉ trả lời "Đã ghi nhớ phần {idx}"."""

                response = self.ai_client.send_message(conversation_id, remember_prompt, temperature=0.3)
                logger.info(f"📖 Bước 3 chunk {idx}/{total_chunks}: {response[:30]}...")
                _progress("step3_chunk", 8 + int(6 * idx / total_chunks), f"Ghi nhớ {idx}/{total_chunks}...", f"Memorizing {idx}/{total_chunks}...")
            
            # BƯỚC 4: Phân tích cấu trúc
            logger.info("📊 [15%] Bước 4: Phân tích cấu trúc...")
            _progress("step4_structure", 15, "Phân tích cấu trúc...", "Analyzing structure...")
            
            if use_en_prompts:
                step4_prompt = """Analyze structure: word count, hook duration, climax location.

Return JSON:
{"total_word_count": 0, "hook_duration": "", "climax_location": "", "payoff_location": "", "section_breakdown": []}

Return ONLY JSON."""
            else:
                step4_prompt = """Phân tích cấu trúc: số từ, thời lượng hook, vị trí cao trào.

Trả về JSON:
{"total_word_count": 0, "hook_duration": "", "climax_location": "", "payoff_location": "", "section_breakdown": []}

Chỉ trả về JSON."""

            response = self.ai_client.send_message(conversation_id, step4_prompt, temperature=0.5)
            
            try:
                clean = response.strip()
                if "{" in clean:
                    start = clean.find("{")
                    brace_count = 0
                    end = start
                    for i, c in enumerate(clean[start:]):
                        if c == '{': brace_count += 1
                        elif c == '}': brace_count -= 1
                        if brace_count == 0:
                            end = start + i + 1
                            break
                    data = json.loads(clean[start:end])
                    results["structure_analysis"] = StructureAnalysis(
                        total_word_count=data.get("total_word_count", len(original_script.split())),
                        hook_duration=data.get("hook_duration", "15-30s"),
                        climax_location=data.get("climax_location", "70%"),
                        payoff_location=data.get("payoff_location", "90%"),
                        section_breakdown=data.get("section_breakdown", [])
                    )
            except Exception:
                results["structure_analysis"] = StructureAnalysis(total_word_count=len(original_script.split()))
            
            logger.info("✅ Bước 4 complete")
            _progress("step4_done", 22, "Cấu trúc xong", "Structure complete")
            
            # BƯỚC 5: Phân tích nội dung gốc
            logger.info("📝 [25%] Bước 5: Phân tích nội dung gốc...")
            _progress("step5_analyze", 25, "Phân tích Core Angle, INSIGHT, HOOK...", "Analyzing Core Angle, INSIGHT, HOOK...")
            
            if use_en_prompts:
                step5_prompt = """Identify Core Angle, INSIGHT, HOOK, Style, Retention Engine, CTA strategy.

Return JSON:
{"core_angle": "", "main_ideas": [], "viewer_insight": "", "hook_analysis": {}, "writing_style": {}, "cultural_context": "", "narrative_voice": "", "retention_engine": "", "cta_strategy": ""}

Return ONLY JSON."""
            else:
                step5_prompt = """Xác định Core Angle, INSIGHT, HOOK, Phong cách, Retention Engine, CTA strategy.

Trả về JSON:
{"core_angle": "", "main_ideas": [], "viewer_insight": "", "hook_analysis": {}, "writing_style": {}, "cultural_context": "", "narrative_voice": "", "retention_engine": "", "cta_strategy": ""}

Chỉ trả về JSON."""

            response = self.ai_client.send_message(conversation_id, step5_prompt, temperature=0.5)
            results["original_analysis_raw"] = response
            
            try:
                clean_response = response.strip()
                if clean_response.startswith("```"):
                    clean_response = re.sub(r'^```(?:json)?\s*', '', clean_response)
                    clean_response = re.sub(r'\s*```$', '', clean_response)
                start_idx = clean_response.find('{')
                if start_idx != -1:
                    brace_count = 0
                    end_idx = start_idx
                    for i, char in enumerate(clean_response[start_idx:], start_idx):
                        if char == '{': brace_count += 1
                        elif char == '}': brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                    data = json.loads(clean_response[start_idx:end_idx])
                    results["original_analysis"] = OriginalScriptAnalysis(
                        core_angle=data.get("core_angle", ""),
                        main_ideas=data.get("main_ideas", []),
                        viewer_insight=data.get("viewer_insight", ""),
                        hook_analysis=data.get("hook_analysis", {}),
                        narrative_voice=data.get("narrative_voice", ""),
                        retention_engine=data.get("retention_engine", ""),
                        cta_strategy=data.get("cta_strategy", ""),
                        writing_style=data.get("writing_style", {}),
                        cultural_context=data.get("cultural_context", "")
                    )
            except Exception as e:
                logger.warning(f"Step 5 parse error: {e}")
                results["original_analysis"] = OriginalScriptAnalysis(core_angle="General", main_ideas=["Main idea"])
            
            # ═══════════════════════════════════════════════════════════════
            # MERGE: Ghép TÙY BIẾN từ kịch bản gốc vào StyleA → Giọng Văn A hoàn chỉnh
            # ═══════════════════════════════════════════════════════════════
            if style_profile and results.get("original_analysis"):
                analysis = results["original_analysis"]
                # Merge customizable fields from OriginalScriptAnalysis into StyleA
                style_profile["core_angle"] = analysis.core_angle
                style_profile["viewer_insight"] = analysis.viewer_insight
                style_profile["main_ideas"] = analysis.main_ideas
                logger.info(f"✅ Merged customizable fields into Giọng Văn A: core_angle='{analysis.core_angle[:50]}...'")
                
                # Rebuild style_context with complete Giọng Văn A
                style_context = self._build_style_context(style_profile, language=language)
            
            logger.info("✅ Bước 5 complete")
            _progress("step5_done", 30, "Phân tích nội dung xong", "Content analysis complete")
            
            # BƯỚC 6: Ghi nhớ giọng văn A
            logger.info("✍️ [33%] Bước 6: Ghi nhớ giọng văn A...")
            _progress("step6_style", 33, "Ghi nhớ giọng văn...", "Memorizing writing style...")
            
            # DEBUG: Log style_profile
            logger.info(f"🔍 DEBUG style_profile present: {style_profile is not None}")
            if style_profile:
                logger.info(f"🔍 DEBUG style_profile keys: {list(style_profile.keys())}")
            
            # Lấy NỘI DUNG từ analysis (Bước 4) và CẤU TRÚC từ structure (Bước 5)
            analysis_data = results.get("original_analysis")
            structure_data = results.get("structure_analysis")
            
            # Language-aware storytelling descriptions
            if use_en_prompts:
                storytelling_desc = {
                    "immersive": "IMMERSIVE/ROLE-PLAYING",
                    "documentary": "DOCUMENTARY",
                    "conversational": "CONVERSATIONAL",
                    "analytical": "ANALYTICAL",
                    "narrative": "NARRATIVE/STORYTELLING"
                }
            else:
                storytelling_desc = {
                    "immersive": "NHẬP VAI",
                    "documentary": "THUYẾT MINH",
                    "conversational": "ĐỐI THOẠI",
                    "analytical": "PHÂN TÍCH",
                    "narrative": "KỂ CHUYỆN"
                }
            
            # Build DNA section from style_profile (language-aware labels)
            dna_section = ""
            if style_profile:
                if use_en_prompts:
                    dna_section = """
🧬 PREFERRED WRITING STYLE DNA (keep 100% - from saved StyleA):"""
                else:
                    dna_section = """
🧬 DNA GIỌNG VĂN YÊU THÍCH (giữ nguyên 100% - từ StyleA đã lưu):"""
                
                # Voice description
                voice_label = "Voice/Style" if use_en_prompts else "Giọng văn"
                if style_profile.get("voice_description"):
                    dna_section += f"\n- {voice_label}: {style_profile['voice_description']}"
                elif style_profile.get("tone"):
                    dna_section += f"\n- {voice_label}: {style_profile['tone']}"
                
                # Storytelling approach
                storytelling_label = "Storytelling Approach" if use_en_prompts else "Cách dẫn chuyện"
                if style_profile.get("storytelling_approach"):
                    dna_section += f"\n- {storytelling_label}: {style_profile['storytelling_approach']}"
                elif style_profile.get("narrative_structure"):
                    dna_section += f"\n- {storytelling_label}: {style_profile['narrative_structure']}"
                
                # Author's Soul
                soul_label = "Author's Soul" if use_en_prompts else "Hồn văn"
                if style_profile.get("authors_soul"):
                    dna_section += f"\n- {soul_label}: {style_profile['authors_soul']}"
                
                # HOOK patterns (common_hook_types - NOT hook_patterns)
                hooks = style_profile.get("common_hook_types") or style_profile.get("hook_patterns")
                if hooks:
                    if isinstance(hooks, list):
                        dna_section += f"\n- HOOK patterns: {', '.join(str(h) for h in hooks[:3])}"
                    else:
                        dna_section += f"\n- HOOK patterns: {hooks}"
                
                # Retention patterns (retention_techniques)
                retention = style_profile.get("retention_techniques") or style_profile.get("retention_patterns")
                if retention:
                    if isinstance(retention, list):
                        dna_section += f"\n- Retention patterns: {', '.join(str(r) for r in retention[:3])}"
                    else:
                        dna_section += f"\n- Retention patterns: {retention}"
                
                # CTA patterns
                if style_profile.get("cta_patterns"):
                    cta = style_profile["cta_patterns"]
                    if isinstance(cta, list):
                        dna_section += f"\n- CTA patterns: {', '.join(str(c) for c in cta[:3])}"
                    else:
                        dna_section += f"\n- CTA patterns: {cta}"
                
                # Emotional range
                if style_profile.get("emotional_range"):
                    emotions = style_profile["emotional_range"]
                    if isinstance(emotions, list):
                        dna_section += f"\n- Emotional range: {', '.join(str(e) for e in emotions[:5])}"
                    else:
                        dna_section += f"\n- Emotional range: {emotions}"
                
                # vocabulary_level (additional)
                if style_profile.get("vocabulary_level"):
                    dna_section += f"\n- Vocabulary level: {style_profile['vocabulary_level']}"
                
                # key_phrases (additional)
                if style_profile.get("key_phrases"):
                    phrases = style_profile["key_phrases"]
                    if isinstance(phrases, list):
                        dna_section += f"\n- Key phrases: {', '.join(str(p) for p in phrases[:5])}"
                    else:
                        dna_section += f"\n- Key phrases: {phrases}"
                
                logger.info(f"🧬 DNA section built: {len(dna_section)} chars")
            
            # Build CONTENT section from original_analysis (language-aware headers)
            content_section = ""
            if analysis_data:
                if use_en_prompts:
                    content_header = "CONTENT FROM ORIGINAL SCRIPT (Step 4)"
                else:
                    content_header = "NỘI DUNG TỪ KỊCH BẢN GỐC (Bước 4)"
                content_section = f"""

📝 {content_header}:
- Core Angle: {getattr(analysis_data, 'core_angle', 'N/A')}
- Main Ideas: {getattr(analysis_data, 'main_ideas', [])}
- Viewer Insight: {getattr(analysis_data, 'viewer_insight', 'N/A')}
- Cultural Context: {getattr(analysis_data, 'cultural_context', 'N/A')}"""
            
            # Build STRUCTURE section from structure_analysis (language-aware headers)
            structure_section = ""
            if structure_data:
                if use_en_prompts:
                    structure_header = "RHYTHM & STRUCTURE (Step 5)"
                else:
                    structure_header = "CẤU TRÚC NHỊP ĐIỆU (Bước 5)"
                structure_section = f"""

📊 {structure_header}:
- Hook Duration: {getattr(structure_data, 'hook_duration', '15-30s')}
- Climax Location: {getattr(structure_data, 'climax_location', '70%')}
- Payoff Location: {getattr(structure_data, 'payoff_location', '90%')}"""
            
            if use_en_prompts:
                style_merge = f"""Memorize and apply Writing Style A:
{dna_section}
{content_section}
{structure_section}

✏️ CUSTOMIZABLE SETTINGS (can be adjusted):
- Narrator: Always use "{resolved_narrative_voice}"
- Audience: Always address as "{resolved_audience_address}" """
                if storytelling_style:
                    style_merge += f"\n- Storytelling Style: {storytelling_desc.get(storytelling_style, storytelling_style)}"
                style_merge += f"""

RULES: Use the DNA from saved StyleA for VOICE/STYLE. Use content from original script. Write like a REAL PERSON. NO icons. NO jargon. Write ONLY in {lang_name}.

🌍 CULTURAL & LANGUAGE RULES:
{culture_rules}

Reply only "Style A memorized"."""
            else:
                style_merge = f"""Ghi nhớ và áp dụng Giọng văn A:
{dna_section}
{content_section}
{structure_section}

✏️ PHẦN TÙY BIẾN (có thể điều chỉnh):
- Ngôi kể: Luôn xưng "{resolved_narrative_voice}"
- Khán giả: Luôn gọi là "{resolved_audience_address}" """
                if storytelling_style:
                    style_merge += f"\n- Phong cách kể: {storytelling_desc.get(storytelling_style, storytelling_style)}"
                style_merge += f"""

QUY TẮC: Dùng DNA từ StyleA đã lưu cho GIỌNG VĂN/PHONG CÁCH. Dùng nội dung từ kịch bản gốc. Viết như NGƯỜI THẬT. KHÔNG icon. KHÔNG thuật ngữ. CHỈ viết bằng {lang_name}.

Chỉ trả lời "Đã ghi nhớ giọng văn A"."""

            response = self.ai_client.send_message(conversation_id, style_merge, temperature=0.3)
            logger.info(f"✍️ Bước 6 done: {response[:30]}...")
            _progress("step6_done", 38, "Giọng văn xong", "Style memorized")
            
            # BƯỚC 7: Tạo dàn ý B
            logger.info("📋 [40%] Bước 7: Tạo dàn ý B...")
            _progress("step7_outline", 40, "Tạo dàn ý...", "Creating outline...")
            
            if use_en_prompts:
                step7_prompt = f"""Create Outline B in {lang_name}. Max 5 sections. Target {target_word_count} words. Use AIDA.

Return JSON:
{{"sections": [{{"id": "section_1", "title": "", "description": "", "word_count_target": 0, "key_points": [], "aida_stages": "", "special_instructions": ""}}]}}

Return ONLY JSON."""
            else:
                step7_prompt = f"""Tạo dàn ý B bằng {lang_name}. Tối đa 5 phần. Mục tiêu {target_word_count} từ. Dùng AIDA.

Trả về JSON:
{{"sections": [{{"id": "section_1", "title": "", "description": "", "word_count_target": 0, "key_points": [], "aida_stages": "", "special_instructions": ""}}]}}

Chỉ trả về JSON."""

            response = self.ai_client.send_message(conversation_id, step7_prompt, temperature=0.5)
            results["outline_a_raw"] = response
            
            try:
                clean = response.strip()
                if "{" in clean:
                    start = clean.find("{")
                    brace_count = 0
                    end = start
                    for i, c in enumerate(clean[start:]):
                        if c == '{': brace_count += 1
                        elif c == '}': brace_count -= 1
                        if brace_count == 0:
                            end = start + i + 1
                            break
                    data = json.loads(clean[start:end])
                    
                    sections = []
                    for s in data.get("sections", []):
                        sections.append(OutlineSectionA(
                            id=s.get("id", f"section_{len(sections)+1}"),
                            title=s.get("title", ""),
                            description=s.get("description", ""),
                            order=len(sections)+1,
                            word_count_target=s.get("word_count_target", 100),
                            key_points=s.get("key_points", []),
                            special_instructions=s.get("special_instructions", "")
                        ))
                    
                    results["outline_a"] = OutlineA(
                        sections=sections,
                        target_word_count=target_word_count,
                        language=language,
                        dialect=dialect,
                        channel_name=channel_name,
                        narrative_voice=narrative_voice or "Ngôi thứ nhất",
                        audience_address=audience_address or "bạn"
                    )
            except Exception as e:
                logger.warning(f"Bước 7 parse error: {e}")
                results["outline_a"] = self._create_default_outline_a(target_word_count, language, dialect, channel_name, 5, storytelling_style, narrative_voice, audience_address)
            
            logger.info(f"✅ Bước 7: {len(results['outline_a'].sections)} sections")
            _progress("step7_done", 45, f"Dàn ý: {len(results['outline_a'].sections)} sections", f"Outline: {len(results['outline_a'].sections)} sections")
            
            # BƯỚC 8: Viết 3 CÂU LỆNH
            logger.info("✍️ [48%] Bước 8: Viết 3 câu lệnh...")
            _progress("step8_write", 48, "Viết nội dung...", "Writing content...")
            
            # CL1 = stages 1-4 (~25-30%), CL2 = stage 5 (~40-50%), CL3 = stages 6-8 (~25-30%)
            wc_opening = int(target_word_count * 0.28)
            wc_body = int(target_word_count * 0.44)
            wc_closing = int(target_word_count * 0.28)
            
            full_content = ""
            draft_sections = []
            
            # CL1: Mở bài (stages 1-4)
            logger.info("✍️ CL1: Mở bài...")
            _progress("cl1", 50, "Viết mở bài...", "Writing opening...")
            
            quiz_instr = ""
            if add_quiz:
                quiz_instr = "\n- Tạo 1 câu hỏi trắc nghiệm A/B để tương tác" if not use_en_prompts else "\n- Create a short A/B quiz"
            
            if use_en_prompts:
                greeting_instr = f'- Include greeting: "This is {channel_name}"\n- After hook, call for subscribe' if channel_name else '- NO channel greeting, NO subscribe/like/share calls'
                cl1 = f"""Using Style A and Outline B, write OPENING (stages 1-4 combined). ~{wc_opening} words.
- Open naturally — draw the viewer in with genuine curiosity or emotion
{greeting_instr}{quiz_instr}
- Apply hook techniques from Style A
- Write in {lang_name} as a native speaker would naturally speak. No icons. No canvas.
{culture_rules}

{f'Do NOT use any channel name, brand, or CTA from the ORIGINAL script. Use ONLY "{channel_name}".' if channel_name else 'No channel names, brands, or CTAs. No subscribe/like/share.'} No books, products, or courses from the original.

Write opening ONLY:"""
            else:
                greeting_instr_vi = f'- Chèn lời chào: "Đây là {channel_name}"\n- Sau hook, kêu gọi đăng ký kênh' if channel_name else '- KHÔNG chào tên kênh, KHÔNG nhắc subscribe/like/share/đăng ký kênh'
                cl1 = f"""Dựa trên Giọng văn A và Dàn ý B, viết MỞ BÀI (gộp giai đoạn 1-4). ~{wc_opening} từ.
- Mở đầu tự nhiên — cuốn người xem bằng sự tò mò hoặc cảm xúc thật
{greeting_instr_vi}{quiz_instr}
- Áp dụng kỹ thuật mở bài từ Giọng văn A
- Viết bằng {lang_name} như người bản xứ thực sự nói. Không icon. Tắt canvas.
- ĐẢM BẢO dấu tiếng Việt đầy đủ (bạn, không, được, mình, những).

{f'KHÔNG dùng bất kỳ tên kênh, thương hiệu, hay CTA nào từ kịch bản GỐC. CHỈ dùng "{channel_name}".' if channel_name else 'KHÔNG nhắc subscribe, like, share, đăng ký kênh.'} KHÔNG đề cập sách, sản phẩm, khóa học từ kịch bản gốc.

Chỉ viết mở bài:"""

            response = self.ai_client.send_message(conversation_id, cl1, temperature=0.7)
            cl1_content = self._clean_ai_output(response.strip(), language=language)
            
            draft_sections.append(DraftSection(section_id="opening_1_4", content=cl1_content, version=1, word_count=len(cl1_content.split()), status="refined"))
            full_content += cl1_content + "\n\n"
            logger.info(f"✅ CL1: {len(cl1_content.split())} words")
            _progress("cl1_done", 58, f"Mở bài: {len(cl1_content.split())} từ", f"Opening: {len(cl1_content.split())} words")
            
            # CL2: Nội dung chính (stage 5)
            logger.info("✍️ CL2: Nội dung chính...")
            _progress("cl2", 60, "Viết nội dung chính...", "Writing main content...")
            
            if use_en_prompts:
                cl2 = f"""Continue with Style A, write stage 5 (Main Content). ~{wc_body} words.
- Connect naturally with the previous section
- This is the HEART of the video — deliver real value through stories, insights, analysis
- Maintain the Core Angle analyzed earlier
- Write in {lang_name} as a native speaker would. No icons. No canvas.
{culture_rules}

No subscribe, like, share, quiz, or channel promotion.
No channel names, brands, books, products, or courses from the ORIGINAL script.

Write main content ONLY:"""
            else:
                cl2 = f"""Tiếp tục với Giọng văn A, viết giai đoạn 5 (Nội dung chính). ~{wc_body} từ.
- Kết nối tự nhiên với phần trước
- Đây là TRÁI TIM của video — mang lại giá trị thật qua câu chuyện, góc nhìn, phân tích
- Giữ đúng góc nhìn chủ đạo đã phân tích
- Viết bằng {lang_name} như người bản xứ thực sự nói. Không icon. Tắt canvas.
- ĐẢM BẢO dấu tiếng Việt đầy đủ.

Không nhắc subscribe, like, share, quiz, quảng bá kênh.
KHÔNG dùng tên kênh, thương hiệu, tên sách/sản phẩm/khóa học từ kịch bản GỐC.

Chỉ viết nội dung chính:"""

            response = self.ai_client.send_message(conversation_id, cl2, temperature=0.7)
            cl2_content = self._clean_ai_output(response.strip(), language=language)
            
            draft_sections.append(DraftSection(section_id="main_5", content=cl2_content, version=1, word_count=len(cl2_content.split()), status="refined"))
            full_content += cl2_content + "\n\n"
            logger.info(f"✅ CL2: {len(cl2_content.split())} words")
            _progress("cl2_done", 72, f"Nội dung chính: {len(cl2_content.split())} từ", f"Main content: {len(cl2_content.split())} words")
            
            # CL3: Kết (stages 6-8)
            logger.info("✍️ CL3: Phần kết...")
            _progress("cl3", 74, "Viết phần kết...", "Writing closing...")
            
            value_instr = ""
            if value_type or custom_value:
                if use_en_prompts:
                    val_map = {"sell": "call to purchase", "engage": "engagement & subscribe", "community": "join community & subscribe"}
                else:
                    val_map = {"sell": "kêu gọi mua hàng", "engage": "tương tác & đăng ký", "community": "tham gia cộng đồng & đăng ký"}
                
                if custom_value and custom_value.strip():
                    if not use_en_prompts:
                        value_instr = f"\n- Thêm giá trị: {custom_value}"
                    else:
                        value_instr = f"\n- Add value: {custom_value}"
                elif value_type:
                    if not use_en_prompts:
                        value_instr = f"\n- Thêm giá trị: {val_map.get(value_type, value_type)}"
                    else:
                        value_instr = f"\n- Add value: {val_map.get(value_type, value_type)}"
            
            if use_en_prompts:
                if channel_name:
                    cta_closing_en = f"- Use CTA approach from Style A\n- Include subscribe to {channel_name}{value_instr}"
                    closing_warning_en = f'Use ONLY "{channel_name}" as channel name. No names, brands, or products from the original script.'
                else:
                    cta_closing_en = f"- Provide a natural, thoughtful conclusion{value_instr}\n- NO subscribe, like, share, or channel promotion"
                    closing_warning_en = 'No channel names, brands, or CTAs. Focus on a meaningful conclusion.'
                cl3 = f"""Finish with Style A, combine stages 6-8 into closing. ~{wc_closing} words.
- Flow naturally from the previous section
- Provide depth — a real lesson or insight the viewer takes away
{cta_closing_en}
- Write in {lang_name} as a native speaker would. No icons. No canvas.
{culture_rules}

{closing_warning_en}

Write closing ONLY:"""
            else:
                if channel_name:
                    cta_closing_vi = f"- Dùng cách CTA từ Giọng văn A\n- Kêu gọi đăng ký kênh {channel_name}{value_instr}"
                    closing_warning_vi = f'CHỈ dùng "{channel_name}" làm tên kênh. Không dùng tên, thương hiệu, sản phẩm từ kịch bản gốc.'
                else:
                    cta_closing_vi = f"- Đưa ra kết luận tự nhiên, sâu sắc{value_instr}\n- KHÔNG nhắc subscribe, like, share, đăng ký kênh"
                    closing_warning_vi = 'KHÔNG nhắc subscribe, like, share. Tập trung vào bài học ý nghĩa.'
                cl3 = f"""Hoàn thành với Giọng văn A, gộp giai đoạn 6-8 thành đoạn kết. ~{wc_closing} từ.
- Kết nối tự nhiên với phần trước
- Đưa ra bài học sâu sắc, điều người xem thực sự mang đi được
{cta_closing_vi}
- Viết bằng {lang_name} như người bản xứ thực sự nói. Không icon. Tắt canvas.
- ĐẢM BẢO dấu tiếng Việt đầy đủ.

{closing_warning_vi}

Chỉ viết phần kết:"""

            response = self.ai_client.send_message(conversation_id, cl3, temperature=0.7)
            cl3_content = self._clean_ai_output(response.strip(), language=language)
            
            draft_sections.append(DraftSection(section_id="closing_6_8", content=cl3_content, version=1, word_count=len(cl3_content.split()), status="refined"))
            full_content += cl3_content
            logger.info(f"✅ CL3: {len(cl3_content.split())} words")
            _progress("cl3_done", 80, f"Phần kết: {len(cl3_content.split())} từ", f"Closing: {len(cl3_content.split())} words")
            
            results["draft_sections"] = draft_sections
            results["refined_sections"] = draft_sections
            
            # BƯỚC 9: Auto-continue
            current_wc = len(full_content.split())
            threshold = target_word_count * 0.9
            
            if current_wc < threshold:
                logger.info(f"📝 Bước 9: Auto-continue {current_wc}/{target_word_count}")
                _progress("step9", 82, f"Bổ sung ({current_wc}/{target_word_count} từ)...", f"Expanding ({current_wc}/{target_word_count} words)...")
                
                needed = target_word_count - current_wc
                cont_prompt = f"Viết tiếp ~{needed} từ. Giữ phong cách. KHÔNG thêm CTA. Tắt canvas." if not use_en_prompts else f"Continue with ~{needed} words. Keep style. NO new CTAs."
                
                try:
                    cont = self.ai_client.send_message(conversation_id, cont_prompt, temperature=0.7)
                    cont_content = self._clean_ai_output(cont.strip(), language=language)
                    full_content += "\n\n" + cont_content
                    logger.info(f"✅ Auto-continue: +{len(cont_content.split())} words")
                except Exception as e:
                    logger.warning(f"Auto-continue failed: {e}")
            
            _progress("step9_done", 85, f"Bổ sung xong: {len(full_content.split())} từ", f"Expansion done: {len(full_content.split())} words")
            
            # BƯỚC 10: Kiểm tra
            logger.info("🔍 [88%] Bước 10: Kiểm tra...")
            _progress("step10", 88, "Kiểm tra tương đồng...", "Checking similarity...")
            
            if use_en_prompts:
                country_check = f"\n5. ✅ Violated {country} law?" if country else ""
            else:
                country_check = f"\n5. ✅ Vi phạm pháp luật {country}?" if country else ""
            
            if use_en_prompts:
                review = f"""Review content:
1. ✅ Similar to original?
2. ✅ Repetitive content?
3. ✅ YouTube guidelines violated?
4. ✅ Narrator "{resolved_narrative_voice}" consistent?
4b. ✅ Audience "{resolved_audience_address}" consistent?{country_check}

Brief review:"""
            else:
                review = f"""Kiểm tra:
1. ✅ Tương đồng với gốc?
2. ✅ Lặp nội dung?
3. ✅ Vi phạm YouTube?
4. ✅ Ngôi kể "{resolved_narrative_voice}" nhất quán?
4b. ✅ Xưng hô "{resolved_audience_address}" nhất quán?{country_check}

Trả lời ngắn:"""

            try:
                review_resp = self.ai_client.send_message(conversation_id, review, temperature=0.3)
                results["similarity_review"] = review_resp.strip()
            except:
                results["similarity_review"] = "Review skipped"
            
            _progress("step10_done", 93, "Kiểm tra xong", "Check complete")
            
            # BƯỚC 12: Kiểm tra cuối
            logger.info("🔍 [95%] Bước 12: Kiểm tra cuối...")
            _progress("step12", 95, "Kiểm tra cuối cùng...", "Final check...")
            
            if use_en_prompts:
                final = f"""FINAL CHECK:
1. Content similar to original?
2. No repetition?
3. YouTube compliant?
4. No jargon leaked?
5. Narrator "{resolved_narrative_voice}" consistent?
6. Audience "{resolved_audience_address}" consistent?

Brief validation:"""
            else:
                final = f"""KIỂM TRA CUỐI:
1. Tương đồng nội dung?
2. Không lặp?
3. Không vi phạm YouTube?
4. Không lọt thuật ngữ?
5. Ngôi kể "{resolved_narrative_voice}" nhất quán?
6. Xưng hô "{resolved_audience_address}" nhất quán?

Trả lời ngắn:"""

            try:
                final_resp = self.ai_client.send_message(conversation_id, final, temperature=0.3)
                results["validation_result"] = final_resp.strip()
            except:
                results["validation_result"] = "Validation skipped"
            
            results["final_script"] = self._clean_ai_output(full_content.strip(), language=language)
            results["word_count"] = len(results["final_script"].split())
            
            logger.info(f"✅ Pipeline complete! {results['word_count']} words")
            _progress("complete", 100, f"Hoàn thành: {results['word_count']} từ", f"Complete: {results['word_count']} words")
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            raise
        finally:
            if conversation_id:
                try:
                    self.ai_client.end_conversation(conversation_id)
                    logger.info(f"Ended conversation: {conversation_id[:8]}...")
                except:
                    pass
        
        return results


# Template presets

SCRIPT_TEMPLATES = {
    "educational": {
        "name": "Video Giáo dục",
        "description": "Template cho video hướng dẫn, giải thích kiến thức",
        "style": StyleProfile(
            tone="educational",
            vocabulary_level="intermediate",
            sentence_structure="mixed",
            pacing="moderate",
            target_audience="general"
        ),
        "structure": ["Intro", "Problem/Question", "Explanation", "Examples", "Summary", "CTA"]
    },
    "storytelling": {
        "name": "Video Kể chuyện", 
        "description": "Template cho video narrative, story-driven",
        "style": StyleProfile(
            tone="dramatic",
            vocabulary_level="intermediate",
            sentence_structure="complex",
            pacing="slow",
            emotional_range="emotional",
            target_audience="general"
        ),
        "structure": ["Hook", "Setup", "Rising Action", "Climax", "Resolution", "Outro"]
    },
    "marketing": {
        "name": "Video Marketing",
        "description": "Template cho video quảng cáo, giới thiệu sản phẩm",
        "style": StyleProfile(
            tone="inspiring",
            vocabulary_level="simple",
            sentence_structure="short",
            pacing="fast",
            emotional_range="emotional",
            target_audience="general"
        ),
        "structure": ["Attention", "Problem", "Solution", "Benefits", "Social Proof", "CTA"]
    },
    "podcast": {
        "name": "Podcast/Talkshow",
        "description": "Template cho podcast, video conversational",
        "style": StyleProfile(
            tone="casual",
            vocabulary_level="simple",
            sentence_structure="short",
            pacing="moderate",
            emotional_range="mixed",
            target_audience="general"
        ),
        "structure": ["Intro", "Topic Overview", "Main Discussion", "Key Takeaways", "Outro"]
    }
}


def get_template(template_id: str) -> Optional[Dict]:
    """Get a template by ID"""
    return SCRIPT_TEMPLATES.get(template_id)


def list_templates() -> List[Dict]:
    """List all available templates"""
    return [
        {
            "id": k,
            "name": v["name"],
            "description": v["description"],
            "structure": v["structure"]
        }
        for k, v in SCRIPT_TEMPLATES.items()
    ]
