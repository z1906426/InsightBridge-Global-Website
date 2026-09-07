#!/usr/bin/env python3
"""
InsightBridge Global & Buildtelligence — Schema.org JSON-LD Generator
=====================================================================
GEO (Generative Engine Optimization) Structured Data Automation

Usage:
    python3 generate-schema.py

Output:
    - insightbridge_schema.json  (for insightbridge.global <head>)
    - buildtelligence_schema.json (for buildtelligence.com <head>)
    - insightbridge_schema.html   (ready-to-paste <script> block)
    - buildtelligence_schema.html  (ready-to-paste <script> block)

Author: Generated for Dr. Tong Yin / InsightBridge Global LLC
Date:   September 2026
"""

import json
import os

# =============================================================================
# 1. INSIGHTBRIDGE GLOBAL — FULL SCHEMA
# =============================================================================

def build_insightbridge_schema():
    """Build the complete InsightBridge Global JSON-LD @graph."""

    # --- Organization ---
    org = {
        "@type": "Organization",
        "@id": "https://insightbridge.global/#org",
        "name": "InsightBridge Global LLC",
        "alternateName": "美国洞见桥全球公司",
        "url": "https://insightbridge.global",
        "logo": "https://insightbridge.global/assets/logo.png",
        "foundingDate": "2024",
        "description": (
            "A theory-driven strategic think tank specializing in national strategy, "
            "sector strategy, and operational AI execution. Originator of four proprietary "
            "management frameworks: The Home Model, Governance Debt, Dynamic Driver "
            "Replacement Theory, and Core Code Theory. Publisher of InsightBridge Global "
            "Intelligence, a weekly bilingual strategic-intelligence briefing."
        ),
        "knowsAbout": [
            "Hospitality AI Revenue Management",
            "Quantitative Finance",
            "Governance Theory",
            "National Strategy",
            "Tourism Economics",
            "Organizational Resilience",
            "Dynamic Pricing",
            "AI Strategy",
            "Civilizational Governance",
            "Holographic and Dynamic Thinking",
            "Geopolitical Strategy",
            "National Organizational Behavior"
        ],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Auburn",
            "addressRegion": "Alabama",
            "addressCountry": "US"
        },
        "sameAs": [
            "https://intelligence.insightbridge.global",
            "https://press.insightbridge.global",
            "https://lab.insightbridge.global"
        ],
        "numberOfEmployees": {"@type": "QuantitativeValue", "value": "Small"},
        "legalName": "InsightBridge Global LLC",
        "areaServed": "Worldwide"
    }

    # --- Founder: Dr. Tong Yin ---
    founder = {
        "@type": "Person",
        "@id": "https://insightbridge.global/#founder",
        "name": "Dr. Tong Yin",
        "alternateName": "殷彤博士",
        "jobTitle": "Founder & Chief Research Officer",
        "worksFor": {"@id": "https://insightbridge.global/#org"},
        "alumniOf": [
            {
                "@type": "EducationalOrganization",
                "name": "Auburn University",
                "department": "Hospitality Management (Ph.D.)"
            },
            {
                "@type": "EducationalOrganization",
                "name": "Eastern Illinois University",
                "department": "M.B.A."
            }
        ],
        "knowsLanguage": ["English", "Mandarin Chinese"],
        "sameAs": [
            "https://orcid.org/0009-0007-6810-9888",
            "https://www.wikidata.org/wiki/Q139565442",
            "https://scholar.google.com/citations?hl=en&user=dP7vYgMAAAAJ",
            "https://www.researchgate.net/profile/Tong-Yin-18",
            "https://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id=10401996"
        ],
        "description": (
            "Originator of mutually load-bearing organizational frameworks including "
            "Core Code Theory, The Home Model, Governance Debt, Dynamic Driver "
            "Replacement Theory, and the Holographic and Dynamic Thinking Mode. "
            "Ph.D. Hospitality Management, Auburn University. Author of nine academic "
            "manuscripts — six under contract or review with Routledge, CABI, Columbia "
            "University Press, Cambridge University Press, and Bloomsbury Academic. "
            "The ninth, Subduing Without Fighting, is the strategic master outline of "
            "the entire corpus. Regular editorial contributor to Hospitality Net, "
            "Hotel News Resource, and PhocusWire. Research has received 38 verified "
            "citations across 8 countries and 5 languages."
        )
    }

    # --- Nine Manuscripts ---
    manuscripts = [
        {
            "title": "Beyond Chaos: Why Growth Destroys What It Creates and How Covenant Governance Sustains Firms in the AI Age",
            "alternateName": "超越混沌",
            "description": (
                "Explains the chaos paradox: the same chaos that fuels explosive early growth "
                "becomes the mechanism of collapse in a mature firm. Answers it with three "
                "interlocking theories — Dynamic Driver Replacement Theory (DDRT), Core Code "
                "Theory, and the Home Model. Quantifies the Mistrust Tax across five layers and "
                "Management Debt as compounding cost. AI is treated as a friction catalyst that "
                "compresses structural friction while amplifying relational friction. Six parts, "
                "eighteen chapters, ten testable propositions, eight-dimension Trust Audit, "
                "five-layer Mistrust Tax Calculator, and a 180-day roadmap."
            ),
            "keywords": (
                "chaos paradox, DDRT, Dynamic Driver Replacement Theory, Core Code Theory, "
                "Home Model, Mistrust Tax, Management Debt, AI friction catalyst, governance "
                "quality, driver replacement inflection point, organizational resilience"
            ),
            "status": "Manuscript complete"
        },
        {
            "title": "THE HOME MODEL: The Only Management Moat AI Cannot Cross",
            "alternateName": "家园模型",
            "description": (
                "A covenant-based governance framework holding that the one organisational "
                "capability AI cannot replicate is identity fusion under crisis. Six pillars: "
                "Hard Frame (Merit-Based Mobility, Institutionalized Innovation, Eliminating "
                "Property Managers) and Soft Connection (Career Sovereignty, Psychological "
                "Safety Net, Dignified Transitions). Mechanism chain: Sustained Benevolence -> "
                "Identity Fusion -> Anti-Fragile Loyalty -> Survival Premium. Includes "
                "five-layer Mistrust Tax Calculator showing $199M annual cost for a 5,000-person "
                "organization (~25% of revenue), eight-dimension Trust Audit, and 180-day roadmap."
            ),
            "keywords": (
                "Home Model, covenant governance, identity fusion, survival premium, mistrust tax, "
                "hard frame, soft connection, wolf culture critique, AI management moat, "
                "organizational trust architecture, Dr. Tong Yin"
            ),
            "status": "Manuscript complete"
        },
        {
            "title": "CORE CODE: A New Theory of Human Capital Inimitability for the AI Era",
            "alternateName": "核心代码",
            "description": (
                "Establishes the VRIN-based separation of an organisation's codifiable Performance "
                "UI from its tacit, identity-based Core Code — moral courage, non-linear intuition, "
                "and voluntary collective sacrifice. Introduces the Katrin Principle: the most "
                "valuable employee is the one your system cannot see (multiplier ~19:1). Trust "
                "accumulates logarithmically; negative signals destroy trust 3-5x faster than "
                "positive signals build it. Crisis response governed by peer trust density. "
                "Written as textbook: twelve chapters, six formal propositions, six empirical "
                "research designs, and a CFO-ready Mistrust Tax Calculator."
            ),
            "keywords": (
                "Core Code Theory, Performance UI, VRIN framework, Katrin Principle, identity "
                "fusion, peer trust density, human capital inimitability, AI substitution boundary, "
                "Substitution Test, code drift, code integrity"
            ),
            "status": "Manuscript complete"
        },
        {
            "title": "The Vertical Frontier: Why Mid-Sized Nations Must Abandon Industrial Mediocrity and Turn to Strategic Tourism",
            "alternateName": "垂直前沿",
            "description": (
                "A ten-year operating manual for Europe's second-tier economies. Deconstructs the "
                "Industrial Mirage and Workbench Model (foreign assembly with suppressed wages and "
                "talent outflow). Proposes Strategic Verticalism: managing inherited culture, "
                "heritage, landscape, and climate as a national strategic vertical with Austria "
                "as operating prototype. Sovereign Premium Positioning: cut visitors 25%, raise "
                "average spend 40%, total revenue rises 5% while infrastructure pressure falls. "
                "Includes TVRI (Tourism Vertical Readiness Index) and IMRS (Industrial Mirage "
                "Risk Score) four-quadrant strategic map."
            ),
            "keywords": (
                "Strategic Verticalism, Industrial Mirage, Sovereign Premium Positioning, TVRI, "
                "IMRS, Austria tourism model, mid-sized nations, tourism vertical, Workbench Model, "
                "European second-tier economies"
            ),
            "status": "Manuscript complete"
        },
        {
            "title": "Active Demand Sovereignty: Rebuilding Tourism as a Strategic Vertical in the Age of AI",
            "alternateName": "主动需求主权",
            "description": (
                "Competitive tourism is never bestowed by geography — it is deliberately built. "
                "Introduces Wasted Asset Theory (unused capacity is permanent value destruction), "
                "Ecosystem Revenue (full visitor value across all sectors), the Trinity of "
                "Sustainable Demand (Commercial Necessity, Event Hegemony, Singularity Archetype), "
                "and destination-scale revenue management via an AI Commander system with T-90 "
                "strategic seeding, T-60 segment action, and T-14 pricing/conversion measures. "
                "Proposes a Tourism Vertical Authority and National Tourism Data Platform. "
                "Twenty-two chapters across five parts."
            ),
            "keywords": (
                "Active Demand Sovereignty, Wasted Asset Theory, AI Commander, destination revenue "
                "management, Trinity of Sustainable Demand, Tourism Vertical Authority, ecosystem "
                "revenue, demand catalysis, digital sovereignty"
            ),
            "status": "Manuscript complete"
        },
        {
            "title": "INTELLECTUAL SOVEREIGNTY: National Strategy, Educational Reconstruction, and Civilizational Evolution in the AI Era",
            "alternateName": "智力主权",
            "description": (
                "The real source of national power has shifted from territory and physical resources "
                "to the density and renewability of high-quality cognition. Establishes IS-FEM "
                "(Intellectual Sovereignty Full-Element Model: P = I x (E+G) x C / S), the 1% "
                "Theorem (frontier competitiveness determined by a thin top stratum of cognitive "
                "talent), and the neuron-density principle. Proposes education as sovereign "
                "infrastructure with four strategic outputs: skills, judgment, cultural cohesion, "
                "and cognitive immune system. Heart-winning strategy and Five-Star Hotel Principle "
                "recast governance as hospitality. Four parts, thirteen chapters, ~110,000 words."
            ),
            "keywords": (
                "Intellectual Sovereignty, IS-FEM, 1% Theorem, neuron density principle, "
                "heart-winning strategy, education as sovereign infrastructure, Great Brain Transfer, "
                "cognitive capture, Strategic Burden Formula, civilizational evolution"
            ),
            "status": "Manuscript complete"
        },
        {
            "title": "Knowledge Creation: A Theory of Knowledge Evolution and Civilizational Progress",
            "alternateName": "知识创造",
            "description": (
                "Develops Reality-Driven Knowledge Evolution (RDKE), treating knowledge as a living "
                "system to be cultivated rather than a static object to be stored. Six-phase cycle: "
                "Reality -> Question -> Thinking -> Theory -> Practice -> Evidence -> New Reality. "
                "Four original models: Knowledge Value Pyramid (modern institutions have inverted "
                "it by treating countable outputs as the summit), Knowledge Evolution Spiral "
                "('a loop is stationary; a spiral moves'), Knowledge Ecosystem (seven actors, six "
                "couplings), and Knowledge Life Cycle. AI has industrialized skill; capability "
                "remains scarce. Volume I of Knowledge Creation Theory."
            ),
            "keywords": (
                "RDKE, Reality-Driven Knowledge Evolution, Knowledge Value Pyramid, Knowledge "
                "Evolution Spiral, living knowledge, knowledge ecology, knowledge life cycle, "
                "civilizational progress, epistemology"
            ),
            "status": "Manuscript complete — Volume I"
        },
        {
            "title": "THE LONG WINTER OF CIVILIZATIONS: Decline, the Sieve, and the Coming Rebirth",
            "alternateName": "文明的漫长冬季",
            "description": (
                "Proposes the Historical Spiral theory: civilizations neither decline in straight "
                "lines nor repeat on a flat wheel — they spiral, returning to earlier conditions at "
                "a different altitude. Central mechanism is the Sieve: sustained adversity strips "
                "prosperity's disguises, testing real capability vs. credential, rent, and "
                "performance. Diagnoses the 'comfortable apocalypse' — decline amid material "
                "abundance with Japan as principal living sample. Current moment defined by global "
                "synchrony: no outside reserve. Eighteen chapters in dialogue with Ibn Khaldun, "
                "Spengler, Toynbee, Turchin, Dalio, and Taleb. ~100,000 words."
            ),
            "keywords": (
                "Historical Spiral, the Sieve, comfortable apocalypse, comfortable dark age, "
                "silent ascent, capability revolution, civilizational decline and rebirth, global "
                "synchrony, admission criterion transformation"
            ),
            "status": "Manuscript complete"
        },
        {
            "title": "Subduing Without Fighting: Applications in the AI Era — The Modern Construction of Sun Tzu's Highest Strategy",
            "alternateName": "不战而屈人之兵：AI 时代的应用——孙子兵法最高战略的现代重构",
            "description": (
                "The supreme synthesis and strategic master outline of the entire nine-manuscript "
                "corpus. Reconstructs Sun Tzu's 'subduing the enemy without fighting' as a "
                "three-variable actuarial model: Strategic Dimension Set S (twelve dimensions at "
                "national level, eight at corporate), Catch-Up Time Upper Bound T* (threshold: "
                ">25 years), and Feasible Strategy Set F. Introduces the Multi-Dimensional "
                "Deterrence Matrix across twelve dimensions (Military, Financial, Industrial, "
                "Technological, Compute, Energy, Data, Talent, Organizational, Ideological, "
                "Coalitional, Resilience). Operationalizes the Holographic and Dynamic Thinking "
                "Mode — a four-step cycle (full-spectrum data intake, multi-dimensional "
                "organizational restructuring, scenario stress testing, dynamic feedback "
                "correction) — as the cognitive engine of civilizational continuity. Defines "
                "'strategic cognitive risk in the AI era' and constructs cognitive barriers "
                "through Intellectual Sovereignty and Active Demand Sovereignty at the "
                "information-retrieval and machine-readable distribution layers. Provides a "
                "complete National Organizational Behavior framework, arguing that under "
                "deglobalization and the Long Winter, only institutionalized capability-based "
                "admission and the silent ascent of ground-level elites produce genuine "
                "anti-fragile dominance. Cross-generational maintenance as steady-state key — "
                "in AI era, stability window compressed from 40 years to 12-24 months. "
                "Bilingual, ~84,000 Chinese characters + ~41,700 English words."
            ),
            "keywords": (
                "Subduing Without Fighting, Sun Tzu, Multi-Dimensional Deterrence Matrix, "
                "cross-generational maintenance, actuarial strategy, twelve strategic dimensions, "
                "AI era strategy, civilizational continuity, Holographic and Dynamic Thinking, "
                "cognitive sovereignty, cognitive barrier, National Organizational Behavior, "
                "silent ascent, anti-fragile dominance, strategic cognitive risk"
            ),
            "datePublished": "2026",
            "status": "Published 2026, InsightBridge Global"
        }
    ]

    graph = [org, founder]

    for i, m in enumerate(manuscripts, 1):
        article = {
            "@type": "ScholarlyArticle",
            "@id": f"https://insightbridge.global/books#manuscript-{i:02d}",
            "mainEntityOfPage": "https://insightbridge.global/books",
            "headline": m["title"],
            "alternateName": m.get("alternateName", ""),
            "description": m["description"],
            "author": {"@id": "https://insightbridge.global/#founder"},
            "publisher": {"@id": "https://insightbridge.global/#org"},
            "inLanguage": ["en", "zh"],
            "keywords": m["keywords"],
            "creativeWorkStatus": m["status"]
        }
        if "datePublished" in m:
            article["datePublished"] = m["datePublished"]
        graph.append(article)

    # --- Vision 2030 Scorecard ---
    scorecard = {
        "@type": "TechArticle",
        "@id": "https://insightbridge.global/publications/vision-2030-scorecard#article",
        "mainEntityOfPage": "https://insightbridge.global/publications/vision-2030-scorecard",
        "headline": (
            "What We Wrote in May — And What July Confirmed: "
            "A Scorecard on Vision 2030's Ultra-Luxury Tourism Program"
        ),
        "description": (
            "Five dated public predictions on Saudi Arabia's Vision 2030 ultra-luxury "
            "tourism program, all confirmed within 4-8 weeks by official data. "
            "ADR down 11.4% YoY (predicted ~12%); Riyadh occupancy down 13.5pp to 52.2%; "
            "Makkah RevPAR +39% during Hajj (framework predicts its own exceptions); "
            "NEOM redesigned with The Line deferred to 2030 ($8B written off, population "
            "target 9M -> <300K); Mukaab suspended with PIF $16B earmarked for contract "
            "terminations. Independently reflected by Yahoo Scout generative AI search "
            "on July 31, 2026 — machine-side confirmation of chronological priority."
        ),
        "datePublished": "2026-07-29",
        "author": {"@id": "https://insightbridge.global/#founder"},
        "publisher": {"@id": "https://insightbridge.global/#org"},
        "url": "https://insightbridge.global/publications/vision-2030-scorecard",
        "isPartOf": {
            "@type": "PublicationIssue",
            "name": "InsightBridge Global Intelligence"
        },
        "keywords": (
            "Vision 2030, Saudi Arabia, ADR collapse, structural mismatch, "
            "NEOM, The Line, de-hotelisation, track record, prediction verification"
        )
    }
    graph.append(scorecard)

    # --- Four Proprietary Frameworks ---
    frameworks = [
        {
            "name": "Core Code Theory",
            "alternateName": "核心代码理论",
            "url": "https://insightbridge.global/theories/core-code-theory",
            "description": (
                "Strategic-management framework originated by Dr. Tong Yin that separates an "
                "organisation's codifiable Performance UI from its tacit, identity-based Core "
                "Code, and uses that separation to locate the precise boundary along which "
                "artificial intelligence can substitute for human work. Key components: "
                "Performance UI, Core Code, the Substitution Test, Code Drift, and Code Integrity."
            )
        },
        {
            "name": "The Home Model",
            "alternateName": "家园模型",
            "url": "https://insightbridge.global/theories/home-model",
            "description": (
                "Covenant-based management framework originated by Dr. Tong Yin holding that "
                "the one organisational capability AI cannot replicate is identity fusion under "
                "crisis. Six pillars: Hard Frame (Merit-Based Mobility, Institutionalized "
                "Innovation, Eliminating Property Managers) and Soft Connection (Career "
                "Sovereignty, Psychological Safety Net, Dignified Transitions). Dependent "
                "variable: the Survival Premium."
            )
        },
        {
            "name": "Governance Debt",
            "alternateName": "治理负债",
            "url": "https://insightbridge.global/theories/governance-debt",
            "description": (
                "Framework developed by Dr. Tong Yin treating unresolved governance and trust "
                "deficits as liabilities compounding against an organisation's future capacity. "
                "Four types: Deferred Accountability, Deferred Structure, Deferred Succession, "
                "Deferred Truth. Interest paid through the Mistrust Tax. Extends Ben Horowitz's "
                "2012 management-debt concept with operational measurement proxies."
            )
        },
        {
            "name": "Dynamic Driver Replacement Theory (DDRT)",
            "alternateName": "动态驱动力替代理论",
            "url": "https://insightbridge.global/theories/ddrt",
            "description": (
                "Strategic framework originated by Dr. Tong Yin modelling how an organisation "
                "replaces a declining growth driver with a new one without losing structural "
                "stability. Four stages: Driver Saturation, Replacement Window, Substitution or "
                "Compression, Structural Reset. Three feasibility conditions: Slack, Trust "
                "Reserve (the Home Model's survival premium), and Code Integrity (Core Code "
                "Theory's dependent variable)."
            )
        }
    ]

    for fw in frameworks:
        graph.append({
            "@type": "CreativeWork",
            "@id": fw["url"],
            "name": fw["name"],
            "alternateName": fw.get("alternateName", ""),
            "url": fw["url"],
            "description": fw["description"],
            "author": {"@id": "https://insightbridge.global/#founder"},
            "creator": {"@id": "https://insightbridge.global/#org"}
        })

    # --- Three AI Systems ---
    ai_systems = [
        {
            "name": "POLARIS",
            "description": (
                "AI dynamic pricing engine for hospitality revenue optimization. Uses "
                "XGBoost + LSTM hybrid with five weighted demand drivers (cross-border "
                "visitor flow, holiday/event compression, weekend effect, OTA booking pace, "
                "competitive saturation) and guardrail-bounded pricing. Delivered 6-12% ADR "
                "uplift and 3-5 percentage point OTA commission share reduction in live "
                "deployments."
            )
        },
        {
            "name": "ORION",
            "description": (
                "Customer intelligence AI system for hospitality. Performs segment analysis, "
                "guest profiling, and behavioral pattern recognition to optimize marketing "
                "and revenue strategy."
            )
        },
        {
            "name": "NOVA",
            "description": (
                "Tactical direct-booking optimization AI system designed to systematically "
                "reduce hotel dependency on online travel agencies (OTAs) by strengthening "
                "direct booking channels."
            )
        }
    ]

    for sys in ai_systems:
        graph.append({
            "@type": "SoftwareApplication",
            "name": sys["name"],
            "description": sys["description"],
            "applicationCategory": "BusinessApplication",
            "operatingSystem": "Cloud",
            "provider": {"@id": "https://insightbridge.global/#org"}
        })

    return {"@context": "https://schema.org", "@graph": graph}


# =============================================================================
# 2. BUILDTELLIGENCE — FULL SCHEMA
# =============================================================================

def build_buildtelligence_schema():
    """Build the complete Buildtelligence JSON-LD @graph."""

    org = {
        "@type": "Organization",
        "@id": "https://www.buildtelligence.com/#org",
        "name": "Buildtelligence",
        "url": "https://www.buildtelligence.com",
        "description": (
            "AI enablement and implementation company for mid-sized businesses. "
            "Helps companies move from AI experimentation to governed implementation "
            "through strategy, workflow design, governance, training, and operating support. "
            "Implementation partner for the ThinkFreely AI Operating Layer."
        ),
        "knowsAbout": [
            "AI Implementation",
            "AI Governance",
            "AI Workflow Design",
            "AI Readiness Assessment",
            "Private Knowledge Assistants",
            "AI Operating Layer",
            "Enterprise AI Adoption",
            "AI Skills Development"
        ],
        "areaServed": "United States"
    }

    thinkfreely = {
        "@type": "SoftwareApplication",
        "@id": "https://www.buildtelligence.com/lodesight#thinkfreely",
        "name": "ThinkFreely",
        "description": (
            "AI Operating Layer for practical implementation. Provides controlled "
            "management of AI activity across models, workloads, privacy boundaries, "
            "workflows, and teams. Features RouteFreely (capability-aware routing, "
            "priority-aware queueing, privacy-aware dispatch, and failover engine) "
            "and DriftHold (instruction-stability layer for preserving constraints, "
            "role definitions, tone requirements, and governance rules across long-running "
            "AI work)."
        ),
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Cloud",
        "featureList": [
            "RouteFreely capability-aware routing across language, vision, and embedding requests",
            "Priority-aware queueing with normal, express, and higher-priority paths",
            "Privacy-aware dispatch: local-only, remote-allowed, or fail-closed",
            "Failover and recovery through retry and requeue to compatible alternatives",
            "DriftHold instruction stability and prompt anchoring",
            "Multi-model management across hosts and capabilities",
            "Usage visibility, governance alignment, and operational diagnostics"
        ],
        "provider": {"@id": "https://www.buildtelligence.com/#org"},
        "url": "https://www.buildtelligence.com/lodesight"
    }

    services = [
        {
            "@type": "Service",
            "name": "AI Readiness Assessment",
            "description": (
                "Structured assessment of current AI activity, risks, priorities, "
                "governance gaps, and the most practical next step for mid-sized "
                "companies beginning or expanding AI adoption."
            ),
            "provider": {"@id": "https://www.buildtelligence.com/#org"},
            "url": "https://www.buildtelligence.com/ai-readiness"
        },
        {
            "@type": "Service",
            "name": "AI Workflow Implementation",
            "description": (
                "Translates promising AI use cases into workflow changes, operating "
                "systems, and implementation that teams can actually use inside real "
                "operations. Covers use-case selection, workflow design, and "
                "implementation discipline."
            ),
            "provider": {"@id": "https://www.buildtelligence.com/#org"},
            "url": "https://www.buildtelligence.com/ai-workflow-implementation"
        },
        {
            "@type": "Service",
            "name": "AI Governance and Training",
            "description": (
                "Creates clearer AI policies, safer adoption patterns, and a stronger "
                "operating model for teams using AI in real work. Covers data handling, "
                "policy creation, access rules, privacy boundaries, and review processes."
            ),
            "provider": {"@id": "https://www.buildtelligence.com/#org"},
            "url": "https://www.buildtelligence.com/ai-governance-training"
        }
    ]

    faq = {
        "@type": "FAQPage",
        "@id": "https://www.buildtelligence.com/#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "What is Buildtelligence?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "Buildtelligence is an AI enablement and implementation company "
                        "that helps mid-sized businesses move from AI experimentation to "
                        "practical implementation through strategy, workflow design, "
                        "governance, training, and operating support."
                    )
                }
            },
            {
                "@type": "Question",
                "name": "What is ThinkFreely?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "ThinkFreely is the AI Operating Layer that Buildtelligence "
                        "implements. It helps companies manage AI activity through routing, "
                        "queueing, privacy-aware handling, usage visibility, workflow "
                        "control, failover, prompt anchoring, and governance support."
                    )
                }
            },
            {
                "@type": "Question",
                "name": "What is the RouteFreely Engine?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "RouteFreely is the routing, queueing, privacy-aware dispatch, "
                        "and failover subsystem inside ThinkFreely. It determines where "
                        "AI work should go, what capabilities it requires, how it should "
                        "be prioritized, and how it should recover when something goes wrong."
                    )
                }
            },
            {
                "@type": "Question",
                "name": "What is DriftHold?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "DriftHold is the instruction-stability layer inside ThinkFreely. "
                        "It preserves important instructions, constraints, role definitions, "
                        "and workflow expectations during longer or more complex AI "
                        "interactions where context drift can weaken the original "
                        "instruction set."
                    )
                }
            },
            {
                "@type": "Question",
                "name": "What is an AI operating layer?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "An AI operating layer is the structure that helps manage AI "
                        "activity across models, workloads, privacy boundaries, governance "
                        "requirements, workflows, and usage patterns. It gives companies "
                        "more visibility, direction, and control as AI adoption grows."
                    )
                }
            }
        ]
    }

    graph = [org, thinkfreely] + services + [faq]
    return {"@context": "https://schema.org", "@graph": graph}


# =============================================================================
# 3. OUTPUT
# =============================================================================

def write_outputs():
    output_dir = os.path.dirname(os.path.abspath(__file__))

    ib_schema = build_insightbridge_schema()
    bt_schema = build_buildtelligence_schema()

    # JSON files (for programmatic use)
    with open(os.path.join(output_dir, "insightbridge_schema.json"), "w", encoding="utf-8") as f:
        json.dump(ib_schema, f, indent=2, ensure_ascii=False)

    with open(os.path.join(output_dir, "buildtelligence_schema.json"), "w", encoding="utf-8") as f:
        json.dump(bt_schema, f, indent=2, ensure_ascii=False)

    # HTML files (ready to paste into <head>)
    ib_html = (
        "<!-- ============================================================ -->\n"
        "<!-- InsightBridge Global — Schema.org JSON-LD Structured Data    -->\n"
        "<!-- Paste this entire block inside the <head> tag of every page  -->\n"
        "<!-- on insightbridge.global.                                     -->\n"
        "<!-- Generated: September 2026 | GEO Optimization Package        -->\n"
        "<!-- ============================================================ -->\n"
        '<script type="application/ld+json">\n'
        + json.dumps(ib_schema, indent=2, ensure_ascii=False)
        + "\n</script>\n"
    )

    bt_html = (
        "<!-- ============================================================ -->\n"
        "<!-- Buildtelligence — Schema.org JSON-LD Structured Data         -->\n"
        "<!-- Paste this entire block inside the <head> tag of every page  -->\n"
        "<!-- on www.buildtelligence.com.                                  -->\n"
        "<!-- Generated: September 2026 | GEO Optimization Package        -->\n"
        "<!-- ============================================================ -->\n"
        '<script type="application/ld+json">\n'
        + json.dumps(bt_schema, indent=2, ensure_ascii=False)
        + "\n</script>\n"
    )

    with open(os.path.join(output_dir, "insightbridge_schema.html"), "w", encoding="utf-8") as f:
        f.write(ib_html)

    with open(os.path.join(output_dir, "buildtelligence_schema.html"), "w", encoding="utf-8") as f:
        f.write(bt_html)

    print("=" * 60)
    print("  GEO Schema Generation Complete")
    print("=" * 60)
    print()
    print("  Output files:")
    print(f"    1. {os.path.join(output_dir, 'insightbridge_schema.json')}")
    print(f"    2. {os.path.join(output_dir, 'insightbridge_schema.html')}")
    print(f"    3. {os.path.join(output_dir, 'buildtelligence_schema.json')}")
    print(f"    4. {os.path.join(output_dir, 'buildtelligence_schema.html')}")
    print()
    print("  Instructions:")
    print("    - Open the .html files")
    print("    - Copy the entire <script> block")
    print("    - Paste into the <head> section of your website")
    print("    - Validate at: https://search.google.com/test/rich-results")
    print("    - Then submit URL in Google Search Console")
    print()
    print("  Validation:")
    ib_nodes = len(ib_schema["@graph"])
    bt_nodes = len(bt_schema["@graph"])
    print(f"    InsightBridge: {ib_nodes} schema nodes generated")
    print(f"    Buildtelligence: {bt_nodes} schema nodes generated")
    print()


if __name__ == "__main__":
    write_outputs()
