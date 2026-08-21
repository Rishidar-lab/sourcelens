# Incident Response Policy

**Document status:** Current policy
**Document owner:** Security Operations
**Effective date:** 2026-02-01
**Version:** 2.1

## Purpose and scope

This policy establishes the minimum response process for suspected or confirmed security incidents involving company information, systems, accounts, devices, or vendors. An incident includes unauthorized access, malware, accidental disclosure, lost equipment containing company data, suspicious credential use, and material service compromise. The policy applies to employees, contractors, and interns.

## Immediate reporting

Anyone who suspects a security incident must report it to the Security Operations channel or the on-call security address **within 30 minutes of discovery**. The report should state what was observed, when it was observed, which system or data may be involved, and how the reporter can be reached. A reporter should not delay reporting while attempting to prove the incident or determine its severity.

If an account may be compromised, the reporter should stop using the affected session, disconnect an affected device from untrusted networks when safe, and contact Security Operations. Employees must not delete logs, wipe devices, negotiate with an attacker, or send potentially sensitive evidence to a personal account. Security Operations coordinates containment and decides whether additional leaders, legal counsel, customers, or regulators must be notified.

## Triage and severity

Security Operations assigns an incident lead and records a case identifier. The lead classifies the event as critical, high, medium, or low using impact, scope, data sensitivity, and ongoing exposure. Critical incidents require continuous coordination and an executive notification as soon as practical. High incidents require an incident lead, documented containment actions, and updates at least every four hours while active. Medium and low incidents are tracked to closure with an agreed owner and target date.

## Evidence and communications

Evidence must be preserved in its original form whenever practical. Access to the incident record is limited to people who need it for response. Public statements, customer notices, and regulator communications may be issued only by the designated communications or legal representative. Team members must not speculate publicly or post incident details on social media.

## Recovery and learning

Before closing an incident, the lead records the timeline, root cause or current hypothesis, affected assets, containment and recovery actions, notification decisions, and follow-up owners. Security Operations conducts a review within ten business days for every critical or high incident and updates controls when the review identifies a repeatable improvement.

**SourceLens evaluation note:** The 30-minute reporting requirement and the ten-business-day review window are distinct facts that should not be conflated.
