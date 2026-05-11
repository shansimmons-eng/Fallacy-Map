"""
Sliding Window Buffer for Real-Time Input Streams
Implements the Inverion Protocol for high-frequency argument analysis.
"""

import hashlib
import json
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional, List, Callable, AsyncIterator
import asyncio

@dataclass
class WindowChunk:
    """A chunk of text within the sliding window."""
    text: str
    start_token: int
    end_token: int
    timestamp: float
    content_hash: str
    fallacy_count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WindowChunk':
        return cls(**data)

class SlidingWindowBuffer:
    """
    Sliding Window Buffer for real-time transcript analysis.
    
    Maintains context across chunks while allowing continuous streaming.
    Uses 512 token window with 50% overlap by default.
    """
    
    def __init__(
        self,
        window_size: int = 512,
        overlap: float = 0.5,
        on_chunk_processed: Optional[Callable] = None,
        on_bypass_detected: Optional[Callable] = None
    ):
        self.window_size = window_size
        self.overlap = overlap
        self.step_size = int(window_size * (1 - overlap))
        
        self.buffer: deque[str] = deque(maxlen=window_size * 2)
        self.chunks: deque[WindowChunk] = deque(maxlen=100)
        self.analysis_history: List[dict] = []
        
        self._token_count = 0
        self._last_chunk_time = time.time()
        self._bypass_lockout_until: Optional[float] = None
        
        self.on_chunk_processed = on_chunk_processed
        self.on_bypass_detected = on_bypass_detected
        
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization by whitespace - replace with proper tokenizer."""
        return text.split()
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        return len(self._tokenize(text))
    
    def _hash_content(self, text: str) -> str:
        """Create SHA256 hash of content for sovereign ledger."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def ingest(self, text: str, is_final: bool = False) -> List[WindowChunk]:
        """
        Ingest new text into the sliding window.
        Returns list of chunks ready for analysis when window is full.
        """
        self.buffer.append(text)
        self._token_count += self._estimate_tokens(text)
        
        ready_chunks = []
        
        while self._token_count >= self.window_size:
            chunk_text = self._extract_window()
            
            chunk = WindowChunk(
                text=chunk_text,
                start_token=self._token_count - self._estimate_tokens(chunk_text),
                end_token=self._token_count,
                timestamp=time.time(),
                content_hash=self._hash_content(chunk_text)
            )
            
            self.chunks.append(chunk)
            ready_chunks.append(chunk)
            
            if self.on_chunk_processed:
                self.on_chunk_processed(chunk)
                
        return ready_chunks
    
    def _extract_window(self) -> str:
        """Extract window_size tokens from buffer."""
        tokens = []
        total_tokens = 0
        
        while tokens and total_tokens < self.window_size:
            if self.buffer:
                next_text = self.buffer.popleft()
                next_tokens = self._tokenize(next_text)
                tokens.extend(next_tokens)
                total_tokens = len(tokens)
            else:
                break
        
        if total_tokens > self.window_size:
            excess = total_tokens - self.window_size
            tokens = tokens[excess:]
        
        self._token_count = max(0, self._token_count - total_tokens)
        
        return ' '.join(tokens[-self.window_size:])
    
    def flush(self) -> Optional[WindowChunk]:
        """Flush remaining content in buffer as final chunk."""
        if not self.buffer:
            return None
            
        remaining = ' '.join(self.buffer)
        self.buffer.clear()
        
        chunk = WindowChunk(
            text=remaining,
            start_token=0,
            end_token=self._estimate_tokens(remaining),
            timestamp=time.time(),
            content_hash=self._hash_content(remaining)
        )
        
        self.chunks.append(chunk)
        return chunk
    
    def check_bypass(self, decay_rate: float, threshold: float = 0.5) -> bool:
        """
        Check if decay rate exceeds bypass threshold.
        Returns True if bypass detected and should trigger lockout.
        """
        if self._bypass_lockout_until and time.time() < self._bypass_lockout_until:
            return True
            
        if decay_rate > threshold:
            self._bypass_lockout_until = time.time() + 3.0
            
            if self.on_bypass_detected:
                self.on_bypass_detected(decay_rate)
                
            return True
            
        return False
    
    def get_ledger_entry(self, analysis_result: dict) -> dict:
        """Create immutable ledger entry for Sovereign Ledger."""
        return {
            "timestamp": time.time(),
            "window_hash": self._hash_content(' '.join(self.buffer)) if self.buffer else None,
            "chunks_processed": len(self.chunks),
            "analysis": analysis_result
        }
    
    def export_archive(self) -> dict:
        """Export all chunks and analysis to archive format."""
        return {
            "window_config": {
                "window_size": self.window_size,
                "overlap": self.overlap
            },
            "chunks": [c.to_dict() for c in self.chunks],
            "analysis_history": self.analysis_history,
            "export_timestamp": time.time()
        }


class StreamBridge:
    """
    Bridge for real-time input streams (YouTube Live, Zoom, Mic-to-Text).
    Wraps sliding window buffer with stream-specific handling.
    """
    
    def __init__(
        self,
        buffer: Optional[SlidingWindowBuffer] = None,
        source_name: str = "unknown"
    ):
        self.buffer = buffer or SlidingWindowBuffer()
        self.source_name = source_name
        self._running = False
        self._archive_dir = "data/archive"
        
    async def ingest_stream(self, stream_iterator: AsyncIterator[str]) -> AsyncIterator[WindowChunk]:
        """Ingest from async stream (YouTube Live, etc)."""
        self._running = True
        
        async for text_chunk in stream_iterator:
            if not self._running:
                break
                
            chunks = self.buffer.ingest(text_chunk)
            
            for chunk in chunks:
                yield chunk
                
            await asyncio.sleep(0.01)
    
    def ingest_file(self, filepath: str) -> List[WindowChunk]:
        """Ingest from local file (.txt, .pdf, .json)."""
        chunks = []
        
        if filepath.endswith('.json'):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        chunks.extend(self.buffer.ingest(str(item)))
                else:
                    chunks.extend(self.buffer.ingest(str(data)))
        else:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                chunks = self.buffer.ingest(content)
        
        final_chunk = self.buffer.flush()
        if final_chunk:
            chunks.append(final_chunk)
            
        return chunks
    
    def archive_chunk(self, chunk: WindowChunk, analysis: dict) -> str:
        """Archive analyzed chunk to Sovereign Ledger."""
        import os
        os.makedirs(self._archive_dir, exist_ok=True)
        
        ledger_entry = self.buffer.get_ledger_entry(analysis)
        archive_data = {
            "source": self.source_name,
            "chunk": chunk.to_dict(),
            "analysis": analysis,
            "ledger": ledger_entry,
            "archived_at": time.time()
        }
        
        filename = f"{self._archive_dir}/{chunk.content_hash}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(archive_data, f, indent=2)
            
        return filename