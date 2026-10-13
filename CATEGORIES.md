# Category Definitions

Domain: **IT helpdesk**. The machine-readable version of this file is [`categories.json`](categories.json). The classifier builds its prompt and its output schema from that file, so the two cannot drift apart.

## Output fields

| Field | Values |
|---|---|
| `request_type` | `it_related`, `non_it_related`, `unclear` |
| `category` | `hardware`, `software`, `network`, `account`, `access`, `security`, `other` |
| `subcategory` | One of the subcategories of the chosen category (see below) |
| `affected_device` | `laptop`, `desktop`, `monitor`, `printer`, `mobile`, `router`, `peripheral`, `other`, `none`, `unknown` |
| `priority` | `low`, `medium`, `high` |
| `confidence` | 0.0–1.0, how sure the model is about category and subcategory |
| `needs_clarification` | `true` when the message cannot be routed without more details |
| `reasoning` | One short sentence explaining the choice |

## Request types

| Value | Meaning | Example |
|---|---|---|
| `it_related` | An IT problem or request | "My laptop won't turn on." |
| `non_it_related` | Clearly outside IT | "What is the company's holiday policy?" |
| `unclear` | Asks for help but does not say what is wrong | "It's not working. Please fix it." |

## Categories and subcategories

### hardware: physical devices and peripherals
| Subcategory | Meaning |
|---|---|
| `startup_failure` | Device will not power on, boot or start |
| `display_issue` | Screen or monitor blank, flickering, distorted, no signal |
| `printer_issue` | Paper jam, offline, not printing, broken |
| `peripheral_issue` | Keyboard, mouse, headset, webcam, dock |
| `physical_damage` | Cracked, dropped, water-damaged |
| `hardware_other` | Any other hardware problem |

### software: applications and the operating system
| Subcategory | Meaning |
|---|---|
| `application_crash` | App closes, crashes or will not open |
| `software_installation` | Install, uninstall or license software |
| `software_update` | Request for, or problem with, an update |
| `performance_issue` | Slow, freezing, hanging |
| `software_error` | Error message or incorrect behaviour |
| `how_to_question` | How to use or configure software |
| `software_other` | Any other software problem |

### network: Wi-Fi, wired, internet, VPN
| Subcategory | Meaning |
|---|---|
| `wifi_connection` | Cannot connect, drops, or Wi-Fi is down |
| `internet_connectivity` | On the network but no internet |
| `vpn_issue` | VPN will not connect or keeps dropping |
| `network_other` | Any other network problem |

### account: identity and credentials
| Subcategory | Meaning |
|---|---|
| `password_reset` | Forgot password or wants a reset |
| `login_failure` | Knows credentials but cannot sign in |
| `account_locked` | Account locked or disabled |
| `account_creation` | Create or remove an account |
| `account_other` | Any other account problem |

### access: permissions for a user who can already sign in
| Subcategory | Meaning |
|---|---|
| `permission_request` | Asking for new access |
| `permission_error` | "Access denied" on something they should reach |
| `application_access` | Cannot reach an internal system or portal (not a credentials problem) |
| `access_other` | Any other access problem |

### security: risk to company data or systems
| Subcategory | Meaning |
|---|---|
| `phishing_suspicion` | Suspicious email, message or link |
| `malware_suspicion` | Virus, ransomware, suspicious pop-ups |
| `lost_or_stolen_device` | Work device lost or stolen |
| `data_breach` | Data exposed or accessed without authorisation |
| `security_other` | Any other security concern |

### other
`other` is used only for `non_it_related` and `unclear` messages.

## Affected device rules

- A device named in the message is used (`laptop`, `printer`, …).
- `none`: the issue is not about a device (account, access, phishing, non-IT).
- `unknown`: a device is involved but not named ("my email app crashes", "my Wi-Fi drops"), and for unclear messages.

## Priority rules

| Priority | When |
|---|---|
| `high` | Any suspected security incident, or an outage stopping many people, a team or the whole office |
| `medium` | Stops or seriously disrupts one person's (or a small group's) work |
| `low` | Requests, how-to questions, minor problems with a workaround, non-IT and unclear messages |

Priority is based on impact, not tone: "URGENT!!!" on its own does not raise priority.

## Handling unclear input

- Empty input returns `unclear` immediately without calling the model.
- Vague or gibberish messages get `request_type: unclear`, `needs_clarification: true`, priority `low`.
- If the model returns a subcategory that belongs to a different category, the category is corrected to match the subcategory.
- If the model returns `non_it_related` or `unclear`, the remaining fields are forced to their fixed values.
- Text in the message that tries to change the rules (prompt injection) is ignored.
