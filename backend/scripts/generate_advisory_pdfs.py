"""
Generate Advisory PDFs for Bower Ag CowCare Tool RAG Layer.

Creates 5 representative advisory PDFs based on the domain knowledge
described in Documents A and B. Each PDF contains structured content
that will be chunked and embedded for similarity search.

Domains covered:
  1. troubleshooting - Bacteria/SPC troubleshooting guide
  2. sds            - Safety Data Sheet binder (product safety)
  3. procedure      - CIP decision tree and procedures
  4. product_info   - Technical data sheets
  5. calculation    - Shield OFB reference calculations

Run: python scripts/generate_advisory_pdfs.py
Output: backend/data/advisory_docs/*.pdf
"""

from fpdf import FPDF
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "advisory_docs")

# Unicode -> Latin-1 safe replacements for FPDF core fonts
_UNICODE_REPLACEMENTS = {
    "\u2014": "--",   # em dash
    "\u2013": "-",    # en dash
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2026": "...",  # ellipsis
    "\u00b0": " degrees",  # degree sign (already spelled out mostly)
}


def _sanitize(text: str) -> str:
    """Replace Unicode characters that Latin-1 core fonts cannot encode."""
    for char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    return text


def _create_pdf(filename: str, title: str, sections: list[tuple[str, str]]) -> str:
    """Create a PDF with title page + section headings + body text."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 40, "", ln=True)
    pdf.multi_cell(0, 12, _sanitize(title), align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, "", ln=True)
    pdf.cell(0, 8, "Bower Ag - CowCare Division", align="C", ln=True)
    pdf.cell(0, 8, "Internal Advisory Reference", align="C", ln=True)
    pdf.cell(0, 8, "Confidential - For Bower Ag Representatives Only", align="C", ln=True)

    # Content pages
    for heading, body in sections:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 8, _sanitize(heading.upper()))
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 11)
        for paragraph in body.split("\n\n"):
            paragraph = _sanitize(paragraph.strip())
            if paragraph:
                pdf.multi_cell(0, 6, paragraph)
                pdf.ln(3)

    path = os.path.join(OUTPUT_DIR, filename)
    pdf.output(path)
    return path


# ═══════════════════════════════════════════════════════════════════
# PDF 1: TROUBLESHOOTING GUIDE (domain='troubleshooting')
# Covers bacteria, SPC, water quality, parlor, CIP flow issues
# ═══════════════════════════════════════════════════════════════════

TROUBLESHOOTING_SECTIONS = [
    ("HIGH BACTERIA COUNT TROUBLESHOOTING",
     """When a dairy operation reports elevated Standard Plate Count (SPC) or high bacteria counts, the first step is always a systematic evaluation rather than an immediate product change. High bacteria counts are among the most common issues Bower Ag consultants encounter, and the root cause is often mechanical or procedural, not chemical.

The target SPC range for raw bulk tank milk is below 10,000 CFU/mL. Counts between 10,000 and 25,000 indicate a developing problem that needs attention. Counts above 25,000 require immediate investigation. Counts above 100,000 typically result in milk quality penalties from the processor.

Before recommending any product changes, always gather these four critical data points: the current SPC count and trend direction (rising, stable, or declining), recent water test results including hardness and iron levels, the current CIP chemical program with concentrations and contact times, and any recent changes to the milking system such as new liners, changed timing, or a new water source."""),

    ("WATER QUALITY AND HARDNESS ASSESSMENT",
     """Water quality is the single most overlooked factor in dairy sanitation problems. Every Bower Ag consultant should request a water test before recommending any CIP program changes. Hard water directly reduces the effectiveness of alkaline detergents and can cause mineral buildup in milking systems.

Water hardness is measured in grains per gallon (gpg) or parts per million (ppm). Soft water is 0-3.5 gpg (0-60 ppm). Moderately hard water is 3.5-7 gpg (60-120 ppm). Hard water is 7-10.5 gpg (120-180 ppm). Very hard water is above 10.5 gpg (above 180 ppm).

For operations with hard water above 7 gpg, alkaline CIP wash concentrations must be increased by 25-50 percent. Additionally, an acid rinse cycle becomes essential to prevent mineral scale buildup. Iron levels above 0.3 ppm can cause red-brown staining and biofilm formation in pipelines.

Recommended action: If the operation has not tested water in the last 12 months, request a comprehensive water analysis before making any chemical program recommendations. Bower Ag can coordinate water testing through our lab partnerships."""),

    ("CIP FLOW AND MECHANICAL TROUBLESHOOTING",
     """Clean-in-place (CIP) system problems account for approximately 40 percent of bacteria issues in dairy operations. Before changing chemicals, verify the mechanical system is functioning correctly.

Flow rate verification: The minimum effective CIP flow rate is 5 feet per second (fps) in the pipeline. For a 2-inch pipeline, this requires approximately 20 gallons per minute (GPM). For a 3-inch pipeline, approximately 45 GPM is needed. Use a bucket test at the end of the return line to verify actual flow rate.

If the bucket test shows less than 8 gallons per unit, there is likely a flow restriction that needs on-site diagnosis. Common flow restrictions include partially closed valves, kinked hoses, clogged filters, and air injector timing issues.

Air injector timing: A flooded CIP system usually indicates the air injector is firing too early or too late. The air injector should create distinct slugs of solution separated by air gaps. If the return line shows continuous flow without air breaks, the air injector needs adjustment.

Temperature verification: Alkaline wash temperature should be 160-170 degrees Fahrenheit at the start, and no less than 120 degrees Fahrenheit at the return. A temperature drop greater than 40 degrees indicates insufficient water heater capacity or heat loss in the system. Acid rinse temperature should be 100-130 degrees Fahrenheit."""),

    ("MILKING SYSTEM VACUUM AND PULSATION",
     """Vacuum and pulsation problems cause both milk quality issues and teat end damage. A vacuum test should be part of every comprehensive barn evaluation.

System vacuum should be set per the equipment manufacturer's recommendation, typically 12.5-13.5 inches of mercury (Hg) for most modern systems. Vacuum fluctuation during milking should not exceed 2 inches Hg. Excessive fluctuation indicates undersized vacuum pumps, air leaks, or inadequate regulator capacity.

Pulsation ratio and rate affect milking efficiency and teat end health. Standard pulsation is 60:40 ratio at 60 cycles per minute. Deviation from these settings can cause incomplete milkout, increased milking time, and teat end hyperkeratosis.

Liner condition: Rubber liners should be replaced every 2,500 milkings or per the manufacturer's recommendation. Worn liners lose their ability to properly massage the teat, leading to teat end damage and potential bacterial colonization. Silicone liners have longer service life (approximately 10,000 milkings) but must still be inspected regularly.

Signs of liner wear include cracking, discoloration, tackiness, and loss of tension. A simple squeeze test can identify liners that have lost their compression. Replace all liners in a set simultaneously to maintain uniform performance."""),

    ("PARLOR HYGIENE AND PREP PROCEDURE AUDIT",
     """Consistent milking prep procedure is critical to both milk quality and cow health. When auditing a parlor, observe at least 10 consecutive cows through the full prep routine.

Recommended milking prep sequence: Apply pre-dip (contact time minimum 30 seconds), strip each quarter (2-3 squirts minimum) to check for abnormal milk, wipe teats with individual towels (cloth or disposable), and attach milking unit within 60-90 seconds of stimulation.

Common prep procedure failures: Insufficient pre-dip contact time (rushing to attach), not stripping before wiping (missing clinical mastitis detection), sharing towels between cows (cross-contamination), and delayed attachment (losing the oxytocin letdown window, which peaks at 60-90 seconds after stimulation).

Post-milking: Apply post-dip immediately after unit detachment. Ensure complete teat barrel coverage, not just the teat end. Post-dip should remain on the teat; do not wipe off. If cows lie down immediately after milking, consider adjusting feed delivery timing to keep cows standing for 30-60 minutes post-milking (the teat canal takes approximately 30 minutes to close).

Documentation: Record prep time per cow, pre-dip contact time, and any skipped steps. This data helps identify training needs and procedural drift over time."""),

    ("BULK TANK SANITATION TROUBLESHOOTING",
     """Elevated bulk tank counts that do not correlate with milking system issues often point to bulk tank sanitation problems. The bulk tank is frequently a blind spot in bacteria investigations.

Inspection checklist: Check the tank outlet valve and gasket for residue buildup. Inspect the agitator shaft seal for milk residue or biofilm. Verify that the CIP spray ball or spray wand reaches all interior surfaces. Check for any dead spots where the wash solution does not contact the tank surface.

Wash temperature: The bulk tank wash cycle should start at 170 degrees Fahrenheit and maintain at least 140 degrees throughout the cycle. If the dairy uses a manual wash procedure, verify water temperature with a thermometer at each step. Pre-rinse should be lukewarm (100-110 degrees Fahrenheit) to prevent protein bonding. Hot rinse should be 170 degrees or above.

Sanitizer rinse: The final sanitizer rinse before the next milking should be fresh and at the correct concentration. Many dairies prepare the sanitizer rinse too early, allowing it to lose effectiveness. Chlorine-based sanitizers should be prepared within 1 hour of use and at 200 ppm concentration for bulk tank application."""),
]

# ═══════════════════════════════════════════════════════════════════
# PDF 2: SDS BINDER (domain='sds')
# Safety Data Sheet summaries for key Bower Ag products
# ═══════════════════════════════════════════════════════════════════

SDS_SECTIONS = [
    ("SDS OVERVIEW AND SAFETY PROTOCOLS",
     """This Safety Data Sheet (SDS) binder contains critical safety information for all Bower Ag chemical products. Every sales representative and technician must be familiar with the safety requirements for each product they recommend or handle.

All Bower Ag products are formulated for use in dairy environments and meet FDA and EPA regulatory requirements for dairy chemical applications. However, proper handling, storage, and personal protective equipment (PPE) requirements vary by product chemistry and concentration.

General safety principles: Always read the product-specific SDS before handling any concentrate. Never mix chemicals from different product lines without consulting the technical team. Store all chemicals in their original containers in a cool, dry, well-ventilated area away from direct sunlight. Maintain SDS documents on-site and ensure all dairy employees know their location."""),

    ("CURIASS TEAT DIP SAFETY DATA",
     """Product: Curiass Barrier Teat Dip. Active ingredient: Chlorine dioxide (CLO2). Concentration: Varies by formulation (RTU and concentrate available).

Hazard classification: Skin irritation Category 2, Eye irritation Category 2. Signal word: Warning.

PPE requirements: Chemical-resistant gloves (nitrile recommended), safety goggles when handling concentrate, chemical-resistant apron for bulk transfers. No respiratory protection required at normal use concentrations.

First aid: Skin contact - wash with soap and water for 15 minutes. Eye contact - rinse with clean water for 15 minutes, seek medical attention if irritation persists. Ingestion - do not induce vomiting, rinse mouth with water, seek medical attention immediately. Inhalation - move to fresh air, seek medical attention if symptoms persist.

Storage: Store between 50-80 degrees Fahrenheit. Keep away from direct sunlight and heat sources. Chlorine dioxide is light-sensitive and degrades when exposed to UV. Keep containers tightly closed when not in use. Shelf life is 12 months from manufacture date when stored properly.

Spill procedure: Contain spill with absorbent material. Do not wash into storm drains or waterways. Collect absorbent material and dispose of according to local regulations. Rinse affected area with clean water.

Compatibility: Do not mix Curiass with iodine-based products. Do not mix with strong acids or bases. Compatible with standard dairy milking equipment materials including stainless steel, rubber, and silicone."""),

    ("PAVISE TEAT DIP SAFETY DATA",
     """Product: Pavise Barrier Teat Dip. Active ingredient: Chlorhexidine gluconate. Available in both concentrate and ready-to-use (RTU) formulations.

Hazard classification: Skin sensitization Category 1, Eye irritation Category 2A. Signal word: Warning.

PPE requirements: Chemical-resistant gloves (nitrile or butyl rubber), safety goggles mandatory when handling concentrate. Chemical-resistant apron recommended for transfers exceeding 5 gallons. No respiratory protection required at dairy use concentrations.

First aid: Skin contact - remove contaminated clothing, wash skin thoroughly with soap and water for 15 minutes. Some individuals may develop skin sensitivity with repeated exposure. Eye contact - flush eyes with clean water for at least 20 minutes, holding eyelids open. Seek medical attention. Ingestion - do not induce vomiting, give water to drink, seek medical attention. Inhalation - move to fresh air.

Storage: Store between 40-90 degrees Fahrenheit. Protect from freezing. Chlorhexidine products may precipitate if frozen and should be discarded if freezing occurs. Keep containers sealed. Shelf life is 18 months from manufacture when stored properly.

Environmental: Chlorhexidine is toxic to aquatic organisms. Do not allow product to enter waterways, storm drains, or sewage systems. Dispose of empty containers according to local regulations. Triple-rinse containers before recycling.

Compatibility: Do not mix with anionic detergents or soaps, which inactivate chlorhexidine. Compatible with most nonionic surfactants. Compatible with standard dairy equipment materials."""),

    ("CD114 CIP DETERGENT SAFETY DATA",
     """Product: CD114 Chlorinated Alkaline Detergent. Active ingredients: Sodium hydroxide (alkaline), sodium hypochlorite (chlorine). Used in CIP (Clean-In-Place) milking systems.

Hazard classification: Skin corrosion Category 1A, Serious eye damage Category 1, Corrosive to metals Category 1. Signal word: Danger.

PPE requirements: Chemical-resistant gloves (heavy-duty nitrile or butyl rubber required), full-face shield or tight-fitting chemical splash goggles, chemical-resistant apron, closed-toe chemical-resistant boots. When handling in poorly ventilated areas, use a NIOSH-approved respirator with chlorine cartridge.

First aid: Skin contact - immediately flush with large amounts of water for at least 20 minutes. Remove all contaminated clothing. Seek medical attention immediately for any burn symptoms. Eye contact - immediately flush eyes with clean water for at least 30 minutes while holding eyelids open. This is a medical emergency; seek immediate medical attention. Ingestion - do not induce vomiting. Do not give anything by mouth if the person is unconscious. Call Poison Control immediately. Inhalation - move to fresh air immediately. If breathing is difficult, administer oxygen. Seek medical attention.

Storage: Store in original HDPE container only. Keep tightly closed. Store in a cool, dry, well-ventilated area below 100 degrees Fahrenheit. Separate from acids, which can release toxic chlorine gas. Never store above or adjacent to acid products.

Dilution: Always add product to water, never water to product. Use the Bower Ag CD114 Usage Rate chart to determine correct dilution for the specific water hardness and system type. Incorrect concentration can damage equipment or leave residues."""),

    ("ACID RINSE AND SANITIZER SAFETY DATA",
     """Product: Bower Ag Acid Rinse and Sanitizer products. Active ingredients vary by formulation: phosphoric acid, citric acid, peracetic acid, or combinations thereof.

Hazard classification: Varies by specific product. Phosphoric acid products: Skin corrosion Category 1, Eye damage Category 1. Peracetic acid products: Skin corrosion Category 1, Serious eye damage Category 1, Oxidizer Category 2. Signal word: Danger (for all acid concentrates).

PPE requirements: Same as CD114 — chemical-resistant gloves, face shield or splash goggles, chemical-resistant apron. Additional requirement for peracetic acid: vapor-rated respiratory protection in enclosed spaces due to the strong oxidizing fumes.

First aid: Follow the same emergency procedures as for CD114. Acid burns require immediate and prolonged flushing with water. Do not attempt to neutralize acids on skin — water flushing is the correct response.

Storage: Store separately from alkaline products (CD114) and chlorinated products. Acid and alkaline chemicals must be stored on separate shelving or in separate secondary containment. Never store acids above alkaline products. Maintain at least 4 feet of separation or use a physical barrier.

Critical safety warning: Never mix acid products with chlorinated alkaline products. This combination produces toxic chlorine gas, which is immediately dangerous to life and health (IDLH). If accidental mixing occurs, evacuate the area immediately, ventilate, and call emergency services.

Disposal: Neutralize waste acid solutions before disposal according to local wastewater regulations. Contact the Bower Ag technical team for specific neutralization procedures."""),

    ("GENERAL CHEMICAL HANDLING FOR DAIRY OPERATIONS",
     """All dairy operations using Bower Ag chemical products should implement these standard safety practices.

Emergency equipment: Maintain a functioning eyewash station within 10 seconds of chemical handling areas. The eyewash station must provide at least 15 minutes of continuous flushing. A safety shower should be available within 25 feet of bulk chemical transfer areas. Test emergency equipment monthly and document the test.

Training: All employees who handle chemicals must receive initial training and annual refresher training on chemical safety, SDS locations and interpretation, PPE selection and use, and emergency procedures. Maintain training records for regulatory compliance.

Secondary containment: All bulk chemical storage must have secondary containment capable of holding 110 percent of the largest container volume. Containment must be chemical-resistant and regularly inspected for cracks or deterioration.

Transportation: When transporting chemicals between locations, secure containers to prevent tipping. Separate acids from bases during transport. Keep SDS documents accessible during transport. Report any spills during transport immediately to the Bower Ag safety coordinator.

PPE maintenance: Inspect gloves before each use for tears, holes, or degradation. Replace safety goggles that are scratched or damaged. Launder chemical-resistant aprons after each use. Do not share PPE between employees without proper cleaning."""),
]

# ═══════════════════════════════════════════════════════════════════
# PDF 3: CIP DECISION TREE (domain='procedure')
# Step-by-step CIP procedures and decision logic
# ═══════════════════════════════════════════════════════════════════

CIP_SECTIONS = [
    ("CIP SYSTEM OVERVIEW AND PRINCIPLES",
     """Clean-In-Place (CIP) is the standard method for cleaning milking system pipelines, bulk tanks, and associated equipment without disassembly. A properly designed and maintained CIP program is essential for milk quality, equipment longevity, and regulatory compliance.

The four factors of effective CIP cleaning are temperature, concentration, time, and mechanical action (turbulent flow). These factors are interdependent — if one factor is reduced, another must be increased to maintain cleaning effectiveness. This is known as the Sinner's Circle principle.

CIP cycle sequence: Pre-rinse (lukewarm water to remove bulk milk residue), alkaline wash (hot detergent to dissolve milk fats and proteins), intermediate rinse (remove alkaline residue), acid rinse (remove mineral deposits and neutralize residual alkalinity), and sanitizer rinse (final antimicrobial treatment before the next milking). Not all operations run every cycle at every milking; consult the operation's specific protocol."""),

    ("CIP DECISION TREE: ALKALINE WASH SELECTION",
     """Use this decision tree to determine the correct alkaline wash product and concentration for any dairy operation.

Step 1: Determine system type. Parlor pipeline system or round-the-barn pipeline? Parlor systems typically require higher flow rates and may use different concentrations than round-the-barn systems.

Step 2: Check water hardness. Soft water (0-3.5 gpg): Use standard concentration per product label. Moderate water (3.5-7 gpg): Increase concentration by 15 percent. Hard water (7-10.5 gpg): Increase concentration by 25 percent and ensure acid rinse cycle is included. Very hard water (above 10.5 gpg): Increase concentration by 50 percent, mandatory acid rinse after every alkaline wash, consider water treatment.

Step 3: Select product. CD114 is the primary chlorinated alkaline for most applications. For organic-certified operations, use the approved non-chlorinated alkaline alternative. For operations with stainless steel sensitivity, use the low-caustic formulation.

Step 4: Calculate volume. Pipeline volume (gallons) equals pipeline length (feet) times the area of the pipe cross-section. Add 50 percent for wash solution reservoir. Minimum solution volume is pipeline volume times 2.5 to ensure adequate slug formation with air injection.

Step 5: Set temperature. Start temperature: 160-170 degrees Fahrenheit. Return temperature must be at least 120 degrees Fahrenheit. If return temperature drops below 120, increase water heater capacity or reduce cycle time to maintain temperature."""),

    ("CIP DECISION TREE: ACID RINSE SELECTION",
     """Use this decision tree to determine when and how to implement acid rinse cycles.

Decision point 1: Is acid rinse needed? Answer YES if any of the following are true: Water hardness exceeds 5 gpg, visible mineral scale or milkstone present, SPC counts trending upward despite proper alkaline wash, or the operation has not used acid rinse in the past 7 days.

Decision point 2: Which acid product? Phosphoric acid-based: Standard choice for most operations. Effective mineral removal, moderate cost, good compatibility. Citric acid-based: For operations preferring organic-compatible options. Slightly less effective on heavy mineral deposits. Peracetic acid-based: Dual-purpose (acid rinse plus sanitization). More aggressive, requires careful handling.

Frequency decision tree: Daily acid rinse: Operations with water hardness above 7 gpg, or operations with active bacteria issues. Every-other-milking acid rinse: Operations with water hardness 5-7 gpg and stable SPC counts. Weekly acid rinse: Operations with water hardness below 5 gpg and excellent SPC history.

Concentration and temperature: Phosphoric acid at 0.5-1.0 ounce per gallon, temperature 100-130 degrees Fahrenheit. Do not heat acid rinse above 140 degrees. Warm acid is more effective, but excessive heat can cause acid to become volatile. Contact time: 5-8 minutes for pipeline circulation.

Important: Never follow an alkaline wash immediately with an acid rinse without an intermediate water rinse. Direct acid-to-alkaline contact neutralizes both chemicals and wastes product. The intermediate rinse should be clean water at ambient temperature for 2-3 minutes."""),

    ("CIP TROUBLESHOOTING DECISION TREE",
     """Use this decision tree when a CIP program is not producing satisfactory results despite correct chemical selection and concentration.

Problem: Residue visible after wash cycle. Check 1: Is the pre-rinse removing bulk milk? If milky residue remains after pre-rinse, increase pre-rinse water volume or duration. Pre-rinse should remove 95 percent of visible milk. Check 2: Is the wash temperature correct? Use an inline thermometer to verify start and return temperatures. Check 3: Is flow velocity adequate? Perform a bucket test. Minimum 5 fps for effective slug formation. If flow is low, check for restrictions (see flow troubleshooting section).

Problem: Milkstone or mineral buildup. Check 1: Is acid rinse being used? If not, implement immediately. Check 2: Is acid concentration correct for the water hardness? Refer to acid rinse decision tree. Check 3: When was the last manual inspection and hand-cleaning? Some buildup requires manual removal as a one-time reset before CIP can maintain cleanliness.

Problem: Biofilm formation (slimy residue). Biofilm is a serious issue that requires aggressive intervention. Step 1: Verify chlorine level in the alkaline wash is at least 100 ppm free chlorine. Step 2: Increase alkaline wash temperature to 170 degrees Fahrenheit start. Step 3: Extend alkaline wash contact time by 2-3 minutes. Step 4: If biofilm persists after 3 days, schedule an on-site visit for manual system inspection and deep cleaning.

Problem: Odor in the milking system. Check 1: Is the sanitizer rinse fresh? Old sanitizer rinse can develop odor. Check 2: Are there dead legs or unused pipeline sections holding stagnant solution? Check 3: Is the bulk tank CIP reaching all surfaces? Inspect spray ball coverage."""),

    ("SANITIZER RINSE PROTOCOLS",
     """The sanitizer rinse is the final step before milking and is critical for food safety. This section covers protocols for different sanitizer types.

Chlorine-based sanitizers: Concentration: 200 ppm for equipment surfaces. Prepare fresh solution within 1 hour of milking. Chlorine degrades rapidly, especially in warm environments. Do not heat chlorine sanitizer above 75 degrees Fahrenheit. Test concentration with chlorine test strips before each use.

Peracetic acid sanitizers: Concentration: 100-200 ppm depending on product. More stable than chlorine but must still be prepared fresh daily. Effective over a wider pH range than chlorine. No rinse required before milking when used at approved concentrations.

Quaternary ammonium sanitizers: Not recommended for dairy milking equipment as primary sanitizer due to potential residue concerns. May be used for non-food-contact surfaces in the parlor environment. Always verify product approval for dairy use.

Application method: For CIP systems, circulate sanitizer for 5-10 minutes at ambient temperature. Drain but do not rinse. For manual application, spray all food-contact surfaces and allow to drain. For bulk tanks, circulate or spray to cover all interior surfaces.

Record keeping: Document sanitizer type, concentration (verified by test strip), preparation time, and application time. This documentation is required for most dairy quality assurance programs and processor audits."""),

    ("NEW SYSTEM STARTUP PROCEDURE",
     """When a dairy installs new milking equipment or after major system modifications, follow this startup CIP protocol to establish a clean baseline.

Day 1 — Initial alkaline wash: Run three consecutive alkaline wash cycles at maximum recommended concentration. Temperature start at 170 degrees Fahrenheit. This removes manufacturing oils, metal residues, and packaging contaminants.

Day 1 — Acid treatment: After alkaline cycles, run one acid rinse cycle at maximum concentration to passivate stainless steel surfaces. This creates a protective oxide layer that resists future mineral adhesion.

Day 1 — Final rinse and sanitize: Rinse with clean water, then apply sanitizer at standard concentration. The system is ready for first milking.

Days 2-7 — Enhanced monitoring: Run the full CIP cycle after every milking (no shortcuts during the break-in period). Take SPC samples at days 2, 4, and 7 to establish a baseline.

After day 7: Transition to the operation's standard CIP protocol. The first four weeks of SPC data establish the expected performance range for the system. If counts trend upward during this period, investigate immediately rather than waiting for stabilization."""),
]

# ═══════════════════════════════════════════════════════════════════
# PDF 4: TECHNICAL DATA SHEETS (domain='product_info')
# Product technical specifications and application guides
# ═══════════════════════════════════════════════════════════════════

TECH_DATA_SECTIONS = [
    ("CURIASS BARRIER TEAT DIP TECHNICAL DATA",
     """Product name: Curiass Barrier Teat Dip. Chemistry: Chlorine dioxide (CLO2). Available in both concentrate and ready-to-use (RTU) formulations.

Curiass is Bower Ag's flagship barrier teat dip, designed for superior teat conditioning and germicidal protection. The chlorine dioxide chemistry provides broad-spectrum antimicrobial activity effective against the major mastitis-causing organisms including Staphylococcus aureus, Streptococcus agalactiae, Streptococcus uberis, and environmental coliforms.

Application: Curiass is approved for both pre-milking and post-milking teat dip application. As a pre-dip, apply and allow a minimum 30-second contact time before wiping teats and attaching milking units. As a post-dip, apply immediately after unit detachment for complete teat barrel and teat end coverage.

Barrier properties: The proprietary barrier film forms within 60 seconds of application and provides a persistent antimicrobial shield between milkings. The barrier film is designed to remain on the teat skin without irritation and washes off easily with the next pre-dip application.

Emollients: Curiass contains skin conditioning agents to maintain teat skin health even in harsh weather conditions. The emollient package includes glycerin at concentrations that maintain teat skin hydration without compromising germicidal activity.

RTU dilution: For operations using the concentrate formulation, refer to the CL2 Chart for correct dilution ratios. The standard RTU concentration produces a free CLO2 level of 50-100 ppm at the teat surface. Do not exceed or fall below the recommended dilution range.

Shelf life: 12 months from date of manufacture when stored at 50-80 degrees Fahrenheit in the original opaque container. Protect from light — CLO2 is photosensitive. Once diluted to RTU, use within 48 hours."""),

    ("PAVISE BARRIER TEAT DIP TECHNICAL DATA",
     """Product name: Pavise Barrier Teat Dip. Chemistry: Chlorhexidine gluconate. Available in concentrate and RTU formulations.

Pavise is Bower Ag's chlorhexidine-based teat dip offering persistent antimicrobial activity with excellent skin conditioning properties. Chlorhexidine provides sustained germicidal residual activity that continues working between milkings, making it particularly effective for post-dip applications in herds with contagious mastitis challenges.

Application: Approved for pre-milking and post-milking teat dip. Pre-dip application requires 30-second contact time. Post-dip: apply immediately after unit removal with full teat coverage. The chlorhexidine film is substantive to skin proteins, providing extended protection.

Efficacy: Chlorhexidine is effective against gram-positive bacteria (Staphylococcus aureus, Streptococcus species) and has moderate activity against gram-negative organisms. It is less affected by organic matter than iodine or chlorine-based dips, making it reliable in high-organic-load environments.

Skin conditioning: Pavise contains a proprietary emollient blend designed for harsh weather teat conditioning. Chlorhexidine's inherent mildness combined with the emollient package makes Pavise an excellent choice for operations where teat skin condition is a primary concern.

Compatibility: Pavise is compatible with standard dairy milking equipment. Do not use with anionic soap-based hand cleaners, which inactivate chlorhexidine. Ensure hands are rinsed after washing before applying Pavise.

AMS compatibility: Pavise RTU formulations are compatible with most automatic milking system (AMS) teat spray assemblies. Verify nozzle compatibility and spray pattern before use in robotic applications. Adjust spray volume per AMS manufacturer recommendations."""),

    ("SHIELD TEAT DIP TECHNICAL DATA",
     """Product name: Shield Teat Dip. Chemistry: Iodine-based (PVP-I, Povidone-iodine). Available in various concentrations.

Shield is Bower Ag's iodine-based teat dip product line. Iodine is one of the most well-established and proven germicides in dairy teat antisepsis, with decades of research supporting its efficacy against a broad spectrum of mastitis pathogens.

Available concentrations: Shield is offered in standard concentrations of 0.5 percent and 1.0 percent available iodine. The 1.0 percent formulation is recommended for herds with active contagious mastitis challenges. The 0.5 percent formulation is suitable for maintenance programs in herds with good udder health status.

Application: Approved for both pre-dip and post-dip use. Pre-dip: allow 30-second contact time. The iodine color provides visual confirmation of teat coverage, which is an advantage for training and auditing parlor staff.

Skin conditioning: Shield contains emollients including lanolin and glycerin to counteract the natural drying effect of iodine. Operations in cold climates should consider the higher-emollient formulation (Shield Plus) for winter months.

Iodine residue considerations: High-concentration iodine teat dips can contribute to elevated iodine levels in bulk tank milk if pre-dip is not properly wiped before milking. Always ensure complete pre-dip removal with clean, dry towels before unit attachment.

OFB (On-Farm Blending): Shield is available in tote quantities for on-farm blending programs. The Shield OFB program uses Shield concentrate at a base cost of 38 dollars per gallon combined with HydroSurge at 15 dollars per gallon for the blending base. Refer to the Shield OFB Reference Calculator for specific blend ratios and cost calculations."""),

    ("CD114 CHLORINATED ALKALINE DETERGENT TECHNICAL DATA",
     """Product name: CD114 Chlorinated Alkaline Detergent. Chemistry: Sodium hydroxide plus sodium hypochlorite. Primary application: CIP (Clean-In-Place) milking system wash.

CD114 is Bower Ag's workhorse CIP alkaline detergent designed for removing milk fats, proteins, and organic residues from dairy milking equipment. The dual-action formula combines alkaline cleaning power with chlorinated oxidation for superior organic soil removal.

Concentration guidelines: Use the CD114 Usage Rate reference chart for exact dilution based on water hardness and system type. General ranges: Soft water (0-3.5 gpg): 1.0-1.5 oz per gallon. Moderate water (3.5-7 gpg): 1.5-2.0 oz per gallon. Hard water (7-10.5 gpg): 2.0-2.5 oz per gallon. Very hard water (above 10.5 gpg): 2.5-3.0 oz per gallon.

Temperature requirements: Wash solution must start at 160-170 degrees Fahrenheit. Return temperature must not drop below 120 degrees Fahrenheit. Higher start temperatures improve fat emulsification but should not exceed 180 degrees to prevent protein denaturation and baking onto surfaces.

Contact time: Minimum 8 minutes of circulation at proper temperature and flow velocity. Longer contact times (10-12 minutes) are recommended for systems with heavy soil loads or extended milking times.

Chlorine content: CD114 provides approximately 100-150 ppm free chlorine at standard use dilution. This chlorine level is sufficient for organic soil oxidation and assists in biofilm prevention. Chlorine levels decline during the wash cycle; the starting concentration ensures adequate levels throughout.

Storage: Store between 40-100 degrees Fahrenheit. Keep container sealed when not in use. Chlorinated alkaline products slowly lose chlorine activity over time; use within 6 months of purchase for optimal performance. Do not store near acid products."""),

    ("ACID RINSE PRODUCTS TECHNICAL DATA",
     """Bower Ag offers multiple acid rinse formulations for different dairy applications and preferences.

Phosphoric Acid Rinse: Standard dairy acid rinse. Effective for mineral deposit removal including milkstone (calcium phosphate) and hard water scale (calcium carbonate). Use at 0.5-1.0 oz per gallon at 100-130 degrees Fahrenheit. Safe for all standard dairy equipment materials at recommended concentrations.

Citric Acid Rinse: Organic-compatible option. Effective for light to moderate mineral deposits. Slightly less aggressive than phosphoric acid on heavy scale but suitable for operations with organic certification requirements. Use at 0.75-1.5 oz per gallon at 100-120 degrees Fahrenheit.

Peracetic Acid Combination: Dual-purpose acid rinse and sanitizer. Provides both mineral removal and antimicrobial activity in a single step. Particularly useful for operations looking to simplify their CIP program or those with limited hot water capacity. Use at manufacturer-specified concentration (varies by formulation).

Selection guide: Choose phosphoric acid for standard operations with moderate to heavy mineral challenges. Choose citric acid for organic operations or those with light mineral issues. Choose peracetic acid combination for operations wanting simplified CIP or where a separate sanitizer step is impractical.

All acid rinse products must be used with an intermediate water rinse between the alkaline wash and acid rinse. Never allow alkaline and acid products to mix in the system."""),

    ("PRODUCT COMPATIBILITY MATRIX",
     """This matrix defines which Bower Ag products can be used in sequence or in proximity within a dairy operation. Following these guidelines prevents chemical incompatibilities and ensures optimal product performance.

Teat dip rotation: Curiass (CLO2) and Pavise (chlorhexidine) can be rotated seasonally without adverse effects. However, do not mix the two products in the same application device. Flush application equipment thoroughly when switching between product chemistries.

Curiass and Shield: Both can be used in the same operation for different purposes (e.g., Curiass as pre-dip, Shield as post-dip). Do not mix in the same container. Each has distinct chemistry that should be applied independently.

CIP and teat dip: CIP chemicals (CD114, acid rinse) do not interact with teat dip products as they serve different functions and contact different surfaces. However, ensure thorough rinsing of milking equipment after CIP before milking to prevent any CIP chemical residue from contacting cow teats.

Concentrate mixing: Never combine concentrates from different product lines. Each product is formulated as a complete chemistry. Adding additional chemicals to a Bower Ag product invalidates the product's performance claims and may create safety hazards.

Equipment materials: All Bower Ag products are compatible with stainless steel (304 and 316), food-grade rubber, food-grade silicone, and HDPE plastic at recommended concentrations. Extended exposure to concentrations above recommended levels may damage rubber components over time."""),
]

# ═══════════════════════════════════════════════════════════════════
# PDF 5: SHIELD OFB REFERENCE (domain='calculation')
# On-Farm Blending calculations and reference tables
# ═══════════════════════════════════════════════════════════════════

SHIELD_OFB_SECTIONS = [
    ("SHIELD OFB PROGRAM OVERVIEW",
     """The Shield On-Farm Blending (OFB) program allows dairy operations to create their own teat dip formulations using Bower Ag Shield concentrate and HydroSurge blending base. This program offers cost savings for large operations while maintaining consistent product quality.

Base components: Shield concentrate at 38 dollars per gallon. HydroSurge blending base at 15 dollars per gallon. The final blended product cost depends on the mixing ratio, which is determined by the target iodine concentration and desired emollient level.

Program eligibility: OFB is typically recommended for operations milking 500 or more cows, purchasing in tote quantities (275-gallon minimum). Smaller operations should use pre-mixed Shield products for consistency and convenience.

Quality assurance: Every OFB batch must be tested with an iodine test strip to verify the target concentration before use. Bower Ag provides test strips and a quality log template for each OFB customer. Out-of-spec batches must be adjusted or discarded, never used on cows.

Equipment requirements: Tote storage with secondary containment, mixing tank (food-grade polyethylene, minimum 100-gallon capacity), transfer pump (chemical-resistant, low-shear), iodine test strips (provided by Bower Ag), graduated measuring container for volume accuracy."""),

    ("SHIELD OFB MIXING RATIOS AND CALCULATIONS",
     """Standard mixing ratios for Shield OFB program. All ratios are expressed as parts Shield concentrate to parts HydroSurge base.

Target 1.0 percent available iodine (post-dip, high-challenge herds): Mix ratio: 1 part Shield to 2 parts HydroSurge. Cost per gallon of finished product: Calculate as (38 times 1 plus 15 times 2) divided by 3 equals 22.67 dollars per gallon. Volume example: To make 100 gallons, use 33.3 gallons Shield plus 66.7 gallons HydroSurge.

Target 0.5 percent available iodine (post-dip, maintenance herds): Mix ratio: 1 part Shield to 4 parts HydroSurge. Cost per gallon of finished product: (38 times 1 plus 15 times 4) divided by 5 equals 19.60 dollars per gallon. Volume example: To make 100 gallons, use 20 gallons Shield plus 80 gallons HydroSurge.

Target 0.25 percent available iodine (pre-dip application): Mix ratio: 1 part Shield to 8 parts HydroSurge. Cost per gallon of finished product: (38 times 1 plus 15 times 8) divided by 9 equals 17.56 dollars per gallon. Volume example: To make 100 gallons, use 11.1 gallons Shield plus 88.9 gallons HydroSurge.

General formula: Cost per gallon equals (Shield gallons times 38 plus HydroSurge gallons times 15) divided by total gallons. Always round up Shield volume to ensure minimum iodine concentration is met."""),

    ("SHIELD OFB TOTE COST CALCULATIONS",
     """Tote-based calculations for Shield OFB cost analysis and customer quoting.

Tote sizes: Standard Shield concentrate tote: 275 gallons. Standard HydroSurge tote: 275 gallons. Both components must be ordered in full tote quantities for OFB pricing to apply.

Cost per tote: Shield concentrate tote: 275 gallons times 38 dollars equals 10,450 dollars per tote. HydroSurge tote: 275 gallons times 15 dollars equals 4,125 dollars per tote.

Yield calculations at 1.0 percent target: One Shield tote plus two HydroSurge totes equals 825 gallons of finished product. Total cost: 10,450 plus 8,250 equals 18,700 dollars. Cost per gallon: 22.67 dollars. Yield per cow per year: At approximately 0.5 ounces per application, 2 applications per day, 365 days equals approximately 2.85 gallons per cow per year. A 1,000-cow operation uses approximately 2,850 gallons per year, requiring 3.45 tote sets per year.

Yield calculations at 0.5 percent target: One Shield tote plus four HydroSurge totes equals 1,375 gallons of finished product. Total cost: 10,450 plus 16,500 equals 26,950 dollars. Cost per gallon: 19.60 dollars. This lower concentration yields more volume per Shield tote, reducing per-cow cost.

Comparison to pre-mixed: Pre-mixed Shield at 1.0 percent costs approximately 28-32 dollars per gallon depending on quantity. OFB at 22.67 dollars per gallon represents a savings of 5.33-9.33 dollars per gallon, or approximately 19-29 percent cost reduction. For a 1,000-cow operation, annual savings range from 15,000 to 26,000 dollars."""),

    ("CL2 CHART: CURIASS AND PAVISE RTU CALCULATIONS",
     """The CL2 (Chlorine Dioxide Level 2) Chart provides standard dilution calculations for Curiass and Pavise concentrate-to-RTU conversion.

Curiass concentrate-to-RTU dilution: Standard RTU target: 50-100 ppm free CLO2 at the teat surface. Dilution ratio: 1 part concentrate to 3 parts water for standard applications. This produces approximately 75 ppm free CLO2.

High-challenge dilution: 1 part concentrate to 2 parts water produces approximately 100 ppm free CLO2. Use this concentration for herds with active contagious mastitis outbreaks, new infection rates above 5 percent per month, or when environmental pathogen pressure is high (e.g., wet bedding, overcrowded housing).

Low-maintenance dilution: 1 part concentrate to 4 parts water produces approximately 50 ppm free CLO2. Use this concentration only for herds with excellent udder health history (SCC below 150,000, new infection rate below 1 percent per month).

Cost-per-gallon at each dilution: Assuming Curiass concentrate at its current location-specific pricing. Standard (1:3): Concentrate cost divided by 4. High-challenge (1:2): Concentrate cost divided by 3. Low-maintenance (1:4): Concentrate cost divided by 5.

Pavise concentrate-to-RTU: Standard dilution: 1 part concentrate to 3 parts water. Chlorhexidine concentration at RTU should be 0.5-1.0 percent depending on the specific Pavise formulation. Verify target concentration with the Pavise product label.

Important: Always use clean, potable water for dilution. Water temperature should be ambient (50-70 degrees Fahrenheit). Do not use hot water for teat dip dilution. Mix thoroughly for at least 2 minutes to ensure homogeneous solution. Use within 48 hours of preparation."""),

    ("CD114 USAGE RATE REFERENCE",
     """The CD114 Usage Rate reference provides exact concentration calculations based on water hardness and system parameters.

CD114 is a chlorinated alkaline CIP detergent. Correct concentration is critical: too low allows soil buildup, too high wastes product and may damage equipment components (particularly rubber parts).

Standard usage rate table: Water hardness 0-3 gpg: 1.0 oz per gallon of wash solution. Water hardness 3-5 gpg: 1.25 oz per gallon. Water hardness 5-7 gpg: 1.5 oz per gallon. Water hardness 7-10 gpg: 2.0 oz per gallon. Water hardness 10-15 gpg: 2.5 oz per gallon. Water hardness above 15 gpg: 3.0 oz per gallon (and strongly recommend water softener installation).

System volume calculation: Determine total pipeline volume in gallons. Add wash solution reservoir volume (typically 20-30 percent of pipeline volume). Multiply total volume by the usage rate for your water hardness to get the total CD114 volume needed per wash cycle.

Example: A parlor with 200 feet of 2-inch pipeline. Pipeline volume: approximately 17 gallons. Reservoir: 5 gallons. Total wash volume: 22 gallons. At 7 gpg water hardness (2.0 oz per gallon): 22 times 2.0 equals 44 oz (approximately 1.4 quarts) of CD114 per wash cycle.

Monthly cost calculation: CD114 volume per wash times washes per day times 30 days equals monthly CD114 usage. Multiply by cost per ounce (from location-specific pricing) for the monthly CIP detergent cost.

Verification: After each wash cycle, test rinse water pH to ensure alkaline residue is removed (target pH 6.5-7.5 after final rinse). Periodically test wash solution concentration using alkalinity test strips to verify automatic dispensing accuracy."""),
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    pdfs = [
        ("Bower_Ag_Troubleshooting_Guide.pdf",
         "Bower Ag — Troubleshooting Guide\nBacteria, Water Quality, CIP Flow & Parlor Systems",
         TROUBLESHOOTING_SECTIONS),

        ("Bower_Ag_SDS_Binder.pdf",
         "Bower Ag — Safety Data Sheet Binder\nProduct Safety, Handling & Emergency Procedures",
         SDS_SECTIONS),

        ("Bower_Ag_CIP_Decision_Tree.pdf",
         "Bower Ag — CIP Decision Tree\nClean-In-Place Procedures & Protocols",
         CIP_SECTIONS),

        ("Bower_Ag_Tech_Data_Sheets.pdf",
         "Bower Ag — Technical Data Sheets\nProduct Specifications & Application Guides",
         TECH_DATA_SECTIONS),

        ("Bower_Ag_Shield_OFB_Reference.pdf",
         "Bower Ag — Shield OFB Reference\nOn-Farm Blending Calculations & Cost Analysis",
         SHIELD_OFB_SECTIONS),
    ]

    for filename, title, sections in pdfs:
        path = _create_pdf(filename, title, sections)
        print(f"✅ Created: {filename} ({len(sections)} sections)")

    print(f"\n📁 All PDFs saved to: {OUTPUT_DIR}")
    print(f"📊 Total documents: {len(pdfs)}")
    print(f"📊 Total sections: {sum(len(s) for _, _, s in pdfs)}")


if __name__ == "__main__":
    main()
