import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from decouple import config
from openai import OpenAI

from agent.reviews_collector import find_app_id_by_name, fetch_all_reviews

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=config("OPENROUTER_API_KEY"),
)

MODEL_MAP: Dict[str, str] = {
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
    "qwen-7b-chat": "qwen/qwen-7b-chat",
}


def _extract_json_from_text(text: str) -> str:
    """Try to extract a JSON string from possible fenced Markdown or mixed text.

    Returns the best-effort JSON substring, or the original text if not found.
    """
    if not text:
        return ""
    # Prefer explicit json fences
    if "```json" in text:
        start = text.find("```json") + len("```json")
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    # Generic fence
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    # Attempt to locate first and last curly braces
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return text[first : last + 1].strip()
    return text.strip()


def call_llm(
    model_name: str,
    user_content: str,
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    retries: int = 2,
) -> str:
    
    model_id = MODEL_MAP.get(model_name)
    if not model_id:
        raise ValueError(f"Unknown model: {model_name}")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:  # Network/transient errors
            last_err = exc
            
    raise RuntimeError(f"LLM call failed after {retries + 1} attempts: {last_err}")


def _safe_load_json(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Load JSON with best-effort extraction; return (data, error)."""
    candidate = _extract_json_from_text(text)
    try:
        return json.loads(candidate), None
    except json.JSONDecodeError as e:
        return None, f"Failed to parse JSON: {e}"


def app_review_analysis(reviews_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    reviews_json = json.dumps(reviews_list, ensure_ascii=False, indent=2)

    system_prompt = """
        You are an expert Mobile Application Analyst with 30 years of experience in:
        - Mobile app development across iOS and Android platforms
        - App Store Optimization (ASO) and user retention strategies
        - Mobile app legal compliance (GDPR, COPPA, accessibility laws, data privacy)
        - User experience design and mobile UI/UX best practices
        - Play Store and App Store guidelines and policies
        - Technical troubleshooting of mobile app issues
        - Competitive analysis and market positioning

        Your role is to analyze Google Play Store reviews and provide actionable insights for app improvement.

        ANALYSIS REQUIREMENTS:

        1. SENTIMENT CLASSIFICATION:
        - Classify each review as: POSITIVE, NEGATIVE, or NEUTRAL
        - Provide exact counts and percentages
        - Consider: rating score, content tone, specific complaints/praise

        2. KEY ISSUES IDENTIFICATION:
        - Technical issues (crashes, bugs, performance, compatibility)
        - UX/UI problems (navigation, design, usability)
        - Feature requests and missing functionality
        - Privacy/security concerns
        - Payment and subscription issues
        - Legal compliance concerns

        3. POSITIVE HIGHLIGHTS:
        - What users love most
        - Competitive advantages mentioned
        - Strong features to maintain and promote

        4. RECOMMENDATIONS:
        - Priority fixes (HIGH/MEDIUM/LOW)
        - Feature development roadmap
        - Legal/compliance actions needed
        - Customer support improvements
        - Marketing messaging opportunities

        5. TREND ANALYSIS:
        - Recurring themes across multiple reviews
        - Version-specific feedback patterns
        - User segment insights (new vs returning users)

        OUTPUT FORMAT (JSON):
        {
        "sentiment_summary": {
            "positive_count": <int>,
            "negative_count": <int>,
            "neutral_count": <int>,
            "positive_percentage": <float>,
            "negative_percentage": <float>,
            "neutral_percentage": <float>
        },
        "rating_distribution": {
            "1_star": <int>,
            "2_star": <int>,
            "3_star": <int>,
            "4_star": <int>,
            "5_star": <int>
        },
        "key_issues": [
            {
            "category": "<Technical|UX|Feature|Privacy|Payment|Other>",
            "issue": "<brief description>",
            "severity": "<HIGH|MEDIUM|LOW>",
            "frequency": <int>
            }
        ],
        "positive_highlights": [
            {
            "feature": "<feature name>",
            "mentions": <int>,
            "user_quotes": ["<quote1>", "<quote2>"]
            }
        ],
        "recommendations": [
            {
            "priority": "<HIGH|MEDIUM|LOW>",
            "action": "<specific recommendation>",
            "category": "<Technical|UX|Feature|Compliance|Support|Marketing>",
            "expected_impact": "<description>",
            "estimated_effort": "<Quick Win|Short-term|Long-term>"
            }
        ],
        "compliance_alerts": [
            {
            "type": "<GDPR|COPPA|Accessibility|Privacy|Other>",
            "concern": "<description>",
            "action_required": "<immediate action>"
            }
        ],
        "executive_summary": "<2-3 paragraph overview with key metrics and top 3 action items>"
        }

        Be specific, data-driven, and actionable. Use your 30 years of expertise to prioritize what matters most.
    """

    try:
        analysis_response = call_llm(
            model_name="gpt-4.1-mini",  # Prefer strong text model for analysis
            user_content=reviews_json,
            system_prompt=system_prompt,
            max_tokens=8000,
        )
    except Exception as exc:
        return {"error": f"LLM analysis call failed: {exc}"}
    
    # Parse JSON response
    data, err = _safe_load_json(analysis_response)
    if data is not None:
        return data
    return {"error": err or "Unknown JSON parse error", "raw_response": analysis_response}


def generate_visualizations(analysis_data: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, str]:
    """Generate pie charts and bar graphs for the analysis report.

    Returns a dict mapping chart names to file paths. Uses non-interactive backend.
    """
  

    if output_dir is None:
        output_dir = Path("./analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    chart_paths: Dict[str, str] = {}

    # 1) Sentiment pie chart
    sentiment = analysis_data.get("sentiment_summary") or {}
    counts = [
        int(sentiment.get("positive_count", 0) or 0),
        int(sentiment.get("negative_count", 0) or 0),
        int(sentiment.get("neutral_count", 0) or 0),
    ]
    if sum(counts) > 0:
        fig, ax = plt.subplots(figsize=(10, 7))
        labels = ["Positive", "Negative", "Neutral"]
        colors = ["#4CAF50", "#F44336", "#FFC107"]
        explode = (0.05, 0.0, 0.0)
        ax.pie(
            counts,
            explode=explode,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            shadow=False,
            startangle=90,
        )
        ax.set_title("Sentiment Distribution", fontsize=16, fontweight="bold")
        path = output_dir / "sentiment_pie_chart.png"
        plt.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        chart_paths["sentiment_pie"] = str(path)

    # 2) Rating distribution bar chart
    ratings = analysis_data.get("rating_distribution") or {}
    rating_counts = [
        int(ratings.get("1_star", 0) or 0),
        int(ratings.get("2_star", 0) or 0),
        int(ratings.get("3_star", 0) or 0),
        int(ratings.get("4_star", 0) or 0),
        int(ratings.get("5_star", 0) or 0),
    ]
    if sum(rating_counts) > 0:
        fig, ax = plt.subplots(figsize=(12, 7))
        stars = ["1 Star", "2 Star", "3 Star", "4 Star", "5 Star"]
        colors_bar = ["#D32F2F", "#F57C00", "#FBC02D", "#8BC34A", "#4CAF50"]
        bars = ax.bar(stars, rating_counts, color=colors_bar, edgecolor="black", linewidth=1.0)
        ax.set_xlabel("Rating", fontsize=14, fontweight="bold")
        ax.set_ylabel("Number of Reviews", fontsize=14, fontweight="bold")
        ax.set_title("Rating Distribution", fontsize=16, fontweight="bold")
        ax.grid(axis="y", alpha=0.25)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, h, f"{int(h)}", ha="center", va="bottom", fontsize=10)
        path = output_dir / "rating_distribution.png"
        plt.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        chart_paths["rating_distribution"] = str(path)

    # 3) Key issues horizontal bar chart
    issues = analysis_data.get("key_issues") or []
    if isinstance(issues, list) and issues:
        sorted_issues = sorted(issues, key=lambda x: int(x.get("frequency", 0) or 0), reverse=True)[:10]
        if sorted_issues:
            fig, ax = plt.subplots(figsize=(12, 8))
            labels = [f"{i.get('category', 'Unknown')}: {str(i.get('issue', ''))[:40]}" for i in sorted_issues]
            freqs = [int(i.get("frequency", 0) or 0) for i in sorted_issues]
            severity_colors = {"HIGH": "#F44336", "MEDIUM": "#FF9800", "LOW": "#4CAF50"}
            colors = [severity_colors.get(str(i.get("severity", "LOW")), "#9E9E9E") for i in sorted_issues]
            y = range(len(labels))
            bars = ax.barh(list(y), freqs, color=colors, edgecolor="black", linewidth=1.0)
            ax.set_yticks(list(y))
            ax.set_yticklabels(labels, fontsize=10)
            ax.set_xlabel("Frequency", fontsize=14, fontweight="bold")
            ax.set_title("Top 10 Key Issues (Color = Severity)", fontsize=16, fontweight="bold")
            ax.grid(axis="x", alpha=0.25)
            for idx, (bar, freq) in enumerate(zip(bars, freqs)):
                ax.text(freq, idx, f" {freq}", va="center", fontsize=9)
            path = output_dir / "key_issues_chart.png"
            plt.savefig(path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            chart_paths["key_issues"] = str(path)

    return chart_paths


def generate_ai_report(analysis_data: Dict[str, Any]) -> str:
    """Generate a professional Markdown report using an LLM.

    The output is ASCII-only and avoids emojis or decorative symbols.
    """
    system_prompt = (
        "You are a senior mobile application product and engineering analyst. "
        "Generate a concise, professional MARKDOWN report based ONLY on the provided JSON analysis data. "
        "Do NOT add emojis, decorative unicode, marketing fluff, or unverifiable claims. Maintain a neutral, executive tone. "
        "Sections required in this exact order:\n"
        "# Mobile App Review Analysis Report\n"
        "## 1. Executive Summary\n"
        "## 2. Sentiment Overview\n"
        "## 3. Rating Distribution\n"
        "## 4. Key Issues (grouped by severity: HIGH, MEDIUM, LOW)\n"
        "## 5. Positive Highlights\n"
        "## 6. Recommendations (priority ordered: HIGH, MEDIUM, LOW)\n"
        "## 7. Compliance Alerts\n"
        "## 8. Data Snapshot\n"
        "## 9. Next Steps\n"
        "Rules:\n"
        "- No emojis.\n"
        "- Use plain ASCII only.\n"
        "- Use bullet lists where helpful.\n"
        "- Keep Executive Summary to <= 180 words.\n"
        "- If a section has no data, write 'No data available.'\n"
        "- In Data Snapshot include raw counts from sentiment and rating_distribution.\n"
        "Close with a short disclaimer: 'This report is generated from user review data and may not reflect full production telemetry.'"
    )

    analysis_json = json.dumps(analysis_data, ensure_ascii=True)
    try:
        report_md = call_llm(
            model_name="gpt-4.1-mini",
            user_content=analysis_json,
            system_prompt=system_prompt,
            max_tokens=4000,
        )
        # Strip fenced code blocks if any
        txt = report_md.strip()
        if txt.startswith("```"):
            start = txt.find("\n") + 1
            end = txt.rfind("```")
            if end > start:
                txt = txt[start:end].strip()
        # Ensure ASCII-only
        try:
            txt.encode("ascii")
        except UnicodeEncodeError:
            txt = txt.encode("ascii", errors="ignore").decode("ascii")
        return txt
    except Exception as exc:
        return f"Report generation via AI failed: {exc}"


def generate_text_report(analysis_data: Dict[str, Any], chart_paths: Dict[str, str]) -> str:
    """Fallback static report generator (no emojis)."""
    lines: List[str] = []
    lines.append("# Mobile App Review Analysis Report")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. Executive Summary")
    lines.append(analysis_data.get("executive_summary", "No data available."))
    lines.append("")
    # Sentiment
    sentiment = analysis_data.get("sentiment_summary", {})
    lines.append("## 2. Sentiment Overview")
    if sentiment:
        lines.append(f"Positive: {sentiment.get('positive_count', 0)} ({sentiment.get('positive_percentage', 0):.1f}%)")
        lines.append(f"Negative: {sentiment.get('negative_count', 0)} ({sentiment.get('negative_percentage', 0):.1f}%)")
        lines.append(f"Neutral: {sentiment.get('neutral_count', 0)} ({sentiment.get('neutral_percentage', 0):.1f}%)")
    else:
        lines.append("No data available.")
    lines.append("")
    # Ratings
    ratings = analysis_data.get("rating_distribution", {})
    lines.append("## 3. Rating Distribution")
    if ratings:
        total_reviews = sum(ratings.get(f"{i}_star", 0) for i in range(1, 6))
        for i in range(5, 0, -1):
            count = ratings.get(f"{i}_star", 0)
            pct = (count / total_reviews * 100) if total_reviews else 0
            lines.append(f"{i} Star: {count} ({pct:.1f}%)")
    else:
        lines.append("No data available.")
    lines.append("")
    # Key Issues
    issues = analysis_data.get("key_issues", [])
    lines.append("## 4. Key Issues")
    if issues:
        high = [i for i in issues if i.get('severity') == 'HIGH']
        med = [i for i in issues if i.get('severity') == 'MEDIUM']
        low = [i for i in issues if i.get('severity') == 'LOW']
        def section(label, coll):
            lines.append(f"### {label}")
            if not coll:
                lines.append("None")
            for item in coll:
                lines.append(f"- {item.get('category')}: {item.get('issue')} (freq: {item.get('frequency', 0)})")
        section("HIGH", high)
        section("MEDIUM", med)
        section("LOW", low)
    else:
        lines.append("No data available.")
    lines.append("")
    # Positive Highlights
    highlights = analysis_data.get("positive_highlights", [])
    lines.append("## 5. Positive Highlights")
    if highlights:
        for h in highlights:
            lines.append(f"- {h.get('feature')}: mentions {h.get('mentions', 0)}")
    else:
        lines.append("No data available.")
    lines.append("")
    # Recommendations
    recs = analysis_data.get("recommendations", [])
    lines.append("## 6. Recommendations")
    if recs:
        for r in recs:
            lines.append(f"- {r.get('priority')} {r.get('category')}: {r.get('action')} (impact: {r.get('expected_impact')}, effort: {r.get('estimated_effort')})")
    else:
        lines.append("No data available.")
    lines.append("")
    # Compliance Alerts
    compliance = analysis_data.get("compliance_alerts", [])
    lines.append("## 7. Compliance Alerts")
    if compliance:
        for c in compliance:
            lines.append(f"- {c.get('type')}: {c.get('concern')} (action: {c.get('action_required')})")
    else:
        lines.append("No data available.")
    lines.append("")
    # Data Snapshot
    lines.append("## 8. Data Snapshot")
    lines.append(f"Sentiment raw: {sentiment if sentiment else '{}'}")
    lines.append(f"Ratings raw: {ratings if ratings else '{}'}")
    lines.append("")
    lines.append("## 9. Next Steps")
    lines.append("Review HIGH severity issues, schedule sprint triage, validate recurring technical complaints against crash/error telemetry.")
    lines.append("")
    lines.append("Disclaimer: This report is generated from user review data and may not reflect full production telemetry.")
    return "\n".join(lines)


def analyze_app_and_report(app_name: str, max_reviews: int = 1000, output_dir: str = "./analysis") -> Dict[str, Any]:
    """Complete pipeline: Fetch reviews → Analyze with AI → Generate reports & charts.
    
    Args:
        app_name: App package name or search query
        max_reviews: Maximum number of reviews to fetch
        output_dir: Directory to save reports and charts
    
    Returns:
        Dict with analysis data and file paths
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Step 1: Fetch reviews
        app_id = find_app_id_by_name(app_name)
        if not app_id:
            return {"error": f"App not found: {app_name}"}
       
        reviews_list = fetch_all_reviews(app_id, max_total=max_reviews)
        # Normalize reviews
        reviews_data = [
            {"score": r.score, "content": r.content} for r in reviews_list
        ]
        # Step 2: AI Analysis
        analysis_data = app_review_analysis(reviews_data)
        if "error" in analysis_data:
            with open(output_path / "raw_analysis.txt", "w", encoding="utf-8") as f:
                f.write(analysis_data.get("raw_response", ""))
            return analysis_data
        # Step 3: Charts
        chart_paths = generate_visualizations(analysis_data, output_path)
        # Step 4: AI Report
        report_text = generate_ai_report(analysis_data)
        if report_text.startswith("Report generation via AI failed"):
            report_text = generate_text_report(analysis_data, chart_paths)
        report_path = output_path / "analysis_report.md"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        json_path = output_path / "analysis_data.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        return {
            "success": True,
            "app_id": app_id,
            "reviews_analyzed": len(reviews_data),
            "analysis_data": analysis_data,
            "report_path": str(report_path),
            "json_path": str(json_path),
            "chart_paths": chart_paths,
        }
    except Exception as e:
        pass 

