import re 
import asyncio 
import json 
import base64 
from pathlib import Path 
from typing import List, Dict, Any, Optional 

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

class LLM_agent:
    def __init__(self, prompt: str, model_name: str, system_role: str, max_tokens: int, temperature: float = 0.0, image_paths: Optional[List[Path]] = None):
        self.prompt = prompt
        self.model_name = model_name
        self.system_role = system_role
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.image_paths = image_paths or [] 


def call_vision_model(model_key: str, system_prompt: str, user_prompt: str, image_paths: Optional[List[Path]] = None, max_tokens: int = 5000, temperature: float = 0.0,) -> str:
    model_id = MODEL_MAP.get(model_key)  

    content_parts = [{"type": "text", "text": user_prompt}] 

    for idx, img_path in enumerate(image_paths or [], start=1):
        try:
            img_bytes = img_path.read_bytes()
            img_base64 = base64.b64encode(img_bytes).decode('ascii') 
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                }
            )
        except Exception as e:
            continue 

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content_parts},
    ]

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    except Exception as e:
        # Fallback on context-length or similar payload errors: reduce prompt and images
        msg = str(e)
        if "maximum context length" in msg or "context" in msg.lower():
            # Use a compact prompt and fewer images
            compact_prompt = "Analyze the attached screenshots. Return JSON only."
            compact_parts = [{"type": "text", "text": compact_prompt}]
            limited_images = (image_paths or [])[:2]
            for img_path in limited_images:
                try:
                    img_b = img_path.read_bytes()
                    img_b64 = base64.b64encode(img_b).decode('ascii')
                    compact_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    })
                except Exception:
                    pass
            compact_messages = [
                {"role": "system", "content": system_prompt[:2000]},
                {"role": "user", "content": compact_parts},
            ]
            response = client.chat.completions.create(
                model=model_id,
                messages=compact_messages,
                max_tokens=min(max_tokens, 1500),
                temperature=temperature,
            )
            return response.choices[0].message.content
        raise


def image_to_datauri_markdown(image_paths: List[Path], max_images: int = 4) -> str:
    chunks: List[str] = []

    for idx, path in enumerate(image_paths[:max_images], start=1):
        b = path.read_bytes()
        b64 = base64.b64encode(b).decode("ascii")
        chunks.append(
            f"### Screenshot {idx}\n\n![screenshot_{idx}](data:image/png;base64,{b64})\n"
        )
    return "\n".join(chunks)


def image_analysis_agent(image_paths: List[Path], page_url: str, persona_note: str, image_model: str = "gemini-2.5-flash-image", max_images_for_model: int = 2 )-> str: 

    system_prompt = (
        "You are an elite multidisciplinary UX/UI expert with 20+ years of experience in comprehensive "
        "website analysis, visual design auditing, and accessibility evaluation. Your expertise spans:\n\n"
        
        "VISUAL DESIGN:\n"
        "- Layout hierarchy and information architecture\n"
        "- Gestalt principles (proximity, similarity, closure, continuity, figure-ground)\n"
        "- Visual balance, symmetry, and white space utilization\n"
        "- Color theory, contrast ratios (WCAG 2.2 AA/AAA standards)\n"
        "- Typography hierarchy, readability (font sizes, line height, letter spacing)\n"
        "- Grid systems and responsive design patterns\n\n"
        
        "USABILITY HEURISTICS:\n"
        "- Nielsen's 10 Usability Heuristics (visibility, match real-world, user control, consistency, "
        "error prevention, recognition vs recall, flexibility, aesthetic design, error recovery, documentation)\n"
        "- Fitts's Law (target sizing and placement for clickable elements - minimum 44x44px)\n"
        "- Hick's Law (choice complexity and decision time)\n"
        "- Miller's Law (cognitive load - 7±2 items per group)\n"
        "- Jakob's Law (consistency with user expectations)\n"
        "- Doherty Threshold (response time < 400ms for perceived immediacy)\n\n"
        
        "ACCESSIBILITY (WCAG 2.2):\n"
        "- Contrast ratios: text (4.5:1 normal, 3:1 large), UI components (3:1)\n"
        "- Semantic HTML structure (headings, landmarks, ARIA)\n"
        "- Keyboard navigation and focus management\n"
        "- Alt text for images and meaningful link text\n"
        "- Form labels and error messages\n"
        "- Screen reader compatibility\n\n"
        
        "CONVERSION & UX PATTERNS:\n"
        "- Call-to-action clarity, prominence, and hierarchy\n"
        "- Trust signals (testimonials, badges, social proof)\n"
        "- Form design and friction reduction\n"
        "- Visual flow and F/Z-pattern reading\n"
        "- Mobile-first responsive considerations\n"
        "- Loading states and performance perception\n\n"
        
        "ANALYSIS FRAMEWORK:\n"
        "Analyze ALL provided screenshots sequentially. For each screenshot, identify:\n"
        "1. Visual Hierarchy: What draws attention first/second/third? Is it intentional?\n"
        "2. Usability Issues: Apply Nielsen heuristics - what breaks conventions or confuses users?\n"
        "3. Accessibility Gaps: Contrast issues, missing alt text, keyboard traps, semantic problems\n"
        "4. Conversion Blockers: What prevents users from taking desired actions?\n"
        "5. Design Inconsistencies: Typography, spacing, color usage, component styles\n"
        "6. Mobile Considerations: Touch target sizes, responsive breakpoints, viewport optimization\n\n"
        
        "OUTPUT FORMAT:\n"
        "Provide a comprehensive analysis with:\n"
        "- Screenshot Number: Reference which image you're analyzing\n"
        "- Priority Level: Include severity tags: 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low\n"
        "- Specific Location: Describe the element/section\n"
        "- Issue Description: With rationale (cite principles/standards)\n"
        "- Impact Assessment: User experience, conversion, accessibility\n"
        "- Actionable Recommendations: With implementation effort estimate\n"
        "- Positive Observations: What works well\n\n"
        
        "TASK: ONLY output a strict, valid JSON object. NO markdown code blocks, NO commentary outside JSON.\n\n"
        "Be thorough yet concise. Reference specific heuristics, principles, and WCAG criteria. "
        "Prioritize by business impact and user pain points. Think like both a designer and a user advocate."
    )
     
    user_prompt = (
        f"ANALYZING: {page_url}\n"
        f"TOTAL SCREENSHOTS: {len(image_paths)}\n\n"
        f"I have captured {len(image_paths)} sequential screenshots of the entire webpage from top to bottom. "
        f"Please analyze ALL {len(image_paths)} images comprehensively. These screenshots show the complete user journey "
        f"as they scroll through the page. Pay attention to:\n"
        f"- How visual hierarchy changes across sections\n"
        f"- Consistency of design patterns throughout the page\n"
        f"- Navigation and orientation cues for different sections\n"
        f"- Call-to-action placement and prominence at different scroll depths\n"
        f"- Overall page flow and user journey coherence\n\n"
        f"USER REQUEST: {persona_note}\n\n"
        "INSTRUCTIONS:\n"
        "1) Read the screenshots below. Produce a single JSON object that follows this schema EXACTLY:\n"
        "{\n"
        "  \"page_title\": string or null,\n"
        "  \"elements\": [\n"
        "    {\"id\": string, \"type\": string, \"text\": string|null, \"bbox\": [x,y,w,h], \"confidence\": 0.0-1.0}\n"
        "  ],\n"
        "  \"visual_flags\": {\"low_contrast\": bool, \"small_cta\": bool, \"crowded_layout\": bool, \"missing_alt\": bool},\n"
        "  \"ocr_text_snippets\": [\"...\"],\n"
        "  \"notes\": string (short summary, <= 200 chars)\n"
        "}\n\n"
        "2) For element.type use one of: header, nav, hero, button, link, input, form, image, card, footer, text, icon.\n"
        "3) bbox coordinates should be [x, y, width, height] relative to the page (pixels). If you cannot determine exact numbers, use approximate integers.\n"
        "4) Put confidence for each element (0.0 to 1.0). Keep OCR snippets to the most important visible texts (max 10).\n"
        "5) Output MUST be JSON only (no markdown, no commentary).\n\n"
        "SCREENSHOTS:\n\n"
    )

    # Do NOT embed base64 images in text; pass images via content parts only.
    limited_images = image_paths[:max_images_for_model]

    raw_response = call_vision_model(
        model_key=image_model,
        system_prompt=system_prompt,
        user_prompt=user_prompt[:4000],
        image_paths=limited_images,
        max_tokens=1500,
        temperature=0.0,
    ) 

    parsed_response = None 
    try:
        parsed_response = json.loads(raw_response)
    except Exception as e:
        m = re.search(r"\{.*\}", raw_response, re.DOTALL) 

        if m:
            try:
                parsed_response = json.loads(m.group(0)) 
            except Exception:
                parsed_response = {"_raw": raw_response} 
        else:
            parsed_response = {"_raw": raw_response} 
    
    parsed_response = json.dumps(parsed_response, indent=2) 

    return parsed_response 



def recommendation_agent(structured_json: Dict[str, any], persona_note: str, fast_text_model: str = "grok-4.1-fast:free", max_issues: int = 4)-> str:
    system_prompt = (
        "You are a pragmatic senior UX/UI consultant with 20+ years of experience in digital product design, "
        "conversion rate optimization, and accessibility compliance.\n\n"
        
        "YOUR MISSION:\n"
        "Transform raw UI analysis data into actionable, prioritized recommendations that drive measurable improvements "
        "in user experience, accessibility compliance, and business conversions.\n\n"
        
        "EVALUATION FRAMEWORK:\n"
        "Apply these proven principles to assess and prioritize issues:\n"
        "- Nielsen's Usability Heuristics - identify violations and their severity\n"
        "- WCAG 2.2 AA/AAA Standards - flag accessibility barriers (contrast, semantics, keyboard, ARIA)\n"
        "- Gestalt Principles - evaluate visual grouping and information hierarchy\n"
        "- Fitts's Law - assess interactive target sizing and placement\n"
        "- Hick's Law - identify choice overload and decision paralysis points\n"
        "- Miller's Law - spot cognitive overload (too many options/items)\n"
        "- Jakob's Law - flag deviations from established web conventions\n"
        "- Conversion Best Practices - evaluate CTA clarity, trust signals, friction points\n\n"
        
        "PRIORITIZATION CRITERIA:\n"
        "- HIGH: Blocks conversions, violates WCAG, causes user abandonment\n"
        "- MEDIUM: Reduces efficiency, creates confusion, inconsistent patterns\n"
        "- LOW: Minor polish, nice-to-have improvements, edge cases\n\n"
        
        "CRITICAL: Output ONLY a valid JSON object. NO markdown, NO prose before or after JSON.\n\n"
        
        "Each recommendation MUST include:\n"
        "- Specific, actionable fix with implementation guidance\n"
        "- Clear rationale citing relevant principle/standard\n"
        "- Accurate severity and effort assessment\n"
        "- Business/UX impact explanation"
    )

    user_prompt = (
        "INPUT_OBSERVATIONS:\n"
        f"{json.dumps(structured_json)}\n\n"
        "TASK:\n"
        "1) Return a JSON object with keys:\n"
        "   - issues: array of {title, reason, severity (low|med|high), suggested_fix, estimated_effort (low|med|high)}\n"
        "   - positive: 1-sentence positive note\n"
        "   - confidence: 0.0-1.0\n"
        f"2) Limit issues to at most {max_issues}. Prioritize by impact to conversions and accessibility.\n"
        f"PERSONA_NOTE: {persona_note}\n\n"
        "OUTPUT JSON ONLY."
    )

    raw = call_vision_model(
        model_key=fast_text_model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        image_paths=None,  # text-only recommendation generation
        max_tokens=800,
        temperature=0.1,
    )

    # Try parse
    try:
        result_json = json.loads(raw.strip())
        return json.dumps(result_json, indent=2)
    except Exception:
        return raw
    

def polish_agent(rough_report: str, persona_note: str, polish_model: str = "gpt-4o-mini", report_tone: str = "formal, professional",) -> str:
    system_prompt = (
        "You are an expert UX writer, design strategist, and client communication specialist with deep expertise "
        "in translating technical UX/UI findings into compelling, actionable business recommendations.\n\n"
        
        "YOUR MISSION:\n"
        "Transform raw technical analysis into a polished, executive-ready report (500-800 words) that:\n"
        "- Communicates clearly to both technical and non-technical stakeholders\n"
        "- Justifies each recommendation with established design principles\n"
        "- Quantifies impact on business metrics (conversion, engagement, accessibility compliance)\n"
        "- Provides clear implementation roadmap with effort estimates\n\n"
        
        "WRITING GUIDELINES:\n"
        "- Start with executive summary highlighting top 3-5 priority items\n"
        "- Group recommendations by category (Visual Design, Usability, Accessibility, Conversion)\n"
        "- Use concrete, specific language ('Increase CTA button size to 44px' not 'make buttons bigger')\n"
        "- Reference standards naturally ('WCAG 2.2 contrast requirements', 'Nielsen's consistency heuristic')\n"
        "- Include severity tags: 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low\n"
        "- Balance critique with positive observations to maintain credibility\n\n"
        
        "CRITICAL RULES:\n"
        "- PRESERVE all factual findings - do NOT invent new issues\n"
        "- MAINTAIN technical accuracy while improving readability\n"
        "- DO NOT remove or downplay accessibility issues\n"
        "- DO NOT exaggerate severity or business impact\n"
        "- Each recommendation must have: Issue, Impact, Fix, Effort\n\n"
        
        "TONE:\n"
        "Professional yet approachable. Expert but not condescending. Data-driven but human-centered. "
        "Balance urgency (for critical issues) with encouragement (for strengths)."
    )

    user_prompt = (
        f"INPUT (do not invent new issues):\n{rough_report}\n\n"
        f"PERSONA: {persona_note}\n\n"
        f"DELIVERABLE: A polished client report in {report_tone} tone. Keep each recommendation short and include the severity tag."
    )

    raw = call_vision_model(model_key=polish_model, system_prompt=system_prompt,
        user_prompt=user_prompt,
        image_paths=None,  # polishing is text-only
        max_tokens=1200,
        temperature=0.2,
    )

    return raw



def analyze_page_and_report(image_paths: List[Path], page_url: str, persona_note: str, do_polish: bool = False,) -> Dict[str, Any]:
  
    # 1) Image analysis (expensive multimodal)
    image_analysis = image_analysis_agent(
        image_paths=image_paths,
        page_url=page_url,
        persona_note=persona_note,
        image_model="gemini-2.5-flash-image",
        max_images_for_model=6,
    )

    # 2) Fast text recommendation model
    rough_recommendations = recommendation_agent(
        structured_json=image_analysis,
        persona_note=persona_note,
        fast_text_model="grok-4.1-fast:free",
        max_issues=6,
    )
 
    if do_polish:
        final_report_text = polish_agent(
            rough_report=rough_recommendations,
            persona_note=persona_note,
            polish_model="gpt-4o-mini",
            report_tone="formal, professional",
        )

    if final_report_text:
        report =  final_report_text 
    else:
        report = rough_recommendations   
    
    return report 

       
    


