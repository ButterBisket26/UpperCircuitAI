import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def split_into_sentences(text: str) -> List[str]:
    """
    Splits text into sentences using a regex pattern that avoids splitting on common abbreviations.
    """
    # Pattern looks for ending punctuation followed by whitespace, avoiding common abbreviations
    sentence_end = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s')
    sentences = sentence_end.split(text)
    return [s.strip() for s in sentences if s.strip()]

def chunk_text_page(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 64
) -> List[str]:
    """
    Splits a single page text block into chunks of max_tokens with an overlap,
    respecting sentence boundaries. Estimating 1 word = 1.3 tokens for BGE encoding.
    """
    sentences = split_into_sentences(text)
    chunks: List[str] = []
    
    current_chunk: List[str] = []
    current_token_count = 0
    
    def estimate_tokens(s: str) -> int:
        # standard estimation: word count * 1.3
        return int(len(s.split()) * 1.3)
        
    i = 0
    while i < len(sentences):
        sentence = sentences[i]
        sentence_tokens = estimate_tokens(sentence)
        
        # If a single sentence is extremely long, treat it as its own chunk
        if sentence_tokens >= max_tokens:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_token_count = 0
            chunks.append(sentence)
            i += 1
            continue
            
        if current_token_count + sentence_tokens > max_tokens:
            # Current chunk is full, store it
            chunks.append(" ".join(current_chunk))
            
            # Apply sliding window overlap by rolling back sentences
            overlap_sentences: List[str] = []
            overlap_count = 0
            for prev_sentence in reversed(current_chunk):
                prev_tokens = estimate_tokens(prev_sentence)
                if overlap_count + prev_tokens > overlap_tokens:
                    break
                overlap_sentences.insert(0, prev_sentence)
                overlap_count += prev_tokens
                
            current_chunk = overlap_sentences
            current_token_count = overlap_count
            
        current_chunk.append(sentence)
        current_token_count += sentence_tokens
        i += 1
        
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def build_chunks(
    extracted_elements: List[Dict[str, Any]],
    company_metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Transforms extracted PDF elements (text/tables) into metadata-enriched chunks.
    
    Args:
        extracted_elements: List of {"page_number": int, "content": str, "content_type": "text" | "table"}
        company_metadata: Dict containing { "company_name": str, "ticker": str, "report_type": str, "fiscal_period": str }
        
    Returns:
        List of dicts: {"content": str, "metadata": dict, "chunk_type": "text" | "table"}
    """
    chunks: List[Dict[str, Any]] = []
    
    for element in extracted_elements:
        page_num = element["page_number"]
        content = element["content"]
        content_type = element["content_type"]
        
        # Setup metadata schema
        meta = {
            "company": company_metadata.get("company_name", company_metadata.get("company", "")),
            "ticker": company_metadata["ticker"].upper(),
            "report_type": company_metadata["report_type"],
            "fiscal_period": company_metadata["fiscal_period"].upper(),
            "page_number": page_num,
            "chunk_type": content_type
        }
        
        if content_type == "table":
            # Table chunks are atomic
            chunks.append({
                "content": content,
                "metadata": meta,
                "chunk_type": "table"
            })
            logger.info(f"Chunker: Added atomic table chunk for page {page_num}")
        else:
            # Text chunks undergo sliding-window segmentation
            text_splits = chunk_text_page(content)
            for idx, split in enumerate(text_splits):
                chunk_meta = meta.copy()
                chunk_meta["sub_index"] = idx
                chunks.append({
                    "content": split,
                    "metadata": chunk_meta,
                    "chunk_type": "text"
                })
            logger.info(f"Chunker: Segmented page {page_num} text into {len(text_splits)} chunks")
            
    return chunks
