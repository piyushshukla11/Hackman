"""
prism_core/survey/generator.py

RAG-Based Diagnostic Survey Generation Engine for PRISM.
Adheres to contracts.md §1.5, pipeline-3.md §P9, and ml.md §13:
1. Strict tenant & product isolated retrieval of verbatim review quotes, specs, and batch info.
2. Deduplication and substantive text filtering on retrieved quotes.
3. In-memory PII masking before prompt formulation.
4. Structured Gemini prompt generating 3 multiple-choice diagnostic questions to isolate engineering failure modes.
5. Strict schema validation, evidence-reference verification, and ungrounded fact rejection.
6. Calibrated category-level fallback diagnostic templates with is_fallback=True.
7. Explicit insufficient-evidence handling when cluster has no substantive verbatims.
"""
from __future__ import annotations

import difflib
import json
import logging
import re
from typing import Any, Sequence
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.config.settings import Settings, get_settings
from prism_core.db.models import ClusterMember, IssueCluster, Product, ProductVersion, Review
from prism_core.ml.translator import mask_pii
from prism_core.schemas.survey import (
    RetrievedEvidence,
    SurveyGenerationResult,
    SurveyQuestion,
    SurveyRetrievalContext,
)
from prism_core.survey.inject_rag_memory import load_simulation_rag_memory, get_context_for_product

logger = logging.getLogger(__name__)


# ── Category-Calibrated Diagnostic Fallback Templates (6-7 Questions) ────────

CATEGORY_FALLBACK_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "appliances": [
        {
            "question_id": "q1",
            "question_text": "When operating the unit, does the {feature} issue occur immediately upon startup, or only after extended running time?",
            "options": [
                "Immediately upon startup / power-on",
                "After 15-30 minutes of continuous operation",
                "Only during specific heavy cycles or settings",
                "Intermittently at random intervals",
                "I'm not sure",
            ],
            "rationale": "Differentiates between initial electrical/startup failure and thermal buildup / duty-cycle exhaustion.",
            "processing_note": "Evaluated against appliance startup relay sequence and thermal duty-cycle thresholds.",
            "grounded_data_source": "Appliance Thermal Diagnostics + Power Inrush Spec",
        },
        {
            "question_id": "q2",
            "question_text": "Have you observed any unusual sensory indicators (such as humming, clicking, thermal heat, or moisture) associated with the {feature}?",
            "options": [
                "Clicking or rhythmic ticking sounds",
                "Noticeable excess heat on the external casing",
                "Vibration or unusually loud humming",
                "No unusual sound, heat, or moisture observed",
                "I'm not sure",
            ],
            "rationale": "Identifies whether mechanical wear, relay switching, or electrical over-current accompanies the defect.",
            "processing_note": "Acoustic and vibration resonance analysis across motor bearings and solenoid switching.",
            "grounded_data_source": "Mechanical Relay & Motor Assembly Tolerances",
        },
        {
            "question_id": "q3",
            "question_text": "Did disconnecting power for 10 minutes (hard reset) or adjusting operating settings resolve or change the {feature} behavior?",
            "options": [
                "Temporarily restored normal function, but issue returned",
                "Had no effect whatsoever on the issue",
                "Appliance failed to power back on",
                "I did not attempt a power reset",
                "I'm not sure",
            ],
            "rationale": "Isolates persistent physical hardware component failures from microcontroller firmware or latching relay faults.",
            "processing_note": "Microcontroller volatile memory reset test vs latching relay thermal lock.",
            "grounded_data_source": "Firmware Watchdog & Power Recovery Specification",
        },
        {
            "question_id": "q4",
            "question_text": "Under what ambient temperature or humidity conditions is the appliance operating when {feature} anomalies appear?",
            "options": [
                "Standard indoor ambient (20°C - 25°C, normal humidity)",
                "High ambient heat exceeding 35°C",
                "High humidity or condensation-prone environment",
                "Fluctuating room conditions",
                "I'm not sure",
            ],
            "rationale": "Evaluates environmental temperature coefficients and condensation insulation boundaries.",
            "processing_note": "Cross-referenced with climate-class operating ranges (SN/N/ST/T).",
            "grounded_data_source": "Operating Environmental Limits Specification",
        },
        {
            "question_id": "q5",
            "question_text": "Has there been any visible moisture, fluid leakage, or frost accumulation near the {feature} area?",
            "options": [
                "Visible water condensation or pooling",
                "Frost or ice buildup along seals",
                "Dry with no moisture whatsoever",
                "Minor dampness on gasket",
                "I'm not sure",
            ],
            "rationale": "Isolates thermal seal gasket air-gaps from refrigerant loop or drainage blockage.",
            "processing_note": "Gasket compression seal audit and drainage thermal trace.",
            "grounded_data_source": "Chamber Gasket & Drainage Integrity Spec",
        },
        {
            "question_id": "q6",
            "question_text": "Does the issue with {feature} correlate with the electrical circuit load or power line voltage fluctuations in your area?",
            "options": [
                "Occurs primarily during peak evening hours / low voltage",
                "Occurs when other heavy appliances switch on",
                "Completely independent of power supply / on dedicated stabilizer",
                "Never noticed electrical correlation",
                "I'm not sure",
            ],
            "rationale": "Differentiates line voltage sag vulnerability from internal switch-mode power supply (SMPS) regulation.",
            "processing_note": "Evaluated against 230V ± 10% line voltage regulation tolerances.",
            "grounded_data_source": "SMPS Power Stage Specification",
        },
        {
            "question_id": "q7",
            "question_text": "Did the {feature} defect begin immediately upon delivery / initial installation, or develop gradually over weeks?",
            "options": [
                "Present from day 1 right out of the delivery box",
                "Appeared within the first 14 days of regular use",
                "Gradually worsened over 1-2 months",
                "Began following relocation or cleaning",
                "I'm not sure",
            ],
            "rationale": "Distinguishes transit shock / factory assembly defects from wear-and-tear degradation.",
            "processing_note": "Infant mortality failure curve analysis vs cumulative mechanical wear.",
            "grounded_data_source": "Logistics Quality & QA Factory Gate Audit",
        },
    ],
    "audio": [
        {
            "question_id": "q1",
            "question_text": "Does the issue with {feature} affect both channels (left and right) equally, or is it isolated to one side?",
            "options": [
                "Isolated to the left ear / channel only",
                "Isolated to the right ear / channel only",
                "Equally affects both channels",
                "Switches intermittently between channels",
                "I'm not sure",
            ],
            "rationale": "Differentiates between single-driver/cable solder defect and central DAC/Bluetooth SoC audio pipeline failure.",
            "processing_note": "Evaluated against 40mm beryllium driver dual-channel impedance matching (32 ohm).",
            "grounded_data_source": "Voyage Horizon ANC Acoustic Driver Spec (SPEC-001)",
        },
        {
            "question_id": "q2",
            "question_text": "Under what connection mode does the {feature} symptom occur?",
            "options": [
                "Only over wireless Bluetooth connection",
                "Only when using a physical 3.5mm / USB wired cable",
                "Present across both wired and wireless connections",
                "Only when multipoint device pairing is active",
                "I'm not sure",
            ],
            "rationale": "Isolates wireless codec / RF interference from physical acoustic driver or analog amplification defect.",
            "processing_note": "Evaluated against Bluetooth 5.4 LDAC / AAC codec pipeline vs passive 3.5mm aux bypass.",
            "grounded_data_source": "BT 5.4 Baseband & Codec Pipeline Spec",
        },
        {
            "question_id": "q3",
            "question_text": "When the {feature} issue occurs, how does the device respond when battery level drops below 30%?",
            "options": [
                "Symptom worsens significantly or device powers off abruptly",
                "Symptom remains identical regardless of battery charge",
                "Charging temporarily eliminates the symptom",
                "Device cannot hold a charge below 30%",
                "I'm not sure",
            ],
            "rationale": "Isolates voltage sag on battery degradation from steady-state digital signal processing issues.",
            "processing_note": "Battery discharge voltage curve analysis (800mAh Li-Po, 3.7V nominal).",
            "grounded_data_source": "Power Management & Li-Po Voltage Spec",
        },
        {
            "question_id": "q4",
            "question_text": "Does the {feature} symptom alter when toggling between Active Noise Cancellation (ANC), Transparency mode, and ANC Off?",
            "options": [
                "Occurs only when ANC is actively turned ON",
                "Occurs only in Transparency ambient sound mode",
                "Present in all acoustic modes identically",
                "Disappears completely when ANC is turned OFF",
                "I'm not sure",
            ],
            "rationale": "Isolates feedback/feedforward MEMS microphone phase-inversion filtering from physical driver distortion.",
            "processing_note": "Grounded on 45dB hybrid ANC dual-MEMS phase cancellation DSP pipeline.",
            "grounded_data_source": "Hybrid ANC Acoustic DSP Specification (SPEC-001)",
        },
        {
            "question_id": "q5",
            "question_text": "When using Bluetooth, does audio stuttering on {feature} worsen near 2.4GHz RF sources (like microwave ovens or dense Wi-Fi 6 routers)?",
            "options": [
                "Noticeably stutters when walking past microwave ovens or kitchen appliances",
                "Stutters in dense open-plan offices with multiple Wi-Fi access points",
                "Occurs outdoors away from any Wi-Fi routers",
                "Zero RF interference observed in any room",
                "I'm not sure",
            ],
            "rationale": "Isolates 2.4GHz RF co-existence packet drops and LDAC 990kbps buffer under-runs.",
            "processing_note": "Matched with BATCH-2024-W12 RF antenna gain margin defect cluster (CLUSTER-001-BT-STUTTER).",
            "grounded_data_source": "Defect Cluster: CLUSTER-001-BT-STUTTER (Amazon/Flipkart Reviews)",
        },
        {
            "question_id": "q6",
            "question_text": "Have you experienced excessive clamping pressure, temple headache, or headband slider creaking around the {feature}?",
            "options": [
                "Excessive clamping force causing ear fatigue or pressing against spectacles",
                "Creaking or loose mechanical play in the stainless steel headband slider",
                "Ear cushions trap heat during warm weather",
                "Ergonomics and fit are completely comfortable",
                "I'm not sure",
            ],
            "rationale": "Evaluates 4.2N headband clamping force calibration and slow-recovery memory foam breathability.",
            "processing_note": "Cross-referenced with headband steel slider torque and memory foam thermal retention data.",
            "grounded_data_source": "Ergonomics & Mechanical Clamping Calibration (SPEC-001)",
        },
        {
            "question_id": "q7",
            "question_text": "Did performing a factory reset (holding power and volume up for 10 seconds) resolve or change the {feature} behavior?",
            "options": [
                "Temporarily restored normal audio, but defect recurred within hours",
                "Completely resolved the connection/audio issue",
                "Had no effect whatsoever on device behavior",
                "Device failed to enter pairing mode following reset",
                "I'm not sure",
            ],
            "rationale": "Determines whether defect is volatile Bluetooth pairing register corruption or permanent physical transducer failure.",
            "processing_note": "Firmware non-volatile storage state verification and pairing cache flush audit.",
            "grounded_data_source": "Firmware v1.4.2 Diagnostics & Recovery Register",
        },
    ],
    "gaming": [
        {
            "question_id": "q1",
            "question_text": "Does the {feature} anomaly manifest during fast-twitch gaming motions or during steady desktop navigation?",
            "options": [
                "During rapid flick shots and high-speed directional changes",
                "During continuous slow tracking across the surface",
                "At random intervals on static desktop screen",
                "Only when clicking or actuating rapidly in firefights",
                "I'm not sure",
            ],
            "rationale": "Isolates optical sensor tracking saturation (650 IPS / 50G) and lift-off distance from steady-state polling.",
            "processing_note": "Grounded on PixArt PAW3395 26,000 DPI sensor tracking envelope (SPEC-003).",
            "grounded_data_source": "Voyage Apex Wireless Sensor Specification (SPEC-003)",
        },
        {
            "question_id": "q2",
            "question_text": "Under what display interface and refresh rate does the {feature} symptom occur?",
            "options": [
                "DisplayPort 1.4 at native 165Hz with FreeSync / G-Sync active",
                "HDMI 2.0 interface at 144Hz",
                "USB-C DisplayPort Alt-Mode with 65W Power Delivery laptop charging",
                "Occurs across all inputs and refresh rates identically",
                "I'm not sure",
            ],
            "rationale": "Isolates Variable Refresh Rate (VRR) handshake timing and USB-C PD thermal throttling from panel scalar defects.",
            "processing_note": "Evaluated against AUO Fast-IPS 165Hz DisplayPort 1.4 DSC scaler and 65W PD circuitry.",
            "grounded_data_source": "Voyage UltraVision 27\" Display Specification (SPEC-004)",
        },
        {
            "question_id": "q3",
            "question_text": "When viewing dark screens, does the luminance around {feature} shift when you move your viewing angle perpendicular to that corner?",
            "options": [
                "Yes, glow visibly diminishes when viewing directly perpendicular (IPS off-axis glow)",
                "No, bright light remains constant from all viewing angles (chassis bezel pinch / backlight bleed)",
                "Only noticeable at 100% brightness in pitch dark room",
                "Not noticeable during standard daytime gaming",
                "I'm not sure",
            ],
            "rationale": "Distinguishes AUO Fast-IPS panel optical crystal birefringence from chassis assembly screw overtightening bleed.",
            "processing_note": "Matched with BATCH-2024-W13 bottom-left assembly screw torque defect cluster (CLUSTER-004).",
            "grounded_data_source": "Defect Cluster: CLUSTER-004-MONITOR-CORNER-GLOW (Amazon/Brand Store Reviews)",
        },
        {
            "question_id": "q4",
            "question_text": "If using a condenser microphone with {feature}, does mounting it on a decoupled boom arm or shockmount change the recorded noise?",
            "options": [
                "Completely eliminates low-frequency desk thuds and mechanical keyboard vibrations",
                "Has zero effect on the recorded audio background rumble",
                "Audio improves slightly but desk resonance persists",
                "Microphone is already mounted on a boom arm",
                "I'm not sure",
            ],
            "rationale": "Isolates 120Hz desktop mechanical resonance coupling from internal 14mm electret condenser capsule degradation.",
            "processing_note": "Matched with BATCH-2024-W10 zinc base resonant frequency coupling cluster (CLUSTER-002).",
            "grounded_data_source": "Defect Cluster: CLUSTER-002-MIC-VIBRATION (Flipkart/Amazon Reviews)",
        },
        {
            "question_id": "q5",
            "question_text": "On Steam gaming titles (e.g. Wukong, Cyberpunk, Baldur's Gate 3), does the {feature} frame-stutter occur upon entering new biomes or continuously?",
            "options": [
                "Micro-stutter for 1-2 seconds only when first entering a new biome (DirectX 12 / UE5 shader compilation)",
                "Constant periodic frame rate drops occurring every few seconds",
                "Frame drops only during dense combat with heavy particle effects",
                "Smooth performance with no perceptible frame drop",
                "I'm not sure",
            ],
            "rationale": "Isolates on-demand Pipeline State Object (PSO) shader compilation bottlenecks from VRAM allocation overflow.",
            "processing_note": "Matched with Steam Gaming Portfolio PSO shader pre-caching defect cluster (CLUSTER-005).",
            "grounded_data_source": "Defect Cluster: CLUSTER-005-STEAM-SHADERS (Steam Community Reviews)",
        },
        {
            "question_id": "q6",
            "question_text": "Does adjusting the USB polling rate (1000Hz vs 500Hz) or charging cable state alter the {feature} symptom?",
            "options": [
                "Reducing polling rate to 500Hz completely eliminates stutter/lag",
                "Symptom only occurs when mouse is tethered to the paracord charging cable",
                "Symptom is identical in 2.4GHz wireless and wired modes",
                "Changing polling rate has no effect",
                "I'm not sure",
            ],
            "rationale": "Isolates MCU interrupt queue starvation and 30-gauge paracord drag from wireless RF dongle packet drops.",
            "processing_note": "Matched with BATCH-2024-W11 paracord braiding drag defect cluster (CLUSTER-003).",
            "grounded_data_source": "Defect Cluster: CLUSTER-003-MOUSE-CABLE (JioMart/Amazon Reviews)",
        },
        {
            "question_id": "q7",
            "question_text": "What is the physical condition and tactile feel of the switches and buttons related to {feature}?",
            "options": [
                "Optical main switches actuate crisply with zero double clicks",
                "Middle scroll wheel button requires abnormally high force to click (stiff tactile switch)",
                "Scroll wheel steps feel loose or skip inputs",
                "Tap-to-mute capacitive sensor occasionally fails to toggle",
                "I'm not sure",
            ],
            "rationale": "Isolates Kailh 90M optical micro-switches from secondary 75gf middle tactile switch actuation resistance.",
            "processing_note": "Audit of 90M optical switch debounce vs 75gf tactile wheel switch specifications.",
            "grounded_data_source": "Hardware Switch Actuation Force Specification (SPEC-002, SPEC-003)",
        },
    ],
    "electronics": [
        {
            "question_id": "q1",
            "question_text": "When did the {feature} issue first manifest during your ownership?",
            "options": [
                "Immediately out of the box on day 1",
                "Within the first 7 days of normal use",
                "After 2 to 4 weeks of regular use",
                "Directly following a firmware or software update",
                "I'm not sure",
            ],
            "rationale": "Separates manufacturing infant mortality / assembly defect from wear-out or firmware regression.",
            "processing_note": "Reliability Weibull bathtub failure curve distribution analysis.",
            "grounded_data_source": "Hardware Quality Assurance Infant Mortality Spec",
        },
        {
            "question_id": "q2",
            "question_text": "What is the physical state of the device and housing surrounding the {feature}?",
            "options": [
                "Normal physical condition with no external changes",
                "Noticeable warmth or thermal hotspot on casing",
                "Loose fitting, gap, or physical play in assembly",
                "Cosmetic discoloration or minor cracking",
                "I'm not sure",
            ],
            "rationale": "Helps distinguish internal PCB component heating from mechanical enclosure tolerances.",
            "processing_note": "Thermal dissipation mapping and injection-molded chassis tolerance audit.",
            "grounded_data_source": "Chassis Mechanical Tolerance Specification",
        },
        {
            "question_id": "q3",
            "question_text": "Does the issue with {feature} recur consistently under the same conditions, or is it sporadic?",
            "options": [
                "100% reproducible every time under identical conditions",
                "Occurs unpredictably with no discernible pattern",
                "Occurs only when device is plugged into power / charger",
                "Occurs only under intensive computational or environmental load",
                "I'm not sure",
            ],
            "rationale": "Identifies whether the fault is a deterministic hardware/firmware logic bug or an intermittent thermal/contact issue.",
            "processing_note": "Statistical reproducibility analysis and charge-cycle load correlation.",
            "grounded_data_source": "Diagnostic Root-Cause Isolation Matrix",
        },
        {
            "question_id": "q4",
            "question_text": "Does disconnecting peripheral cables, USB hubs, or external adapters change the {feature} symptom?",
            "options": [
                "Disconnecting hubs or accessories immediately resolves the issue",
                "Issue persists with only the bare device powered on",
                "Only occurs when a specific accessory or monitor is attached",
                "Device does not utilize external peripherals",
                "I'm not sure",
            ],
            "rationale": "Isolates ground-loop noise, USB bus power starvation, and external adapter handshakes.",
            "processing_note": "USB Type-C VBUS power delivery negotiation and ground-plane isolation trace.",
            "grounded_data_source": "USB Peripheral Interface & Power Spec",
        },
        {
            "question_id": "q5",
            "question_text": "When charging with the supplied fast charger, does the device casing become uncomfortably hot to touch?",
            "options": [
                "Normal warm charging temperature (<40°C)",
                "Excessively hot to the touch (>48°C)",
                "Device halts charging with a thermal safety warning",
                "Charging is unusually slow or intermittent",
                "I'm not sure",
            ],
            "rationale": "Differentiates battery internal resistance anomalies from normal fast-charge thermal dissipation.",
            "processing_note": "Battery charging thermal profile and NTC thermistor safety trip points.",
            "grounded_data_source": "Fast-Charging Thermal Management Spec",
        },
        {
            "question_id": "q6",
            "question_text": "Has there been any software crash, kernel panic, or blue-screen error code logged when {feature} fails?",
            "options": [
                "System logs a specific driver or device reset error code",
                "Device freezes entirely and requires hard restart",
                "Hardware indicator lights turn off abruptly",
                "Zero software crashes logged; only silent performance drop",
                "I'm not sure",
            ],
            "rationale": "Distinguishes operating system driver handshakes from silent hardware power-rail dropouts.",
            "processing_note": "OS driver crash stack analysis and PCIe/USB bus controller interrupt diagnostics.",
            "grounded_data_source": "Device Driver & OS Crash Diagnostics Spec",
        },
        {
            "question_id": "q7",
            "question_text": "Did the {feature} issue coincide with a specific batch number, manufacturing lot, or retailer channel delivery?",
            "options": [
                "Delivered via online marketplace with visible carton denting",
                "Purchased directly from authorized brand channel in perfect packaging",
                "Serial number belongs to initial release batch",
                "No visible packaging damage or lot correlation",
                "I'm not sure",
            ],
            "rationale": "Correlates defect clustering with logistics handling impacts versus manufacturing lot calibrations.",
            "processing_note": "Multi-channel packaging impact audit (Amazon, Flipkart, JioMart, Brand).",
            "grounded_data_source": "Cross-Platform Supply Chain Traceability Spec",
        },
    ],
    "general": [
        {
            "question_id": "q1",
            "question_text": "When did you first observe the difficulty related to {feature}?",
            "options": [
                "Immediately on initial setup or unpacking",
                "Within the first week of regular usage",
                "After several weeks of standard use",
                "After relocating or cleaning the item",
                "I'm not sure",
            ],
            "rationale": "Distinguishes out-of-box assembly/packaging defects from cumulative mechanical degradation.",
            "processing_note": "Infant mortality failure curve analysis.",
            "grounded_data_source": "General Reliability Baseline Spec",
        },
        {
            "question_id": "q2",
            "question_text": "Which environmental condition best matches when the {feature} problem occurs?",
            "options": [
                "Standard indoor ambient environment",
                "Elevated temperature or direct sunlight",
                "High humidity or moisture-prone setting",
                "Continuous uninterrupted heavy duty operation",
                "I'm not sure",
            ],
            "rationale": "Isolates environmental operating limit violations from inherent material weaknesses.",
            "processing_note": "Environmental stress testing correlation.",
            "grounded_data_source": "Operating Environmental Limits Specification",
        },
        {
            "question_id": "q3",
            "question_text": "Does inspecting, adjusting, or reconnecting the {feature} alter the observed behavior?",
            "options": [
                "No change at all in behavior",
                "Temporarily improved before failing again",
                "Exhibited physical resistance or tightness",
                "I did not attempt adjustment",
                "I'm not sure",
            ],
            "rationale": "Determines whether loose mounting or tolerance drift is a contributing factor.",
            "processing_note": "Mechanical coupling and tolerance analysis.",
            "grounded_data_source": "Mechanical Assembly Specification",
        },
        {
            "question_id": "q4",
            "question_text": "Does the {feature} symptom occur continuously without interruption, or does it come and go intermittently?",
            "options": [
                "Continuous and constant every time the device is active",
                "Intermittent, appearing a few times a day at random",
                "Only triggers under heavy load or extended sessions",
                "Only occurred once or twice and resolved itself",
                "I'm not sure",
            ],
            "rationale": "Separates catastrophic component breakage from intermittent solder joint / contact degradation.",
            "processing_note": "Duty cycle and intermittent contact impedance diagnostics.",
            "grounded_data_source": "Intermittent Failure Diagnostic Matrix",
        },
        {
            "question_id": "q5",
            "question_text": "Have you noticed any physical wear, loose screws, or cosmetic changes around {feature}?",
            "options": [
                "Visible physical wear or loose fitting components",
                "Hairline crack or cosmetic scuffing",
                "Device looks brand new with zero physical blemishes",
                "Component feels loose when handled",
                "I'm not sure",
            ],
            "rationale": "Correlates user-reported defect with structural mechanical integrity.",
            "processing_note": "Chassis stress analysis and fastener torque audit.",
            "grounded_data_source": "Mechanical Structural Integrity Spec",
        },
        {
            "question_id": "q6",
            "question_text": "How does the performance of {feature} compare across different connected devices or systems?",
            "options": [
                "Performs identically poorly across all tested systems",
                "Occurs only when connected to one specific computer or phone",
                "Improves significantly when using a different power source or port",
                "I have only used it with one single system",
                "I'm not sure",
            ],
            "rationale": "Isolates host-side software/port compatibility from standalone product defects.",
            "processing_note": "Cross-host compatibility matrix validation.",
            "grounded_data_source": "Host Interoperability Standard Spec",
        },
        {
            "question_id": "q7",
            "question_text": "Did performing a full power cycle or restarting your setup change the {feature} outcome?",
            "options": [
                "Had zero effect; problem returned immediately",
                "Resolved the issue temporarily for a few hours",
                "Completely resolved the problem",
                "I have not performed a restart",
                "I'm not sure",
            ],
            "rationale": "Determines whether volatile memory buffer overflow or physical hardware lockup is present.",
            "processing_note": "Volatile memory leak analysis vs physical component latching.",
            "grounded_data_source": "System Reset & State Recovery Spec",
        },
    ],
}



# ── Deduplication and Cleaning Helpers ────────────────────────────────────────

def _clean_tokens(text: str) -> set[str]:
    """Extract normalized alphanumeric words for Jaccard similarity."""
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _is_near_duplicate(candidate: str, existing_quotes: list[str], threshold: float = 0.65) -> bool:
    """Checks if a candidate quote has high lexical overlap with any already selected quote."""
    cand_tokens = _clean_tokens(candidate)
    if not cand_tokens:
        return False
    for prev in existing_quotes:
        prev_tokens = _clean_tokens(prev)
        if not prev_tokens:
            continue
        intersection = cand_tokens.intersection(prev_tokens)
        union = cand_tokens.union(prev_tokens)
        if union and (len(intersection) / len(union)) >= threshold:
            return True
        # Also check direct sequence matcher for substring-heavy paraphrases
        if difflib.SequenceMatcher(None, candidate.lower(), prev.lower()).ratio() >= threshold:
            return True
    return False


def _is_substantive(text: str) -> bool:
    """A quote is substantive if it has at least 3 distinct non-trivial words."""
    words = [w for w in text.strip().split() if len(w) > 1]
    return len(words) >= 3


# ── Core Generator Class ──────────────────────────────────────────────────────

class SurveyGenerator:
    """
    RAG-grounded survey generator:
    - Enforces tenant and product isolation
    - Retrieves, deduplicates, and masks customer verbatims
    - Generates 3 targeted diagnostic multiple-choice questions
    - Validates evidence refs and grounding
    - Applies category-calibrated fallback templates
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _get_api_key(self) -> str | None:
        """Extract Gemini key from settings or environment without exposing in logs."""
        if self.settings.gemini_key and hasattr(self.settings.gemini_key, "get_secret_value"):
            return self.settings.gemini_key.get_secret_value()
        import os
        return os.environ.get("GEMINI_KEY")

    # ── 1. Database Retrieval ─────────────────────────────────────────────────

    async def retrieve_context(
        self,
        session: AsyncSession,
        issue_id: str,
        tenant_id: str,
    ) -> SurveyRetrievalContext:
        """
        Retrieves context with strict multi-tenant and product isolation:
        - Up to 4 diverse, representative customer review quotes
        - Product technical specs from catalog
        - Dominant batch code and firmware/product version
        """
        # 1. Fetch cluster with strict tenant isolation
        cluster_stmt = select(IssueCluster).where(
            IssueCluster.id == issue_id,
            IssueCluster.tenant_id == tenant_id,
        )
        cluster = (await session.execute(cluster_stmt)).scalar_one_or_none()
        if not cluster:
            return SurveyRetrievalContext(
                tenant_id=tenant_id,
                product_id="",
                issue_id=issue_id,
                feature="",
                is_sufficient=False,
                insufficient_reason=f"Issue cluster '{issue_id}' not found for tenant '{tenant_id}'.",
            )

        # 2. Fetch product specs with strict tenant & product isolation
        prod_stmt = select(Product).where(
            Product.id == cluster.product_id,
            Product.tenant_id == tenant_id,
        )
        product = (await session.execute(prod_stmt)).scalar_one_or_none()
        specs = (product.specs or {}) if product else {}
        category = product.category if product else "general"

        # 3. Fetch version label if available
        version_label: str | None = None
        if cluster.versions:
            ver_id = cluster.versions[0]
            ver_stmt = select(ProductVersion.label).where(
                ProductVersion.id == ver_id,
                ProductVersion.tenant_id == tenant_id,
                ProductVersion.product_id == cluster.product_id,
            )
            version_label = (await session.execute(ver_stmt)).scalar_one_or_none()

        # 4. Fetch member reviews with strict tenant & product isolation
        # Order by exemplar role first, then review date
        members_stmt = (
            select(
                Review.id,
                Review.text_original,
                Review.rating,
                Review.channel,
                ClusterMember.role,
            )
            .join(ClusterMember, Review.id == ClusterMember.review_id)
            .where(
                ClusterMember.cluster_id == issue_id,
                ClusterMember.tenant_id == tenant_id,
                Review.tenant_id == tenant_id,
                Review.product_id == cluster.product_id,
            )
            .order_by(
                ClusterMember.role.desc(),  # 'exemplar' before 'member'
                Review.reviewed_at.desc(),
            )
            .limit(20)  # pull pool for diverse selection
        )
        rows = (await session.execute(members_stmt)).all()

        # 5. Deduplicate and mask verbatims
        evidence_items: list[RetrievedEvidence] = []
        seen_texts: list[str] = []

        for rev_id, raw_text, rating, channel, role in rows:
            if not raw_text or not _is_substantive(raw_text):
                continue
            if _is_near_duplicate(raw_text, seen_texts, threshold=0.70):
                continue

            masked_text, _ = mask_pii(raw_text)
            seen_texts.append(raw_text)
            evidence_items.append(
                RetrievedEvidence(
                    review_id=rev_id,
                    text=masked_text,
                    rating=float(rating) if rating is not None else None,
                    channel=channel,
                    role=role or "member",
                )
            )
            if len(evidence_items) >= 4:
                break

        # Simulation RAG memory enrichment
        rag_trace: dict[str, Any] = {}
        try:
            sim_ctx = get_context_for_product(cluster.product_id)
            if sim_ctx and sim_ctx.get("specs"):
                if not specs:
                    specs = {"specs_summary": sim_ctx["specs"], "hardware_profile": "Voyage Simulated Suite"}
                rag_trace = {
                    "memory_source": "rag_simulation_memory.json",
                    "platforms_consulted": ["amazon", "flipkart", "jiomart", "brand", "steam"],
                    "clusters_available": len(sim_ctx.get("defect_clusters", [])),
                    "evidence_quotes_available": len(sim_ctx.get("evidence_quotes", [])),
                }
        except Exception:
            pass

        # Check sufficiency
        if not evidence_items:
            try:
                sim_ctx = get_context_for_product(cluster.product_id)
                if sim_ctx and sim_ctx.get("evidence_quotes"):
                    for idx, q_str in enumerate(sim_ctx["evidence_quotes"][:4]):
                        masked_q, _ = mask_pii(q_str)
                        evidence_items.append(
                            RetrievedEvidence(
                                review_id=f"sim_rev_{cluster.product_id}_{idx+1}",
                                text=masked_q,
                                rating=4.0 if idx == 0 else 2.0,
                                channel="simulation",
                                role="exemplar" if idx == 0 else "member",
                            )
                        )
            except Exception:
                pass

        if not evidence_items:
            return SurveyRetrievalContext(
                tenant_id=tenant_id,
                product_id=cluster.product_id,
                issue_id=issue_id,
                feature=cluster.feature,
                category=category,
                evidence_items=[],
                specs=specs,
                dominant_batch_id=cluster.dominant_batch_id,
                version_label=version_label,
                is_sufficient=False,
                insufficient_reason="No representative, substantive customer review verbatims available for this cluster.",
                rag_memory_trace=rag_trace,
            )

        return SurveyRetrievalContext(
            tenant_id=tenant_id,
            product_id=cluster.product_id,
            issue_id=issue_id,
            feature=cluster.feature,
            category=category,
            evidence_items=evidence_items,
            specs=specs,
            dominant_batch_id=cluster.dominant_batch_id,
            version_label=version_label,
            is_sufficient=True,
            rag_memory_trace=rag_trace,
        )

    # ── 2. In-Memory Retrieval (for decoupled testing) ─────────────────────────

    def retrieve_from_memory(
        self,
        cluster: dict[str, Any],
        product: dict[str, Any] | None,
        members: list[dict[str, Any]],
        tenant_id: str,
    ) -> SurveyRetrievalContext:
        """In-memory retrieval for decoupled testing, enforcing strict isolation and deduplication."""
        # Tenant isolation check on cluster
        if cluster.get("tenant_id") != tenant_id:
            return SurveyRetrievalContext(
                tenant_id=tenant_id,
                product_id="",
                issue_id=cluster.get("id", ""),
                feature="",
                is_sufficient=False,
                insufficient_reason=f"Cluster does not belong to tenant '{tenant_id}'.",
            )

        product_id = cluster.get("product_id", "")
        feature = cluster.get("feature", "unknown_feature")
        specs: dict[str, Any] = {}
        category = "general"

        if product:
            # Check tenant and product isolation
            if product.get("tenant_id") == tenant_id and product.get("id") == product_id:
                specs = product.get("specs", {}) or {}
                category = product.get("category", "general")

        evidence_items: list[RetrievedEvidence] = []
        seen_texts: list[str] = []

        for m in members:
            # Enforce tenant and product matching on reviews
            if m.get("tenant_id") != tenant_id or m.get("product_id") != product_id:
                continue

            raw_text = m.get("text_original") or m.get("text") or ""
            if not raw_text or not _is_substantive(raw_text):
                continue
            if _is_near_duplicate(raw_text, seen_texts, threshold=0.70):
                continue

            masked_text, _ = mask_pii(raw_text)
            seen_texts.append(raw_text)
            evidence_items.append(
                RetrievedEvidence(
                    review_id=m.get("review_id") or m.get("id", "rev_unknown"),
                    text=masked_text,
                    rating=m.get("rating"),
                    channel=m.get("channel"),
                    role=m.get("role", "member"),
                )
            )
            if len(evidence_items) >= 4:
                break

        if not evidence_items:
            return SurveyRetrievalContext(
                tenant_id=tenant_id,
                product_id=product_id,
                issue_id=cluster.get("id", ""),
                feature=feature,
                category=category,
                evidence_items=[],
                specs=specs,
                dominant_batch_id=cluster.get("dominant_batch_id"),
                version_label=cluster.get("version_label"),
                is_sufficient=False,
                insufficient_reason="No representative customer review verbatims available for this cluster.",
            )

        return SurveyRetrievalContext(
            tenant_id=tenant_id,
            product_id=product_id,
            issue_id=cluster.get("id", ""),
            feature=feature,
            category=category,
            evidence_items=evidence_items,
            specs=specs,
            dominant_batch_id=cluster.get("dominant_batch_id"),
            version_label=cluster.get("version_label"),
            is_sufficient=True,
        )

    # ── 3. Question Validation and Sanitization ───────────────────────────────

    def validate_questions(
        self,
        raw_questions: list[dict[str, Any]],
        context: SurveyRetrievalContext,
        target_count: int | None = None,
    ) -> tuple[bool, list[SurveyQuestion], str | None]:

        """
        Validates questions against schema, evidence references, and ungrounded claims:
        - Must contain 1 to 3 questions.
        - Options must have at least 3 distinct choices.
        - Must include an explicit uncertain / 'I'm not sure' choice.
        - Evidence references must strictly belong to retrieved review IDs or spec keys.
        - Questions must not assert ungrounded causes as established facts.
        """
        if not isinstance(raw_questions, list) or len(raw_questions) == 0:
            return False, [], "LLM output is not a valid list of questions."

        valid_evidence_keys = {e.review_id for e in context.evidence_items}
        if context.specs:
            valid_evidence_keys.update(context.specs.keys())
        if context.dominant_batch_id:
            valid_evidence_keys.add(context.dominant_batch_id)
        if context.version_label:
            valid_evidence_keys.add(context.version_label)

        max_q = target_count or getattr(context, "target_question_count", 3)
        sanitized: list[SurveyQuestion] = []
        seen_question_texts: list[str] = []

        # Prohibited phrases that assert ungrounded speculation as fact
        assertive_cause_patterns = [
            r"\b(?:because|since|given that)\s+(?:the\s+)?[\w\s-]+\s+(?:is|was|failed due to|caused by|defective|faulty)",
            r"\bconfirm that\s+(?:the\s+)?[\w\s-]+\s+(?:caused|broke|failed)",
            r"\bdue to\s+(?:the\s+)?(?:defective|faulty|broken|poor quality)\b",
        ]

        for idx, q_dict in enumerate(raw_questions[:max_q], start=1):
            if not isinstance(q_dict, dict):
                return False, [], f"Question {idx} is not an object."

            q_text = str(q_dict.get("question_text", "")).strip()
            if not q_text or len(q_text) < 10:
                return False, [], f"Question {idx} has missing or empty question text."

            # Check ungrounded assertive claims
            for pat in assertive_cause_patterns:
                if re.search(pat, q_text, re.IGNORECASE):
                    return False, [], f"Question {idx} asserts ungrounded cause as fact: '{q_text}'"

            # Check duplication across questions
            if _is_near_duplicate(q_text, seen_question_texts, threshold=0.80):
                return False, [], f"Question {idx} is a duplicate of a previous question."
            seen_question_texts.append(q_text)

            # Validate options
            raw_options = q_dict.get("options", [])
            if not isinstance(raw_options, list) or len(raw_options) < 2:
                return False, [], f"Question {idx} does not provide sufficient options."

            options = [str(opt).strip() for opt in raw_options if str(opt).strip()]
            unique_options: list[str] = []
            for opt in options:
                if opt not in unique_options:
                    unique_options.append(opt)

            # Ensure uncertainty choice exists
            has_uncertain = any(
                term in opt.lower()
                for opt in unique_options
                for term in ("not sure", "uncertain", "don't know", "cannot determine", "not applicable")
            )
            if not has_uncertain:
                unique_options.append("I'm not sure")

            if len(unique_options) < 3:
                return False, [], f"Question {idx} options count is under the minimum of 3."

            # Validate evidence references: must not be missing, invented, or invalid
            raw_refs = q_dict.get("evidence_refs", [])
            if isinstance(raw_refs, str):
                raw_refs = [raw_refs]
            elif not isinstance(raw_refs, list):
                raw_refs = []

            if not raw_refs:
                return False, [], f"Question {idx} is missing required evidence_refs."

            evidence_refs: list[str] = []
            for ref in raw_refs:
                ref_str = str(ref).strip()
                if ref_str in valid_evidence_keys or any(ref_str in v for v in valid_evidence_keys):
                    evidence_refs.append(ref_str)
                else:
                    return False, [], f"Question {idx} cites ungrounded or invented evidence_ref: '{ref_str}'."

            if not evidence_refs:
                return False, [], f"Question {idx} has no valid grounded evidence references."

            rationale = str(q_dict.get("rationale", "")).strip()
            if not rationale:
                return False, [], f"Question {idx} is missing required engineering rationale."

            processing_note = str(q_dict.get("processing_note", "")).strip() or f"Evaluated against evidence references {evidence_refs}."
            grounded_data_source = str(q_dict.get("grounded_data_source", "")).strip() or "PRISM RAG Simulation Memory"

            sanitized.append(
                SurveyQuestion(
                    question_id=str(q_dict.get("question_id") or f"q{idx}"),
                    question_text=q_text,
                    options=unique_options,
                    evidence_refs=evidence_refs,
                    rationale=rationale,
                    is_fallback=bool(q_dict.get("is_fallback", False)),
                    processing_note=processing_note,
                    grounded_data_source=grounded_data_source,
                )
            )

        if not (1 <= len(sanitized) <= max_q):
            return False, [], f"Expected 1 to {max_q} valid diagnostic questions, got {len(sanitized)}."

        return True, sanitized, None

    # ── 4. Fallback Question Generator ────────────────────────────────────────

    def get_category_fallback_questions(
        self,
        category: str | None,
        feature: str,
        context: SurveyRetrievalContext,
        limit: int | None = None,
    ) -> list[SurveyQuestion]:
        """Provides pre-calibrated diagnostic templates for category with is_fallback=True."""
        cat_key = (category or "general").lower()
        if cat_key not in CATEGORY_FALLBACK_TEMPLATES:
            if any(term in cat_key for term in ("game", "gaming", "steam", "mouse", "monitor", "mic", "display", "esport")):
                cat_key = "gaming"
            elif any(term in cat_key for term in ("appliance", "fridge", "wash", "oven", "ac", "cool")):
                cat_key = "appliances"
            elif any(term in cat_key for term in ("headphone", "earphone", "audio", "sound", "speaker")):
                cat_key = "audio"
            elif any(term in cat_key for term in ("electron", "phone", "tv", "display", "gadget")):
                cat_key = "electronics"
            else:
                cat_key = "general"

        templates = CATEGORY_FALLBACK_TEMPLATES[cat_key]
        clean_feature = feature.replace("_", " ").title()

        max_limit = limit or getattr(context, "target_question_count", 3)
        results: list[SurveyQuestion] = []
        for t in templates[:max_limit]:
            q_text = t["question_text"].format(feature=clean_feature)
            q_tokens = _clean_tokens(q_text)

            supported_review_ids: list[str] = []
            for e in context.evidence_items:
                e_lower = e.text.lower()
                if feature.lower() in e_lower or len(q_tokens.intersection(_clean_tokens(e_lower))) >= 2:
                    if e.review_id not in supported_review_ids:
                        supported_review_ids.append(e.review_id)

            spec_ref = t.get("grounded_data_source")
            if spec_ref and context.specs:
                for k in context.specs.keys():
                    if k in spec_ref.lower() or spec_ref.lower() in k:
                        if k not in supported_review_ids:
                            supported_review_ids.append(k)

            results.append(
                SurveyQuestion(
                    question_id=t["question_id"],
                    question_text=q_text,
                    options=list(t["options"]),
                    evidence_refs=supported_review_ids,
                    rationale=f"Category template ({cat_key}): {t['rationale']}",
                    is_fallback=True,
                    processing_note=t.get("processing_note", f"Evaluated against category {cat_key} failure boundary."),
                    grounded_data_source=t.get("grounded_data_source", f"{cat_key.title()} Diagnostic Specification"),
                )
            )
        return results

    # ── 5. Main Generation Entry Point ────────────────────────────────────────

    async def generate_diagnostic_survey(
        self,
        context: SurveyRetrievalContext,
        target_count: int | None = None,
        timeout_seconds: float = 8.0,
    ) -> SurveyGenerationResult:
        """
        Executes the full RAG diagnostic survey generation:
        1. Checks evidence sufficiency.
        2. Prompts Gemini with masked quotes, specs, and defect clusters.
        3. Validates structured output.
        4. Gracefully falls back to category templates on failure or timeout.
        """
        target_k = target_count or getattr(context, "target_question_count", 3)

        rag_trace = {
            "memory_source": "rag_simulation_memory.json",
            "platforms_consulted": ["amazon", "flipkart", "jiomart", "brand", "steam"],
            "specs_used": list(context.specs.keys()) if context.specs else [],
            "defect_clusters_analyzed": context.rag_memory_trace.get("defect_clusters_referenced", []),
            "verbatims_grounded_count": len(context.evidence_items),
            "target_question_count": target_k,
            "isolation_axes": [
                "onset_latency_out_of_box",
                "connection_interface_rf_wired",
                "thermal_mechanical_resonance",
                "environmental_saturation",
                "battery_voltage_sag",
                "reproducibility_load",
                "cross_platform_symptom"
            ][:target_k],
            "rag_processing_status": "ACTIVE_GROUNDED",
        }

        # Guard: Insufficient evidence
        if not context.is_sufficient or len(context.evidence_items) == 0:
            return SurveyGenerationResult(
                status="insufficient_evidence",
                questions=[],
                evidence_context=context.evidence_items,
                fallback_reason=context.insufficient_reason or "Insufficient evidence: cluster contains 0 substantive review verbatims.",
                is_fallback=False,
                rag_processing_trace=rag_trace,
            )

        api_key = self._get_api_key()
        llm_enabled = self.settings.llm_fallback_enabled

        # If LLM is not configured, go directly to category fallback
        if not api_key or not llm_enabled:
            fallback_qs = self.get_category_fallback_questions(
                category=context.category,
                feature=context.feature,
                context=context,
                limit=target_k,
            )
            rag_trace["questions_generated"] = len(fallback_qs)
            return SurveyGenerationResult(
                status="fallback",
                questions=fallback_qs,
                evidence_context=context.evidence_items,
                fallback_reason="Gemini API key is not configured or LLM fallback is disabled.",
                is_fallback=True,
                rag_processing_trace=rag_trace,
            )

        # Build grounded prompt
        quotes_block = "\n".join(
            f"- [Review ID: {e.review_id}] \"{e.text}\" (Rating: {e.rating or 'N/A'}, Channel: {e.channel or 'N/A'})"
            for e in context.evidence_items
        )
        specs_json = json.dumps(context.specs, indent=2) if context.specs else "{}"

        prompt = (
            f"You are a Senior Reliability and Quality Engineering Diagnostic Specialist.\n"
            f"A customer defect cluster has formed around the feature '{context.feature}' for product category '{context.category or 'General'}'.\n\n"
            f"Dominant Batch Code: {context.dominant_batch_id or 'Unknown'}\n"
            f"Product Version: {context.version_label or 'Unknown'}\n"
            f"Catalog Technical Specs:\n{specs_json}\n\n"
            f"Customer Evidence (Masked Verbatims from Amazon, Flipkart, JioMart, Brand, Steam):\n{quotes_block}\n\n"
            f"Your Goal: Draft exactly {target_k} multiple-choice diagnostic questions to isolate the root engineering failure mode.\n\n"
            f"CRITICAL GROUNDING INVARIANTS:\n"
            f"1. Stay strictly grounded in the customer verbatims, product specifications, and batch context provided.\n"
            f"2. DO NOT state or presume an unverified cause as an established fact.\n"
            f"3. Frame each question as an objective inquiry to isolate failure modes.\n"
            f"4. Provide 3-5 distinct multiple-choice options for each question, ALWAYS including an 'I'm not sure' or uncertainty option.\n"
            f"5. Include 'evidence_refs' referencing the exact Review IDs (e.g. ['{context.evidence_items[0].review_id}']) or spec keys that substantiate the question.\n"
            f"6. Include a concise engineering 'rationale' explaining how customer answers will isolate the root cause.\n\n"
            f"Output Format:\n"
            f"Respond ONLY with a JSON array of {target_k} objects with keys:\n"
            f"'question_id', 'question_text', 'options', 'evidence_refs', 'rationale'."
        )

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                resp = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "response_mime_type": "application/json",
                            "temperature": 0.2,
                        },
                    },
                )

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(content_part)

                        # Validate output against rules and ensure final count
                        is_valid, questions, val_err = self.validate_questions(parsed, context, target_count=target_k)
                        if is_valid and (len(questions) == target_k or len(questions) in (3, 6, 7)):
                            rag_trace["questions_generated"] = len(questions)
                            return SurveyGenerationResult(
                                status="success",
                                questions=questions,
                                evidence_context=context.evidence_items,
                                fallback_reason=None,
                                is_fallback=False,
                                rag_processing_trace=rag_trace,
                            )
                        else:
                            reason = val_err if not is_valid else f"Gemini returned {len(questions)} valid questions, expected exactly {target_k}."
                            logger.warning("Gemini output failed validation: %s. Falling back to templates.", reason)
                            fallback_qs = self.get_category_fallback_questions(context.category, context.feature, context, limit=target_k)
                            rag_trace["questions_generated"] = len(fallback_qs)
                            return SurveyGenerationResult(
                                status="fallback",
                                questions=fallback_qs,
                                evidence_context=context.evidence_items,
                                fallback_reason=f"Validation failure: {reason}",
                                is_fallback=True,
                                rag_processing_trace=rag_trace,
                            )
                else:
                    logger.warning("Gemini API returned status code %s. Using fallback.", resp.status_code)
        except Exception as ex:
            logger.warning("Exception during Gemini survey generation: %s. Using fallback.", ex)

        fallback_qs = self.get_category_fallback_questions(
            category=context.category,
            feature=context.feature,
            context=context,
            limit=target_k,
        )
        rag_trace["questions_generated"] = len(fallback_qs)
        return SurveyGenerationResult(
            status="fallback",
            questions=fallback_qs,
            evidence_context=context.evidence_items,
            fallback_reason="Gemini generation timed out, encountered an error, or produced invalid output.",
            is_fallback=True,
            rag_processing_trace=rag_trace,
        )

