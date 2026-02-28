# BOWJOB_REFERENCE.md
# HirePilot-AI — BowJob Reference Implementation
# ═══════════════════════════════════════════════
# Copilot: Read this ENTIRE file before building any CV-related task.
# Relevant tasks: TASK-008, TASK-009, TASK-017, TASK-018
# ═══════════════════════════════════════════════

---

## GEMINI REPLACEMENT RULES — READ FIRST BEFORE ANY CODE

```
Rule A: PyPDF2 is REPLACED by PyMuPDF (fitz) in HirePilot-AI
  BowJob uses:       PyPDF2.PdfReader(file)
  HirePilot-AI uses: fitz.open(pdf_path)

Rule B: python-docx handles DOCX files (BowJob only handled PDF)
  HirePilot-AI adds: if file.endswith('.docx') → use python-docx

Rule C: No token cost tracking needed
  BowJob tracked INPUT_COST_PER_1M and OUTPUT_COST_PER_1M
  HirePilot-AI REMOVES all cost tracking — Gemini is free tier

Rule D: No tool_choice in Gemini — use JSON prompt pattern instead
  BowJob used:        OpenAI function calling with tool_choice
  HirePilot-AI uses:  JSON prompt + clean_json_response() + json.loads()

Rule E: session_id is REQUIRED for get_llm()
  Every agent node receives state["session_id"]
  Pass it: get_llm(state["session_id"], "AgentName")

Rule F: LLM import pattern for HirePilot-AI
  REMOVE:  from openai import OpenAI
  ADD:     from backend.tools.gemini_llm import get_llm
           from langchain.schema import HumanMessage
```

---

## SECTION 1: WHAT BOWJOB IS

BowJob is a CV improvement system built by our instructor (Sir).
HirePilot-AI PORTS its core logic — we do NOT rewrite it from scratch.

The two BowJob modules we port:

```
bowjob-cv-parser/parser_v3.py       → backend/agents/_cv_schema.py
                                      backend/agents/cv_parser_agent.py

cv-jd-matching/improvement_engine.py → backend/agents/_cv_improvement_schema.py
                                        backend/agents/cv_tailoring_agent.py
```

---

## SECTION 2: WHAT MUST BE CHANGED (OpenAI → Gemini)

### Pattern A — Replace API call in cv_parser_agent.py

```python
# ── REMOVE THIS (BowJob OpenAI pattern) ──────────────────────────
response = self.client.chat.completions.create(
    model=self.model,
    messages=[
        {"role": "system", "content": self.SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract info:\n\n{cv_text}"}
    ],
    tools=self.CV_FUNCTION,
    tool_choice={"type": "function", "function": {"name": "extract_cv_information"}}
)
function_args = response.choices[0].message.tool_calls[0].function.arguments
parsed_data = json.loads(function_args)

# ── REPLACE WITH THIS (HirePilot-AI Gemini pattern) ───────────────
llm, langfuse_handler = get_llm(state["session_id"], "CVParserAgent")

prompt = f"""{CV_SYSTEM_PROMPT}

Return ONLY a valid JSON object. No markdown. No code blocks. No explanation.
Just pure raw JSON.

Required top-level fields:
contact_info, title, professional_summary, work_experience,
education, projects, skills, languages, certifications,
awards_scholarships, publications, total_years_of_experience

CV TEXT:
{cv_text}"""

response = llm.invoke([HumanMessage(content=prompt)])
clean = clean_json_response(response.content)
parsed_data = json.loads(clean)
```

### Pattern B — Replace API call in cv_tailoring_agent.py (analyze)

```python
# ── REMOVE THIS (BowJob OpenAI pattern) ──────────────────────────
response = self.client.chat.completions.create(
    model=self.model,
    messages=[
        {"role": "system", "content": self.SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze CV against JD:\n{cv_text}"}
    ],
    tools=self.ANALYSIS_FUNCTION,
    tool_choice={"type": "function", "function": {"name": "analyze_cv_against_jd"}}
)
result = json.loads(response.choices[0].message.tool_calls[0].function.arguments)

# ── REPLACE WITH THIS (HirePilot-AI Gemini pattern) ───────────────
llm, langfuse_handler = get_llm(state["session_id"], "CVTailoringAgent")

prompt = f"""{SYSTEM_PROMPT}

Return ONLY a valid JSON object. No markdown. No code blocks. No explanation.

Required top-level keys:
industry, scores, skills_analysis, experience_analysis,
education_analysis, cv_sections, non_cv_sections, overall_feedback

{user_instructions_section}

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

PARSED CV DATA:
{cv_text}"""

response = llm.invoke([HumanMessage(content=prompt)])
clean = clean_json_response(response.content)
result = json.loads(clean)
```

### Helper function — clean_json_response() — add to backend/utils/helpers.py

```python
import re

def clean_json_response(text: str) -> str:
    """Strip markdown code fences from LLM JSON responses."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()
```

---

## SECTION 3: WHAT MUST NEVER BE CHANGED

Port these VERBATIM — zero modifications:

```
1. CV_FUNCTION schema (entire JSON structure from parser_v3.py)
   - All field names: contact_info, title, professional_summary, etc.
   - All null handling patterns
   - The total_years_of_experience calculation description

2. ANALYSIS_FUNCTION schema (entire JSON from improvement_engine.py)
   - cv_sections vs non_cv_sections distinction
   - All field names, descriptions, enums

3. SYSTEM_PROMPT string (from improvement_engine.py)
   - All industry detection rules
   - All output format rules

4. calculate_match_score() method — COMPLETELY DETERMINISTIC, no LLM
   - Skills: 35 points
   - Experience: 25 points
   - Education: 15 points
   - Projects: 15 points  (0=0pts, 1=5pts, 2=10pts, 3+=15pts)
   - Keywords: 10 points

5. _apply_project_guardrail() — minimum 3 projects rule
6. _add_field_paths() — frontend field path generation
7. get_improvement_suggestions() — suggestion logic
```

---

## SECTION 4: THE MOST IMPORTANT CONCEPT

```
cv_sections     = ONLY for MODIFYING content that ALREADY EXISTS in the CV
non_cv_sections = For NEW content where CV section is NULL or EMPTY

EXAMPLES:
  CV has certifications: [{...}]  → modifications → cv_sections.certifications
  CV has certifications: null     → new certs     → non_cv_sections.certifications
  CV has projects: [{...}]        → modified ones → cv_sections.projects
  CV has projects: null           → inject into   → work_experience descriptions

COPILOT: This is the most critical concept in the CV tailoring system.
Never confuse cv_sections and non_cv_sections.
```

---

## SECTION 5: SCORING WEIGHTS

```
Skills match:     35 points  (keywords in CV vs keywords in JD)
Experience:       25 points  (years of experience)
Education:        15 points  (degree level match)
Projects:         15 points  (0 projects=0, 1=5, 2=10, 3+=15)
Keywords/ATS:     10 points  (keyword density)
──────────────────────────────
TOTAL:           100 points

Ratings:
  80-100 → Excellent
  65-79  → Good
  50-64  → Fair
  0-49   → Poor
```

---

## SECTION 6: COMPLETE parser_v3.py SOURCE CODE (Port This)

```python
"""
CV Parser module using OpenAI GPT-4o-mini with Focused Schema (Experiment 3).
Extracts essential CV information with NULL values for missing data.

HIREPILOT-AI NOTE:
- Replace OpenAI calls with Gemini via get_llm()
- Replace PyPDF2 with fitz (PyMuPDF)
- Remove all cost tracking (INPUT_COST_PER_1M etc.)
- CV_FUNCTION and SYSTEM_PROMPT: copy verbatim
"""
import os
import json
import time
from typing import Dict, Any, Optional
from openai import OpenAI
import PyPDF2


class CVParserV3:
    """CV Parser using OpenAI API with focused structured schema."""

    # GPT-4o-mini pricing (per 1M tokens)
    INPUT_COST_PER_1M = 0.150
    OUTPUT_COST_PER_1M = 0.600

    # Focused CV Function Schema
    CV_FUNCTION = [{
        "type": "function",
        "function": {
            "name": "extract_cv_information",
            "description": "Extract essential information from a CV/Resume. Only include information that is explicitly present in the CV. Use null for any field where information is not available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_info": {
                        "type": "object",
                        "description": "Contact information of the candidate - extract ALL available contact details",
                        "properties": {
                            "full_name": {
                                "type": ["string", "null"],
                                "description": "Full name of the candidate or null if not available"
                            },
                            "email": {
                                "type": ["string", "null"],
                                "description": "Email address or null if not available"
                            },
                            "phone": {
                                "type": ["string", "null"],
                                "description": "Phone number or null if not available"
                            },
                            "location": {
                                "type": ["string", "null"],
                                "description": "City, State/Country. Return null if not available"
                            },
                            "address": {
                                "type": ["string", "null"],
                                "description": "Full postal/street address if provided (separate from location). Return null if not available"
                            },
                            "linkedin": {
                                "type": ["string", "null"],
                                "description": "LinkedIn profile URL or null if not available"
                            },
                            "github": {
                                "type": ["string", "null"],
                                "description": "GitHub profile URL or null if not available"
                            },
                            "website": {
                                "type": ["string", "null"],
                                "description": "Personal website or portfolio URL. Return null if not available"
                            },
                            "portfolio": {
                                "type": ["string", "null"],
                                "description": "Portfolio URL (Behance, Dribbble, etc.) if separate from website. Return null if not available"
                            },
                            "twitter": {
                                "type": ["string", "null"],
                                "description": "Twitter/X profile URL or null if not available"
                            },
                            "nationality": {
                                "type": ["string", "null"],
                                "description": "Nationality or citizenship if mentioned. Return null if not available"
                            },
                            "gender": {
                                "type": ["string", "null"],
                                "description": "Gender if explicitly mentioned. Return null if not available"
                            },
                            "date_of_birth": {
                                "type": ["string", "null"],
                                "description": "Date of birth if mentioned (any format). Return null if not available"
                            },
                            "other_links": {
                                "type": ["array", "null"],
                                "description": "Array of other profile/social links not covered above (Medium, StackOverflow, etc.)",
                                "items": {
                                    "type": "string"
                                }
                            }
                        }
                    },
                    "title": {
                        "type": ["string", "null"],
                        "description": "Current job title, professional headline, or desired position mentioned in the CV. Return null if not explicitly stated"
                    },
                    "professional_summary": {
                        "type": ["string", "array", "null"],
                        "description": "Professional summary, objective, or about section from the CV. If written as bullet points or multiple paragraphs, return as array of strings. If written as single paragraph, return as string. Return null if not present",
                        "items": {
                            "type": "string"
                        }
                    },
                    "work_experience": {
                        "type": ["array", "null"],
                        "description": "Array of work experience entries. Return null if no work experience is mentioned",
                        "items": {
                            "type": "object",
                            "properties": {
                                "job_title": {
                                    "type": ["string", "null"],
                                    "description": "Job title/position"
                                },
                                "company": {
                                    "type": ["string", "null"],
                                    "description": "Company/organization name"
                                },
                                "location": {
                                    "type": ["string", "null"],
                                    "description": "Job location (city, country) or null"
                                },
                                "start_date": {
                                    "type": ["string", "null"],
                                    "description": "Start date in YYYY-MM-DD format. If month not available use YYYY-01-01. Return null if not available"
                                },
                                "end_date": {
                                    "type": ["string", "null"],
                                    "description": "End date in YYYY-MM-DD format. Use 'Present' or 'Current' if still employed. If month not available use YYYY-12-31. Return null if not available"
                                },
                                "description": {
                                    "type": ["string", "array", "null"],
                                    "description": "Job responsibilities, achievements, and key points. If listed as bullet points or separate lines, return as array of strings (each bullet/line as separate element). If written as a continuous paragraph, return as single string. Return null if not provided",
                                    "items": {
                                        "type": "string"
                                    }
                                }
                            }
                        }
                    },
                    "education": {
                        "type": ["array", "null"],
                        "description": "Array of education entries. Return null if no education is mentioned",
                        "items": {
                            "type": "object",
                            "properties": {
                                "degree": {
                                    "type": ["string", "null"],
                                    "description": "Degree name (e.g., Bachelor of Science, Master of Arts, MBA, Ph.D.)"
                                },
                                "field_of_study": {
                                    "type": ["string", "null"],
                                    "description": "Major/field of study (e.g., Computer Science, Business Administration)"
                                },
                                "institution": {
                                    "type": ["string", "null"],
                                    "description": "University or institution name"
                                },
                                "location": {
                                    "type": ["string", "null"],
                                    "description": "Institution location or null"
                                },
                                "start_date": {
                                    "type": ["string", "null"],
                                    "description": "Start date in YYYY-MM-DD format or YYYY if only year available"
                                },
                                "end_date": {
                                    "type": ["string", "null"],
                                    "description": "End date in YYYY-MM-DD format or YYYY if only year available. Use 'Present' if currently studying"
                                },
                                "gpa": {
                                    "type": ["string", "null"],
                                    "description": "GPA or grade if mentioned, otherwise null"
                                }
                            }
                        }
                    },
                    "projects": {
                        "type": ["array", "null"],
                        "description": "Array of projects. Return null if no projects are mentioned",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": ["string", "null"],
                                    "description": "Project name or title"
                                },
                                "description": {
                                    "type": ["string", "array", "null"],
                                    "description": "Project description, objectives, and outcomes. If listed as bullet points or separate lines, return as array of strings (each bullet/line as separate element). If written as a continuous paragraph, return as single string. Return null if not provided",
                                    "items": {
                                        "type": "string"
                                    }
                                },
                                "technologies": {
                                    "type": ["array", "null"],
                                    "description": "Technologies, tools, or frameworks used in the project",
                                    "items": {
                                        "type": "string"
                                    }
                                },
                                "date": {
                                    "type": ["string", "null"],
                                    "description": "Project date or duration (e.g., '2023', 'Jan 2023 - Mar 2023')"
                                },
                                "url": {
                                    "type": ["string", "null"],
                                    "description": "Project URL or repository link if available"
                                }
                            }
                        }
                    },
                    "skills": {
                        "type": ["array", "null"],
                        "description": "ALL skills from the CV in a single flat array. Extract EVERY skill from ANY section - skills section, interests, hobbies, work experience descriptions, projects, certifications, anywhere. Include technical skills, soft skills, tools, platforms, methodologies, domain skills - everything. Do NOT miss any skill mentioned anywhere in the CV.",
                        "items": {
                            "type": "string"
                        }
                    },
                    "languages": {
                        "type": ["array", "null"],
                        "description": "Spoken/written languages with proficiency level if mentioned",
                        "items": {
                            "type": "object",
                            "properties": {
                                "language": {
                                    "type": "string"
                                },
                                "proficiency": {
                                    "type": ["string", "null"],
                                    "description": "Proficiency level (e.g., Native, Fluent, Professional, Intermediate, Basic) or null"
                                }
                            }
                        }
                    },
                    "certifications": {
                        "type": ["array", "null"],
                        "description": "Array of certifications. Return null if no certifications are mentioned",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": ["string", "null"],
                                    "description": "Certification name"
                                },
                                "issuing_organization": {
                                    "type": ["string", "null"],
                                    "description": "Organization that issued the certification"
                                },
                                "issue_date": {
                                    "type": ["string", "null"],
                                    "description": "Date issued in YYYY-MM-DD or YYYY format"
                                },
                                "expiry_date": {
                                    "type": ["string", "null"],
                                    "description": "Expiry date if applicable, otherwise null"
                                },
                                "credential_id": {
                                    "type": ["string", "null"],
                                    "description": "Credential ID or certificate number if available"
                                }
                            }
                        }
                    },
                    "awards_scholarships": {
                        "type": ["array", "null"],
                        "description": "Array of awards, honors, or scholarships. Return null if none are mentioned",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": ["string", "null"],
                                    "description": "Award or scholarship title"
                                },
                                "issuer": {
                                    "type": ["string", "null"],
                                    "description": "Organization or institution that granted the award"
                                },
                                "date": {
                                    "type": ["string", "null"],
                                    "description": "Date received (YYYY or YYYY-MM format)"
                                },
                                "description": {
                                    "type": ["string", "array", "null"],
                                    "description": "Brief description if available. If listed as bullet points or separate lines, return as array. If paragraph, return as string. Return null if not provided",
                                    "items": {
                                        "type": "string"
                                    }
                                }
                            }
                        }
                    },
                    "publications": {
                        "type": ["array", "null"],
                        "description": "Array of publications, research papers, or articles. Return null if none are mentioned",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": ["string", "null"],
                                    "description": "Publication title"
                                },
                                "authors": {
                                    "type": ["string", "null"],
                                    "description": "Authors (including the candidate)"
                                },
                                "publisher": {
                                    "type": ["string", "null"],
                                    "description": "Publisher, journal, or conference name"
                                },
                                "date": {
                                    "type": ["string", "null"],
                                    "description": "Publication date (YYYY or YYYY-MM format)"
                                },
                                "url": {
                                    "type": ["string", "null"],
                                    "description": "URL or DOI if available"
                                }
                            }
                        }
                    },
                    "total_years_of_experience": {
                        "type": ["number", "null"],
                        "description": "Calculate total years of professional work experience. Rules: 1) Find earliest start_date across all work experiences. 2) Calculate each position duration. 3) If overlapping positions exist, count that period only once. 4) Identify and SUBTRACT gap periods between positions. 5) Return decimal number (e.g., 3.5 for 3 years 6 months). 6) Return null if insufficient data. Example: worked 2018-2020, gap 2020-2021, worked 2021-Present(2025) = 2 + 4 = 6 years (gap excluded)"
                    }
                },
                "required": []
            }
        }
    }]

    SYSTEM_PROMPT = """You are an expert CV/Resume parser. Your job is to extract ALL content from the CV and map it to the output schema. DO NOT MISS ANY CONTENT.

CRITICAL RULE: CAPTURE EVERYTHING
- Parse EVERY section of the CV
- Map ALL content to the nearest matching output field
- Do NOT skip or ignore any section - find a place for it in the schema

SECTION MAPPING - Map by CONTENT, not section title:
| CV Section | Maps To |
|------------|---------|
| Skills, Technical Skills, Core Competencies, Expertise | skills (flat array) |
| Interests, Hobbies (if professional/field-related) | skills |
| Tools, Technologies, Platforms | skills |
| Soft Skills, Interpersonal Skills | skills |
| Projects, Personal Projects, Side Projects | projects |
| Activities, Extracurriculars (if project-like) | projects |
| Volunteer Experience, Community Service | work_experience |
| Internships | work_experience |
| Achievements, Honors, Awards | awards_scholarships |
| Courses, Training, Workshops | certifications |
| Research, Papers, Publications | publications |
| Languages, Language Skills | languages |

SKILLS - SINGLE FLAT ARRAY:
- Put ALL skills into ONE array: technical, soft, tools, platforms, methodologies, domain skills
- Extract skills from EVERYWHERE: skills section, work descriptions, projects, interests, hobbies
- Example: ["Python", "AWS", "Leadership", "Agile", "Docker", "Communication", "Machine Learning"]

MAPPING RULES:
1. Analyze CONTENT to decide where it belongs, not just the section title
2. "Interests: Building ML models, Contributing to open source" -> skills + projects
3. "Hobbies: Team captain of soccer team" -> skills (Leadership, Teamwork)
4. "Volunteer: Taught coding to kids at NGO" -> work_experience
5. Only skip content that is purely personal with zero professional relevance
6. When in doubt, include it - better to capture than to miss

OTHER RULES:
1. Do NOT make up or infer information not in the CV
2. Return null only if a field is genuinely not present
3. Extract information exactly as written
4. For dates, use YYYY-MM-DD format where possible
5. Calculate total_years_of_experience excluding gaps

FORMATTING FOR DESCRIPTIONS:
- BULLET POINTS -> return as ARRAY
- MULTIPLE LINES -> return as ARRAY
- SINGLE PARAGRAPH -> return as STRING"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided.")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """Extract text content from a PDF file using PyPDF2."""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {str(e)}")
            return None

    def parse_cv_text(self, cv_text: str, filename: str = "unknown") -> Optional[Dict[str, Any]]:
        """Parse CV text using OpenAI API with focused schema."""
        try:
            print(f"Processing: {filename}")
            start_time = time.time()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Extract the essential information from this CV. Only include information that is clearly present. Use null for missing fields:\n\n{cv_text}"}
                ],
                tools=self.CV_FUNCTION,
                tool_choice={"type": "function", "function": {"name": "extract_cv_information"}}
            )

            end_time = time.time()
            processing_time = end_time - start_time

            if response.choices[0].message.tool_calls:
                function_args = response.choices[0].message.tool_calls[0].function.arguments
                parsed_data = json.loads(function_args)

                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens

                input_cost = (input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
                output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
                total_cost = input_cost + output_cost

                print(f"Successfully parsed {filename}")
                print(f"Time: {processing_time:.2f}s | Tokens: {total_tokens:,}")

                return {
                    'data': parsed_data,
                    'metrics': {
                        'processing_time': processing_time,
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'total_tokens': total_tokens,
                        'cost': total_cost
                    }
                }
            else:
                print(f"No data extracted for {filename}")
                return None

        except Exception as e:
            print(f"Error parsing {filename}: {str(e)}")
            return None

    def parse_cv(self, pdf_path: str, filename: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Parse a CV PDF file end-to-end."""
        if filename is None:
            filename = os.path.basename(pdf_path)
        cv_text = self.extract_text_from_pdf(pdf_path)
        if cv_text is None:
            return None
        return self.parse_cv_text(cv_text, filename)
```

---

## SECTION 7: COMPLETE improvement_engine.py SOURCE CODE (Port This)

```python
"""
CV Improvement Engine using OpenAI GPT-4o-mini.
Analyzes CVs against Job Descriptions and provides comprehensive improvement suggestions.

HIREPILOT-AI NOTE:
- Replace OpenAI calls with Gemini via get_llm()
- Keep ALL schemas, prompts, and logic verbatim
- Keep calculate_match_score() completely unchanged (no LLM used there)
- Keep _apply_project_guardrail(), _add_field_paths(), get_improvement_suggestions() verbatim
"""

import json
from typing import Dict, Any, Optional
from openai import OpenAI


class CVImprovementEngine:
    """Engine for CV-JD matching and improvement suggestions."""

    ANALYSIS_FUNCTION = [{
        "type": "function",
        "function": {
            "name": "analyze_cv_against_jd",
            "description": "Analyze a CV against a Job Description with industry-specific tone",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "Detected industry/niche (e.g., 'technology', 'finance', 'healthcare', 'marketing')"
                    },
                    "scores": {
                        "type": "object",
                        "properties": {
                            "current_match_score": {"type": "number"},
                            "potential_score_after_changes": {"type": "number"},
                            "rating": {"type": "string", "enum": ["Poor", "Fair", "Good", "Excellent"]},
                            "breakdown": {
                                "type": "object",
                                "properties": {
                                    "skills_score": {"type": "number"},
                                    "experience_score": {"type": "number"},
                                    "education_score": {"type": "number"},
                                    "projects_score": {"type": "number"}
                                }
                            }
                        }
                    },
                    "skills_analysis": {
                        "type": "object",
                        "properties": {
                            "matched_skills": {"type": "array", "items": {"type": "string"}},
                            "missing_skills": {"type": "array", "items": {"type": "string"}},
                            "nice_to_have_missing": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "experience_analysis": {
                        "type": "object",
                        "properties": {
                            "years_required": {"type": "string"},
                            "years_in_cv": {"type": "number"},
                            "is_sufficient": {"type": "boolean"},
                            "gap_description": {"type": ["string", "null"]}
                        }
                    },
                    "education_analysis": {
                        "type": "object",
                        "properties": {
                            "required_education": {"type": ["string", "null"]},
                            "cv_education": {"type": ["string", "null"]},
                            "is_match": {"type": "boolean"},
                            "gap_description": {"type": ["string", "null"]}
                        }
                    },
                    "cv_sections": {
                        "type": "object",
                        "description": "ONLY MODIFICATIONS to sections that HAVE EXISTING CONTENT in CV. If a section is null/empty/missing in CV, do NOT put new content here - put it in non_cv_sections instead.",
                        "properties": {
                            "title": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"},
                                    "original_content": {"type": "string"},
                                    "tag": {"type": "string", "enum": ["modified"]},
                                    "reason": {"type": "string"}
                                }
                            },
                            "professional_summary": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"},
                                    "original_content": {"type": "string"},
                                    "tag": {"type": "string", "enum": ["modified"]},
                                    "reason": {"type": "string"}
                                }
                            },
                            "work_experience": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "job_title": {"type": "string"},
                                        "company": {"type": "string"},
                                        "descriptions": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "content": {"type": "string"},
                                                    "original_content": {"type": "string"},
                                                    "tag": {"type": "string", "enum": ["modified", "new"]},
                                                    "reason": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            },
                            "skills": {
                                "type": "array",
                                "description": "Only NEW skills to add (not already in CV).",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "content": {"type": "string"},
                                        "tag": {"type": "string", "enum": ["new"]},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "projects": {
                                "type": "array",
                                "description": "MODIFIED existing projects with JD keywords naturally injected.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "original_name": {"type": "string"},
                                        "original_description": {"type": "string"},
                                        "technologies": {"type": "array", "items": {"type": "string"}},
                                        "tag": {"type": "string", "enum": ["modified"]},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "certifications": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "issuer": {"type": "string"},
                                        "tag": {"type": "string", "enum": ["new"]},
                                        "reason": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "non_cv_sections": {
                        "type": "object",
                        "description": "NEW content for sections that are NULL, EMPTY, or MISSING in CV.",
                        "properties": {
                            "professional_summary": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"},
                                    "reason": {"type": "string"}
                                }
                            },
                            "skills": {
                                "type": "array",
                                "description": "If CV has NO skills - put ALL new skills HERE as flat array",
                                "items": {"type": "string"}
                            },
                            "certifications": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "issuer": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "projects": {
                                "type": "array",
                                "description": "NEW projects when CV HAS a projects section. Add 1-2 NEW projects to reach MINIMUM 3 total.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "technologies": {"type": "array", "items": {"type": "string"}},
                                        "reason": {"type": "string"},
                                        "tag": {"type": "string", "enum": ["new"]}
                                    }
                                }
                            },
                            "awards": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "issuer": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "languages": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "language": {"type": "string"},
                                        "proficiency": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "overall_feedback": {
                        "type": "object",
                        "properties": {
                            "strengths": {"type": "array", "items": {"type": "string"}},
                            "weaknesses": {"type": "array", "items": {"type": "string"}},
                            "quick_wins": {"type": "array", "items": {"type": "string"}},
                            "interview_tips": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "writing_quality": {
                        "type": "object",
                        "properties": {
                            "grammar_issues": {"type": "array", "items": {"type": "object"}},
                            "tone_analysis": {"type": "object"},
                            "passive_voice_instances": {"type": "array", "items": {"type": "object"}},
                            "weak_phrases": {"type": "array", "items": {"type": "object"}},
                            "action_verbs": {"type": "object"}
                        }
                    },
                    "ats_optimization": {
                        "type": "object",
                        "properties": {
                            "ats_score": {"type": "number"},
                            "keyword_density": {"type": "object"},
                            "formatting_issues": {"type": "array", "items": {"type": "string"}},
                            "section_headers": {"type": "object"}
                        }
                    },
                    "industry_vocabulary": {
                        "type": "object",
                        "properties": {
                            "current_industry_terms": {"type": "array", "items": {"type": "string"}},
                            "missing_industry_terms": {"type": "array", "items": {"type": "string"}},
                            "buzzwords_to_add": {"type": "array", "items": {"type": "string"}},
                            "outdated_terms": {"type": "array", "items": {"type": "object"}}
                        }
                    },
                    "quantification_opportunities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "current_text": {"type": "string"},
                                "location": {"type": "string"},
                                "suggestion": {"type": "string"},
                                "example_metrics": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    },
                    "red_flags": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "issue": {"type": "string"},
                                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                                "recommendation": {"type": "string"}
                            }
                        }
                    },
                    "length_analysis": {
                        "type": "object",
                        "properties": {
                            "current_length": {"type": "string"},
                            "recommended_length": {"type": "string"},
                            "sections_to_trim": {"type": "array", "items": {"type": "string"}},
                            "sections_to_expand": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "required": ["industry", "scores", "skills_analysis", "experience_analysis",
                             "education_analysis", "cv_sections", "non_cv_sections", "overall_feedback",
                             "writing_quality", "ats_optimization", "industry_vocabulary"]
            }
        }
    }]

    SYSTEM_PROMPT = """You are an expert HR analyst and CV optimization specialist.
Analyze the CV against the Job Description and provide ONLY modifications and new content.

CRITICAL RULES:

1. DETECT INDUSTRY & SUB-DOMAIN - ADAPT TONE:
   Identify MAIN INDUSTRY + SUB-DOMAIN from JD. Use domain-specific terminology.
   TECHNOLOGY: "scalable architecture", "CI/CD", "microservices", "MLOps", etc.
   FINANCE: "deal flow", "M&A", "valuation models", "VaR", etc.
   HEALTHCARE: "patient outcomes", "clinical trials", "EHR/EMR", etc.
   MARKETING: "SEO/SEM", "conversion optimization", "CAC/LTV", etc.

2. OUTPUT ONLY CHANGES - DO NOT RETURN UNTOUCHED CONTENT:
   RETURN: "modified" (content that was improved) and "new" (completely new content)
   DO NOT RETURN: Original content with no modification

3. CRITICAL: cv_sections vs non_cv_sections DISTINCTION:
   cv_sections = ONLY for MODIFYING existing content that HAS DATA in CV
   non_cv_sections = For NEW content where CV section is NULL, EMPTY, or MISSING

   EXAMPLES:
   - CV has "certifications": null -> Put new certs in non_cv_sections.certifications
   - CV has "certifications": [{...}] -> Put modified certs in cv_sections.certifications
   - CV has "awards_scholarships": null -> Put suggested awards in non_cv_sections.awards

4. FOR MODIFIED CONTENT - ALWAYS INCLUDE original_content:
   tag="modified" MUST have: content (new), original_content (exact original), reason

5. PROJECTS - MINIMUM 3 REQUIRED:
   SCENARIO A - CV HAS projects section:
     Modify 1-2 existing -> cv_sections.projects
     Add 1-2 NEW ones -> non_cv_sections.projects
     TOTAL must be >= 3

   SCENARIO B - CV has NO projects section:
     Generate 3+ project-style achievements
     Inject as NEW bullet points into cv_sections.work_experience descriptions

   NATURAL KEYWORD INJECTION:
   Title: Include 1-2 keywords naturally
   Description: Weave in 3-5 keywords in context
   Do NOT keyword-stuff

6. SKILLS: Only return NEW skills (JD keywords to add, not already in CV)

7. TWO SCORES:
   current_match_score: Based on CV as-is
   potential_score_after_changes: Projected if all changes accepted

SCORING WEIGHTS:
- Technical Skills: 35%
- Experience: 25%
- Education: 15%
- Projects: 15%
- Keywords/Soft Skills: 10%"""

    CHAT_SYSTEM_PROMPT = """You are a helpful CV improvement assistant. Use industry-specific terminology based on the job context."""

    SCORE_WEIGHTS = {
        "skills": 35,
        "experience": 25,
        "education": 15,
        "projects": 15,
        "keywords": 10
    }

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def calculate_match_score(
        self,
        parsed_cv: Dict[str, Any],
        job_description: str,
        jd_requirements: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        DETERMINISTIC score — NO LLM used here. Port VERBATIM.

        Scoring Formula (100 points total):
        - Skills: 35 points (matched_skills / required_skills * 35)
        - Experience: 25 points (cv_years / required_years * 25, capped at 25)
        - Education: 15 points (degree match level)
        - Projects: 15 points (0=0, 1=5, 2=10, 3+=15)
        - Keywords: 10 points (keywords_found / total_keywords * 10)
        """
        import re

        cv_text = json.dumps(parsed_cv).lower()
        jd_lower = job_description.lower()

        jd_keywords = set()
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9+#.-]*[a-zA-Z0-9]\b|\b[A-Z]{2,}\b', job_description)
        for word in words:
            if len(word) > 2:
                jd_keywords.add(word.lower())

        stop_words = {'the', 'and', 'for', 'with', 'our', 'you', 'your', 'will', 'are', 'have',
                      'has', 'been', 'being', 'was', 'were', 'can', 'could', 'should', 'would',
                      'may', 'might', 'must', 'shall', 'this', 'that', 'these', 'those', 'what',
                      'which', 'who', 'whom', 'where', 'when', 'why', 'how', 'all', 'each',
                      'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'than',
                      'too', 'very', 'just', 'also', 'only', 'own', 'same', 'into', 'over',
                      'after', 'before', 'between', 'under', 'again', 'further', 'then', 'once',
                      'here', 'there', 'about', 'above', 'below', 'from', 'down', 'out', 'off',
                      'through', 'during', 'including', 'include', 'includes', 'etc', 'ability',
                      'able', 'work', 'working', 'worked', 'team', 'teams', 'role', 'roles',
                      'job', 'jobs', 'position', 'positions', 'company', 'companies',
                      'organization', 'organizations', 'looking', 'seeking', 'ideal', 'candidate',
                      'candidates', 'opportunity', 'opportunities'}

        jd_keywords = {w for w in jd_keywords if w not in stop_words and len(w) > 2}

        # SKILLS SCORE (35 points)
        cv_skills = parsed_cv.get("skills", []) or []
        if isinstance(cv_skills, dict):
            all_skills = []
            for key, val in cv_skills.items():
                if isinstance(val, list):
                    all_skills.extend(val)
            cv_skills = all_skills

        cv_skills_lower = [s.lower() if isinstance(s, str) else str(s).lower() for s in cv_skills]
        cv_skills_text = ' '.join(cv_skills_lower)

        skills_matched = 0
        for kw in jd_keywords:
            if kw in cv_skills_text or kw in cv_text:
                skills_matched += 1

        skills_score = min(35, (skills_matched / max(len(jd_keywords), 1)) * 35) if jd_keywords else 20

        # EXPERIENCE SCORE (25 points)
        cv_years = parsed_cv.get("total_years_of_experience", 0) or 0

        years_patterns = [
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience',
            r'minimum\s*(?:of)?\s*(\d+)\s*(?:years?|yrs?)',
            r'at\s*least\s*(\d+)\s*(?:years?|yrs?)',
            r'(\d+)\s*-\s*\d+\s*(?:years?|yrs?)',
        ]

        required_years = 0
        for pattern in years_patterns:
            match = re.search(pattern, jd_lower)
            if match:
                required_years = int(match.group(1))
                break

        if required_years > 0:
            experience_ratio = min(cv_years / required_years, 1.5)
            experience_score = min(25, experience_ratio * 25)
        else:
            experience_score = min(25, cv_years * 2.5) if cv_years > 0 else 10

        # EDUCATION SCORE (15 points)
        cv_education = parsed_cv.get("education", []) or []
        has_degree = len(cv_education) > 0
        degree_keywords = ['bachelor', 'master', 'phd', 'doctorate', 'degree', 'mba', 'bs', 'ms', 'ba', 'ma']
        jd_requires_degree = any(dk in jd_lower for dk in degree_keywords)

        if has_degree:
            education_score = 15
        elif not jd_requires_degree:
            education_score = 12
        else:
            education_score = 5

        # PROJECTS SCORE (15 points)
        cv_projects = parsed_cv.get("projects", []) or []
        project_count = len(cv_projects) if isinstance(cv_projects, list) else 0

        if project_count >= 3:
            projects_score = 15
        elif project_count == 2:
            projects_score = 10
        elif project_count == 1:
            projects_score = 5
        else:
            projects_score = 0

        # KEYWORDS SCORE (10 points)
        keywords_found = 0
        for kw in jd_keywords:
            if kw in cv_text:
                keywords_found += 1

        keywords_score = min(10, (keywords_found / max(len(jd_keywords), 1)) * 10) if jd_keywords else 5

        # TOTAL
        total_score = round(skills_score + experience_score + education_score + projects_score + keywords_score)

        if total_score >= 80:
            rating = "Excellent"
        elif total_score >= 65:
            rating = "Good"
        elif total_score >= 50:
            rating = "Fair"
        else:
            rating = "Poor"

        return {
            "current_match_score": total_score,
            "rating": rating,
            "breakdown": {
                "skills_score": round(skills_score, 1),
                "experience_score": round(experience_score, 1),
                "education_score": round(education_score, 1),
                "projects_score": round(projects_score, 1),
                "keywords_score": round(keywords_score, 1)
            },
            "details": {
                "jd_keywords_count": len(jd_keywords),
                "keywords_matched": keywords_found,
                "cv_years": cv_years,
                "required_years": required_years,
                "project_count": project_count,
                "skills_count": len(cv_skills)
            }
        }

    def get_improvement_suggestions(
        self,
        parsed_cv: Dict[str, Any],
        job_description: str
    ) -> Dict[str, Any]:
        """Generate actionable suggestions based on score gaps. Port VERBATIM."""
        scores = self.calculate_match_score(parsed_cv, job_description)
        breakdown = scores["breakdown"]
        details = scores["details"]

        suggestions = []
        priority = 1

        if breakdown["projects_score"] < 15:
            project_count = details["project_count"]
            needed = 3 - project_count
            if needed > 0:
                suggestions.append({
                    "priority": priority,
                    "section": "projects",
                    "current_score": breakdown["projects_score"],
                    "max_score": 15,
                    "potential_gain": 15 - breakdown["projects_score"],
                    "action": f"Add {needed} more project(s) to reach 3 total",
                    "hint": "Ask me to 'add a project about [technology from JD]'",
                    "impact": "high"
                })
                priority += 1

        if breakdown["skills_score"] < 28:
            suggestions.append({
                "priority": priority,
                "section": "skills",
                "current_score": breakdown["skills_score"],
                "max_score": 35,
                "potential_gain": min(10, 35 - breakdown["skills_score"]),
                "action": f"Add more JD-relevant skills ({details['keywords_matched']}/{details['jd_keywords_count']} keywords matched)",
                "hint": "Ask me to 'add missing skills from the JD'",
                "impact": "high"
            })
            priority += 1

        if breakdown["keywords_score"] < 7:
            suggestions.append({
                "priority": priority,
                "section": "work_experience",
                "current_score": breakdown["keywords_score"],
                "max_score": 10,
                "potential_gain": 10 - breakdown["keywords_score"],
                "action": "Inject more JD keywords into work experience descriptions",
                "hint": "Ask me to 'optimize my work experience for ATS'",
                "impact": "medium"
            })
            priority += 1

        if breakdown["experience_score"] < 20:
            if details["cv_years"] < details["required_years"]:
                suggestions.append({
                    "priority": priority,
                    "section": "work_experience",
                    "current_score": breakdown["experience_score"],
                    "max_score": 25,
                    "potential_gain": 5,
                    "action": f"Experience gap: you have {details['cv_years']} years, JD wants {details['required_years']}+",
                    "hint": "Ask me to 'emphasize transferable skills'",
                    "impact": "medium"
                })
                priority += 1

        if breakdown["education_score"] < 15:
            suggestions.append({
                "priority": priority,
                "section": "education",
                "current_score": breakdown["education_score"],
                "max_score": 15,
                "potential_gain": 15 - breakdown["education_score"],
                "action": "Add relevant education or certifications",
                "hint": "Ask me to 'suggest certifications for this role'",
                "impact": "low"
            })
            priority += 1

        total_potential = sum(s["potential_gain"] for s in suggestions)

        return {
            "current_score": scores["current_match_score"],
            "potential_score": min(95, scores["current_match_score"] + total_potential),
            "rating": scores["rating"],
            "suggestions": suggestions[:5],
            "summary": self._generate_suggestion_summary(suggestions) if suggestions else "Your CV is well-optimized for this role!"
        }

    def _generate_suggestion_summary(self, suggestions: list) -> str:
        """Generate human-readable summary. Port VERBATIM."""
        if not suggestions:
            return "No major improvements needed."
        top = suggestions[0]
        if top["section"] == "projects":
            return f"Focus on adding projects to gain up to {top['potential_gain']} points."
        elif top["section"] == "skills":
            return f"Add more JD-relevant skills to gain up to {top['potential_gain']} points."
        elif top["section"] == "work_experience":
            return f"Enhance work experience with JD keywords to improve your score."
        else:
            return f"Focus on {top['section']} to improve your match score."

    def _count_projects(self, result: Dict[str, Any], parsed_cv: Dict[str, Any]) -> int:
        """Count total projects in analysis response. Port VERBATIM."""
        cv_has_projects = parsed_cv.get("projects") not in [None, []]
        if cv_has_projects:
            modified = len(result.get("cv_sections", {}).get("projects", []))
            new = len(result.get("non_cv_sections", {}).get("projects", []))
            return modified + new
        else:
            count = 0
            for job in result.get("cv_sections", {}).get("work_experience", []):
                for desc in job.get("descriptions", []):
                    if desc.get("tag") == "new":
                        count += 1
            return count

    def _generate_missing_projects(
        self,
        parsed_cv: Dict[str, Any],
        job_title: str,
        job_description: str,
        needed: int,
        cv_has_projects: bool
    ) -> list:
        """Generate missing projects. IN HIREPILOT-AI: replace OpenAI call with Gemini."""
        prompt = f"""Generate EXACTLY {needed} highly relevant project(s) for this job application.

JOB TITLE: {job_title}
JOB DESCRIPTION: {job_description}

REQUIREMENTS:
1. Each project must target a SPECIFIC JD requirement
2. Include realistic metrics and outcomes
3. Naturally inject 3-5 JD keywords into each description
4. Make projects impressive and recruiter-attractive

Return ONLY a JSON array of {needed} project(s) with fields:
name, description, technologies, reason, tag (always "new")"""

        # IN HIREPILOT-AI: replace below with Gemini call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a CV optimization expert. Generate realistic, impressive projects."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        try:
            content = response.choices[0].message.content
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "projects" in data:
                return data["projects"]
            else:
                return list(data.values())[0] if data else []
        except:
            return []

    def _inject_projects_to_work_exp(self, result: Dict[str, Any], projects: list) -> None:
        """Inject projects as new descriptions into work experience. Port VERBATIM."""
        work_exp = result.get("cv_sections", {}).get("work_experience", [])
        if not work_exp:
            if "cv_sections" not in result:
                result["cv_sections"] = {}
            if "work_experience" not in result["cv_sections"]:
                result["cv_sections"]["work_experience"] = []
            work_exp = result["cv_sections"]["work_experience"]

        for project in projects:
            desc = {
                "content": f"{project.get('name', 'Project')}: {project.get('description', '')}",
                "tag": "new",
                "reason": project.get("reason", "Generated to meet JD requirements")
            }
            if work_exp:
                if "descriptions" not in work_exp[0]:
                    work_exp[0]["descriptions"] = []
                work_exp[0]["descriptions"].append(desc)
            else:
                work_exp.append({
                    "job_title": "Relevant Experience",
                    "company": "Various Projects",
                    "descriptions": [desc]
                })

    def _apply_project_guardrail(
        self,
        result: Dict[str, Any],
        parsed_cv: Dict[str, Any],
        job_title: str,
        job_description: str
    ) -> Dict[str, Any]:
        """Ensure minimum 3 projects exist. Port VERBATIM (replace OpenAI in _generate_missing_projects)."""
        project_count = self._count_projects(result, parsed_cv)
        cv_has_projects = parsed_cv.get("projects") not in [None, []]

        if project_count < 3:
            missing = 3 - project_count
            additional_projects = self._generate_missing_projects(
                parsed_cv, job_title, job_description, missing, cv_has_projects
            )
            if additional_projects:
                if cv_has_projects:
                    if "non_cv_sections" not in result:
                        result["non_cv_sections"] = {}
                    if "projects" not in result["non_cv_sections"]:
                        result["non_cv_sections"]["projects"] = []
                    result["non_cv_sections"]["projects"].extend(additional_projects)
                else:
                    self._inject_projects_to_work_exp(result, additional_projects)

        return result

    def _add_field_paths(self, result: Dict[str, Any], parsed_cv: Dict[str, Any]) -> Dict[str, Any]:
        """Add field_path to each recommendation so frontend knows where to apply changes. Port VERBATIM."""
        cv_sections = result.get("cv_sections", {})
        non_cv_sections = result.get("non_cv_sections", {})

        if "title" in cv_sections and cv_sections["title"]:
            cv_sections["title"]["field_path"] = "title"

        if "professional_summary" in cv_sections and cv_sections["professional_summary"]:
            cv_sections["professional_summary"]["field_path"] = "professional_summary"

        if "work_experience" in cv_sections:
            for job_idx, job in enumerate(cv_sections.get("work_experience", [])):
                job["job_index"] = job_idx
                if "descriptions" in job:
                    cv_work_exp = parsed_cv.get("work_experience", [])
                    existing_desc_count = 0
                    if job_idx < len(cv_work_exp):
                        existing_descs = cv_work_exp[job_idx].get("description", [])
                        if isinstance(existing_descs, list):
                            existing_desc_count = len(existing_descs)
                    new_desc_idx = existing_desc_count
                    for desc_idx, desc in enumerate(job["descriptions"]):
                        if desc.get("tag") == "modified" and desc.get("original_content"):
                            if job_idx < len(cv_work_exp):
                                cv_descs = cv_work_exp[job_idx].get("description", [])
                                if isinstance(cv_descs, list):
                                    for i, cv_desc in enumerate(cv_descs):
                                        if cv_desc == desc.get("original_content"):
                                            desc["field_path"] = f"work_experience[{job_idx}].description[{i}]"
                                            break
                                    else:
                                        desc["field_path"] = f"work_experience[{job_idx}].description[{desc_idx}]"
                        elif desc.get("tag") == "new":
                            desc["field_path"] = f"work_experience[{job_idx}].description[{new_desc_idx}]"
                            new_desc_idx += 1

        if "skills" in cv_sections:
            cv_skills = parsed_cv.get("skills", [])
            existing_count = len(cv_skills) if isinstance(cv_skills, list) else 0
            for idx, skill in enumerate(cv_sections.get("skills", [])):
                skill["field_path"] = f"skills[{existing_count + idx}]"

        if "projects" in cv_sections:
            for idx, project in enumerate(cv_sections.get("projects", [])):
                cv_projects = parsed_cv.get("projects", [])
                if cv_projects and project.get("original_name"):
                    for i, cv_proj in enumerate(cv_projects):
                        if cv_proj.get("name") == project.get("original_name"):
                            project["field_path"] = f"projects[{i}]"
                            break
                    else:
                        project["field_path"] = f"projects[{idx}]"
                else:
                    project["field_path"] = f"projects[{idx}]"

        if "projects" in non_cv_sections:
            cv_projects = parsed_cv.get("projects", [])
            existing_count = len(cv_projects) if isinstance(cv_projects, list) else 0
            cv_section_projects = len(cv_sections.get("projects", []))
            start_idx = existing_count + cv_section_projects
            for idx, project in enumerate(non_cv_sections.get("projects", [])):
                project["field_path"] = f"projects[{start_idx + idx}]"

        if "certifications" in non_cv_sections:
            cv_certs = parsed_cv.get("certifications", [])
            existing_count = len(cv_certs) if isinstance(cv_certs, list) else 0
            for idx, cert in enumerate(non_cv_sections.get("certifications", [])):
                cert["field_path"] = f"certifications[{existing_count + idx}]"

        if "skills" in non_cv_sections:
            for idx, skill in enumerate(non_cv_sections.get("skills", [])):
                if isinstance(skill, dict):
                    skill["field_path"] = f"skills[{idx}]"
                elif isinstance(skill, str):
                    non_cv_sections["skills"][idx] = {
                        "content": skill,
                        "field_path": f"skills[{idx}]",
                        "tag": "new"
                    }

        if "awards" in non_cv_sections:
            for idx, award in enumerate(non_cv_sections.get("awards", [])):
                award["field_path"] = f"awards_scholarships[{idx}]"

        if "professional_summary" in non_cv_sections and non_cv_sections["professional_summary"]:
            non_cv_sections["professional_summary"]["field_path"] = "professional_summary"

        return result

    def analyze(
        self,
        parsed_cv: Dict[str, Any],
        job_title: str,
        job_description: str,
        options: Dict[str, bool],
        instructions: str = None
    ) -> Dict[str, Any]:
        """Main analysis function. IN HIREPILOT-AI: replace OpenAI tool_choice with Gemini JSON prompt."""
        cv_text = json.dumps(parsed_cv, indent=2)

        user_instructions_section = ""
        if instructions and instructions.strip():
            user_instructions_section = f"""
PRIORITY OVERRIDE - USER CUSTOM INSTRUCTIONS:
{instructions}
"""
        # IN HIREPILOT-AI: replace self.client.chat.completions.create with get_llm() Gemini call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this CV against the Job Description.\n{user_instructions_section}\nJOB TITLE: {job_title}\nJOB DESCRIPTION:\n{job_description}\nPARSED CV DATA:\n{cv_text}"}
            ],
            tools=self.ANALYSIS_FUNCTION,
            tool_choice={"type": "function", "function": {"name": "analyze_cv_against_jd"}}
        )

        if response.choices[0].message.tool_calls:
            function_args = response.choices[0].message.tool_calls[0].function.arguments
            try:
                result = json.loads(function_args)
            except json.JSONDecodeError as e:
                import re as re_module
                fixed = re_module.sub(r',(\s*[}\]])', r'\1', function_args)
                result = json.loads(fixed)

            result = self._apply_project_guardrail(result, parsed_cv, job_title, job_description)
            result = self._add_field_paths(result, parsed_cv)

            deterministic_scores = self.calculate_match_score(parsed_cv, job_description)
            result["scores"] = {
                "current_match_score": deterministic_scores["current_match_score"],
                "potential_score_after_changes": min(95, deterministic_scores["current_match_score"] + 20),
                "rating": deterministic_scores["rating"],
                "breakdown": deterministic_scores["breakdown"]
            }
            return result

        raise ValueError("Failed to generate analysis")

    SECTION_CHAT_FUNCTION = [{
        "type": "function",
        "function": {
            "name": "respond_with_action",
            "description": "Respond to user message with optional actionable changes",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Your response message to the user"
                    },
                    "has_action": {
                        "type": "boolean",
                        "description": "Whether this response includes an actionable change"
                    },
                    "action": {
                        "type": "object",
                        "properties": {
                            "action_type": {
                                "type": "string",
                                "enum": ["improve", "add", "remove", "replace", "rewrite"]
                            },
                            "description": {"type": "string"},
                            "changes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "field": {"type": "string"},
                                        "change_type": {"type": "string", "enum": ["replace", "add", "remove", "modify"]},
                                        "original_value": {"type": "string"},
                                        "new_value": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                "required": ["message", "has_action"]
            }
        }
    }]

    def chat_with_section(self, message: str, section: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """Chat with section context. IN HIREPILOT-AI: replace OpenAI with Gemini JSON prompt."""
        import uuid
        job_title = session_context.get("job_title", "Unknown")
        job_description = session_context.get("job_description", "")
        parsed_cv = session_context.get("current_cv") or session_context.get("parsed_cv", {})
        chat_history = session_context.get("chat_history", [])
        section_content = self._get_section_content(parsed_cv, section)

        history_messages = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history[-10:]]

        system_prompt = f"""{self.CHAT_SYSTEM_PROMPT}
CONTEXT:
- Job Title: {job_title}
- Current Section: {section}
- Section Content: {json.dumps(section_content, indent=2) if section_content else "Empty/Not available"}

JOB DESCRIPTION:
{job_description[:1500] if job_description else "Not provided"}

RULES:
1. If user is asking/brainstorming -> has_action = false
2. If user wants to change/add/remove -> has_action = true, include action with specific changes
3. Provide EXACT field paths and values that can be applied to the CV"""

        messages = [
            {"role": "system", "content": system_prompt},
            *history_messages,
            {"role": "user", "content": f"[Section: {section}] {message}"}
        ]

        # IN HIREPILOT-AI: replace below with Gemini call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.SECTION_CHAT_FUNCTION,
            tool_choice={"type": "function", "function": {"name": "respond_with_action"}}
        )

        if response.choices[0].message.tool_calls:
            function_args = response.choices[0].message.tool_calls[0].function.arguments
            try:
                result = json.loads(function_args)
            except json.JSONDecodeError:
                result = {"message": response.choices[0].message.content or "I can help with that.", "has_action": False}
        else:
            result = {"message": response.choices[0].message.content or "I can help with that.", "has_action": False}

        response_data = {
            "message": result.get("message", ""),
            "section": section,
            "session_id": session_context.get("session_id"),
        }

        if result.get("has_action") and result.get("action"):
            action_data = result["action"]
            response_data["action"] = {
                "action_id": f"action_{uuid.uuid4().hex[:12]}",
                "action_type": action_data.get("action_type", "improve"),
                "section": section,
                "status": "pending",
                "description": action_data.get("description", "Apply suggested changes"),
                "changes": action_data.get("changes", []),
                "requires_confirmation": True
            }

        return response_data

    def _get_section_content(self, parsed_cv: Dict[str, Any], section: str) -> Any:
        """Extract content for a specific section. Port VERBATIM."""
        section_map = {
            "entire_resume": parsed_cv,
            "professional_summary": parsed_cv.get("professional_summary"),
            "work_experience": parsed_cv.get("work_experience"),
            "education": parsed_cv.get("education"),
            "skills": parsed_cv.get("skills"),
            "projects": parsed_cv.get("projects"),
            "certifications": parsed_cv.get("certifications"),
            "contact_info": parsed_cv.get("contact_info"),
            "title": parsed_cv.get("title"),
            "languages": parsed_cv.get("languages"),
            "awards_scholarships": parsed_cv.get("awards_scholarships"),
            "publications": parsed_cv.get("publications")
        }
        return section_map.get(section, parsed_cv)
```

---

## SECTION 8: COMPLETE app_v3.py SOURCE CODE (Reference Only — Do Not Port)

```python
"""
FastAPI application for CV/Resume parsing.
HIREPILOT-AI NOTE: Do not port this file directly.
Your backend/main.py replaces this. Use this only as reference
for understanding how the parser was called.
"""

import os
import tempfile
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from parser_v3 import CVParserV3

app = FastAPI(
    title="CV Parser API (Experiment 3)",
    description="Extract essential CV information. Accepts CV PDF file uploads.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

parser = None

def get_parser():
    global parser
    if parser is None:
        parser = CVParserV3()
    return parser

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "cv-parser-api-v3",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    }

@app.post("/parse", response_model=Dict[str, Any])
async def parse_cv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        pdf_content = await file.read()
        if len(pdf_content) < 100:
            raise HTTPException(status_code=400, detail="File too small or empty")
        if not pdf_content.startswith(b'%PDF'):
            raise HTTPException(status_code=400, detail="Not a valid PDF file")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file_path = tmp_file.name

        result = get_parser().parse_cv(tmp_file_path, file.filename)
        os.unlink(tmp_file_path)

        if result is None:
            raise HTTPException(status_code=500, detail="Failed to parse CV")

        return {
            "success": True,
            "filename": file.filename,
            "data": result['data']
        }
    except HTTPException:
        raise
    except Exception as e:
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        raise HTTPException(status_code=500, detail=f"Error processing CV: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app_v3:app", host="0.0.0.0", port=port)
```

---

## SECTION 9: HOW TO PORT FOR HIREPILOT-AI — TASK BY TASK

### TASK-008: Create _cv_schema.py
```
Action: Copy from Section 6 (parser_v3.py)
Take:   CV_FUNCTION → rename to CV_EXTRACTION_FUNCTION
Take:   SYSTEM_PROMPT → rename to CV_SYSTEM_PROMPT
File:   backend/agents/_cv_schema.py
Rule:   No classes, no methods — constants only
Change: Nothing in the schema itself — copy verbatim
```

### TASK-009: Create cv_parser_agent.py
```
Action: Port parse_cv_text() logic from Section 6
File:   backend/agents/cv_parser_agent.py
Function: cv_parser_node(state: HirePilotState) -> HirePilotState

Changes from BowJob:
1. Replace PyPDF2 with fitz (PyMuPDF)
2. Add DOCX support via python-docx
3. Replace OpenAI call with Gemini via get_llm()
4. Add @observe(name="CVParserAgent") decorator
5. Remove all cost tracking
6. Save parsed CV to SQLite cv_versions table
7. Return updated state

Keep unchanged:
- CV_EXTRACTION_FUNCTION schema (from _cv_schema.py)
- CV_SYSTEM_PROMPT (from _cv_schema.py)
- The JSON prompt structure
```

### TASK-017: Create _cv_improvement_schema.py
```
Action: Copy from Section 7 (improvement_engine.py)
Take:   ANALYSIS_FUNCTION → rename to CV_IMPROVEMENT_FUNCTION
Take:   SYSTEM_PROMPT → rename to CV_IMPROVEMENT_SYSTEM_PROMPT
Take:   CHAT_SYSTEM_PROMPT → rename to CV_CHAT_SYSTEM_PROMPT
Take:   SCORE_WEIGHTS → keep same name
File:   backend/agents/_cv_improvement_schema.py
Rule:   Constants only, no class
Change: Nothing — copy verbatim
```

### TASK-018: Create cv_tailoring_agent.py
```
Action: Port CVImprovementEngine class from Section 7
File:   backend/agents/cv_tailoring_agent.py
Function: cv_tailoring_node(state: HirePilotState) -> HirePilotState

COPY VERBATIM (zero changes):
- calculate_match_score()
- get_improvement_suggestions()
- _generate_suggestion_summary()
- _count_projects()
- _inject_projects_to_work_exp()
- _apply_project_guardrail()
- _add_field_paths()
- _get_section_content()

REPLACE OpenAI with Gemini in:
- analyze() → replace tool_choice call with Gemini JSON prompt
- _generate_missing_projects() → replace OpenAI call with Gemini
- chat_with_section() → replace tool_choice call with Gemini JSON prompt

ADD:
- @observe(name="CVTailoringAgent") decorator
- Langfuse score logging for HITL approval/rejection
- Save tailored CV to cv_versions table in SQLite
```

---

## SECTION 10: QUICK REFERENCE CHEAT SHEET

```
SCORING WEIGHTS (never change):
  Skills     = 35 pts
  Experience = 25 pts
  Education  = 15 pts
  Projects   = 15 pts (3+ projects = full 15 pts)
  Keywords   = 10 pts
  Total      = 100 pts

cv_sections     = modifications to EXISTING content
non_cv_sections = NEW content for NULL/EMPTY sections

MINIMUM 3 PROJECTS always required

Gemini call pattern:
  llm, handler = get_llm(state["session_id"], "AgentName")
  response = llm.invoke([HumanMessage(content=prompt)])
  clean = clean_json_response(response.content)
  data = json.loads(clean)

PDF extraction (HirePilot-AI):
  import fitz
  doc = fitz.open(pdf_path)
  text = ""
  for page in doc:
      text += page.get_text()

DOCX extraction (HirePilot-AI):
  from docx import Document
  doc = Document(file_path)
  text = "\n".join([para.text for para in doc.paragraphs])
```
