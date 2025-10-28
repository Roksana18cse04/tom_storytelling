# app/services/depth_scorer.py

import re

class DepthScorer:
    """Calculate depth score for user responses"""
    
    SENSORY_KEYWORDS = ['saw', 'looked', 'bright', 'dark', 'colorful', 'picture', 'heard', 'sound', 
                        'music', 'voice', 'loud', 'quiet', 'felt', 'touch', 'warm', 'cold', 'soft', 
                        'smell', 'scent', 'aroma', 'taste', 'flavor']
    
    EMOTIONAL_KEYWORDS = ['happy', 'joyful', 'excited', 'loved', 'proud', 'grateful', 'sad', 'angry', 
                          'scared', 'worried', 'disappointed', 'nervous', 'thrilled', 'overwhelmed', 
                          'nostalgic', 'bittersweet']
    
    def calculate_depth_score(self, text: str) -> dict:
        """Calculate depth score (0-100)"""
        if not text or len(text.strip()) < 5:
            return {"total_score": 0, "depth_level": "Minimal", "breakdown": {}}
        
        text_lower = text.lower()
        words = text.split()
        word_count = len(words)
        
        # 1. Word Count Score (0-20)
        if word_count < 10:
            word_score = 0
        elif word_count < 30:
            word_score = 5
        elif word_count < 60:
            word_score = 10
        elif word_count < 100:
            word_score = 15
        else:
            word_score = 20
        
        # 2. Sensory Details Score (0-25)
        sensory_count = sum(1 for kw in self.SENSORY_KEYWORDS if kw in text_lower)
        if sensory_count == 0:
            sensory_score = 0
        elif sensory_count <= 2:
            sensory_score = 10
        elif sensory_count <= 4:
            sensory_score = 18
        else:
            sensory_score = 25
        
        # 3. Emotional Language Score (0-25)
        emotion_count = sum(1 for kw in self.EMOTIONAL_KEYWORDS if kw in text_lower)
        if emotion_count == 0:
            emotion_score = 0
        elif emotion_count <= 2:
            emotion_score = 10
        elif emotion_count <= 4:
            emotion_score = 18
        else:
            emotion_score = 25
        
        # 4. Specific Details Score (0-20)
        names = len(re.findall(r'\b[A-Z][a-z]+\b', text))
        numbers = len(re.findall(r'\b\d+\b', text))
        specific_details = names + numbers
        
        if specific_details <= 1:
            detail_score = 0
        elif specific_details <= 3:
            detail_score = 8
        elif specific_details <= 5:
            detail_score = 15
        else:
            detail_score = 20
        
        # 5. Temporal Context Score (0-10)
        temporal_score = 0
        if re.search(r'\b(19|20)\d{2}\b', text):
            temporal_score += 5
        seasons = ['spring', 'summer', 'autumn', 'fall', 'winter', 'morning', 'afternoon', 'evening']
        if any(s in text_lower for s in seasons):
            temporal_score += 3
        if re.search(r'\b\d+\s*years?\s*old\b', text_lower):
            temporal_score += 2
        temporal_score = min(temporal_score, 10)
        
        # Total Score
        total_score = word_score + sensory_score + emotion_score + detail_score + temporal_score
        
        # Depth Level
        if total_score < 20:
            depth_level = "Minimal"
        elif total_score < 40:
            depth_level = "Basic"
        elif total_score < 60:
            depth_level = "Moderate"
        elif total_score < 80:
            depth_level = "Rich"
        else:
            depth_level = "Exceptional"
        
        return {
            "total_score": total_score,
            "depth_level": depth_level,
            "breakdown": {
                "word_count": word_score,
                "sensory_details": sensory_score,
                "emotional_language": emotion_score,
                "specific_details": detail_score,
                "temporal_context": temporal_score
            }
        }

depth_scorer = DepthScorer()
