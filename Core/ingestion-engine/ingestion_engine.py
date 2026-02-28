from sentence_transformers import SentenceTransformer, util
import torch
import re

class SimilarityClassifier:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        
        # Define prototypes for each intent
        self.prototypes = {
            "commitment": [
                "I will get this done by Friday",
                "I will follow up with the department",
                "We will ensure this is completed",
                "I promise to look into this matter",
                "I will personally ensure the work begins",
                "I will get back to you with a timeline",
                "I'll take care of this issue personally",
                "I will speak to the commissioner today",
                "I am committed to resolving this",
                "We will add this to our priority list",
                "I will contact the department today",
                "I will personally look into this matter",
                "I will ensure this is resolved by",
                "I will speak to the commissioner directly",
                "I will demand a written update",
                "I will raise this formally with the department",
                "I will get back to you with a timeline by Friday",
                "We will take this up with PWD this week",
                "I will personally follow up with the commissioner",
                "I will raise this with the department head",
                "I will contact the department this afternoon",
                "I will call the commissioner directly today",
                "I will demand a written update by end of week",
                "I will raise this formally with the department this week",
                "I will ensure work begins by the given date",
                "I will get a timeline by Friday",
                "I will get back to you on this",
                "Kindly look into this matter",
                "We will take this up immediately",
                "I will personally ensure this is resolved",
                "I will speak to the concerned officer today",
                "I will send a notice to the department",
                "I will escalate this to the commissioner",
                "We will take strict action on this",
                "We will fix it",
                "I will fix this issue"
            ],
            "question": [
                "Can you give an update on this?",
                "What is the current status?",
                "Has this work been completed?",
                "When will this be done?",
                "Can you check whether the applications have been processed?",
                "What is the reason for the delay?",
                "Why has no progress been made?",
                "How much more time is required?",
                "Is there any update on the pending files?",
                "Who is responsible for this task?",
                "What is the status of the repair work",
                "Has any work started yet",
                "What is the current budget utilization",
                "Has this been processed yet",
                "Why has no progress been made on this",
                "When will this be completed",
                "What action has been taken so far",
                "Can you explain the delay",
                "Who is responsible for this",
                "Is the contractor assigned yet"
            ],
            "action": [
                "Follow up with PWD commissioner",
                "Send a written update by end of week",
                "Check the status of applications",
                "Fix the contractor assignment issue",
                "Provide a written report on the delay",
                "Coordinate with the local councillor",
                "Assign this task to the junior engineer"
            ],
            "context": [
                "The ward has a population of approximately 45,000",
                "This issue has been ongoing since last monsoon",
                "The budget allocated for this is 2.3 crore",
                "Coverage in the ward is currently at 60 percent",
                "Eligible families are still waiting for processing",
                "The remaining 40 percent relies on open drains",
                "Flooding occurs every year in this specific area",
                "The previous contractor abandoned the site"
            ],
            "noise": [
                "Good morning everyone",
                "Thank you for coming",
                "That concludes the meeting",
                "Please be seated",
                "Thank you all for your questions",
                "Next meeting is scheduled for tomorrow",
                "Let's move to the next item on the agenda",
                "Thank you",
                "Thanks",
                "Okay",
                "Right",
                "I see",
                "Let us begin",
                "Shall we start",
                "Let us move to the next point",
                "That is all for today",
                "We will close here",
                "Please proceed",
                "Go ahead",
                "Yes please",
                "We need to move faster on this",
                "This is priority",
                "Time is running out",
                "We should focus on this"
            ],
            "answer": [
                "Yes, that is correct",
                "The budget for this is 2.3 crore",
                "We have already processed the applications",
                "The work started last week",
                "No, that has not been done yet",
                "I have the report right here",
                "The contractor has been notified",
                "The funds have already been released",
                "It is currently under process",
                "The department has approved the plan"
            ]
        }
        
        # Pre-embed prototypes for efficiency
        self.prototype_embeddings = {}
        for label, texts in self.prototypes.items():
            self.prototype_embeddings[label] = self.model.encode(texts, convert_to_tensor=True)

    def classify(self, text):
        """
        Calculates cosine similarity between input text and all prototype groups.
        Returns the best matching label and the confidence score.
        """
        text_embedding = self.model.encode(text, convert_to_tensor=True)
        
        best_label = "noise"
        max_similarity = 0.0
        
        for label, proto_embeds in self.prototype_embeddings.items():
            # Calculate cosine similarities
            cos_sim = util.cos_sim(text_embedding, proto_embeds)
            # Take the maximum similarity in this group as the score for the category
            group_max = torch.max(cos_sim).item()
            
            if group_max > max_similarity:
                max_similarity = group_max
                best_label = label
                
        return best_label, max_similarity

class IngestionEngine:
    def __init__(self, model_name="all-MiniLM-L6-v2", user_name="User"):
        """
        Initialize the Ingestion Engine with Embedding Similarity.
        """
        self.user_name = user_name
        self.model_name = model_name
        
        # Load spaCy for sentence boundary detection
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
        except (ImportError, Exception) as e:
            self.nlp = None
            print(f"Warning: spaCy could not be loaded ({type(e).__name__}). Using basic sentence splitting fallback.")

        # Load our new Similarity Classifier
        self.classifier = SimilarityClassifier(model_name=self.model_name)
        self.threshold = 0.45
        print(f"Ingestion Engine initialized with {self.model_name} (Threshold: {self.threshold})")

    def _basic_sentence_split(self, text):
        """Fallback sentence splitter if spaCy is unavailable."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def segment_text(self, text):
        """
        Splits raw text into sentences while ensuring speaker persistence.
        1. Split by newline (transcript line level)
        2. Detect speaker per line
        3. Split each line into sentences
        4. Carry speaker forward to all sub-sentences
        """
        all_sentences = []
        lines = text.splitlines()
        
        # Step 0: Strip metadata headers (lines before the first valid speaker tag)
        start_index = 0
        for i, line in enumerate(lines):
            # Looking specifically for common speaker patterns to avoid "Date:" etc.
            if re.match(r"^(User|Person|Staff|MLA|Commissioner|Councillor)\s*(\d+)?\s*:", line, re.IGNORECASE):
                start_index = i
                break
        lines = lines[start_index:]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Step 1: Detect speaker for this specific transcript line
            speaker, clean_text = self.detect_speaker(line)
            
            # Step 2: Split the cleaned text into sentences
            if self.nlp:
                doc = self.nlp(clean_text)
                sub_sentences = [sent.text.strip() for sent in doc.sents]
            else:
                sub_sentences = self._basic_sentence_split(clean_text)
                
            # Step 3: Re-attach speaker to each sub-sentence for context
            for sent in sub_sentences:
                if speaker:
                    all_sentences.append(f"{speaker}: {sent}")
                else:
                    all_sentences.append(sent)
                    
        return all_sentences

    def apply_sliding_window(self, sentences):
        """
        Creates chunks with sliding window context.
        Each chunk contains: [previous_sentence, current_sentence, next_sentence].
        """
        chunks = []
        for i in range(len(sentences)):
            prev_sent = sentences[i-1] if i > 0 else ""
            curr_sent = sentences[i]
            next_sent = sentences[i+1] if i < len(sentences) - 1 else ""
            
            # Combine for classification context
            context_text = f"{prev_sent} {curr_sent} {next_sent}".strip()
            chunks.append({
                "original": curr_sent,
                "with_context": context_text
            })
        return chunks

    def detect_speaker(self, text):
        """
        Detects if a sentence has a clear speaker label (e.g., 'User: ...').
        Returns (speaker, clean_text).
        """
        match = re.match(r"^([^:]+):\s*(.*)$", text)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None, text

    def is_obvious_noise(self, text):
        """
        Quickly identifies common meeting fillers, greetings, and closures 
        using regex to avoid expensive and potentially confusing LLM classification.
        """
        noise_patterns = [
            r"^(good\s+(morning|afternoon|evening|day))",
            r"^(hello|hi|hey|ok|yes|no|dear|sir|maam|everyone)\.?$",
            r"^(thank\s+you|thanks|welcome|bye|goodbye)",
            r"^(can\s+you\s+hear\s+me\??)",
            r"^(shall\s+we\s+begin\??)",
            r"^(i am aware|i know|noted|understood|i see|certainly|of course|sure|absolutely)(\s+.*)?\.?$"
        ]
        text_clean = text.lower().strip()
        for pattern in noise_patterns:
            if re.search(pattern, text_clean):
                return True
        return False

    def smart_routing(self, label, confidence, speaker, original_text, is_answered=False):
        """
        Determines the destination engine based on label, confidence, speaker, and resolution status.
        """
        threshold = self.threshold
        
        # Priority 1: Sentinel / Noise check
        if label == "noise" or confidence < threshold:
            return "discarded" if label == "noise" else "flagged"

        # Special Case: Acknowledgements that might have been classified but are noise
        if self.is_obvious_noise(original_text):
            return "discarded"

        # Determine if the user is involved
        is_user = (speaker and speaker.lower() == self.user_name.lower())
        
        if label in ["commitment", "action"]:
            # Commitments/Actions only count if they come FROM the user
            if is_user:
                return "commitment_engine"
            elif speaker is None:
                return "flagged"
            else:
                return "discarded"
        
        if label == "question":
            # If answered (by User or anyone), we archive it in RAG as historical context
            if is_answered:
                return "rag_engine"
            
            # If open:
            if not is_user:
                # Directed AT the user? Track it as a commitment.
                return "commitment_engine" if speaker is not None else "flagged"
            else:
                # User asking others? No commitment needed for User.
                return "discarded"

        if label in ["context", "answer"]:
            return "rag_engine"

        return "discarded"

    def process_text(self, text, source_id="unknown"):
        """Main pipeline execution with Two-Pass QA detection."""
        from tqdm import tqdm
        
        print(f"Processing text from '{source_id}'...")
        sentences = self.segment_text(text)
        chunks = self.apply_sliding_window(sentences)
        
        print(f"Created {len(chunks)} chunks. Step 1: Classification...")
        
        # Step 1: Classify all chunks first
        raw_results = []
        for chunk in tqdm(chunks, desc="Classifying", unit="chunk"):
            speaker, clean_text = self.detect_speaker(chunk["original"])
            
            # CHECK SENTINEL FIRST: Pre-filter so classification doesn't get confused
            is_noise = self.is_obvious_noise(clean_text)
            
            if is_noise:
                top_label = "noise"
                top_score = 1.0
            else:
                # Classify the CLEAN text to avoid "User: " prefix interference
                # Use context only if the clean text is very short (< 20 chars)
                classify_input = clean_text
                if len(clean_text) < 20:
                    classify_input = chunk["with_context"]
                
                top_label, top_score = self.classifier.classify(classify_input)
            
            raw_results.append({
                "chunk": chunk,
                "speaker": speaker,
                "clean_text": clean_text,
                "label": top_label,
                "confidence": top_score,
                "is_sentinel_noise": is_noise
            })

        print("Step 2: Smart Routing & QA Pairing...")
        results = {
            "source_id": source_id,
            "total_chunks": len(chunks),
            "routed": {
                "commitment_engine": 0,
                "rag_engine": 0,
                "discarded": 0,
                "flagged": 0,
                "uncertain": 0
            },
            "items": []
        }

        for i in range(len(raw_results)):
            item = raw_results[i]
            
            # QA Pairing Logic (Round 3: Look ahead TWO chunks)
            is_answered = False
            if item["label"] == "question":
                # Check next 2 items
                for lookahead in [1, 2]:
                    if i + lookahead < len(raw_results):
                        next_item = raw_results[i + lookahead]
                        # Answer can be answer, commitment, action, or context
                        if next_item["label"] in ["answer", "commitment", "action", "context"]:
                            if next_item["confidence"] >= self.threshold:
                                is_answered = True
                                break
            
            route = self.smart_routing(
                item["label"], 
                item["confidence"], 
                item["speaker"], 
                item["clean_text"],
                is_answered=is_answered
            )
            
            # Label adjustment for display
            display_label = item["label"]
            if is_answered:
                display_label = "answered_question"
            elif item["label"] == "question":
                display_label = "open_question"
            
            # Log results
            results["routed"][route] += 1
            if route == "flagged":
                results["routed"]["uncertain"] += 1
                
            results["items"].append({
                "chunk_text": item["chunk"]["original"],
                "speaker": item["speaker"],
                "label": display_label,
                "confidence": item["confidence"],
                "routed_to": route
            })

            if route == "commitment_engine":
                print(f"[ROUTE] Sending to Commitment Engine: {item['clean_text']}")
            elif route == "rag_engine":
                print(f"[ROUTE] Sending to RAG Engine: {item['clean_text']}")

        return results

if __name__ == "__main__":
    # Quick sanity check
    engine = IngestionEngine()
    test_text = """
    User: I will fix the drainage issue in Ward 12 by next Friday.
    Staff: Sir, the budget for the new park is still pending.
    Staff: Can you approve the new sewage plant design by tomorrow?
    User: How much does it cost?
    """
    res = engine.process_text(test_text)
    print(res["routed"])
