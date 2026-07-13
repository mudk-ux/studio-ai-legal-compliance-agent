# Formal Specification: M&E Copyright Infringement & Legal Compliance Platform
**Version:** 1.0.0  
**Specification Type:** Behavior-Driven Development (BDD / Gherkin)  
**Target Runtimes:** Google Cloud Agent Development Kit (ADK 2.0) / Vertex AI Reasoning Engine  

---

## Feature 1: Dynamic Intake & Policy Constitution Compilation
As a Studio Legal Clearance Operator  
I want to upload a media asset accompanied by dynamic show constraints (`constraints.json`)  
So that the Coordinator Agent adapts its vetting boundaries at runtime.

### Scenario 1.1: Ingestion of Text Screenplay with Dynamic Sponsor & Census Rules
- **Given** an uploaded text screenplay asset (`social_network_script.txt`)
- **And** a dynamic constraint payload specifying `target_rating: "TV-14"`, `target_city_census: "Seattle"`, and `restricted_competitors: ["GoDaddy", "Heineken"]`
- **When** the Coordinator Agent compiles the Active Policy Constitution
- **Then** the Name Vetter Agent must evaluate extracted character surnames against the Seattle metropolitan census 0/3-Plus Rule
- **And** the Brand Vetter Agent must flag commercial references to "GoDaddy" or "Heineken" as un-cleared product references.

---

## Feature 2: Hybrid ML + GenAI Multimodal Image & Wardrobe Clearance
As a Wardrobe Clearance Specialist  
I want pre-production set and costume photographs audited against open-world sponsor exclusivity deals  
So that un-cleared competitor logos are caught before filming begins.

### Scenario 2.1: Sportswear Logo Exclusivity Audit
- **Given** an uploaded costume photograph (`mock_sports_clothing.jpg`)
- **And** an active exclusivity constraint specifying `primary_sponsor: "Adidas"` and `restricted_competitors: ["Nike", "Puma"]`
- **When** the Image Vetting pipeline executes
- **Then** the Cloud Vision API performs initial logo and web detection
- **And** Gemini 3.5 Pro evaluates the detected "Nike" swoosh logo against the `restricted_competitors` constraint
- **Then** the report must record a high-severity `EXCLUSIVITY_BREACH` flag (`FLAG-02`) recommending wardrobe replacement or VFX masking.

---

## Feature 3: Temporal Script-to-Video Synchronization & Selective Keyframe Vetting
As a Post-Production Supervisor  
I want long rough-cut video timelines audited only at specific script-identified timestamps  
So that long-form video analysis is fast, cost-efficient, and visually precise.

### Scenario 3.1: Temporal Keyframe Extraction & Hardware Exclusivity Audit
- **Given** an uploaded 1080p rough-cut video (`tears_of_steel_1080p.mov`)
- **And** a dynamic temporal constraint specifying target timestamps (`00:00:33` for robotic arm design check, `00:02:30` for control room hardware check)
- **And** hardware sponsor exclusivity rules specifying `primary_sponsor: "Dell"` and `restricted_competitors: ["Apple", "Google"]`
- **When** the Script-to-Video Synchronization Engine executes
- **Then** `ffmpeg_slicer` must extract isolated JPEG keyframes strictly around `00:00:33` and `00:02:30`
- **And** Gemini 3.5 Pro must audit the keyframe at `00:02:30` for competitor hardware emblems
- **Then** if an un-cleared competitor emblem is detected, the report must output an automated `VFXPaintOutSlate` with exact timecode EDL parameters.

---

## Feature 4: E&O Insurance Audit Ledger Generation
As an Errors & Omissions (E&O) Insurance Underwriter  
I want a cryptographically verifiable JSONL audit trail of every clearance check  
So that diligence is documented for broadcast liability coverage.

### Scenario 4.1: Audit Ledger Export
- **Given** a completed multi-agent compliance evaluation run
- **When** the report compiler finalizes the deliverable
- **Then** it must output a structured `ComplianceReport` JSON containing itemized `FlaggedViolation` objects, human-in-the-loop sign-off statuses, and timestamped API execution spans.
