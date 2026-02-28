from typing import Dict, Any

CV_SYSTEM_PROMPT = """You are an expert CV/Resume parser. Your job is to extract ALL content from the CV and map it to the output schema. DO NOT MISS ANY CONTENT.

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

# Extracted from BOWJOB_REFERENCE.md (CV_FUNCTION[0]["function"]["parameters"])
CV_EXTRACTION_SCHEMA: Dict[str, Any] = {
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
            "description": "Professional summary, objective, or about section from the CV. If written as bullet points or multiple paragraphs, return as array of strings. If written as single paragraph, return as string. Return null if not present"
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
                        "description": "Job responsibilities, achievements, and key points. If listed as bullet points or separate lines, return as array of strings (each bullet/line as separate element). If written as a continuous paragraph, return as single string. Return null if not provided"
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
                        "description": "Project description, objectives, and outcomes. If listed as bullet points or separate lines, return as array of strings (each bullet/line as separate element). If written as a continuous paragraph, return as single string. Return null if not provided"
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
                        "description": "Brief description if available. If listed as bullet points or separate lines, return as array. If paragraph, return as string. Return null if not provided"
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
