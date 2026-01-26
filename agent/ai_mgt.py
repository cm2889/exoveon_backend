import re 
import json
import asyncio 
import base64 
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from openai import OpenAI 
from decouple import config 

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=config("OPENROUTER_API_KEY"),
)

MODEL_MAP = {
    "gemma-3-27b-it-free": "google/gemma-3-27b-it:free",
    "gemma-3-12b-it:free": "google/gemma-3-12b-it:free",
    "gemma-3-27b-it": "google/gemma-3-27b-it",
    "gemma-7b-it": "google/gemma-7b-it",
    "gemini-2.5-flash-image": "google/gemini-2.5-flash-image",
    "gemini-2.5-flash-image-preview": "google/gemini-2.5-flash-image-preview",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4.1-mini": "openai/gpt-4.1-mini",
    "grok-4.1-fast:free": "x-ai/grok-4.1-fast:free",
    "nova-lite-v1": "amazon/nova-lite-v1",
}

# ============================================================================
# REUSABLE UTILITY FUNCTIONS
# ============================================================================

def get_model_id(model_key: str) -> str:
    """Get the full model ID from a model key."""
    return MODEL_MAP.get(model_key, model_key)


def encode_image_to_base64(image_path: Path) -> Optional[str]:
    """Encode an image file to base64 string."""
    try:
        img_bytes = image_path.read_bytes()
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        return None


def build_image_content_parts(image_paths: List[Path]) -> List[Dict[str, Any]]:
    """Build content parts array with encoded images."""
    content_parts = []
    for index, img_path in enumerate(image_paths):
        img_b64 = encode_image_to_base64(img_path)
        if img_b64:
            content_parts.append({
                'type': 'image_url',
                'image_url': {
                    'url': f'data:image/png;base64,{img_b64}',
                },
                'alt_text': f'Screenshot {index + 1}',
            })
    return content_parts


def call_llm(
    model_key: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4000,
    temperature: float = 0.0,
) -> str:
    """Reusable function to call LLM without images."""
    model_id = get_model_id(model_key)
    
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]
    
    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    
    return response.choices[0].message.content


def call_vision_model(
    model_key: str,
    system_prompt: str,
    user_prompt: str,
    img_paths: Optional[List[Path]] = None,
    max_tokens: int = 8000,
    temperature: float = 0.0,
) -> str:
    """Reusable function to call vision model with images."""
    model_id = get_model_id(model_key)

    content_parts = [
        {'type': 'text', 'text': user_prompt},
    ]

    if img_paths:
        image_parts = build_image_content_parts(img_paths)
        content_parts.extend(image_parts)

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': content_parts},
    ]

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return response.choices[0].message.content


def parse_json_response(response: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    cleaned = response.strip()
    
    # Remove markdown code blocks if present
    if cleaned.startswith('```json'):
        cleaned = cleaned[7:]
    elif cleaned.startswith('```'):
        cleaned = cleaned[3:]
    
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]
    
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse JSON response",
            "raw_response": response,
            "parse_error": str(e)
        }


# ============================================================================
# MAIN AGENT FUNCTIONS
# ============================================================================

class LLMManager:
    """Reusable LLM Manager for custom prompts and configurations."""
    
    def __init__(
        self,
        prompt: str,
        model_name: str,
        system_role: str,
        max_tokens: int = 4000,
        temperature: float = 0.0,
        img_paths: Optional[List[Path]] = None
    ):
        self.prompt = prompt
        self.model_name = get_model_id(model_name)
        self.system_role = system_role
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.img_paths = img_paths or []
    
    def execute(self) -> str:
        """Execute the LLM call and return the response."""
        if self.img_paths:
            return call_vision_model(
                model_key=self.model_name,
                system_prompt=self.system_role,
                user_prompt=self.prompt,
                img_paths=self.img_paths,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        else:
            return call_llm(
                model_key=self.model_name,
                system_prompt=self.system_role,
                user_prompt=self.prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )


# ============================================================================
# REUSABLE PROMPT TEMPLATES
# ============================================================================

CTO_ANALYSIS_SYSTEM_PROMPT = """
    
    You are a CTO (Chief Technology Officer) with 15+ years of experience in building scalable products, leading engineering teams at top tech companies (Google, Meta, Amazon, Stripe), and deep expertise in:

    - Modern tech stack evaluation (React, Next.js, Vue, Angular, Flutter, React Native, Swift, Kotlin)
    - Cloud architecture (AWS, GCP, Azure), microservices, serverless, and edge computing
    - AI/ML integration, LLM-powered features, and intelligent automation
    - Performance optimization, Core Web Vitals, and technical SEO
    - Security best practices (OWASP, SOC2, GDPR compliance)
    - DevOps, CI/CD pipelines, and infrastructure as code
    - Scalability patterns for handling millions of users

    You are analyzing product UI screenshots from a TECHNICAL LEADERSHIP perspective. Your role is to:
    1. Evaluate the technical architecture decisions visible in the UI
    2. Identify technology modernization opportunities
    3. Assess performance, security, and scalability implications
    4. Recommend cutting-edge features that provide competitive advantage
    5. Flag features that add technical debt without business value

    ANALYSIS FRAMEWORK:

    ## 1. Technical Architecture Assessment
    - Infer the likely tech stack from UI patterns and behaviors
    - Evaluate component architecture and state management approach
    - Assess API design implications from UI interactions
    - Identify potential performance bottlenecks

    ## 2. Technology Modernization Opportunities
    - AI/ML-powered features (personalization, recommendations, chatbots, predictive analytics)
    - Real-time capabilities (WebSockets, Server-Sent Events, live collaboration)
    - Progressive Web App (PWA) features (offline mode, push notifications, installability)
    - Edge computing and CDN optimization opportunities
    - Modern authentication (passkeys, biometrics, SSO)

    ## 3. Performance & Core Web Vitals
    - Loading performance (LCP optimization opportunities)
    - Interactivity (FID/INP improvements)
    - Visual stability (CLS issues)
    - Bundle size and code splitting opportunities
    - Image optimization and lazy loading

    ## 4. Security & Compliance Assessment
    - Authentication and authorization patterns
    - Data privacy implications (GDPR, CCPA)
    - Input validation and XSS prevention
    - Secure communication requirements

    ## 5. Scalability & Infrastructure
    - Caching strategies needed
    - Database optimization implications
    - Microservices vs monolith considerations
    - Global distribution requirements

    ## 6. Feature Categorization (CRITICAL)
    A. **MUST BUILD** - High-impact features that are technically feasible and provide significant competitive advantage
    B. **SHOULD BUILD** - Valuable features requiring moderate effort with good ROI
    C. **COULD BUILD** - Nice-to-have features for future consideration
    D. **AVOID BUILDING** - Features that add technical debt, complexity without value, or are technically premature

    ## 7. Technical Debt & Risk Assessment
    - Identify visible technical debt indicators
    - Security vulnerabilities to address
    - Scalability risks if not addressed
    - Maintenance burden of current implementation

    ## 8. Innovation Opportunities
    - AI/ML integration points
    - Automation opportunities
    - Data analytics and insights features
    - Integration ecosystem potential

    ## 9. Implementation Roadmap
    - Quick wins (1-2 weeks)
    - Short-term improvements (1-3 months)
    - Medium-term initiatives (3-6 months)
    - Long-term strategic investments (6-12 months)

    ## 10. Executive Technical Summary
    - Current technical maturity score (1-10)
    - Top 3 technical risks
    - Top 3 innovation opportunities
    - Strategic recommendation for engineering leadership

    CONSTRAINTS:
    - Base all recommendations on visible UI evidence
    - Consider realistic development timelines and resources
    - Prioritize security and performance over features
    - Avoid recommending trendy tech without clear business value
    - Focus on sustainable, maintainable solutions
    """


def image_analysis_manager(
    image_paths: List[Path],
    page_url: str,
    persona_note: str,
    image_model: str = "gemini-2.5-flash-image",
    max_images_for_model: int = 6,
    max_tokens: int = 8000,
    temperature: float = 0.2,
) -> str:
    
    selected_images = image_paths[:max_images_for_model]

    user_prompt = f"""Analyze the following UI screenshots for the product at: {page_url}

    TARGET PERSONA: {persona_note}

    NUMBER OF SCREENSHOTS: {len(selected_images)}

    Please provide a comprehensive CTO-level technical analysis following the system framework. Focus on:
    1. What technology stack is likely being used
    2. What modern features should be built (AI, real-time, PWA, etc.)
    3. What features should NOT be built (technical debt, complexity without value)
    4. Performance and security implications
    5. Scalability considerations
    6. Realistic implementation roadmap

    Be specific, actionable, and base all recommendations on visible evidence from the screenshots."""

    analysis = call_vision_model(
        model_key=image_model,
        system_prompt=CTO_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        img_paths=selected_images,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return analysis


PROJECT_MANAGER_SYSTEM_PROMPT = """You are a Senior Project Manager / Product Owner with expertise in:

    - Agile/Scrum methodology and sprint planning
    - User story creation and acceptance criteria
    - Stakeholder management and requirement gathering
    - Risk assessment and mitigation
    - Resource allocation and timeline estimation
    - Feature prioritization frameworks (MoSCoW, RICE, Kano)
    - Cross-functional team coordination

    Based on the CTO's technical analysis, your role is to:
    1. Transform technical recommendations into actionable user stories
    2. Prioritize features based on business value and technical feasibility
    3. Create a realistic implementation roadmap
    4. Identify dependencies and potential blockers
    5. Define success metrics and KPIs for each feature

    ANALYSIS FRAMEWORK:

    ## 1. Feature Prioritization Matrix
    Using RICE scoring (Reach, Impact, Confidence, Effort):
    - Calculate priority score for each recommendation
    - Justify prioritization decisions
    - Identify quick wins vs strategic investments

    ## 2. User Story Creation
    For each recommended feature, provide:
    - User story format: "As a [user type], I want [feature], so that [benefit]"
    - Acceptance criteria (Given/When/Then)
    - Story points estimation (Fibonacci: 1, 2, 3, 5, 8, 13)
    - Dependencies and blockers

    ## 3. Sprint Planning Recommendations
    - Sprint 1-2: Foundation and quick wins
    - Sprint 3-4: Core feature development
    - Sprint 5-6: Enhancement and optimization
    - Future backlog items

    ## 4. Risk Assessment
    - Technical risks and mitigation strategies
    - Resource risks and contingency plans
    - Timeline risks and buffer recommendations
    - Stakeholder alignment risks

    ## 5. Success Metrics & KPIs
    For each major feature:
    - Primary success metric
    - Secondary metrics
    - Baseline and target values
    - Measurement methodology

    ## 6. Resource Requirements
    - Frontend development effort
    - Backend development effort
    - Design/UX effort
    - QA/Testing effort
    - DevOps/Infrastructure effort

    ## 7. Dependency Mapping
    - Feature dependencies
    - Technical dependencies
    - External dependencies (APIs, third-party services)
    - Team dependencies

    ## 8. Go/No-Go Decision Framework
    For each feature category:
    - Build criteria met?
    - Resources available?
    - Timeline realistic?
    - Risk acceptable?
    - Final recommendation: GO / NO-GO / DEFER

    CONSTRAINTS:
    - Base estimates on industry standards
    - Consider team velocity and capacity
    - Account for technical debt and maintenance
    - Include buffer for unexpected issues
    - Align with business objectives and OKRs
"""

def recommendation_agent_manager(
    analysis: str,
    additional_context: Optional[Dict[str, Any]] = None,
    model_name: str = "gemini-2.5-flash-image",
    max_tokens: int = 6000,
    temperature: float = 0.1,
) -> str:
    """
    Project Manager perspective - transforms CTO analysis into actionable recommendations.
    
    Args:
        analysis: CTO technical analysis output
        additional_context: Optional additional context (business goals, constraints, etc.)
        model_name: Model to use for analysis
        max_tokens: Maximum tokens for response
        temperature: Model temperature
    
    Returns:
        Project management analysis with user stories and prioritization
    """
    context_section = ""
    if additional_context:
        context_section = f"\n\nADDITIONAL BUSINESS CONTEXT:\n{json.dumps(additional_context, indent=2)}"

    user_prompt = f"""Based on the following CTO Technical Analysis, provide a comprehensive Project Management perspective:

    === CTO TECHNICAL ANALYSIS ===
    {analysis}
    {context_section}

    Please transform this technical analysis into:
    1. Prioritized feature backlog using RICE scoring
    2. User stories with acceptance criteria for top recommendations
    3. Sprint planning recommendations
    4. Risk assessment and mitigation strategies
    5. Success metrics and KPIs
    6. Resource requirements estimation
    7. Clear GO/NO-GO recommendations for each feature category

    Focus on actionable, realistic recommendations that balance technical excellence with business value."""

    response = call_llm(
        model_key=model_name,
        system_prompt=PROJECT_MANAGER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return response


WRITER_JSON_SYSTEM_PROMPT = """You are a Technical Documentation Specialist who transforms technical analysis into structured JSON reports for executive stakeholders and development teams.

    Your output MUST be valid JSON that can be parsed by any JSON parser. Do not include any text outside the JSON structure.

    OUTPUT JSON SCHEMA:
    {
        "report_metadata": {
            "generated_at": "ISO 8601 timestamp",
            "analysis_type": "UI/UX Technical Analysis",
            "version": "1.0"
        },
        "executive_summary": {
            "overall_score": "number 1-10",
            "maturity_level": "string (Beginner/Intermediate/Advanced/Expert)",
            "one_line_summary": "string",
            "key_strengths": ["string array"],
            "critical_issues": ["string array"],
            "strategic_recommendation": "string"
        },
        "feature_recommendations": {
            "must_build": [
                {
                    "feature_name": "string",
                    "description": "string",
                    "business_value": "string",
                    "technical_complexity": "Low/Medium/High",
                    "estimated_effort": "string (e.g., '2-3 sprints')",
                    "priority_score": "number 1-100",
                    "user_story": "string",
                    "acceptance_criteria": ["string array"],
                    "dependencies": ["string array"],
                    "success_metrics": ["string array"]
                }
            ],
            "should_build": [
                {
                    "feature_name": "string",
                    "description": "string",
                    "business_value": "string",
                    "technical_complexity": "Low/Medium/High",
                    "estimated_effort": "string",
                    "priority_score": "number 1-100",
                    "user_story": "string",
                    "acceptance_criteria": ["string array"],
                    "dependencies": ["string array"],
                    "success_metrics": ["string array"]
                }
            ],
            "could_build": [
                {
                    "feature_name": "string",
                    "description": "string",
                    "reason_to_defer": "string",
                    "future_consideration": "string"
                }
            ],
            "avoid_building": [
                {
                    "feature_name": "string",
                    "reason": "string",
                    "alternative_approach": "string"
                }
            ]
        },
        "technical_assessment": {
            "current_stack_inference": ["string array"],
            "performance_issues": ["string array"],
            "security_concerns": ["string array"],
            "scalability_risks": ["string array"],
            "technical_debt_items": ["string array"]
        },
        "implementation_roadmap": {
            "phase_1_quick_wins": {
                "duration": "string",
                "items": ["string array"],
                "expected_outcomes": ["string array"]
            },
            "phase_2_core_features": {
                "duration": "string",
                "items": ["string array"],
                "expected_outcomes": ["string array"]
            },
            "phase_3_enhancements": {
                "duration": "string",
                "items": ["string array"],
                "expected_outcomes": ["string array"]
            },
            "phase_4_innovation": {
                "duration": "string",
                "items": ["string array"],
                "expected_outcomes": ["string array"]
            }
        },
        "risk_matrix": [
            {
                "risk_type": "string",
                "description": "string",
                "probability": "Low/Medium/High",
                "impact": "Low/Medium/High",
                "mitigation_strategy": "string"
            }
        ],
        "resource_estimation": {
            "frontend_effort_percentage": "number",
            "backend_effort_percentage": "number",
            "design_effort_percentage": "number",
            "qa_effort_percentage": "number",
            "devops_effort_percentage": "number",
            "total_estimated_sprints": "number",
            "recommended_team_size": "number"
        },
        "success_metrics": {
            "primary_kpis": [
                {
                    "metric_name": "string",
                    "current_baseline": "string",
                    "target_value": "string",
                    "measurement_method": "string"
                }
            ],
            "secondary_kpis": [
                {
                    "metric_name": "string",
                    "target_value": "string"
                }
            ]
        },
        "next_steps": [
            {
                "action": "string",
                "owner": "string",
                "deadline": "string",
                "priority": "High/Medium/Low"
            }
        ]
    }

    CRITICAL RULES:
    1. Output ONLY valid JSON - no markdown, no explanations, no code blocks
    2. All string values must be properly escaped
    3. All arrays must have at least one item or be empty []
    4. All numbers must be actual numbers, not strings
    5. Follow the exact schema structure provided
    6. Ensure all required fields are present

"""


def writer_agent_manager(
    cto_analysis: str,
    pm_analysis: str,
    model_name: str = "gemini-2.5-flash-image",
    max_tokens: int = 8000,
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """
    Technical Writer agent that produces structured JSON report.
    
    Args:
        cto_analysis: CTO technical analysis output
        pm_analysis: Project Manager analysis output
        model_name: Model to use
        max_tokens: Maximum tokens for response
        temperature: Model temperature
    
    Returns:
        Structured JSON dictionary with complete analysis report
    """

    user_prompt = f"""Transform the following CTO and Project Manager analyses into a structured JSON report.

        === CTO TECHNICAL ANALYSIS ===
        {cto_analysis}

        === PROJECT MANAGER ANALYSIS ===
        {pm_analysis}

        Generate a complete JSON report following the exact schema provided in the system prompt.
        Output ONLY valid JSON - no additional text, explanations, or markdown formatting.
        
        """

    response = call_llm(
        model_key=model_name,
        system_prompt=WRITER_JSON_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return parse_json_response(response)


def run_full_analysis_pipeline(
    image_paths: List[Path],
    page_url: str,
    persona_note: str,
    additional_context: Optional[Dict[str, Any]] = None,
    image_model: str = "gemini-2.5-flash-image",
    analysis_model: str = "gemini-2.5-flash-image",
    max_images: int = 6,
) -> Dict[str, Any]:
    """
    Run the complete analysis pipeline: CTO Analysis -> PM Analysis -> JSON Report.
    
    Args:
        image_paths: List of screenshot paths
        page_url: URL being analyzed
        persona_note: Target user persona
        additional_context: Optional business context
        image_model: Model for image analysis
        analysis_model: Model for text analysis
        max_images: Maximum images to process
    
    Returns:
        Complete analysis report as JSON dictionary
    """
    # Step 1: CTO Technical Analysis
    cto_analysis = image_analysis_manager(
        image_paths=image_paths,
        page_url=page_url,
        persona_note=persona_note,
        image_model=image_model,
        max_images_for_model=max_images,
    )
    
    # Step 2: Project Manager Analysis
    pm_analysis = recommendation_agent_manager(
        analysis=cto_analysis,
        additional_context=additional_context,
        model_name=analysis_model,
    )
    
    # Step 3: Generate JSON Report
    final_report = writer_agent_manager(
        cto_analysis=cto_analysis,
        pm_analysis=pm_analysis,
        model_name=analysis_model,
    )
    
    # Add raw analyses to report for reference
    if isinstance(final_report, dict) and "error" not in final_report:
        final_report["_raw_analyses"] = {
            "cto_analysis": cto_analysis,
            "pm_analysis": pm_analysis,
        }
    
    return final_report