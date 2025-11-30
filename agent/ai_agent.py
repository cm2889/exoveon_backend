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


def call_vision_model(model_key: str, system_prompt: str, user_prompt: str, image_paths: Optional[List[Path]] = None, max_tokens: int = 20000, temperature: float = 0.0,) -> str:
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
                {"role": "system", "content": system_prompt[:10000]},
                {"role": "user", "content": compact_parts},
            ]
            response = client.chat.completions.create(
                model=model_id,
                messages=compact_messages,
                max_tokens=min(max_tokens, 10000),
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


def image_analysis_agent(image_paths: List[Path], page_url: str, persona_note: str, image_model: str = "gemini-2.5-flash-image", max_images_for_model: int = 6 )-> str: 
  
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
        "Be thorough yet concise. Reference specific heuristics, principles, and WCAG criteria. "
        "Prioritize by business impact and user pain points. Think like both a designer and a user advocate."
    )

    user_prompt = (
        f"PAGE_URL: {page_url}\n\n"
        f"PERSONA_NOTE: {persona_note}\n\n"
        f"Analyze ALL {len(image_paths)} screenshot(s) of this webpage comprehensively.\n\n"
        "For each screenshot, provide:\n"
        "- Screenshot Number\n"
        "- Section/Category (Visual Hierarchy, Usability Issues, Accessibility Gaps, Conversion Blockers, Design Inconsistencies, Mobile Considerations)\n"
        "- Priority Level with emoji (🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low)\n"
        "- Specific Location (which element/section)\n"
        "- Issue Description (with principle/standard references)\n"
        "- Impact Assessment\n"
        "- Actionable Recommendations (with effort estimate)\n\n"
        "Include Positive Observations throughout.\n"
        "End with an Overall Summary.\n\n"
        "SCREENSHOTS TO ANALYZE:\n\n"
    )
  
    # Limit images for model context
    limited_images = image_paths[:max_images_for_model]

    print(f"[DEBUG] Sending {len(limited_images)} images to vision model for comprehensive narrative analysis...")

    raw_response = call_vision_model(
        model_key=image_model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        image_paths=limited_images,
        max_tokens=16000,  # Increased for detailed narrative
        temperature=0.1,  # Slight temperature for natural writing
    ) 

    print(f"[DEBUG] Received comprehensive analysis ({len(raw_response)} chars)")
    return raw_response 



def recommendation_agent(narrative_analysis: str, persona_note: str, fast_text_model: str = "grok-4.1-fast:free")-> str:
    """
    This agent is now optional - the narrative analysis is already comprehensive.
    Use this only if you want a second-pass refinement or summarization.
    """
    system_prompt = (
        "You are a pragmatic senior UX/UI consultant reviewing a comprehensive UI/UX analysis report.\n\n"
        
        "YOUR MISSION:\n"
        "Enhance and refine the existing analysis by:\n"
        "- Ensuring all issues cite specific principles (Nielsen, WCAG, Fitts, Hick, Miller, Jakob)\n"
        "- Verifying severity tags are accurate (🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low)\n"
        "- Confirming actionable recommendations with effort estimates\n"
        "- Maintaining the comprehensive, narrative format\n"
        "- Preserving all positive observations\n\n"
        
        "DO NOT:\n"
        "- Remove or downplay any findings\n"
        "- Convert to JSON or executive summary format\n"
        "- Add new issues not present in the original analysis\n"
        "- Change the overall structure or tone\n\n"
        
        "OUTPUT: Return the refined analysis in the same comprehensive narrative format."
    )

    user_prompt = (
        f"PERSONA_NOTE: {persona_note}\n\n"
        "ORIGINAL COMPREHENSIVE ANALYSIS:\n\n"
        f"{narrative_analysis}\n\n"
        "Please review and enhance this analysis while maintaining its comprehensive narrative format."
    )

    print("[DEBUG] Running optional recommendation refinement...")

    raw = call_vision_model(
        model_key=fast_text_model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        image_paths=None,
        max_tokens=16000,
        temperature=0.1,
    )

    print(f"[DEBUG] Refinement complete ({len(raw)} chars)")
    return raw
    

def polish_agent(narrative_report: str, persona_note: str, polish_model: str = "gpt-4o-mini", report_tone: str = "formal, professional",) -> str:
    """
    Optional polishing pass - only use if the narrative needs minor editorial improvements.
    The comprehensive analysis from image_analysis_agent is already detailed and well-structured.
    """
    system_prompt = (
        "You are an expert UX writer and editor specializing in comprehensive UI/UX analysis reports.\n\n"
        
        "YOUR MISSION:\n"
        "Polish the existing comprehensive analysis for clarity and professionalism while:\n"
        "- Maintaining the detailed, narrative format with all sections\n"
        "- Preserving ALL technical findings, severity tags, and recommendations\n"
        "- Ensuring consistent use of design principles and standards references\n"
        "- Improving readability without removing detail\n"
        "- Keeping all positive observations\n\n"
        
        "CRITICAL RULES:\n"
        "- DO NOT convert to executive summary format\n"
        "- DO NOT remove or condense findings\n"
        "- DO NOT change severity assessments\n"
        "- DO NOT add new issues\n"
        "- MAINTAIN the comprehensive narrative structure\n\n"
        
        "TONE:\n"
        f"{report_tone} - Professional yet approachable. Expert but not condescending."
    )

    user_prompt = (
        f"PERSONA: {persona_note}\n\n"
        "COMPREHENSIVE ANALYSIS TO POLISH:\n\n"
        f"{narrative_report}\n\n"
        "Please polish this analysis for clarity and professionalism while preserving all content and structure."
    )

    print("[DEBUG] Running optional polish pass...")

    raw = call_vision_model(
        model_key=polish_model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        image_paths=None,
        max_tokens=16000,
        temperature=0.2,
    )

    print(f"[DEBUG] Polish complete ({len(raw)} chars)")
    return raw



def analyze_page_and_report(image_paths: List[Path],  page_url: str, persona_note: str, do_refinement: bool = False, do_polish: bool = False, ) -> str:
    """
    Main analysis pipeline - now generates comprehensive narrative reports like sam.txt.
    
    Args:
        image_paths: List of screenshot paths to analyze
        page_url: URL being analyzed
        persona_note: Context about the persona/focus area
        do_refinement: Optional second-pass to refine findings (rarely needed)
        do_polish: Optional editorial polish (rarely needed)
    
    Returns:
        Comprehensive narrative analysis report
    """
    
    print(f"\n{'='*80}")
    print(f"STARTING COMPREHENSIVE UX/UI ANALYSIS")
    print(f"{'='*80}")
    print(f"URL: {page_url}")
    print(f"Screenshots: {len(image_paths)}")
    print(f"Persona: {persona_note}")
    print(f"{'='*80}\n")
  
    # 1) Comprehensive narrative analysis (primary output - matches sam.txt approach)
    print("STAGE 1: Comprehensive Visual Analysis")
    print("-" * 80)
    
    comprehensive_analysis = image_analysis_agent(
        image_paths=image_paths,
        page_url=page_url,
        persona_note=persona_note,
        image_model="gemini-2.5-flash-image",
        max_images_for_model=6,
    )

    print(f"\n✓ Analysis complete: {len(comprehensive_analysis)} characters")
    print(f"Preview: {comprehensive_analysis[:200]}...\n")

    # 2) Optional refinement pass (usually not needed - the first pass is comprehensive)
    if do_refinement:
        print("STAGE 2: Refinement Pass (Optional)")
        print("-" * 80)
        
        refined_analysis = recommendation_agent(
            narrative_analysis=comprehensive_analysis,
            persona_note=persona_note,
            fast_text_model="grok-4.1-fast:free",
        )
        
        print(f"✓ Refinement complete: {len(refined_analysis)} characters\n")
        comprehensive_analysis = refined_analysis
 
    # 3) Optional polish pass (usually not needed - for final editorial touch only)
    if do_polish:
        print("STAGE 3: Editorial Polish (Optional)")
        print("-" * 80)
        
        polished_analysis = polish_agent(
            narrative_report=comprehensive_analysis,
            persona_note=persona_note,
            polish_model="gpt-4o-mini",
            report_tone="formal, professional",
        )
        
        print(f"✓ Polish complete: {len(polished_analysis)} characters\n")
        comprehensive_analysis = polished_analysis

    print(f"\n{'='*80}")
    print(f"ANALYSIS PIPELINE COMPLETE")
    print(f"{'='*80}")
    print(f"Final report length: {len(comprehensive_analysis)} characters")
    print(f"{'='*80}\n")

    return comprehensive_analysis 


# Debug/Test helper: run end-to-end analysis with sample data
def debug_run(image_paths: List[Path], page_url: str, persona_note: str, do_refinement: bool = False, do_polish: bool = False) -> str:
    """
    Quick test function to validate the entire pipeline.
    Returns the final comprehensive analysis report.
    """
    print("\n" + "="*80)
    print("DEBUG RUN - Testing Analysis Pipeline")
    print("="*80 + "\n")
    
    result = analyze_page_and_report(
        image_paths=image_paths,
        page_url=page_url,
        persona_note=persona_note,
        do_refinement=do_refinement,
        do_polish=do_polish,
    )
    
    print("\n" + "="*80)
    print("DEBUG RUN COMPLETE")
    print("="*80)
    print(f"\nFinal report preview (first 500 chars):\n")
    print(result[:500])
    print("\n...")
    print(f"\nTotal length: {len(result)} characters")
    print("="*80 + "\n")
    
    return result

       
    


