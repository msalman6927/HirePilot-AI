# filepath: backend/agents/_cv_improvement_schema.py
# ══════════════════════════════════════════════════════════════════
# PORTED VERBATIM FROM BOWJOB: cv-jd-matching/improvement_engine.py
# DO NOT MODIFY schemas, prompts, or weights — they are production-tested.
# Only rename constants per BOWJOB_REFERENCE.md Section 9 (TASK-017).
# ══════════════════════════════════════════════════════════════════

# --- ANALYSIS FUNCTION SCHEMA (verbatim from BowJob) ---
CV_IMPROVEMENT_FUNCTION = [{
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

# --- SYSTEM PROMPT (verbatim from BowJob) ---
CV_IMPROVEMENT_SYSTEM_PROMPT = """You are an expert HR analyst and CV optimization specialist.
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

# --- CHAT SYSTEM PROMPT (verbatim from BowJob) ---
CV_CHAT_SYSTEM_PROMPT = """You are a helpful CV improvement assistant. Use industry-specific terminology based on the job context."""

# --- SECTION CHAT FUNCTION SCHEMA (verbatim from BowJob) ---
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

# --- SCORING WEIGHTS (verbatim from BowJob) ---
SCORE_WEIGHTS = {
    "skills": 35,
    "experience": 25,
    "education": 15,
    "projects": 15,
    "keywords": 10
}
