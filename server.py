#!/usr/bin/env python3
"""
Inverion Semantic Bridge — The Sovereign Scrubber

Local-to-Arc Pipeline:
1. Ingests GDELT/RSS publication streams
2. Geocodes location strings via GeoPy
3. Calculates Veracity Scores via SemanticScrubber
4. Pushes Sunrise-encoded markers to WordPress/MapPress

Usage:
    python3 server.py --stream --wp-site https://kylosarc.com --wp-user admin
    python3 server.py --gdelt "climate change"
    python3 server.py --rss https://example.com/feed.xml

The server outputs JSON telemetry to stdout for stitching with the frontend.
"""

import sys
import json
import time
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

FEEDPARSER_AVAILABLE = False

def load_env_file(env_path: str = ".env") -> None:
    """Load environment variables from .env file if it exists."""
    path = Path(env_path)
    if not path.exists():
        return
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            line = line.lstrip('export ').strip()
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value

# Logic Constants: The Inverion Thresholds
VERACITY_CONSTANT = 1.0
BYPASS_THRESHOLD = 0.5
LOCKOUT_THRESHOLD = 0.1
SHUTDOWN_THRESHOLD = 0.0


class SunriseColor(Enum):
    """Sunrise spectrum colors for map markers."""
    IGNITION = "#FFFFFF"       # Veracity > 0.8 - High Veracity / Objective
    MORNING = "#FFB300"       # Veracity 0.5-0.8 - Morning Amber
    SUNSET = "#FF8F00"         # Veracity 0.3-0.5 - Distorted
    CRIMSON = "#B71C1C"       # Veracity < 0.3 - Structural Collapse


@dataclass
class FallacyTelemetry:
    """Represents a detected fallacy as telemetry for the manifold."""
    type: str
    magnitude: float
    persistence: float
    coord: List[float]  # [x, y, z] spatial position
    depth: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass  
class VeracityState:
    """Current veracity state of the analysis."""
    V_active: float
    V_initial: float
    ticks: int
    bypass_count: int
    inverion_triggered: bool
    root_fallacy_id: Optional[str]
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PublicationMarker:
    """
    A Sunrise-encoded publication marker for MapPress.
    
    Contains all data needed for WordPress/MapPress injection.
    """
    id: str
    title: str
    headline: str
    source_url: str
    source_name: str
    lat: Optional[float]
    lon: Optional[float]
    veracity_score: float
    fallacy_types: List[str]
    published_at: str
    color: str = "#FFFFFF"
    
    def __post_init__(self):
        self.id = hashlib.md5(self.headline.encode()).hexdigest()[:12]
        self.color = self._calculate_color()
    
    def _calculate_color(self) -> str:
        """Calculate Sunrise color based on veracity score."""
        if self.veracity_score > 0.8:
            return SunriseColor.IGNITION.value
        elif self.veracity_score > 0.5:
            return SunriseColor.MORNING.value
        elif self.veracity_score > 0.3:
            return SunriseColor.SUNSET.value
        else:
            return SunriseColor.CRIMSON.value
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_wp_rest_payload(self) -> dict:
        """Convert to WordPress REST API payload for MapPress."""
        return {
            "title": self.headline[:200],
            "content": f"Veracity: {self.veracity_score:.2f}\nFallacies: {', '.join(self.fallacy_types)}\nSource: {self.source_url}",
            "status": "publish",
            "meta": {
                "mappress_veracity_score": self.veracity_score,
                "mappress_color": self.color,
                "mappress_lat": self.lat or 0.0,
                "mappress_lng": self.lon or 0.0,
                "mappress_fallacy_types": ",".join(self.fallacy_types),
                "mappress_source": self.source_name,
            }
        }
    
    def to_manifold_jump(self) -> dict:
        """Data for syncing to 3D manifold when marker is clicked."""
        return {
            "id": self.id,
            "headline": self.headline,
            "veracity_score": self.veracity_score,
            "fallacy_types": self.fallacy_types,
            "position": [self.lon or 0, 0, self.lat or 0] if self.lat else [0, 0, 0],
            "color": self.color
        }


class SemanticScrubber:
    """
    Simulated LLM-Bridge / Regex Scrubber.
    
    Patterns based on Wikipedia's List of Fallacies + real examples from:
    - https://en.wikipedia.org/wiki/List_of_fallacies
    - https://github.com/tmakesense/logical-fallacy (400+ labeled examples)
    
    Each pattern maps a regex to a fallacy type with magnitude and persistence scores.
    """
    
    FALLACY_PATTERNS = [
        # ===== FAULTY GENERALIZATION / HASTY GENERALIZATION =====
        # Based on real examples: "All women are bad drivers", "All Germans are thieves", etc.
        {"pattern": r"\ball\s+(women|men|people|children|teenagers|students|teachers|parents)\s+(are|is)\b", 
         "type": "hasty_generalization", "magnitude": 0.7, "persistence": 0.65},
        {"pattern": r"\b(every|all|everyone|no one|nobody)\s+(does|is|are|were|said|knows?)\b", 
         "type": "hasty_generalization", "magnitude": 0.65, "persistence": 0.6},
        {"pattern": r"\b(all|every|any)\s+\w+\s+(are|is|does|can)\b", 
         "type": "hasty_generalization", "magnitude": 0.6, "persistence": 0.55},
        {"pattern": r"\bI\s+(met|saw|know|experienced?|talked\s+to)\s+(one|two|a\s+few|some)\b.*\b(now\s+I\s+believe|so\s+|therefore)\b",
         "type": "hasty_generalization", "magnitude": 0.65, "persistence": 0.6},
        {"pattern": r"\b(since|because)\s+.*\b(all|every)\b.*\btherefore\b", 
         "type": "hasty_generalization", "magnitude": 0.7, "persistence": 0.65},
        {"pattern": r"\bcan'?t?\s+(trust|believe|accept)\s+.*\s+(all|because\s+all|since\s+all)\b",
         "type": "hasty_generalization", "magnitude": 0.6, "persistence": 0.55},
        
        # ===== FALSE CAUSALITY / POST HOC =====
        # Based on real examples: "Every time I go to sleep the sun goes down", "I ate Oreos and got sick"
        {"pattern": r"\b(every\s+time|every\s+time\s+I)\b.*\b(then|therefore|so\s+)\b.*\b(causes?|led\s+to|resulted\s+in)\b",
         "type": "post_hoc", "magnitude": 0.7, "persistence": 0.65},
        {"pattern": r"\b(I\s+ate|after\s+I\s+)\b.*\b(then\s+I\s+was|next\s+day|after\s+that)\b.*\b(sick|ill|got\s+hurt|broke)\b",
         "type": "post_hoc", "magnitude": 0.65, "persistence": 0.6},
        {"pattern": r"\b(since|because|after)\s+.*\b(caused?|led\s+to|resulted\s+in|brought\s+about)\b",
         "type": "false_cause", "magnitude": 0.6, "persistence": 0.55},
        {"pattern": r"\b(correlation|linked|connected|related)\s+(to|with)\b.*\b(therefore|so|proves?|means)\b",
         "type": "false_cause", "magnitude": 0.55, "persistence": 0.5},
        {"pattern": r"\b(the\s+rooster|every\s+time)\b.*\b(causes?|before)\b",
         "type": "post_hoc", "magnitude": 0.75, "persistence": 0.7},
        
        # ===== CIRCULAR REASONING =====
        # Based on real examples: "God exists because Bible says so", "We know he's not lying since he says he's telling truth"
        {"pattern": r"\bbecause\s+(the\s+)?Bible\s+says\s+so\b", "type": "circular_reasoning", "magnitude": 0.85, "persistence": 0.8},
        {"pattern": r"\b(because|since)\s+it\s+(says?|tells?|states?)\s+(so|it's\s+true|the\s+truth)\b",
         "type": "circular_reasoning", "magnitude": 0.75, "persistence": 0.7},
        {"pattern": r"\bwe\s+know\s+(he|she|they)\s+(is|are)\s+(not\s+)?lying\s+because\s+(he|she|they)\s+says?\s+(so|truth)\b",
         "type": "circular_reasoning", "magnitude": 0.8, "persistence": 0.75},
        {"pattern": r"\b(it'?s?\s+true\s+)?because\s+it'?s?\s+(true|real|right)\b", "type": "circular_reasoning", "magnitude": 0.8, "persistence": 0.75},
        {"pattern": r"\byou\s+must\s+obey\s+the\s+law\s+because\s+(it'?s?\s+)?illegal\s+to\s+break\s+it\b",
         "type": "circular_reasoning", "magnitude": 0.75, "persistence": 0.7},
        {"pattern": r"\b(better|best|greatest)\s+than\s+(any|other|all)\b.*\b(because|since)\b",
         "type": "circular_reasoning", "magnitude": 0.65, "persistence": 0.6},
        {"pattern": r"\b(you should|you need to)\s+accept\s+because\s+(it'?s?\s+)?obvious\b",
         "type": "begging_the_question", "magnitude": 0.7, "persistence": 0.65},
        
        # ===== AD POPULUM / APPEAL TO POPULARITY =====
        # Based on real examples: "Everyone is doing it", "95% of teachers do", "McDonald's 99 billion served"
        {"pattern": r"\b(everyone|everybody|all\s+the\s+(cool|kids|people))\s+(does|is|are|doing|said|wants)\s+(it|so|this|them)\b",
         "type": "bandwagon", "magnitude": 0.55, "persistence": 0.5},
        {"pattern": r"\b(you\s+should\s+too|so\s+should\s+you|be\s+part\s+of)\b.*\b(everyone|majority|millions|crowd)\b",
         "type": "bandwagon", "magnitude": 0.5, "persistence": 0.45},
        {"pattern": r"\b\d+%\s+(of\s+)?(all\s+)?(people|everyone|surveyed|teachers?|doctors?)\b.*\b(so|therefore|must)\b",
         "type": "bandwagon", "magnitude": 0.5, "persistence": 0.45},
        {"pattern": r"\b(over\s+)?\d+\s+(billion|million|thousand)\s+(served|sold|used)\b",
         "type": "bandwagon", "magnitude": 0.4, "persistence": 0.35},
        {"pattern": r"\b(everyone\s+should|everyone\s+wants?|everyone\s+loves?)\b", "type": "bandwagon", "magnitude": 0.45, "persistence": 0.4},
        
        # ===== AD HOMINEM =====
        # Based on real examples: "Look at that face", "He's just a dumb actor", "How can you trust someone who wears bow ties"
        {"pattern": r"\b(just|a\s+dumb?|an?\s+(idiot|stupid|dumb))\b.*\b(actor|doctor|lawyer|expert)\b.*\b(what\s+(does|can)|so\s+)", 
         "type": "ad_hominem", "magnitude": 0.7, "persistence": 0.65},
        {"pattern": r"\blook\s+at\s+(that\s+)?(face|person|man|woman)\b.*\b(vote|trust|believe|support)\b",
         "type": "ad_hominem", "magnitude": 0.75, "persistence": 0.7},
        {"pattern": r"\b(how\s+(can|could)\s+you\s+(trust|believe|listen\s+to))\b.*\b(who|that|someone)\b.*\b(wears?|doesn)", 
         "type": "ad_hominem", "magnitude": 0.65, "persistence": 0.6},
        {"pattern": r"\b(you|he|she|they)\s+(never\s+)?(finished|graduated|went\s+to)\b.*\b(so\s+why|therefore)\b.*\b(trust|believe|listen)\b",
         "type": "ad_hominem", "magnitude": 0.65, "persistence": 0.6},
        {"pattern": r"\b(Don'?t?|Don'?t\s+listen\s+to)\b.*\b(because\s+(he|she|they)|how\s+can\s+)\b",
         "type": "ad_hominem", "magnitude": 0.6, "persistence": 0.55},
        {"pattern": r"\b(stupid|dumb|idiot|liar|criminal|corrupt)\b.*\b(so\s+why|therefore|can'?t?)\b",
         "type": "ad_hominem", "magnitude": 0.7, "persistence": 0.65},
        
        # ===== APPEAL TO EMOTION =====
        # Based on real examples: "Don't you want the best for your baby", "Grandma worked so hard on it"
        {"pattern": r"\b(don'?t\s+you\s+want|want\s+the\s+best\s+for)\b.*\b(baby|child|kids?|family|loved\s+one)\b",
         "type": "appeal_to_emotion", "magnitude": 0.6, "persistence": 0.55},
        {"pattern": r"\b(grandma|grandfather|mother|father|parent)\s+(worked\s+so\s+hard|made|tried)\b.*\b(it|this|the)\b",
         "type": "appeal_to_pity", "magnitude": 0.55, "persistence": 0.5},
        {"pattern": r"\b(if\s+we\s+don'?t?\s+|unless\s+)\b.*\b(could\s+put\s+down|will\s+(die|suffer|get\s+hurt|be\s+harmed))\b",
         "type": "appeal_to_fear", "magnitude": 0.65, "persistence": 0.6},
        {"pattern": r"\b(do\s+you\s+want\s+to\s+be\s+responsible|You\s+can'?t?\s+let\s+this\s+happen)\b",
         "type": "appeal_to_fear", "magnitude": 0.6, "persistence": 0.55},
        {"pattern": r"\b(we\s+the\s+people|justice|unity|integrity)\b.*\b(work\s+together|fight\s+for|protect)\b",
         "type": "appeal_to_emotion", "magnitude": 0.5, "persistence": 0.45},
        
        # ===== FALSE DICHOTOMY / FALSE DILEMMA =====
        # Based on real examples: "Either you're with us or against us"
        {"pattern": r"\b(either\s+you('?re| are)|either\s+we('?re| are)|either\s+)\b.*\b(or\s+you('?re| are)|or\s+we('?re| are)|or\s+)\b",
         "type": "false_dilemma", "magnitude": 0.7, "persistence": 0.65},
        {"pattern": r"\b(only\s+two|just\s+two|one\s+or\s+the\s+other)\b.*\b(possible|options|choices|alternatives)\b",
         "type": "false_dilemma", "magnitude": 0.65, "persistence": 0.6},
        {"pattern": r"\byou('?re| are)\s+(either\s+)?(with\s+us|against\s+us|for\s+us)\b",
         "type": "false_dilemma", "magnitude": 0.7, "persistence": 0.65},
        
        # ===== SLIPPERY SLOPE =====
        # Based on real examples: "If I don't take AP class...I'll live in parents' basement forever"
        {"pattern": r"\bif\s+(we\s+don'?t?|I\s+don'?t?|you\s+don'?t?)\b.*\bthen\s+(eventually|soon|next\s+thing)\b",
         "type": "slippery_slope", "magnitude": 0.7, "persistence": 0.65},
        {"pattern": r"\b(if\s+.*\s+then\s+.*\s+then\s+.*\s+then\s+.*\s+then\s+.*)\b", "type": "slippery_slope", "magnitude": 0.75, "persistence": 0.7},
        {"pattern": r"\b(the\s+next\s+thing\s+(we\s+know|you\s+know)|the\s+next\s+thing\s+we\s+know)\b",
         "type": "slippery_slope", "magnitude": 0.6, "persistence": 0.55},
        {"pattern": r"\b(can'?t?\s+freeze|won'?t?\s+stop|cannot\s+allow)\b.*\b(next\s+(thing|step)|soon|eventually)\b",
         "type": "slippery_slope", "magnitude": 0.65, "persistence": 0.6},
        
        # ===== FALSE AUTHORITY =====
        # Based on real examples: "Leonardo DiCaprio is just a dumb actor...what does he really know"
        {"pattern": r"\b(he'?s?\s+just|a\s+)?(dumb|stupid|just\s+an?)\s+(actor|actress|celebrity|celeb)\b.*\b(what\s+(does|can)|knows?\s+nothing)\b",
         "type": "false_authority", "magnitude": 0.65, "persistence": 0.6},
        {"pattern": r"\b(according\s+to|as\s+(one|a)\s+)\b.*\b(says|told|believes?)\s+(so|it'?s?\s+true)\b",
         "type": "false_authority", "magnitude": 0.5, "persistence": 0.45},
        {"pattern": r"\b(a\s+)?(famous|well-known|renowned|celebrity)\s+(expert|authority|scientist|actress|actor)\b",
         "type": "false_authority", "magnitude": 0.5, "persistence": 0.45},
        
        # ===== STRAWMAN =====
        # Based on: misrepresenting someone's position
        {"pattern": r"\b(says?|claims?|thinks?)\s+(that\s+)?(all|every|everyone|nobody)\b.*\b(so\s+(he|she|they)|therefore|which\s+means)\b",
         "type": "strawman", "magnitude": 0.6, "persistence": 0.55},
        {"pattern": r"\bdoesn't\s+(actually|really|truly)\s+(believe|think|mean)\b",
         "type": "strawman", "magnitude": 0.55, "persistence": 0.5},
        
        # ===== BEGGING THE QUESTION =====
        {"pattern": r"\b(obviously|certainly|clearly|everyone\s+knows)\b.*\b(so|therefore|thus)\b",
         "type": "begging_the_question", "magnitude": 0.7, "persistence": 0.65},
        {"pattern": r"\bit'?s?\s+(obvious|clear|certain|evident)\s+because\s+(it)?'?s?\s+(true|real|obvious)\b",
         "type": "begging_the_question", "magnitude": 0.7, "persistence": 0.65},
        
        # ===== RED HERRING =====
        {"pattern": r"\byes\s+but\s+what\s+about\b", "type": "red_herring", "magnitude": 0.55, "persistence": 0.5},
        {"pattern": r"\b(nevermind|anyway|side\s+note|by\s+the\s+way)\b.*\b(let'?s?\s+look|consider|focus)\b",
         "type": "red_herring", "magnitude": 0.5, "persistence": 0.45},
        
        # ===== FALSE ANALOGY =====
        # Based on: "The mind is like a knife"
        {"pattern": r"\b(is\s+like|a\s+lot\s+like|similar\s+to|just\s+like)\b.*\b(can\s+should|must|will|would)\b",
         "type": "false_analogy", "magnitude": 0.55, "persistence": 0.5},
        {"pattern": r"\bif\s+.*\s+(works?|helps?|functions?)\s+(for|in|with)\b.*\bthen\s+.*\s+(can|must|should)\s+(for|in|with)\b",
         "type": "false_analogy", "magnitude": 0.55, "persistence": 0.5},
        
        # ===== COMPOSITION / DIVISION =====
        {"pattern": r"\b(all|every|each)\s+(part|member|piece)\b.*\b(therefore|so|thus)\b.*\b(whole|entire|all)\b",
         "type": "composition_division", "magnitude": 0.55, "persistence": 0.5},
        {"pattern": r"\b(the\s+whole|entire)\b.*\b(must|will|should)\b.*\b(every|all|each)\b",
         "type": "composition_division", "magnitude": 0.55, "persistence": 0.5},
        
        # ===== AFFIRMING THE CONSEQUENT =====
        {"pattern": r"\bif\s+(.+)\s+then\s+(.+)\b.*\b\2\b.*\btherefore|\1\b", "type": "affirming_consequent", "magnitude": 0.7, "persistence": 0.65},
        
        # ===== DENYING THE ANTECEDENT =====
        {"pattern": r"\b(not\s+A|because\s+not\s+A)\b.*\b(therefore|so)\b.*\b(not\s+B|then\s+not\s+B)\b",
         "type": "denying_antecedent", "magnitude": 0.65, "persistence": 0.6},
        
        # ===== NON-SEQUITUR =====
        {"pattern": r"\b(all\s+men\s+are\s+mortal.*Socrates\s+is\s+a\s+man)\b", "type": "non_sequitur", "magnitude": 0.7, "persistence": 0.65},
        {"pattern": r"\b(we\s+should\s+stop\s+using|ban)\b.*\b(because\s+it\s+is\s+snowing|so\s+)\b",
         "type": "non_sequitur", "magnitude": 0.75, "persistence": 0.7},
        
        # ===== GAMBLER'S FALLACY =====
        {"pattern": r"\b(due|overdue|has\s+to\s+hit|has\s+to\s+come|it's\s+time\s+for)\b",
         "type": "gamblers_fallacy", "magnitude": 0.55, "persistence": 0.5},
        
        # ===== SUNK COST =====
        {"pattern": r"\b(we'?ve?|I'?ve?|they'?ve?)\s+(already|spent|invested)\b.*\b(might\s+as\s+well|should|have\s+to)\b",
         "type": "sunk_cost_fallacy", "magnitude": 0.6, "persistence": 0.55},
        
        # ===== NOVELTY / TRADITION =====
        {"pattern": r"\b(newest?|latest|cutting-edge|modern)\s+(so\s+)?(it's\s+)?(better|superior|improved)\b",
         "type": "appeal_to_novelty", "magnitude": 0.5, "persistence": 0.45},
        {"pattern": r"\b(we'?ve?\s+always|traditionally|historically)\s+(done?|been|said)\b",
         "type": "appeal_to_tradition", "magnitude": 0.5, "persistence": 0.45},
        
        # ===== MIDDLE GROUND =====
        {"pattern": r"\b(balance|compromise|middle\s+ground|halfway)\s+(is\s+)?(always\s+)?(best|correct|right)\b",
         "type": "middle_ground", "magnitude": 0.45, "persistence": 0.4},
        
        # ===== SPECIAL PLEADING =====
        {"pattern": r"\b(this\s+is\s+an?\s+)?exception\b.*\b(deserves?|justifies?|warrants?)\b",
         "type": "special_pleading", "magnitude": 0.55, "persistence": 0.5},
        
        # ===== APPEAL TO NATURE =====
        {"pattern": r"\b(natural|organic|all-natural)\s+(is\s+)?(better|good|healthy|safer)\b",
         "type": "appeal_to_nature", "magnitude": 0.5, "persistence": 0.45},
        
        # ===== LOADED QUESTION =====
        {"pattern": r"\b(have\s+you\s+stopped|have\s+you\s+been|are\s+you\s+still)\b.*\b(cheating|lying|cutting|doing)\b",
         "type": "loaded_question", "magnitude": 0.7, "persistence": 0.65},
        
        # ===== TU QUOQUE =====
        {"pattern": r"\b(you|they|he|she)\s+(do|does|is|are)\s+(it|so|same|too)\b.*\b(so|therefore|which\s+proves)\b",
         "type": "tu_quoque", "magnitude": 0.55, "persistence": 0.5},
        {"pattern": r"\bwhat\s+about\s+(your|their|his|her)\s+(own|corruption|failure)\b",
         "type": "tu_quoque", "magnitude": 0.5, "persistence": 0.45},
        
        # ===== IGNORATIO ELENCHI =====
        {"pattern": r"\b(what\s+this\s+means?\s+is|basically|the\s+point\s+is)\b",
         "type": "ignoratio_elenchi", "magnitude": 0.5, "persistence": 0.45},
        
        # ===== THOUGHT-TERMINATING CLICHÉ =====
        {"pattern": r"\b(at\s+the\s+end\s+of\s+the\s+day|it\s+is\s+what\s+it\s+is|time\s+will\s+tell)\b",
         "type": "thought_terminating_cliche", "magnitude": 0.35, "persistence": 0.3},
        
        # ===== PROSECUTOR'S FALLACY =====
        {"pattern": r"\b(one\s+in\s+a\s+million|low\s+probability|rare\s+chance)\b.*\b(must\s+be|therefore|so\s+it\s+is)\b",
         "type": "prosecutors_fallacy", "magnitude": 0.55, "persistence": 0.5},
        
        # ===== MOVING THE GOALPOSTS =====
        {"pattern": r"\b(that'?s?\s+not\s+enough|you\s+need\s+more|this\s+doesn'?t?\s+count)\b.*\b(prove|demonstrate|show)\b",
         "type": "moving_goalposts", "magnitude": 0.65, "persistence": 0.6},
        
        # ===== EQUIVOCATION =====
        {"pattern": r"\b(depends?\s+on\s+(how\s+)?what\s+(you\s+)?mean\s+by|your\s+definition\s+of)\b",
         "type": "equivocation", "magnitude": 0.5, "persistence": 0.45},
        
        # ===== GENETIC FALLACY =====
        {"pattern": r"\b(comes?\s+from|stems?\s+from|originated?|traced?\s+to)\b.*\b(bad|flawed|biased|discredited)\b",
         "type": "genetic_fallacy", "magnitude": 0.5, "persistence": 0.45},
        
        # ===== APPEAL TO SILENCE =====
        {"pattern": r"\b(no\s+evidence|absence\s+of\s+proof|nobody\s+has\s+shown|there'?s?\s+no\s+proof)\b.*\b(true|real|actual)\b",
         "type": "appeal_to_silence", "magnitude": 0.5, "persistence": 0.45},
    ]
    
    FALLACY_TEMPLATES = [
        # "All X are Y" - Hasty Generalization
        {"template": r"\ball\s+\w+\s+are\s+\w+", "type": "hasty_generalization", "magnitude": 0.7, "persistence": 0.65},
        {"template": r"\ball\s+\w+\s+is\s+\w+", "type": "hasty_generalization", "magnitude": 0.7, "persistence": 0.65},
        # "Everyone X" / "Nobody X" - Universal Quantifier
        {"template": r"\beveryone\s+\w+", "type": "hasty_generalization", "magnitude": 0.65, "persistence": 0.6},
        {"template": r"\bnobody\s+\w+", "type": "hasty_generalization", "magnitude": 0.65, "persistence": 0.6},
        # "Either X or Y" - False Dilemma
        {"template": r"\beither\s+\w+\s+or\s+\w+", "type": "false_dilemma", "magnitude": 0.7, "persistence": 0.65},
        # "If X then Y" chains - Slippery Slope
        {"template": r"\bif\s+\w+.*\bthen\s+\w+.*\b(if|then|eventually|soon)\b", "type": "slippery_slope", "magnitude": 0.75, "persistence": 0.7},
        # "I met one X who Y, so all X are Y" - Anecdotal Generalization
        {"template": r"\bi\s+met\s+\w+\s+who\s+.*\bso\s+all\s+\w+\s+are\s+\w+", "type": "hasty_generalization", "magnitude": 0.75, "persistence": 0.7},
        # "X because Y because X" - Circular
        {"template": r"\b\w+\s+because\s+.*\s+because\s+", "type": "circular_reasoning", "magnitude": 0.8, "persistence": 0.75},
        # "Everyone knows X so Y" - Begging the Question
        {"template": r"\beveryone\s+(knows?|believes?|agrees?)\s+", "type": "begging_the_question", "magnitude": 0.6, "persistence": 0.55},
        # "You shouldn't X because Y" where Y is same as X - Tu Quoque
        {"template": r"\byou\s+(shouldn'?t?|can'?t?|don'?t?)\s+\w+\s+because\s+", "type": "tu_quoque", "magnitude": 0.6, "persistence": 0.55},
    ]
    
    NGRAM_WEIGHTS = {
        ("all", "are"): 0.8, ("all", "is"): 0.8,
        ("if", "then"): 0.7, ("either", "or"): 0.75,
        ("because", "therefore"): 0.85, ("since", "therefore"): 0.8,
        ("every", "time"): 0.7, ("after", "therefore"): 0.75,
        ("everyone", "should"): 0.65, ("nobody", "should"): 0.65,
        ("you", "should"): 0.5, ("I", "believe"): 0.45,
        ("it", "is", "true"): 0.6, ("obviously", "therefore"): 0.7,
        ("clearly", "therefore"): 0.7, ("therefore", "all"): 0.75,
        ("then", "eventually"): 0.6, ("next", "thing"): 0.55,
    }
    
    QUANTIFIER_COMBOS = [
        (r"\b(all|every|everyone|nobody)\b", r"\b(should|must|are|is|will)\b", "hasty_generalization", 0.75),
        (r"\b(always|never)\b", r"\b(because|therefore|so)\b", "hasty_generalization", 0.7),
        (r"\b(all|every)\b", r"\b(cannot|can'?t)\b", "hasty_generalization", 0.7),
    ]
    
    SENTIMENT_EXTREMITY_WEIGHTS = {
        "fear": 0.7, "afraid": 0.7, "terrible": 0.8, "horrible": 0.8,
        "destroy": 0.85, "kill": 0.85, "die": 0.8, "dead": 0.75,
        "love": 0.5, "best": 0.5, "great": 0.5, "wonderful": 0.6,
        "hope": 0.4, "dream": 0.4, "peace": 0.3, "justice": 0.4,
    }
    
    DISCOURSE_MARKERS = {
        "but": 0.2, "however": 0.3, "although": 0.25, "yet": 0.2,
        "on the other hand": 0.35, "that said": 0.3, "still": 0.15,
    }
    
    def __init__(self):
        self._temporal_index = 0
    
    def _check_templates(self, text: str) -> List[FallacyTelemetry]:
        """Check text against sentence templates."""
        import re
        fallacies = []
        text_lower = text.lower()
        
        for tmpl in self.FALLACY_TEMPLATES:
            if re.search(tmpl["template"], text_lower):
                fallacies.append(FallacyTelemetry(
                    type=tmpl["type"],
                    magnitude=tmpl["magnitude"],
                    persistence=tmpl["persistence"],
                    coord=[self._temporal_index * 2.0, tmpl["magnitude"] * 2.0, -tmpl["magnitude"] * 3.0],
                    depth=1
                ))
                self._temporal_index += 1
        
        return fallacies
    
    def _check_ngrams(self, text: str) -> List[FallacyTelemetry]:
        """Check for high-weight ngram sequences."""
        import re
        fallacies = []
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        for i in range(len(words) - 1):
            bigram = (words[i], words[i + 1])
            if bigram in self.NGRAM_WEIGHTS:
                weight = self.NGRAM_WEIGHTS[bigram]
                fallacies.append(FallacyTelemetry(
                    type=self._infer_fallacy_type(bigram),
                    magnitude=weight,
                    persistence=weight * 0.9,
                    coord=[self._temporal_index * 2.0, weight * 2.0, -weight * 3.0],
                    depth=2
                ))
                self._temporal_index += 1
        
        for i in range(len(words) - 2):
            trigram = (words[i], words[i + 1], words[i + 2])
            trigram_str = " ".join(trigram)
            for key_ngram, weight in self.NGRAM_WEIGHTS.items():
                if isinstance(key_ngram, tuple) and len(key_ngram) == 2:
                    bigram_str = " ".join(key_ngram)
                    if bigram_str in trigram_str:
                        fallacies.append(FallacyTelemetry(
                            type="causal_chain",
                            magnitude=weight * 1.1,
                            persistence=weight,
                            coord=[self._temporal_index * 2.0, weight * 2.0, -weight * 3.0],
                            depth=2
                        ))
                        self._temporal_index += 1
                        break
        
        return fallacies
    
    def _check_quantifier_combos(self, text: str) -> List[FallacyTelemetry]:
        """Check for dangerous quantifier + modal combinations."""
        import re
        fallacies = []
        text_lower = text.lower()
        
        for quant_pat, modal_pat, fallacy_type, weight in self.QUANTIFIER_COMBOS:
            quant_match = re.search(quant_pat, text_lower)
            modal_match = re.search(modal_pat, text_lower)
            if quant_match and modal_match:
                if modal_match.start() > quant_match.start():
                    fallacies.append(FallacyTelemetry(
                        type=fallacy_type,
                        magnitude=weight,
                        persistence=weight * 0.9,
                        coord=[self._temporal_index * 2.0, weight * 2.0, -weight * 3.0],
                        depth=3
                    ))
                    self._temporal_index += 1
        
        return fallacies
    
    def _check_sentiment_extremity(self, text: str) -> List[FallacyTelemetry]:
        """Check for extreme sentiment combined with universal quantifiers."""
        import re
        fallacies = []
        text_lower = text.lower()
        
        has_extreme_sentiment = any(re.search(pat, text_lower) for pat in self.SENTIMENT_EXTREMITY_WEIGHTS.keys())
        has_quantifier = re.search(r"\b(all|every|everyone|nobody|always|never)\b", text_lower)
        
        if has_extreme_sentiment and has_quantifier:
            if isinstance(has_extreme_sentiment, bool):
                avg_sentiment = 0.6
            else:
                match_val = has_extreme_sentiment.group() if hasattr(has_extreme_sentiment, 'group') else list(self.SENTIMENT_EXTREMITY_WEIGHTS.keys())[0]
                avg_sentiment = self.SENTIMENT_EXTREMITY_WEIGHTS.get(match_val, 0.6)
            
            fallacies.append(FallacyTelemetry(
                type="appeal_to_emotion",
                magnitude=avg_sentiment,
                persistence=avg_sentiment * 0.9,
                coord=[self._temporal_index * 2.0, avg_sentiment * 2.0, -avg_sentiment * 3.0],
                depth=4
            ))
            self._temporal_index += 1
        
        return fallacies
    
    def _check_discourse_markers(self, text: str) -> List[FallacyTelemetry]:
        """Check for discourse markers indicating deflection."""
        import re
        fallacies = []
        text_lower = text.lower()
        
        for marker, weight in self.DISCOURSE_MARKERS.items():
            if marker in text_lower:
                pos = text_lower.index(marker)
                context_start = max(0, pos - 30)
                context = text_lower[context_start:pos + len(marker)]
                if re.search(r"\bbut\s+\w+\s+\w+\s+(should|must|need)\b", context) or \
                   re.search(r"\bhowever\s+.*\b(you|they|we)\b", context):
                    fallacies.append(FallacyTelemetry(
                        type="red_herring",
                        magnitude=weight,
                        persistence=weight * 0.9,
                        coord=[self._temporal_index * 2.0, weight * 2.0, -weight * 3.0],
                        depth=5
                    ))
                    self._temporal_index += 1
                    break
        
        return fallacies
    
    def _infer_fallacy_type(self, bigram: tuple) -> str:
        """Infer fallacy type from bigram context."""
        first, second = bigram
        if first in ("all", "every", "everyone", "nobody"):
            return "hasty_generalization"
        elif first in ("if", "when") and second == "then":
            return "conditional_reasoning"
        elif first == "because" or second == "therefore":
            return "causal_fallacy"
        elif first == "either" and second == "or":
            return "false_dilemma"
        else:
            return "general_fallacy"
    
    def analyze(self, raw_input: str) -> List[FallacyTelemetry]:
        """Analyze raw text and return fallacy telemetry using multiple detection layers."""
        import re
        
        fallacies = []
        input_lower = raw_input.lower()
        
        pattern_fallacies = self._check_patterns(input_lower)
        fallacies.extend(pattern_fallacies)
        
        template_fallacies = self._check_templates(raw_input)
        fallacies.extend(template_fallacies)
        
        ngram_fallacies = self._check_ngrams(raw_input)
        fallacies.extend(ngram_fallacies)
        
        quant_fallacies = self._check_quantifier_combos(raw_input)
        fallacies.extend(quant_fallacies)
        
        sentiment_fallacies = self._check_sentiment_extremity(raw_input)
        fallacies.extend(sentiment_fallacies)
        
        discourse_fallacies = self._check_discourse_markers(raw_input)
        fallacies.extend(discourse_fallacies)
        
        return fallacies
    
    def _check_patterns(self, text: str) -> List[FallacyTelemetry]:
        """Original regex pattern matching."""
        import re
        fallacies = []
        
        for fp in self.FALLACY_PATTERNS:
            if re.search(fp["pattern"], text, re.IGNORECASE):
                fallacies.append(FallacyTelemetry(
                    type=fp["type"],
                    magnitude=fp["magnitude"],
                    persistence=fp["persistence"],
                    coord=[self._temporal_index * 2.0, fp["magnitude"] * 2.0, -fp["magnitude"] * 3.0],
                    depth=0
                ))
                self._temporal_index += 1
        
        return fallacies
    
    def analyze_headline(self, headline: str) -> tuple[List[FallacyTelemetry], float]:
        """
        Analyze a headline and return fallacies plus veracity score.
        
        Returns (fallacies, veracity_score) where veracity_score is 1.0 minus decay.
        """
        fallacies = self.analyze(headline)
        
        # Calculate veracity decay
        total_cost = sum(f.magnitude * f.persistence for f in fallacies)
        veracity_score = max(0.0, VERACITY_CONSTANT - total_cost)
        
        return fallacies, veracity_score


class GeoTransformer:
    """
    Geographic Transformer for resolving location strings to coordinates.
    
    Uses GeoPy for geocoding with pattern-matching fallback.
    """
    
    US_STATES = {
        "AL": (32.3182, -86.9023), "AK": (61.2181, -149.9003), "AZ": (34.0489, -111.0937),
        "AR": (35.2010, -91.8318), "CA": (36.7783, -119.4179), "CO": (39.5501, -105.7821),
        "CT": (41.6032, -73.0877), "DE": (38.9108, -75.5277), "FL": (27.6648, -81.5158),
        "GA": (32.1574, -81.4250), "HI": (19.8968, -155.5828), "ID": (43.6151, -116.2023),
        "IL": (40.6331, -89.3985), "IN": (40.2672, -86.1349), "IA": (41.8780, -93.0977),
        "KS": (39.0119, -98.4842), "KY": (37.8392, -84.2700), "LA": (30.9843, -91.9623),
        "ME": (44.6938, -69.3819), "MD": (39.0458, -76.6413), "MA": (42.4072, -71.3824),
        "MI": (44.3148, -85.6024), "MN": (46.7296, -94.6859), "MS": (32.3546, -89.3985),
        "MO": (37.9642, -91.8318), "MT": (46.8797, -110.3626), "NE": (41.4925, -99.9018),
        "NV": (38.8026, -116.4194), "NH": (43.1939, -71.5724), "NJ": (40.0583, -74.4057),
        "NM": (34.8403, -106.2485), "NY": (43.2994, -74.2179), "NC": (35.7596, -79.0193),
        "ND": (47.5515, -101.0020), "OH": (40.4173, -82.9071), "OK": (35.0078, -97.0929),
        "OR": (43.8041, -120.5542), "PA": (41.2033, -77.1945), "RI": (41.5801, -71.4774),
        "SC": (33.8361, -81.1637), "SD": (43.9695, -99.9018), "TN": (35.5175, -86.5804),
        "TX": (31.9686, -99.9018), "UT": (39.3200, -111.0937), "VT": (44.5588, -72.5778),
        "VA": (37.4316, -78.6569), "WA": (47.7511, -120.7401), "WV": (38.5972, -80.4549),
        "WI": (43.7844, -88.7879), "WY": (43.0760, -107.2903),
    }
    
    def __init__(self, geopy_enabled: bool = True):
        self.geopy_enabled = geopy_enabled
        self._geocoder = None
        self._init_geopy()
        self._cache: Dict[str, Tuple[float, float]] = {}
    
    def _init_geopy(self) -> bool:
        """Initialize GeoPy geocoder."""
        self.geopy_enabled = False
        return False
    
    def geocode(self, location_str: str) -> tuple[Optional[float], Optional[float]]:
        """
        Geocode a location string to (lat, lon).
        
        Returns (None, None) if geocoding fails.
        """
        if not location_str:
            return None, None
        
        location_clean = location_str.strip()
        
        # Check cache first
        if location_clean in self._cache:
            return self._cache[location_clean]
        
        # Try GeoPy if enabled
        if self.geopy_enabled and self._geocoder:
            try:
                location = self._geocoder.geocode(location_clean, timeout=5)
                if location:
                    coords = (location.latitude, location.longitude)
                    self._cache[location_clean] = coords
                    return coords
            except Exception as e:
                print(f"Geocoding error for '{location_clean}': {e}", file=sys.stderr)
        
        # Fall back to pattern matching
        lat, lon = self._pattern_match(location_clean)
        if lat is not None and lon is not None:
            self._cache[location_clean] = (lat, lon)
        
        return lat, lon
    
    def _pattern_match(self, location_str: str) -> tuple[Optional[float], Optional[float]]:
        """Match location using pattern database."""
        loc_lower = location_str.lower()
        
        # Check for US state
        for abbrev, coords in self.US_STATES.items():
            if abbrev.lower() in loc_lower or f" {abbrev.lower()}" in loc_lower:
                return coords
        
        # Check for country names
        countries = {
            "france": (46.2276, 2.2137), "germany": (51.1657, 10.4515),
            "uk": (55.3781, -3.4360), "united kingdom": (55.3781, -3.4360),
            "canada": (56.1304, -106.3468), "australia": (-25.2744, 133.7751),
            "india": (20.5937, 78.9629), "brazil": (-14.2350, -51.9253),
            "china": (35.8617, 104.1954), "japan": (36.2048, 138.2529),
        }
        
        for country, coords in countries.items():
            if country in loc_lower:
                return coords
        
        return None, None


class GDELTConnector:
    """
    GDELT stream connector for real-time headline ingestion.
    """
    
    GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    def fetch(self, query: str, max_records: int = 50) -> List[Dict]:
        """Fetch headlines from GDELT."""
        params = {
            "query": query,
            "mode": "artimeline",
            "format": "json",
            "maxrecords": max_records
        }
        
        if self.api_key:
            params["key"] = self.api_key
        
        url = f"{self.GDELT_API}?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Inverion-Sovereignty-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                return data.get("articles", [])
        except Exception as e:
            print(f"GDELT fetch error: {e}", file=sys.stderr)
            return []
    
    def fetch_with_geocode(self, query: str, geo_transformer: GeoTransformer) -> List[PublicationMarker]:
        """Fetch GDELT headlines and geocode them."""
        articles = self.fetch(query)
        markers = []
        
        for article in articles:
            headline = article.get("title", "")
            source_url = article.get("url", "")
            source_name = article.get("domain", "")
            location_raw = source_name.split(".")[-1] if "." in source_name else ""
            
            # Analyze veracity
            scrubber = SemanticScrubber()
            fallacies, veracity_score = scrubber.analyze_headline(headline)
            fallacy_types = [f.type for f in fallacies]
            
            # Geocode location
            lat, lon = geo_transformer.geocode(location_raw)
            
            marker = PublicationMarker(
                id="",
                title=headline[:100],
                headline=headline,
                source_url=source_url,
                source_name=source_name,
                lat=lat,
                lon=lon,
                veracity_score=veracity_score,
                fallacy_types=fallacy_types,
                published_at=article.get("seendate", "")
            )
            markers.append(marker)
        
        return markers


class RSSConnector:
    """
    RSS feed connector for headline ingestion.
    """
    
    def fetch(self, feed_url: str) -> List[Dict]:
        """Fetch headlines from RSS feed using urllib."""
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Inverion-Sovereignty-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8', errors='ignore')
            
            entries = []
            import re
            item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL | re.IGNORECASE)
            title_pattern = re.compile(r'<title>(.*?)</title>', re.DOTALL | re.IGNORECASE)
            link_pattern = re.compile(r'<link>(.*?)</link>', re.DOTALL | re.IGNORECASE)
            
            for item in item_pattern.findall(content):
                title = title_pattern.search(item)
                link = link_pattern.search(item)
                
                entries.append({
                    "title": title.group(1) if title else "",
                    "link": link.group(1) if link else "",
                    "published": "",
                    "source": feed_url
                })
            
            return entries[:50]
        except Exception as e:
            print(f"RSS fetch error: {e}", file=sys.stderr)
            return []
    
    def fetch_with_geocode(self, feed_url: str, geo_transformer: GeoTransformer) -> List[PublicationMarker]:
        """Fetch RSS headlines and geocode them."""
        articles = self.fetch(feed_url)
        markers = []
        
        for article in articles:
            headline = article.get("title", "")
            source_url = article.get("link", "")
            source_name = article.get("source", "")
            
            # Analyze veracity
            scrubber = SemanticScrubber()
            fallacies, veracity_score = scrubber.analyze_headline(headline)
            fallacy_types = [f.type for f in fallacies]
            
            # Extract location from source or title
            location_hint = self._extract_location(article, headline)
            lat, lon = geo_transformer.geocode(location_hint) if location_hint else (None, None)
            
            marker = PublicationMarker(
                id="",
                title=headline[:100],
                headline=headline,
                source_url=source_url,
                source_name=source_name,
                lat=lat,
                lon=lon,
                veracity_score=veracity_score,
                fallacy_types=fallacy_types,
                published_at=article.get("published", "")
            )
            markers.append(marker)
        
        return markers
    
    def _extract_location(self, article: Dict, headline: str) -> str:
        """Extract location hint from article or headline."""
        # Try to find location patterns in title
        import re
        loc_pattern = r'\b([A-Z]{2})\b'
        matches = re.findall(loc_pattern, headline)
        if matches:
            return matches[0]
        return ""


class LocalLedgerConnector:
    """
    Local JSON file connector for zero-cost mock testing.
    Reads simulated event packets from a local ledger file.
    """
    
    def __init__(self, ledger_path: str = "mock_ledger.json"):
        self.ledger_path = ledger_path
        self._index = 0
    
    def _load_ledger(self) -> List[Dict]:
        """Load events from local ledger file."""
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("events", [])
        except Exception as e:
            print(f"[LocalLedger] Failed to load ledger: {e}", file=sys.stderr)
            return []
    
    def fetch(self) -> List[Dict]:
        """Fetch all events from local ledger."""
        return self._load_ledger()
    
    def fetch_with_geocode(self, geo_transformer: GeoTransformer) -> List[PublicationMarker]:
        """Fetch events from local ledger and geocode them."""
        events = self._load_ledger()
        markers = []
        
        for event in events:
            headline = event.get("title", "")
            source_url = event.get("source_url", "")
            source_name = event.get("source_name", "")
            raw_location = event.get("raw_location", "")
            veracity_score = event.get("veracity_score", 1.0)
            fallacy_types = event.get("fallacy_types", [])
            
            lat, lon = geo_transformer.geocode(raw_location)
            
            marker = PublicationMarker(
                id="",
                title=headline[:100],
                headline=headline,
                source_url=source_url,
                source_name=source_name,
                lat=lat,
                lon=lon,
                veracity_score=veracity_score,
                fallacy_types=fallacy_types,
                published_at=datetime.now().isoformat()
            )
            markers.append(marker)
        
        return markers
    
    def fetch_next(self, geo_transformer: GeoTransformer) -> Optional[PublicationMarker]:
        """Fetch next event in round-robin fashion from ledger."""
        events = self._load_ledger()
        if not events:
            return None
        
        event = events[self._index % len(events)]
        self._index += 1
        
        headline = event.get("title", "")
        source_url = event.get("source_url", "")
        source_name = event.get("source_name", "")
        raw_location = event.get("raw_location", "")
        veracity_score = event.get("veracity_score", 1.0)
        fallacy_types = event.get("fallacy_types", [])
        
        lat, lon = geo_transformer.geocode(raw_location)
        
        return PublicationMarker(
            id="",
            title=headline[:100],
            headline=headline,
            source_url=source_url,
            source_name=source_name,
            lat=lat,
            lon=lon,
            veracity_score=veracity_score,
            fallacy_types=fallacy_types,
            published_at=datetime.now().isoformat()
        )


class MapPressBridge:
    """
    MapPress REST API bridge for injecting markers into Map ID 2.
    
    Hardcoded for KylosArc.com Geographic Handshake.
    """
    
    MAP_ID = 2  # Hardcoded target map
    
    SUNRSE_ICON_MAP = {
        "#FFFFFF": 1,  # White-Hot (Ignition) - Veracity > 0.8
        "#FFB300": 2,  # Morning Amber - Veracity 0.4-0.7
        "#880E4F": 3,  # Shadow Crimson - Veracity < 0.3
        "#FF8F00": 4,  # Sunset Orange - Veracity 0.3-0.5
    }
    
    def __init__(self, site_url: str, username: str, password: str = ""):
        self.site_url = site_url.rstrip("/")
        self.username = username
        self.password = password
        self._markers_cache: List[PublicationMarker] = []
        self._archive_dir = "data/archive/shadow"
    
    def _get_auth_header(self) -> str:
        """Get base64 auth header for WordPress."""
        import base64
        auth = f"{self.username}:{self.password}"
        return base64.b64encode(auth.encode()).decode()
    
    def _get_icon_id(self, veracity_score: float) -> int:
        """Map veracity score to Sunrise icon ID."""
        if veracity_score > 0.8:
            return self.SUNRSE_ICON_MAP["#FFFFFF"]
        elif veracity_score > 0.5:
            return self.SUNRSE_ICON_MAP["#FFB300"]
        elif veracity_score > 0.3:
            return self.SUNRSE_ICON_MAP["#FF8F00"]
        else:
            return self.SUNRSE_ICON_MAP["#880E4F"]
    
    def post_marker(self, marker: PublicationMarker) -> Dict:
        """
        Post a single marker to MapPress Map ID 2.
        
        Tries multiple methods:
        1. MapPress REST API (if plugin installed)
        2. Generic WordPress post with MapPress metadata
        3. JWT authentication if configured
        """
        last_error = None
        
        for method in ["mappress_rest", "wp_post", "jwt_auth"]:
            result = None
            try:
                if method == "mappress_rest":
                    result = self._post_to_mappress_rest(marker)
                elif method == "wp_post":
                    result = self._post_as_wp_post(marker)
                elif method == "jwt_auth":
                    result = self._post_with_jwt(marker)
                
                if result and "error" not in result and result.get("id"):
                    print(f"[MapPress] Marker posted via {method}: {result.get('id')}", file=sys.stderr)
                    return result
            except Exception as e:
                last_error = str(e)
                print(f"[MapPress] {method} failed: {last_error[:100]}", file=sys.stderr)
                continue
        
        return {"error": f"All methods failed. Last error: {last_error}"}
    
    def _post_to_mappress_rest(self, marker: PublicationMarker) -> Dict:
        """Try MapPress REST API endpoint."""
        url = f"{self.site_url}/wp-json/wp/v2/mappress_marker"
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({
                    "mapid": self.MAP_ID,
                    "title": marker.headline[:200],
                    "lat": marker.lat or 0.0,
                    "lng": marker.lon or 0.0,
                    "content": f"Veracity Score: {marker.veracity_score:.2f} | Source: {marker.source_name}",
                    "iconid": self._get_icon_id(marker.veracity_score),
                    "linked_post": 0,
                    "tags": ",".join(marker.fallacy_types) if marker.fallacy_types else ""
                }).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {self._get_auth_header()}"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise Exception(f"HTTP {e.code}: {error_body[:200]}")
        except Exception as e:
            raise Exception(str(e))
    
    def _post_with_jwt(self, marker: PublicationMarker) -> Dict:
        """Post using JWT authentication if configured."""
        jwt_secret = (os.environ.get("JWT_WP_API_KEY", "") or 
                     os.environ.get("JWT_WP_API_TOKEN", "") or 
                     os.environ.get("JWT_SECRET", ""))
        
        jwt_user = (os.environ.get("WP_APP_USER", "") or 
                   os.environ.get("JWT_WP_USER", "") or 
                   os.environ.get("JWT_WP_EMAIL", "").split('@')[0] or
                   os.environ.get("KYLOSARC_WP_EMAIL", "").split('@')[0])
        
        app_password = (os.environ.get("WP_App_PW_MAPAPP", "") or 
                       os.environ.get("KYLOSARC_WP_PW", ""))
        
        if not jwt_secret or not jwt_user:
            raise Exception("JWT credentials not configured")
        
        try:
            token_url = f"{self.site_url}/wp-json/jwt-auth/v1/token"
            token_data = json.dumps({
                "username": jwt_user,
                "password": app_password
            }).encode()
            
            token_req = urllib.request.Request(token_url, data=token_data, headers={"Content-Type": "application/json"})
            
            with urllib.request.urlopen(token_req, timeout=30) as response:
                token_result = json.loads(response.read().decode())
                token = token_result.get("token", "")
            
            if not token:
                raise Exception("No JWT token received")
            
            post_url = f"{self.site_url}/wp-json/wp/v2/posts"
            post_data = json.dumps({
                "title": marker.headline[:200],
                "content": f"<!-- MapPress --><!-- MapID: {self.MAP_ID} -->\nVeracity: {marker.veracity_score:.2f} | Source: {marker.source_name}",
                "status": "publish",
                "meta": {
                    "_mappress_veracity_score": str(marker.veracity_score),
                    "_mappress_lat": str(marker.lat or 0),
                    "_mappress_lng": str(marker.lon or 0),
                    "_mappress_fallacy_types": ",".join(marker.fallacy_types),
                }
            }).encode()
            
            post_req = urllib.request.Request(
                post_url,
                data=post_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(post_req, timeout=30) as response:
                return json.loads(response.read().decode())
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise Exception(f"HTTP {e.code}: {error_body[:200]}")
        except Exception as e:
            raise Exception(str(e))
    
    def _post_as_wp_post(self, marker: PublicationMarker) -> Dict:
        """
        Fallback: Post as WordPress post with MapPress metadata.
        
        Used when MapPress REST API is not available.
        """
        url = f"{self.site_url}/wp-json/wp/v2/posts"
        
        custom_meta = {
            "_mappress_veracity_score": str(marker.veracity_score),
            "_mappress_color": marker.color,
            "_mappress_lat": str(marker.lat or 0),
            "_mappress_lng": str(marker.lon or 0),
            "_mappress_fallacy_types": ",".join(marker.fallacy_types),
            "_mappress_source": marker.source_name,
            "_mappress_gdel_hash": marker.id,
        }
        
        payload = {
            "title": marker.headline[:200],
            "content": f"<!-- MapPress --><!-- MapID: {self.MAP_ID} -->\nVeracity: {marker.veracity_score:.2f} | Source: {marker.source_name}",
            "status": "publish",
            "categories": [self.MAP_ID],
            "meta": custom_meta
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {self._get_auth_header()}"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                print(f"[MapPress-Fallback] Post created: {result.get('id', 'unknown')}", file=sys.stderr)
                return result
                
        except Exception as e:
            print(f"MapPress fallback error: {e}", file=sys.stderr)
            return {"error": str(e)}
    
    def sync_markers(self, markers: List[PublicationMarker]) -> int:
        """Sync multiple markers to MapPress Map ID 2."""
        self._markers_cache = markers
        count = 0
        
        for marker in markers:
            result = self.post_marker(marker)
            if "id" in result or "post_id" in result:
                # Archive to Shadow Ledger
                self._archive_to_shadow(marker, result.get("id", result.get("post_id", "unknown")))
                count += 1
            time.sleep(0.5)  # Rate limit
        
        return count
    
    def _archive_to_shadow(self, marker: PublicationMarker, wp_id: Any) -> str:
        """Archive marker to Shadow Ledger for forensic record."""
        import os
        os.makedirs(self._archive_dir, exist_ok=True)
        
        archive_entry = {
            "gdelt_hash": marker.id,
            "wp_id": wp_id,
            "headline": marker.headline,
            "source_url": marker.source_url,
            "source_name": marker.source_name,
            "lat": marker.lat,
            "lon": marker.lon,
            "veracity_score": marker.veracity_score,
            "fallacy_types": marker.fallacy_types,
            "color": marker.color,
            "icon_id": self._get_icon_id(marker.veracity_score),
            "map_id": self.MAP_ID,
            "archived_at": datetime.now().isoformat()
        }
        
        filename = f"{self._archive_dir}/{marker.id}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(archive_entry, f, indent=2)
        
        print(f"[Shadow Archive] {filename}", file=sys.stderr)
        return filename
    
    def export_manifest(self, filepath: str = "data/manifest.json") -> str:
        """Export markers as JSON manifest for frontend MapPress sync."""
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "map_id": self.MAP_ID,
            "count": len(self._markers_cache),
            "markers": [m.to_dict() for m in self._markers_cache],
            "manifold_jumps": [m.to_manifold_jump() for m in self._markers_cache]
        }
        
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        return filepath


class WordPressBridge:
    """
    WordPress REST API bridge for MapPress marker injection.
    """
    
    def __init__(self, site_url: str, username: str, password: str = ""):
        self.site_url = site_url.rstrip("/")
        self.username = username
        self.password = password
        self._markers_cache: List[PublicationMarker] = []
    
    def post_marker(self, marker: PublicationMarker) -> Dict:
        """Post a single marker to WordPress via REST API."""
        payload = marker.to_wp_rest_payload()
        
        # WordPress REST API endpoint for posts
        url = f"{self.site_url}/wp-json/wp/v2/posts"
        
        auth = f"{self.username}:{self.password}"
        import base64
        auth_header = base64.b64encode(auth.encode()).decode()
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {auth_header}"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"WordPress POST error: {e}", file=sys.stderr)
            return {"error": str(e)}
    
    def sync_markers(self, markers: List[PublicationMarker]) -> int:
        """Sync multiple markers to WordPress."""
        self._markers_cache = markers
        count = 0
        
        for marker in markers:
            result = self.post_marker(marker)
            if "id" in result:
                count += 1
        
        return count
    
    def export_manifest(self, filepath: str = "data/manifest.json") -> str:
        """Export markers as JSON manifest for frontend MapPress sync."""
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "count": len(self._markers_cache),
            "markers": [m.to_dict() for m in self._markers_cache],
            "manifold_jumps": [m.to_manifold_jump() for m in self._markers_cache]
        }
        
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        return filepath


class VeracityAuditor:
    """
    The Veracity Gate — tracks V_active and triggers lockouts.
    
    In production, this wraps engine/auditor/veracity_auditor.py.
    """
    
    def __init__(self):
        self.V_active = VERACITY_CONSTANT
        self.V_initial = VERACITY_CONSTANT
        self.ticks = 0
        self.bypass_count = 0
        self.inverion_triggered = False
        self.root_fallacy_id: Optional[str] = None
        self._lockout_until: Optional[float] = None
        
    def process_fallacies(self, fallacies: List[FallacyTelemetry]) -> Dict:
        """Process detected fallacies and update veracity state."""
        self.ticks += 1
        
        # Check for lockout
        if self._lockout_until and time.time() < self._lockout_until:
            return {
                "accepted": False,
                "reason": "lockout",
                "V_active": self.V_active,
                "bypass_triggered": True
            }
        
        # Calculate veracity decay
        total_cost = sum(f.magnitude * f.persistence for f in fallacies)
        
        previous_V = self.V_active
        self.V_active -= total_cost
        
        # Bypass detection: sudden spike
        bypass_triggered = (previous_V - self.V_active) > BYPASS_THRESHOLD
        if bypass_triggered:
            self.bypass_count += 1
            self._lockout_until = time.time() + 3.0
            
        # Inverion Divide: total collapse
        if self.V_active <= SHUTDOWN_THRESHOLD:
            self.V_active = SHUTDOWN_THRESHOLD
            self.inverion_triggered = True
            if not self.root_fallacy_id and fallacies:
                self.root_fallacy_id = hashlib.md5(
                    f"{fallacies[0].type}:{fallacies[0].coord}".encode()
                ).hexdigest()[:12]
        
        return {
            "accepted": True,
            "V_cost": total_cost,
            "V_before": previous_V,
            "V_after": self.V_active,
            "bypass_triggered": bypass_triggered,
            "inverion_triggered": self.inverion_triggered
        }
    
    def get_state(self) -> VeracityState:
        """Get current veracity state."""
        return VeracityState(
            V_active=self.V_active,
            V_initial=self.V_initial,
            ticks=self.ticks,
            bypass_count=self.bypass_count,
            inverion_triggered=self.inverion_triggered,
            root_fallacy_id=self.root_fallacy_id
        )


class InverionBridge:
    """
    The Sovereign Scrubber — main server loop.
    
    Ingests from sources, audits through Veracity Gate, 
    and serves Sunrise telemetry to frontend.
    """
    
    def __init__(self):
        self.scrubber = SemanticScrubber()
        self.auditor = VeracityAuditor()
        self._running = False
        
    def process_input(self, raw_input: str) -> Dict:
        """Process input through the full Inverion pipeline."""
        # 1. Semantic analysis
        fallacies = self.scrubber.analyze(raw_input)
        
        # 2. Veracity audit
        audit_result = self.auditor.process_fallacies(fallacies)
        
        # 3. Build output
        output = {
            "timestamp": time.time(),
            "input_hash": hashlib.sha256(raw_input.encode()).hexdigest()[:16],
            "input_preview": raw_input[:100] + "..." if len(raw_input) > 100 else raw_input,
            "fallacies": [f.to_dict() for f in fallacies],
            "veracity": self.auditor.get_state().to_dict(),
            "audit": audit_result
        }
        
        return output
    
    def run(self, source_file: Optional[str] = None):
        """Run the bridge loop."""
        self._running = True
        
        print(f"--- [INVERION BRIDGE ACTIVE] ---", file=sys.stderr)
        print(f"Veracity Constant: {VERACITY_CONSTANT}", file=sys.stderr)
        print(f"Bypass Threshold: {BYPASS_THRESHOLD}", file=sys.stderr)
        print(f"Lockout Threshold: {LOCKOUT_THRESHOLD}", file=sys.stderr)
        
        try:
            while self._running:
                # 1. Ingest from source
                if source_file and Path(source_file).exists():
                    with open(source_file, 'r', encoding='utf-8') as f:
                        raw_input = f.read()
                else:
                    # Read from stdin (pipe mode)
                    raw_input = input().strip()
                    if not raw_input:
                        break
                        
                # 2. Process through pipeline
                result = self.process_input(raw_input)
                
                # 3. Check for Inverion Divide
                if result["veracity"]["inverion_triggered"]:
                    print("[!] INVERION DIVIDE CROSSED: LOCKOUT INITIATED", file=sys.stderr)
                    
                # 4. Output JSON for frontend stitching
                print(json.dumps(result), flush=True)
                
                # 5. Check for lockout
                if result["audit"].get("bypass_triggered"):
                    print("[!] BYPASS DETECTED: Lockout for 3 seconds", file=sys.stderr)
                    time.sleep(3.0)
                    
        except KeyboardInterrupt:
            print("--- [BRIDGE SHUTDOWN] ---", file=sys.stderr)
            
    def stop(self):
        """Stop the bridge loop."""
        self._running = False


def main():
    """Main entry point."""
    load_env_file()  # Load .env if present
    import argparse
    
    parser = argparse.ArgumentParser(description="Inverion Semantic Bridge")
    parser.add_argument("--source", "-s", help="Source file to analyze")
    parser.add_argument("--test", "-t", action="store_true", help="Run test mode")
    parser.add_argument("--local-ledger", help="Path to local mock_ledger.json file for zero-cost testing")
    parser.add_argument("--loop", action="store_true", help="Loop continuously when using --local-ledger")
    parser.add_argument("--interval", type=int, default=30, help="Loop interval in seconds (default: 30)")
    parser.add_argument("--push-markers", action="store_true", help="Push markers to WordPress")
    parser.add_argument("--wp-site", help="WordPress site URL")
    parser.add_argument("--wp-user", help="WordPress username")
    parser.add_argument("--news-api", help="Query NewsAPI.org with this search term (requires NEWS_API_KEY)")
    parser.add_argument("--newsdata-io", help="Query NewsData.io with this search term (requires NEWSDATAIO_API_KEY)")
    args = parser.parse_args()
    
    bridge = InverionBridge()
    
    if args.local_ledger:
        ledger_path = args.local_ledger
        if not Path(ledger_path).exists():
            print(f"[LocalLedger] Ledger file not found: {ledger_path}", file=sys.stderr)
            sys.exit(1)
        
        connector = LocalLedgerConnector(ledger_path=ledger_path)
        geo = GeoTransformer()
        
        if args.loop:
            print(f"[LocalLedger] Starting loop mode, interval={args.interval}s", file=sys.stderr)
            print(f"[LocalLedger] Press Ctrl+C to stop", file=sys.stderr)
            try:
                while True:
                    marker = connector.fetch_next(geo)
                    if marker:
                        print(f"[LocalLedger] Processing: {marker.headline[:60]}...", file=sys.stderr)
                        
                        result = {
                            "timestamp": time.time(),
                            "marker": marker.to_dict(),
                            "manifold_jump": marker.to_manifold_jump()
                        }
                        print(json.dumps(result), flush=True)
                        
                        if args.push_markers and args.wp_site and args.wp_user:
                            wp_user = (os.environ.get("WP_APP_USER", "") or 
                                      os.environ.get("JWT_WP_USER", "") or 
                                      os.environ.get("JWT_WP_EMAIL", "").split('@')[0] or
                                      os.environ.get("KYLOSARC_WP_EMAIL", "").split('@')[0] or
                                      args.wp_user)
                            wp_pw = (os.environ.get("WP_App_PW_MAPAPP", "") or 
                                    os.environ.get("KYLOSARC_WP_PW", ""))
                            if wp_pw:
                                bridge_wp = MapPressBridge(args.wp_site, wp_user, wp_pw)
                                push_result = bridge_wp.post_marker(marker)
                                if "error" not in push_result:
                                    print(f"[LocalLedger] Marker pushed: {push_result.get('id', 'unknown')}", file=sys.stderr)
                                else:
                                    print(f"[LocalLedger] Push failed: {push_result}", file=sys.stderr)
                    
                    time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\n[LocalLedger] Loop stopped", file=sys.stderr)
        else:
            markers = connector.fetch_with_geocode(geo)
            print(f"[LocalLedger] Loaded {len(markers)} markers from ledger", file=sys.stderr)
            
            if args.push_markers and args.wp_site and args.wp_user:
                wp_user = (os.environ.get("WP_APP_USER", "") or 
                          os.environ.get("JWT_WP_USER", "") or 
                          os.environ.get("JWT_WP_EMAIL", "").split('@')[0] or
                          os.environ.get("KYLOSARC_WP_EMAIL", "").split('@')[0] or
                          args.wp_user)
                wp_pw = (os.environ.get("WP_App_PW_MAPAPP", "") or 
                        os.environ.get("KYLOSARC_WP_PW", ""))
                if wp_pw:
                    bridge_wp = MapPressBridge(args.wp_site, wp_user, wp_pw)
                    count = bridge_wp.sync_markers(markers)
                    print(f"[MapPress] Synced {count} markers to WordPress Map ID 2", file=sys.stderr)
    
    elif args.news_api:
        from news_connector import NewsAPIConnector
        connector = NewsAPIConnector()
        geo = GeoTransformer()
        scrubber = SemanticScrubber()
        
        print(f"[NewsAPI] Fetching news for: {args.news_api}", file=sys.stderr)
        articles = connector.fetch(args.news_api)
        print(f"[NewsAPI] Got {len(articles)} articles", file=sys.stderr)
        
        markers = []
        for article in articles:
            headline = article.get("title", "")
            if not headline:
                continue
            
            fallacies = scrubber.analyze(headline)
            total_cost = sum(f.magnitude * f.persistence for f in fallacies)
            veracity_score = max(0.0, VERACITY_CONSTANT - total_cost)
            fallacy_types = [f.type for f in fallacies]
            
            location_hint = article.get("source", "")
            lat, lon = geo.geocode(location_hint)
            
            marker = PublicationMarker(
                id="",
                title=headline[:100],
                headline=headline,
                source_url=article.get("link", ""),
                source_name=article.get("source", "NewsAPI"),
                lat=lat,
                lon=lon,
                veracity_score=veracity_score,
                fallacy_types=fallacy_types,
                published_at=article.get("published", "")
            )
            markers.append(marker)
        
        print(f"[NewsAPI] Processed {len(markers)} markers", file=sys.stderr)
        
        if args.push_markers and args.wp_site and args.wp_user:
            wp_user = (os.environ.get("WP_APP_USER", "") or 
                      os.environ.get("JWT_WP_USER", "") or 
                      os.environ.get("JWT_WP_EMAIL", "").split('@')[0] or
                      os.environ.get("KYLOSARC_WP_EMAIL", "").split('@')[0] or
                      args.wp_user)
            wp_pw = (os.environ.get("WP_App_PW_MAPAPP", "") or 
                    os.environ.get("KYLOSARC_WP_PW", ""))
            if wp_pw:
                bridge_wp = MapPressBridge(args.wp_site, wp_user, wp_pw)
                count = bridge_wp.sync_markers(markers)
                print(f"[MapPress] Synced {count} markers to WordPress Map ID 2", file=sys.stderr)
    
    elif args.test:
        # Test with sample input
        test_inputs = [
            "You should believe me because I am always right.",
            "Either we cut spending or we go bankrupt.",
            "If we allow this, then bad things will happen too.",
            "Everyone knows that this is obviously the best approach, therefore we must proceed.",
        ]
        
        for inp in test_inputs:
            result = bridge.process_input(inp)
            print(f"\nInput: {inp}")
            print(json.dumps(result, indent=2))
            
    elif args.source:
        bridge.run(source_file=args.source)
        
    else:
        # Interactive mode
        print("Enter text to analyze (Ctrl+C to exit):", file=sys.stderr)
        bridge.run()


if __name__ == "__main__":
    main()