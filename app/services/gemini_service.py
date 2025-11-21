import os
import json
import re
from datetime import datetime
import google.generativeai as genai

class GeminiService:
    """Service for interacting with Gemini API"""
    
    def __init__(self):
        """Initialize Gemini service"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        # Try different model names in order of preference
        # Based on official docs: https://ai.google.dev/gemini-api/docs
        model_names = [
            'gemini-2.5-flash',         # Latest flash model (recommended)
            'gemini-1.5-flash',         # Stable and fast
            'gemini-1.5-pro',           # More capable
            'gemini-pro',               # Fallback (deprecated)
        ]
        
        self.model = None
        for model_name in model_names:
            try:
                self.model = genai.GenerativeModel(model_name)
                print(f"✅ Successfully initialized Gemini model: {model_name}")
                break
            except Exception as e:
                print(f"❌ Failed to initialize {model_name}: {e}")
                continue
        
        if not self.model:
            # Try to list available models for debugging
            try:
                available_models = [model.name for model in genai.list_models()]
                print(f"Available models: {available_models}")
            except Exception as e:
                print(f"Could not list models: {e}")
            
            raise ValueError("Could not initialize any Gemini model. Please check your API key and model availability.")
    
    @staticmethod
    def list_available_models():
        """List all available Gemini models"""
        try:
            models = genai.list_models()
            return [{"name": model.name, "display_name": model.display_name} for model in models]
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def extract_task_from_email(self, email_subject, email_body):
        """
        Extract task information from email using Gemini AI
        
        Args:
            email_subject: Email subject line
            email_body: Email body content
        
        Returns:
            Dictionary with task information or None if no task found
        """
        prompt = self._build_extraction_prompt(email_subject, email_body)
        
        try:
            response = self.model.generate_content(prompt)
            task_data = self._parse_gemini_response(response.text)
            return task_data
        except Exception as e:
            print(f"Error extracting task with Gemini: {e}")
            return None
    
    def _build_extraction_prompt(self, subject, body):
        """Build prompt for Gemini to extract task information"""
        prompt = f"""
You are an AI assistant helping an employee organize tasks from their manager's emails.

Your role: Analyze emails from managers/supervisors and identify ALL work assignments, action items, and responsibilities.

Email Subject: {subject}
Email Body:
{body}

Extract task, request, or action item mentioned and return them as a JSON array.

Return ONLY valid JSON (no markdown, no explanation):

{{
  "has_tasks": true or false,
  "tasks": [
    {{
      "title": "Brief task title (max 100 chars)",
      "description": "Complete context of what needs to be done",
      "priority": "low" | "medium" | "high",
      "deadline": "YYYY-MM-DD" | null
    }}
  ]
}}

Task Identification Rules:
1. A "task" is ANY instruction, request, deliverable, or action item assigned to the employee
2. Extract EVERY separate task mentioned - even if they're in one sentence
   Examples:
   - "Update the report and send it to the team" = 2 tasks
   - "Fix bug #123, test it, and deploy to staging" = 3 tasks
   - "Prepare slides, book a room, and invite stakeholders" = 3 tasks

3. Common task indicators:
   - Action verbs: create, update, fix, send, prepare, complete, review, test, deploy, etc.
   - Phrases like "Your tasks for this week", "Action items", "To-do"

Priority Detection:
- HIGH: "urgent", "ASAP", "critical", "important", "high priority", "immediately", "today", "emergency"
- MEDIUM: Default for most tasks, "normal", "standard"
- LOW: "when you can", "low priority", "nice to have", "optional", "if time permits"

Deadline Detection:
- Exact dates: "2025-12-25", "December 25", "Dec 25"
- Relative: "by Friday", "by tomorrow", "by end of week", "by Monday"
- Time-based: "end of day", "EOD", "by 5pm", "before the meeting"
- Week/month: "this week", "next week", "end of month"
- If multiple deadlines mentioned, use the earliest one
- If no deadline → null

Edge Cases:
- If email is just FYI/informational → {{"has_tasks": false, "tasks": []}}
- If email asks questions but no action needed → {{"has_tasks": false, "tasks": []}}
- If email is a status update only → {{"has_tasks": false, "tasks": []}}

Example 1 - Manager's task list:
Input: "Hi team, please complete: 1) Update client presentation 2) Fix login bug (urgent!) 3) Review Q4 metrics by Friday"
Output: {{"has_tasks": true, "tasks": [{{"title": "Update client presentation", "description": "Update the client presentation as requested by manager", "priority": "medium", "deadline": null}}, {{"title": "Fix login bug", "description": "Fix the login bug - marked as urgent", "priority": "high", "deadline": null}}, {{"title": "Review Q4 metrics", "description": "Review Q4 metrics as requested, due by Friday", "priority": "medium", "deadline": "2025-11-22"}}]}}

Example 2 - Single email, multiple tasks:
Input: "Can you send me the report, update the dashboard, and schedule a team meeting for next week?"
Output: {{"has_tasks": true, "tasks": [{{"title": "Send report", "description": "Send the requested report to manager", "priority": "medium", "deadline": null}}, {{"title": "Update dashboard", "description": "Update the dashboard as requested", "priority": "medium", "deadline": null}}, {{"title": "Schedule team meeting", "description": "Schedule a team meeting for next week", "priority": "medium", "deadline": "2025-11-27"}}]}}

Example 3 - No tasks:
Input: "FYI - The server maintenance is scheduled for tonight. No action needed from your end."
Output: {{"has_tasks": false, "tasks": []}}

Return ONLY the JSON object. No additional text, no markdown formatting.
"""
        return prompt
    
    def _parse_gemini_response(self, response_text):
        """Parse Gemini response to extract JSON with multiple tasks"""
        try:
            # Remove markdown code blocks if present
            cleaned_text = response_text.strip()
            cleaned_text = re.sub(r'^```json\s*', '', cleaned_text)
            cleaned_text = re.sub(r'^```\s*', '', cleaned_text)
            cleaned_text = re.sub(r'\s*```$', '', cleaned_text)
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON
            response_data = json.loads(cleaned_text)
            
            # Validate structure
            if not isinstance(response_data, dict):
                return None
            
            # Check if email contains tasks
            if not response_data.get('has_tasks', False):
                return None
            
            # Get tasks array
            tasks = response_data.get('tasks', [])
            if not tasks or not isinstance(tasks, list):
                return None
            
            # Process and validate each task
            validated_tasks = []
            valid_priorities = ['low', 'medium', 'high']
            
            for task in tasks:
                # Validate required fields
                if not task.get('title') or not task.get('description'):
                    continue
                
                # Validate and fix priority
                if task.get('priority') not in valid_priorities:
                    task['priority'] = 'medium'
                
                # Parse deadline
                if task.get('deadline'):
                    try:
                        deadline = datetime.strptime(task['deadline'], '%Y-%m-%d')
                        task['deadline'] = deadline
                    except ValueError:
                        task['deadline'] = None
                else:
                    task['deadline'] = None
                
                validated_tasks.append(task)
            
            # Return the first task for backward compatibility
            # Or return all tasks if you want to create multiple
            if validated_tasks:
                # Return structure with all tasks
                return {
                    'has_task': True,  # For backward compatibility
                    'has_tasks': True,
                    'tasks': validated_tasks,
                    # Also include first task at root level for backward compatibility
                    'title': validated_tasks[0]['title'],
                    'description': validated_tasks[0]['description'],
                    'priority': validated_tasks[0]['priority'],
                    'deadline': validated_tasks[0]['deadline']
                }
            
            return None
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse Gemini response as JSON: {e}")
            print(f"Response text: {response_text}")
            return None
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            return None
    
    def analyze_email_sentiment(self, email_body):
        """
        Analyze sentiment of email (optional feature)
        
        Args:
            email_body: Email content
        
        Returns:
            Dictionary with sentiment analysis
        """
        prompt = f"""
Analyze the sentiment and urgency of this email. Return only a JSON object:

Email:
{email_body}

Return format:
{{"sentiment": "positive" or "neutral" or "negative", "urgency": "low" or "medium" or "high"}}
"""
        try:
            response = self.model.generate_content(prompt)
            cleaned_text = re.sub(r'^```json\s*|\s*```$', '', response.text.strip())
            return json.loads(cleaned_text)
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {"sentiment": "neutral", "urgency": "medium"}
    
    def summarize_email(self, email_body, max_length=200):

        prompt = f"""
Summarize the following email in {max_length} characters or less:

{email_body}

Provide only the summary, no additional text.
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error summarizing email: {e}")
            return email_body[:max_length]
    
    def summarize_meeting_transcript(self, transcript_text, meeting_title='', attendees=None):

        attendees_list = ', '.join([a.get('name', a.get('email', '')) for a in (attendees or [])])
        
        prompt = f"""
You are an expert AI assistant analyzing business meeting transcripts. Your job is to extract actionable insights, decisions, and tasks from the conversation.

Meeting Title: {meeting_title}
Attendees: {attendees_list}

Transcript:
{transcript_text}

Analyze this meeting transcript thoroughly and provide a comprehensive summary in JSON format.

Return ONLY valid JSON (no markdown, no code blocks, no explanation):

{{
  "summary": "A comprehensive 2-4 sentence overview of the meeting covering main topics, outcomes, and overall context",
  "key_points": [
    "Critical point or insight from the meeting",
    "Important discussion topic or finding",
    "Significant update or information shared"
  ],
  "decisions_made": [
    "Concrete decision that was finalized",
    "Agreement or consensus reached",
    "Approved plan or approach"
  ],
  "action_items": [
    {{
      "description": "Clear, specific description of what needs to be done",
      "assigned_to": "Person's name or email (ONLY if explicitly mentioned in transcript, otherwise use 'Unassigned')",
      "priority": "low" | "medium" | "high",
      "deadline": "YYYY-MM-DD" | null,
      "context": "Why this task is needed or what it relates to"
    }}
  ],
  "topics_discussed": [
    "Main topic 1",
    "Main topic 2"
  ],
  "participants_mentioned": [
    "Person 1 who actively participated",
    "Person 2 who actively participated"
  ],
  "next_meeting": {{
    "suggested_date": "YYYY-MM-DD or descriptive text like 'next week'",
    "topics": ["Topic to discuss next time"]
  }} OR null if not mentioned
}}

CRITICAL RULES FOR EXTRACTION:

1. **Action Items - Extract EVERYTHING actionable:**
   - ANY task, deliverable, or work assignment mentioned
   - Follow-up items, even if minor
   - Preparatory work mentioned for future meetings
   - Documentation or reporting requirements
   - Reviews or approvals needed
   - Research or investigation tasks
   
   Examples of action items to catch:
   - "Can you send me the report?" → Action item
   - "We need to update the documentation" → Action item  
   - "Someone should reach out to the client" → Action item
   - "Let's prepare slides for next week" → Action item
   - "I'll look into that issue" → Action item

2. **Assignment Detection:**
   - ONLY assign to someone if their name is EXPLICITLY mentioned with the task
   - "John, can you handle this?" → assigned_to: "John"
   - "We need someone to do X" → assigned_to: "Unassigned"
   - "The team should work on Y" → assigned_to: "Team"
   - If speaker says "I'll do X" → use the speaker's name if identifiable

3. **Priority Determination:**
   - **HIGH**: Contains words like "urgent", "ASAP", "critical", "immediately", "high priority", "blocker", "emergency", "today", "by end of day"
   - **MEDIUM**: Default for most tasks, or words like "soon", "this week", "important", "needed"
   - **LOW**: Contains "when you can", "low priority", "nice to have", "optional", "if time permits", "eventually"

4. **Deadline Extraction:**
   - Exact dates: "May 10", "next Friday", "by the 15th"
   - Relative: "by tomorrow", "by next week", "by end of month", "by Monday"
   - Time-based: "EOD", "by 5pm", "before the meeting", "this week"
   - Current date context: Today is November 20, 2025
   - Convert relative dates to YYYY-MM-DD format
   - If no deadline mentioned → null

5. **Key Points - What matters:**
   - Major insights or learnings
   - Important updates or announcements
   - Concerns or risks raised
   - Progress updates on ongoing work
   - Technical decisions or architectural choices

6. **Decisions Made:**
   - ONLY include actual decisions that were finalized
   - Must have clear consensus or approval
   - "We agreed to X" → Decision
   - "We're discussing X" → NOT a decision (just a topic)
   - "Let's think about X" → NOT a decision

7. **Next Meeting:**
   - Only include if explicitly discussed
   - Extract suggested dates or timeframes
   - List topics mentioned for next meeting
   - If not mentioned at all → null

QUALITY STANDARDS:
- Be precise and specific in descriptions
- Capture the business context, not just the words
- Distinguish between discussion and decisions
- Don't invent or assume information not in the transcript
- If transcript is unclear or incomplete, still extract what you can

Example Input:
"John: We need to finalize the API design this week. Sarah, can you update the documentation by Friday? Also, we should schedule a follow-up meeting for next Monday to review progress."

Example Output:
{{
  "summary": "Team meeting focused on API design finalization. Documentation updates assigned with Friday deadline. Follow-up meeting scheduled for next week to review progress.",
  "key_points": [
    "API design needs to be finalized this week",
    "Documentation requires updating",
    "Progress review scheduled for next meeting"
  ],
  "decisions_made": [
    "Scheduled follow-up meeting for next Monday"
  ],
  "action_items": [
    {{
      "description": "Update API documentation",
      "assigned_to": "Sarah",
      "priority": "medium",
      "deadline": "2025-11-22",
      "context": "Required for API design finalization"
    }},
    {{
      "description": "Finalize API design",
      "assigned_to": "Team",
      "priority": "medium",
      "deadline": "2025-11-22",
      "context": "Needs completion this week"
    }}
  ],
  "topics_discussed": [
    "API design finalization",
    "Documentation updates",
    "Follow-up meeting planning"
  ],
  "participants_mentioned": [
    "John",
    "Sarah"
  ],
  "next_meeting": {{
    "suggested_date": "2025-11-25",
    "topics": ["Review progress on API design and documentation"]
  }}
}}

Now analyze the provided meeting transcript and return ONLY the JSON object.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return self._parse_meeting_summary_response(response.text)
        except Exception as e:
            print(f"Error summarizing meeting: {e}")
            return None
    
    def _parse_meeting_summary_response(self, response_text):
        """Parse meeting summary response from Gemini"""
        try:
            # Remove markdown code blocks
            cleaned_text = response_text.strip()
            cleaned_text = re.sub(r'^```json\s*', '', cleaned_text)
            cleaned_text = re.sub(r'^```\s*', '', cleaned_text)
            cleaned_text = re.sub(r'\s*```$', '', cleaned_text)
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON
            summary_data = json.loads(cleaned_text)
            
            # Validate structure
            required_fields = ['summary', 'key_points', 'action_items']
            for field in required_fields:
                if field not in summary_data:
                    print(f"Missing required field: {field}")
                    return None
            
            # Process action items
            valid_priorities = ['low', 'medium', 'high']
            for item in summary_data.get('action_items', []):
                if item.get('priority') not in valid_priorities:
                    item['priority'] = 'medium'
                
                # Parse deadline if present
                if item.get('deadline'):
                    try:
                        datetime.strptime(item['deadline'], '%Y-%m-%d')
                    except ValueError:
                        item['deadline'] = None
            
            return summary_data
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse meeting summary JSON: {e}")
            print(f"Response text: {response_text}")
            return None
        except Exception as e:
            print(f"Error parsing meeting summary: {e}")
            return None
    
    def extract_insights_from_meeting(self, transcript_text):
        """
        Extract deeper insights from meeting (technical decisions, risks, blockers)
        
        Args:
            transcript_text: Full meeting transcript
        
        Returns:
            Dictionary with insights
        """
        prompt = f"""
Analyze this meeting transcript and extract technical insights.

Transcript:
{transcript_text}

Return ONLY valid JSON:

{{
  "technical_decisions": [
    "Decision about technology, architecture, or approach"
  ],
  "risks_identified": [
    "Risk or concern mentioned"
  ],
  "blockers": [
    "Blocking issue or dependency"
  ],
  "questions_raised": [
    "Unanswered question or open issue"
  ]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            cleaned_text = re.sub(r'^```json\s*|\s*```$', '', response.text.strip())
            return json.loads(cleaned_text)
        except Exception as e:
            print(f"Error extracting insights: {e}")
            return {
                "technical_decisions": [],
                "risks_identified": [],
                "blockers": [],
                "questions_raised": []
            }
