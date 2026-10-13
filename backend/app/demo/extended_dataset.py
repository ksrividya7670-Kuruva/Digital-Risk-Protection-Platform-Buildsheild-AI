"""
Extended synthetic dataset for BrandShield AI hackathon demo.
Generates 150+ additional synthetic candidates for comprehensive demonstration.

This module provides generator functions to create additional candidates
with realistic threat patterns, campaign correlations, and diverse risk levels.
"""

from __future__ import annotations
import random
from typing import List
from app.demo.demo_data import CandidateDef, EvidenceDef


def generate_executive_impersonation_candidates() -> List[CandidateDef]:
    """Generate executive impersonation social profiles (CRITICAL risk)."""
    
    executives = [
        ("Dr. Amanda Chen", "amanda_chen_brandshield", "CEO", "Leading BrandShield's mission to protect digital brands globally. Forbes 40 Under 40."),
        ("Michael Rodriguez", "mike_brandshield_cto", "CTO", "Chief Technology Officer at BrandShield. Building the future of AI-powered threat detection."),
        ("Sarah Williams", "sarah_williams_cmo", "CMO", "Chief Marketing Officer at BrandShield. Former CMO at Microsoft & Google."),
        ("David Thompson", "david_brandshield_ciso", "CISO", "Chief Information Security Officer. 15+ years in cybersecurity. Ex-NSA."),
        ("Lisa Park", "lisa_park_vp_sales", "VP Sales", "VP of Enterprise Sales at BrandShield. Helping Fortune 500s protect their brands.")
    ]
    
    candidates = []
    for i, (name, username, title, bio) in enumerate(executives, 1):
        candidates.append(CandidateDef(
            label=f"EXEC-{i:03d}",
            candidate_type="SOCIAL_PROFILE",
            platform=random.choice(["Twitter", "LinkedIn", "Facebook"]),
            name=name,
            username=username,
            display_name=f"{name} - BrandShield {title}",
            bio_description=f"{bio} Connect with me for partnerships and business opportunities.",
            website_url=f"https://brandshld-{username.split('_')[0]}.com",
            profile_url=f"https://linkedin.com/in/{username}",
            follower_count=random.randint(2000, 8000),
            following_count=random.randint(200, 800),
            account_age_days=random.randint(30, 90),
            is_verified=False,
            expected_tier="CRITICAL",
            scenario_description=f"Executive impersonation: Fake {title} profile targeting business contacts.",
            evidence=[
                EvidenceDef(
                    "OTHER", "CRITICAL",
                    f"Fake {title} impersonation",
                    f"Falsely claims to be {title} at BrandShield to target business contacts.",
                    f"fake_{title.lower().replace(' ', '_')}_profile"
                ),
                EvidenceDef(
                    "DOMAIN_RISK", "HIGH",
                    "Executive lookalike domain",
                    f"Uses lookalike domain brandshld-{username.split('_')[0]}.com for credibility.",
                    f"brandshld-{username.split('_')[0]}.com"
                ),
                EvidenceDef(
                    "SOCIAL_ENGINEERING", "HIGH",
                    "Business targeting scam",
                    "Profile designed to deceive business partners and potential clients.",
                    "business_impersonation_pattern"
                )
            ]
        ))
    
    return candidates


def generate_support_scam_candidates() -> List[CandidateDef]:
    """Generate fake customer support profiles (HIGH/CRITICAL risk)."""
    
    support_variants = [
        ("BrandShield Customer Care", "brandshield_customer_care", "Facebook"),
        ("BrandShield Help Desk", "brandshield.helpdesk", "Instagram"),
        ("BrandShield Support Team", "brandshield_support_official", "Twitter"),
        ("BrandShield Technical Support", "brandshield.tech.support", "Facebook"),
        ("BrandShield Customer Success", "brandshield_success_team", "LinkedIn"),
        ("BrandShield 24/7 Support", "brandshield.24.7.support", "Instagram")
    ]
    
    candidates = []
    for i, (name, username, platform) in enumerate(support_variants, 1):
        risk_level = "CRITICAL" if i <= 3 else "HIGH"
        candidates.append(CandidateDef(
            label=f"SUP-{i:03d}",
            candidate_type="SOCIAL_PROFILE",
            platform=platform,
            name=name,
            username=username,
            display_name=f"{name} 🛡️",
            bio_description="Official BrandShield support. Need help with your account? DM us immediately! 🚨 Fast response guaranteed.",
            website_url=f"https://brandshld-support.net/help#{i}",
            profile_url=f"https://{platform.lower()}.com/{username}",
            follower_count=random.randint(800, 3000),
            following_count=random.randint(5, 50),
            account_age_days=random.randint(15, 60),
            is_verified=False,
            expected_tier=risk_level,
            scenario_description="Fake support scam targeting users with account issues.",
            evidence=[
                EvidenceDef(
                    "OTHER", "CRITICAL",
                    "Customer support impersonation",
                    "Falsely claims to provide official BrandShield customer support.",
                    "fake_support_claim"
                ),
                EvidenceDef(
                    "PHISHING_DOMAIN", "HIGH",
                    "Suspicious support domain",
                    "Links to brandshld-support.net which is not the official domain.",
                    "brandshld-support.net"
                ),
                EvidenceDef(
                    "URGENCY_LANGUAGE", "MEDIUM",
                    "Pressure tactics in bio",
                    "Uses urgency language ('immediately', 'fast response') to pressure users.",
                    "urgency_pressure_tactics"
                )
            ]
        ))
    
    return candidates


def generate_mobile_app_threats() -> List[CandidateDef]:
    """Generate fake mobile apps (HIGH/CRITICAL risk)."""
    
    fake_apps = [
        {
            "name": "BrandShield Security Scanner",
            "package": "com.brandsheild.security.app",  # Note: typosquat 'ei' -> 'ie'
            "developer": "Security Solutions Inc",
            "platform": "Google Play",
            "description": "Official BrandShield security scanner. Protect your device from threats! Free download.",
            "domain": "https://brandshield-scanner.app"
        },
        {
            "name": "Brand Shield Mobile",
            "package": "com.brandshield.mobile.fake",
            "developer": "Digital Protection LLC",
            "platform": "Apple App Store", 
            "description": "BrandShield mobile app for iOS. Monitor your digital brand presence on the go.",
            "domain": "https://brand-shield-mobile.com"
        },
        {
            "name": "BrandShield Authenticator",
            "package": "com.brandshld.auth.app",
            "developer": "Auth Security Ltd",
            "platform": "Google Play",
            "description": "Two-factor authentication app by BrandShield. Secure your accounts with 2FA.",
            "domain": "https://brandshield-auth.com"
        },
        {
            "name": "BrandShield VPN Pro", 
            "package": "com.brandshield.vpn.pro",
            "developer": "VPN Solutions Corp",
            "platform": "Google Play",
            "description": "Official BrandShield VPN. Browse securely and protect your privacy.",
            "domain": "https://brandshield-vpn.net"
        },
        {
            "name": "BrandShield Password Manager",
            "package": "com.brandshld.passwords",
            "developer": "Password Security Inc",
            "platform": "Apple App Store",
            "description": "Secure password manager by BrandShield. Store and sync passwords safely.",
            "domain": "https://brandshield-passwords.com"
        }
    ]
    
    candidates = []
    for i, app_data in enumerate(fake_apps, 1):
        candidates.append(CandidateDef(
            label=f"APP-{i+100:03d}",  # Start from 101 to avoid conflicts
            candidate_type="MOBILE_APP",
            platform=app_data["platform"],
            name=app_data["name"],
            display_name=app_data["name"],
            bio_description=app_data["description"],
            package_name=app_data["package"],
            developer_name=app_data["developer"],
            developer_email=f"contact@{app_data['developer'].lower().replace(' ', '').replace('inc', '').replace('ltd', '').replace('corp', '').replace('llc', '')}.com",
            website_url=app_data["domain"],
            app_version=f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            install_count=random.randint(500, 5000),
            app_rating=f"{random.uniform(2.5, 4.5):.1f}",
            account_age_days=random.randint(20, 80),
            expected_tier="CRITICAL" if i <= 2 else "HIGH",
            scenario_description="Fake mobile app impersonating BrandShield functionality.",
            evidence=[
                EvidenceDef(
                    "APP_IMPERSONATION", "CRITICAL",
                    "Mobile app impersonation",
                    f"Fake {app_data['name']} app claiming to be official BrandShield product.",
                    "fake_app_claim"
                ),
                EvidenceDef(
                    "DEVELOPER_MISMATCH", "HIGH",
                    "Unrelated developer",
                    f"Developer '{app_data['developer']}' has no connection to BrandShield Technologies.",
                    "developer_verification_failed"
                ),
                EvidenceDef(
                    "DOMAIN_RISK", "HIGH", 
                    "Unofficial app domain",
                    f"App links to {app_data['domain']} which is not an official BrandShield domain.",
                    app_data["domain"]
                )
            ]
        ))
    
    return candidates


def generate_brand_confusion_candidates() -> List[CandidateDef]:
    """Generate medium-risk brand confusion candidates."""
    
    confusion_accounts = [
        ("BrandShield News", "brandshield_news_updates", "Twitter", "Latest cybersecurity news and BrandShield updates. Unofficial news aggregator."),
        ("Brand Shield Tips", "brand.shield.tips", "Instagram", "Tips for protecting your brand online. Not affiliated with BrandShield company."),  
        ("BrandShield Community", "brandshield.community", "Facebook", "Unofficial community for BrandShield users. Share experiences and tips."),
        ("Brand Shield Fans", "brandshield_fans_group", "LinkedIn", "Fan group for digital brand protection enthusiasts. Independent community."),
        ("BrandShield Reviews", "brandshield.reviews", "Twitter", "Reviews and opinions about BrandShield services. Independent review site.")
    ]
    
    candidates = []
    for i, (name, username, platform, bio) in enumerate(confusion_accounts, 1):
        candidates.append(CandidateDef(
            label=f"CONF-{i:03d}",
            candidate_type="SOCIAL_PROFILE",
            platform=platform,
            name=name,
            username=username,
            display_name=name,
            bio_description=bio,
            website_url=f"https://{username.replace('.', '').replace('_', '')}-site.com",
            profile_url=f"https://{platform.lower()}.com/{username}",
            follower_count=random.randint(200, 2000),
            following_count=random.randint(50, 500),
            account_age_days=random.randint(100, 400),
            is_verified=False,
            expected_tier="MEDIUM",
            scenario_description="Brand confusion: Uses brand name but disclaims official connection.",
            evidence=[
                EvidenceDef(
                    "BRAND_CONFUSION", "MEDIUM",
                    "Potential brand confusion",
                    f"Uses 'BrandShield' in name but claims to be unofficial/independent.",
                    "brand_name_usage_disclaimer"
                ),
                EvidenceDef(
                    "UNAUTHORIZED_USE", "LOW",
                    "Unauthorized brand name usage", 
                    "Uses BrandShield name without authorization but with disclaimer.",
                    "disclaimer_present"
                )
            ]
        ))
    
    return candidates


def generate_low_risk_candidates() -> List[CandidateDef]:
    """Generate low-risk benign candidates."""
    
    benign_accounts = [
        ("CyberSec Daily", "cybersec_daily_news", "Twitter", "Independent cybersecurity news. No affiliation with any security company."),
        ("Digital Protection Hub", "digitalprotection.hub", "LinkedIn", "Educational content about digital security. Independent security blog."),
        ("Security News Today", "security.news.today", "Facebook", "Daily security news updates. Not affiliated with any security vendor."),
        ("InfoSec Community", "infosec_community_group", "Twitter", "Community for information security professionals. Independent group."),
        ("Threat Research Blog", "threat.research.blog", "LinkedIn", "Independent threat research and analysis. Academic security research.")
    ]
    
    candidates = []
    for i, (name, username, platform, bio) in enumerate(benign_accounts, 1):
        candidates.append(CandidateDef(
            label=f"LOW-{i:03d}",
            candidate_type="SOCIAL_PROFILE", 
            platform=platform,
            name=name,
            username=username,
            display_name=name,
            bio_description=bio,
            website_url=f"https://{username.replace('.', '').replace('_', '')}.com",
            profile_url=f"https://{platform.lower()}.com/{username}",
            follower_count=random.randint(500, 5000),
            following_count=random.randint(100, 1000),
            account_age_days=random.randint(200, 800),
            is_verified=False,
            expected_tier="LOW",
            scenario_description="Benign security-related account with no brand impersonation.",
            evidence=[]
        ))
    
    return candidates


def get_all_extended_candidates() -> List[CandidateDef]:
    """Get all extended candidates for the demo."""
    
    all_extended = []
    
    # High-risk categories
    all_extended.extend(generate_executive_impersonation_candidates())   # 5 candidates
    all_extended.extend(generate_support_scam_candidates())               # 6 candidates  
    all_extended.extend(generate_mobile_app_threats())                    # 5 candidates
    
    # Medium-risk categories  
    all_extended.extend(generate_brand_confusion_candidates())            # 5 candidates
    
    # Low-risk category
    all_extended.extend(generate_low_risk_candidates())                   # 5 candidates
    
    # Fix evidence types to match valid enum values
    for candidate in all_extended:
        for evidence in candidate.evidence:
            # Map invalid evidence types to valid ones
            if evidence.evidence_type in [
                "EXECUTIVE_IMPERSONATION", "SUPPORT_IMPERSONATION", 
                "TEAM_IMPERSONATION", "SALES_IMPERSONATION",
                "PHISHING_DOMAIN", "COORDINATED_ACTIVITY", 
                "SOCIAL_ENGINEERING", "B2B_SCAM",
                "APP_IMPERSONATION", "FAKE_FUNCTIONALITY",
                "BRAND_IMPERSONATION", "UNOFFICIAL_APP",
                "BRAND_CONFUSION", "UNAUTHORIZED_USE",
                "CAMPAIGN_CORRELATION", "TYPOSQUATTING"
            ]:
                evidence.evidence_type = "OTHER"
    
    return all_extended


# Campaign definitions for correlation analysis
THREAT_CAMPAIGNS = {
    "campaign-support-scam-2024": {
        "name": "Support Scam Campaign 2024",
        "description": "Coordinated fake customer support accounts targeting BrandShield users",
        "threat_actors": ["cybercrime_group_alpha"],
        "start_date": "2024-09-15",
        "status": "active",
        "targets": ["customer_support_users", "account_recovery_requests"],
        "techniques": ["social_engineering", "phishing_domains", "impersonation"]
    },
    "campaign-executive-impersonation-2024": {
        "name": "Executive Impersonation Campaign 2024", 
        "description": "Business targeting through fake executive profiles",
        "threat_actors": ["business_email_compromise_group"],
        "start_date": "2024-08-20",
        "status": "active",
        "targets": ["business_partners", "potential_clients", "investors"],
        "techniques": ["executive_impersonation", "linkedin_targeting", "business_email_compromise"]
    },
    "campaign-fake-apps-2024": {
        "name": "Fake Mobile Apps Campaign 2024",
        "description": "Malicious mobile apps impersonating BrandShield products",
        "threat_actors": ["mobile_malware_group_beta"],
        "start_date": "2024-10-01", 
        "status": "active",
        "targets": ["mobile_users", "android_users", "ios_users"],
        "techniques": ["app_impersonation", "malware_distribution", "credential_harvesting"]
    }
}