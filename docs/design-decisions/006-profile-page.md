# 006: Profile Page

**Date**: 2026-03-23
**Status**: Implemented
**Context**: Users needed a way to update their personal info and preferences after initial registration. The onboarding survey was separated from account creation, so users might want to fill in or update venture details later.

## Decision
Add a profile screen accessible from the drawer footer ("Profile & Settings"):

- **Personal Info**: name, phone number (editable)
- **Business**: venture name, description, industry (editable)
- **Preferences**: language (English, Luganda, Acholi)

All fields save via `PATCH /api/v1/me`. Backend `allowed_fields` expanded to include: name, phone_number, venture_name, venture_description, industry_vertical, language_preference.

## UX
- Back arrow returns to chat (not to a separate screen)
- "Saved!" confirmation appears briefly after save
- Profile data is populated from the `participant` object in localStorage

## Language preference
Stored as `language_preference` on the participant model. Included in the system prompt so the AI can match the user's preferred language. Not yet enforced in the UI itself (UI remains English).
