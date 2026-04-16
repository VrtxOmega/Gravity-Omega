"""
VERITAS NEURAL CORE
Advanced conversational AI routing with memory and context awareness
"""
import re
from typing import Dict, List, Any
from datetime import datetime
from collections import deque


class ConversationMemory:
    """Maintains conversation context and user preferences"""
    
    def __init__(self, max_history: int = 50):
        self.history = deque(maxlen=max_history)
        self.user_profile = {
            "name": None,
            "preferences": {},
            "common_tasks": [],
            "interaction_style": "professional"  # casual, professional, technical
        }
        self.session_context = {}
    
    def add_exchange(self, user_msg: str, system_response: str, metadata: Dict = None):
        """Record a conversation exchange"""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "user": user_msg,
            "system": system_response,
            "metadata": metadata or {}
        })
    
    def get_recent_context(self, n: int = 5) -> List[Dict]:
        """Get last N conversation exchanges"""
        return list(self.history)[-n:]
    
    def extract_preferences(self, user_input: str):
        """Learn from user's language patterns"""
        # Detect formality level
        casual_markers = ["hey", "yeah", "gonna", "wanna", "cool", "awesome"]
        technical_markers = ["execute", "compile", "deploy", "initialize", "configure"]
        
        if any(marker in user_input.lower() for marker in casual_markers):
            self.user_profile["interaction_style"] = "casual"
        elif any(marker in user_input.lower() for marker in technical_markers):
            self.user_profile["interaction_style"] = "technical"


class NeuralRouter:
    """
    Advanced intent classification and parameter extraction
    Converts natural language to structured commands
    """
    
    def __init__(self):
        self.memory = ConversationMemory()
        self.intent_patterns = self._build_intent_patterns()
        
    def _build_intent_patterns(self) -> Dict[str, List[Dict]]:
        """Define natural language patterns for each intent"""
        return {
            "AUDIT": [
                {
                    "patterns": [
                        r"(?:run|execute|perform|do|start)\s+(?:an?\s+)?audit",
                        r"audit\s+(?:the\s+)?(.+)",
                        r"check\s+(?:the\s+)?(.+)\s+(?:for\s+)?(?:issues|problems|anomalies)",
                        r"analyze\s+(.+)",
                        r"verify\s+(.+)",
                    ],
                    "param_extraction": {
                        "target": r"(?:audit|check|analyze|verify)\s+(?:the\s+)?([a-zA-Z0-9\s_-]+)",
                        "scope": r"(?:for|in|within)\s+([a-zA-Z0-9\s_-]+)"
                    }
                }
            ],
            "PULSE": [
                {
                    "patterns": [
                        r"(?:search|find|look\s+up|get\s+info(?:rmation)?)\s+(?:about\s+)?(.+)",
                        r"what(?:'s|\s+is)\s+(?:the\s+)?(?:latest|current)\s+(?:on\s+)?(.+)",
                        r"pulse\s+(?:on\s+)?(.+)",
                        r"web\s+(?:search|scan)\s+(.+)"
                    ],
                    "param_extraction": {
                        "topic": r"(?:about|on|for)\s+([^.!?]+)"
                    }
                }
            ],
            "STATUS": [
                {
                    "patterns": [
                        r"(?:what(?:'s|\s+is)|show)\s+(?:the\s+)?(?:system\s+)?status",
                        r"how\s+(?:is|are)\s+(?:things|systems?|everything)",
                        r"(?:health|diagnostic)\s+(?:check|report)",
                        r"are\s+you\s+(?:alive|online|working)"
                    ]
                }
            ],
            "REPORT": [
                {
                    "patterns": [
                        r"(?:generate|create|make|produce)\s+(?:a\s+)?report",
                        r"report\s+on\s+(.+)",
                        r"(?:show|give)\s+me\s+(?:a\s+)?(?:summary|overview)",
                    ],
                    "param_extraction": {
                        "topic": r"(?:on|about|for)\s+([^.!?]+)",
                        "format": r"(?:as|in)\s+(pdf|docx|json|html)"
                    }
                }
            ],
            "CONFIGURE": [
                {
                    "patterns": [
                        r"(?:set|change|update|configure)\s+(.+)",
                        r"(?:turn\s+(?:on|off)|enable|disable)\s+(.+)",
                        r"(?:my|user)\s+(?:settings|preferences|config)"
                    ]
                }
            ],
            "HELP": [
                {
                    "patterns": [
                        r"(?:help|what\s+can\s+you\s+do|commands|instructions)",
                        r"how\s+do\s+i\s+(.+)",
                        r"show\s+(?:me\s+)?(?:available\s+)?(?:commands|options|features)"
                    ]
                }
            ]
        }
    
    def parse_natural_language(self, user_input: str) -> Dict[str, Any]:
        """
        Convert natural language to structured intent
        
        Returns:
            {
                "intent": "AUDIT",
                "confidence": 0.95,
                "params": {...},
                "raw_input": "...",
                "suggested_response_style": "casual|professional|technical"
            }
        """
        user_input = user_input.strip()
        
        # Update memory and learn preferences
        self.memory.extract_preferences(user_input)
        
        # Try to match intent patterns
        best_match = None
        highest_confidence = 0.0
        
        for intent, pattern_groups in self.intent_patterns.items():
            for pattern_group in pattern_groups:
                for pattern in pattern_group["patterns"]:
                    match = re.search(pattern, user_input, re.IGNORECASE)
                    if match:
                        confidence = self._calculate_confidence(pattern, user_input)
                        if confidence > highest_confidence:
                            highest_confidence = confidence
                            params = self._extract_parameters(
                                user_input, 
                                pattern_group.get("param_extraction", {}),
                                match
                            )
                            best_match = {
                                "intent": intent,
                                "confidence": confidence,
                                "params": params,
                                "raw_input": user_input,
                                "suggested_response_style": self.memory.user_profile["interaction_style"]
                            }
        
        # If no pattern matched, use fallback classification
        if not best_match or highest_confidence < 0.5:
            return self._fallback_classification(user_input)
        
        return best_match
    
    def _extract_parameters(self, text: str, param_patterns: Dict, match) -> Dict[str, Any]:
        """Extract structured parameters from natural language"""
        params = {}
        
        # Try to extract from pattern groups
        if match.groups():
            params["target"] = match.group(1).strip()
        
        # Try specific parameter patterns
        for param_name, pattern in param_patterns.items():
            param_match = re.search(pattern, text, re.IGNORECASE)
            if param_match:
                params[param_name] = param_match.group(1).strip()
        
        # Smart defaults
        if "summary" not in params and "target" in params:
            params["summary"] = f"Analysis of {params['target']}"
        
        return params
    
    def _calculate_confidence(self, pattern: str, text: str) -> float:
        """Calculate confidence score for pattern match"""
        # Base confidence from pattern match
        base_confidence = 0.7
        
        # Boost if entire sentence matches
        if re.fullmatch(pattern, text, re.IGNORECASE):
            base_confidence += 0.2
        
        # Boost for longer, more specific patterns
        if len(pattern) > 50:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _fallback_classification(self, text: str) -> Dict[str, Any]:
        """Classify intent using keyword analysis when patterns fail"""
        text_lower = text.lower()
        
        # Keyword-based classification
        keyword_map = {
            "AUDIT": ["audit", "check", "verify", "analyze", "inspect", "validate"],
            "PULSE": ["search", "find", "lookup", "info", "web", "latest", "news"],
            "STATUS": ["status", "health", "alive", "working", "online", "how are"],
            "REPORT": ["report", "summary", "overview", "document", "export"],
            "HELP": ["help", "how", "what can", "commands", "guide"]
        }
        
        scores = {}
        for intent, keywords in keyword_map.items():
            scores[intent] = sum(1 for kw in keywords if kw in text_lower)
        
        best_intent = max(scores, key=scores.get) if max(scores.values()) > 0 else "CHAT"
        
        return {
            "intent": best_intent,
            "confidence": 0.4,  # Low confidence fallback
            "params": {"query": text},
            "raw_input": text,
            "suggested_response_style": self.memory.user_profile["interaction_style"]
        }
    
    def get_conversational_response(self, intent_result: Dict) -> str:
        """Generate human-friendly acknowledgment based on intent"""
        intent = intent_result["intent"]
        style = intent_result.get("suggested_response_style", "professional")
        params = intent_result["params"]
        
        responses = {
            "casual": {
                "AUDIT": f"Got it! Running audit on {params.get('target', 'system')}...",
                "PULSE": f"Looking that up for you...",
                "STATUS": "Everything's running smooth! 🟢",
                "REPORT": "Generating that report now...",
                "HELP": "Here's what I can help with:",
                "CHAT": "I'm listening! What's up?"
            },
            "professional": {
                "AUDIT": f"Initiating comprehensive audit: {params.get('summary', 'System Analysis')}",
                "PULSE": f"Executing web intelligence scan: {params.get('topic', 'query')}",
                "STATUS": "System Status: All subsystems operational.",
                "REPORT": f"Compiling {params.get('format', 'standard')} report...",
                "HELP": "Available commands and capabilities:",
                "CHAT": "How may I assist you?"
            },
            "technical": {
                "AUDIT": f"EXEC: Reality.Audit({params.get('target', 'NULL')})",
                "PULSE": f"CALL: WebIntelligence.Pulse(topic={params.get('topic')})",
                "STATUS": "SYS_CHECK: 0x00 [ALL_GREEN]",
                "REPORT": f"COMPILE: Report.Generate(format={params.get('format', 'json')})",
                "HELP": "System Capabilities Index:",
                "CHAT": "STDIN_READY>"
            }
        }
        
        return responses.get(style, responses["professional"]).get(intent, "Processing...")


# Singleton instance
_neural_router = None

def get_neural_router() -> NeuralRouter:
    """Get or create the neural router singleton"""
    global _neural_router
    if _neural_router is None:
        _neural_router = NeuralRouter()
    return _neural_router
